# Troubleshooting

[← Docs Home](../)

프로젝트 진행 중 발생한 주요 문제와 해결 방법을 한 페이지에 정리합니다.

## On this page

- [1. Namespace / Domain Bridge](#namespace-domain-bridge)
- [2. Map Server Duplication](#map-server-duplication)
- [3. ROS2-LeRobot Python Conflict](#ros2-lerobot-python-conflict)
- [4. cmd_vel Type Mismatch](#cmd-vel-type-mismatch)
- [5. Imitation Learning Latency](#imitation-learning-latency)
- [6. YOLO Low Confidence](#yolo-low-confidence)
- [7. Checklist](#checklist)

<a id="namespace-domain-bridge"></a>
## 1. Namespace / Domain Bridge

### Problem

여러 로봇이 동일 topic/frame을 사용하면 topic, TF, map이 충돌합니다.

### Solution

```text
/pinky
/wf1
/wf2
```

로봇별 namespace를 분리하고, 필요한 topic만 domain_bridge로 중앙 서버에 전달합니다.

<a id="map-server-duplication"></a>
## 2. Map Server Duplication

### Problem

WF1/WF2에서 map server를 각각 실행하면 Pinky map과 충돌할 수 있습니다.

### Solution

- Pinky의 `/map`을 기준 map으로 사용합니다.
- WF1/WF2 map server를 제거합니다.
- domain_bridge로 동일 map을 전달합니다.

<a id="ros2-lerobot-python-conflict"></a>
## 3. ROS2-LeRobot Python Conflict

### Problem

ROS 2와 LeRobot이 요구하는 Python 버전 또는 dependency가 충돌합니다.

### Solution

- 실행 환경을 분리합니다.
- 필요한 LeRobot 모듈만 프로젝트 패키지 내부로 복사합니다.
- 추론 서버와 ROS 2 노드를 process 단위로 분리합니다.

<a id="cmd-vel-type-mismatch"></a>
## 4. cmd_vel Type Mismatch

### Problem

Jazzy 환경에서 TurtleBot3 `/cmd_vel` subscriber가 `TwistStamped`를 요구하는데, PC 코드가 `Twist`를 publish하면 로봇이 움직이지 않습니다.

### Solution

```text
geometry_msgs/msg/TwistStamped 사용
```

확인 명령:

```bash
ros2 topic info -v /wf2/cmd_vel
```

<a id="imitation-learning-latency"></a>
## 5. Imitation Learning Latency

### Problem

네트워크 지연 또는 추론 서버 지연으로 제어 안정성이 떨어질 수 있습니다.

### Solution

- 독립망 구성
- 추론 서버와 제어 노드 분리
- 지연 허용 범위 조정
- 안전 정지 timeout 추가

<a id="yolo-low-confidence"></a>
## 6. YOLO Low Confidence

### Problem

조명, 시점, 데이터 부족으로 confidence가 낮거나 오탐이 발생합니다.

### Solution

- low/high confidence threshold 분리
- stable frame 조건 추가
- 조명/각도별 데이터 추가 수집
- low confidence에서는 상태 전이를 발생시키지 않음

<a id="checklist"></a>
## 7. Checklist

- [ ] `ros2 topic list`에서 namespace 확인
- [ ] `ros2 topic info -v /cmd_vel` 타입 확인
- [ ] `/tf` frame id 중복 확인
- [ ] `/map` publisher 개수 확인
- [ ] YOLO 서버 포트 중복 확인
- [ ] Web UI API 응답 확인
