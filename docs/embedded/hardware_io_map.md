# Hardware I/O Map

STM32 시나리오 객체의 핀맵과 입출력 정의를 정리합니다.

---

## Pin Map

| Signal | STM32 Pin | Direction | Description |
|---|---|---|---|
| Button A | TODO | Input | 절차 입력 버튼 |
| Button B | TODO | Input | 절차 입력 버튼 |
| Button C | TODO | Input | 절차 입력 버튼 |
| Button D | TODO | Input | 절차 입력 버튼 |
| LCD SDA | TODO | I2C | LCD data |
| LCD SCL | TODO | I2C | LCD clock |
| Buzzer | TODO | Output | 경고음 |
| LED Red | TODO | Output | 실패/위험 상태 |
| LED Yellow | TODO | Output | 진행 상태 |
| LED Green | TODO | Output | 성공 상태 |
| Joystick X | TODO | Analog | 조이스틱 X |
| Joystick Y | TODO | Analog | 조이스틱 Y |

---

## TODO

- [ ] 실제 보드 기준 핀맵 작성
- [ ] pull-up/pull-down 설정 기록
- [ ] debounce 기준 추가
- [ ] I2C LCD 주소 기록
