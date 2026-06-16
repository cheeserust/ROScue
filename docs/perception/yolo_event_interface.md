# YOLO Event Interface

YOLO 탐지 결과를 Mission Manager가 처리할 수 있는 event로 변환하는 구조를 정리합니다.

---

## Event Example

```json
{
  "event_type": "EXPLOSIVE_FOUND",
  "robot_id": "wf1",
  "box_id": "box_001",
  "label": "Bomb_A",
  "confidence": 0.91,
  "bbox": [120, 80, 240, 190],
  "timestamp": 1730000000.0
}
```

---

## Event Types

| Event | Description |
|---|---|
| `BOX_FOUND` | 박스 발견 |
| `BOX_COVER_OPEN` | 뚜껑 열린 상태 확인 |
| `EMPTY` | 내부 등록 객체 없음 |
| `EXPLOSIVE_FOUND` | 등록 객체 후보 탐지 |
| `LOW_CONFIDENCE` | 신뢰도 부족, 재확인 필요 |
| `UNKNOWN_OBJECT` | 미등록 객체 수동 보고 |

---

## TODO

- [ ] ROS message type 정의
- [ ] `/yolo/event` schema 확정
- [ ] cooldown 정책 작성
- [ ] duplicate event filtering 구현
