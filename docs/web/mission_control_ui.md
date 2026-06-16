# Mission Control UI

운영자 Web UI의 미션 제어 기능을 정리합니다.

---

## Required Controls

| Control | API | Description |
|---|---|---|
| Mission Start | `POST /api/command` | 자율 탐색 시작 |
| Mission Stop | `POST /api/command` | 미션 정지 |
| Manual Done | `POST /api/manual_done` | 운영자 처리 완료 |
| Emergency Stop | `POST /api/emergency_stop` | 긴급 정지 |
| Unknown Report | `POST /api/user_report` | Bomb_C 등 미등록 객체 수동 보고 |

---

## Required Displays

```text
- 미션 상태
- WF1/WF2 상태
- box registry
- explosive queue
- 최신 YOLO event
- 최신 LLM/RAG 안내문
- heartbeat 상태
```

---

## TODO

- [ ] 실제 API path와 통일
- [ ] 상태 카드 디자인 캡처 추가
- [ ] 수동 조작 버튼 정의
- [ ] error toast/message 정책 작성
