#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// ==========================================
// 工業用無線遙控器硬體腳位配置 (ESP32)
// 工業級天車起重機無線遙控規範 (符合 EN ISO 13849-1 / SIL2 安全標準)
// ==========================================

// 1. 緊急停止開關 (Emergency Stop - 常閉 NC 迴路，拉高時正常，按下開路/低電位)
#define PIN_ESTOP       4

// 2. 六大動作按鈕 (6 Motion Push Buttons)
#define PIN_BTN_UP      13   // 上 (升)
#define PIN_BTN_DOWN    12   // 下 (降)
#define PIN_BTN_EAST    14   // 東
#define PIN_BTN_WEST    27   // 西
#define PIN_BTN_SOUTH   26   // 南
#define PIN_BTN_NORTH   25   // 北

// 3. 兩大輔助按鈕 (2 Auxiliary Buttons)
#define PIN_BTN_START   33   // 啟動開關 / 電源聯鎖
#define PIN_BTN_HORN    32   // 警報喇叭 / 輔助功能

// 4. 狀態指示 LED (Status LEDs)
#define PIN_LED_STATUS  19   // 綠色 LED：發射中 / 正常工作
#define PIN_LED_FAULT   18   // 紅色 LED：急停觸發 / 互鎖錯誤 / 低電壓

// 5. I2C 顯示螢幕 (SSD1306 128x64 OLED)
#define PIN_I2C_SDA     21
#define PIN_I2C_SCL     22
#define OLED_SCREEN_WIDTH   128
#define OLED_SCREEN_HEIGHT  64
#define OLED_RESET          -1
#define OLED_I2C_ADDRESS    0x3C

// ==========================================
// 系統與安全時間參數
// ==========================================
#define DEBOUNCE_MS         20    // 按鍵防彈跳濾波時間 (毫秒)
#define HEARTBEAT_INTERVAL_MS 100 // 無按鍵時心跳封包發送間隔 (毫秒)
#define ACTIVE_TX_INTERVAL_MS 40  // 有按鍵動作時的高頻發送間隔 (毫秒)
#define SYSTEM_SECURITY_ID  0x53595331 // 32-bit 系統唯一配對安全碼 ('SYS1')

#endif // CONFIG_H
