# Setup

ROScue 개발 환경 설치 및 기본 설정 문서입니다.

---

## Target Environment

| Item | Version / Note |
|---|---|
| OS | Ubuntu 24.04 or TODO |
| ROS | ROS 2 Jazzy |
| Python | ROS 2: Python 3.12 or distribution default / LeRobot 환경 별도 관리 필요 |
| Robot | TurtleBot3 Waffle 계열 / Pinky / WF1 / WF2 |
| AI Server | Central Server PC |

---

## Basic ROS 2 Workspace

```bash
cd ros2_ws
colcon build
source install/setup.bash
```

---

## Environment Variables

```bash
export TURTLEBOT3_MODEL=waffle
export ROS_DOMAIN_ID=10
```

로봇별 domain은 [ROS Domain & Namespace](architecture/ros_domain_namespace.md)를 참고합니다.

---

## TODO

- [ ] 실제 OS 버전 확정
- [ ] ROS 2 Jazzy 설치 명령 추가
- [ ] TurtleBot3 패키지 설치 명령 추가
- [ ] YOLO/LeRobot/RAG 의존성 분리 정리
- [ ] STM32 toolchain 설치법 추가
