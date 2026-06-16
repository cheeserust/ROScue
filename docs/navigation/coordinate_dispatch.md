# Coordinate Dispatch

중앙 서버가 목표 좌표를 저장하고 가까운 로봇에게 할당하는 구조를 정리합니다.

---

## Dispatch Flow

```text
1. Pinky 수동 주행으로 map 작성
2. RViz2 clicked_point 또는 랜덤 좌표 발행
3. 중앙 서버가 좌표 DB에 저장
4. WF1/WF2 현재 위치 수신
5. 목표 좌표와 각 로봇 간 거리 계산
6. 더 가까운 로봇에게 goal_pose 전달
```

---

## Distance Rule

```python
distance = sqrt((goal_x - robot_x)**2 + (goal_y - robot_y)**2)
```

---

## Topics

| Topic | Description |
|---|---|
| `/clicked_point` | 사용자가 지정한 좌표 |
| `/wf1/amcl_pose` | WF1 현재 위치 |
| `/wf2/amcl_pose` | WF2 현재 위치 |
| `/wf1/goal_pose` | WF1 목표 좌표 |
| `/wf2/goal_pose` | WF2 목표 좌표 |

---

## TODO

- [ ] 좌표 DB 스키마 작성
- [ ] 랜덤 좌표 생성 조건 정리
- [ ] obstacle/costmap 고려 방식 추가
- [ ] goal assignment 실패 처리 추가
