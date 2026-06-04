# Python 파일보다 터미널 명령이 더 적합

# 08 라즈베리파이
# ros2 launch turtlebot3_bringup robot.launch.py

# 09 새 터미널 오픈 후
# ros2 topic list
# 확인 
# /scan
# /cmd_vel
# /joint_states

# 10 LiDAR 확인
# ros2 topic echo /scan
# ranges:
# - 1.2
# - 1.3
# - 1.1
# ... 계속 출력

# 최종 순서
# 1. 01_usb_check.py
# 2. 02_serial_check.py
# 3. 03_camera_info.py
# 4. 04_single_camera_test.py
# 5. 05_dual_camera_test.py
# 6. 06_opencr_check.py
# 7. ros2 launch turtlebot3_bringup robot.launch.py
# 8. ros2 topic list
# 9. ros2 topic echo /scan
# 10. 07_system_monitor.py

# USB 허브 → 시리얼 장치 → 카메라 → OpenCR → ROS2 → LiDAR → 시스템 부하를 단계적으로 검증