# ROS 2 Interfaces

ROScue에서 사용하는 topic, service, action 인터페이스를 정리합니다.

> 실제 메시지 타입은 `roscue_interfaces` 패키지 구현 후 업데이트합니다.

---

## Topics

| Topic | Direction | Type | Description |
|---|---|---|---|
| `/map` | Pinky → Server → WF1/WF2 | `nav_msgs/msg/OccupancyGrid` | SLAM map |
| `/map_metadata` | Pinky → Server → WF1/WF2 | `nav_msgs/msg/MapMetaData` | map metadata |
| `/clicked_point` | RViz/Pinky → Server | `geometry_msgs/msg/PointStamped` | 수동 지정 좌표 |
| `/wf1/goal_pose` | Server → WF1 | `geometry_msgs/msg/PoseStamped` | WF1 목표 좌표 |
| `/wf2/goal_pose` | Server → WF2 | `geometry_msgs/msg/PoseStamped` | WF2 목표 좌표 |
| `/wf1/amcl_pose` | WF1 → Server | `geometry_msgs/msg/PoseWithCovarianceStamped` | WF1 현재 위치 |
| `/wf2/amcl_pose` | WF2 → Server | `geometry_msgs/msg/PoseWithCovarianceStamped` | WF2 현재 위치 |
| `/yolo/event` | YOLO → Mission Manager | TODO | BOX_FOUND, EMPTY, EXPLOSIVE_FOUND 등 |
| `/mission/state` | Mission Manager → Web UI | TODO | 미션 상태 |
| `/mission/emergency_stop` | Web UI → Mission Manager | TODO | 긴급 정지 |
| `/<robot_ns>/heartbeat` | Robot → Server | TODO | 로봇 생존 신호 |

---

## Actions

| Action | Description |
|---|---|
| `/<robot_ns>/navigate_to_pose` | Nav2 목표 위치 이동 |
| `/<robot_ns>/follow_target` | YOLO 기반 비주얼 서보 접근 |
| `/<robot_ns>/open_box_cover` | 상자 뚜껑 개방 |
| `/<robot_ns>/arm_manual_control` | 수동 조작 모드 |

---

## Services

| Service | Description |
|---|---|
| `/mission/start` | 미션 시작 |
| `/mission/stop` | 미션 정지 |
| `/mission/manual_done` | 운영자 처리 완료 |
| `/llm_rag/safety_notice` | RAG 기반 안내문 요청 |
