# Web UI

[← Docs Home](../)

운영자 Web/App UI, mission control, dual YOLO dashboard 구조를 정리합니다.

## On this page

- [1. Overview](#overview)
- [2. Mission Control UI](#mission-control-ui)
- [3. Dual YOLO Dashboard](#dual-yolo-dashboard)
- [4. Safety Notice Panel](#safety-notice-panel)
- [5. API Endpoints](#api-endpoints)
- [6. UI Layout](#ui-layout)
- [7. Open Issues](#open-issues)

<a id="overview"></a>
## 1. Overview

Web UI는 운영자가 미션 시작, 정지, 수동 처리 완료, 수동 보고, dual YOLO 화면 확인을 수행하는 인터페이스입니다.

<a id="mission-control-ui"></a>
## 2. Mission Control UI

주요 버튼:

- Mission Start
- Mission Stop
- SLAM Start
- Manual Done
- Emergency Stop
- YOLO Mode 변경
- User Report

<a id="dual-yolo-dashboard"></a>
## 3. Dual YOLO Dashboard

```text
Detection Tab
├── YOLO 화면 · wf1
├── YOLO 화면 · wf2
└── 탐지 확정 및 절차 안내 패널
```

기본 포트 예시:

| Robot | Port | URL |
|---|---:|---|
| wf1 | 5055 | `http://<PC_IP>:5055/dashboard/debug` |
| wf2 | 5056 | `http://<PC_IP>:5056/dashboard/debug` |

<a id="safety-notice-panel"></a>
## 4. Safety Notice Panel

LLM/RAG 모듈에서 생성한 최신 안내문을 표시합니다.

```text
source: YOLO or USER_REPORT
label: Bomb_A / Bomb_B / Bomb_C / Empty
confidence: 0.82
message: ...
```

<a id="api-endpoints"></a>
## 5. API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/command` | POST | mission start/stop 등 명령 |
| `/api/boxes` | GET | box registry 조회 |
| `/api/teleop` | POST | 수동 조작 명령 |
| `/api/yolo_report` | POST | YOLO 탐지 결과 보고 |
| `/api/user_report` | POST | 사용자 수동 보고 |
| `/api/safety_notice/latest` | GET | 최신 안내문 조회 |

<a id="ui-layout"></a>
## 6. UI Layout

![Web UI](../assets/web_ui.png)

> TODO: `docs/assets/web_ui.png` 추가

<a id="open-issues"></a>
## 7. Open Issues

- [ ] WF1/WF2 stream URL 환경변수화
- [ ] mission state 실시간 업데이트 방식 확정
- [ ] emergency stop 버튼 위치 고정
- [ ] mobile layout 대응
