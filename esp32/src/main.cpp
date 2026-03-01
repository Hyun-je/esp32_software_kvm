#include <Arduino.h>
#include "ble_hid/BleHid.h"
#include "serial_receiver/SerialReceiver.h"
#include "protocol/Protocol.h"

// -----------------------------------------------------------------------
// Globals
// -----------------------------------------------------------------------
SerialReceiver receiver(Serial);

// BLE connection state (tracked to print connect/disconnect messages once)
static bool _wasBleConnected = false;

// -----------------------------------------------------------------------
// setup
// -----------------------------------------------------------------------
void setup() {
    // USB CDC Serial @ 115200 — matches PC sender config
    Serial.begin(115200);

    // Give the USB CDC stack a moment to enumerate on host
    delay(500);

    Serial.println("[KVM] Initialising BLE HID keyboard...");
    bleHid.begin();
    Serial.println("[KVM] BLE advertising started. Waiting for iPhone to pair...");
}

// -----------------------------------------------------------------------
// loop
// -----------------------------------------------------------------------
void loop() {
    // ---- BLE connection status change ----
    bool connected = bleHid.isConnected();
    if (connected && !_wasBleConnected) {
        Serial.println("[KVM] BLE connected.");
        _wasBleConnected = true;
    } else if (!connected && _wasBleConnected) {
        Serial.println("[KVM] BLE disconnected.");
        _wasBleConnected = false;
    }

    // ---- Process incoming serial packets ----
    Packet pkt = receiver.poll();
    if (!pkt.valid) {
        return;  // Nothing ready yet
    }

    Serial.printf("[KVM] Packet: type=0x%02X mod=0x%02X key=0x%02X\n",
                  pkt.eventType, pkt.modifier, pkt.keycode);

    if (!connected) {
        // Drop packet — iPhone not connected
        Serial.println("[KVM] BLE not connected; packet dropped.");
        return;
    }

    switch (pkt.eventType) {
        case EVT_KEY_DOWN:
            bleHid.sendKey(pkt.modifier, pkt.keycode);
            break;

        case EVT_KEY_UP:
            bleHid.releaseAll();
            break;

        case EVT_CONSUMER_KEY: {
            // keycode holds the low byte; for now single-byte consumer IDs suffice
            bleHid.sendConsumer(static_cast<uint16_t>(pkt.keycode));
            break;
        }

        default:
            Serial.printf("[KVM] Unknown event type: 0x%02X\n", pkt.eventType);
            break;
    }
}
