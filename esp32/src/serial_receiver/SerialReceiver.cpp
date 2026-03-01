#include "SerialReceiver.h"
#include "../protocol/Protocol.h"

SerialReceiver::SerialReceiver(Stream& serial)
    : _serial(serial), _pos(0) {
    memset(_buf, 0, PKT_LEN);
}

Packet SerialReceiver::poll() {
    Packet empty{};
    empty.valid = false;

    while (_serial.available()) {
        uint8_t byte = (uint8_t)_serial.read();

        if (_pos == 0) {
            // Wait for start byte
            if (byte != PKT_START) {
                continue;
            }
        }

        _buf[_pos++] = byte;

        if (_pos == PKT_LEN) {
            // Attempt to parse the complete packet
            Packet pkt = Protocol::parse(_buf);
            _reset();
            if (pkt.valid) {
                return pkt;
            }
            // Invalid packet (bad end byte or checksum) — discard and resync
        }
    }

    return empty;
}

void SerialReceiver::flush() {
    while (_serial.available()) {
        _serial.read();
    }
    _reset();
}

void SerialReceiver::_reset() {
    _pos = 0;
    memset(_buf, 0, PKT_LEN);
}
