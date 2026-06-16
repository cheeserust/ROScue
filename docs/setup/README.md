# Setup

[← Docs Home](../)

개발 환경 설치와 기본 설정을 정리합니다.

## On this page

- [1. Target Environment](#target-environment)
- [2. ROS 2 Setup](#ros-2-setup)
- [3. Python Environment](#python-environment)
- [4. YOLO / AI Environment](#yolo-ai-environment)
- [5. Ollama / RAG Environment](#ollama-rag-environment)
- [6. STM32 Environment](#stm32-environment)
- [7. Network Settings](#network-settings)

<a id="target-environment"></a>
## 1. Target Environment

| Target | Version / Note |
|---|---|
| OS | Ubuntu 24.04 or project environment |
| ROS 2 | Jazzy |
| Python | ROS 2: Python 3.12 계열 / LeRobot 호환성 확인 필요 |
| Robot | TurtleBot3 Waffle / custom platform |
| MCU | STM32 |

<a id="ros-2-setup"></a>
## 2. ROS 2 Setup

```bash
source /opt/ros/jazzy/setup.bash
mkdir -p ~/roscue_ws/src
cd ~/roscue_ws
colcon build
source install/setup.bash
```

<a id="python-environment"></a>
## 3. Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
```

<a id="yolo-ai-environment"></a>
## 4. YOLO / AI Environment

```bash
pip install ultralytics opencv-python torch torchvision
```

<a id="ollama-rag-environment"></a>
## 5. Ollama / RAG Environment

```bash
ollama pull gemma3:4b
ollama pull mxbai-embed-large
pip install chromadb langchain-text-splitters requests
```

<a id="stm32-environment"></a>
## 6. STM32 Environment

> TODO: STM32CubeIDE, Makefile, flashing 방법 정리

<a id="network-settings"></a>
## 7. Network Settings

| Target | Example |
|---|---|
| Central Server | `ROS_DOMAIN_ID=10` |
| Pinky | `ROS_DOMAIN_ID=13` |
| WF1 | `ROS_DOMAIN_ID=14` |
| WF2 | `ROS_DOMAIN_ID=15` |
