#!/usr/bin/env python3
"""
Study Notes CLI - 跨專案通用學習筆記管理工具
支援自動同步至 Google Drive 的 Agent_Study_Notes 目錄（按 repo名/類別_檔名.md 存放）。
支援本地檔案系統直連與 gdrive CLI / 雲端環境雙模自動切換。
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DEFAULT_LOCAL_PATH = (
    Path.home()
    / "Library"
    / "CloudStorage"
    / "GoogleDrive-hachi.tsai@gmail.com"
    / "我的雲端硬碟"
    / "00_Claude"
    / "Agent_Study_Notes"
)
DEFAULT_FOLDER_ID = "1Xlj49hpabV47WMzctSNS29_Vuuh6ddHn"


def get_current_repo_name() -> str:
    """自動偵測當前 Git Repository 名稱，若不在 git 內則回傳 'Common'"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip()).name
    except Exception:
        pass
    return "Common"


def sanitize_filename(name: str) -> str:
    """清理檔名中的非法字元"""
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = re.sub(r"\s+", "_", name.strip())
    return name


def find_gdrive_bin() -> Optional[str]:
    """尋找 gdrive CLI 執行檔路徑"""
    custom_bin = Path.home() / ".gemini" / "antigravity" / "bin" / "gdrive"
    if custom_bin.exists() and os.access(custom_bin, os.X_OK):
        return str(custom_bin)
    system_bin = shutil.which("gdrive")
    if system_bin:
        return system_bin
    return None


class StorageBackend:
    def add(
        self,
        repo: str,
        category: str,
        title: str,
        content: str,
        tags: List[str],
    ) -> Tuple[str, str]:
        """新增筆記，回傳 (狀態訊息, 檔案路徑或ID)"""
        raise NotImplementedError

    def search(self, query: str, repo: Optional[str] = None) -> List[Dict]:
        """檢索筆記"""
        raise NotImplementedError

    def read(self, identifier: str, repo: Optional[str] = None) -> Optional[str]:
        """讀取筆記內容"""
        raise NotImplementedError

    def list_notes(self, repo: Optional[str] = None) -> List[Dict]:
        """列出筆記"""
        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _format_content(
        self, repo: str, category: str, title: str, content: str, tags: List[str]
    ) -> str:
        today = datetime.date.today().isoformat()
        tags_str = ", ".join(f'"{t.strip()}"' for t in tags if t.strip())
        frontmatter = (
            f"---\n"
            f'title: "{title}"\n'
            f'repo: "{repo}"\n'
            f'category: "{category}"\n'
            f"date: {today}\n"
            f"tags: [{tags_str}]\n"
            f"---\n\n"
        )
        return frontmatter + content.strip() + "\n"

    def add(
        self,
        repo: str,
        category: str,
        title: str,
        content: str,
        tags: List[str],
    ) -> Tuple[str, str]:
        repo_dir = self.root_dir / sanitize_filename(repo)
        repo_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{sanitize_filename(category)}_{sanitize_filename(title)}.md"
        target_path = repo_dir / filename
        formatted_content = self._format_content(
            repo, category, title, content, tags
        )

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(formatted_content)

        return (
            f"成功寫入本機筆記（Google Drive 自動背景同步）: {filename}",
            str(target_path),
        )

    def list_notes(self, repo: Optional[str] = None) -> List[Dict]:
        notes = []
        if repo:
            target_dirs = [self.root_dir / sanitize_filename(repo)]
        else:
            target_dirs = [p for p in self.root_dir.iterdir() if p.is_dir()]

        for r_dir in target_dirs:
            if not r_dir.exists():
                continue
            for file_path in r_dir.glob("*.md"):
                try:
                    stat = file_path.stat()
                    notes.append(
                        {
                            "repo": r_dir.name,
                            "filename": file_path.name,
                            "path": str(file_path),
                            "modified": datetime.datetime.fromtimestamp(
                                stat.st_mtime
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                        }
                    )
                except Exception:
                    pass
        notes.sort(key=lambda x: (x["repo"], x["filename"]))
        return notes

    def search(self, query: str, repo: Optional[str] = None) -> List[Dict]:
        all_notes = self.list_notes(repo)
        query_lower = query.lower()
        results = []

        for note in all_notes:
            file_path = Path(note["path"])
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                matched = False
                snippet = ""
                if query_lower in note["filename"].lower():
                    matched = True
                    snippet = "匹配檔名"
                elif query_lower in content.lower():
                    matched = True
                    # 擷取關鍵字上下文片段
                    idx = content.lower().find(query_lower)
                    start = max(0, idx - 40)
                    end = min(len(content), idx + 60)
                    snippet = "..." + content[start:end].replace("\n", " ") + "..."

                if matched:
                    res = dict(note)
                    res["snippet"] = snippet
                    results.append(res)
            except Exception:
                continue

        return results

    def read(self, identifier: str, repo: Optional[str] = None) -> Optional[str]:
        target = Path(identifier)
        if target.exists() and target.is_file():
            with open(target, "r", encoding="utf-8") as f:
                return f.read()

        # 嘗試在指定或所有 repo 中尋找該檔案名稱
        all_notes = self.list_notes(repo)
        for note in all_notes:
            if (
                note["filename"] == identifier
                or note["filename"].lower() == identifier.lower()
                or identifier.lower() in note["filename"].lower()
            ):
                with open(note["path"], "r", encoding="utf-8") as f:
                    return f.read()
        return None


class GDriveCliStorageBackend(StorageBackend):
    def __init__(self, gdrive_bin: str, folder_id: str):
        self.gdrive_bin = gdrive_bin
        self.folder_id = folder_id

    def _run_gdrive(self, args: List[str]) -> subprocess.CompletedProcess:
        cmd = [self.gdrive_bin] + args
        return subprocess.run(cmd, capture_output=True, text=True, check=False)

    def _get_or_create_repo_folder(self, repo: str) -> str:
        # 1. 查詢 folder_id 底下的資料夾
        res = self._run_gdrive(["readonly", "ls", self.folder_id, "--json"])
        if res.returncode == 0:
            try:
                items = json.loads(res.stdout.strip() or "[]")
                for item in items:
                    if item.get("name") == repo and item.get("mimeType") == "application/vnd.google-apps.folder":
                        return item["id"]
            except Exception:
                pass

        # 2. 不存在則建立
        res_mkdir = self._run_gdrive(["mutate", "mkdir", repo, "--parent", self.folder_id, "--json"])
        if res_mkdir.returncode == 0:
            try:
                data = json.loads(res_mkdir.stdout.strip())
                if "id" in data:
                    return data["id"]
            except Exception:
                pass
        return self.folder_id

    def add(
        self,
        repo: str,
        category: str,
        title: str,
        content: str,
        tags: List[str],
    ) -> Tuple[str, str]:
        repo_folder_id = self._get_or_create_repo_folder(repo)
        filename = f"{sanitize_filename(category)}_{sanitize_filename(title)}.md"

        # 寫入暫存檔
        temp_dir = Path("/tmp/claude_notes")
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / filename

        today = datetime.date.today().isoformat()
        tags_str = ", ".join(f'"{t.strip()}"' for t in tags if t.strip())
        formatted = (
            f"---\n"
            f'title: "{title}"\n'
            f'repo: "{repo}"\n'
            f'category: "{category}"\n'
            f"date: {today}\n"
            f"tags: [{tags_str}]\n"
            f"---\n\n"
            f"{content.strip()}\n"
        )
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(formatted)

        # 上傳至 Google Drive
        res = self._run_gdrive(
            ["mutate", "upload", str(temp_file), "--parent", repo_folder_id, "--json"]
        )
        if res.returncode == 0:
            return (f"成功上傳筆記至 Google Drive: {filename}", res.stdout.strip())
        else:
            return (
                f"上傳失敗，保留暫存於 {temp_file}: {res.stderr.strip()}",
                str(temp_file),
            )

    def list_notes(self, repo: Optional[str] = None) -> List[Dict]:
        target_id = self.folder_id
        if repo:
            target_id = self._get_or_create_repo_folder(repo)

        res = self._run_gdrive(["readonly", "ls", target_id, "--json"])
        notes = []
        if res.returncode == 0:
            try:
                items = json.loads(res.stdout.strip() or "[]")
                for item in items:
                    if item.get("name", "").endswith(".md"):
                        notes.append(
                            {
                                "repo": repo or "Remote",
                                "filename": item.get("name"),
                                "id": item.get("id"),
                                "modified": item.get("modifiedTime", ""),
                            }
                        )
            except Exception:
                pass
        return notes

    def search(self, query: str, repo: Optional[str] = None) -> List[Dict]:
        res = self._run_gdrive(["readonly", "search", "--name-contains", query, "--json"])
        results = []
        if res.returncode == 0:
            try:
                items = json.loads(res.stdout.strip() or "[]")
                for item in items:
                    if item.get("name", "").endswith(".md"):
                        results.append(
                            {
                                "repo": repo or "Remote",
                                "filename": item.get("name"),
                                "id": item.get("id"),
                                "snippet": f"匹配 Drive 檔案: {item.get('name')}",
                            }
                        )
            except Exception:
                pass
        return results

    def read(self, identifier: str, repo: Optional[str] = None) -> Optional[str]:
        # 如果是 file ID 或需下載查看
        temp_dir = Path("/tmp/claude_notes")
        temp_dir.mkdir(parents=True, exist_ok=True)
        out_file = temp_dir / "read_note.md"

        res = self._run_gdrive(["readonly", "download", identifier, "-o", str(out_file)])
        if res.returncode == 0 and out_file.exists():
            with open(out_file, "r", encoding="utf-8") as f:
                return f.read()
        return None


def select_backend() -> StorageBackend:
    """自動判定最適合的儲存後端"""
    env_dir = os.environ.get("AGENT_STUDY_NOTES_DIR")
    if env_dir:
        return LocalStorageBackend(Path(env_dir))

    # 檢查本機 Google Drive 同步資料夾是否存在
    if DEFAULT_LOCAL_PATH.exists() and DEFAULT_LOCAL_PATH.is_dir():
        return LocalStorageBackend(DEFAULT_LOCAL_PATH)

    # 檢查 gdrive CLI
    gdrive_bin = find_gdrive_bin()
    folder_id = os.environ.get("AGENT_STUDY_NOTES_FOLDER_ID", DEFAULT_FOLDER_ID)
    if gdrive_bin:
        return GDriveCliStorageBackend(gdrive_bin, folder_id)

    # 兜底：如果完全沒有本機 Drive 也沒有 gdrive CLI，存放在當前專案 .claude/notes
    fallback_dir = Path(".claude") / "notes"
    print(
        f"⚠️ 未偵測到本機 Google Drive 掛載或 gdrive CLI，自動退回專案本地儲存: {fallback_dir}",
        file=sys.stderr,
    )
    return LocalStorageBackend(fallback_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Study Notes CLI - 跨專案通用學習筆記管理工具"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Add command
    parser_add = subparsers.add_parser("add", help="新增一則學習筆記")
    parser_add.add_argument("--category", "-c", required=True, help="筆記類別 (例: GCP, Architecture, BugFix)")
    parser_add.add_argument("--title", "-t", required=True, help="筆記標題 (例: Slack_Webhook_Fix)")
    parser_add.add_argument("--tags", help="標籤列表，以逗號分隔 (例: gcp,slack,webhook)")
    parser_add.add_argument("--content", help="筆記內文 (Markdown 格式)")
    parser_add.add_argument("--content-file", help="從指定的 Markdown 檔案讀取筆記內文")
    parser_add.add_argument("--repo", help="指定專案名稱 (預設自動偵測 Git repo)")

    # Search command
    parser_search = subparsers.add_parser("search", help="搜尋既有筆記")
    parser_search.add_argument("query", help="搜尋關鍵字")
    parser_search.add_argument("--repo", help="限定在特定 repo 內搜尋")

    # Read command
    parser_read = subparsers.add_parser("read", help="讀取筆記內容")
    parser_read.add_argument("identifier", help="筆記檔名、路徑或 Drive File ID")
    parser_read.add_argument("--repo", help="指定專案名稱")

    # List command
    parser_list = subparsers.add_parser("list", help="列出所有筆記")
    parser_list.add_argument("--repo", help="限定特定 repo")

    args = parser.parse_args()
    backend = select_backend()

    repo = args.repo or get_current_repo_name()

    if args.command == "add":
        content = ""
        if args.content_file:
            cf = Path(args.content_file)
            if not cf.exists():
                print(f"❌ 錯誤: 找不到指定的內容檔案 {args.content_file}", file=sys.stderr)
                sys.exit(1)
            with open(cf, "r", encoding="utf-8") as f:
                content = f.read()
        elif args.content:
            content = args.content
        else:
            print("❌ 錯誤: 請提供 --content 或 --content-file", file=sys.stderr)
            sys.exit(1)

        tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
        msg, path_or_id = backend.add(repo, args.category, args.title, content, tags)
        print(f"✅ {msg}")
        print(f"📍 位置: {path_or_id}")

    elif args.command == "search":
        results = backend.search(args.query, repo=args.repo)
        if not results:
            print(f"🔍 未找到與 '{args.query}' 相關的筆記。")
        else:
            print(f"🔍 找到 {len(results)} 則相關筆記:")
            for idx, item in enumerate(results, 1):
                repo_label = f"[{item.get('repo', 'N/A')}]"
                fname = item.get("filename", "")
                snippet = item.get("snippet", "")
                path_or_id = item.get("path") or item.get("id") or ""
                print(f"  {idx}. {repo_label} {fname}")
                if snippet:
                    print(f"     細節: {snippet}")
                if path_or_id:
                    print(f"     路徑: {path_or_id}")

    elif args.command == "read":
        content = backend.read(args.identifier, repo=args.repo)
        if content is None:
            print(f"❌ 找不到筆記: {args.identifier}", file=sys.stderr)
            sys.exit(1)
        print(content)

    elif args.command == "list":
        notes = backend.list_notes(repo=args.repo)
        if not notes:
            print("📭 目前尚無任何筆記。")
        else:
            print(f"📚 共有 {len(notes)} 則筆記:")
            for idx, item in enumerate(notes, 1):
                repo_label = f"[{item.get('repo', 'N/A')}]"
                fname = item.get("filename", "")
                mtime = item.get("modified", "")
                print(f"  {idx}. {repo_label} {fname} ({mtime})")


if __name__ == "__main__":
    main()
