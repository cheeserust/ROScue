# Runbook

ROScue 데모 실행 순서를 정리합니다.

---

## 1. Pre-Check

```text
[ ] Central Server PC 네트워크 확인
[ ] Pinky, WF1, WF2 전원 확인
[ ] ROS_DOMAIN_ID 확인
[ ] camera stream 확인
[ ] LiDAR /scan 확인
[ ] emergency stop 동작 확인
```

---

## 2. Start Central Server

```bash
cd ros2_ws
source install/setup.bash
ros2 launch roscue_bringup central_server.launch.py
```

---

## 3. Start Pinky Mapping Robot

```bash
export ROS_DOMAIN_ID=13
ros2 launch roscue_bringup pinky_mapping.launch.py
```

---

## 4. Start WF1/WF2

```bash
export ROS_DOMAIN_ID=14
ros2 launch roscue_bringup robot.launch.py robot_ns:=wf1
```

```bash
export ROS_DOMAIN_ID=15
ros2 launch roscue_bringup robot.launch.py robot_ns:=wf2
```

---

## 5. Start Web UI

```bash
cd web
python3 web_server.py
```

---

## 6. Demo Sequence

```text
1. SLAM 시작
2. 지도 작성 완료
3. 미션 시작
4. 박스 탐지
5. 박스 접근
6. 박스 개방
7. 내부 객체 탐지
8. 파트너 호출
9. DUAL_MANUAL 전환
10. 운영자 완료 입력
11. 탐색 복귀 또는 미션 종료
```
