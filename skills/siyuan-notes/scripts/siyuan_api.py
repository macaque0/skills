#!/usr/bin/env python3
"""Small CLI wrapper for common SiYuan API operations."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:6806"


def post_json(base_url: str, endpoint: str, payload: dict[str, Any] | None = None) -> Any:
    token = os.environ.get("SIYUAN_TOKEN", "")
    endpoint = endpoint if endpoint.startswith("/") else "/" + endpoint
    url = base_url.rstrip("/") + endpoint

    data = b"" if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Token {token}"

    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        message = raw.decode("utf-8", errors="replace") if raw else str(exc)
        raise RuntimeError(f"HTTP {exc.code} {endpoint}: {message}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach SiYuan at {base_url}: {exc}") from exc

    text = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"code": 0, "msg": "", "data": text}


def print_result(result: Any) -> int:
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if isinstance(result, dict) and result.get("code", 0) != 0:
        return 1
    return 0


def read_markdown(args: argparse.Namespace) -> str:
    if getattr(args, "markdown_file", None):
        return Path(args.markdown_file).read_text(encoding="utf-8")
    if getattr(args, "markdown", None) is not None:
        return args.markdown
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("Provide --markdown-file, --markdown, or pipe Markdown on stdin.")


def load_data_arg(args: argparse.Namespace) -> dict[str, Any] | None:
    if args.data_file:
        return json.loads(Path(args.data_file).read_text(encoding="utf-8"))
    if args.data_json:
        return json.loads(args.data_json)
    return None


def notebook_id(base_url: str, notebook: str | None) -> str:
    ref = notebook or os.environ.get("SIYUAN_NOTEBOOK")
    result = post_json(base_url, "/api/notebook/lsNotebooks")
    if isinstance(result, dict) and result.get("code", 0) != 0:
        raise SystemExit(json.dumps(result, ensure_ascii=False, indent=2))

    notebooks = ((result or {}).get("data") or {}).get("notebooks") or []
    if ref:
        matches = [item for item in notebooks if item.get("id") == ref or item.get("name") == ref]
        if len(matches) == 1:
            return matches[0]["id"]
        raise SystemExit(f"Notebook not found or ambiguous: {ref}")

    open_notebooks = [item for item in notebooks if not item.get("closed")]
    if len(open_notebooks) == 1:
        return open_notebooks[0]["id"]

    names = ", ".join(item.get("name", item.get("id", "")) for item in open_notebooks)
    raise SystemExit(f"Notebook is required. Open notebooks: {names or '(none)'}")


def parse_attrs(items: list[str]) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"Attribute must be KEY=VALUE: {item}")
        key, value = item.split("=", 1)
        if not key.startswith("custom-"):
            raise SystemExit(f"Custom attribute key must start with custom-: {key}")
        attrs[key] = value
    return attrs


def cmd_version(args: argparse.Namespace) -> int:
    return print_result(post_json(args.base_url, "/api/system/version"))


def cmd_notebooks(args: argparse.Namespace) -> int:
    return print_result(post_json(args.base_url, "/api/notebook/lsNotebooks"))


def cmd_call(args: argparse.Namespace) -> int:
    return print_result(post_json(args.base_url, args.endpoint, load_data_arg(args)))


def cmd_create_notebook(args: argparse.Namespace) -> int:
    return print_result(post_json(args.base_url, "/api/notebook/createNotebook", {"name": args.name}))


def cmd_create_doc(args: argparse.Namespace) -> int:
    path = args.path if args.path.startswith("/") else "/" + args.path
    payload = {
        "notebook": notebook_id(args.base_url, args.notebook),
        "path": path,
        "markdown": read_markdown(args),
    }
    return print_result(post_json(args.base_url, "/api/filetree/createDocWithMd", payload))


def cmd_block(args: argparse.Namespace, endpoint: str, extra: dict[str, Any]) -> int:
    payload = {"dataType": args.data_type, "data": read_markdown(args)}
    payload.update(extra)
    return print_result(post_json(args.base_url, endpoint, payload))


def cmd_append_block(args: argparse.Namespace) -> int:
    return cmd_block(args, "/api/block/appendBlock", {"parentID": args.parent_id})


def cmd_prepend_block(args: argparse.Namespace) -> int:
    return cmd_block(args, "/api/block/prependBlock", {"parentID": args.parent_id})


def cmd_insert_block(args: argparse.Namespace) -> int:
    payload = {
        "nextID": args.next_id or "",
        "previousID": args.previous_id or "",
        "parentID": args.parent_id or "",
    }
    if not any(payload.values()):
        raise SystemExit("At least one of --next-id, --previous-id, or --parent-id is required.")
    return cmd_block(args, "/api/block/insertBlock", payload)


def cmd_query(args: argparse.Namespace) -> int:
    return print_result(post_json(args.base_url, "/api/query/sql", {"stmt": args.stmt}))


def cmd_export_md(args: argparse.Namespace) -> int:
    return print_result(post_json(args.base_url, "/api/export/exportMdContent", {"id": args.id}))


def cmd_attrs_get(args: argparse.Namespace) -> int:
    return print_result(post_json(args.base_url, "/api/attr/getBlockAttrs", {"id": args.id}))


def cmd_attrs_set(args: argparse.Namespace) -> int:
    return print_result(post_json(args.base_url, "/api/attr/setBlockAttrs", {"id": args.id, "attrs": parse_attrs(args.attr)}))


def cmd_notify(args: argparse.Namespace) -> int:
    endpoint = "/api/notification/pushErrMsg" if args.error else "/api/notification/pushMsg"
    return print_result(post_json(args.base_url, endpoint, {"msg": args.message, "timeout": args.timeout}))


def add_markdown_args(parser: argparse.ArgumentParser) -> None:
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--markdown-file", help="UTF-8 Markdown file to send.")
    source.add_argument("--markdown", help="Markdown text to send.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Call common SiYuan local API endpoints.")
    parser.add_argument("--base-url", default=os.environ.get("SIYUAN_BASE_URL", DEFAULT_BASE_URL))
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("version").set_defaults(func=cmd_version)
    subparsers.add_parser("notebooks").set_defaults(func=cmd_notebooks)

    call = subparsers.add_parser("call", help="Call any JSON SiYuan endpoint.")
    call.add_argument("endpoint")
    call.add_argument("--data-json")
    call.add_argument("--data-file")
    call.set_defaults(func=cmd_call)

    create_notebook = subparsers.add_parser("create-notebook")
    create_notebook.add_argument("--name", required=True)
    create_notebook.set_defaults(func=cmd_create_notebook)

    create_doc = subparsers.add_parser("create-doc")
    create_doc.add_argument("--notebook")
    create_doc.add_argument("--path", default=os.environ.get("SIYUAN_INBOX_PATH", "/Inbox") + "/Untitled")
    add_markdown_args(create_doc)
    create_doc.set_defaults(func=cmd_create_doc)

    for name, func in [("append-block", cmd_append_block), ("prepend-block", cmd_prepend_block)]:
        block = subparsers.add_parser(name)
        block.add_argument("--parent-id", required=True)
        block.add_argument("--data-type", choices=["markdown", "dom"], default="markdown")
        add_markdown_args(block)
        block.set_defaults(func=func)

    insert = subparsers.add_parser("insert-block")
    insert.add_argument("--next-id")
    insert.add_argument("--previous-id")
    insert.add_argument("--parent-id")
    insert.add_argument("--data-type", choices=["markdown", "dom"], default="markdown")
    add_markdown_args(insert)
    insert.set_defaults(func=cmd_insert_block)

    query = subparsers.add_parser("query")
    query.add_argument("--stmt", required=True)
    query.set_defaults(func=cmd_query)

    export_md = subparsers.add_parser("export-md")
    export_md.add_argument("--id", required=True)
    export_md.set_defaults(func=cmd_export_md)

    attrs_get = subparsers.add_parser("attrs-get")
    attrs_get.add_argument("--id", required=True)
    attrs_get.set_defaults(func=cmd_attrs_get)

    attrs_set = subparsers.add_parser("attrs-set")
    attrs_set.add_argument("--id", required=True)
    attrs_set.add_argument("--attr", action="append", required=True, help="Repeatable KEY=VALUE. Key must start with custom-.")
    attrs_set.set_defaults(func=cmd_attrs_set)

    notify = subparsers.add_parser("notify")
    notify.add_argument("--message", required=True)
    notify.add_argument("--timeout", type=int, default=7000)
    notify.add_argument("--error", action="store_true")
    notify.set_defaults(func=cmd_notify)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
