# LLM / RAG

[← Docs Home](../)

YOLO 탐지 결과를 기반으로 등록 객체 안내를 생성하는 LLM/RAG 구조를 정리합니다.

## On this page

- [1. Overview](#overview)
- [2. Response Flow](#response-flow)
- [3. Registered Object Policy](#registered-object-policy)
- [4. Procedure RAG](#procedure-rag)
- [5. API Design](#api-design)
- [6. Safety Guardrails](#safety-guardrails)
- [7. Test Cases](#test-cases)

<a id="overview"></a>
## 1. Overview

LLM/RAG 모듈은 로봇 제어권을 갖지 않습니다. Mission Manager가 상태 전이와 로봇 제어를 수행하고, LLM/RAG는 Web UI에 표시할 등록 객체 안내문을 생성합니다.

<a id="response-flow"></a>
## 2. Response Flow

```text
카메라 영상 수신
→ YOLO 탐지
→ confidence 기준 확인
→ 일정 시간 유지 조건 확인
→ Web Server 탐지 결과 수신
→ RAG 문서 검색
→ LLM 안내문 생성
→ Web UI 출력
```

<a id="registered-object-policy"></a>
## 3. Registered Object Policy

| Type | Example | Handling |
|---|---|---|
| Registered Object | Bomb_A, Bomb_B | 등록된 절차 문서 기반 안내 |
| Empty | Empty | 등록 객체 없음 안내 |
| Unregistered Object | Bomb_C | 정보 없음, 조작 중지, 관리자 확인 요청 |

<a id="procedure-rag"></a>
## 4. Procedure RAG

RAG 문서는 label별로 분리하고, label 정확 매칭을 우선합니다.

```text
Bomb_A 감지 → Bomb_A 문서만 검색
Bomb_B 감지 → Bomb_B 문서만 검색
Bomb_C 입력 → RAG/LLM 호출 전 미등록 처리
```

<a id="api-design"></a>
## 5. API Design

| API | Description |
|---|---|
| `POST /api/yolo_report` | YOLO high/low confidence 결과 보고 |
| `POST /api/user_report` | 사용자가 Bomb_C 등 수동 보고 |
| `GET /api/safety_notice/latest` | 최신 안내문 조회 |

<a id="safety-guardrails"></a>
## 6. Safety Guardrails

- 등록 label whitelist 사용
- 미등록 객체는 LLM 호출 전 차단
- RAG 문서 범위 안에서만 답변
- 실제 위험물 제작/무력화 절차 제공 금지
- 로봇 제어 함수와 LLM 응답 분리

<a id="test-cases"></a>
## 7. Test Cases

| Test | Expected Result |
|---|---|
| Bomb_A high confidence | Bomb_A 절차 안내 생성 |
| Bomb_B high confidence | Bomb_B 절차 안내 생성 |
| Bomb_A low confidence | 재확인 안내, 상태 전이 없음 |
| Bomb_C user report | 등록 정보 없음 안내 |
| Empty | 등록 객체 없음 안내 |
