# Troubleshooting: Domain Bridge

ROS_DOMAIN_ID, namespace, domain_bridge 관련 문제 해결 기록입니다.

---

## Problem

```text
- 여러 로봇 topic/frame 충돌
- map server 중복 발행
- WF1/WF2 내부 remap 문제
```

---

## Cause

```text
- 모든 로봇이 같은 기본 topic/frame 사용
- /map을 여러 곳에서 발행
- /tf frame_id가 유일하지 않음
```

---

## Solution

```text
1. ROS_DOMAIN_ID 분리
2. /pinky, /wf1, /wf2 namespace 사용
3. WF1/WF2 map server 제거
4. Pinky map을 중앙 서버에서 bridge
5. robot별 frame_id 유일화
```

---

## TODO

- [ ] 실제 domain_bridge yaml 추가
- [ ] 문제 재현 명령 추가
- [ ] 해결 전/후 topic list 캡처 추가
