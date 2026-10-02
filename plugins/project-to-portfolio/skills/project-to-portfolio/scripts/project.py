#!/usr/bin/env python3
"""Local student intake and approval snapshots. Python standard library only."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath

SKILL = Path(__file__).resolve().parent.parent
STATES = {"confirmed", "pending official verification", "user-authorized TBD", "N/A", "unresolved"}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def within(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError("Use a nonempty project-relative path with forward slashes.")
    if Path(name).is_absolute() or PureWindowsPath(name).is_absolute() or re.match(r"^[a-zA-Z]+:", name):
        raise ValueError("Paths must be relative to the selected project.")
    resolved = (root / name).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("A path leaves the selected project.")
    return resolved


def questions():
    return read_json(SKILL / "assets" / "questions.json")


def question_map():
    return {field["id"]: field for section in questions()["sections"] for field in section["questions"]}


def check_field(key: str, field, question):
    if not isinstance(field, dict) or set(field) - {"state", "value", "notes"}:
        raise ValueError(f"Invalid field record: {key}")
    if not {"state", "value"}.issubset(field):
        raise ValueError(f"Field needs state and value: {key}")
    state, value = field["state"], field["value"]
    if state not in STATES or not isinstance(field.get("notes", ""), str):
        raise ValueError(f"Invalid state or notes: {key}")
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        raise ValueError(f"Field values must be text or an integer: {key}")
    if state == "N/A" and not question.get("allowNA"):
        raise ValueError(f"N/A is not allowed: {key}")
    if state == "pending official verification" and not question.get("externallyVerifiable"):
        raise ValueError(f"Official verification is not applicable: {key}")
    if state == "confirmed":
        if value == "" or (isinstance(value, str) and not value.strip()):
            raise ValueError(f"Confirmed answer is empty: {key}")
        if question["kind"] == "number":
            if not isinstance(value, int) or not question["min"] <= value <= question["max"]:
                raise ValueError(f"Spread count must be an integer from {question['min']}–{question['max']}.")
        elif not isinstance(value, str):
            raise ValueError(f"Text answer required: {key}")
        if question["kind"] == "select" and value not in question["options"]:
            raise ValueError(f"Choose a listed option: {key}")
    elif question["kind"] != "number" and not isinstance(value, str):
        raise ValueError(f"Text answer required: {key}")


def check_input(data, *, partial=False):
    if not isinstance(data, dict) or data.get("schemaVersion") != 1:
        raise ValueError("Expected a schemaVersion 1 intake object.")
    allowed = {"schemaVersion", "projectSlug", "workspaceId", "intakeRevision", "language", "fields", "createdAt", "updatedAt"}
    if set(data) - allowed:
        raise ValueError("Intake contains unsupported keys; approvals are separate from answers.")
    if "projectSlug" in data and (not isinstance(data["projectSlug"], str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", data["projectSlug"])):
        raise ValueError("Project slug must use lowercase letters, numbers and hyphens.")
    if data.get("language", "en") not in ("en", "zh"):
        raise ValueError("Language must be en or zh.")
    fields = data.get("fields")
    if not isinstance(fields, dict):
        raise ValueError("Intake fields must be an object.")
    mapping = question_map()
    if set(fields) - set(mapping):
        raise ValueError("Unknown question IDs: " + ", ".join(sorted(set(fields) - set(mapping))))
    if not partial and set(fields) != set(mapping):
        raise ValueError("The project ledger must retain all thirty question IDs.")
    for key, value in fields.items():
        check_field(key, value, mapping[key])


def missing_fields(data, *, figma=False):
    result = []
    ai = data["fields"]["ai.used"]
    ai_yes = ai["state"] == "confirmed" and ai["value"] == "Yes"
    for key, question in question_map().items():
        if question.get("conditionalOnAI") and not ai_yes:
            continue
        if question["requiredFor"] == "preflight" and not figma:
            continue
        field = data["fields"][key]
        accepted = field["state"] in {"confirmed", "N/A", "user-authorized TBD"}
        if question.get("requiresConfirmed") and field["state"] != "confirmed":
            accepted = False
        if not accepted:
            result.append({"id": key, "label": question["label"], "state": field["state"]})
    return result


def project_root(value: str) -> Path:
    root = Path(value).expanduser().resolve()
    plugin = SKILL.parent.parent
    if root.is_relative_to(plugin):
        raise ValueError("Select a project workspace outside the installed plugin folder.")
    return root


def form_html(data):
    template = (SKILL / "assets" / "intake.template.html").read_text(encoding="utf-8")
    embed = lambda value: json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")
    return template.replace("__QUESTIONS_JSON__", embed(questions())).replace("__PROJECT_JSON__", embed(data))


def initialize(root: Path, slug: str):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("Project slug must use lowercase letters, numbers and hyphens.")
    if (root / "project.json").exists() or (root / "intake.html").exists():
        raise ValueError("An existing project/form will not be replaced; use status or import.")
    fields = {key: {"state": "unresolved", "value": "", "notes": ""} for key in question_map()}
    fields["delivery.plannedPages"] = {"state": "confirmed", "value": 5, "notes": ""}
    timestamp = now()
    data = {"schemaVersion": 1, "projectSlug": slug, "workspaceId": uuid.uuid4().hex,
            "intakeRevision": 1, "language": "en", "fields": fields,
            "createdAt": timestamp, "updatedAt": timestamp}
    html = form_html(data)
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "project.json", data)
    (root / "intake.html").write_text(html, encoding="utf-8")
    return {"project": str(root), "intake": str(root / "intake.html"), "questionCount": len(fields)}


def import_intake(root: Path, source: Path):
    current = read_json(root / "project.json")
    check_input(current)
    patch = read_json(source)
    check_input(patch, partial=True)
    if patch.get("projectSlug", current["projectSlug"]) != current["projectSlug"]:
        raise ValueError("This intake belongs to a different project slug.")
    if patch.get("workspaceId", current["workspaceId"]) != current["workspaceId"]:
        raise ValueError("This export belongs to a different project workspace.")
    if "intakeRevision" in patch and patch["intakeRevision"] != current["intakeRevision"]:
        raise ValueError("This export is from an older project revision; recover selected changes as a partial import.")
    merged = copy.deepcopy(current)
    merged["fields"].update({key: {"state": value["state"], "value": value["value"], "notes": value.get("notes", "")} for key, value in patch["fields"].items()})
    merged["language"] = patch.get("language", current["language"])
    changed = [key for key in current["fields"] if merged["fields"][key] != current["fields"][key]]
    if not changed and merged["language"] == current["language"]:
        return {"changedFields": [], "intakeRevision": current["intakeRevision"], "ready": not missing_fields(current)}
    merged["intakeRevision"] += 1
    merged["updatedAt"] = now()
    check_input(merged)
    html = form_html(merged)
    history = root / ".history"
    history.mkdir(exist_ok=True)
    snapshot = history / f"intake-r{current['intakeRevision']}-{uuid.uuid4().hex[:8]}.json"
    write_json(snapshot, current)
    write_json(root / "project.json", merged)
    (root / "intake.html").write_text(html, encoding="utf-8")
    return {"changedFields": changed, "intakeRevision": merged["intakeRevision"], "ready": not missing_fields(merged)}


def artifact_digest(path: Path):
    if path.is_symlink():
        raise ValueError("Bind approval to a real artifact, not a symbolic link.")
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    if not path.is_dir():
        raise ValueError("Approval artifact does not exist.")
    files = sorted(p for p in path.rglob("*") if p.is_file())
    if not files:
        raise ValueError("Approval directory is empty.")
    hashes = []
    for file in files:
        if file.is_symlink() or not file.resolve().is_relative_to(path.resolve()):
            raise ValueError("Approval artifacts cannot reference files outside their directory.")
        hashes.append([file.relative_to(path).as_posix(), hashlib.sha256(file.read_bytes()).hexdigest()])
    return hashlib.sha256(json.dumps(hashes, separators=(",", ":")).encode()).hexdigest()


def approve(root: Path, stage: str, artifact: str, record: str):
    if not record.strip():
        raise ValueError("Approval requires the student's actual authorization text.")
    project = read_json(root / "project.json")
    target = within(root, artifact)
    item = {"stage": stage, "artifact": target.relative_to(root.resolve()).as_posix(),
            "sha256": artifact_digest(target), "record": record,
            "intakeRevision": project["intakeRevision"], "approvedAt": now()}
    store = root / "approvals.json"
    ledger = read_json(store) if store.exists() else {"schemaVersion": 1, "records": []}
    ledger["records"].append(item)
    write_json(store, ledger)
    return item


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "status", "import", "validate", "approve"):
        command = sub.add_parser(name)
        command.add_argument("--project", required=True)
        if name == "init":
            command.add_argument("--slug", required=True)
        if name == "import":
            command.add_argument("--input", required=True)
        if name == "validate":
            command.add_argument("--ready", action="store_true")
            command.add_argument("--figma", action="store_true")
        if name == "approve":
            command.add_argument("--stage", choices=("plan", "sample", "batch", "source-conversion"), required=True)
            command.add_argument("--artifact", required=True)
            command.add_argument("--record", required=True)
    args = parser.parse_args()
    try:
        root = project_root(args.project)
        if args.command == "init":
            result = initialize(root, args.slug)
        elif args.command == "import":
            result = import_intake(root, Path(args.input).expanduser().resolve())
        elif args.command == "approve":
            result = approve(root, args.stage, args.artifact, args.record)
        else:
            data = read_json(root / "project.json")
            check_input(data)
            missing = missing_fields(data, figma=getattr(args, "figma", False))
            result = {"projectSlug": data["projectSlug"], "intakeRevision": data["intakeRevision"],
                      "ready": not missing, "missing": missing,
                      "pageCount": data["fields"]["delivery.plannedPages"]["value"]}
            if args.command == "validate" and args.ready and missing:
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 2
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
