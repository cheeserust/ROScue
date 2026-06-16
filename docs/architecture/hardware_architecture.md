# Hardware Architecture

ROScue 하드웨어 구성도를 정리합니다.

---

## Components

| Component | Role |
|---|---|
| High-Performance PC | 관제, AI 서버, LLM/RAG, 모방학습 추론 서버 |
| Raspberry Pi 4 | 상위 제어기, ROS 2 통신, 카메라/LiDAR 데이터 처리 |
| OpenCR | 하위 제어기, Dynamixel 및 주행 하드웨어 제어 |
| Camera | 상황 관찰, YOLO 입력 영상 스트림 |
| LiDAR | 공간 정보, SLAM 및 Nav2 입력 |
| OMX Arm | 박스 개방, 수동 조작, 리더-팔로워 제어 |
| Dynamixel | 주행 구동 및 엔코더 상태 피드백 |
| STM32 | 등록 객체 인터페이스, 버튼/LCD/LED/Buzzer/센서 제어 |

---

## Communication Summary

```text
Camera / LiDAR / Manipulator
        ↓ USB / TTL / ROS 2
Raspberry Pi 4
        ↓ UART / Micro-ROS / USB-Serial
OpenCR or STM32
        ↓ TTL / Dynamixel Protocol / GPIO
Actuator / Sensor / Scenario Object
```

---

## TODO

- [ ] 실제 배선도 이미지 추가
- [ ] 전원 구성 정리
- [ ] 12V 외부 전원, 컨버터, 배터리 사양 작성
- [ ] 각 로봇별 카메라 위치 사진 추가
