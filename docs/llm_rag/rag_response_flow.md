# RAG Response Flow

LLM/RAG 기반 안내문 생성 흐름을 정리합니다.

---

## Flow

```text
카메라 영상 수신
→ YOLO 탐지
→ confidence 기준 확인
→ stable frame 조건 확인
→ Web Server 또는 Mission Manager가 탐지 결과 수신
→ RAG 문서 검색
→ LLM 안내문 생성
→ Web UI 출력
```

---

## Role Separation

| Module | Role |
|---|---|
| Mission Manager | 상태 전이, 로봇 명령, 파트너 호출 |
| YOLO | label, confidence, bbox 산출 |
| RAG | 등록 문서 검색 |
| LLM | 웹 UI용 설명문 생성 |
| Web UI | 운영자에게 안내문 표시 |

---

## TODO

- [ ] RAG DB path 확정
- [ ] Ollama model name 확정
- [ ] response JSON schema 정의
- [ ] timeout/fallback 응답 작성
