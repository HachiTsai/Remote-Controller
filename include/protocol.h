#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>

// ==========================================
// 工業遙控通訊協定規範 (RF Protocol)
// ==========================================

#define PROTOCOL_SYNC_BYTE1 0x53  // 'S'
#define PROTOCOL_SYNC_BYTE2 0x45  // 'E'

// 封包類型
enum PacketType : uint8_t {
    PKT_HEARTBEAT = 0x01,  // 待機心跳封包
    PKT_COMMAND   = 0x02,  // 動作控制命令封包
    PKT_ESTOP     = 0xFF   // 緊急停止強制封包
};

// 遙控器系統安全狀態
enum SystemState : uint8_t {
    STATE_STANDBY   = 0,   // 待機模式
    STATE_ARMED     = 1,   // 啟動/聯鎖就緒
    STATE_OPERATING = 2,   // 正在操作按鈕
    STATE_ESTOP     = 3,   // 緊急停止
    STATE_ERROR     = 4    // 對向互鎖錯誤
};

// 按鈕狀態遮罩位元 (Bitmask)
enum ButtonMask : uint16_t {
    BTN_MASK_NONE   = 0x0000,
    BTN_MASK_UP     = (1 << 0),  // 0x0001 (一段速)
    BTN_MASK_DOWN   = (1 << 1),  // 0x0002 (一段速)
    BTN_MASK_EAST   = (1 << 2),  // 0x0004 (一段速)
    BTN_MASK_WEST   = (1 << 3),  // 0x0008 (一段速)
    BTN_MASK_SOUTH  = (1 << 4),  // 0x0010 (一段速)
    BTN_MASK_NORTH  = (1 << 5),  // 0x0020 (一段速)
    BTN_MASK_START  = (1 << 6),  // 0x0040 (啟動)
    BTN_MASK_HORN   = (1 << 7),  // 0x0080 (電笛)
    BTN_MASK_ESTOP  = (1 << 8),  // 0x0100 (急停觸發)
    // 二段速擴充位元 (2nd Speed Detent Masks)
    BTN_MASK_UP_2   = (1 << 9),  // 0x0200 (UP 二速重按)
    BTN_MASK_DOWN_2 = (1 << 10), // 0x0400 (DOWN 二速重按)
    BTN_MASK_EAST_2 = (1 << 11), // 0x0800 (EAST 二速重按)
    BTN_MASK_WEST_2 = (1 << 12), // 0x1000 (WEST 二速重按)
    BTN_MASK_SOUTH_2= (1 << 13), // 0x2000 (SOUTH 二速重按)
    BTN_MASK_NORTH_2= (1 << 14), // 0x4000 (NORTH 二速重按)
    BTN_MASK_SPEED2 = (1 << 15), // 0x8000 (通用二速旗標)
};

// 接收端繼電器輸出遮罩 (Relay Outputs)
enum RelayMask : uint16_t {
    RELAY_NONE        = 0x0000,
    RELAY_UP          = (1 << 0),  // K1: 主鉤上升 (一速)
    RELAY_DOWN        = (1 << 1),  // K2: 主鉤下降 (一速)
    RELAY_EAST        = (1 << 2),  // K3: 小車東向 (一速)
    RELAY_WEST        = (1 << 3),  // K4: 小車西向 (一速)
    RELAY_NORTH       = (1 << 4),  // K5: 大車北向 (一速)
    RELAY_SOUTH       = (1 << 5),  // K6: 大車南向 (一速)
    RELAY_HORN        = (1 << 6),  // K7: 警報蜂鳴器/電笛
    RELAY_MAIN        = (1 << 7),  // K8: 主接觸器 (Main Contactor)
    RELAY_SPEED_2     = (1 << 8),  // K9: 二速加速繼電器 (2nd Speed Inverter/Resistance Relay)
    RELAY_BRAKE_DELAY = (1 << 9),  // 煞車延遲保護指示 (Brake Delay in effect)
};

// 嚴格位元組對齊的工業遙控封包結構
#pragma pack(push, 1)
struct RemotePacket {
    uint8_t  sync1;          // 同步標頭 1 (0x53)
    uint8_t  sync2;          // 同步標頭 2 (0x45)
    uint32_t systemId;       // 32-bit 安全配對碼
    uint16_t seqNumber;      // 滾動序號 (防止重放攻擊)
    uint8_t  packetType;     // 封包類型 (PacketType)
    uint8_t  systemState;    // 系統狀態 (SystemState)
    uint16_t buttonState;    // 按鍵狀態遮罩 (ButtonMask)
    uint8_t  batteryPercent; // 電量百分比 (0-100%)
    uint16_t checksum;       // CRC-16-CCITT 校驗碼
};
#pragma pack(pop)

// 簡易快速 CRC-16-CCITT 計算
inline uint16_t calculateCRC16(const uint8_t* data, uint16_t length) {
    uint16_t crc = 0xFFFF;
    for (uint16_t i = 0; i < length; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (uint8_t j = 0; j < 8; j++) {
            if (crc & 0x8000) {
                crc = (crc << 1) ^ 0x1021;
            } else {
                crc <<= 1;
            }
        }
    }
    return crc;
}

#endif // PROTOCOL_H
