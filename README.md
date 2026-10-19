# Remote-Controller 工業用無線遙控器研發專案

本專案為工業級天車/起重機無線遙控器（Wireless Pendant Remote Controller）之系統架構與韌體開發倉庫。

參考工業標竿規格：
- **Schneider Electric**：Harmony eXLhoist (ZART8LS)
- **Advanced Radiotech (ARC)**：FLEX 8EX / 8ES 工業安全無線遙控系列

---

## 🌟 核心特色

1. **雙重安全防護機制**：
   - **緊急停止 (E-Stop)**：常閉 (NC) 硬體級迴路概念，按下強制切斷所有動作通道並發射急停封包。
   - **對向互鎖 (Interlock Protection)**：`UP/DOWN`、`EAST/WEST`、`NORTH/SOUTH` 相反方向嚴禁同動，防呆全斷。
2. **緊密二進位射頻協定 (RF Protocol)**：
   - 封裝對齊結構體、32-bit 安全配對 ID、滾動序號（Anti-Replay）、CRC-16 校驗。
3. **無硬體虛擬機工作台 (Virtual Machine HMI & Simulator)**：
   - **Web 虛擬機介面 (`simulator/index.html`)**：開箱即用的擬真手持遙控器操作台、即時 OLED 畫面與封包 Hex 監聽面板。
   - **Wokwi 模擬器 (`diagram.json`)**：搭配 PlatformIO 直接在虛擬 ESP32 上執行真實 C/C++ 韌體。
4. **Agent 協作規範與自動化提交流程**：
   - 遵照 `.claude/` 為唯一真實來源（SSOT），配置 `.agent/rules/AGENT.md` 與 `CLAUDE.md`。
   - 內建 `commit-workflow` 技能腳本自動執行 Conventional Commits 結構化提交。

---

## 📁 目錄結構

```text
Remote-Controller/
├── .claude/                # Claude / Agent SSOT 規範與技能庫
│   ├── rules/              # Git 提交、韌體架構、工業安全規範
│   └── skills/             # commit-workflow 結構化提交技能
├── .agent/                 # Antigravity 專用入口 (指向 .claude/)
├── CLAUDE.md               # 專案總覽入口與開發鐵律
├── platformio.ini          # PlatformIO 建構設定 (ESP32)
├── wokwi.toml              # Wokwi 模擬器配置
├── diagram.json            # Wokwi 虛擬電路圖 (ESP32 + 按鍵 + OLED + LED)
├── include/                # 標頭檔
│   ├── config.h            # 腳位定義、計時防彈跳參數
│   └── protocol.h          # 工業通訊協定、封包結構體、CRC16
├── src/                    # 韌體原始碼
│   └── main.cpp            # 主狀態機、互鎖邏輯、OLED 顯示
├── simulator/              # 虛擬機畫面 (Web 擬真操作面板)
│   └── index.html          # 雙擊即可在瀏覽器開啟
└── docs/                   # 系統架構與通訊協定規格書
    └── architecture-and-specs.md
```

---

## 🚀 快速上手

### 1. 開啟虛擬機操作面板 (Web Simulator)
無需安裝任何編譯工具，直接使用瀏覽器開啟：
```bash
open simulator/index.html
```
- 點擊「🟢 START」按鍵完成開機就緒。
- 測試操作 6 向動作按鍵、觀察 OLED 畫面與 RF 封包流。
- 測試紅色「STOP」急停拍下與復歸。

### 2. PlatformIO 韌體編譯 (選配)
本專案支援以 PlatformIO 編譯並透過 Wokwi 執行：
```bash
pio run
```

---

## 🤖 Agent 提交流程

本專案啟用結構化提交技能，執行：
```bash
python3 .claude/skills/commit-workflow/scripts/committer.py
```
可自動驗證規範索引、檢查敏感檔案、並產出標準 Conventional Commits 格式訊息。