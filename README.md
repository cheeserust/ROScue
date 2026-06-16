# ROScue
Rescue / bomb defusal system with Turtlebot, Pinky Pro, and ROBOTIS OMX-AI

# 💣 ROS2-Based Intelligent Collaborative Bomb Disposal Robot System
## ROS2 기반 지능형 협업 폭발물 해체 로봇 시스템

> **Intelligent multi-robot collaboration system for safe explosive ordnance disposal (EOD)**  
> YOLO 기반 실시간 탐지 · 모방학습 기반 로봇팔 제어 · RAG-LLM 통합 의사결정 · 다중 로봇 자율 주행

---

## 📌 Overview | 개요

전 세계 폭발물 피해는 지속적으로 증가하고 있으며, 2023년 한 해에만 **47,000명 이상**의 사상자가 발생했습니다 (그 중 민간인 비율 72%). 기존 EOD 요원은 일반 직군 대비 **자살률 4배, 직업성 사망률 164% (2.6배)** 에 달하는 극단적 위험 환경에서 근무합니다.

본 프로젝트는 이러한 문제를 해결하기 위해, **탐색 로봇 + 해체 로봇의 유기적 협업**을 통해 폭발물을 자율 탐지·식별·해체하는 지능형 로봇 시스템을 개발합니다.

Explosive casualties are continuously rising worldwide — over **47,000 casualties in 2023 alone** (72% civilian). Active EOD personnel face a suicide rate **4× higher** than general workers and a **164% higher occupational fatality rate**. This project develops an intelligent collaborative robot system that autonomously detects, identifies, and disposes of explosives using a tandem **patrol robot + disposal robot** architecture.

---

## 🎯 Key Features | 핵심 기능

| Feature | Description |
|---|---|
| 🔍 **YOLO 기반 실시간 탐지** | YOLOv26m 모델로 폭발물 상자 탐지 (mAP50-95: **95.21%**, Recall: **99.71%**, Precision: **99.91%**) |
| 🗺️ **SLAM 기반 자율 주행** | LiDAR + Nav2 + ROS2로 실시간 지도 생성 및 다중 로봇 자율 경로 계획 |
| 🦾 **모방학습 기반 로봇팔 제어** | OMX 팔로워암 + 터틀봇 결합, Box Open 동작 메뉴얼 기반 imitation learning |
| 🤖 **RAG + LLM 통합 의사결정** | 탐지된 폭발물 정보를 RAG-LLM에 전달, 상황별 해체 방법 및 수통 보고 자동 생성 |
| 🌐 **Web 기반 원격 모니터링** | Flask 서버 + HTML/CSS/JS UI로 실시간 카메라 스트리밍 및 원격 제어 |
| 🔗 **Domain Bridge 다중 로봇 통신** | ROS_DOMAIN_ID 분리로 Pinky(SLAM) / wf1, wf2(해체) 간 충돌 없는 토픽 공유 |

---

## 🏗️ System Architecture | 시스템 구조

### Hardware Configuration | 하드웨어 구성

```
[고성능 PC / AI 서버]
    │  WLAN / gRPC / ROS2 통신
    │  AI 추론 및 원격 제어 명령
    ▼
[Raspberry Pi 4 - 상위 제어기]
    ├── USB  ← 카메라 (상황 관측) : 실시간 영상 스트림
    ├── USB  ← LiDAR (공간 정보) : 2D Point Cloud
    │  UART / Micro-ROS
    ▼
[OpenCR - 하위 제어기]
    ├── TTL (DYNAMIXEL Protocol) → 터틀봇 주행 / 엔코더 피드백
    └── USB & TTL → 매니퓰레이터 + 전방 카메라
        (동작 제어 명령 하달 / 센서·조인트 상태 피드백)

[매니퓰레이터 리더암] → 리더암 조인트 입력 데이터 → [고성능 PC]
```

### Tech Stack | 기술 스택

| Layer | Category | Tech / Tools | Role |
|---|---|---|---|
| **Front-End** | Web | HTML · CSS · JavaScript | 미션 시작 / 수동 조작 인터페이스 |
| **Back-End** | Flask Server | Python · Flask · OpenCV | 카메라 스트리밍 |
| **Middleware** | ROS2 Mission Manager | ROS2 · Python · State Machine | 상태 관리 · 로봇 상태 모니터링 · 이벤트 핸들링 |
| **AI / ML** | AI Perception | YOLOv26m · PyTorch · OpenCV | 박스 탐지 · 폭편물 탐지 |
| **Navigation** | Navigation | SLAM · Nav2 · ROS2 | 지도 작성 · 경로 계획 · 다중 로봇 제어 |
| **Hardware Control** | Robot Manipulation | OMX Arm · Imitation Learning | 로봇 팔 제어 · 모방 학습 · 리더-팔로워 제어 |

---

## 🔄 System Workflow | 동작 흐름

```
폭발물 탐지 및 해체 사전 작업 시작
        │
        ▼
순찰 로봇 목적 운용
        │
        ▼
SLAM 기반 지도 작성 및 실시간 공유
        │
        ▼
의심지역 목표 및 갱신 좌표 전송 ──────────────────────────┐
        │                                                    │
        ▼                                              [최표 데이터 송신]
 ┌─────────────────────────────────────────────────────┐
 │               탐지 및 해체 로봇 동작 프로토콜           │
 │                                                      │
 │  YOLO 기반 목표물 탐지 및 접근                         │
 │         │                                            │
 │         ▼                                            │
 │  YOLO 기반 폭발물 개폐여부/폭발물 존재여부 확인          │
 │         │                              │             │
 │    폭발물 미발견               [딸려있는 객체,         │
 │    우선 폼배 및                  폭발물 미발견]        │
 │    다음 프로브 임지 재개           │                  │
 │         │              모방 학습 및 매니퓰레이터 기반   │
 │         │              의심 객체 개방                 │
 │         │                     │                      │
 │         │              특발물 위치 공유 및             │
 │         │              해제 로봇 합류                  │
 │         │                     │                      │
 │         │              원격 조작 기반                  │
 │         │              다수 매니퓰레이터               │
 │         │              폭발물 동해 해제                │
 │         │                     │                      │
 │         │       탐지 완료 기준 충족 및 운용자 판단에     │
 │         │       따른 임무 종료 및 복귀                  │
 └─────────────────────────────────────────────────────┘
```

---

## 🤖 Multi-Robot Navigation | 다중 로봇 내비게이션

### ROS Domain 구조

```
ROS_DOMAIN_ID = 13         ROS_DOMAIN_ID = 10              ROS_DOMAIN_ID = 14 / 15
[Pinky Mapping Robot]  →  [주행 서버 / PC]            →   [주행 로봇 wf1 / wf2]
  - SLAM 실시간 지도          - Dispatcher 노드               - Nav2 주행 노드
  - /map publish              - DB 좌표 저장                  - 목표 이동 / 정지
                              - 좌표 발행 및 명령 분배
```

### 좌표 발행 방식

| 방식 | 설명 |
|---|---|
| **clicked_point** | rviz2 GUI에서 직접 클릭 → 주행 서버로 좌표 전달 → 가장 가까운 로봇에 명령 하달 |
| **랜덤 좌표** | 맵 위 랜덤 좌표 자동 발행 → 주행 서버 전달 → 거리 기반 로봇 선택 |

### Namespace / Domain Bridge 트러블슈팅

| 문제 | 원인 | 해결 |
|---|---|---|
| 외쪽 위치 추정 및 경로 계획 실패 | prefix 중복 적용으로 `map → odom → base_link` 연결 실패 | 독립된 Domain ID 사용 → Namespace 충돌 방지 |
| Nav2가 `/map` 구독 실패 | `/map`과 `map` 토픽 설정 불일치, AMCL map 구독 실패 | Pinky 단독 SLAM · wf1/wf2 map server 제거 → 하나의 `/map` 사용 |
| wf1/wf2가 잘못된 `/tf` 구독 | namespace 적용 Nav2가 `/wf1/tf` 구독 시도 | 주행 서버 PC ↔ 로봇 간 bridge에서만 토픽 구분, 로봇 내부 remap 문제 제거 |

---

## 🧠 AI / Perception | 인지 시스템

### YOLO 폭발물 탐지 모델 성능 비교

| Model | mAP50-95 | Recall | Precision |
|---|---|---|---|
| YOLOv10m | 93.9% | 99.66% | 99.64% |
| YOLOv11m | 94.11% | 99.71% | 99.89% |
| **YOLOv26m** | **95.21%** | **99.71%** | **99.91%** |

→ **YOLOv26m** 최종 채택

### LLM · RAG 통합 구조

```
카메라 영상 수신
      │
      ▼
  YOLO 탐지
      │
  신뢰도 판단 (conf ≥ 0.80)
      │
  확인 조건 (2초간 유지)
      │
  Web Server 탐지 결과 수신
      │
  RAG + LLM
      │
  해체 방법 출력
```

- **등록된 객체 (Bomb_A, Bomb_B)**: YOLO 탐지 결과 + 해체 방법 정보 제공
- **미등록 객체 (Bomb_C 등)**: 수통 보고 자동 생성 — 현재 조치 중지, 해치로 안내 이송, 주변 접근 제한, 관리자 확인 요청

---

## 🦾 Imitation Learning | 모방학습

### 시스템 구성

| 항목 | 내용 |
|---|---|
| **작업 플랫폼** | OMX 팔로워암 + 터틀봇 결합 |
| **전원 안정화** | 12V 외부 전원 공급, 5A 이상 전류 공급을 위한 고전압 배터리와 컨버터 활용 |
| **관찰 환경** | 각 로봇마다 웹캠 장착, 팔로워암 위치와 목표 객체의 상황이 동시에 보이도록 배치 |
| **데이터 수집** | 동작 메뉴얼 정의 및 메뉴얼 기반 데이터 수집, 모델 성능 향상을 위해 약간의 카메라 시점 차이로 로봇 데이터 동시 수집 |
| **데이터 다양성** | 상자 위치와 덮개 각도 변화, 실패/복구 상황 데이터 의도적 수집 |

### Box Open 동작 메뉴얼

1. 상자 전체와 손잡이가 카메라 화면에 최대한 포함되도록 로봇 초기 위치 조정
2. 손잡이가 명확히 관찰되도록 매니퓰레이터 하강
3. 안정적인 파지를 위해 엔드이펙터의 좌우 위치 조정
4. 손잡이 방향으로 자연스럽게 진입 가능하도록 엔드이펙터 벌림 각도 조정
5. 매니퓰레이터를 가능 거리까지 전진 시킨 후 손잡이 파지 동작 실행
6. 모터에 과한 부하가 발생하지 않도록 매니퓰레이터 상승 후 Box Open
7. 매니퓰레이터를 지정된 위치로 이동 시킨 후, 엔드이펙터 각도 하향 조정
8. 파지 해제 후, 매니퓰레이터 초기 상태로 복귀

### 모방학습 추론 통신 구조

```
[cam_1 / cam_2]  →  Raspberry Pi
                        │  영상 데이터 수집 및 전송 / 관절 각도 정보 수집 및 전송
                        ▼
                   [PC 추론 서버]
                        │  학습된 모방학습 모델 실행, 관절 각도 제어 명령 전송
                        ▼
                   Raspberry Pi → 로봇 제어

통신 성능 개선 결과:
  - 지연시간: 약 5~10ms 수준
  - 영상 전송: 약 30FPS
  - 실시간 추론 안정성 향상
```

### 모델 강건성 향상 전략

| 기법 | 설명 |
|---|---|
| **Domain Randomization** | 조명, 배경, 객체 색상/질감 등 시각적 요소 및 물리 파라미터(마찰력, 질량, 센서 노이즈)를 의도적으로 무작위화 |
| **State Perturbation** | 로봇을 이상한 위치나 불안정한 상태(Sub-optimal state)에 두고 복구 궤도 학습 |
| **DAgger** | 학습 중 사용자가 다양한 환경을 부딪쳐보며 실수하게 두고, 난처한 상황 대처 데이터 추가 수집 |

---

## 📋 State Control Process | 상태 제어 프로세스

### 식별부터 해체까지 전체 흐름

```
시작
  │
탐색 데이터 기반 맵 로딩
  │
해체 로봇 두 대 자율 탐색
  │
상자 타겟팅 (YOLO Detection)
  │
대상(close box) 식별? ──NO──→ (계속 탐색)
  │ YES
  ▼
의료 저장 근접 주행
  │
작업 위치 정지
  │
모방학습 기반 두부 개방 / 내부 상태 분석 (YOLO Detection)
  │
폭발물(Bomb_A/B) 식별? ──NO──→ [딸려있는 객체, 폭발물 미발견]
  │ YES                               └→ 우선 폼배 및 다음 프로브 임지 재개
  ▼
협업 요청 및 로봇 호출
  │
합동 작업 환경 구성
  │
원격 수동 제어 모드 전환
  │
원격 정밀 해체 수행
  │
해제 작업 완료
  │
추가 폭발물 미탐지? ──NO──→ (계속)
  │ YES
임무 수행 시간 경과? ──NO──→ (계속)
  │ YES
복귀 명령
  │
종료
```

---

## 🛠️ Setup & Installation | 설치 및 실행

### Prerequisites | 필수 환경

```bash
# ROS2 (Humble 이상)
# Python 3.8+
# PyTorch
# OpenCV
# Flask
```

### 주요 의존성 설치

```bash
pip install torch torchvision opencv-python flask ultralytics

# ROS2 패키지
sudo apt install ros-humble-navigation2 ros-humble-nav2-bringup
sudo apt install ros-humble-slam-toolbox
```

### ROS Domain 설정

```bash
# Pinky (SLAM 로봇)
export ROS_DOMAIN_ID=13

# 주행 서버 / PC
export ROS_DOMAIN_ID=10

# wf1 (해체 로봇 1)
export ROS_DOMAIN_ID=14

# wf2 (해체 로봇 2)
export ROS_DOMAIN_ID=15
```

### 실행 순서

```bash
# 1. Pinky SLAM 시작
ros2 launch pinky_slam slam_launch.py

# 2. 주행 서버 실행
python3 dispatcher_server.py

# 3. wf1 / wf2 Nav2 실행
ros2 launch waffle_nav2 nav2_launch.py robot_name:=wf1
ros2 launch waffle_nav2 nav2_launch.py robot_name:=wf2

# 4. YOLO 탐지 서버 실행
python3 yolo_detection_server.py

# 5. Flask 웹 서버 실행
python3 app.py

# 6. 모방학습 추론 서버 실행
python3 imitation_inference_server.py
```

---

## 📁 Repository Structure | 디렉토리 구조

```
📦 bomb-disposal-robot
 ┣ 📂 patrol_robot/          # Pinky 순찰 로봇 패키지
 ┃ ┗ 📂 slam/                # SLAM 관련 launch 및 config
 ┣ 📂 disposal_robot/        # wf1/wf2 해체 로봇 패키지
 ┃ ┣ 📂 navigation/          # Nav2 설정 및 launch
 ┃ ┗ 📂 manipulation/        # 매니퓰레이터 제어
 ┣ 📂 dispatcher_server/     # 주행 서버 (좌표 DB / 명령 분배)
 ┣ 📂 ai_perception/         # YOLO 탐지 모델 및 추론 서버
 ┣ 📂 imitation_learning/    # 모방학습 데이터 수집 / 학습 / 추론
 ┣ 📂 llm_rag/               # RAG + LLM 통합 모듈
 ┣ 📂 web_server/            # Flask 서버 + 프론트엔드 UI
 ┣ 📂 domain_bridge/         # ROS Domain Bridge 설정
 ┗ 📜 README.md
```

---

## 📊 Background & Motivation | 배경 및 필요성

- **글로벌 폭발물 피해**: 2023년 전 세계 폭발물 사상자 **47,000명+**, 민간인 비율 72%
- **EOD 요원 위험도**: 일반 직군 대비 자살률 4배, 직업성 사망률 164%, 평균 사망 연령 30세
- **기존 기술의 한계**:
  - 드론(UAV), 지표투과레이더(GPR) 등 탐지 기술은 급격히 발전 중
  - 발견 후 안전하게 해체하는 정밀 로봇 기술은 공백 상태
  - 단순 2D 카메라에 의존한 작업자가 임체감과 기리감을 상실
- **본 프로젝트의 목표**:
  - 실시간 인지: YOLO 기반 비전 시스템으로 위험물 자동 인식 및 시각화
  - 직관적 정밀 제어: 다관절 매니퓰레이터의 직관적 연동 제어로 작업 정밀도 극대화

---

## 📎 References | 참고 자료

- Action on Armed Violence (AOAV), *"Civilian casualties from explosive weapons in populated areas: a decade in review (2015–2023)"*
- U.S. Department of Defense (DOD) records, cited in *The Assembly (2026)*
- GICHD Innovation Conference 2025, *"Technology Speed Pitches" & "Breakout Robotics" sessions*

---

> 본 프로젝트는 **한화 로보틱스 & ROBOTIS AI 융합 로봇 SW 개발자 과정 (2기)** 결과물입니다.  
> This project is a capstone deliverable of the **Hanwha Robotics & ROBOTIS AI Convergence Robot SW Developer Program (Cohort 2)**.
