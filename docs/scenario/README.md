# Scenario

[← Docs Home](../)

ROScue의 전체 미션 시나리오와 Phase별 흐름을 정리합니다.

## On this page

- [1. Scenario Summary](#scenario-summary)
- [2. Phase 0 — SLAM Mapping](#phase-0-slam-mapping)
- [3. Phase 1 — Autonomous Exploration](#phase-1-autonomous-exploration)
- [4. Phase 2 — Box Opening and Internal Scan](#phase-2-box-opening-and-internal-scan)
- [5. Phase 3 — Dual-Robot Cooperative Response](#phase-3-dual-robot-cooperative-response)
- [6. Exception Handling](#exception-handling)
- [7. Demo Flow](#demo-flow)

<a id="scenario-summary"></a>
## 1. Scenario Summary

ROScue는 SLAM 지도 생성, 자율 탐색, 박스 탐지, 박스 개방, 내부 객체 탐지, 파트너 로봇 호출, 운영자 수동 대응으로 이어지는 다중 로봇 시나리오입니다.

<a id="phase-0-slam-mapping"></a>
## 2. Phase 0 — SLAM Mapping

```text
운영자 SLAM 시작
→ Pinky Mapping Robot 수동 주행
→ SLAM 지도 생성
→ /map, /map_metadata 중앙 서버 전달
→ 좌표 DB 저장
→ WF1/WF2 자율 주행 준비
```

State transition:

```text
IDLE → SLAM_MAPPING → IDLE
```

<a id="phase-1-autonomous-exploration"></a>
## 3. Phase 1 — Autonomous Exploration

```text
운영자 미션 시작
→ WF1/WF2 자율 탐색
→ YOLO 기반 close/open 박스 탐지
→ 박스 좌표 등록
→ 목표 지점 접근
```

<a id="phase-2-box-opening-and-internal-scan"></a>
## 4. Phase 2 — Box Opening and Internal Scan

```text
목표 박스 접근 완료
→ 매니퓰레이터 위치 정렬
→ 모방학습 기반 박스 개방
→ 내부 카메라 스캔
→ YOLO 기반 Empty / Bomb_A / Bomb_B 판단
```

<a id="phase-3-dual-robot-cooperative-response"></a>
## 5. Phase 3 — Dual-Robot Cooperative Response

```text
Bomb_A/B 감지
→ 발견 로봇 WAIT_PARTNER
→ 파트너 로봇 호출
→ 두 로봇 DUAL_MANUAL 진입
→ 운영자가 원격 수동 조작
→ 완료 후 탐색 재개 또는 임무 종료
```

<a id="exception-handling"></a>
## 6. Exception Handling

| Situation | Handling |
|---|---|
| SLAM 실패 | `SLAM_MAPPING → RECOVER`, 운영자 재시도 |
| Visual servo LOST/TIMEOUT | 박스 `REVISIT` 등록 후 `EXPLORE` 복귀 |
| 뚜껑 열기 실패 | 박스 `OPEN_FAILED`, `EXPLORE` 복귀 |
| 파트너 120s 내 미도착 | 발견 로봇 `RECOVER` |
| heartbeat 3s 단절 | 로봇 `LOST` 처리 |
| 수동 조작 10분 초과 | 일시정지 및 알림 |
| 미션 정지 명령 | 어떤 상태에서든 `IDLE` 복귀 |

<a id="demo-flow"></a>
## 7. Demo Flow

![Demo Scenario](../assets/demo_scenario.png)

> TODO: `docs/assets/demo_scenario.png` 추가
