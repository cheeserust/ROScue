# Leader-Follower Control

두 로봇 매니퓰레이터의 원격 수동 조작 구조를 정리합니다.

---

## Flow

```text
운영자 리더암 조작
    ↓
관절 입력 데이터 수집
    ↓
Central Server PC
    ↓ gRPC / ROS 2 / custom bridge
WF1/WF2 follower arm 제어
```

---

## Dual Manual Mode

```text
WAIT_PARTNER
→ partner_arrived
→ DUAL_MANUAL
→ operator manual control
→ manual_done
→ EXPLORE or mission_end
```

---

## TODO

- [ ] 리더암 topic/service 정의
- [ ] follower arm command type 확정
- [ ] 수동 조작 timeout 정책 작성
- [ ] emergency stop 동작 확인
