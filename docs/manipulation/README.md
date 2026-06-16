# Manipulation

[← Docs Home](../)

박스 개방, 모방학습 기반 매니퓰레이션, 리더-팔로워 수동 조작 구조를 정리합니다.

## On this page

- [1. Overview](#overview)
- [2. Box Open Motion Sequence](#box-open-motion-sequence)
- [3. Imitation Learning System](#imitation-learning-system)
- [4. Robustness Strategy](#robustness-strategy)
- [5. Leader-Follower Control](#leader-follower-control)
- [6. Failure Handling](#failure-handling)

<a id="overview"></a>
## 1. Overview

Manipulation 모듈은 박스 개방과 dual manual 대응을 담당합니다.

<a id="box-open-motion-sequence"></a>
## 2. Box Open Motion Sequence

![Box Open Manual](../assets/box_open_manual.png)

> TODO: `docs/assets/box_open_manual.png` 추가

```text
접근 위치 조정
→ 손잡이 인식
→ 엔드이펙터 정렬
→ 전진 및 파지
→ 상승 동작
→ 지정 위치 이동
→ 파지 해제 및 복귀
```

<a id="imitation-learning-system"></a>
## 3. Imitation Learning System

![Imitation Learning System](../assets/imitation_learning_system.png)

> TODO: `docs/assets/imitation_learning_system.png` 추가

```text
cam_1 / cam_2
  ↓
Raspberry Pi
  ↓
PC Inference Server
  ↓
LeRobot Policy
  ↓
Manipulator Command
```

<a id="robustness-strategy"></a>
## 4. Robustness Strategy

| Method | Description |
|---|---|
| Domain Randomization | 조명, 배경, 색상, 질감, 센서 노이즈 변화 |
| State Perturbation | 비정상 초기 상태에서 복구하는 데이터 수집 |
| DAgger | 사용자 개입 데이터를 누적하여 어려운 상태 대응 성능 개선 |

<a id="leader-follower-control"></a>
## 5. Leader-Follower Control

Dual manual 단계에서는 운영자가 Web UI와 리더암을 통해 두 로봇팔을 수동 조작합니다.

```text
Operator Leader Arm
  ↓
PC Control Server
  ↓
WF1 / WF2 Follower Arm
```

<a id="failure-handling"></a>
## 6. Failure Handling

| Failure | Handling |
|---|---|
| OPEN timeout | 박스 `OPEN_FAILED`, `EXPLORE` 복귀 |
| camera lost | 동작 중지, 운영자 확인 |
| policy error | fallback manual mode |
| excessive delay | 추론 서버 상태 확인 |
