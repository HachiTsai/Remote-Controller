#include <cassert>
#include <iostream>
#include "../include/protocol.h"

// 驗證安全互鎖模擬函式
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

int main() {
    std::cout << "[TEST] Running Protocol & Safety Unit Tests...\n";

    // 1. 測試封包結構緊密對齊
    std::cout << "  - Checking RemotePacket size & packing... ";
    assert(sizeof(RemotePacket) == 15);
    std::cout << "PASSED (15 Bytes packed)\n";

    // 2. 測試 CRC16 校驗碼計算
    std::cout << "  - Checking CRC16 calculation... ";
    RemotePacket pkt{};
    pkt.sync1 = PROTOCOL_SYNC_BYTE1;
    pkt.sync2 = PROTOCOL_SYNC_BYTE2;
    pkt.systemId = 0x41524331;
    pkt.seqNumber = 1;
    pkt.packetType = PKT_COMMAND;
    pkt.systemState = STATE_OPERATING;
    pkt.buttonState = BTN_MASK_UP;
    pkt.batteryPercent = 100;
    
    uint16_t crc1 = calculateCRC16((const uint8_t*)&pkt, sizeof(RemotePacket) - sizeof(uint16_t));
    assert(crc1 != 0);

    // 修改任意一個位元，CRC 必須改變
    pkt.seqNumber = 2;
    uint16_t crc2 = calculateCRC16((const uint8_t*)&pkt, sizeof(RemotePacket) - sizeof(uint16_t));
    assert(crc1 != crc2);
    std::cout << "PASSED\n";

    // 3. 測試對向互鎖 (Interlock)
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

    std::cout << "[SUCCESS] All Protocol & Safety Unit Tests Passed!\n";
    return 0;
}
