# Perception

[← Docs Home](../)

YOLO 기반 박스 탐지, 내부 객체 탐지, 모델 성능 비교, 이벤트 인터페이스를 정리합니다.

## On this page

- [1. Overview](#overview)
- [2. Detection Modes](#detection-modes)
- [3. YOLO Model Benchmark](#yolo-model-benchmark)
- [4. Confidence Policy](#confidence-policy)
- [5. Event Interface](#event-interface)
- [6. Data Flow](#data-flow)
- [7. Open Issues](#open-issues)

<a id="overview"></a>
## 1. Overview

Perception 모듈은 카메라 영상에서 박스와 내부 등록 객체를 탐지하고, Mission Manager가 처리할 수 있는 이벤트로 변환합니다.

<a id="detection-modes"></a>
## 2. Detection Modes

| Mode | Target | Description |
|---|---|---|
| `BOX_DETECTION_MODEL` | close box, open box | 탐색 중 박스 탐지 |
| `EXPLOSIVE_DETECTION_MODEL` | Empty, Bomb_A, Bomb_B | 박스 내부 객체 탐지 |
| `OFF` | none | 수동 조작 또는 비활성 상태 |

<a id="yolo-model-benchmark"></a>
## 3. YOLO Model Benchmark

![YOLO Benchmark](../assets/yolo_benchmark.png)

> TODO: `docs/assets/yolo_benchmark.png` 추가

| Model | mAP50-95 | Recall | Precision |
|---|---:|---:|---:|
| YOLO10m | 93.90% | 99.66% | 99.64% |
| YOLO11m | 94.11% | 99.71% | 99.89% |
| YOLO26m | 95.21% | 99.71% | 99.91% |

<a id="confidence-policy"></a>
## 4. Confidence Policy

| Level | Range | Handling |
|---|---:|---|
| Ignore | `< 0.35` | 이벤트 발생 안 함 |
| Low confidence | `0.35 ~ 0.65` | 재확인 안내, 상태 전이 없음 |
| High confidence | `>= 0.65` | `EXPLOSIVE_FOUND` 이벤트 발생 |

<a id="event-interface"></a>
## 5. Event Interface

```json
{
  "event_type": "EXPLOSIVE_FOUND",
  "robot_id": "wf1",
  "box_id": "box_001",
  "label": "Bomb_A",
  "confidence": 0.91,
  "bbox": [120, 80, 240, 190]
}
```

<a id="data-flow"></a>
## 6. Data Flow

```text
Camera Stream
  ↓
YOLO Inference
  ↓
label / confidence / bbox
  ↓
stable frame filter
  ↓
/yolo/event
  ↓
Mission Manager
```

<a id="open-issues"></a>
## 7. Open Issues

- [ ] 최종 YOLO 모델 경로 확정
- [ ] confidence threshold 실험값 업데이트
- [ ] stable frame 수 확정
- [ ] `/yolo/event` 메시지 타입 확정
