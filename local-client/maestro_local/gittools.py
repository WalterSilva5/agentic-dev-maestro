"""Cockpit de Git/PR: lê estado do repositório (branch, mudanças, commits) e,
se o `gh` estiver disponível, lista PRs. Somente leitura."""
from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger("maestro.gittools")


def _git(path: str, *args: str, timeout: int = 20) -> tuple[int, str, str]:
    try:
        out = subprocess.run(
            ["git", "-C", path, "--no-pager", *args],
            capture_output=True, text=True, timeout=timeout,
        )
    except FileNotFoundError:
        raise RuntimeError("git não encontrado no PATH")
    except subprocess.TimeoutExpired:
        raise RuntimeError("git excedeu o tempo limite")
    return out.returncode, out.stdout, out.stderr


def git_status(path: str) -> dict:
    """Estado do repositório: branch, ahead/behind, arquivos alterados e commits."""
    rc, _, err = _git(path, "rev-parse", "--is-inside-work-tree")
    if rc != 0:
        raise RuntimeError((err or "não é um repositório git").strip())

    branch = _git(path, "rev-parse", "--abbrev-ref", "HEAD")[1].strip()

    ahead = behind = 0
    rc, out, _ = _git(path, "rev-list", "--left-right", "--count", "@{upstream}...HEAD")
    if rc == 0 and out.strip():
        parts = out.split()
        if len(parts) == 2:
            behind, ahead = int(parts[0]), int(parts[1])

    staged, unstaged, untracked = [], [], []
    rc, out, _ = _git(path, "status", "--porcelain")
    if rc == 0:
        for line in out.splitlines():
            if not line:
                continue
            x, y, name = line[0], line[1], line[3:]
            if x == "?" and y == "?":
                untracked.append(name)
                continue
            if x != " ":
                staged.append(f"{x} {name}")
            if y != " ":
                unstaged.append(f"{y} {name}")

    commits = []
    rc, out, _ = _git(path, "log", "-15", "--pretty=format:%h\x1f%s\x1f%an\x1f%ar")
    if rc == 0:
        for line in out.splitlines():
            f = line.split("\x1f")
            if len(f) == 4:
                commits.append({"hash": f[0], "subject": f[1], "author": f[2], "when": f[3]})

    return {
        "branch": branch,
        "ahead": ahead,
        "behind": behind,
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
        "commits": commits,
        "clean": not (staged or unstaged or untracked),
    }


def gh_prs(path: str) -> list:
    """Lista PRs abertos via `gh` (best-effort; vazio se indisponível)."""
    import json
    try:
        out = subprocess.run(
            ["gh", "pr", "list", "--json", "number,title,headRefName,state,url", "--limit", "20"],
            capture_output=True, text=True, timeout=20, cwd=path,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if out.returncode != 0:
        return []
    try:
        data = json.loads(out.stdout or "[]")
    except json.JSONDecodeError:
        return []
    return [
        {"number": p.get("number"), "title": p.get("title"),
         "branch": p.get("headRefName"), "state": p.get("state"), "url": p.get("url")}
        for p in data
    ]
