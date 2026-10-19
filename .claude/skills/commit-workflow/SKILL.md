---
name: commit-workflow
description: 結構化 Git 提交流程：分析 staged diff，依統一模板草擬 Commit Message，用 git commit -F 提交並推送。
whenToUse: 當用戶說「開始提交流程」、「幫我 commit」，或需要產出結構化 Commit Message 時
disableModelInvocation: false
metadata:
  version: "2026.10.19.1"
---

# Commit Workflow Skill

## 觸發指令

- `開始提交流程`
- `幫我 commit`
- `python3 .claude/skills/commit-workflow/scripts/committer.py`（暫存並印出 diff 與模板，供 Agent 草擬）
- `python3 .claude/skills/commit-workflow/scripts/committer.py --message-file .git/COMMIT_MSG_TEMP --no-stage`（提交已草擬的訊息並推送）
- `python3 .claude/skills/commit-workflow/scripts/committer.py --auto-quick`（自動產生精簡訊息並提交，限小型變更）

### 參數

| 參數 | 用途 |
| :--- | :--- |
| `--message-file PATH` | 讀取訊息檔，驗證標題後 `git commit -F`，並補上 Co-Authored-By |
| `--auto-quick` | 依 staged 檔案自動產生標題與 bullet；與 `--message-file` 互斥；超過 10 檔會警告 |
| `--no-push` | 提交後不推送 |
| `--dry-run` | 只預覽訊息，不提交 |
| `--no-stage` | 不執行 `git add`，使用既有暫存區 |
| `--stage-list PATH...` | 清空暫存區後只暫存指定路徑 |
| `--exclude PATH...` | `git add .` 後排除指定路徑（支援 glob 與目錄前綴） |
| `--allow-sensitive` | 略過敏感檔案檢查（`.env`、`*.pem`、`*.key` 等） |
| `--allow-missing-deps` | 略過規範索引（`CLAUDE.md`／`.agent/rules/AGENT.md`）同步檢查 |

## 核心原則

讓每一次提交都成為日後可考古的紀錄：標題說明改了什麼，內文說明為什麼改、怎麼驗證。
遵循 Conventional Commits，並以統一模板取代分層判斷。

## 流程

1. **暫存**：`git add .`。使用者指定只提交某些檔案時，改為只暫存該些路徑。
2. **分析**：`git status --short` 與 `git diff --staged`。
3. **安全與規範檢查**：
   - staged 內若含 `.env`、金鑰、憑證等敏感內容，停止並告知使用者，不提交。
   - 檢查 `.claude/rules/*.md` 是否 100% 索引於 `CLAUDE.md` 與 `.agent/rules/AGENT.md` 中。
4. **草擬**：依模板寫出最終版本。
5. **提交**：寫入 `.git/COMMIT_MSG_TEMP`，執行 `python3 .claude/skills/commit-workflow/scripts/committer.py --message-file .git/COMMIT_MSG_TEMP --no-stage`。
6. **推送**：推送到當前分支。

## Commit Message 格式

### 標題
`<type>(<scope>): <簡短描述>`

- 標題不超過 72 字元，描述用現在式，說明結果而不是過程。
- Type 清單：`feat`, `fix`, `refactor`, `docs`, `test`, `style`, `chore`, `revert`, `merge`。

### 內文模板

```markdown
<type>(<scope>): <簡短描述>

## 核心變更

- 具體改了什麼（按主題分組，一行一件事）

## 變更理由

- 為什麼改、解決了什麼問題

## 驗證

- 跑過什麼檢查與結果（例：Wokwi 模擬測試通過、Web 虛擬機按鍵反應正常）

## Pending Tasks

- 發現但未處理的事項；沒有就寫「無」

Co-Authored-By: Claude <noreply@anthropic.com>
```
