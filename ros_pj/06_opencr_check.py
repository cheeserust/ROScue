# OpenCR 인식 확인
import serial.tools.list_ports

found = False

for port in serial.tools.list_ports.comports():

    if "OpenCR" in port.description:
        found = True
        print("OpenCR 발견")
        print(port.device)

if not found:
    print("OpenCR 미발견")