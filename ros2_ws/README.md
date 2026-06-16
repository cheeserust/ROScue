# ros2_ws

ROS 2 workspace입니다.

---

## Expected Structure

```text
ros2_ws/
└── src/
    ├── roscue_bringup/
    ├── roscue_mission_manager/
    ├── roscue_interfaces/
    ├── roscue_navigation/
    ├── roscue_perception/
    ├── roscue_manipulation/
    └── roscue_web_bridge/
```

---

## Build

```bash
colcon build
source install/setup.bash
```

---

## TODO

- [ ] 실제 패키지명 확정
- [ ] launch 파일 목록 작성
- [ ] message/action/service 정의 추가
