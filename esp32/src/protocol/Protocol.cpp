#include "Protocol.h"

namespace Protocol {

uint8_t checksum(uint8_t type, uint8_t mod, uint8_t keycode) {
    return type ^ mod ^ keycode;
}

Packet parse(const uint8_t* buf) {
    Packet pkt{};
    pkt.valid = false;

    if (buf[0] != PKT_START || buf[PKT_LEN - 1] != PKT_END) {
        return pkt;
    }

    uint8_t type    = buf[1];
    uint8_t mod     = buf[2];
    uint8_t keycode = buf[3];
    uint8_t csum    = buf[4];

    if (checksum(type, mod, keycode) != csum) {
        return pkt;
    }

    pkt.eventType = type;
    pkt.modifier  = mod;
    pkt.keycode   = keycode;
    pkt.valid     = true;
    return pkt;
}

} // namespace Protocol
