#ifndef RECEIVER_H
#define RECEIVER_H

#include <stdint.h>
#include "protocol.h"

// ==========================================
// 工業天車接收主機引擎 (Crane Receiver Engine)
// 參考標準：Schneider eXLhoist & ARC FLEX 接收機安全規範
// ==========================================

enum ReceiverState : uint8_t {
    RX_STATE_DISENGAGED = 0,   // 未啟動 / 主接觸器開路
    RX_STATE_ENGAGED    = 1,   // 正常聯鎖 / 主迴路通電
    RX_STATE_ESTOP      = 2,   // 緊急停止跳脫
    RX_STATE_LOST_LINK  = 3,   // 斷訊失聯 (看門狗超時)
};

class ReceiverEngine {
public:
    explicit ReceiverEngine(uint32_t expectedSystemId = 0x41524331, uint32_t watchdogTimeoutMs = 500)
        : m_systemId(expectedSystemId),
          m_watchdogTimeoutMs(watchdogTimeoutMs),
          m_state(RX_STATE_DISENGAGED),
          m_relays(RELAY_NONE),
          m_lastPacketTimeMs(0),
          m_packetsReceived(0),
          m_crcErrors(0),
          m_watchdogTrips(0) {}

    // 處理傳入的無線封包
    bool processPacket(const RemotePacket& pkt, uint32_t nowMs, bool upperLimitSensor = false) {
        // 1. 同步標頭驗證
        if (pkt.sync1 != PROTOCOL_SYNC_BYTE1 || pkt.sync2 != PROTOCOL_SYNC_BYTE2) {
            return false;
        }

        // 2. 系統識別碼配對驗證 (防跨台串動)
        if (pkt.systemId != m_systemId) {
            return false;
        }

        // 3. CRC-16-CCITT 完整性校驗
        uint16_t expectedCrc = calculateCRC16((const uint8_t*)&pkt, sizeof(RemotePacket) - sizeof(uint16_t));
        if (pkt.checksum != expectedCrc) {
            m_crcErrors++;
            return false;
        }

        // 4. 重設看門狗計時器
        m_lastPacketTimeMs = nowMs;
        m_packetsReceived++;

        // 5. 緊急停止優先權檢查 (最高安全等級)
        if (pkt.packetType == PKT_ESTOP || (pkt.buttonState & BTN_MASK_ESTOP)) {
            m_state = RX_STATE_ESTOP;
            m_relays = RELAY_NONE; // 切斷主接觸器與所有動作繼電器
            return true;
        }

        // 6. 啟動程序 (開機按鈕)
        if (m_state == RX_STATE_DISENGAGED || m_state == RX_STATE_LOST_LINK) {
            if (pkt.buttonState & BTN_MASK_START) {
                m_state = RX_STATE_ENGAGED;
            } else {
                m_relays = RELAY_NONE;
                return true;
            }
        }

        // 7. 若在 ESTOP 狀態，唯有遙控器回歸正常且按 START 才能解除
        if (m_state == RX_STATE_ESTOP) {
            if ((pkt.buttonState & BTN_MASK_START) && !(pkt.buttonState & BTN_MASK_ESTOP)) {
                m_state = RX_STATE_ENGAGED;
            } else {
                m_relays = RELAY_NONE;
                return true;
            }
        }

        // 8. 正常聯鎖運作 (驅動繼電器)
        if (m_state == RX_STATE_ENGAGED) {
            uint16_t out = RELAY_MAIN; // 主接觸器常時閉合

            // 動作對向互鎖 (雙重保護：發射端做過，接收端二次驗證防呆)
            bool upActive   = (pkt.buttonState & BTN_MASK_UP)   && !(pkt.buttonState & BTN_MASK_DOWN);
            bool downActive = (pkt.buttonState & BTN_MASK_DOWN) && !(pkt.buttonState & BTN_MASK_UP);
            bool eastActive = (pkt.buttonState & BTN_MASK_EAST) && !(pkt.buttonState & BTN_MASK_WEST);
            bool westActive = (pkt.buttonState & BTN_MASK_WEST) && !(pkt.buttonState & BTN_MASK_EAST);
            bool northActive= (pkt.buttonState & BTN_MASK_NORTH)&& !(pkt.buttonState & BTN_MASK_SOUTH);
            bool southActive= (pkt.buttonState & BTN_MASK_SOUTH)&& !(pkt.buttonState & BTN_MASK_NORTH);

            // 衝頂極限開關保護 (Upper Limit Switch)
            // 若吊鉤碰觸到頂端極限開關，禁止上升 (UP)，但允許下降 (DOWN) 脫困
            if (upActive && !upperLimitSensor) {
                out |= RELAY_UP;
            }
            if (downActive) {
                out |= RELAY_DOWN;
            }
            if (eastActive)  out |= RELAY_EAST;
            if (westActive)  out |= RELAY_WEST;
            if (northActive) out |= RELAY_NORTH;
            if (southActive) out |= RELAY_SOUTH;
            if (pkt.buttonState & BTN_MASK_HORN) out |= RELAY_HORN;

            m_relays = out;
        }

        return true;
    }

    // 週期性心跳檢視 (Watchdog Tick)
    void tick(uint32_t nowMs) {
        if (m_state == RX_STATE_ENGAGED) {
            if (nowMs - m_lastPacketTimeMs > m_watchdogTimeoutMs) {
                // 超過看門狗時限，自動判定斷訊跳脫
                m_state = RX_STATE_LOST_LINK;
                m_relays = RELAY_NONE;
                m_watchdogTrips++;
            }
        }
    }

    // 狀態存取器
    ReceiverState getState() const { return m_state; }
    uint16_t getRelays() const { return m_relays; }
    bool isMainEngaged() const { return (m_relays & RELAY_MAIN) != 0; }
    uint32_t getPacketsReceived() const { return m_packetsReceived; }
    uint32_t getCrcErrors() const { return m_crcErrors; }
    uint32_t getWatchdogTrips() const { return m_watchdogTrips; }

private:
    uint32_t m_systemId;
    uint32_t m_watchdogTimeoutMs;
    ReceiverState m_state;
    uint16_t m_relays;
    uint32_t m_lastPacketTimeMs;
    uint32_t m_packetsReceived;
    uint32_t m_crcErrors;
    uint32_t m_watchdogTrips;
};

#endif // RECEIVER_H
