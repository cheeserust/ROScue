## Imitation Learning

ROScue는 박스 뚜껑을 여는 조작 동작에 모방학습을 적용했습니다.  
사람이 직접 조작한 전문가 데이터를 수집하고, 이를 기반으로 로봇이 유사한 상황에서 뚜껑 개방 동작을 수행하도록 구성했습니다.

<div align="center">

<img src="./docs/assets/imitation_learning_inference.png" width="90%">

</div>

---

### Inference Structure

| Component | Role |
|---|---|
| Raspberry Pi | 카메라 영상 및 매니퓰레이터 관절 데이터 수집 |
| Camera 1 / Camera 2 | 서로 다른 시점의 작업 장면 수집 |
| OMX Arm | 박스 뚜껑 개방 동작 수행 |
| Dedicated Wireless Network | 영상 및 제어 데이터 송수신 |
| PC Inference Server | LeRobot Policy 실행 및 추론 명령 생성 |

---

### Data Flow

1. Raspberry Pi가 카메라 영상과 관절 각도 정보를 수집
2. 수집된 데이터가 독립 무선망을 통해 PC 추론 서버로 전송
3. PC 추론 서버에서 학습된 모방학습 모델 실행
4. 관절 각도 제어 명령 전송
5. OMX 매니퓰레이터가 박스 뚜껑 개방 동작 수행

---

### Box Opening Motion

1. 상자 전체와 손잡이가 카메라 화면에 최대한 포함되도록 로봇의 초기 위치 조정
2. 손잡이가 명확히 관찰되도록 매니퓰레이터를 하강
3. 안정적인 파지를 위해 엔드이펙터의 좌우 위치 조정
4. 손잡이 방향으로 자연스럽게 진입 가능하도록 엔드이펙터의 벌림 각도 조정
5. 매니퓰레이터를 가능 거리까지 전진 시킨 후 손잡이 파지 동작 실행
6. 모터에 과한 부하가 발생하지 않도록 매니퓰레이터 상승 후 Box Open
7. 매니퓰레이터를 지정된 위치로 이동 시킨 후, 엔드이펙트 각도 하향 조정
8. 파지 해체 후, 매니퓰레이터 초기 상태로 복귀
