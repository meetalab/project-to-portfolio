# Project to Portfolio

**Your work. A story worth showing.**

A local student portfolio plugin for Codex and ChatGPT's supported plugin environment. Bring your project notes, images or code; recover the facts, fill the bilingual brief and generate reviewed portfolio spreads using your own account.

Start with:

> Use Project to Portfolio to turn my project into a portfolio. Recover what you can from my files, then ask only what is missing.

The installable plugin lives in [`plugins/project-to-portfolio`](plugins/project-to-portfolio/README.md). Its core uses file/code tools and Python 3.10+, with no API key, npm, backend or intake login. Editable Figma is optional and uses your own separate Figma connection.

## Install from this repository

Register the repository marketplace through the supported Codex CLI, replacing `OWNER` with this repository's GitHub owner:

```sh
codex plugin marketplace add OWNER/project-to-portfolio
```

Then install **Project to Portfolio** from that source in the plugin directory. A public repository can be read without connecting Codex to a GitHub account; private repositories need Git access through your chosen credentials. Repository distribution is separate from approval in the official public plugin directory.

The catalog is at `.agents/plugins/marketplace.json`. Source-based copy, model/effort recommendations and local workflow instructions are in the plugin's skill. Use GPT-6.1 Sol / high for a complete run.

## Verify or rebuild

```sh
python3 -m unittest discover -s tests -v
python3 scripts/build_release.py --output /path/outside/this-repository/release
```

The builder prepares an audited skills-only directory ZIP and a GitHub upload ZIP without authenticating to any account. See [publishing instructions](docs/publishing.md). Generated student files belong outside this repository and are never release material.
