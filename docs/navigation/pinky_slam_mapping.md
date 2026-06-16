# Pinky SLAM Mapping

Pinky Mapping Robot의 SLAM 지도 생성 과정을 정리합니다.

---

## Flow

```text
1. 운영자가 Web UI에서 SLAM 시작
2. Pinky Mapping Robot 수동 주행
3. slam_toolbox 실행
4. /map, /map_metadata 생성
5. 중앙 서버로 지도 전달
6. 지도 저장 후 WF1/WF2 navigation 준비
```

---

## Main Topics

| Topic | Direction | Description |
|---|---|---|
| `/driving_command` | Server → Pinky | SLAM start/stop |
| `/map` | Pinky → Server | SLAM map |
| `/map_metadata` | Pinky → Server | map metadata |
| `/clicked_point` | RViz2 → Server | 수동 목표 좌표 |

---

## TODO

- [ ] 실제 slam_toolbox launch 명령 추가
- [ ] map 저장 경로 정리
- [ ] Pinky ROS_DOMAIN_ID 확정
- [ ] map bridge 설정 추가
