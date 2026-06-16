# Runbook

[← Docs Home](../)

시연 및 데모 실행 순서를 정리합니다.

## On this page

- [1. Pre-check](#pre-check)
- [2. Start Central Server](#start-central-server)
- [3. Start Pinky Mapping](#start-pinky-mapping)
- [4. Start WF1 / WF2](#start-wf1-wf2)
- [5. Start YOLO Servers](#start-yolo-servers)
- [6. Start Web UI](#start-web-ui)
- [7. Demo Sequence](#demo-sequence)
- [8. Shutdown](#shutdown)

<a id="pre-check"></a>
## 1. Pre-check

- [ ] 배터리 상태 확인
- [ ] 로봇별 IP 확인
- [ ] ROS_DOMAIN_ID 확인
- [ ] 카메라 스트림 확인
- [ ] LiDAR `/scan` 확인
- [ ] `/tf`, `/odom`, `/cmd_vel` 타입 확인

<a id="start-central-server"></a>
## 2. Start Central Server

```bash
cd ros2_ws
source install/setup.bash
ros2 launch roscue_bringup central_server.launch.py
```

<a id="start-pinky-mapping"></a>
## 3. Start Pinky Mapping

```bash
export ROS_DOMAIN_ID=13
ros2 launch roscue_bringup pinky_mapping.launch.py
```

<a id="start-wf1-wf2"></a>
## 4. Start WF1 / WF2

```bash
export ROS_DOMAIN_ID=14
ros2 launch roscue_bringup robot.launch.py robot_ns:=wf1
```

```bash
export ROS_DOMAIN_ID=15
ros2 launch roscue_bringup robot.launch.py robot_ns:=wf2
```

<a id="start-yolo-servers"></a>
## 5. Start YOLO Servers

```bash
DEBUG_PORT=5055 ROBOT_NAME=wf1 python3 yolo_server.py
DEBUG_PORT=5056 ROBOT_NAME=wf2 python3 yolo_server.py
```

<a id="start-web-ui"></a>
## 6. Start Web UI

```bash
cd web
python3 web_server.py
```

<a id="demo-sequence"></a>
## 7. Demo Sequence

```text
1. SLAM 시작
2. 지도 생성 및 저장
3. 미션 시작
4. 박스 탐색
5. 박스 접근
6. 박스 개방
7. 내부 탐지
8. 파트너 호출
9. Dual manual control
10. 완료 후 복귀
```

<a id="shutdown"></a>
## 8. Shutdown

```bash
# TODO: 종료 스크립트 확정 후 작성
```
