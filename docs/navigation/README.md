# Navigation

[← Docs Home](../)

Pinky SLAM mapping, 좌표 발행, WF1/WF2 Nav2 주행 구조를 정리합니다.

## On this page

- [1. Overview](#overview)
- [2. Pinky SLAM Mapping](#pinky-slam-mapping)
- [3. Coordinate Dispatch](#coordinate-dispatch)
- [4. Nav2 Multi-Robot Control](#nav2-multi-robot-control)
- [5. Map Sharing Policy](#map-sharing-policy)
- [6. Topics](#topics)
- [7. Troubleshooting Notes](#troubleshooting-notes)

<a id="overview"></a>
## 1. Overview

Navigation 모듈은 Pinky가 생성한 map을 기준으로 WF1/WF2가 목표 좌표로 이동하는 구조입니다.

```text
Pinky SLAM
  ↓
/map, /map_metadata
  ↓
Central Server DB
  ↓
coordinate dispatch
  ↓
/wf1/goal_pose or /wf2/goal_pose
```

<a id="pinky-slam-mapping"></a>
## 2. Pinky SLAM Mapping

```text
1. Pinky 수동 주행
2. slam_toolbox 실행
3. /map, /map_metadata 생성
4. 중앙 서버로 map 전달
5. WF1/WF2가 동일 map 사용
```

<a id="coordinate-dispatch"></a>
## 3. Coordinate Dispatch

좌표 발행 방식:

| Method | Description |
|---|---|
| `clicked_point` | RViz2 GUI에서 publish point 지정 |
| random coordinate | map 내 랜덤 좌표 발행 |
| detected object pose | YOLO/센서 기반 의심 위치 좌표 등록 |

Dispatch rule:

```text
1. 목표 좌표 생성
2. WF1/WF2 현재 위치 수신
3. 각 로봇과 목표 좌표 간 거리 계산
4. 더 가까운 로봇에게 goal 전달
```

<a id="nav2-multi-robot-control"></a>
## 4. Nav2 Multi-Robot Control

```text
/wf1/navigate_to_pose
/wf2/navigate_to_pose
```

각 로봇은 고유 namespace와 frame prefix를 사용해야 합니다.

```text
map
 ├── wf1/odom
 │    └── wf1/base_link
 └── wf2/odom
      └── wf2/base_link
```

<a id="map-sharing-policy"></a>
## 5. Map Sharing Policy

- Pinky가 생성한 map을 기준 map으로 사용합니다.
- WF1/WF2의 개별 map server는 제거합니다.
- domain_bridge를 통해 중앙 서버가 map을 전달합니다.

<a id="topics"></a>
## 6. Topics

| Topic | Description |
|---|---|
| `/map` | SLAM map |
| `/map_metadata` | map metadata |
| `/clicked_point` | RViz2 clicked point |
| `/wf1/goal_pose` | WF1 target pose |
| `/wf2/goal_pose` | WF2 target pose |
| `/wf1/amcl_pose` | WF1 current pose |
| `/wf2/amcl_pose` | WF2 current pose |
| `/cancel_navigation` | Nav2 cancel command |

<a id="troubleshooting-notes"></a>
## 7. Troubleshooting Notes

| Issue | Check |
|---|---|
| goal이 안 감 | goal frame_id가 `map`인지 확인 |
| 로봇 둘의 TF가 섞임 | `base_link`, `odom` frame id 충돌 확인 |
| map이 중복 발행됨 | WF1/WF2 map server 제거 여부 확인 |
| `/cmd_vel` 무시됨 | `Twist` vs `TwistStamped` 타입 확인 |
