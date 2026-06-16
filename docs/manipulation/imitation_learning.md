# Imitation Learning

LeRobot 기반 박스 개방 policy 추론 구조를 정리합니다.

---

## System Flow

```text
cam_1 / cam_2
    ↓
Raspberry Pi
    ↓ 영상/관절 데이터 전송
PC Inference Server
    ↓ policy action
Robot Manipulator
```

---

## Robustness Strategy

| Method | Description |
|---|---|
| Domain Randomization | 조명, 배경, 객체 색상, 질감, 센서 노이즈를 변화시키며 데이터 수집 |
| State Perturbation | 불안정한 초기 상태에서 복구하는 데이터 수집 |
| DAgger | 사용자 개입 데이터를 누적하여 어려운 상태 대응 성능 개선 |

---

## TODO

- [ ] LeRobot 실행 환경 기록
- [ ] Python 버전 충돌 해결법 링크
- [ ] dataset format 정리
- [ ] policy checkpoint 위치 정리
- [ ] inference latency 측정
