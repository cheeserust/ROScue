# robot: omx_remote_controll_receiver.py
import socket
import struct
import numpy as np
from lerobot.motors.dynamixel import DynamixelMotorsBus

# LeRobot v0.4.4 호환용 커스텀 모터 객체
class Motor:
    def __init__(self, idx, model):
        self.id = idx
        self.model = model

UDP_IP = "0.0.0.0"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

# 팔로워 암 (ID 11~16) - XL430 하단부 포함
motors_config = {
    "m1": Motor(11, "xl430-w250"),
    "m2": Motor(12, "xl430-w250"),
    "m3": Motor(13, "xl430-w250"),
    "m4": Motor(14, "xl330-m288"),
    "m5": Motor(15, "xl330-m288"),
    "m6": Motor(16, "xl330-m288"),
}

# 라즈베리파이 로컬 포트 (ttyACM0)
follower_bus = DynamixelMotorsBus(port="/dev/ttyACM0", motors=motors_config)
follower_bus.connect()

print("UDP 수신 대기 중...")
try:
    while True:
        # 24바이트 수신 대기
        data, addr = sock.recvfrom(24)
        
        # 바이너리를 다시 6개의 정수 배열로 해제
        positions = list(struct.unpack('6i', data))
        
        # 목표 각도(Goal_Position) 일괄 Write
        follower_bus.sync_write("Goal_Position", np.array(positions, dtype=np.int32), normalize=False)

except KeyboardInterrupt:
    print("\n종료합니다.")
finally:
    follower_bus.disconnect()
    sock.close()
