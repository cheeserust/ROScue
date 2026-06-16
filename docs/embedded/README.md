# Embedded

[← Docs Home](../)

STM32 기반 시나리오 객체 인터페이스, Bomb_A/B 하드웨어 구성, IO map을 정리합니다.

## On this page

- [1. Overview](#overview)
- [2. Communication Architecture](#communication-architecture)
- [3. Bomb A/B Hardware](#bomb-ab-hardware)
- [4. IO Map](#io-map)
- [5. LED / LCD / Buzzer Policy](#led-lcd-buzzer-policy)
- [6. Firmware Structure](#firmware-structure)
- [7. Test Checklist](#test-checklist)

<a id="overview"></a>
## 1. Overview

Embedded 모듈은 STM32를 기반으로 버튼, LCD, LED, Buzzer, 조도센서, 조이스틱 등 시나리오 객체 인터페이스를 관리합니다.

<a id="communication-architecture"></a>
## 2. Communication Architecture

```text
STM32
  ↔ USB-Serial / UART / micro-ROS
Raspberry Pi 4
  ↔ ROS 2
Central Server PC
```

개발 초기에는 USB-Serial/UART를 우선 사용하고, 필요 시 CAN으로 확장합니다.

<a id="bomb-ab-hardware"></a>
## 3. Bomb A/B Hardware

![Bomb A/B Hardware](../assets/stm32_bomb_ab.png)

> TODO: `docs/assets/stm32_bomb_ab.png` 추가

| Component | Role |
|---|---|
| Button A/B/C/D | 입력 버튼 |
| LCD | 카운트다운 및 상태 표시 |
| LED | 단계별 상태 표시 |
| Buzzer | 경고음 출력 |
| Light Sensor | 특정 조건 감지 |
| Joystick | 상하좌우 조작 |
| STM32 | 메인 제어기 |

<a id="io-map"></a>
## 4. IO Map

| Pin | Device | Direction | Note |
|---|---|---|---|
| TODO | Button A | Input | pull-up/down 확인 |
| TODO | Button B | Input |  |
| TODO | LCD SDA | I2C |  |
| TODO | LCD SCL | I2C |  |
| TODO | Buzzer | Output | PWM 가능 |
| TODO | LED Red | Output |  |

<a id="led-lcd-buzzer-policy"></a>
## 5. LED / LCD / Buzzer Policy

| Output | Meaning |
|---|---|
| RED | 카운트다운 시작 또는 실패 |
| YELLOW | 진행 중 또는 성공 |
| GREEN | 단계별 성공 |
| LCD | countdown, ready, safe, fail 표시 |
| Buzzer | 경고음 또는 실패음 |

<a id="firmware-structure"></a>
## 6. Firmware Structure

```text
embedded/stm32/
├── Core/
├── Drivers/
├── Inc/
├── Src/
└── README.md
```

<a id="test-checklist"></a>
## 7. Test Checklist

- [ ] 버튼 입력 debounce 확인
- [ ] LCD 주소 확인
- [ ] LED 색상 매핑 확인
- [ ] Buzzer PWM 출력 확인
- [ ] UART/USB-Serial packet 송수신 확인
- [ ] 실패/성공 상태 전이 확인
