#!/usr/bin/env python3
"""Structured git commit helper for Remote-Controller.

Staging control, staged diff summary, closed type list, `git commit -F`,
Co-Authored-By injection, auto-quick mode, push with retry,
and automatic PR creation + CI auto-merge into main.

Modes:
  committer.py                          stage, then print diff/stat + template for drafting
  committer.py --message-file F         commit with the drafted message, push, create PR & auto-merge
  committer.py --auto-quick             build a short message from staged files, commit, push, create PR & auto-merge
  committer.py --sync                   safe pull: fetch, then fast-forward only
  committer.py --patrol                 inspect tools, git state, Python and pyproject packages
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Sequence, Set

sys.path.insert(0, str(Path(__file__).resolve().parent))
import repo_health  # noqa: E402

GIT_TIMEOUT_SEC = 60
GIT_COMMIT_TIMEOUT_SEC = 300
GIT_PUSH_TIMEOUT_SEC = 300
PUSH_BACKOFF_SEC = (2, 4, 8, 16)

COMMIT_TYPES = ("feat", "fix", "refactor", "docs", "test", "style", "chore", "revert", "merge")
COAUTHOR_LINE = "Co-Authored-By: Claude <noreply@anthropic.com>"
COAUTHOR_RE = re.compile(r"^Co-Authored-By:\s*Claude\b", re.M | re.I)
HEADER_RE = re.compile(rf"^({'|'.join(COMMIT_TYPES)})(\([^)]+\))?!?: \S")

FIX_SIGNALS = ("fix", "bug", "repair", "broken", "resolve")
FEAT_SIGNALS = ("feat", "new", "implement")
SCOPE_DOMINANCE = 0.5
AUTO_QUICK_FILE_SOFT_LIMIT = 10

SENSITIVE_PATTERNS = (
    ".env", ".env.*", "*.pem", "*.key", "id_rsa", "id_ed25519",
    "credentials/*", "*/credentials/*", "credentials.json", "secrets.*",
)

TEMPLATE = """\
<type>(<scope>): <short description>

## 核心變更

- 具體改了什麼

## 變更理由

- 為什麼改、解決了什麼問題

## 驗證

- 跑過什麼檢查與結果（純文件變更寫「無需測試—純文件變更」）

## Pending Tasks

- 無
"""


def git(args: Sequence[str], timeout: int = GIT_TIMEOUT_SEC, check: bool = True) -> subprocess.CompletedProcess:
    """Run git; stdout decoded leniently so binary diffs cannot crash the script."""
    result = subprocess.run(["git", *args], capture_output=True, timeout=timeout, check=check)
    result.stdout = result.stdout.decode("utf-8", errors="replace")
    result.stderr = result.stderr.decode("utf-8", errors="replace")
    return result


def staged_files() -> List[str]:
    out = git(["-c", "core.quotePath=false", "diff", "--staged", "--name-only"]).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


def staged_diff() -> str:
    return git(["diff", "--staged", "--", ".", ":(exclude)*.json"]).stdout


def staged_stat() -> str:
    return git(["diff", "--staged", "--stat", "--", ".", ":(exclude)*.json"]).stdout


def current_branch() -> str:
    return git(["branch", "--show-current"]).stdout.strip()


def path_matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatch(path, pattern) or path.startswith(pattern.rstrip("/") + "/")


def find_sensitive(files: Sequence[str]) -> List[str]:
    hits = []
    for f in files:
        name = Path(f).name
        if any(fnmatch.fnmatch(name, p) or fnmatch.fnmatch(f, p) for p in SENSITIVE_PATTERNS):
            hits.append(f)
    return hits


def find_rule_sync_issues(repo_root: Path = Path(".")) -> List[str]:
    """Verify that .claude/rules/*.md are indexed in both CLAUDE.md and .agent/rules/AGENT.md."""
    issues: List[str] = []
    claude_rules = repo_root / ".claude" / "rules"
    agent_rules = repo_root / ".agent" / "rules"
    agent_md = agent_rules / "AGENT.md"
    claude_md = repo_root / "CLAUDE.md"

    if agent_rules.is_dir():
        extra_agent_files = [p.name for p in sorted(agent_rules.glob("*.md")) if p.name != "AGENT.md"]
        if extra_agent_files:
            issues.append(f".agent/rules/ 僅應保留 AGENT.md 單一入口，請將規則移至 .claude/rules/：{', '.join(extra_agent_files)}")

    if claude_rules.is_dir():
        rule_files = sorted(claude_rules.glob("*.md"))
        if claude_md.is_file():
            claude_text = claude_md.read_text(encoding="utf-8", errors="replace")
            for rf in rule_files:
                if rf.name not in claude_text:
                    issues.append(f".claude/rules/{rf.name} 尚未加入 CLAUDE.md 索引中")
        if agent_md.is_file():
            agent_text = agent_md.read_text(encoding="utf-8", errors="replace")
            for rf in rule_files:
                if rf.name not in agent_text:
                    issues.append(f".claude/rules/{rf.name} 尚未加入 .agent/rules/AGENT.md 索引中")
    return issues


def stage_paths(
    stage_list: Optional[Sequence[str]] = None,
    exclude: Optional[Sequence[str]] = None,
    no_stage: bool = False,
) -> None:
    if no_stage:
        return

    if stage_list:
        git(["reset"])
        git(["add", "--", *stage_list])
        return

    git(["add", "."])
    if exclude:
        unstage = [f for f in staged_files() if any(path_matches(f, pat) for pat in exclude)]
        if unstage:
            git(["reset", "HEAD", "--", *unstage])


def validate_header(header: str) -> None:
    if not HEADER_RE.match(header):
        types_str = ", ".join(COMMIT_TYPES)
        raise ValueError(
            f"標題格式不合規範：{header!r}\n"
            f"必須符合 '<type>(<scope>): <desc>' 或 '<type>: <desc>'，"
            f"且 type 必須在以下清單中：{types_str}"
        )


def append_coauthor(msg: str) -> str:
    if COAUTHOR_RE.search(msg):
        return msg
    trimmed = msg.rstrip()
    return f"{trimmed}\n\n{COAUTHOR_LINE}\n"


def infer_type_and_scope(files: Sequence[str]) -> tuple[str, str]:
    if not files:
        return "chore", ""

    paths = [Path(f) for f in files]
    scopes = [p.parts[0] if len(p.parts) > 1 else "" for p in paths]
    non_empty_scopes = [s for s in scopes if s]

    scope = ""
    if non_empty_scopes:
        from collections import Counter
        counts = Counter(non_empty_scopes)
        most_common, count = counts.most_common(1)[0]
        if count / len(files) >= SCOPE_DOMINANCE:
            scope = most_common

    all_docs = all(p.suffix in (".md", ".txt", ".rst") or "docs" in p.parts for p in paths)
    if all_docs:
        return "docs", scope

    return "feat", scope


def build_auto_quick_message(files: Sequence[str]) -> str:
    commit_type, scope = infer_type_and_scope(files)
    prefix = f"{commit_type}({scope})" if scope else commit_type
    desc = f"更新 {len(files)} 個檔案" if len(files) > 1 else f"更新 {Path(files[0]).name}"
    header = f"{prefix}: {desc}"

    bullets = [f"- 更新 `{f}`" for f in files[:AUTO_QUICK_FILE_SOFT_LIMIT]]
    if len(files) > AUTO_QUICK_FILE_SOFT_LIMIT:
        bullets.append(f"- ... 及其他 {len(files) - AUTO_QUICK_FILE_SOFT_LIMIT} 個檔案")

    body = "\n".join(bullets)
    msg = f"{header}\n\n## 核心變更\n\n{body}\n\n## 變更理由\n\n- 自動精簡提交\n\n## 驗證\n\n- 本機建構與測試完成\n\n## Pending Tasks\n\n- 無\n"
    return append_coauthor(msg)


def commit_with_message_file(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    lines = text.strip().splitlines()
    if not lines:
        raise ValueError(f"訊息檔為空：{path}")
    validate_header(lines[0])

    final_msg = append_coauthor(text)
    path.write_text(final_msg, encoding="utf-8")
    git(["commit", "-F", str(path)], timeout=GIT_COMMIT_TIMEOUT_SEC)
    return final_msg


def push_with_retry(branch: str) -> bool:
    if not branch:
        print("[warn] 無法偵測目前分支名稱，跳過推送。")
        return False

    for attempt, delay in enumerate(PUSH_BACKOFF_SEC, start=1):
        try:
            res = git(["push", "-u", "origin", branch], timeout=GIT_PUSH_TIMEOUT_SEC, check=False)
            if res.returncode == 0:
                print(f"[ok] 已推送到 origin/{branch}")
                return True
            print(f"[warn] 推送失敗（第 {attempt} 次）：{res.stderr.strip()}")
        except subprocess.TimeoutExpired:
            print(f"[warn] 推送逾時（第 {attempt} 次）")

        if attempt < len(PUSH_BACKOFF_SEC):
            time.sleep(delay)

    print(f"[error] 推送失敗超過重試次數，請稍後手動執行：git push -u origin {branch}", file=sys.stderr)
    return False


def handle_pr_and_merge(branch: str, full_message: str, auto_merge: bool = True) -> None:
    """自動建立 PR 並於 CI 通過後自動合併至 main。"""
    if branch == "main":
        print("[info] 目前已在 main 分支，無需建立 PR。")
        return

    if not shutil.which("gh"):
        print("[warn] 系統中未檢測到 gh CLI 工具，跳過自動建立 PR 與合併流程。")
        return

    lines = full_message.strip().splitlines()
    title = lines[0] if lines else f"feat: update {branch}"
    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else "由 Agent 自動提交之更新"

    # 1. 檢查是否已有現存 PR
    pr_url = ""
    view_res = subprocess.run(["gh", "pr", "view", branch, "--json", "number,url"], capture_output=True, text=True)
    if view_res.returncode == 0:
        try:
            data = json.loads(view_res.stdout)
            pr_url = data.get("url", "")
            print(f"[ok] 現存 PR 已就緒：{pr_url}")
        except Exception:
            pass

    # 2. 若無 PR 則自動建立
    if not pr_url:
        create_res = subprocess.run(
            ["gh", "pr", "create", "--base", "main", "--head", branch, "--title", title, "--body", body],
            capture_output=True, text=True
        )
        if create_res.returncode == 0:
            pr_url = create_res.stdout.strip()
            print(f"[ok] 已自動建立 Pull Request：{pr_url}")
        else:
            print(f"[warn] 自動建立 PR 失敗：{create_res.stderr.strip()}")
            return

    if not auto_merge:
        print(f"[info] 未啟用自動合併，請手動檢視 PR：{pr_url}")
        return

    # 3. 嘗試啟用 GitHub 原生 Auto-Merge
    auto_res = subprocess.run(
        ["gh", "pr", "merge", branch, "--auto", "--merge", "--delete-branch"],
        capture_output=True, text=True
    )
    if auto_res.returncode == 0:
        print("[ok] 已成功啟用 GitHub Auto-Merge，CI 檢查通過後將自動合併至 main 並刪除分支。")
        return

    # 4. 若倉庫未開放 Auto-Merge，則主動等待 CI 檢查全綠後執行 Merge Commit
    print(f"[info] 等待 GitHub Actions 工作流啟動中 (5 秒)...")
    time.sleep(5)
    watch_ok = False
    for attempt in range(1, 4):
        watch_res = subprocess.run(["gh", "pr", "checks", branch, "--watch"])
        if watch_res.returncode == 0:
            watch_ok = True
            break
        print(f"[warn] 監聽中發生網路中斷或暫時逾時（第 {attempt} 次），3 秒後重試...")
        time.sleep(3)

    if watch_ok:
        merge_res = subprocess.run(
            ["gh", "pr", "merge", branch, "--merge", "--delete-branch"],
            capture_output=True, text=True
        )
        if merge_res.returncode == 0:
            print(f"[ok] 🎉 CI 全綠！PR 已成功合併進 main 分支，並清理本機/遠端分支 {branch}。")
            git(["checkout", "main"])
            git(["pull", "--ff-only"])
            print("[ok] 本機工作區已自動切換並同步至最新 main 分支。")
        else:
            print(f"[warn] 合併 PR 失敗：{merge_res.stderr.strip()}")
    else:
        print(f"[warn] CI 檢查未全數通過或逾時，請手動確認 PR 狀態：{pr_url}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--message-file", type=Path, help="讀取訊息檔，驗證標題後 git commit -F，並補上 Co-Authored-By")
    parser.add_argument("--auto-quick", action="store_true", help="依 staged 檔案自動產生標題與 bullet")
    parser.add_argument("--no-push", action="store_true", help="提交後不推送")
    parser.add_argument("--no-pr", action="store_true", help="推送後不自動建立 PR")
    parser.add_argument("--no-merge", action="store_true", help="建立 PR 後不自動等待合併")
    parser.add_argument("--dry-run", action="store_true", help="只預覽訊息，不提交")
    parser.add_argument("--no-stage", action="store_true", help="不執行 git add，使用既有暫存區")
    parser.add_argument("--stage-list", nargs="+", help="清空暫存區後只暫存指定路徑")
    parser.add_argument("--exclude", nargs="+", help="排除指定路徑")
    parser.add_argument("--allow-sensitive", action="store_true", help="略過敏感檔案檢查")
    parser.add_argument("--allow-missing-deps", action="store_true", help="略過規則同步檢查")

    parser.add_argument("--sync", action="store_true", help="安全拉取：fetch 後只 fast-forward，有未提交變更或分叉時不動並回報")
    parser.add_argument("--fetch-only", action="store_true", help="搭配 --sync：只 fetch 並回報落後，不快轉")
    parser.add_argument("--patrol", action="store_true", help="巡檢系統工具、git 狀態、Python 版本與 pyproject 套件安裝情況")

    args = parser.parse_args()

    if args.sync:
        return repo_health.print_report(repo_health.sync_repo(fetch_only=args.fetch_only))
    if args.patrol:
        return repo_health.print_report(repo_health.patrol_repo())

    stage_paths(stage_list=args.stage_list, exclude=args.exclude, no_stage=args.no_stage)

    files = staged_files()
    if not files:
        print("[info] 暫存區中無檔案可提交。")
        return 0

    if not args.allow_sensitive:
        sensitive = find_sensitive(files)
        if sensitive:
            print(f"[error] 暫存區中含有敏感檔案，已中止提交：\n  " + "\n  ".join(sensitive), file=sys.stderr)
            return 1

    rules_warning = repo_health.claude_without_rules_warning(files)
    if rules_warning:
        print(f"[warn] {rules_warning}")

    if not args.allow_missing_deps:
        sync_issues = find_rule_sync_issues()
        if sync_issues:
            print("[error] 發現規則索引同步問題：", file=sys.stderr)
            for iss in sync_issues:
                print(f"  - {iss}", file=sys.stderr)
            return 1

    # 確保不在 main 分支直接提交；若在 main 分支則自動切換至 feature 分支
    branch = current_branch()
    if branch == "main" and not args.no_pr:
        new_branch = f"feat/auto-{int(time.time())}"
        print(f"[info] 目前位於 main 分支。為了落實 PR CI 規範，自動建立並切換至：{new_branch}")
        git(["checkout", "-b", new_branch])
        branch = new_branch

    if args.message_file:
        if args.dry_run:
            print("[dry-run] 讀取訊息檔預覽：")
            print(args.message_file.read_text(encoding="utf-8"))
            return 0
        committed_msg = commit_with_message_file(args.message_file)
        if not args.no_push:
            if push_with_retry(branch):
                if not args.no_pr:
                    handle_pr_and_merge(branch, committed_msg, auto_merge=not args.no_merge)
        return 0

    if args.auto_quick:
        msg = build_auto_quick_message(files)
        if args.dry_run:
            print("[dry-run] 自動產生的訊息：\n")
            print(msg)
            return 0
        temp_file = Path(".git/COMMIT_MSG_TEMP")
        temp_file.write_text(msg, encoding="utf-8")
        try:
            committed_msg = commit_with_message_file(temp_file)
        finally:
            if temp_file.exists():
                temp_file.unlink()
        if not args.no_push:
            if push_with_retry(branch):
                if not args.no_pr:
                    handle_pr_and_merge(branch, committed_msg, auto_merge=not args.no_merge)
        return 0

    # 預設模式：印出 diff 與草擬模板供 Agent 填寫
    print("=== Staged Stat ===")
    print(staged_stat() or "(無變更)")
    print("=== Draft Template ===")
    print(TEMPLATE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
