# USB 허브에 연결된 장치가 모두 보이는지 확인
import subprocess

print("\n===== USB DEVICE LIST =====\n")

subprocess.run(["lsusb"])

# 확인 항목
# OpenCR
# LiDAR
# Webcam
# Arm Camera
# USB Hurb
# 관련 장치가 lsusb 목록에 나타나는지 확인