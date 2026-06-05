# server pc: omx_manual_control.py
import socket
import struct
import time
from lerobot.motors.dynamixel import DynamixelMotorsBus

# LeRobot v0.4.4 호환용 커스텀 모터 객체
class Motor:
    def __init__(self, idx, model):
        self.id = idx
        self.model = model

RASPBERRY_PI_IP = "10.10.14.10" # 라즈베리파이 IP 주소 (확인 필수)
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 리더 암 (ID 1~6) - 튜플이 아닌 Motor 객체로 전달
motors_config = {
    "m1": Motor(1, "xl330-m288"),
    "m2": Motor(2, "xl330-m288"),
    "m3": Motor(3, "xl330-m288"),
    "m4": Motor(4, "xl330-m288"),
    "m5": Motor(5, "xl330-m288"),
    "m6": Motor(6, "xl330-m077"),
}

# PC에 꽂힌 리더 암 포트 확인 (ttyACM0 또는 ttyACM1)
leader_bus = DynamixelMotorsBus(port="/dev/ttyACM0", motors=motors_config)
leader_bus.connect()

print("UDP 송신 시작...")
try:
    while True:
        # 각 관절의 현재 각도 정수값(Present_Position) 읽어오기

        #  obs = leader_bus.sync_read("Present_Position") # 아랫줄 수정 전
        obs = leader_bus.sync_read("Present_Position", normalize=False)
        
        if isinstance(obs, dict):
            positions = [int(obs[k]) for k in motors_config.keys()]
        else:
            positions = [int(x) for x in obs]
        
        # 6개의 정수 데이터를 24바이트로 압축하여 전송
        packet = struct.pack('6i', *positions)
        sock.sendto(packet, (RASPBERRY_PI_IP, UDP_PORT))
        
        time.sleep(1/60)

except KeyboardInterrupt:
    print("\n종료합니다.")
finally:
    leader_bus.disconnect()
    sock.close()