# Git 結構化提交流程規範

本專案所有 Git 提交與推送操作一律透過 `.claude/skills/commit-workflow/scripts/committer.py` 執行，並遵循 [`.claude/skills/commit-workflow/SKILL.md`](../skills/commit-workflow/SKILL.md) 規範：

## 1. 分支與提交流程鐵律

1. **先開 PR 再合併 `main`**：
   - 所有變更（包括功能開發、模擬器更新、韌體重構、通訊協定修訂與文件）都在指定的分支上 commit 並推送，向 `main` 發起 Pull Request。
   - 禁止在未經充分驗證的情況下直接 push 到 `main` 分支。
2. **保留完整歷史歷程**：
   - 提交訊息需符合結構化模板，便於以 `git log --grep` 追溯歷史決策與硬體/通訊協定演進。

## 2. 自動提交流程原則

- **任務完成主動提交（Auto-Commit on Completion）**：任何功能開發、模擬器介面、韌體邏輯或設定變更完成後，**Agent 必須主動使用 `commit-workflow` 技能執行結構化提交與推送，無需等待使用者口令催促**。
- **禁止隨意手動提交**：嚴禁使用 raw `git commit -m`，所有提交一律使用技能腳本，確保 Commit Message 符合結構化模板規範。

## 3. 標準提交步驟

1. **暫存與檢查**：
   ```bash
   python3 .claude/skills/commit-workflow/scripts/committer.py
   ```
   檢查 staged diff、敏感檔案（`.env`、`*.key`、憑證私鑰）與規範索引同步情況。
2. **草擬與提交**：
   將符合模板的 Commit Message 寫入 `.git/COMMIT_MSG_TEMP`，再執行：
   ```bash
   python3 .claude/skills/commit-workflow/scripts/committer.py --message-file .git/COMMIT_MSG_TEMP --no-stage
   ```

## 4. 安全防護

- **敏感檔案攔截**：暫存區若包含 `.env*`、憑證私鑰、金鑰等檔案，腳本將自動中止並阻擋提交。
- **規則索引同步檢查**：驗證 `.claude/rules/*.md` 是否 100% 索引於根目錄 `CLAUDE.md` 與 `.agent/rules/AGENT.md` 中。

## 5. 禁止事項

- 禁止使用 `git commit -m` 傳遞多行未經格式化的訊息，一律使用 `--message-file`。
- 禁止提交任何明文金鑰、機密或硬編碼 Wi-Fi 密碼。
- 未經使用者明確同意，禁止執行 `git reset --hard`、`git rebase` 或 `git push --force`。
