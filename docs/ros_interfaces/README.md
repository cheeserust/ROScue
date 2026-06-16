# ROS Interfaces

[← Docs Home](../)

ROScue에서 사용하는 ROS 2 topic, service, action 인터페이스를 정리합니다.

## On this page

- [1. Namespace Rule](#namespace-rule)
- [2. Topics](#topics)
- [3. Services](#services)
- [4. Actions](#actions)
- [5. Messages](#messages)
- [6. Event Examples](#event-examples)

<a id="namespace-rule"></a>
## 1. Namespace Rule

```text
/<robot_ns>/cmd_vel
/<robot_ns>/odom
/<robot_ns>/scan
/<robot_ns>/amcl_pose
/<robot_ns>/navigate_to_pose
```

Example:

```text
/wf1/cmd_vel
/wf2/cmd_vel
/pinky/map
```

<a id="topics"></a>
## 2. Topics

| Topic | Direction | Description |
|---|---|---|
| `/map` | Pinky → Server → WF1/WF2 | SLAM map |
| `/map_metadata` | Pinky → Server → WF1/WF2 | Map metadata |
| `/clicked_point` | RViz/Pinky → Server | 수동 지정 좌표 |
| `/wf1/goal_pose` | Server → WF1 | WF1 목표 좌표 |
| `/wf2/goal_pose` | Server → WF2 | WF2 목표 좌표 |
| `/wf1/amcl_pose` | WF1 → Server | WF1 현재 위치 |
| `/wf2/amcl_pose` | WF2 → Server | WF2 현재 위치 |
| `/yolo/event` | YOLO → Mission Manager | YOLO event |
| `/mission/state` | Mission Manager → Web UI | 미션 상태 |
| `/mission/emergency_stop` | Web UI → Mission Manager | 긴급 정지 |

<a id="services"></a>
## 3. Services

| Service | Description |
|---|---|
| `/mission/start` | 미션 시작 |
| `/mission/stop` | 미션 정지 |
| `/mission/manual_done` | 수동 처리 완료 |
| `/llm_rag/request_notice` | RAG 안내문 요청 |

<a id="actions"></a>
## 4. Actions

| Action | Description |
|---|---|
| `/<robot_ns>/navigate_to_pose` | Nav2 목표 이동 |
| `/<robot_ns>/follow_target` | YOLO 기반 비주얼 서보 접근 |
| `/<robot_ns>/open_box_cover` | 박스 뚜껑 개방 |
| `/<robot_ns>/arm_manual_control` | 수동 조작 모드 |

<a id="messages"></a>
## 5. Messages

> TODO: `roscue_interfaces` 패키지 확정 후 message 정의 추가

<a id="event-examples"></a>
## 6. Event Examples

```json
{
  "event_type": "BOX_FOUND",
  "robot_id": "wf1",
  "confidence": 0.87,
  "label": "close_box"
}
```

```json
{
  "event_type": "EXPLOSIVE_FOUND",
  "robot_id": "wf2",
  "box_id": "box_001",
  "label": "Bomb_A",
  "confidence": 0.91
}
```
