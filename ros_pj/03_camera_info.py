# 카메라가 video0, video1 중 어디에 연결됐는지 확인
import subprocess

print("\n===== CAMERA DEVICE INFO =====\n")

subprocess.run(["v4l2-ctl", "--list-devices"])