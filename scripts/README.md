# scripts

실행, 테스트, 배포, 로그 수집용 스크립트를 보관합니다.

---

## Expected Files

```text
scripts/
├── README.md
├── start_server.sh
├── start_pinky.sh
├── start_wf1.sh
├── start_wf2.sh
└── collect_logs.sh
```

---

## Rule

- 스크립트에는 실행 전 필요한 환경변수를 명시합니다.
- 위험한 정지/삭제 명령은 주석으로 설명합니다.
