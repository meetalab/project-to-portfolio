# Project intake

`assets/questions.json` holds the thirty bilingual questions. Read that schema rather than repeating a long questionnaire from memory. Recover supplied facts first; application details may be TBD when the student authorizes that choice. Do not block an ordinary HTML portfolio on a missing Figma destination.

Resolve `<skill>` to this loaded skill's directory and `<project>` to a selected workspace folder. Use the host's Python runtime.

```sh
python3 <skill>/scripts/project.py init --project <project> --slug my-project
python3 <skill>/scripts/project.py status --project <project>
python3 <skill>/scripts/project.py import --project <project> --input selected-intake.json
python3 <skill>/scripts/project.py validate --project <project> --ready
```

The first command creates `project.json` and a working `intake.html`. It refuses to replace an existing project. All helper writes stay within the selected project. The form runs without a server or network requests. Its browser-tab save is a convenience, not durable backup: export JSON before closing the tab or moving to another browser. The host reads only the export the student selects.

For chat intake, write a small selected-input JSON file, then import it. Only listed fields change; unknown IDs, invalid states/types and malformed files are rejected before any write. Every changed import saves the previous project snapshot. A partial import never empties unrelated answers.

```json
{
  "schemaVersion": 1,
  "projectSlug": "my-project",
  "fields": {
    "project.name": {"state": "confirmed", "value": "Working title chosen by the student", "notes": ""},
    "ai.used": {"state": "confirmed", "value": "No", "notes": "No AI/ML in the original project."}
  }
}
```

States are `confirmed`, `pending official verification`, `user-authorized TBD`, `N/A` and `unresolved`. A confirmed value must be nonempty and match its field type. `N/A` is permitted only on fields marked `allowNA`. Explicit TBD preserves uncertainty; do not turn it into a claimed fact. Official verification applies to changeable external claims and requires the original source, not a guessed citation.

`ai.used` distinguishes all AI/ML, including pretrained computer vision, from only generative AI. Its four follow-ups are required only for a confirmed Yes. A confirmed No retains previous follow-up data but excludes it from readiness and portfolio claims. The shared page count defaults to five. Figma URL is a conversion-time field; `validate --ready --figma` checks it only for that requested output.

Approvals are separate from intake. Bind the stage to the exact artifact the student saw:

```sh
python3 <skill>/scripts/project.py approve --project <project> \
  --stage plan --artifact review-v1.html --record "Exact student authorization"
```

Stages are `plan`, `sample`, `batch` and `source-conversion`. Use only real student authorization. The helper records a timestamp and file/directory hash; it cannot know whether the student actually approved. Keep old versions; new authorization belongs to new artifacts.
