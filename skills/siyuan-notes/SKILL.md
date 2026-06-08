---
name: siyuan-notes
description: Collect, create, append, and organize notes in SiYuan via the local SiYuan API. Use when the user asks to save research, meeting notes, summaries, tasks, web clips, source material, or structured knowledge into SiYuan; create notebooks, documents, or blocks; tag, classify, move, or tidy existing SiYuan notes; or explicitly invokes `$siyuan-notes`.
---

# SiYuan Notes

Use this skill to collect, create, and organize notes in SiYuan through its local HTTP API.

## Setup

- Default API base URL: `http://127.0.0.1:6806`.
- Read the API token from `SIYUAN_TOKEN`. Do not ask the user to paste secrets into chat unless there is no workable alternative.
- Optional defaults:
  - `SIYUAN_BASE_URL`: override the API base URL.
  - `SIYUAN_NOTEBOOK`: default notebook ID or notebook name.
  - `SIYUAN_INBOX_PATH`: default collection path, such as `/Inbox`.
- Prefer `scripts/siyuan_api.py` for API calls before writing ad hoc HTTP code.
- Read `references/siyuan-api.md` when endpoint names, payloads, or return values are needed.

## Workflow

1. Confirm SiYuan is reachable with `/api/system/version`.
2. Resolve the target notebook. If the user did not specify one, use `SIYUAN_NOTEBOOK`; if there is exactly one open notebook, that is acceptable. Otherwise ask a short question before writing.
3. Normalize collected material into clean Markdown:
   - Preserve source URLs, authors, timestamps, and quoted text attribution.
   - Add a compact summary before long excerpts.
   - Use `#tags` sparingly for retrieval, not every possible keyword.
4. Choose the write pattern:
   - New standalone note: create a document with `/api/filetree/createDocWithMd`.
   - Add to an existing note or daily note: append/prepend/insert blocks under a known parent block.
   - Organizing existing content: prefer move/rename and custom attributes over delete/rewrite.
5. Verify the result by checking the returned document or block ID, human-readable path, exported Markdown, or child blocks.
6. Report the notebook, path, document/block ID, and any unresolved ambiguity.

## Note Shapes

For collected research or web material:

```markdown
# Title

Source: <url>
Captured: YYYY-MM-DD
Tags: #topic #source

## Summary

## Key Points

## Details

## Next Actions
```

For meetings:

```markdown
# Meeting Title

Date: YYYY-MM-DD
Participants:
Tags: #meeting

## Decisions

## Action Items

## Notes
```

For task or project organization:

```markdown
# Project or Topic

Status:
Tags: #project

## Inbox

## Active

## Waiting

## Archive
```

## Organization Rules

- Use human-readable paths such as `/Inbox/YYYY-MM-DD Title`, `/Projects/Project Name/Topic`, or `/References/Domain/Title`.
- Keep titles short enough to scan; put details in the body.
- Use custom attributes for machine-readable metadata. Custom attribute keys must start with `custom-`, for example `custom-source-url`, `custom-topic`, or `custom-status`.
- Before creating a duplicate note, search by human-readable path or SQL query when available.
- If SQL is disabled, fall back to notebook paths and API lookups.

## Safety

- Create and append are safe defaults for note collection.
- Do not delete, overwrite, move large trees, or mass-update blocks unless the user clearly asked for that exact operation.
- Never use SQL for writes. Use SiYuan's documented write endpoints.
- Do not print API tokens, commit them, or include them in saved notes.
- If an API response has `code != 0`, stop and surface the `msg` instead of continuing.

## Commands

Check connection:

```bash
python /path/to/siyuan-notes/scripts/siyuan_api.py version
```

List notebooks:

```bash
python /path/to/siyuan-notes/scripts/siyuan_api.py notebooks
```

Create a document from Markdown:

```bash
python /path/to/siyuan-notes/scripts/siyuan_api.py create-doc --notebook "Notebook Name" --path "/Inbox/2026-06-08 Example" --markdown-file ./note.md
```

Append Markdown to a parent block:

```bash
python /path/to/siyuan-notes/scripts/siyuan_api.py append-block --parent-id "20260101000000-abcdefg" --markdown-file ./note.md
```

Set metadata:

```bash
python /path/to/siyuan-notes/scripts/siyuan_api.py attrs-set --id "20260101000000-abcdefg" --attr custom-source-url=https://example.com --attr custom-status=collected
```

## References

- `references/siyuan-api.md`: concise endpoint and payload reference based on SiYuan `API_zh_CN.md`.
- `scripts/siyuan_api.py`: standard-library CLI wrapper for common SiYuan API operations.
