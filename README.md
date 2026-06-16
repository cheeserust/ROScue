<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:1a1a2e,50:16213e,100:0f3460&height=200&section=header&text=EOD-Bot&fontSize=60&fontColor=e94560&fontAlignY=35&desc=ROS2%20기반%20지능형%20협업%20폭발물%20해체%20로봇%20시스템&descSize=18&descAlignY=58&descColor=ffffff"/>

<br>

[![ROS2](https://img.shields.io/badge/ROS2-Humble-22314E?style=for-the-badge&logo=ros&logoColor=white)](https://docs.ros.org/en/humble/)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-YOLO-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org)
[![Flask](https://img.shields.io/badge/Flask-Web_UI-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![OpenCV](https://img.shields.io/badge/OpenCV-Vision-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org)

<br>

> **순찰 로봇이 폭발물을 탐지하고, 해체 로봇이 자율 접근 후 원격으로 해체합니다.**
> 사람이 위험 지역에 들어가지 않아도 되는 다중 로봇 협업 EOD 시스템입니다.

</div>

<br>

---

## 🔴 왜 만들었나

<table>
<tr>
<td width="50%">

**2023년 전 세계 폭발물 피해**
- 사상자 **47,000명+**
- 그 중 민간인 비율 **72%**

</td>
<td width="50%">

**현장 EOD 요원 현실**
- 일반 직군 대비 직업성 사망률 **+164%**
- 평균 사망 연령 **30세**
- 임무 후 PTSD로 인한 자살률 일반 병사의 **2배**

</td>
</tr>
</table>

탐지 기술(드론, GPR)은 빠르게 발전하고 있지만, **발견 후 안전하게 해체하는 정밀 로봇 기술은 공백** 상태입니다.
이 프로젝트는 그 공백을 채우기 위해 시작했습니다.

<br>

---

## ⚡ 시스템이 하는 일

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ① Pinky(순찰 로봇)이 SLAM으로 지도를 그리며 폭발물 상자 탐지    │
│            │                                                    │
│            ▼                                                    │
│  ② wf1 / wf2(해체 로봇)가 자율 주행으로 목표 위치 접근          │
│            │                                                    │
│            ▼                                                    │
│  ③ 모방학습 기반 로봇팔이 상자를 열고 내부 폭발물 확인           │
│            │                                                    │
│            ▼                                                    │
│  ④ RAG + LLM이 폭발물 종류 판단 → 해체 방법 제시               │
│            │                                                    │
│            ▼                                                    │
│  ⑤ 운용자가 Web UI로 원격 정밀 해체 수행                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

<br>

---

## 🏆 핵심 성과

<div align="center">

| 항목 | 결과 |
|:---|:---|
| 🎯 폭발물 탐지 정확도 (YOLOv26m) | mAP50-95 **95.21%** / Recall **99.71%** / Precision **99.91%** |
| ⚡ 모방학습 추론 지연시간 | **5~10ms**, 영상 전송 **30FPS** 안정 |
| 🤖 다중 로봇 동시 운용 | ROS Domain Bridge로 3종 로봇 충돌 없이 협업 |
| 🧠 미등록 폭발물 대응 | RAG-LLM이 수통 보고 자동 생성 및 접근 제한 조치 안내 |

</div>

<br>

---

## 🏗️ 시스템 아키텍처

```
                        ┌─────────────────────┐
                        │   운용자 Web UI      │
                        │  (Flask / HTML·JS)  │
                        └──────────┬──────────┘
                                   │
                        ┌──────────▼──────────┐
                        │  고성능 PC / AI 서버  │
                        │  YOLO 추론 · LLM    │
                        └──┬───────────────┬──┘
                 WLAN/gRPC │               │ 리더암 조인트 입력
                           │          ┌────▼─────┐
                ┌──────────▼──────┐   │  리더암  │
                │  Raspberry Pi 4  │   └──────────┘
                │  (상위 제어기)   │◄── LiDAR · Camera
                └──────────┬──────┘
                    UART / Micro-ROS
                ┌──────────▼──────┐
                │     OpenCR      │
                │  (하위 제어기)  │
                └──┬──────────┬───┘
         DYNAMIXEL │          │ USB & TTL
          ┌────────▼───┐  ┌───▼──────────────┐
          │  터틀봇 주행 │  │ 매니퓰레이터     │
          └────────────┘  │ + 전방 카메라    │
                          └──────────────────┘
```

**ROS Domain 분리 구조**

```
  DOMAIN 13 │ Pinky      → SLAM 지도 생성 및 공유
  DOMAIN 10 │ 주행 서버  → 좌표 DB 관리 / 로봇 명령 분배 (Dispatcher)
  DOMAIN 14 │ wf1        → Nav2 자율 주행 / 폭발물 해체
  DOMAIN 15 │ wf2        → Nav2 자율 주행 / 폭발물 해체
```

<br>

---

## 🛠️ 기술 스택

<div align="center">

| 영역 | 기술 |
|:---:|:---|
| 🤖 로봇 미들웨어 | ROS2 Humble · Nav2 · SLAM Toolbox · Micro-ROS · Domain Bridge |
| 🧠 AI / 인지 | YOLOv26m (PyTorch) · OpenCV · RAG + LLM |
| 🦾 모방학습 | Imitation Learning · OMX Leader-Follower Arm |
| ⚙️ 하드웨어 | TurtleBot3 · Raspberry Pi 4 · OpenCR · DYNAMIXEL · LiDAR |
| 🌐 백엔드 / 통신 | Python · Flask · gRPC · ROS2 State Machine |
| 💻 프론트엔드 | HTML · CSS · JavaScript |

</div>

<br>

---

## 🔬 주요 기술 상세

### 🎯 YOLO 기반 실시간 폭발물 탐지

세 가지 모델을 직접 학습하고 비교해 최종 모델을 선정했습니다.

<div align="center">

| Model | mAP50-95 | Recall | Precision |
|:---:|:---:|:---:|:---:|
| YOLOv10m | 93.9% | 99.66% | 99.64% |
| YOLOv11m | 94.11% | 99.71% | 99.89% |
| **YOLOv26m** ✅ | **95.21%** | **99.71%** | **99.91%** |

</div>

> 신뢰도 **0.80 이상**, **2초 유지** 조건을 충족해야 탐지로 확정합니다.

<br>

### 🦾 모방학습 기반 로봇팔 제어

운용자가 리더암을 조작하면 팔로워암이 동작을 따라합니다.
이 과정에서 수집한 데이터로 모델을 학습해 **자율 Box Open**을 구현했습니다.

**강건성 향상을 위해 적용한 방법**

| 기법 | 설명 |
|:---:|:---|
| **Domain Randomization** | 조명·배경·색상·센서 노이즈를 의도적으로 무작위화하여 다양한 환경에 대응 |
| **State Perturbation** | Sub-optimal 상태에서 정상 궤도로 복구하는 데이터 수집 |
| **DAgger** | 학습 중 실수를 유도하고 난처한 상황의 대처 데이터 추가 수집 |

<br>

### 🧠 RAG + LLM 의사결정

```
        YOLO 탐지 결과 수신 (conf ≥ 0.80, 2초 유지)
                    │
           등록된 폭발물?
          ┌─────────┴─────────┐
         YES                  NO
          │                   │
   해체 절차 안내        수통 보고 자동 생성
  (Bomb_A / Bomb_B)    ├─ 현재 조치 즉시 중단
                       ├─ 안전 구역으로 이송
                       ├─ 주변 접근 제한
                       └─ 관리자 확인 요청
```

<br>

### 🔧 다중 로봇 자율 주행 — 트러블슈팅

개발 중 가장 많은 시간을 투자한 문제는 **3대 로봇 동시 운용 시 ROS 토픽 충돌**이었습니다.

<details>
<summary><b>📋 문제 / 원인 / 해결 펼쳐보기</b></summary>

<br>

| 문제 | 원인 | 해결 |
|:---|:---|:---|
| 위치 추정·경로 계획 실패 | Namespace prefix 중복 → `map→odom→base_link` TF 연결 끊김 | 로봇별 독립 `ROS_DOMAIN_ID` 부여 |
| Nav2 `/map` 구독 실패 | wf1/wf2가 자체 map server 실행 → `/map` 충돌 | Pinky 단독 SLAM, wf1/wf2 map server 제거 |
| `/tf` 토픽 오구독 | namespace 적용 Nav2가 `/wf1/tf` 구독 시도 | 주행 서버↔로봇 bridge에서만 토픽 분리, 로봇 내부 remap 제거 |

</details>

<br>

---

## 🚀 설치 및 실행

**의존성 설치**

```bash
pip install torch torchvision opencv-python flask ultralytics
sudo apt install ros-humble-navigation2 ros-humble-nav2-bringup ros-humble-slam-toolbox
```

**실행 순서**

```bash
# ① Pinky SLAM
ROS_DOMAIN_ID=13 ros2 launch pinky_slam slam_launch.py

# ② 주행 서버
ROS_DOMAIN_ID=10 python3 dispatcher_server.py

# ③ 해체 로봇 Nav2
ROS_DOMAIN_ID=14 ros2 launch waffle_nav2 nav2_launch.py robot_name:=wf1
ROS_DOMAIN_ID=15 ros2 launch waffle_nav2 nav2_launch.py robot_name:=wf2

# ④ YOLO 탐지 서버
python3 yolo_detection_server.py

# ⑤ Web UI
python3 app.py

# ⑥ 모방학습 추론
python3 imitation_inference_server.py
```

<br>

---

## 📁 디렉토리 구조

```
📦 eod-bot
 ┣ 📂 patrol_robot/       # Pinky SLAM 패키지
 ┣ 📂 disposal_robot/     # wf1/wf2 Nav2 + 매니퓰레이터 제어
 ┣ 📂 dispatcher_server/  # 좌표 DB 및 로봇 명령 분배
 ┣ 📂 ai_perception/      # YOLOv26m 학습 및 추론
 ┣ 📂 imitation_learning/ # 모방학습 데이터 수집·학습·추론
 ┣ 📂 llm_rag/            # RAG + LLM 의사결정 모듈
 ┣ 📂 web_server/         # Flask + 프론트엔드 UI
 ┣ 📂 domain_bridge/      # ROS Domain Bridge 설정
 ┗ 📜 README.md
```

<br>

---

<div align="center">

한화 로보틱스 & ROBOTIS AI 융합 로봇 SW 개발자 과정 2기

*Source: AOAV (2015–2023) · U.S. DOD / The Assembly (2026) · GICHD Innovation Conference 2025*

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:1a1a2e,50:16213e,100:0f3460&height=100&section=footer"/>

</div>
