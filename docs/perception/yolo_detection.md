# YOLO Detection

ROScue의 YOLO 탐지 구조를 정리합니다.

---

## Detection Modes

| Mode | Target |
|---|---|
| `BOX_DETECTION_MODEL` | close box, open box |
| `EXPLOSIVE_DETECTION_MODEL` | Empty, Bomb_A, Bomb_B |
| `OFF` | 탐지 정지 |

---

## YOLO Output

```json
{
  "label": "Bomb_A",
  "confidence": 0.91,
  "bbox": [120, 80, 240, 190]
}
```

---

## Stable Frame Rule

```text
같은 label이 N프레임 이상 유지될 때만 Mission Manager event로 확정한다.
```

---

## TODO

- [ ] 실제 모델 경로 정리
- [ ] label list 확정
- [ ] confidence threshold 확정
- [ ] low confidence 처리 정책 작성
- [ ] 카메라 스트림 경로 정리
