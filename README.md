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
│   ├── config.py                # 포트, 보드레이트, 토글 단축키 설정
│   ├── gui/
│   │   └── status_window.py     # tkinter 상태창 (ESP32/BLE/FWD LED 인디케이터)
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

## 주요 기능

### 포워딩 토글 (Ctrl+Alt+K)
- **Ctrl+Alt+K** 단축키로 ESP32 포워딩을 켜거나 끔
- 포워딩 ON: PC 키보드 입력이 억제되어 iPhone으로만 전달됨
- 포워딩 OFF: PC 키보드가 정상 동작
- 상태 전환 시 ESP32에 `EVT_FORWARDING_ON/OFF` 패킷을 전송하여 LED와 동기화

### 종료 단축키 (Ctrl+Alt+X)
- **Ctrl+Alt+X** 단축키로 포워딩을 즉시 OFF로 전환한 뒤 0.5초 후 프로그램 종료
- 포워딩 중에도 안전하게 종료 가능 (키 고착 방지 처리 포함)

### 상태창 (tkinter GUI)
- 항상 최상단에 표시되는 소형 상태창 (추가 의존성 없음, stdlib tkinter 사용)
- 3개 LED 인디케이터:
  - **ESP32**: 시리얼 연결 상태 (초록/빨강)
  - **BLE**: iPhone BLE 연결 상태 (초록/빨강/회색=미확인)
  - **FWD**: 포워딩 활성화 여부 (초록/회색)

### CapsLock → Ctrl+Space 리맵
- CapsLock 입력을 Ctrl+Space로 변환하여 iOS의 한/영 전환 트리거
- iPhone에서 별도 설정 없이 CapsLock 키로 입력 언어 전환 가능

### ESP32 IO8 LED 인디케이터
- 포워딩 ON: LED 상시 점등
- 포워딩 OFF: LED 소등
- 키 패킷 수신 시: 30ms 깜빡임 후 복구

### 키 고착 방지
- KEY_DOWN 이후 500ms 내에 KEY_UP이 오지 않으면 자동으로 모든 키 해제
- 프로그램 종료 시 눌린 상태의 모든 키를 자동으로 KEY_UP 처리

---

## 시리얼 프로토콜

PC ↔ ESP32 간 6바이트 바이너리 패킷:

```
| 0xAA | TYPE | MOD | KEYCODE | CHECKSUM | 0x55 |
```

- `TYPE`: 이벤트 타입
  - `0x01` = KEY_DOWN
  - `0x02` = KEY_UP
  - `0x03` = CONSUMER_KEY
  - `0x04` = STATUS_REQUEST (ESP32 BLE 상태 응답 요청)
  - `0x05` = FORWARDING_ON (포워딩 활성화 알림)
  - `0x06` = FORWARDING_OFF (포워딩 비활성화 알림)
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
--port PORT         시리얼 포트 지정 (기본: VID/PID로 자동 탐색)
--baud BAUD         보드레이트 (기본: 115200)
--verbose, -v       DEBUG 로그 활성화 (키 이벤트 출력)
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
- LED 핀: IO8 (active-low)
