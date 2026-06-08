import rclpy
from rclpy.node import Node
import numpy as np
from roscue_interface.msg import ArmPositions
from lerobot.motors.dynamixel import DynamixelMotorsBus

# ros2 run roscue_client robot_omx_manual_control
# ros2 topic echo /waffle1/goal_positions


class Motor:
    def __init__(self, idx, model):
        self.id = idx
        self.model = model

class FollowerNode(Node):
    def __init__(self):
        super().__init__('robot_omx_manual_control', namespace='waffle1')
        
        # 1. ROS 2 파라미터 선언 (로봇 내부 포트 기본값)
        self.declare_parameter('port', '/dev/ttyACM0')
        port_name = self.get_parameter('port').get_parameter_value().string_value

        # 2. 토픽 서브스크라이버 생성 ('goal_positions' 토픽을 구독)
        self.subscription = self.create_subscription(
            ArmPositions,
            'goal_positions',
            self.listener_callback,
            10)

        # 팔로워 암 모터 설정 (ID 11~16)
        self.motors_config = {
            "m1": Motor(11, "xl430-w250"),
            "m2": Motor(12, "xl430-w250"),
            "m3": Motor(13, "xl430-w250"),
            "m4": Motor(14, "xl330-m288"),
            "m5": Motor(15, "xl330-m288"),
            "m6": Motor(16, "xl330-m288"),
        }

        self.get_logger().info(f"omx 다이나믹셀 버스 연결 중... 포트: {port_name}")
        self.follower_bus = DynamixelMotorsBus(port=port_name, motors=self.motors_config)

        # 토크 on
        self.follower_bus.connect()
        torque_on_dict = {k: 1 for k in self.motors_config.keys()}
        self.follower_bus.sync_write("Torque_Enable", torque_on_dict)

        self.get_logger().info("ROS 2 명령 수신 대기 중...")

    def listener_callback(self, msg):
        try:



            # 수신한 메시지에서 각도 배열 추출
            positions = list(msg.positions)
            goal_dict = {key: int(pos) for key, pos in zip(self.motors_config.keys(), positions)}

            # 목표 각도로 로봇 모터에 입력
            self.follower_bus.sync_write("Goal_Position", goal_dict, normalize=False)
            
        except Exception as e:
            self.get_logger().error(f"다이나믹셀 쓰기 실패: {e}")

    def destroy_node(self):
        self.follower_bus.disconnect()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = FollowerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("노드를 종료합니다.")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()