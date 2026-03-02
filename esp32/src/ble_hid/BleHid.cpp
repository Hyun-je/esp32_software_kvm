#include "BleHid.h"
#include <NimBLEDevice.h>

// Global singleton
BleHid bleHid;

BleHid::BleHid(const char* deviceName, const char* manufacturer, uint8_t batteryLevel)
    : _keyboard(deviceName, manufacturer, batteryLevel) {}

void BleHid::begin() {
    _keyboard.begin();
}

bool BleHid::isConnected() {
    return _keyboard.isConnected();
}

void BleHid::sendKey(uint8_t modifier, uint8_t keycode) {
    if (!_keyboard.isConnected()) return;

    // Build a 8-byte HID keyboard report:
    //   [modifier, 0x00, key1, key2, key3, key4, key5, key6]
    // ESP32-BLE-Keyboard exposes press(KeyboardKeycode) and
    // releaseAll(); use the raw report method for efficiency.
    uint8_t report[8] = {modifier, 0x00, keycode, 0, 0, 0, 0, 0};
    _keyboard.sendReport((KeyReport*)report);
}

void BleHid::releaseAll() {
    if (!_keyboard.isConnected()) return;
    _keyboard.releaseAll();
}

void BleHid::disconnect() {
    releaseAll();  // don't leave keys stuck before disconnecting
    NimBLEServer* pServer = NimBLEDevice::getServer();
    if (pServer) {
        uint8_t count = pServer->getConnectedCount();
        for (uint8_t i = 0; i < count; i++) {
            pServer->disconnect(pServer->getPeerInfo(i).getConnHandle());
        }
    }
    NimBLEDevice::stopAdvertising();
}

void BleHid::reconnect() {
    NimBLEDevice::startAdvertising();
}

void BleHid::sendConsumer(uint16_t usageId) {
    if (!_keyboard.isConnected()) return;
    // ESP32-BLE-Keyboard provides a MediaKeyReport path
    MediaKeyReport report = {0, 0};
    // Map common usage IDs to the library's bitmask format
    // (ESP32-BLE-Keyboard uses a 2-byte bitfield for consumer keys)
    // We forward the raw usage ID via the upper/lower bytes.
    report[0] = (uint8_t)(usageId & 0xFF);
    report[1] = (uint8_t)((usageId >> 8) & 0xFF);
    _keyboard.sendReport(&report);
    // Release immediately
    MediaKeyReport empty = {0, 0};
    _keyboard.sendReport(&empty);
}
