# Remote-Controller 開發與環境規範

本專案以 `.claude/` 為唯一真實來源（Single Source of Truth），所有通用規則與技能皆採用 Claude 官方語法集中於 `.claude/rules/` 與 `.claude/skills/` 管理（Antigravity 則透過 `.agent/rules/AGENT.md` 自動載入）：

- **Git 結構化提交流程規範**：@[.claude/rules/git-commit-workflow.md](.claude/rules/git-commit-workflow.md)
- **韌體分層架構規範**：@[.claude/rules/firmware-architecture.md](.claude/rules/firmware-architecture.md)
- **工業安全與互鎖規範**：@[.claude/rules/industrial-safety.md](.claude/rules/industrial-safety.md)

## 開發、擴充與提交鐵律

1. **擴充規則與技能**：新增任何規則或技能時，請以 Claude 官方語法直接建立於 `.claude/rules/<rule-name>.md` 或 `.claude/skills/<skill-name>/`，並同步更新本檔與 `.agent/rules/AGENT.md` 的引用清單。
2. **任務完成主動使用技能自動 Commit**：任何變更完成並通過驗證後，Agent 必須主動使用 `.claude/skills/commit-workflow/scripts/committer.py` 執行結構化 Commit 與 Push，嚴禁使用未經驗證的手動提交，無需等待使用者口令。
3. **安全第一**：本專案為工業級無線遙控器，任何按鈕控制與通訊協定變更必須落實安全急停（E-Stop）與對向互鎖（Interlock）邏輯。
