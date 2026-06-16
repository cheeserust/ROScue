# Bomb A/B Hardware

Bomb_A/B 시나리오 객체의 하드웨어 구성을 정리합니다.

---

## Components

| Component | Role |
|---|---|
| Button A/B/C/D | 입력 버튼 |
| LCD | 카운트다운 및 상태 표시 |
| LED | 단계별 상태 표시 |
| Buzzer | 경고음 출력 |
| Light Sensor | 특정 조건 감지 |
| Joystick | 상하좌우 조작 |
| STM32 | 메인 제어기 |

---

## LED Status Example

| Color | Meaning |
|---|---|
| RED | 카운트다운 시작 또는 실패 |
| YELLOW | 진행 중 또는 성공 |
| GREEN | 단계별 성공 |

---

## TODO

- [ ] Bomb_A 실제 하드웨어 사진 추가
- [ ] Bomb_B 실제 하드웨어 사진 추가
- [ ] 버튼 순서와 RAG 문서 연결
- [ ] LCD 메시지 정의
