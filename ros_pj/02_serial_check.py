# OpenCR, LiDAR, OMX Arm 시리얼 포트 확인
import serial.tools.list_ports

print("\n===== SERIAL PORT CHECK =====\n")

ports = serial.tools.list_ports.comports()

if len(ports) == 0:
    print("시리얼 장치 없음")

for port in ports:
    print(f"PORT : {port.device}")
    print(f"DESC : {port.description}")
    print("-" * 50)