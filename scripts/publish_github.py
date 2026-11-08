# -*- coding: utf-8 -*-
"""可选：用 GITHUB_TOKEN 创建 GitHub 仓库并推送当前目录（一次性发布脚本）。

适用场景：别的电脑上没有 WorkBuddy 的 GitHub 连接器，也不想装 gh CLI。
本仓库首次发布是通过连接器完成的；这个脚本只是把同样的流程做成可复现的命令行版本。

用法：
    export GITHUB_TOKEN=ghp_xxx                 # Windows: set GITHUB_TOKEN=ghp_xxx
    export GITHUB_REPO=douyin-video-to-transcript   # 可选
    export GITHUB_PRIVATE=0                        # 可选，1 = 私有仓库
    python scripts/publish_github.py

安全约定：
    * token 只从环境变量读，不写入任何文件、不打印、不写进 git remote；
    * 带 token 的 URL 仅出现在这一个 git 子进程里，用完即弃；
    * 所有异常信息都先做脱敏再输出；
    * 最小权限：经典 PAT 的 `repo`，或细粒度 PAT 的 Contents/Administration 写权限。
    * 发布完成后建议在 GitHub 设置里撤销该 token。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.github.com"
DEFAULT_REPO = "douyin-video-to-transcript"
DESCRIPTION = ("Fetch a Douyin creator's public posts, transcribe speech locally with "
               "faster-whisper, and merge into a chronological Markdown transcript. No hosted service.")


def redact(text: str, token: str) -> str:
    """任何输出都要过这一层，避免 token 出现在日志里。"""
    return text.replace(token, "***REDACTED***")


def api(method: str, path: str, token: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        API + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "douyin-video-to-transcript-publisher",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        if e.code == 422 and "already exists" in body:
            return {"_already_exists": True}
        raise RuntimeError(f"GitHub API {method} {path} -> HTTP {e.code}: {body[:300]}") from None


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失败: {(r.stderr or r.stdout).strip()[:300]}")
    return r


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("[ERROR] 未设置 GITHUB_TOKEN。请先创建具有 repo 权限的 PAT 并设为环境变量。", file=sys.stderr)
        print("        详见 README.md「从其他电脑发布」一节。", file=sys.stderr)
        return 2
    repo = os.environ.get("GITHUB_REPO") or DEFAULT_REPO
    private = os.environ.get("GITHUB_PRIVATE", "0") == "1"

    try:
        me = api("GET", "/user", token)
        login = me["login"]
        print(f"GitHub 账号: {login}")

        res = api("POST", "/user/repos", token, {
            "name": repo,
            "description": DESCRIPTION,
            "private": private,
            "has_issues": True,
            "has_wiki": False,
            "has_projects": False,
            "auto_init": False,          # 不初始化 README，避免与本地首次提交冲突
        })
        print("仓库已存在，沿用" if res.get("_already_exists") else f"仓库已创建: {login}/{repo}")

        # 本地仓库与提交身份
        if git("rev-parse", "--is-inside-work-tree", check=False).returncode != 0:
            git("init")
        name = os.environ.get("GIT_AUTHOR_NAME") or git("config", "user.name", check=False).stdout.strip()
        email = os.environ.get("GIT_AUTHOR_EMAIL") or git("config", "user.email", check=False).stdout.strip()
        if not name or not email:
            raise RuntimeError("请先设置提交身份：git config user.name / user.email（或环境变量 GIT_AUTHOR_NAME / GIT_AUTHOR_EMAIL）")

        git("add", "-A")
        staged = git("diff", "--cached", "--name-only").stdout.strip()
        if staged:
            git("-c", f"user.name={name}", "-c", f"user.email={email}",
                "commit", "-m", "feat: initial release of douyin video to transcript workflow")
            print(f"已提交 {len(staged.splitlines())} 个文件")
        else:
            print("没有待提交改动，使用现有提交")

        branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "main"
        if branch != "main":
            git("branch", "-M", "main")

        clean_url = f"https://github.com/{login}/{repo}.git"
        # token 只在这一个子进程里出现；不写入 .git/config
        push_url = f"https://x-access-token:{token}@github.com/{login}/{repo}.git"
        r = subprocess.run(["git", "push", push_url, "HEAD:refs/heads/main"],
                           cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            raise RuntimeError("git push 失败: " + (r.stderr or r.stdout).strip()[:300])

        # remote 保存干净地址，不含任何凭据
        git("remote", "remove", "origin", check=False)
        git("remote", "add", "origin", clean_url)
        print(f"\n发布完成: https://github.com/{login}/{repo}")
        print("提示：请在 GitHub 设置中撤销本次使用的 PAT。")
        return 0
    except Exception as e:
        print("[ERROR] " + redact(str(e), token), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
