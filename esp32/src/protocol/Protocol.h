#pragma once
#include <stdint.h>

// Packet byte positions
constexpr uint8_t PKT_START    = 0xAA;
constexpr uint8_t PKT_END      = 0x55;
constexpr uint8_t PKT_LEN      = 6;

// Event types
constexpr uint8_t EVT_KEY_DOWN        = 0x01;
constexpr uint8_t EVT_KEY_UP          = 0x02;
constexpr uint8_t EVT_CONSUMER_KEY    = 0x03;
constexpr uint8_t EVT_STATUS_REQUEST  = 0x04;
constexpr uint8_t EVT_FORWARDING_ON   = 0x05;
constexpr uint8_t EVT_FORWARDING_OFF  = 0x06;

// Modifier bitmasks (HID spec, Keyboard/Keypad page)
constexpr uint8_t MOD_LEFT_CTRL   = 0x01;
constexpr uint8_t MOD_LEFT_SHIFT  = 0x02;
constexpr uint8_t MOD_LEFT_ALT    = 0x04;
constexpr uint8_t MOD_LEFT_GUI    = 0x08;
constexpr uint8_t MOD_RIGHT_CTRL  = 0x10;
constexpr uint8_t MOD_RIGHT_SHIFT = 0x20;
constexpr uint8_t MOD_RIGHT_ALT   = 0x40;
constexpr uint8_t MOD_RIGHT_GUI   = 0x80;

struct Packet {
    uint8_t eventType;
    uint8_t modifier;
    uint8_t keycode;
    bool    valid;
};

namespace Protocol {
    /**
     * Compute XOR checksum: TYPE ^ MOD ^ KEYCODE
     */
    uint8_t checksum(uint8_t type, uint8_t mod, uint8_t keycode);

    /**
     * Parse a raw 6-byte buffer into a Packet.
     * Sets packet.valid = false on any error.
     */
    Packet parse(const uint8_t* buf);
}
