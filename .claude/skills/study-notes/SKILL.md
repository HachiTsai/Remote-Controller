---
name: study-notes
description: 跨專案通用學習筆記技能，支援本機與雲端環境自動同步至 Google Drive 的 Agent_Study_Notes 目錄（按 repo名/類別_檔名.md 存放）。
type: prompt
whenToUse: 當使用者要求記錄學習心得、技術踩坑、架構決策、除錯排錯筆記，或要求查詢/回顧歷史筆記時調用。
disableModelInvocation: false
metadata:
  version: "1.0.0"
  folder_id: "1Xlj49hpabV47WMzctSNS29_Vuuh6ddHn"
---

# Study Notes Skill (跨專案通用學習筆記)

本技能提供標準化的學習筆記沉澱與檢索工作流，直接連接至 Google Drive 的 `00_Claude/Agent_Study_Notes/` 目錄。

## 📋 存放路徑與架構規範

- **本機 Google Drive 同步路徑**：
  `/Users/hachi/Library/CloudStorage/GoogleDrive-hachi.tsai@gmail.com/我的雲端硬碟/00_Claude/Agent_Study_Notes/`
- **雲端 Google Drive Folder ID**：
  `1Xlj49hpabV47WMzctSNS29_Vuuh6ddHn`
- **目錄結構**：
  `Agent_Study_Notes/<repo名>/<類別>_<檔名>.md`
  （若不在 git 目錄下，則預設存放在 `Agent_Study_Notes/Common/<類別>_<檔名>.md`）

---

## 🛠️ 常用指令

腳本位置：`.claude/skills/study-notes/scripts/note.py`

### 1. 新增筆記 (Add / Create)
```bash
python .claude/skills/study-notes/scripts/note.py add \
  --category "GCP" \
  --title "CloudFunction_Slack_Webhook_Fix" \
  --tags "gcp,slack,pubsub" \
  --content "## 📌 核心摘要\n...\n## 🛠️ 排錯步驟\n..."
```
- 或從檔案讀取長篇內容：
```bash
python .claude/skills/study-notes/scripts/note.py add \
  --category "Architecture" \
  --title "SSOT_Pattern" \
  --content-file <path_to_markdown>
```

### 2. 檢索筆記 (Search)
```bash
python .claude/skills/study-notes/scripts/note.py search "Webhook"
```

### 3. 讀取筆記 (Read)
```bash
python .claude/skills/study-notes/scripts/note.py read "GCP_CloudFunction_Slack_Webhook_Fix.md"
```

### 4. 列出目錄現有筆記 (List)
```bash
python .claude/skills/study-notes/scripts/note.py list
```

---

## 📝 筆記格式標準 (Frontmatter + Markdown)

每份筆記自動產生標準 YAML Frontmatter：

```markdown
---
title: "筆記標題"
repo: "當前專案名稱"
category: "技術分類"
date: YYYY-MM-DD
tags: ["tag1", "tag2"]
---

# 標題

## 📌 核心摘要 (TL;DR)
- 簡要說明問題、決策或學習核心。

## 🔍 問題背景與原理探討
- 詳細記錄當時的情境、錯誤現象與根因分析。

## 🛠️ 最佳實踐與排錯手冊
- 具體指令、設定檔範例、架構圖或程式碼片段。
```
