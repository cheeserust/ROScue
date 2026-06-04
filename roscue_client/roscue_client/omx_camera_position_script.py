
import time
import sys
import signal


from lerobot.motors.dynamixel import DynamixelMotorsBus
from lerobot.motors.dynamixel.dynamixel import OperatingMode


#=======================================#
# 터틀봇에서 실행 할 코드
#=======================================#
POSITION_MODE = OperatingMode.POSITION.value
PORT = "/dev/ttyACM0"
READ_MODE = False


# norm_mode 안쓰고 최소한으로
class Motor:
    def __init__(self, idx, model):
        self.id = idx
        self.model = model

MOTORS = {
    "m1": Motor(11, "xl430-w250"),
    "m2": Motor(12, "xl430-w250"),
    "m3": Motor(13, "xl430-w250"),
    "m4": Motor(14, "xl330-m288"),
    "m5": Motor(15, "xl330-m288"),
    "m6": Motor(16, "xl330-m288"),
}

TARGET_POSE = {'m1': 2038, 'm2': 737, 'm3': 3155, 'm4': 1881, 'm5': 2060, 'm6': 2990}







def main():

    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))

    follower_bus = DynamixelMotorsBus(port=PORT, motors=MOTORS)
    follower_bus.connect()

    try:
        if READ_MODE:
            follower_bus.disable_torque()
            print("토크 OFF. 팔을 원하는 자세로 잡고 Enter 를 누르세요.")
            input()
            pose = follower_bus.sync_read("Present_Position", normalize=False)
            print("\n현재 포즈 (이 값을 TARGET_POSE 에 넣으세요):")
            print(pose)
            return

        # 1) 토크 OFF 상태에서 속도 설정
        follower_bus.disable_torque()
        for motor in follower_bus.motors:
            follower_bus.write("Operating_Mode", motor, POSITION_MODE)
            follower_bus.write("Profile_Velocity", motor, 60)      # 작을수록 천천히 이동
            follower_bus.write("Profile_Acceleration", motor, 20)

        # 2) 토크 ON
        follower_bus.enable_torque()

        # 3) 특정 포즈로 이동 → 모터가 알아서 유지
        follower_bus.sync_write("Goal_Position", TARGET_POSE, normalize=False)
        print("특정 포즈로 이동했습니다. 토크가 살아있는 동안 자세를 유지합니다.")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n종료합니다. (토크는 유지되어 자세가 풀리지 않습니다)")
    finally:
        follower_bus.disconnect()


if __name__ == "__main__":
    main()