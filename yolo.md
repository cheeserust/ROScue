## YOLO Object Detection

ROScue는 YOLO 기반 객체 탐지를 통해 폭발물 상자와 내부 모의 폭발물 객체를 인식합니다.

<div align="center">

<img src="./docs/assets/yolo_model_comparison.png" width="85%">

</div>

---

### Detection Modes

| Mode | Purpose |
|---|---|
| `BOX_DETECTION_MODEL` | 탐색 중 폭발물 의심 상자 탐지 |
| `EXPLOSIVE_DETECTION_MODEL` | 박스 내부 모의 폭발물 객체 탐지 |

---

### Model Performance Comparison

| Model | mAP50-95 | Recall | Precision |
|---|---:|---:|---:|
| YOLO10m | 93.90% | 99.66% | 99.64% |
| YOLO11m | 94.11% | 99.71% | 99.89% |
| YOLO26m | 95.21% | 99.71% | 99.91% |

---

### Model Selection

YOLO26m은 비교 모델 중 가장 높은 mAP50-95와 Precision을 기록했습니다.  
따라서 본 프로젝트에서는 폭발물 상자 탐지의 안정성을 높이기 위해 YOLO26m을 주요 후보 모델로 선정했습니다.

다만 실제 로봇 적용에서는 정확도뿐만 아니라 추론 속도, GPU 사용량, 통신 지연, 실시간성도 함께 고려해야 합니다.
