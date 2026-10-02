# Publish Project to Portfolio

## GitHub through your browser

1. Create a repository named `project-to-portfolio` while signed into GitHub's website.
2. Extract the GitHub ZIP. Open its `project-to-portfolio` folder.
3. Use **Add file → Upload files** and upload that folder's contents into the repository root, preserving nested paths. Show hidden files in Finder with Command–Shift–Period so `.agents` and `.gitignore` are included.
4. Commit the files and inspect the root. It must contain `.agents/plugins/marketplace.json` and `plugins/project-to-portfolio/.codex-plugin/plugin.json`.
5. Open the README and confirm the install instructions. Your repository can be private for storage or public for public distribution.

The prepared repository fits GitHub's single-upload limit of 100 files and 25 MiB per file. Upload extracted files for a repository install; uploading only the ZIP creates a downloadable archive. Your browser login is sufficient. Codex does not need a GitHub connection.

Reference: [GitHub browser upload](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository).

## Codex / ChatGPT public plugin directory

1. Open the plugin submission portal and choose the verified publisher identity that will own the listing.
2. Select the **Skills only** path and upload the directory ZIP. It contains one plugin root, valid skill frontmatter, local helpers and icons; it contains no MCP server configuration, app references, hooks, custom-UI screenshots or student data.
3. Inspect automated metadata/skill checks, resolve any actual findings and upload the corrected version when needed.
4. Complete requested listing details and submit for review. Publish only after approval when you choose to make it available.

The package uses `Project to Portfolio` as its author/developer label. If your verified publisher identity uses a different public name, update those two manifest values to match that chosen identity before submission. No unverified publisher name or repository URL has been invented. The portal may request additional details; local checks cannot promise portal acceptance or review approval.

This is a skills-only listing. Optional Figma uses the student's separate Figma tools; it is not a plugin-owned remote MCP connection. No backend or hosted privacy/terms pages are required for the local execution itself. If submission requests public listing/contact information, provide your chosen publisher details there rather than adding a personal-site dependency to the plugin.

Reference: [OpenAI submission guide](https://developers.openai.com/plugins/deploy/submission), [skills-only package checks](https://developers.openai.com/plugins/deploy/submission-errors), [repository marketplaces](https://developers.openai.com/plugins/build/plugins).
