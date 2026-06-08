import socket
import struct
import time
from lerobot.motors.dynamixel import DynamixelMotorsBus

# LeRobot 호환용 커스텀 모터 객체
class Motor:
    def __init__(self, idx, model):
        self.id = idx
        self.model = model

ROBOT_IP = "10.10.14.10" 
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

motors_config = {
    "m1": Motor(1, "xl330-m288"),
    "m2": Motor(2, "xl330-m288"),
    "m3": Motor(3, "xl330-m288"),
    "m4": Motor(4, "xl330-m288"),
    "m5": Motor(5, "xl330-m288"),
    "m6": Motor(6, "xl330-m077"),
}

# PC에 꽂힌 리더 암 포트 확인
leader_bus = DynamixelMotorsBus(port="/dev/ttyACM0", motors=motors_config)
leader_bus.connect()

print("omx 조작 전 초기화중...")
try:
    torque_off_dict = {k: 0 for k in motors_config.keys()}
    leader_bus.sync_write("Torque_Enable", torque_off_dict)
except Exception as e:
    print(f"토크 해제 경고 (무시 가능): {e}")

print("초기화 완료. UDP 송신 시작...")
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
            sock.sendto(packet, (ROBOT_IP, UDP_PORT))
            
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