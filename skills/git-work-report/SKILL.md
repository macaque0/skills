---
name: git-work-report
description: Generate employee daily or weekly work reports from Git commits across one or more repositories. Use only when the user explicitly invokes `$git-work-report` or explicitly says to use `git-work-report`; do not invoke implicitly for ordinary Git questions, reporting questions, or repository analysis.
---

# Git Work Report

Use this skill only after explicit invocation. It generates merged employee daily or weekly reports from Git commit history across one or more repositories.

## Workflow

1. Locate or create a config file. Prefer a user-provided JSON/YAML config. If none exists, look for a default config in the current directory or its parents.
2. Run `scripts/generate_git_report.py` with the period. Omit `--output` by default so Markdown is written to `<config-dir>/git_report/`. Pass `--config` only when the config is outside the default search path.
3. Review the generated Markdown. The default output is management-facing: work items first, commit details later as related commit records. If polishing the text, rewrite only from generated facts; do not invent work not present in Git data.
4. Clearly state the scan mode, time range, target/base branches, and whether unmerged branch work is included.

## Scan Modes

Use `mixed` by default for employee daily/weekly reports:

- `mixed`: scan all local and remote branches, dedupe commits by hash, and split results into "merged to base branches" and "not yet merged".
- `merged-only`: scan only configured/base branches. Use this for official release or archive reports.
- `all-branches`: scan all local and remote branches and report branch sources without treating base-branch merge status as the main grouping.
- `configured-branches`: scan only each repository's configured `branches`.

For `mixed`, configure `scan.base_branches`, usually `develop`, `main`, or both. A commit is treated as merged when it is an ancestor of at least one resolved base branch.

## Config

Use `references/config.example.json` as the starting point.

For routine use, copy it to one of these default names in the project or reporting directory:

- `git-work-report.json`
- `.git-work-report.json`
- `work-report.json`
- the same names with `.yaml` or `.yml`

When `--config` is omitted, the script searches the current directory and then each parent directory for those names.

When `--output` is omitted, reports are written to a `git_report` folder next to the resolved config file. Markdown is the default format. Raw JSON is not written unless `--json-output` is explicitly provided.

Important fields:

- `repositories`: list of repositories. Each item needs `name` plus either `url` or `path`.
- `repositories[].branches`: branches to scan in `configured-branches` mode.
- `scan.mode`: one of `mixed`, `merged-only`, `all-branches`, or `configured-branches`.
- `scan.base_branches`: branches used to determine whether work has landed in the target line.
- `authors`: map Git emails or Git author names to employee display names.
- `repo_labels`: optional map from repository names to business-facing scopes such as service, admin console, or mobile app.
- `cache_dir`: where cloned repositories should be stored.

Module names are inferred automatically. Prefer commit messages as the source of work content; use paths only as a fallback, then recent commit history, README files, and route/menu metadata when available.

Private repositories rely on the user's local Git credentials, SSH keys, or token helpers. Do not ask for secrets in chat.

## Commands

Generate a weekly Markdown report:

```bash
python /path/to/git-work-report/scripts/generate_git_report.py --period weekly
```

Generate a weekly HTML report:

```bash
python /path/to/git-work-report/scripts/generate_git_report.py --period weekly --format html
```

Generate Markdown and HTML together:

```bash
python /path/to/git-work-report/scripts/generate_git_report.py --period weekly --format both
```

Generate a daily report for a specific date:

```bash
python /path/to/git-work-report/scripts/generate_git_report.py --period daily --date 2026-05-27
```

Use an explicit config path when the config lives elsewhere. The default Markdown output still goes to that config file's sibling `git_report` folder:

```bash
python /path/to/git-work-report/scripts/generate_git_report.py --config D:/reports/git-work-report.json --period weekly
```

Only generate raw JSON when the user asks for structured data:

```bash
python /path/to/git-work-report/scripts/generate_git_report.py --period weekly --json-output ./git_report/weekly-report.raw.json
```

Use `--no-fetch` only when the user explicitly wants to avoid network updates and accepts stale local refs.

## Reporting Rules

- Never claim unmerged branch commits are completed or released work. Put them under "not yet merged".
- Present management-facing work items before raw commit details.
- Deduplicate commits by full hash across branches and repositories.
- Preserve repository and branch provenance for each item.
- If an employee used multiple Git emails, require or create an `authors` mapping.
- If there are no commits for a person or period, report that no matching commits were found instead of fabricating work.
- Treat Git data as a record of code activity, not a complete record of meetings, reviews, design, or offline investigation.

## References

- `references/config.example.json`: multi-repository configuration example.
- `references/author-map.example.json`: standalone author mapping example.
- `references/report-template.md`: Markdown report shape to follow when polishing output.
