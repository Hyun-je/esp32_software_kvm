#include <Arduino.h>
#include "ble_hid/BleHid.h"
#include "serial_receiver/SerialReceiver.h"
#include "protocol/Protocol.h"

// -----------------------------------------------------------------------
// Globals
// -----------------------------------------------------------------------
SerialReceiver receiver(Serial);

// LED on IO8:
//   - forwarding ON  → LED steady ON
//   - forwarding OFF → LED OFF
//   - key packet received → brief OFF (30 ms) then restore to forwarding state
static const uint8_t  LED_PIN        = 8;
static const uint32_t LED_BLINK_MS   = 30;
static bool     _forwarding    = false;  // updated by EVT_FORWARDING_ON/OFF
static uint32_t _ledRestoreAt  = 0;     // when to restore LED after blink

// BLE connection state (tracked to print connect/disconnect messages once)
static bool _wasBleConnected = false;

// Key-stuck protection: if a KEY_DOWN was received but no KEY_UP arrives
// within this window (e.g. PC crashed), release all keys automatically.
static uint32_t _lastPacketMs = 0;
static bool _hasKeyDown = false;
static const uint32_t KEY_IDLE_TIMEOUT_MS = 500;

// Periodic BLE status broadcast so the PC always knows the current state
// even if it missed the initial connect/disconnect event.
static uint32_t _lastStatusMs = 0;
static const uint32_t STATUS_INTERVAL_MS = 10000;

// -----------------------------------------------------------------------
// setup
// -----------------------------------------------------------------------
void setup() {
    // LED pin setup (active-low: LOW = ON, HIGH = OFF)
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, HIGH);

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

    // ---- Periodic BLE status broadcast ----
    if (millis() - _lastStatusMs >= STATUS_INTERVAL_MS) {
        _lastStatusMs = millis();
        Serial.printf("[KVM] BLE status: %s\n", connected ? "connected" : "disconnected");
    }

    // ---- LED blink restore ----
    if (_ledRestoreAt && millis() >= _ledRestoreAt) {
        digitalWrite(LED_PIN, _forwarding ? LOW : HIGH);
        _ledRestoreAt = 0;
    }

    // ---- Key-stuck watchdog: release all if KEY_UP never arrived ----
    if (_hasKeyDown && (millis() - _lastPacketMs > KEY_IDLE_TIMEOUT_MS)) {
        bleHid.releaseAll();
        _hasKeyDown = false;
        Serial.println("[KVM] Idle timeout — released all keys.");
    }

    // ---- Process incoming serial packets ----
    Packet pkt = receiver.poll();
    if (!pkt.valid) {
        return;  // Nothing ready yet
    }

    _lastPacketMs = millis();

    Serial.printf("[KVM] Packet: type=0x%02X mod=0x%02X key=0x%02X\n",
                  pkt.eventType, pkt.modifier, pkt.keycode);

    // Forwarding state packets control the LED regardless of BLE connection
    if (pkt.eventType == EVT_FORWARDING_ON) {
        _forwarding = true;
        digitalWrite(LED_PIN, LOW);
        Serial.println("[KVM] Forwarding ON — LED on.");
        return;
    }
    if (pkt.eventType == EVT_FORWARDING_OFF) {
        _forwarding = false;
        digitalWrite(LED_PIN, HIGH);
        Serial.println("[KVM] Forwarding OFF — LED off.");
        return;
    }

    // Blink LED on key packets (OFF briefly, then restore)
    if (pkt.eventType == EVT_KEY_DOWN || pkt.eventType == EVT_KEY_UP
            || pkt.eventType == EVT_CONSUMER_KEY) {
        digitalWrite(LED_PIN, HIGH);
        _ledRestoreAt = millis() + LED_BLINK_MS;
    }

    if (!connected) {
        // Drop packet — iPhone not connected
        Serial.println("[KVM] BLE not connected; packet dropped.");
        return;
    }

    switch (pkt.eventType) {
        case EVT_KEY_DOWN:
            bleHid.sendKey(pkt.modifier, pkt.keycode);
            _hasKeyDown = true;
            break;

        case EVT_KEY_UP:
            bleHid.releaseAll();
            _hasKeyDown = false;
            break;

        case EVT_CONSUMER_KEY:
            bleHid.sendConsumer(static_cast<uint16_t>(pkt.keycode));
            break;

        case EVT_STATUS_REQUEST:
            Serial.printf("[KVM] BLE status: %s\n", connected ? "connected" : "disconnected");
            break;

        default:
            Serial.printf("[KVM] Unknown event type: 0x%02X\n", pkt.eventType);
            break;
    }
}
