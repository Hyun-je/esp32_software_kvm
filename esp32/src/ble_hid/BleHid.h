#pragma once
#include <BleCombo.h>

/**
 * BleComboEx
 *
 * Minimal subclass of BleCombo that promotes the protected methods
 * needed for raw HID report access to public scope.
 */
class BleComboEx : public BleCombo {
public:
    using BleCombo::BleCombo;
    using BleCombo::begin;
    using BleCombo::sendReport;
    using BleCombo::releaseAll;
};

/**
 * BleHid
 *
 * Thin wrapper around ESP32-BLE-Combo that provides the interface used
 * by the KVM firmware (keyboard only — mouse unused):
 *   - begin()           — start BLE advertising
 *   - isConnected()     — check if an iOS/iPadOS device is paired
 *   - sendKey()         — press a key (modifier + HID keycode)
 *   - releaseAll()      — release all keys
 *   - sendConsumer()    — send a consumer/media key usage ID
 */
class BleHid {
public:
    BleHid(const char* deviceName  = "ESP32 Keyboard",
           const char* manufacturer = "Espressif",
           uint8_t     batteryLevel = 100);

    void begin();
    bool isConnected();

    /**
     * Press a key.
     * @param modifier  HID modifier byte (see Protocol.h MOD_* constants)
     * @param keycode   HID Usage ID (keyboard page 0x07)
     */
    void sendKey(uint8_t modifier, uint8_t keycode);

    /** Release all currently held keys. */
    void releaseAll();

    /**
     * Send a Consumer Control key (media keys).
     * @param usageId  HID Consumer page usage (e.g. 0xE9 = Volume Up)
     */
    void sendConsumer(uint16_t usageId);

private:
    BleComboEx _keyboard;
};

// Singleton-style global instance
extern BleHid bleHid;
