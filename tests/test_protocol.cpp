#include <cassert>
#include <iostream>
#include "../include/protocol.h"
#include "../include/receiver.h"

// 驗證安全互鎖模擬函式 (發射端)
uint16_t applyInterlock(uint16_t rawMask, bool& interlockError) {
    interlockError = false;
    uint16_t safeMask = rawMask;

    if ((rawMask & BTN_MASK_UP) && (rawMask & BTN_MASK_DOWN)) {
        interlockError = true;
        safeMask &= ~(BTN_MASK_UP | BTN_MASK_DOWN);
    }
    if ((rawMask & BTN_MASK_EAST) && (rawMask & BTN_MASK_WEST)) {
        interlockError = true;
        safeMask &= ~(BTN_MASK_EAST | BTN_MASK_WEST);
    }
    if ((rawMask & BTN_MASK_NORTH) && (rawMask & BTN_MASK_SOUTH)) {
        interlockError = true;
        safeMask &= ~(BTN_MASK_NORTH | BTN_MASK_SOUTH);
    }
    return safeMask;
}

// 輔助函式：建立已簽章的有效測試封包
RemotePacket createValidPacket(uint32_t systemId, uint16_t seq, uint8_t type, uint8_t state, uint16_t buttons) {
    RemotePacket pkt{};
    pkt.sync1 = PROTOCOL_SYNC_BYTE1;
    pkt.sync2 = PROTOCOL_SYNC_BYTE2;
    pkt.systemId = systemId;
    pkt.seqNumber = seq;
    pkt.packetType = type;
    pkt.systemState = state;
    pkt.buttonState = buttons;
    pkt.batteryPercent = 95;
    pkt.checksum = calculateCRC16((const uint8_t*)&pkt, sizeof(RemotePacket) - sizeof(uint16_t));
    return pkt;
}

int main() {
    std::cout << "[TEST] Running Protocol & Safety Unit Tests...\n";

    // 1. 測試封包結構緊密對齊
    std::cout << "  - Checking RemotePacket size & packing... ";
    assert(sizeof(RemotePacket) == 15);
    std::cout << "PASSED (15 Bytes packed)\n";

    // 2. 測試 CRC16 校驗碼計算
    std::cout << "  - Checking CRC16 calculation... ";
    RemotePacket pkt = createValidPacket(0x53595331, 1, PKT_COMMAND, STATE_OPERATING, BTN_MASK_UP);
    uint16_t crc1 = pkt.checksum;
    assert(crc1 != 0);

    // 修改任意一個位元，CRC 必須改變
    pkt.seqNumber = 2;
    uint16_t crc2 = calculateCRC16((const uint8_t*)&pkt, sizeof(RemotePacket) - sizeof(uint16_t));
    assert(crc1 != crc2);
    std::cout << "PASSED\n";

    // 3. 測試發射端對向互鎖 (Interlock)
    std::cout << "  - Checking Safety Interlock (UP + DOWN collision)... ";
    bool err = false;
    uint16_t safe = applyInterlock(BTN_MASK_UP | BTN_MASK_DOWN, err);
    assert(err == true);
    assert((safe & BTN_MASK_UP) == 0);
    assert((safe & BTN_MASK_DOWN) == 0);
    std::cout << "PASSED\n";

    std::cout << "  - Checking Single Direction (EAST only)... ";
    err = false;
    safe = applyInterlock(BTN_MASK_EAST, err);
    assert(err == false);
    assert(safe == BTN_MASK_EAST);
    std::cout << "PASSED\n";

    // 4. 測試天車接收主機引擎 (ReceiverEngine)
    std::cout << "\n[TEST] Running Crane Receiver Safety Engine Tests...\n";
    ReceiverEngine rx(0x53595331, 500); // 500ms Watchdog

    // 初始狀態確認
    assert(rx.getState() == RX_STATE_DISENGAGED);
    assert(rx.getRelays() == RELAY_NONE);

    // 4.1 拒絕系統識別碼不符的封包
    std::cout << "  - Checking System ID mismatch rejection... ";
    RemotePacket alienPkt = createValidPacket(0xDEADBEEF, 1, PKT_HEARTBEAT, STATE_STANDBY, BTN_MASK_NONE);
    assert(rx.processPacket(alienPkt, 100) == false);
    assert(rx.getPacketsReceived() == 0);
    std::cout << "PASSED\n";

    // 4.2 拒絕 CRC 損壞的封包
    std::cout << "  - Checking CRC error detection... ";
    RemotePacket corruptPkt = createValidPacket(0x53595331, 1, PKT_HEARTBEAT, STATE_STANDBY, BTN_MASK_NONE);
    corruptPkt.checksum ^= 0x1234;
    assert(rx.processPacket(corruptPkt, 110) == false);
    assert(rx.getCrcErrors() == 1);
    std::cout << "PASSED\n";

    // 4.3 正常啟動流程 (按下 START 按鈕)
    std::cout << "  - Checking Start Sequence & Main Contactor engagement... ";
    RemotePacket startPkt = createValidPacket(0x53595331, 2, PKT_COMMAND, STATE_ARMED, BTN_MASK_START);
    assert(rx.processPacket(startPkt, 200) == true);
    assert(rx.getState() == RX_STATE_ENGAGED);
    assert(rx.isMainEngaged() == true);
    assert((rx.getRelays() & RELAY_MAIN) != 0);
    std::cout << "PASSED\n";

    // 4.4 動作控制與接收端二次對向互鎖防呆
    std::cout << "  - Checking Motion Control & Secondary Interlock... ";
    RemotePacket upPkt = createValidPacket(0x53595331, 3, PKT_COMMAND, STATE_OPERATING, BTN_MASK_UP);
    rx.processPacket(upPkt, 250);
    assert((rx.getRelays() & RELAY_UP) != 0);
    assert((rx.getRelays() & RELAY_DOWN) == 0);

    // 若封包同時帶有 UP + DOWN (模擬惡意或故障封包)，接收端必須全數抑制
    RemotePacket conflictPkt = createValidPacket(0x53595331, 4, PKT_COMMAND, STATE_OPERATING, BTN_MASK_UP | BTN_MASK_DOWN);
    rx.processPacket(conflictPkt, 300);
    assert((rx.getRelays() & RELAY_UP) == 0);
    assert((rx.getRelays() & RELAY_DOWN) == 0);

    // 4.4.1 動作中遇 CRC 損壞封包，必須立即阻斷動作繼電器 (防止失控暴衝)
    std::cout << "  - Checking Motion cutoff on CRC error during active drive... ";
    rx.processPacket(upPkt, 310);
    assert((rx.getRelays() & RELAY_UP) != 0); // 動作中
    RemotePacket corruptDrivePkt = createValidPacket(0x53595331, 5, PKT_COMMAND, STATE_OPERATING, BTN_MASK_UP);
    corruptDrivePkt.checksum ^= 0xABCD;
    assert(rx.processPacket(corruptDrivePkt, 320) == false);
    // 動作繼電器必須立即切斷 (不可維持舊的 UP 命令)，但主接觸器保持吸合待命
    assert((rx.getRelays() & RELAY_UP) == 0);
    assert((rx.getRelays() & RELAY_MAIN) != 0);
    std::cout << "PASSED\n";

    // 4.5 衝頂極限開關 (Upper Limit Switch) 防撞保護
    std::cout << "  - Checking Upper Limit Switch protection... ";
    // 極限開關觸發時，禁止上升
    rx.processPacket(upPkt, 350, /* upperLimitSensor= */ true);
    assert((rx.getRelays() & RELAY_UP) == 0);
    // 但允許下降脫困
    RemotePacket downPkt = createValidPacket(0x53595331, 5, PKT_COMMAND, STATE_OPERATING, BTN_MASK_DOWN);
    rx.processPacket(downPkt, 400, /* upperLimitSensor= */ true);
    assert((rx.getRelays() & RELAY_DOWN) != 0);
    std::cout << "PASSED\n";

    // 4.6 看門狗超時斷訊安全跳脫 (Watchdog Timeout Fail-safe)
    std::cout << "  - Checking 500ms Watchdog Timeout Fail-Safe... ";
    // 在 400ms 時有封包，現在時間推進到 950ms (> 500ms 未收封包)
    rx.tick(950);
    assert(rx.getState() == RX_STATE_LOST_LINK);
    assert(rx.getRelays() == RELAY_NONE); // 主接觸器與所有繼電器強制釋放
    assert(rx.getWatchdogTrips() == 1);
    std::cout << "PASSED\n";

    // 4.7 緊急停止 (E-STOP) 測試
    std::cout << "  - Checking E-STOP tripping... ";
    // 先重新啟動
    rx.processPacket(startPkt, 1000);
    assert(rx.getState() == RX_STATE_ENGAGED);
    // 送出急停封包
    RemotePacket estopPkt = createValidPacket(0x53595331, 6, PKT_ESTOP, STATE_ESTOP, BTN_MASK_ESTOP);
    rx.processPacket(estopPkt, 1050);
    assert(rx.getState() == RX_STATE_ESTOP);
    assert(rx.getRelays() == RELAY_NONE);
    std::cout << "PASSED\n";

    std::cout << "\n[SUCCESS] All Protocol & Receiver Safety Tests Passed 100%!\n";
    return 0;
}
