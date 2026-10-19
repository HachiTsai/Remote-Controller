import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".claude" / "skills" / "commit-workflow" / "scripts"))
import committer as c  # noqa: E402


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for cmd in (["init", "-q", "-b", "main"], ["config", "user.email", "test@example.com"], ["config", "user.name", "Tester"]):
        subprocess.run(["git", *cmd], check=True)
    return tmp_path


def test_coauthor_line_appending():
    msg = "feat(core): test message\n"
    res = c.append_coauthor(msg)
    assert c.COAUTHOR_LINE in res
    assert c.append_coauthor(res) == res


def test_header_validation():
    assert c.HEADER_RE.match("feat(core): initialize")
    assert c.HEADER_RE.match("fix: fix bug")
    assert not c.HEADER_RE.match("invalid(type): something")


def test_find_sensitive():
    files = ["src/main.cpp", ".env", "secrets.key", "include/config.h"]
    hits = c.find_sensitive(files)
    assert ".env" in hits
    assert "secrets.key" in hits
    assert "src/main.cpp" not in hits


def test_rule_sync_issues():
    # In this repo, rules must be indexed
    issues = c.find_rule_sync_issues(Path("."))
    assert len(issues) == 0, f"Sync issues found: {issues}"
