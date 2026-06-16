# ROScue Documentation

ROScue 프로젝트의 상세 기술 문서입니다.  
각 카테고리는 별도 세부 파일로 나누지 않고, 해당 폴더의 `README.md` 안에서 섹션별로 정리합니다.

## Categories

| Category | Description |
|---|---|
| [Scenario](scenario/) | 전체 미션 시나리오와 Phase 0~3 흐름 |
| [Setup](setup/) | 개발 환경 설치 및 기본 설정 |
| [Runbook](runbook/) | 데모 실행 순서 |
| [ROS Interfaces](ros_interfaces/) | topic, service, action 정의 |
| [Architecture](architecture/) | 전체 시스템, 하드웨어, ROS_DOMAIN_ID, namespace 구조 |
| [Navigation](navigation/) | Pinky SLAM, 좌표 발행, Nav2 다중 로봇 주행 |
| [Perception](perception/) | YOLO 박스 탐지, 내부 객체 탐지, 모델 성능 비교 |
| [Manipulation](manipulation/) | 박스 개방, 모방학습, 리더-팔로워 제어 |
| [LLM/RAG](llm_rag/) | 등록 객체 안내, 미등록 객체 처리, RAG 응답 구조 |
| [Embedded](embedded/) | STM32 기반 버튼, LCD, LED, Buzzer 인터페이스 |
| [Web UI](web/) | Web/App UI, dual YOLO dashboard |
| [Troubleshooting](troubleshooting/) | namespace, domain bridge, Python 버전, cmd_vel 타입 문제 |
| [Assets](assets/) | 문서 이미지, GIF, 다이어그램 보관 규칙 |

## Writing Rule

- 각 카테고리는 `docs/<category>/README.md` 하나에 작성합니다.
- README 내부의 `On this page` 목차로 섹션 이동을 제공합니다.
- 발표 슬라이드 이미지는 `docs/assets/`에 넣고 상대경로로 연결합니다.
