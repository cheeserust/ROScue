import socket
import struct
import time
from lerobot.motors.dynamixel import DynamixelMotorsBus

# LeRobot 호환용 커스텀 모터 객체
class Motor:
    def __init__(self, idx, model):
        self.id = idx
        self.model = model

# 1. 라즈베리파이 IP 주소 확인 필수!
RASPBERRY_PI_IP = "10.10.14.10" 
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 2. 🔥 PC에는 '리더 암'(ID 1~6)이 연결되어 있어야 합니다!
# (에러가 났던 ID 11~16은 라즈베리파이 코드에만 있어야 합니다)
motors_config = {
    "m1": Motor(1, "xl330-m288"),
    "m2": Motor(2, "xl330-m288"),
    "m3": Motor(3, "xl330-m288"),
    "m4": Motor(4, "xl330-m288"),
    "m5": Motor(5, "xl330-m288"),
    "m6": Motor(6, "xl330-m077"),
}

# PC에 꽂힌 리더 암 포트 확인 (대부분 /dev/ttyACM0)
leader_bus = DynamixelMotorsBus(port="/dev/ttyACM0", motors=motors_config)
leader_bus.connect()

# 🔥 리더 암은 사람이 손으로 움직여야 하므로 토크를 명시적으로 끕니다.
print("리더 모터 토크 해제 중 (수동 조작 모드)...")
try:
    torque_off_dict = {k: 0 for k in motors_config.keys()}
    leader_bus.sync_write("Torque_Enable", torque_off_dict)
except Exception as e:
    print(f"토크 해제 경고 (무시 가능): {e}")

print("UDP 송신 시작...")
try:
    while True:
# 관절 각도 읽기 시도
        try:
            # 관절 각도 읽기 시도
            obs = leader_bus.sync_read("Present_Position", normalize=False)
            
            if isinstance(obs, dict):
                positions = [int(obs[k]) for k in motors_config.keys()]
            else:
                positions = [int(x) for x in obs]
            
            # 정상적으로 읽었을 때만 패킷 전송
            packet = struct.pack('6i', *positions)
            sock.sendto(packet, (RASPBERRY_PI_IP, UDP_PORT))
            
        except ConnectionError as e:
            print(f"다이나믹셀 통신 에러 (스킵함): {e}")
            time.sleep(0.01) # 잠시 쉬어주기
            continue
            
        time.sleep(1/60)

except KeyboardInterrupt:
    print("\n종료합니다.")
finally:
    leader_bus.disconnect()
    sock.close()