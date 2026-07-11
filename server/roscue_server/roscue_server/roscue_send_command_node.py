# roscue_send_command_node.py (Component D 예시)
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class HardwareCommandNode(Node):
    def __init__(self):
        super().__init__('roscue_send_command_node')
        self.subscription = self.create_subscription(
            String,
            '/roscue/hardware_cmd',
            self.cmd_callback,
            10
        )

    def cmd_callback(self, msg):
        self.get_logger().info(f'메인 노드로부터 물리 하드웨어 제어 명령 수신: {msg.data}')
        # ROS 하위 드라이버나 모터 제어 명령으로 변환하는 로직 구현

def main():
    rclpy.init()
    node = HardwareCommandNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()