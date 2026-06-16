# ROS 2 Workspace

ROScue의 ROS 2 패키지를 보관하는 workspace입니다.

## Expected Packages

```text
ros2_ws/src/
├── roscue_bringup/
├── roscue_mission_manager/
├── roscue_interfaces/
├── roscue_navigation/
├── roscue_perception/
├── roscue_manipulation/
└── roscue_web_bridge/
```

## Build

```bash
cd ros2_ws
colcon build
source install/setup.bash
```
