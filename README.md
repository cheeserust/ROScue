<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:1a1a2e,50:16213e,100:0f3460&height=220&section=header&text=ROS2%20기반%20지능형%20협업%20폭발물%20해체%20로봇%20시스템&fontSize=32&fontColor=ffffff&fontAlignY=40&desc=Team%20ROScue&descSize=22&descAlignY=62&descColor=ffffff"/>

<br>

[![ROS2](https://img.shields.io/badge/ROS2-jazzy-22314E?style=for-the-badge&logo=ros&logoColor=white)](https://docs.ros.org/en/jazzy/)
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

## 📌 개발 배경 및 목적

<br>

<div align="center">

### 🌍 글로벌 폭발물 피해 현황 (2023)

<table>
<tr>
<td align="center" width="33%">
<h2>47,000<sup>+</sup></h2>
연간 전 세계 폭발물 사상자
</td>
<td align="center" width="33%">
<h2>72%</h2>
사상자 중 민간인 비율
</td>
<td align="center" width="33%">
<h2>30세</h2>
EOD 요원 평균 사망 연령
</td>
</tr>
</table>

</div>

<br>

<table>
<tr>
<td width="50%" valign="top">

### ⚠️ EOD 요원이 처한 현실

- 임무 후 극심한 PTSD로 인한 **자살률, 일반 병사 대비 2배**
- 직업성 사망률 일반 직군 대비 **+164% (2.6배)**
- 인력을 현장에 직접 투입하는 방식은 **구조적 한계**에 봉착

</td>
<td width="50%" valign="top">

### 🚧 기존 기술의 한계

- 드론(UAV), GPR 등 **탐지 기술은 발전** 중
- 그러나 발견 후 **안전하게 해체하는 정밀 로봇 기술은 공백**
- 2D 카메라 의존으로 작업자가 **입체감·거리감을 상실**

</td>
</tr>
</table>

<br>

<div align="center">

### 💡 이 프로젝트의 목표

| | 목표 | 방법 |
|:---:|:---|:---|
| 🔍 | 실시간 위험물 자동 인식 및 시각화 | YOLO 기반 비전 시스템 |
| 🦾 | 작업자 없이 원격 정밀 해체 | 다관절 매니퓰레이터 직관적 연동 제어 |
| 🤖 | 다중 로봇 자율 협업 | ROS2 기반 탐색·해체 로봇 분업 구조 |
| 🧠 | 미등록 위협 상황 판단 및 대응 | RAG + LLM 의사결정 모듈 |

</div>

<br>

---

## 🎬 시나리오

<br>

```
 ┌──────────────────────────────────────────────────────────────────────┐
 │                                                                      │
 │   STEP 1  🔎  탐색                                                   │
 │   ──────────────────────────────────────────────────────────────     │
 │   Pinky(순찰 로봇)가 LiDAR + SLAM으로 실시간 지도를 생성하며          │
 │   YOLO 탐지로 폭발물 상자를 자율 탐색합니다.                          │
 │                                                                      │
 │                              │                                       │
 │                              ▼                                       │
 │                                                                      │
 │   STEP 2  🚗  접근                                                   │
 │   ──────────────────────────────────────────────────────────────     │
 │   해체 로봇(wf1 / wf2)이 공유된 지도와 좌표를 바탕으로               │
 │   Nav2 자율 주행으로 목표 위치에 접근합니다.                          │
 │                                                                      │
 │                              │                                       │
 │                              ▼                                       │
 │                                                                      │
 │   STEP 3  🦾  개방 및 확인                                           │
 │   ──────────────────────────────────────────────────────────────     │
 │   모방학습으로 학습된 로봇팔이 자율로 상자를 열고,                    │
 │   내부를 YOLO로 재탐지해 폭발물 종류를 확인합니다.                    │
 │                                                                      │
 │                              │                                       │
 │                              ▼                                       │
 │                                                                      │
 │   STEP 4  🧠  판단                                                   │
 │   ──────────────────────────────────────────────────────────────     │
 │   RAG + LLM이 폭발물 등록 여부를 판단합니다.                         │
 │   등록된 경우 해체 절차를 안내하고,                                   │
 │   미등록인 경우 수통 보고를 자동 생성하고 접근 제한 조치를 내립니다.   │
 │                                                                      │
 │                              │                                       │
 │                              ▼                                       │
 │                                                                      │
 │   STEP 5  🎮  원격 해체                                              │
 │   ──────────────────────────────────────────────────────────────     │
 │   운용자가 Web UI를 통해 원격으로 매니퓰레이터를 정밀 제어하여        │
 │   안전하게 폭발물을 해체합니다.                                       │
 │                                                                      │
 └──────────────────────────────────────────────────────────────────────┘
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

**Robotics & Middleware**

![ROS2](https://img.shields.io/badge/ROS2_Jazzy-22314E?style=flat-square&logo=ros&logoColor=white)
![Nav2](https://img.shields.io/badge/Nav2-22314E?style=flat-square&logo=ros&logoColor=white)
![SLAM](https://img.shields.io/badge/SLAM_Toolbox-22314E?style=flat-square&logo=ros&logoColor=white)
![MicroROS](https://img.shields.io/badge/Micro--ROS-22314E?style=flat-square&logo=ros&logoColor=white)
![DomainBridge](https://img.shields.io/badge/Domain_Bridge-22314E?style=flat-square&logo=ros&logoColor=white)

**AI / Vision**

![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)
![YOLO](https://img.shields.io/badge/YOLOv26m-00FFFF?style=flat-square&logoColor=black)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=flat-square&logo=opencv&logoColor=white)
![LLM](https://img.shields.io/badge/RAG_+_LLM-412991?style=flat-square&logo=openai&logoColor=white)

**Hardware**

![TurtleBot3](https://img.shields.io/badge/TurtleBot3-FF6B35?style=flat-square&logoColor=white)
![RPi](https://img.shields.io/badge/Raspberry_Pi_4-A22846?style=flat-square&logo=raspberrypi&logoColor=white)
![OpenCR](https://img.shields.io/badge/OpenCR-A22846?style=flat-square&logoColor=white)
![DYNAMIXEL](https://img.shields.io/badge/DYNAMIXEL-FF6B35?style=flat-square&logoColor=white)
![LiDAR](https://img.shields.io/badge/LiDAR-607D8B?style=flat-square&logoColor=white)

**Backend / Frontend**

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white)
![gRPC](https://img.shields.io/badge/gRPC-4285F4?style=flat-square&logo=google&logoColor=white)
![HTML](https://img.shields.io/badge/HTML-E34F26?style=flat-square&logo=html5&logoColor=white)
![CSS](https://img.shields.io/badge/CSS-1572B6?style=flat-square&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)

</div>

<br>

---

## 🔬 주요 기술 상세

<br>

### 🎯 YOLO 기반 실시간 폭발물 탐지

> 세 가지 모델을 직접 학습하고 비교해 최종 모델을 선정했습니다.

<div align="center">

| Model | mAP50-95 | Recall | Precision |
|:---:|:---:|:---:|:---:|
| YOLOv10m | 93.9% | 99.66% | 99.64% |
| YOLOv11m | 94.11% | 99.71% | 99.89% |
| **✅ YOLOv26m** | **95.21%** | **99.71%** | **99.91%** |

</div>

```
탐지 확정 조건  →  신뢰도(conf) ≥ 0.80  +  2초 이상 유지
```

<br>

---

### 🦾 모방학습 기반 로봇팔 제어

> 운용자가 리더암을 조작하면 팔로워암이 동작을 따라하며, 이 과정에서 수집한 데이터로 **자율 Box Open**을 구현했습니다.

<table>
<tr>
<td width="50%" valign="top">

**📦 Box Open 동작 순서**

```
① 상자·손잡이가 카메라에 최대 포함되도록 초기 위치 조정
② 손잡이가 명확히 보이도록 매니퓰레이터 하강
③ 안정적 파지를 위해 엔드이펙터 좌우 위치 조정
④ 손잡이 방향으로 진입 가능하도록 벌림 각도 조정
⑤ 가능 거리까지 전진 후 손잡이 파지 실행
⑥ 모터 과부하 방지를 위해 상승 후 Box Open
⑦ 지정 위치로 이동 후 엔드이펙터 하향 조정
⑧ 파지 해제 후 초기 상태로 복귀
```

</td>
<td width="50%" valign="top">

**💪 강건성 향상 전략**

| 기법 | 설명 |
|:---:|:---|
| **Domain<br>Randomization** | 조명·배경·색상·센서 노이즈 무작위화 |
| **State<br>Perturbation** | Sub-optimal 상태에서 복구 데이터 수집 |
| **DAgger** | 실수 유도 후 난처한 상황 대처 데이터 추가 수집 |

</td>
</tr>
</table>

**🔗 추론 통신 구조**

```
[cam_1 / cam_2] ──영상 + 관절 각도──▶ [Raspberry Pi] ──네트워크──▶ [PC 추론 서버]
                                                                          │
                                  관절 각도 제어 명령 ◀────────────────────┘

  지연시간 5~10ms  │  영상 전송 30FPS  │  실시간 추론 안정
```

<br>

---

### 🧠 RAG + LLM 의사결정

```
  YOLO 탐지 결과 수신
  (conf ≥ 0.80, 2초 유지)
          │
          ▼
  ┌───────────────┐       YES      ┌──────────────────────────┐
  │ 등록된 폭발물? │ ─────────────▶ │ 해체 절차 안내           │
  │ Bomb_A / B   │                │ (단계별 해체 방법 제공)   │
  └───────────────┘                └──────────────────────────┘
          │ NO
          ▼
  ┌──────────────────────────────────────┐
  │ 수통 보고 자동 생성                   │
  │  ├─ 현재 조치 즉시 중단              │
  │  ├─ 안전 구역으로 이송               │
  │  ├─ 주변 접근 제한                   │
  │  └─ 관리자 확인 요청                 │
  └──────────────────────────────────────┘
```

<br>

---

### 🔧 다중 로봇 자율 주행 — 트러블슈팅

> 개발 중 가장 많은 시간을 투자한 문제는 **3대 로봇 동시 운용 시 ROS 토픽 충돌**이었습니다.

<details>
<summary><b>📋 문제 / 원인 / 해결 펼쳐보기</b></summary>

<br>

| 문제 | 원인 | 해결 |
|:---|:---|:---|
| 위치 추정·경로 계획 실패 | Namespace prefix 중복 → `map→odom→base_link` TF 연결 끊김 | 로봇별 독립 `ROS_DOMAIN_ID` 부여 |
| Nav2 `/map` 구독 실패 | wf1/wf2 자체 map server 실행 → `/map` 충돌 | Pinky 단독 SLAM, wf1/wf2 map server 제거 |
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


<img src="https://capsule-render.vercel.app/api?type=waving&color=0:1a1a2e,50:16213e,100:0f3460&height=100&section=footer"/>

</div>
