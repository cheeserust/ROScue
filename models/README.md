# models

YOLO, LeRobot 등 모델 가중치를 보관합니다.

---

## Expected Structure

```text
models/
├── README.md
├── yolo/
│   └── best.pt
└── lerobot/
    └── policy_checkpoint/
```

---

## Rule

- 대용량 파일은 Git LFS 사용을 검토합니다.
- 모델 파일명에 버전과 학습 날짜를 포함합니다.
