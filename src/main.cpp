#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#include "config.h"
#include "protocol.h"

// 建立 OLED 顯示物件
Adafruit_SSD1306 display(OLED_SCREEN_WIDTH, OLED_SCREEN_HEIGHT, &Wire, OLED_RESET);
bool oledReady = false;

// 系統全域變數
SystemState currentState = STATE_STANDBY;
uint16_t packetSeq = 0;
unsigned long lastTxTime = 0;
unsigned long lastDisplayTime = 0;
uint8_t simulatedBattery = 98;

// 按鍵原始讀取 (主動低電位 Active-LOW)
bool readPinActive(uint8_t pin) {
    return digitalRead(pin) == LOW;
}

// 初始化硬體腳位
void setupPins() {
    pinMode(PIN_ESTOP, INPUT_PULLUP);

    pinMode(PIN_BTN_UP, INPUT_PULLUP);
    pinMode(PIN_BTN_DOWN, INPUT_PULLUP);
    pinMode(PIN_BTN_EAST, INPUT_PULLUP);
    pinMode(PIN_BTN_WEST, INPUT_PULLUP);
    pinMode(PIN_BTN_SOUTH, INPUT_PULLUP);
    pinMode(PIN_BTN_NORTH, INPUT_PULLUP);

    pinMode(PIN_BTN_START, INPUT_PULLUP);
    pinMode(PIN_BTN_HORN, INPUT_PULLUP);

    pinMode(PIN_LED_STATUS, OUTPUT);
    pinMode(PIN_LED_FAULT, OUTPUT);

    digitalWrite(PIN_LED_STATUS, LOW);
    digitalWrite(PIN_LED_FAULT, LOW);
}

// 初始化 OLED 螢幕
void setupDisplay() {
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
    if (display.begin(SSD1306_SWITCHCAPVCC, OLED_I2C_ADDRESS)) {
        oledReady = true;
        display.clearDisplay();
        display.setTextColor(SSD1306_WHITE);
        display.setTextSize(1);
        display.setCursor(10, 15);
        display.println(F("IND CRANE V8"));
        display.setCursor(10, 30);
        display.println(F("REMOTE CONTROLLER"));
        display.setCursor(10, 45);
        display.println(F("SYSTEM BOOTING..."));
        display.display();
        delay(800);
    } else {
        Serial.println(F("[WARN] OLED not detected. Running headless mode."));
    }
}

// 繪製 OLED 畫面 (工業手持遙控器風格介面)
void updateDisplay(uint16_t rawMask, bool interlockError, bool estopActive) {
    if (!oledReady) return;

    display.clearDisplay();

    // 頂部狀態列
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.print(F("ID:SYS1  BAT:"));
    display.print(simulatedBattery);
    display.print(F("%"));

    display.drawLine(0, 10, 127, 10, SSD1306_WHITE);

    // 中間狀態顯示
    if (estopActive) {
        display.setTextSize(2);
        display.setCursor(12, 18);
        display.println(F("! E-STOP !"));
        display.setTextSize(1);
        display.setCursor(16, 40);
        display.println(F("OUTPUT CUT OFF"));
        display.setCursor(10, 52);
        display.println(F("ROTATE TO RELEASE"));
    } else if (interlockError) {
        display.setTextSize(1);
        display.setCursor(8, 20);
        display.println(F("! INTERLOCK ERROR !"));
        display.setCursor(8, 35);
        display.println(F("OPPOSITE KEYS PRESSED"));
        display.setCursor(12, 50);
        display.println(F("COMMAND INHIBITED"));
    } else if (currentState == STATE_STANDBY) {
        display.setTextSize(1);
        display.setCursor(15, 22);
        display.println(F("[ STANDBY MODE ]"));
        display.setCursor(8, 42);
        display.println(F("PRESS [START] TO ARM"));
    } else {
        // ARMED / OPERATING 運作畫面
        display.setTextSize(1);
        display.setCursor(0, 14);
        display.print(F("SYS: READY  TX:#"));
        display.print(packetSeq);

        // 動作向量指示圖示
        display.setCursor(8, 30);
        display.print(F("HOIST: "));
        if (rawMask & BTN_MASK_UP)   display.print(F("[ UP ]"));
        else if (rawMask & BTN_MASK_DOWN) display.print(F("[ DOWN ]"));
        else display.print(F("---"));

        display.setCursor(8, 42);
        display.print(F("TRAV : "));
        if (rawMask & BTN_MASK_EAST) display.print(F("[ EAST ]"));
        else if (rawMask & BTN_MASK_WEST) display.print(F("[ WEST ]"));
        else display.print(F("---"));

        display.setCursor(8, 54);
        display.print(F("CRANE: "));
        if (rawMask & BTN_MASK_NORTH) display.print(F("[ NORTH ]"));
        else if (rawMask & BTN_MASK_SOUTH) display.print(F("[ SOUTH ]"));
        else if (rawMask & BTN_MASK_HORN) display.print(F("< HORN >"));
        else display.print(F("---"));
    }

    display.display();
}

// 發送工業遙控通訊封包
void transmitPacket(uint16_t validButtonMask, PacketType pType) {
    RemotePacket pkt;
    pkt.sync1 = PROTOCOL_SYNC_BYTE1;
    pkt.sync2 = PROTOCOL_SYNC_BYTE2;
    pkt.systemId = SYSTEM_SECURITY_ID;
    pkt.seqNumber = ++packetSeq;
    pkt.packetType = (uint8_t)pType;
    pkt.systemState = (uint8_t)currentState;
    pkt.buttonState = validButtonMask;
    pkt.batteryPercent = simulatedBattery;

    // 校驗碼涵蓋所有欄位 (除 checksum 本身)
    pkt.checksum = calculateCRC16((const uint8_t*)&pkt, sizeof(RemotePacket) - sizeof(uint16_t));

    // 發射 LED 瞬閃
    digitalWrite(PIN_LED_STATUS, HIGH);

    // 透過序列埠輸出 JSON/Hex 供模擬器與上位機接收
    Serial.printf("[PKT #%u] Type:0x%02X State:%u Mask:0x%04X CRC:0x%04X\n",
                  pkt.seqNumber, pkt.packetType, pkt.systemState, pkt.buttonState, pkt.checksum);

    digitalWrite(PIN_LED_STATUS, LOW);
}

void setup() {
    Serial.begin(115200);
    while (!Serial && millis() < 1000);

    Serial.println(F("========================================"));
    Serial.println(F("  Industrial Remote Controller Initializing"));
    Serial.println(F("  Architecture: ESP32 + Interlock Safety"));
    Serial.println(F("========================================"));

    setupPins();
    setupDisplay();
}

void loop() {
    unsigned long now = millis();

    // 1. 讀取緊急停止 (E-Stop)
    // 假設常閉 (NC) 開關：按鍵按下時斷開 (電位為 LOW)
    bool estopTriggered = readPinActive(PIN_ESTOP);

    // 2. 讀取所有按鍵
    bool rawUp    = readPinActive(PIN_BTN_UP);
    bool rawDown  = readPinActive(PIN_BTN_DOWN);
    bool rawEast  = readPinActive(PIN_BTN_EAST);
    bool rawWest  = readPinActive(PIN_BTN_WEST);
    bool rawNorth = readPinActive(PIN_BTN_NORTH);
    bool rawSouth = readPinActive(PIN_BTN_SOUTH);
    bool rawStart = readPinActive(PIN_BTN_START);
    bool rawHorn  = readPinActive(PIN_BTN_HORN);

    // 3. 組合原始按鍵遮罩
    uint16_t rawMask = BTN_MASK_NONE;
    if (rawUp)    rawMask |= BTN_MASK_UP;
    if (rawDown)  rawMask |= BTN_MASK_DOWN;
    if (rawEast)  rawMask |= BTN_MASK_EAST;
    if (rawWest)  rawMask |= BTN_MASK_WEST;
    if (rawNorth) rawMask |= BTN_MASK_NORTH;
    if (rawSouth) rawMask |= BTN_MASK_SOUTH;
    if (rawStart) rawMask |= BTN_MASK_START;
    if (rawHorn)  rawMask |= BTN_MASK_HORN;
    if (estopTriggered) rawMask |= BTN_MASK_ESTOP;

    // 4. 工業級安全互鎖 (Interlock Protection)
    // 相反動作 (UP/DOWN, EAST/WEST, NORTH/SOUTH) 嚴禁同時觸發
    bool interlockError = false;
    uint16_t safeMask = rawMask;

    if (rawUp && rawDown) {
        interlockError = true;
        safeMask &= ~(BTN_MASK_UP | BTN_MASK_DOWN); // 強制解除對向輸出
    }
    if (rawEast && rawWest) {
        interlockError = true;
        safeMask &= ~(BTN_MASK_EAST | BTN_MASK_WEST);
    }
    if (rawNorth && rawSouth) {
        interlockError = true;
        safeMask &= ~(BTN_MASK_NORTH | BTN_MASK_SOUTH);
    }

    // 5. 系統安全狀態機 (Safety State Machine)
    if (estopTriggered) {
        currentState = STATE_ESTOP;
        safeMask = BTN_MASK_ESTOP; // 急停時只帶 ESTOP 旗標，動作一律歸零
        digitalWrite(PIN_LED_FAULT, HIGH);
    } else {
        digitalWrite(PIN_LED_FAULT, interlockError ? HIGH : LOW);

        if (currentState == STATE_ESTOP) {
            // 從急停解除後，強制進入待機模式，必須按 START 重新就緒
            currentState = STATE_STANDBY;
        } else if (currentState == STATE_STANDBY) {
            if (rawStart) {
                currentState = STATE_ARMED;
                Serial.println(F("[SYSTEM] START button detected. Remote ARMED!"));
            }
        } else {
            // ARMED 或 OPERATING 狀態
            if (interlockError) {
                currentState = STATE_ERROR;
            } else if ((safeMask & ~BTN_MASK_START) != 0) {
                currentState = STATE_OPERATING;
            } else {
                currentState = STATE_ARMED;
            }
        }
    }

    // 6. 決定傳送頻率與封包型態
    PacketType txType = PKT_HEARTBEAT;
    unsigned long txInterval = HEARTBEAT_INTERVAL_MS;

    if (currentState == STATE_ESTOP) {
        txType = PKT_ESTOP;
        txInterval = ACTIVE_TX_INTERVAL_MS;
    } else if (currentState == STATE_OPERATING) {
        txType = PKT_COMMAND;
        txInterval = ACTIVE_TX_INTERVAL_MS;
    }

    // 7. 定時發送無線封包
    if (now - lastTxTime >= txInterval) {
        lastTxTime = now;
        transmitPacket(safeMask, txType);
    }

    // 8. 定時刷新 OLED 螢幕 (約 20 FPS，50ms)
    if (now - lastDisplayTime >= 50) {
        lastDisplayTime = now;
        updateDisplay(rawMask, interlockError, estopTriggered);
    }
}
