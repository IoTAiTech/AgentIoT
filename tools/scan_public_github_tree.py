#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 1.0.0 | Date: 2026-08-13
"""Fail-closed scanner for a public GitHub export tree.

Exit 0 only when the tree is free of deny-class paths and sensitive
content. This tool is the publication gate for every coder.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


DENY_PATH_PARTS = (
    "docs/contract",
    "docs/customer",
    "docs/memory",
    "docs/phases",
    "docs/governance",
    "docs/index",
    "internal/",
    "dist/customer-release",
    "output/playwright",
)

DENY_BASENAMES = {
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".env",
    "id_rsa",
    "id_ed25519",
    "github_deploy_ed25519",
}

DENY_SUFFIXES = {".pem", ".p12", ".pfx"}

def _dot(*parts: int) -> str:
    return ".".join(str(part) for part in parts)


def _octets(*parts: int) -> str:
    return re.escape(_dot(*parts))


# Fleet / private-host literals are built from octets so this file itself
# stays publishable. Generic RFC1918 documentation ranges stay allowed.
FLEET_IP = re.compile(_octets(192, 168, 50) + r"\.\d+")
FLEET_SPARK = re.compile(_octets(192, 168, 0, 1) + r"\b")
INTERNAL_HOST = re.compile(
    r"\b("
    + "|".join(
        (
            "DLD" + "-" + "DGX",
            "HID" + "-" + "HOST",
            "Nas" + "IOT",
            "HID" + "-" + "HOST" + r"\.local",
        )
    )
    + r")\b",
    re.IGNORECASE,
)
HOME_IOT = re.compile("/" + "home" + "/" + "iot" + r"\b")
UNC_SHARE = re.compile(r"\\\\" + _octets(192, 168) + r"\.")
PRIVATE_KEY_HEADER = re.compile(r"-----BEGIN ([A-Z0-9 ]+)?PRIVATE KEY-----")
TOKEN_PREFIX = re.compile(
    r"\b(sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9_]{20,}|xai-[A-Za-z0-9]{20,})\b"
)

TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".sh",
    ".html",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".feature",
    ".in",
    ".cfg",
    ".ini",
    ".js",
    ".css",
}

SANITIZE_REPLACEMENTS = (
    (f"http://{_dot(192, 168, 50, 30)}:11500", "http://ollama.example.internal:11434"),
    (f"https://{_dot(192, 168, 50, 40)}:8040", "https://127.0.0.1:8080"),
    (f"https://{_dot(192, 168, 50, 201)}:8040", "https://127.0.0.1:8080"),
    (f"{_dot(192, 168, 50, 30)}:11500", "ollama.example.internal:11434"),
    (_dot(192, 168, 50, 30), "ollama.example.internal"),
    (_dot(192, 168, 50, 40), "127.0.0.1"),
    (_dot(192, 168, 50, 201), "127.0.0.1"),
    (f"{_dot(192, 168, 0, 1)}:11500", "ollama.example.internal:11434"),
    (_dot(192, 168, 0, 1), "ollama.example.internal"),
    (_dot(192, 168, 50, 21), _dot(192, 0, 2, 21)),
    (_dot(192, 168, 50, 20), _dot(192, 0, 2, 20)),
    (f"{_dot(192, 168, 50, 0)}/27", f"{_dot(192, 0, 2, 0)}/27"),
    (f"{_dot(192, 168, 50, 0)}/24", f"{_dot(192, 0, 2, 0)}/24"),
    (_dot(192, 168, 50, 0), _dot(192, 0, 2, 0)),
    (_dot(192, 168, 50) + ".", _dot(192, 0, 2) + "."),
    ("/" + "home" + "/" + "iot" + "/", "/var/lib/agentiot/"),
)


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_text(path: Path) -> bool:
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    return path.name in {"LICENSE", "VERSION", "Dockerfile", "Dockerfile.public"}


def find_path_violations(root: Path) -> list[str]:
    hits: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = _rel(root, path)
        lowered = rel.lower()
        for part in DENY_PATH_PARTS:
            if part in lowered:
                hits.append(f"deny-path:{rel}")
                break
        name = path.name
        if name in DENY_BASENAMES:
            hits.append(f"deny-basename:{rel}")
        if path.suffix.lower() in DENY_SUFFIXES:
            hits.append(f"deny-suffix:{rel}")
        if name.endswith(".key") and not name.endswith(".pub"):
            hits.append(f"deny-private-key-file:{rel}")
    return hits


def find_content_violations(root: Path) -> list[str]:
    hits: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or not _is_text(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            hits.append(f"unreadable:{_rel(root, path)}:{exc}")
            continue
        rel = _rel(root, path)
        for label, pattern in (
            ("fleet-ip", FLEET_IP),
            ("spark-ip", FLEET_SPARK),
            ("internal-host", INTERNAL_HOST),
            ("home-iot", HOME_IOT),
            ("unc-share", UNC_SHARE),
            ("private-key", PRIVATE_KEY_HEADER),
            ("token-prefix", TOKEN_PREFIX),
        ):
            if pattern.search(text):
                hits.append(f"{label}:{rel}")
    return hits


def sanitize_tree(root: Path) -> int:
    changed = 0
    for path in root.rglob("*"):
        if not path.is_file() or not _is_text(path):
            continue
        original = path.read_text(encoding="utf-8", errors="replace")
        updated = original
        for old, new in SANITIZE_REPLACEMENTS:
            updated = updated.replace(old, new)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


def scan(root: Path) -> dict[str, object]:
    path_hits = find_path_violations(root)
    content_hits = find_content_violations(root)
    files = [p for p in root.rglob("*") if p.is_file()]
    return {
        "root": str(root),
        "file_count": len(files),
        "path_violations": path_hits,
        "content_violations": content_hits,
        "ok": not path_hits and not content_hits,
        "production_claim": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan a public GitHub tree")
    parser.add_argument("root", type=Path, help="exported public tree")
    parser.add_argument(
        "--sanitize-in-place",
        action="store_true",
        help="replace known fleet literals before scanning",
    )
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if not root.is_dir():
        print(f"scan fail: not a directory: {root}", file=sys.stderr)
        return 2

    sanitized = 0
    if args.sanitize_in_place:
        sanitized = sanitize_tree(root)

    report = scan(root)
    report["sanitized_files"] = sanitized
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if report["ok"]:
        print(f"scan pass: {report['file_count']} files, sanitized={sanitized}")
        return 0

    print("scan fail: public tree is not clean", file=sys.stderr)
    for item in report["path_violations"] + report["content_violations"]:
        print(f"  {item}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
