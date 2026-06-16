# Folder Structure

이 문서는 ROScue 레포지토리의 폴더 구성 원칙을 설명합니다.

---

## Top-Level Layout

```text
ROScue/
├── README.md                      # 프로젝트 첫 화면
├── FOLDER_STRUCTURE.md            # 폴더 구성 설명
├── docs/                          # 발표/설계/운영 문서
├── ros2_ws/                       # ROS 2 workspace
├── web/                           # Flask/Web UI 코드
├── ai/                            # YOLO, RAG, LeRobot 관련 코드/설정
├── embedded/                      # STM32 펌웨어 및 임베디드 자료
├── maps/                          # SLAM map 파일
├── models/                        # YOLO/IL 모델 가중치
├── scripts/                       # 실행/배포/유틸 스크립트
└── tests/                         # 테스트 코드와 시나리오
```

---

## Design Rule

- 최상위 `README.md`는 짧은 프로젝트 소개와 링크 허브 역할만 합니다.
- 상세 설명은 `docs/` 하위 문서로 분리합니다.
- 코드 폴더에는 각 폴더별 `README.md`를 두어 목적과 실행법을 기록합니다.
- 이미지, 다이어그램, GIF는 `docs/assets/`에 모읍니다.
- 발표 슬라이드에서 나온 내용은 `docs/`의 해당 영역으로 분리합니다.

---

## Documentation Folders

| Folder | Purpose |
|---|---|
| `docs/architecture/` | 전체 아키텍처, 하드웨어, ROS_DOMAIN_ID, namespace, Mission Manager |
| `docs/navigation/` | Pinky SLAM, 좌표 발행, Nav2 다중 로봇 주행 |
| `docs/perception/` | YOLO 탐지, 모델 비교, 이벤트 인터페이스 |
| `docs/manipulation/` | 박스 개방, 모방학습, 리더-팔로워 조작 |
| `docs/llm_rag/` | RAG 응답 흐름, 등록 객체 정책, 절차 안내 |
| `docs/embedded/` | STM32 인터페이스, Bomb_A/B 하드웨어, I/O map |
| `docs/web/` | Web UI, mission control, dual YOLO dashboard |
| `docs/troubleshooting/` | 문제 원인과 해결 기록 |
| `docs/assets/` | 문서에 사용하는 이미지와 GIF |
