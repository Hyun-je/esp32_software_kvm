#pragma once
#include <Arduino.h>
#include "../protocol/Protocol.h"

/**
 * SerialReceiver
 *
 * Reads 6-byte packets from a Stream (HardwareSerial or HWCDC) and validates them.
 * Call poll() from loop(); it returns a Packet with valid=true when a
 * complete, checksummed packet has been received.
 */
class SerialReceiver {
public:
    explicit SerialReceiver(Stream& serial = Serial);

    /**
     * Read from the serial buffer and return the next complete packet.
     * Returns a Packet with valid=false if no full packet is ready yet.
     */
    Packet poll();

    /** Flush any buffered bytes (call on reconnect / reset). */
    void flush();

private:
    Stream& _serial;
    uint8_t         _buf[PKT_LEN];
    uint8_t         _pos;

    void _reset();
};
