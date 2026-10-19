# 工業用無線遙控器系統架構與規格書 (System Architecture & Specs)

## 1. 專案背景與參考標竿

本專案旨在研發工業級行車/起重機無線遙控器（Wireless Pendant Remote Controller），參考以下兩大主流工業廠商標準：
1. **Schneider Electric Harmony eXLhoist (ZART8LS)**：
   - 6 動作按鈕（Up, Down, East, West, North, South）+ 2 輔助按鈕（Start, Horn）+ 頂部急停開關（E-Stop）。
   - IP65 防塵防水防摔規格，LED 狀態指示，雙向通訊機制。
2. **Advanced Radiotech Corporation (大灃科技 ARC FLEX 系列)**：
   - 台灣與全球起重機市場高普及率標準。
   - 工業級對向互鎖防護（Motion Interlock）、32-bit 安全配對 ID、滾動計數與 CRC 校驗、心跳監視（Watchdog Fail-Safe）。

---

## 2. 系統架構分層

```
+-------------------------------------------------------------+
| Application Layer: 狀態機 (Standby / Armed / Run / E-Stop)  |
+-------------------------------------------------------------+
| Safety & Interlock: 急停硬體/軟體雙斷、對向按鍵衝突抑制       |
+-------------------------------------------------------------+
| Protocol Layer: 16-Byte 工業封包封裝、序號防重放、CRC16 校驗 |
+-------------------------------------------------------------+
| Driver / Simulation: ESP32 GPIO, I2C OLED, Wokwi, Web V-HMI |
+-------------------------------------------------------------+
```

---

## 3. 通訊協定規範 (Protocol Specification)

所有無線射頻（RF / ESP-NOW / 2.4GHz）封包均採用緊密二進位結構（位元組對齊）：

| 偏移 (Offset) | 欄位名稱 | 型別 | 說明 |
| :--- | :--- | :--- | :--- |
| `0x00 - 0x01` | `sync1, sync2` | `uint8_t[2]` | 同步標頭：`0x53 0x45` (`'SE'`) |
| `0x02 - 0x05` | `systemId` | `uint32_t` | 32-bit 系統唯一配對碼 (防串台) |
| `0x06 - 0x07` | `seqNumber` | `uint16_t` | 滾動序號 (防重放攻擊) |
| `0x08` | `packetType` | `uint8_t` | `0x01`: 心跳, `0x02`: 命令, `0xFF`: 急停 |
| `0x09` | `systemState` | `uint8_t` | `0`: 待機, `1`: 就緒, `2`: 操作中, `3`: 急停, `4`: 互鎖錯誤 |
| `0x0A - 0x0B` | `buttonState` | `uint16_t` | 16-bit 按鍵狀態遮罩 (Bitmask) |
| `0x0C` | `batteryPercent` | `uint8_t` | 電池電量 (0 - 100%) |
| `0x0D - 0x0E` | `checksum` | `uint16_t` | CRC-16-CCITT 多項式校驗碼 |

---

## 4. 虛擬機模擬工作台 (Virtual Machine Simulation)

本專案提供兩套無硬體模擬方案：
1. **Web 虛擬機操作台 (`simulator/index.html`)**：
   - 工業黃黑防摔外殼擬真 UI。
   - 包含可拍下卡死/旋轉復歸的紅色 E-STOP、8 顆動作與輔助按鍵。
   - 模擬 128x64 點陣 OLED 螢幕，具備實時 RF 封包發射與 Hex 監控視窗。
   - 直接用瀏覽器開啟即可進行全邏輯測試。
2. **Wokwi 嵌入式電路模擬器 (`diagram.json` + `wokwi.toml`)**：
   - 模擬 ESP32 + SSD1306 OLED + 按鍵與 LED 指示燈，直接執行編譯後的 C/C++ 韌體二進位檔。
