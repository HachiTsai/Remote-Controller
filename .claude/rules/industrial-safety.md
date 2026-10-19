# 工業安全與互鎖規範 (Industrial Safety & Interlock Rules)

本專案遵從國際起重機安全標準規範（EN ISO 13849-1 PLd / IEC 61508 SIL2），定義以下安全鐵律：

## 1. 緊急停止（E-Stop / Emergency Stop）最高優先權

- **硬體層級保險**：E-Stop 採用常閉（NC - Normally Closed）安全迴路邏輯。一旦線路斷開或按鍵被拍下，立即進入急停狀態。
- **軟體覆蓋**：若 E-Stop 處於觸發狀態，韌體強制將所有動作通道（Motion Outputs）清零，禁止任何動作封包輸出，並持續發送 `ESTOP` 安全封包通知接收端跳開主電源接觸器（Main Contactor）。
- **重置流程**：E-Stop 解除（旋轉彈起）後，系統不得自動恢復動作，必須重新執行「按下 START 開機按鈕」程序方可重新聯鎖。

## 2. 動作按鈕對向互鎖（Motion Interlock Protection）

工業起重機與行車控制中，相反而衝突的運動方向嚴禁同時觸發：
- **互鎖配對**：
  - `UP`（上） 與 `DOWN`（下）
  - `EAST`（東） 與 `WEST`（西）
  - `NORTH`（北） 與 `SOUTH`（南）
- **處置邏輯**：當操作者因誤觸或開關故障導致對向按鈕同時處於按下狀態時，系統必須**強制判定兩者皆無效（雙向全斷）**，並在狀態 LED 或螢幕上發出 `INTERLOCK_ERR` 警告。

## 3. 心跳包與失聯保護（Watchdog & Fail-Safe）

- **定期心跳**：遙控器即使處於待機靜止狀態，每隔 100ms 仍需發送一筆心跳封包（含滾動計數器 Counter 與電量指標）。
- **逾時急停**：接收端控制器若超過 500ms 未收到任何有效封包，必須自動強制觸發急停並釋放所有繼電器輸出。

## 4. 封包完整性與安全防偽（Data Integrity & Unique ID）

- 每個封包包含唯一的 32-bit System Security ID，避免鄰近遙控器串台誤動作。
- 封包尾端必須附加 CRC16 或 CRC32 檢查碼，任何校驗失敗的封包一律直接拋棄。
