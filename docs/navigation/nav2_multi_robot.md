# Nav2 Multi-Robot

WF1/WF2 다중 로봇 Nav2 실행 및 goal 전송 구조를 정리합니다.

---

## Goal Action

```text
/wf1/navigate_to_pose
/wf2/navigate_to_pose
```

---

## Example Goal

```bash
ros2 action send_goal /wf1/navigate_to_pose nav2_msgs/action/NavigateToPose \
"{pose: {header: {frame_id: 'map'}, pose: {position: {x: 1.2, y: -0.5, z: 0.0}, orientation: {z: 0.0, w: 1.0}}}, behavior_tree: ''}" \
--feedback
```

---

## Rules

- goal pose는 `map` 좌표계 기준이어야 합니다.
- YOLO/카메라 좌표는 TF 변환 후 `map` 좌표로 변환해야 합니다.
- Nav2 주행 중 별도 `/cmd_vel` publisher와 충돌하지 않도록 합니다.
- 다중 로봇에서는 namespace와 TF frame id를 반드시 분리합니다.

---

## TODO

- [ ] WF1/WF2 Nav2 launch 파일 연결
- [ ] cancel_navigation 정책 작성
- [ ] partner summon 위치 계산법 추가
- [ ] recovery behavior 정리
