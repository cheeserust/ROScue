# STM32 Interface

STM32와 Raspberry Pi / ROS 2 연동 구조를 정리합니다.

---

## Recommended Development Path

```text
1. USB-Serial 또는 UART로 STM32 ↔ Raspberry Pi 통신 성공
2. Raspberry Pi에서 ROS 2 serial_bridge_node 작성
3. /cmd_vel, /encoder, /imu/data 토픽 연결
4. 주행이 안정되면 CAN으로 확장
5. 필요하면 micro-ROS 적용
```

---

## Serial Bridge Concept

```text
[STM32 UART]
    encoder, imu, motor state packet
        ↓
[Raspberry Pi 4 ROS 2 node]
    serial_bridge_node
        ├── publish: /encoder, /imu/data, /battery_state
        └── subscribe: /cmd_vel, /motor_cmd
```

---

## TODO

- [ ] 실제 baudrate 확정
- [ ] packet format 작성
- [ ] checksum 방식 추가
- [ ] USB device path 고정법 작성
- [ ] micro-ROS 적용 여부 결정
