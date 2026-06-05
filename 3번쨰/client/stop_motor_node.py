from lerobot.motors.dynamixel import DynamixelMotorsBus

class Motor:
    def __init__(self, idx, model):
        self.id = idx
        self.model = model

MOTORS = {
    "m1": Motor(11, "xl430-w250"), "m2": Motor(12, "xl430-w250"),
    "m3": Motor(13, "xl430-w250"), "m4": Motor(14, "xl330-m288"),
    "m5": Motor(15, "xl330-m288"), "m6": Motor(16, "xl330-m288"),
}

bus = DynamixelMotorsBus(port="/dev/ttyACM0", motors=MOTORS)
bus.connect()
bus.disable_torque()
bus.disconnect()
print("토크 OFF 완료")