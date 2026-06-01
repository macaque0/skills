#!/usr/bin/env python3
"""Generate employee daily/weekly reports from one or more Git repositories."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


DELIM = "\x1f"
MODULE_CACHE: dict[tuple[str, str], str] = {}
HISTORY_CACHE: dict[tuple[str, str], list[str]] = {}
GREP_CACHE: dict[tuple[str, str], str | None] = {}
README_CACHE: dict[Path, str | None] = {}
CONFIG_CANDIDATES = (
    "git-work-report.json",
    ".git-work-report.json",
    "work-report.json",
    "git-work-report.yaml",
    ".git-work-report.yaml",
    "work-report.yaml",
    "git-work-report.yml",
    ".git-work-report.yml",
    "work-report.yml",
)


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def run_git(repo: Path | None, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = ["git", "-c", "core.quotepath=false", "-c", "i18n.logOutputEncoding=utf-8"]
    if repo is not None:
        cmd.extend(["-C", str(repo)])
    cmd.extend(args)
    env = os.environ.copy()
    env["LC_ALL"] = "C.UTF-8"
    env["LANG"] = "C.UTF-8"
    return subprocess.run(
        cmd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=check,
        env=env,
    )


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        fail(f"config file does not exist: {path}")
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".json":
        return json.loads(text)
    if suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ImportError:
            fail("YAML config requires PyYAML. Use JSON or install PyYAML.")
        return yaml.safe_load(text)
    fail("config must be .json, .yaml, or .yml")


def discover_config(start_dir: Path) -> Path:
    for directory in [start_dir, *start_dir.parents]:
        for name in CONFIG_CANDIDATES:
            candidate = directory / name
            if candidate.exists():
                return candidate.resolve()
    names = ", ".join(CONFIG_CANDIDATES)
    fail(f"no config file found from {start_dir} upward. Create one of: {names}, or pass --config.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Git-based employee work reports.")
    parser.add_argument(
        "--config",
        help="Path to JSON/YAML config. If omitted, searches current directory and parents for default config names.",
    )
    parser.add_argument("--period", choices=["daily", "weekly"], default="weekly")
    parser.add_argument("--format", choices=["markdown", "md", "html", "both"], default="markdown")
    parser.add_argument("--date", help="Anchor date, YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--since", help="Override start datetime/date passed to git log.")
    parser.add_argument("--until", help="Override end datetime/date passed to git log.")
    parser.add_argument(
        "--output",
        help="Markdown output path. If omitted, writes to <config-dir>/git_report/.",
    )
    parser.add_argument("--json-output", help="Optional raw JSON output path. Omit to avoid writing raw JSON.")
    parser.add_argument("--no-fetch", action="store_true", help="Do not fetch remote updates.")
    parser.add_argument("--max-files-per-commit", type=int, default=8)
    return parser.parse_args()


def resolve_period(args: argparse.Namespace) -> tuple[str, str, str]:
    if args.since and args.until:
        return args.period, args.since, args.until
    if args.since or args.until:
        fail("--since and --until must be provided together")

    anchor = date.today()
    if args.date:
        anchor = datetime.strptime(args.date, "%Y-%m-%d").date()

    if args.period == "daily":
        start = anchor
        end = anchor
    else:
        start = anchor - timedelta(days=anchor.weekday())
        end = start + timedelta(days=6)
    return args.period, f"{start.isoformat()} 00:00:00", f"{end.isoformat()} 23:59:59"


def date_part(value: str) -> str:
    match = re.search(r"\d{4}-\d{2}-\d{2}", value)
    if not match:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
        return safe or "unknown-date"
    return match.group(0)


def default_output_path(config_path: Path, period: str, since: str, until: str, extension: str = ".md") -> Path:
    output_dir = config_path.parent / "git_report"
    start = date_part(since)
    end = date_part(until)
    if period == "daily" or start == end:
        filename = f"daily-report-{start}{extension}"
    else:
        filename = f"weekly-report-{start}_{end}{extension}"
    return output_dir / filename


def slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    return cleaned[:60] or "repo"


def repo_cache_path(cache_dir: Path, name: str, url: str) -> Path:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    return cache_dir / f"{slug(name)}-{digest}"


def ensure_repo(repo_cfg: dict[str, Any], cache_dir: Path, no_fetch: bool) -> Path:
    name = repo_cfg.get("name") or repo_cfg.get("url") or repo_cfg.get("path")
    if not name:
        fail("each repository needs a name")

    if repo_cfg.get("path"):
        repo_path = Path(repo_cfg["path"]).expanduser().resolve()
        if not repo_path.exists():
            fail(f"repository path does not exist: {repo_path}")
    else:
        url = repo_cfg.get("url")
        if not url:
            fail(f"repository {name} needs either url or path")
        cache_dir.mkdir(parents=True, exist_ok=True)
        repo_path = repo_cache_path(cache_dir, str(name), str(url))
        if not repo_path.exists():
            print(f"cloning {name} -> {repo_path}", file=sys.stderr)
            run_git(None, ["clone", str(url), str(repo_path)])

    if not no_fetch:
        result = run_git(repo_path, ["fetch", "--all", "--prune"], check=False)
        if result.returncode != 0:
            print(f"warning: fetch failed for {name}: {result.stderr.strip()}", file=sys.stderr)
    return repo_path


def ref_exists(repo: Path, ref: str) -> bool:
    result = run_git(repo, ["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], check=False)
    return result.returncode == 0


def clean_ref_name(ref: str) -> str:
    if ref.startswith("refs/remotes/"):
        return ref.removeprefix("refs/remotes/")
    if ref.startswith("refs/heads/"):
        return ref.removeprefix("refs/heads/")
    return ref


def resolve_refs(repo: Path, branch: str) -> list[str]:
    candidates = [
        branch,
        f"origin/{branch}",
        f"refs/remotes/origin/{branch}",
        f"refs/heads/{branch}",
        f"refs/remotes/{branch}",
    ]
    refs: list[str] = []
    for candidate in candidates:
        if ref_exists(repo, candidate):
            refs.append(clean_ref_name(candidate))
    return sorted(set(refs))


def resolve_ref(repo: Path, branch: str) -> str | None:
    refs = resolve_refs(repo, branch)
    return refs[0] if refs else None


def list_refs(repo: Path, include_local: bool, include_remote: bool) -> list[str]:
    refs: list[str] = []
    if include_local:
        result = run_git(repo, ["for-each-ref", "--format=%(refname:short)", "refs/heads"], check=False)
        if result.returncode == 0:
            refs.extend(line.strip() for line in result.stdout.splitlines() if line.strip())
    if include_remote:
        result = run_git(repo, ["for-each-ref", "--format=%(refname:short)", "refs/remotes"], check=False)
        if result.returncode == 0:
            refs.extend(
                line.strip()
                for line in result.stdout.splitlines()
                if line.strip() and not line.strip().endswith("/HEAD")
            )
    return sorted(set(refs))


def configured_branches(repo: Path, repo_cfg: dict[str, Any]) -> list[str]:
    raw = repo_cfg.get("branches", repo_cfg.get("branch", []))
    if isinstance(raw, str):
        raw = [raw]
    refs: list[str] = []
    for branch in raw:
        resolved = resolve_refs(repo, str(branch))
        if resolved:
            refs.extend(resolved)
        else:
            print(f"warning: branch not found in {repo_cfg.get('name')}: {branch}", file=sys.stderr)
    return sorted(set(refs))


def scan_refs(repo: Path, repo_cfg: dict[str, Any], config: dict[str, Any]) -> tuple[list[str], list[str]]:
    scan = config.get("scan", {})
    mode = scan.get("mode", "mixed")
    include_local = bool(scan.get("include_local_branches", True))
    include_remote = bool(scan.get("include_remote_branches", True))

    base_raw = repo_cfg.get("base_branches") or scan.get("base_branches") or repo_cfg.get("branches") or []
    if isinstance(base_raw, str):
        base_raw = [base_raw]
    base_refs = sorted({ref for branch in base_raw for ref in resolve_refs(repo, str(branch))})

    if mode in {"mixed", "all-branches"}:
        refs = list_refs(repo, include_local, include_remote)
    elif mode == "merged-only":
        refs = base_refs or configured_branches(repo, repo_cfg)
    elif mode == "configured-branches":
        refs = configured_branches(repo, repo_cfg)
    else:
        fail(f"unsupported scan.mode: {mode}")

    return sorted(set(refs)), sorted(set(base_refs))


def commits_for_ref(repo: Path, ref: str, since: str, until: str) -> list[str]:
    result = run_git(repo, ["log", f"--since={since}", f"--until={until}", "--format=%H", ref], check=False)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def show_commit(repo: Path, commit: str) -> dict[str, Any]:
    fmt = f"%H{DELIM}%an{DELIM}%ae{DELIM}%aI{DELIM}%s"
    result = run_git(repo, ["show", "-s", f"--format={fmt}", commit])
    parts = result.stdout.rstrip("\n").split(DELIM)
    if len(parts) != 5:
        fail(f"unexpected git show output for commit {commit}")

    stats = run_git(repo, ["show", "--numstat", "--format=", "--no-renames", commit], check=False)
    additions = 0
    deletions = 0
    files: list[str] = []
    if stats.returncode == 0:
        for line in stats.stdout.splitlines():
            fields = line.split("\t")
            if len(fields) < 3:
                continue
            if fields[0].isdigit():
                additions += int(fields[0])
            if fields[1].isdigit():
                deletions += int(fields[1])
            files.append(fields[2])

    return {
        "hash": parts[0],
        "author_name": parts[1],
        "author_email": parts[2],
        "date": parts[3],
        "subject": parts[4],
        "additions": additions,
        "deletions": deletions,
        "files": files,
    }


def is_ancestor(repo: Path, commit: str, ref: str) -> bool:
    result = run_git(repo, ["merge-base", "--is-ancestor", commit, ref], check=False)
    return result.returncode == 0


def classify(subject: str) -> str:
    text = subject.lower()
    rules = [
        ("问题修复", ["fix", "bug", "hotfix", "修复", "异常", "报错", "问题"]),
        ("功能开发", ["feat", "feature", "新增", "增加", "接入", "实现", "开发"]),
        ("重构优化", ["refactor", "perf", "optimize", "优化", "重构", "调整"]),
        ("测试", ["test", "spec", "测试", "用例"]),
        ("文档", ["docs", "doc", "readme", "文档"]),
        ("工程/运维", ["chore", "ci", "build", "deploy", "release", "构建", "部署", "发布"]),
    ]
    for label, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return label
    return "其他"


def display_author(commit: dict[str, Any], authors: dict[str, str]) -> str:
    email = commit["author_email"].lower()
    name = commit["author_name"]
    return authors.get(email) or authors.get(commit["author_email"]) or authors.get(name) or f"{name} <{commit['author_email']}>"


def collect(config: dict[str, Any], since: str, until: str, no_fetch: bool) -> dict[str, Any]:
    scan = config.get("scan", {})
    cache_dir = Path(config.get("cache_dir", ".git-work-report-cache")).expanduser()
    if not cache_dir.is_absolute():
        cache_dir = Path.cwd() / cache_dir

    authors = {str(k).lower(): str(v) for k, v in config.get("authors", {}).items()}
    authors.update({str(k): str(v) for k, v in config.get("authors", {}).items()})

    all_commits: dict[str, dict[str, Any]] = {}
    repo_summaries: list[dict[str, Any]] = []

    repositories = config.get("repositories") or []
    if not repositories:
        fail("config.repositories is empty")

    for repo_cfg in repositories:
        repo_name = str(repo_cfg.get("name") or repo_cfg.get("url") or repo_cfg.get("path"))
        repo_path = ensure_repo(repo_cfg, cache_dir, no_fetch)
        refs, base_refs = scan_refs(repo_path, repo_cfg, config)
        if not refs:
            print(f"warning: no refs selected for {repo_name}", file=sys.stderr)

        ref_hits: dict[str, set[str]] = defaultdict(set)
        for ref in refs:
            for commit_hash in commits_for_ref(repo_path, ref, since, until):
                ref_hits[commit_hash].add(ref)

        for commit_hash, sources in ref_hits.items():
            key = f"{repo_name}:{commit_hash}"
            commit = show_commit(repo_path, commit_hash)
            merged_refs = [ref for ref in base_refs if is_ancestor(repo_path, commit_hash, ref)]
            commit.update(
                {
                    "repository": repo_name,
                    "repository_path": str(repo_path),
                    "source_refs": sorted(sources),
                    "base_refs": base_refs,
                    "merged_refs": sorted(merged_refs),
                    "merged": bool(merged_refs),
                    "category": classify(commit["subject"]),
                }
            )
            commit["employee"] = display_author(commit, authors)
            all_commits[key] = commit

        repo_summaries.append(
            {
                "name": repo_name,
                "path": str(repo_path),
                "selected_refs": refs,
                "base_refs": base_refs,
                "commits": len(ref_hits),
            }
        )

    return {
        "scan": {
            "mode": scan.get("mode", "mixed"),
            "base_branches": scan.get("base_branches", []),
        },
        "repositories": repo_summaries,
        "commits": sorted(all_commits.values(), key=lambda item: (item["employee"], item["date"], item["repository"])),
    }


def md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def short_hash(value: str) -> str:
    return value[:8]


def format_refs(commit: dict[str, Any]) -> str:
    if commit["merged"]:
        merged_refs = commit.get("merged_refs") or []
        text = f"已合入：{', '.join(merged_refs) if merged_refs else '目标分支'}"
        extra_sources = [ref for ref in commit["source_refs"] if ref not in merged_refs]
        if extra_sources:
            visible = ", ".join(extra_sources[:3])
            if len(extra_sources) > 3:
                visible += f" 等{len(extra_sources)}个分支"
            text += f"；出现于：{visible}"
        return text

    visible = ", ".join(commit["source_refs"][:3])
    if len(commit["source_refs"]) > 3:
        visible += f" 等{len(commit['source_refs'])}个分支"
    return f"来源分支：{visible}"


def format_commit_line(commit: dict[str, Any], max_files: int) -> str:
    stats = f"+{commit['additions']}/-{commit['deletions']}"
    files = commit["files"][:max_files]
    files_text = ""
    if files:
        suffix = "" if len(commit["files"]) <= max_files else f" 等{len(commit['files'])}个文件"
        files_text = f"；文件：{', '.join(files)}{suffix}"
    return (
        f"- [{commit['repository']}] {commit['subject']} "
        f"(`{short_hash(commit['hash'])}`, {commit['date'][:10]}, {stats}, {format_refs(commit)}{files_text})"
    )


def clean_subject(subject: str) -> str:
    text = subject.strip()
    text = re.sub(
        r"^(feat|feature|fix|bugfix|hotfix|refactor|perf|docs?|test|chore|ci|build|release)[\s:：_-]+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    text = re.sub(r"\s*(bug|BUG)\s*$", "", text).strip()
    return text or subject.strip()


def repo_label(repo_name: str, config: dict[str, Any]) -> str:
    labels = config.get("repo_labels", {})
    if repo_name in labels:
        return str(labels[repo_name])

    lowered = repo_name.lower()
    if any(word in lowered for word in ["server", "backend", "api"]):
        return "服务端"
    if "admin" in lowered:
        return "管理后台"
    if "merchant" in lowered:
        return "商家端"
    if any(word in lowered for word in ["uniapp", "mobile", "app"]):
        return "小程序/移动端"
    if any(word in lowered for word in ["web", "front", "frontend"]):
        return "前端"
    return repo_name


def split_words(value: str) -> str:
    value = value.replace("_", " ").replace("-", " ")
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return value.strip()


GENERIC_SUBJECTS = {
    "update",
    "updates",
    "fix",
    "bug",
    "bugfix",
    "修改",
    "调整",
    "优化",
    "提交",
    "处理",
    "代码",
    "修复",
    "修复问题",
    "修复bug",
    "问题修复",
}


def has_cjk(value: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", value))


def is_generic_subject(subject: str) -> bool:
    normalized = re.sub(r"[\s:：_\-]+", "", subject.strip().lower())
    if not normalized or normalized in GENERIC_SUBJECTS:
        return True
    if len(subject.strip()) <= 2:
        return True
    return bool(re.fullmatch(r"(修改|调整|优化|修复|处理)(问题|bug|代码)?", subject.strip(), re.IGNORECASE))


def is_readable_label(value: str) -> bool:
    text = value.strip().strip("#:：- ")
    if not text or is_generic_subject(text):
        return False
    if len(text) > 50:
        return False
    if re.search(r"[\\/{};=]", text):
        return False
    return has_cjk(text) or bool(re.search(r"[A-Za-z]{3,}", text))


def path_tokens(files: list[str]) -> list[str]:
    ignored = {
        "src",
        "main",
        "java",
        "com",
        "pages",
        "packages",
        "components",
        "api",
        "doc",
        "docs",
        "resource",
        "mapper",
        "service",
        "impl",
        "vue",
        "js",
        "ts",
        "java",
        "xml",
        "json",
        "sql",
        "page",
        "pages",
        "index",
        "detail",
        "list",
        "record",
        "prize",
        "rule",
        "mapper",
        "action",
        "resource",
        "controller",
        "service",
    }
    candidates: list[str] = []
    for path in files:
        parts = [part for part in path.replace("\\", "/").strip('"').split("/") if part]
        for part in parts[:-1]:
            stem = Path(part).stem
            if stem.lower() not in ignored and len(stem) > 2:
                candidates.append(stem)
        if parts:
            stem = Path(parts[-1]).stem
            if stem.lower() not in ignored and len(stem) > 2:
                candidates.append(stem)

    ranked = [item for item, _ in Counter(candidates).most_common()]
    return ranked


def best_label(values: list[str]) -> str | None:
    cleaned = [clean_subject(value) for value in values if is_readable_label(clean_subject(value))]
    if not cleaned:
        return None
    cjk = [value for value in cleaned if has_cjk(value)]
    pool = cjk or cleaned
    return Counter(pool).most_common(1)[0][0]


def label_from_config(files: list[str], config: dict[str, Any]) -> str | None:
    labels = config.get("module_labels", {})
    for path in files:
        normalized = path.replace("\\", "/").strip('"')
        for key, label in labels.items():
            if str(key).lower() in normalized.lower():
                return str(label)
    return None


def label_from_history(repo_path: Path, files: list[str]) -> str | None:
    values: list[str] = []
    checked: set[str] = set()
    for file_path in files[:8]:
        normalized = file_path.replace("\\", "/").strip('"')
        candidates = [normalized]
        parent = str(Path(normalized).parent).replace("\\", "/")
        if parent and parent != ".":
            candidates.append(parent)
        for candidate in candidates:
            if candidate in checked:
                continue
            checked.add(candidate)
            cache_key = (str(repo_path), candidate)
            if cache_key not in HISTORY_CACHE:
                result = run_git(
                    repo_path,
                    ["log", "--all", "--max-count=30", "--format=%s", "--", candidate],
                    check=False,
                )
                HISTORY_CACHE[cache_key] = result.stdout.splitlines() if result.returncode == 0 else []
            values.extend(HISTORY_CACHE[cache_key])
    return best_label(values)


def label_from_readme(repo_path: Path, files: list[str]) -> str | None:
    for file_path in files[:8]:
        relative = Path(file_path.replace("\\", "/").strip('"'))
        directories = [relative.parent, *relative.parents]
        for directory in directories:
            if str(directory) == ".":
                continue
            absolute_dir = (repo_path / directory).resolve()
            if repo_path not in [absolute_dir, *absolute_dir.parents]:
                continue
            for name in ["README.md", "readme.md", "README.MD", "README.txt"]:
                readme = absolute_dir / name
                if readme not in README_CACHE:
                    if readme.exists() and readme.is_file():
                        try:
                            text = readme.read_text(encoding="utf-8", errors="ignore")[:12000]
                        except OSError:
                            text = ""
                        heading = None
                        for line in text.splitlines():
                            match = re.match(r"^\s*#{1,3}\s+(.+?)\s*$", line)
                            if match and is_readable_label(match.group(1)):
                                heading = match.group(1).strip()
                                break
                        README_CACHE[readme] = heading
                    else:
                        README_CACHE[readme] = None
                if README_CACHE[readme]:
                    return README_CACHE[readme]
    return None


def label_from_routes(repo_path: Path, files: list[str]) -> str | None:
    tokens = path_tokens(files)[:8]
    route_patterns = ["*.js", "*.ts", "*.vue", "*.json", "*.jsx", "*.tsx"]
    for token in tokens:
        if has_cjk(token) or len(token) < 4:
            continue
        cache_key = (str(repo_path), token)
        if cache_key not in GREP_CACHE:
            result = run_git(
                repo_path,
                ["grep", "-n", "-I", "-C3", token, "--", *route_patterns],
                check=False,
            )
            label = None
            if result.returncode == 0:
                text = "\n".join(result.stdout.splitlines()[:240])
                explicit_values = re.findall(
                    r"(?:title|name|label|menuName|navigationBarTitleText|text)['\"]?\s*[:=]\s*['\"]([^'\"]{2,50})['\"]",
                    text,
                    flags=re.IGNORECASE,
                )
                label = best_label(explicit_values)
                if not label:
                    cjk_values = re.findall(r"[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9（）()·\- ]{1,30}", text)
                    label = best_label(cjk_values)
            GREP_CACHE[cache_key] = label
        if GREP_CACHE[cache_key]:
            return GREP_CACHE[cache_key]
    return None


def label_from_path_names(files: list[str]) -> str | None:
    tokens = path_tokens(files)
    cjk_tokens = [token for token in tokens if has_cjk(token) and is_readable_label(token)]
    if cjk_tokens:
        return cjk_tokens[0]
    if tokens:
        return split_words(tokens[0])
    return None


def module_label_from_context(commit: dict[str, Any], config: dict[str, Any]) -> str:
    files = commit.get("files", [])
    repo_path_raw = commit.get("repository_path")
    repo_path = Path(repo_path_raw) if repo_path_raw else None
    cache_key = (str(repo_path_raw), "|".join(files[:12]))
    if cache_key in MODULE_CACHE:
        return MODULE_CACHE[cache_key]

    label = label_from_config(files, config)
    if not label and repo_path:
        label = label_from_history(repo_path, files)
    if not label and repo_path:
        label = label_from_routes(repo_path, files)
    if not label and repo_path:
        label = label_from_readme(repo_path, files)
    if not label:
        label = label_from_path_names(files)
    if not label:
        label = "相关模块"

    MODULE_CACHE[cache_key] = label
    return label


def commit_theme(commit: dict[str, Any], config: dict[str, Any]) -> str:
    subject = clean_subject(commit["subject"])
    if is_generic_subject(subject):
        return module_label_from_context(commit, config)
    return subject


def build_work_items(items: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for commit in items:
        grouped[commit_theme(commit, config)].append(commit)

    work_items: list[dict[str, Any]] = []
    for theme, commits in grouped.items():
        categories = Counter(commit["category"] for commit in commits)
        merged = sum(1 for commit in commits if commit["merged"])
        status = "已合入" if merged == len(commits) else "尚未合入" if merged == 0 else "部分合入"
        repos = sorted({commit["repository"] for commit in commits})
        repo_labels = sorted({repo_label(repo, config) for repo in repos})
        hashes = ", ".join(short_hash(commit["hash"]) for commit in sorted(commits, key=lambda item: item["date"])[:5])
        subjects = sorted({clean_subject(commit["subject"]) for commit in commits})
        work_items.append(
            {
                "theme": theme,
                "summary": summarize_work(theme, categories, status),
                "status": status,
                "commit_count": len(commits),
                "merged_count": merged,
                "repositories": repos,
                "repo_labels": repo_labels,
                "categories": categories,
                "hashes": hashes,
                "subjects": subjects,
                "commits": commits,
            }
        )

    return sorted(work_items, key=lambda item: (item["status"] != "已合入", -item["commit_count"], item["theme"]))


def starts_with_action(theme: str) -> bool:
    return bool(re.match(r"^(修复|修改|新增|增加|优化|调整|完成|实现|接入|处理|完善|排查)", theme))


def summarize_work(theme: str, categories: Counter[str], status: str) -> str:
    if starts_with_action(theme):
        return theme

    has_feature = categories.get("功能开发", 0) > 0
    has_fix = categories.get("问题修复", 0) > 0
    has_refactor = categories.get("重构优化", 0) > 0
    has_test = categories.get("测试", 0) > 0
    has_docs = categories.get("文档", 0) > 0

    if has_feature and has_fix:
        return f"完成并修复{theme}相关功能"
    if has_feature:
        return f"{'完成' if status == '已合入' else '推进'}{theme}相关功能"
    if has_fix:
        return f"修复{theme}相关问题"
    if has_refactor:
        return f"优化{theme}相关实现"
    if has_test:
        return f"补充{theme}相关测试"
    if has_docs:
        return f"完善{theme}相关文档"
    if "适用范围" in theme or "提示" in theme or "配置" in theme:
        return f"完善{theme}"
    if status == "已合入":
        return f"完成{theme}相关调整"
    if status == "部分合入":
        return f"推进{theme}相关调整，部分内容已合入"
    return f"推进{theme}相关工作"


def format_work_item(item: dict[str, Any]) -> str:
    repos = ", ".join(item["repo_labels"])
    related_commits = f"{item['commit_count']} 个提交：{item['hashes']}"
    return f"| {md_escape(item['summary'])} | {item['status']} | {md_escape(repos)} | {md_escape(related_commits)} |"


def render_markdown(data: dict[str, Any], config: dict[str, Any], period: str, since: str, until: str, max_files: int) -> str:
    title = config.get("report", {}).get("title") or ("研发工作日报" if period == "daily" else "研发工作周报")
    commits = data["commits"]
    by_employee: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for commit in commits:
        by_employee[commit["employee"]].append(commit)

    employee_work_items = {employee: build_work_items(items, config) for employee, items in by_employee.items()}
    all_work_items = [item for items in employee_work_items.values() for item in items]
    merged_work_items = sum(1 for item in all_work_items if item["status"] == "已合入")
    unmerged_work_items = sum(1 for item in all_work_items if item["status"] == "尚未合入")
    partial_work_items = sum(1 for item in all_work_items if item["status"] == "部分合入")
    top_themes = Counter(item["theme"] for item in all_work_items).most_common(5)

    lines: list[str] = [
        f"# {title}",
        "",
        f"- 时间范围：{since} 至 {until}",
        f"- 统计口径：{data['scan']['mode']}",
        f"- 目标分支：{', '.join(map(str, data['scan'].get('base_branches') or [])) or '未配置'}",
        f"- 仓库数量：{len(data['repositories'])}",
        "",
        "## 管理摘要",
        "",
        f"本期共统计 {len(by_employee)} 位员工、{len(commits)} 个提交，归并为 {len(all_work_items)} 个工作事项。其中已合入 {merged_work_items} 项，部分合入 {partial_work_items} 项，尚未合入 {unmerged_work_items} 项。",
    ]

    if top_themes:
        lines.append(f"重点工作集中在：{', '.join(theme for theme, _ in top_themes)}。")
    if unmerged_work_items or partial_work_items:
        lines.append("需关注尚未完全合入目标分支的事项，避免周报中将过程提交误认为已完成交付。")

    lines.extend(
        [
            "",
            "## 员工工作概览",
            "",
            "| 员工 | 工作事项 | 已合入 | 部分合入 | 尚未合入 | 涉及范围 |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for employee in sorted(by_employee):
        items = employee_work_items[employee]
        merged_items = sum(1 for item in items if item["status"] == "已合入")
        partial_items = sum(1 for item in items if item["status"] == "部分合入")
        unmerged_items = sum(1 for item in items if item["status"] == "尚未合入")
        labels = sorted({label for item in items for label in item["repo_labels"]})
        lines.append(
            f"| {md_escape(employee)} | {len(items)} | {merged_items} | {partial_items} | {unmerged_items} | {md_escape(', '.join(labels))} |"
        )

    attention_items = [
        (employee, item)
        for employee, items in employee_work_items.items()
        for item in items
        if item["status"] != "已合入"
    ]
    if attention_items:
        lines.extend(
            [
                "",
                "## 待关注事项",
                "",
                "| 员工 | 工作内容 | 当前状态 | 关联提交 |",
                "| --- | --- | --- | --- |",
            ]
        )
        for employee, item in sorted(attention_items, key=lambda value: (value[0], value[1]["theme"])):
            lines.append(f"| {md_escape(employee)} | {md_escape(item['summary'])} | {item['status']} | {md_escape(item['hashes'])} |")

    lines.extend(
        [
            "",
            "## 员工工作内容",
            "",
        ]
    )

    if not commits:
        lines.extend(["未找到符合条件的提交。"])
        return "\n".join(lines) + "\n"

    for employee in sorted(by_employee):
        items = employee_work_items[employee]
        commits_for_employee = by_employee[employee]
        repos = sorted({commit["repository"] for commit in commits_for_employee})
        merged_commits = sum(1 for commit in commits_for_employee if commit["merged"])
        lines.extend(
            [
                f"### {employee}",
                "",
                f"本期形成 {len(items)} 个工作事项，涉及 {', '.join(repos)}；对应 {len(commits_for_employee)} 个提交，其中 {merged_commits} 个已合入目标分支。",
                "",
                "| 工作内容 | 状态 | 涉及范围 | 关联提交 |",
                "| --- | --- | --- | --- |",
            ]
        )
        for item in items:
            lines.append(format_work_item(item))
        lines.append("")

    lines.extend(
        [
            "## 仓库扫描结果",
            "",
            "| 仓库 | 提交数 | 扫描分支数 | 目标分支 |",
            "| --- | ---: | ---: | --- |",
        ]
    )

    for repo in data["repositories"]:
        lines.append(
            f"| {md_escape(repo['name'])} | {repo['commits']} | {len(repo['selected_refs'])} | {md_escape(', '.join(repo['base_refs']) or '未配置')} |"
        )

    lines.extend(
        [
            "",
            "## 提交明细",
            "",
        ]
    )

    for employee in sorted(by_employee):
        items = sorted(by_employee[employee], key=lambda item: item["date"])
        merged_items = [item for item in items if item["merged"]]
        unmerged_items = [item for item in items if not item["merged"]]
        categories = Counter(item["category"] for item in items)

        lines.extend([f"### {employee}", "", "分类统计："])
        for category, count in categories.most_common():
            lines.append(f"- {category}：{count}")

        lines.extend(["", "已合入目标分支：", ""])
        if merged_items:
            for item in merged_items:
                lines.append(format_commit_line(item, max_files))
        else:
            lines.append("无。")

        lines.extend(["", "尚未合入：", ""])
        if unmerged_items:
            for item in unmerged_items:
                lines.append(format_commit_line(item, max_files))
        else:
            lines.append("无。")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def inline_markdown_to_html(value: str) -> str:
    escaped = html.escape(value)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)


def markdown_table_to_html(lines: list[str]) -> str:
    rows: list[list[str]] = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows.append(cells)

    if len(rows) < 2:
        return ""

    header = rows[0]
    body = rows[2:] if re.fullmatch(r"\s*:?-{3,}:?\s*", rows[1][0] if rows[1] else "") else rows[1:]
    html_lines = ["<div class=\"table-wrap\"><table>", "<thead><tr>"]
    html_lines.extend(f"<th>{inline_markdown_to_html(cell)}</th>" for cell in header)
    html_lines.append("</tr></thead>")
    html_lines.append("<tbody>")
    for row in body:
        html_lines.append("<tr>")
        html_lines.extend(f"<td>{inline_markdown_to_html(cell)}</td>" for cell in row)
        html_lines.append("</tr>")
    html_lines.append("</tbody></table></div>")
    return "\n".join(html_lines)


def markdown_to_html_body(markdown: str) -> str:
    result: list[str] = []
    lines = markdown.splitlines()
    i = 0
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            result.append("</ul>")
            in_list = False

    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            close_list()
            i += 1
            continue

        if line.startswith("|") and "|" in line[1:]:
            close_list()
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            result.append(markdown_table_to_html(table_lines))
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            close_list()
            level = len(heading.group(1))
            result.append(f"<h{level}>{inline_markdown_to_html(heading.group(2))}</h{level}>")
            i += 1
            continue

        if line.startswith("- "):
            if not in_list:
                result.append("<ul>")
                in_list = True
            result.append(f"<li>{inline_markdown_to_html(line[2:])}</li>")
            i += 1
            continue

        close_list()
        result.append(f"<p>{inline_markdown_to_html(line)}</p>")
        i += 1

    close_list()
    return "\n".join(result)


def render_html(markdown: str, title: str) -> str:
    body = markdown_to_html_body(markdown)
    escaped_title = html.escape(title)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_title}</title>
  <style>
    :root {{
      color-scheme: light;
      --text: #1f2937;
      --muted: #6b7280;
      --line: #d7dde8;
      --header: #f4f7fb;
      --accent: #0f766e;
      --accent-soft: #e6f4f1;
      --bg: #ffffff;
    }}
    body {{
      margin: 0;
      background: #eef2f6;
      color: var(--text);
      font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", Arial, sans-serif;
      line-height: 1.65;
    }}
    main {{
      max-width: 1120px;
      margin: 28px auto;
      padding: 36px 42px;
      background: var(--bg);
      box-shadow: 0 12px 34px rgba(15, 23, 42, 0.08);
    }}
    h1 {{
      margin: 0 0 16px;
      font-size: 30px;
      line-height: 1.25;
      color: #111827;
    }}
    h2 {{
      margin: 34px 0 14px;
      padding-bottom: 8px;
      border-bottom: 2px solid var(--accent);
      font-size: 22px;
      color: #111827;
    }}
    h3 {{
      margin: 26px 0 10px;
      font-size: 18px;
      color: #1f2937;
    }}
    p, li {{
      font-size: 14px;
    }}
    ul {{
      margin: 8px 0 18px;
      padding-left: 22px;
    }}
    .table-wrap {{
      width: 100%;
      overflow-x: auto;
      margin: 12px 0 24px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 9px 11px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: var(--header);
      color: #111827;
      font-weight: 600;
      white-space: nowrap;
    }}
    tr:nth-child(even) td {{
      background: #fafbfc;
    }}
    code {{
      padding: 1px 5px;
      border-radius: 4px;
      background: var(--accent-soft);
      color: #0f5f59;
      font-family: Consolas, "SFMono-Regular", monospace;
      font-size: 0.92em;
    }}
    @media print {{
      body {{
        background: white;
      }}
      main {{
        margin: 0;
        padding: 18mm;
        box-shadow: none;
      }}
    }}
  </style>
</head>
<body>
  <main>
{body}
  </main>
</body>
</html>
"""


def resolve_output_paths(args: argparse.Namespace, config_path: Path, period: str, since: str, until: str) -> tuple[Path | None, Path | None]:
    output_format = "markdown" if args.format == "md" else args.format

    if args.output:
        explicit = Path(args.output).expanduser().resolve()
        if output_format == "markdown":
            return explicit, None
        if output_format == "html":
            return None, explicit
        return explicit.with_suffix(".md"), explicit.with_suffix(".html")

    md_path = default_output_path(config_path, period, since, until, ".md").resolve()
    html_path = default_output_path(config_path, period, since, until, ".html").resolve()
    if output_format == "markdown":
        return md_path, None
    if output_format == "html":
        return None, html_path
    return md_path, html_path


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).expanduser().resolve() if args.config else discover_config(Path.cwd().resolve())
    print(f"using config {config_path}", file=sys.stderr)
    config = load_config(config_path)
    period, since, until = resolve_period(args)
    data = collect(config, since, until, args.no_fetch)
    markdown = render_markdown(data, config, period, since, until, args.max_files_per_commit)
    report_title = config.get("report", {}).get("title") or ("研发工作日报" if period == "daily" else "研发工作周报")
    md_path, html_path = resolve_output_paths(args, config_path, period, since, until)

    if md_path:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(markdown, encoding="utf-8")
        print(f"wrote {md_path}")

    if html_path:
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(render_html(markdown, report_title), encoding="utf-8")
        print(f"wrote {html_path}")

    if args.json_output:
        json_path = Path(args.json_output).expanduser().resolve()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"period": {"type": period, "since": since, "until": until}, **data}
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
