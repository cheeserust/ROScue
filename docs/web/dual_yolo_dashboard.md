# Dual YOLO Dashboard

Detection 화면에서 WF1/WF2 YOLO 화면을 동시에 표시하는 구조를 정리합니다.

---

## Layout

```text
왼쪽 영역
 ├─ YOLO 화면 · wf1
 └─ YOLO 화면 · wf2

오른쪽 영역
 └─ 탐지 확정 및 절차 안내 패널
```

---

## Port Plan

| Robot | Debug Port | URL |
|---|---:|---|
| WF1 | `5055` | `http://<PC_IP>:5055/dashboard/debug` |
| WF2 | `5056` | `http://<PC_IP>:5056/dashboard/debug` |

---

## TODO

- [ ] 현재 HTML 파일명 기록
- [ ] port 환경변수 적용
- [ ] YOLO mode switch 버튼 연결
- [ ] 최신 RAG 안내문 패널 연결
