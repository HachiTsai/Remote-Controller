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

---

## 5. 天車接收主機與電控箱架構 (Receiver Engine & Electrical Cabinet)

接收端引擎（`include/receiver.h`）實作工業起重機配電安全標準：

### 5.1 繼電器矩陣輸出 (Relay Outputs K1 ~ K8)
- **K1 (`RELAY_UP`)**: 捲揚機主鉤上升 (Hoist Up)
- **K2 (`RELAY_DOWN`)**: 捲揚機主鉤下降 (Hoist Down)
- **K3 (`RELAY_EAST`)**: 橫行小車向東 (Trolley East)
- **K4 (`RELAY_WEST`)**: 橫行小車向西 (Trolley West)
- **K5 (`RELAY_NORTH`)**: 縱行大車向北 (Bridge North)
- **K6 (`RELAY_SOUTH`)**: 縱行大車向南 (Bridge South)
- **K7 (`RELAY_HORN`)**: 警報電笛/蜂鳴器 (Buzzer / Horn)
- **K8 (`RELAY_MAIN`)**: 主電源接觸器 (Main Power Contactor KM1)

### 5.2 核心安全防護機制 (Industrial Safety Invariants)
1. **雙重對向互鎖驗證 (Dual Interlock)**：發射端做過按鍵衝突抑制，接收端韌體再次進行位元遮罩互鎖防呆，嚴禁反向接觸器同時吸合短路。
2. **500ms 看門狗超時斷訊安全跳脫 (Watchdog Fail-Safe)**：接收機持續監聽有效 RF 封包，若訊號中斷超過 500ms，自動判定離線並切斷主接觸器（K8 Drop），所有動作全面停機。
3. **衝頂極限開關保護 (Upper Limit Switch)**：當吊鉤碰觸最高限位微動開關時，硬體/軟體立即鎖定上升動能（禁止 K1），但保留下降動能（允許 K2）供操作員倒退脫困。
4. **急停最高優先權 (E-Stop Highest Priority)**：無論當前狀態為何，一旦收到急停封包或急停按鍵按下，主接觸器與動作繼電器瞬間強制斷電。

---

## 6. 2D 工廠動態數位分身 (Digital Twin Simulation)

在 `simulator/index.html` 內嵌整合式天車工廠動態模擬：
- **三欄一體化設計**：左欄為手持式遙控器（TX HMI），中欄為工廠天車 2D 畫布（60 FPS Canvas），右欄為接收機電控箱與封包終端（RX Cabinet）。
- **天車大樑與小車運動**：小車於雙主樑（Double Girder）水平橫行，鋼索滑輪總成實時帶動鍛造重型吊鉤升降。
- **重物吊裝與吸附**：地面放置 5-Ton 工業鋼卷貨物，吊鉤接近鋼卷並上升時自動掛載（Latch），放置回地面自動釋放（Unlatch）。
- **360° 旋轉警報燈與 Web Audio 聲效**：主接觸器導通時警報燈旋轉發光，動作時加速閃爍，並支援 Web Audio API 合成工業電笛蜂鳴音效。
- **故障注入測試**：提供「模擬斷訊 1 秒」按鈕與「注入 CRC 校驗錯誤」按鈕，讓開發者親眼見證看門狗超時與錯誤封包拒絕的安全反應。

