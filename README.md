# ESP32 Software KVM

USB/Unifying 키보드 입력을 PC에서 후킹하여 ESP32를 거쳐 BLE HID로 iPhone에 전달하는 소프트웨어 KVM.

```
[USB/Unifying 키보드]
        ↓ USB HID
      PC (Python)
        ↓ USB Serial (115200 baud)
      ESP32-C3
        ↓ BLE HID
      iPhone
```

---

## 환경

| 구성 요소 | 사양 |
|----------|------|
| PC OS | Windows / macOS |
| PC 언어 | Python 3.9+ |
| ESP32 보드 | ESP32-C3 DevKitM-1 |
| ESP32 빌드 | PlatformIO (Arduino framework) |
| BLE 스택 | NimBLE-Arduino |
| BLE HID | ESP32-BLE-Keyboard (T-vK fork) |

---

## 코드 구성

```
esp32_software_kvm/
├── pc/                          # PC 측 Python 프로그램
│   ├── requirements.txt
│   ├── main.py                  # CLI 진입점
│   ├── config.py                # 포트, 보드레이트, 패스스루 설정
│   ├── hook/
│   │   ├── base.py              # 키보드 훅 추상 인터페이스
│   │   ├── windows.py           # Windows pynput 훅
│   │   ├── macos.py             # macOS pynput 훅 (Quartz CGEventTap)
│   │   └── hid_keycodes.py      # OS 키코드 → HID Usage ID 변환 테이블
│   ├── protocol/
│   │   └── packet.py            # 6바이트 바이너리 패킷 인코딩/디코딩
│   └── serial_sender/
│       └── sender.py            # pyserial 기반 ESP32 통신 (자동 재연결)
└── esp32/                       # ESP32 펌웨어
    ├── platformio.ini
    └── src/
        ├── main.cpp
        ├── ble_hid/
        │   └── BleHid.h/.cpp    # BLE HID 키보드 래퍼
        ├── serial_receiver/
        │   └── SerialReceiver.h/.cpp  # 6바이트 패킷 수신 및 검증
        └── protocol/
            └── Protocol.h/.cpp  # 패킷 파싱 및 BleHid 호출
```

---

## 시리얼 프로토콜

PC ↔ ESP32 간 6바이트 바이너리 패킷:

```
| 0xAA | TYPE | MOD | KEYCODE | CHECKSUM | 0x55 |
```

- `TYPE`: `0x01` = KEY_DOWN, `0x02` = KEY_UP, `0x03` = CONSUMER_KEY
- `MOD`: HID 수정자 키 비트 플래그 (Ctrl/Shift/Alt/GUI)
- `KEYCODE`: HID Usage ID (PC에서 변환 완료)
- `CHECKSUM`: `TYPE ^ MOD ^ KEYCODE`

---

## 설치 및 실행

### PC (Python)

```bash
cd pc
pip install -r requirements.txt
python main.py
```

**주요 옵션:**

```
--port PORT         시리얼 포트 지정 (기본: 자동 탐색)
--baud BAUD         보드레이트 (기본: 115200)
--no-passthrough    로컬 OS로 키 전달 차단
--list-ports        사용 가능한 시리얼 포트 목록 출력
```

### ESP32 펌웨어

```bash
cd esp32
pio run --target upload
```

---

## 플랫폼별 주의사항

**macOS**
- 접근성 권한 필요: 시스템 설정 → 개인 정보 및 보안 → 접근성 → Python/터미널 허용
- 시리얼 포트: `/dev/cu.usbmodem*`

**Windows**
- 관리자 권한 불필요 (일부 보안 소프트웨어 오탐 가능)
- 시리얼 포트: `COMx`

**ESP32-C3**
- 내장 USB CDC 사용 (외부 USB-UART 칩 불필요)
- iPhone BLE 페어링 최초 1회 필요
- USB CDC + BLE 동시 사용 시 RAM(400KB) 여유 확인