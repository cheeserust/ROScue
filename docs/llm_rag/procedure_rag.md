# Procedure RAG

Bomb_A/B 절차 문서 기반 안내 시스템을 정리합니다.

---

## File Layout

```text
ai/rag/
├── bomb_procedures.md
├── procedure_rag.py
└── bomb_procedure_rag_db/
```

---

## Procedure Document Example

```md
# Bomb_A

## label
Bomb_A

## procedure
1. BUTTON_1을 누릅니다.
2. BUTTON_2를 누릅니다.
3. 타이머가 정지했는지 확인합니다.
4. 상태 표시가 SAFE 또는 STOP으로 바뀌었는지 확인합니다.
```

---

## Retrieval Rule

버튼 순서는 정확해야 하므로 일반 유사도 검색보다 label 정확 매칭을 우선합니다.

```python
collection.get(where={"label": "Bomb_A"})
```

---

## TODO

- [ ] Bomb_A 실제 절차 입력
- [ ] Bomb_B 실제 절차 입력
- [ ] API `/api/yolo_report`와 연결
- [ ] API `/api/user_report`와 연결
