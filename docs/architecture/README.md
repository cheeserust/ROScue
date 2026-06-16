# Architecture

ROScue의 전체 시스템 구조, 하드웨어 구성, ROS 2 네트워크 설계, Mission Manager 구조를 정리합니다.

---

## Documents

| Document | Description |
|---|---|
| [System Architecture](system_architecture.md) | Web UI, Mission Manager, AI, Navigation, Manipulation 전체 흐름 |
| [Hardware Architecture](hardware_architecture.md) | Raspberry Pi, OpenCR, LiDAR, Camera, OMX Arm, STM32 구성 |
| [ROS Domain & Namespace](ros_domain_namespace.md) | ROS_DOMAIN_ID, namespace, domain_bridge 설계 |
| [Mission Manager](mission_manager.md) | FSM, robot registry, box registry, queue, timer 관리 |
