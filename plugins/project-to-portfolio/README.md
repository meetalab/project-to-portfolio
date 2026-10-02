# Project to Portfolio

**Your work. A story worth showing.**

Turn one art, design or creative technology project into a portfolio that shows what you made, why it matters and how your decisions shaped it.

Install the plugin in Codex or ChatGPT's supported plugin environment, use your own account, and start with:

> Use Project to Portfolio to turn my project into a portfolio. Recover what you can from my files, then ask only what is missing.

Answer in chat or use the offline bilingual form. Your assistant handles workspace setup, imports the form export and generates the files. You do not need an API key, a student login, an access code, npm or a hosted service.

The core workflow uses the host's file/code tools and Python 3.10+. If those tools are unavailable, the skill can collect your brief and draft copy in chat; file generation requires an environment with artifact/file tools. “Local” means project files and the form are local to your selected workspace; your conversation and supplied materials are still processed by the Codex/ChatGPT account you choose.

## What you get

- A thirty-field EN/CN brief that reuses information already in your files.
- Clear, source-based English portfolio copy and project-specific visual direction.
- A bilingual wireframe/style review before the final design.
- Five combined 5120 × 1600 HTML spreads by default, with one shared adjustable count.
- Exact text and replaceable-image records in a portable native scene file.
- Optional native editable Figma through your own connected Figma tools.

The sequence is brief → copy/direction → page review → one HTML sample → complete batch → optional Figma. Your project facts remain distinct from suggestions and AI-generated illustrations. Figma is optional; this package does not install its separate connector.

Use **GPT-6.1 Sol / high** for a complete run. The skill explicitly assigns **GPT-6 Luna / medium** to intake and focused checks, and **GPT-6.1 Sol / high** to copy, design and conversion. These are recommended settings; the host and your model choice control what actually runs.

Generated files belong in your project workspace, not the installed plugin folder. The offline form makes no network requests; save/export its JSON before closing the browser tab. No project answers or generated work are uploaded to a publisher-controlled service.

## Optional helper commands

The assistant normally runs these for you. Resolve `<skill>` to the installed `skills/project-to-portfolio` directory:

```sh
python3 <skill>/scripts/project.py init --project <your-workspace> --slug my-project
python3 <skill>/scripts/project.py import --project <your-workspace> --input intake.json
python3 <skill>/scripts/project.py validate --project <your-workspace> --ready
```

The directory package contains skills and portable Python helpers, with no MCP server, lifecycle hook, backend or student data. GitHub distribution includes a repository marketplace catalog. Directory listing still requires the publisher's own identity verification and OpenAI's submission checks; a locally validated ZIP is not an approved or published listing.
