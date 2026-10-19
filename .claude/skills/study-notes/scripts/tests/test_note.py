import tempfile
import unittest
from pathlib import Path
import sys

# 將 scripts 加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from note import (
    sanitize_filename,
    LocalStorageBackend,
    get_current_repo_name,
)


class TestStudyNotes(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root_path = Path(self.temp_dir.name)
        self.backend = LocalStorageBackend(self.root_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_get_current_repo_name(self):
        repo_name = get_current_repo_name()
        self.assertIsInstance(repo_name, str)
        self.assertTrue(len(repo_name) > 0)

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename("GCP / Cloud: Function"), "GCP_Cloud_Function")
        self.assertEqual(sanitize_filename("test?name*"), "testname")

    def test_add_and_list_note(self):
        msg, path = self.backend.add(
            repo="TestRepo",
            category="GCP",
            title="Slack_Webhook",
            content="## 核心摘要\n修復了 Webhook URL。",
            tags=["gcp", "slack"],
        )
        self.assertTrue(Path(path).exists())
        self.assertIn("GCP_Slack_Webhook.md", path)

        notes = self.backend.list_notes(repo="TestRepo")
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]["filename"], "GCP_Slack_Webhook.md")
        self.assertEqual(notes[0]["repo"], "TestRepo")

    def test_search_note_by_content_and_filename(self):
        self.backend.add(
            repo="RepoA",
            category="BugFix",
            title="Database_Connection",
            content="修復了連線逾時問題，使用連線池機制。",
            tags=["db", "sql"],
        )
        self.backend.add(
            repo="RepoB",
            category="Architecture",
            title="Microservices",
            content="微服務架構拆分指引與實踐。",
            tags=["arch"],
        )

        # 搜尋檔名
        res1 = self.backend.search("Database")
        self.assertEqual(len(res1), 1)
        self.assertEqual(res1[0]["repo"], "RepoA")

        # 搜尋內文
        res2 = self.backend.search("連線池")
        self.assertEqual(len(res2), 1)
        self.assertEqual(res2[0]["repo"], "RepoA")
        self.assertIn("連線池", res2[0]["snippet"])

        # 搜尋微服務
        res3 = self.backend.search("微服務")
        self.assertEqual(len(res3), 1)
        self.assertEqual(res3[0]["repo"], "RepoB")

    def test_read_note(self):
        self.backend.add(
            repo="RepoC",
            category="Tips",
            title="Git_Branching",
            content="始終使用 Feature Branch 與 PR。",
            tags=["git"],
        )
        content = self.backend.read("Tips_Git_Branching.md", repo="RepoC")
        self.assertIsNotNone(content)
        self.assertIn("title: \"Git_Branching\"", content)
        self.assertIn("始終使用 Feature Branch 與 PR。", content)


if __name__ == "__main__":
    unittest.main()
