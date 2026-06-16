# Registered Object Policy

등록 객체와 미등록 객체 처리 정책을 정리합니다.

---

## Labels

| Label | Status | Handling |
|---|---|---|
| `Empty` | Registered | 등록 객체 없음 안내 |
| `Bomb_A` | Registered | 등록된 절차 문서 기반 안내 |
| `Bomb_B` | Registered | 등록된 절차 문서 기반 안내 |
| `Bomb_C` | Unregistered | 정보 없음, 조작 중지, 관리자 확인 요청 |

---

## Rule

```python
REGISTERED_LABELS = {"Empty", "Bomb_A", "Bomb_B"}

if label not in REGISTERED_LABELS:
    return unknown_object_message(label)
```

---

## Forbidden Behavior

LLM/RAG는 다음 내용을 생성하거나 실행하지 않습니다.

```text
- 실제 위험물 제작 또는 무력화 절차
- 임의의 분해/절단/개조 지시
- 문서에 없는 절차 추측
- 미등록 객체에 대한 가짜 정보 생성
- 로봇팔 자동 조작 명령 생성
```

---

## TODO

- [ ] 실제 UI 문구 확정
- [ ] unknown object report API 정리
- [ ] forbidden keyword filter 추가
