#!/usr/bin/env python3
"""Build audited directory and GitHub packages without account connections."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

SLUG = "project-to-portfolio"
FORBIDDEN_TEXT = re.compile(r"/(?:Users|home)/[^\s]+|BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY|\b(?:Resend|VPS|private[ -]Studio)\b", re.I)
SECRET = re.compile(r"\bsk-[a-zA-Z0-9_-]{24,}\b")
EXCLUDED = {"__pycache__", ".DS_Store", "node_modules", ".git", ".venv"}


def files(root):
    return sorted(path for path in root.rglob("*") if path.is_file() and not any(part in EXCLUDED for part in path.relative_to(root).parts) and path.suffix not in (".pyc", ".pyo"))


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def plugin_files(root):
    paths = [root / ".codex-plugin" / "plugin.json", root / "README.md"]
    for folder in (root / "assets", root / "skills"):
        paths.extend(files(folder))
    return sorted(paths)


def audit_plugin(root):
    manifest = json.loads((root / ".codex-plugin" / "plugin.json").read_text())
    if manifest.get("name") != SLUG or not re.fullmatch(r"\d+\.\d+\.\d+", manifest.get("version", "")):
        raise ValueError("Plugin identity/version is invalid.")
    if any(key in manifest for key in ("mcpServers", "apps", "hooks")) or "screenshots" in manifest["interface"]:
        raise ValueError("The directory release must remain skills-only.")
    expected = {"logo", "composerIcon"}
    for key in expected:
        path = (root / manifest["interface"][key]).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError("A manifest image is missing or not portable.")
    skills = list((root / "skills").glob("*/SKILL.md"))
    if not skills:
        raise ValueError("At least one skill is required.")
    for skill in skills:
        text = skill.read_text()
        if not text.startswith("---\n") or not re.search(r"^name: " + SLUG + r"$", text, re.M) or not re.search(r"^description: .+", text, re.M) or "[TODO" in text:
            raise ValueError("Skill frontmatter/scaffold is incomplete.")
        for link in re.findall(r"\]\(([^)]+)\)", text):
            if "://" not in link and not (skill.parent / link).is_file():
                raise ValueError("A skill reference is missing: " + link)
    count = 0
    for path in plugin_files(root):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink() or path.name in {".mcp.json", "mcp.json", ".app.json"} or "hooks" in path.parts:
            raise ValueError("Unsupported release entry: " + relative)
        if path.suffix in (".md", ".json", ".yaml", ".py", ".html", ".svg"):
            text = path.read_text(encoding="utf-8")
            if FORBIDDEN_TEXT.search(text) or SECRET.search(text):
                raise ValueError("Publisher-specific material or a secret appears in " + relative)
        count += 1
    return {"version": manifest["version"], "fileCount": count, "skillsOnly": True,
            "bytes": sum(path.stat().st_size for path in plugin_files(root))}


def archive(root, destination):
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for file in files(root):
            info = zipfile.ZipInfo(root.name + "/" + file.relative_to(root).as_posix(), (2026, 10, 2, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            output.writestr(info, file.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(destination) as check:
        if check.testzip() is not None:
            raise ValueError("Archive integrity failed.")
    return {"file": destination.name, "bytes": destination.stat().st_size,
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(), "fileCount": len(files(root))}


def build(source, output):
    plugin = source if (source / ".codex-plugin").is_dir() else source / "plugins" / SLUG
    report = audit_plugin(plugin)
    if output.exists():
        raise ValueError("Release output already exists; choose a new release directory.")
    if output.is_relative_to(plugin):
        raise ValueError("Release output must be outside plugin source.")
    output.mkdir(parents=True)
    clean = output / "directory-package" / SLUG
    for path in plugin_files(plugin):
        target = clean / path.relative_to(plugin)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    audit_plugin(clean)
    github = output / "github-upload" / SLUG
    shutil.copytree(clean, github / "plugins" / SLUG)
    catalog = {"name": SLUG, "interface": {"displayName": "Project to Portfolio"},
               "plugins": [{"name": SLUG, "source": {"source": "local", "path": "./plugins/" + SLUG},
                            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}, "category": "Education"}]}
    dump(github / ".agents" / "plugins" / "marketplace.json", catalog)
    readme = source / "docs" / "github-readme.md"
    if not readme.exists():
        readme = source / "README.md"
    (github / "README.md").write_text(readme.read_text())
    for relative in (".gitignore", "scripts/build_release.py", "tests/test_workflow.py", "docs/publishing.md"):
        target = github / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, target)
    total = files(github)
    if len(total) > 100 or max(path.stat().st_size for path in total) > 25 * 1024 * 1024:
        raise ValueError("GitHub web upload exceeds a single-upload browser limit.")
    # Ignore the audit helper's own regex text; executable plugin payload has already been checked.
    versions = {path.relative_to(clean).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in files(clean)}
    plugin_archive = archive(clean, output / f"{SLUG}-{report['version']}-directory.zip")
    github_archive = archive(github, output / f"{SLUG}-{report['version']}-github.zip")
    receipt = {"name": SLUG, **report, "directoryArchive": plugin_archive, "githubArchive": github_archive,
               "githubWebUpload": {"fileCount": len(total), "maximumFileBytes": max(path.stat().st_size for path in total)},
               "files": versions, "remoteSubmission": "not-performed", "remotePublication": "not-performed"}
    dump(output / "release-manifest.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        report = build(Path(args.source).resolve(), Path(args.output).resolve())
        print(json.dumps({key: report[key] for key in ("name", "version", "fileCount", "bytes", "directoryArchive", "githubArchive", "githubWebUpload")}, indent=2))
        return 0
    except (ValueError, OSError, KeyError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
