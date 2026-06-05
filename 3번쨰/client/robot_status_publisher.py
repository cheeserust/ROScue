# robot_status_publisher.py (로봇에서 실행)
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json
import time

class RobotStatusNode(Node):
    def __init__(self, robot_name="waffle1"):
        super().__init__(f'{robot_name}_status_node')
        self.robot_name = robot_name
        
        # /roscue/robot_status 라는 토픽으로 방송국 개설
        self.publisher_ = self.create_publisher(String, '/roscue/robot_status', 10)
        
        # 1초마다 방송(타이머 콜백)
        self.timer = self.create_timer(1.0, self.publish_status_callback)
        self.battery_level = 100.0

    def publish_status_callback(self):
        self.battery_level -= 0.1 # 배터리가 닳는 척 시뮬레이션
        
        # 확장성을 위해 JSON 포맷 사용 (데이터 추가가 매우 쉬움)
        status_data = {
            "robot_name": self.robot_name,
            "battery": round(self.battery_level, 1),
            "state": "idle", # "moving", "error" 등
            "timestamp": time.time()
        }
        
        msg = String()
        msg.data = json.dumps(status_data)
        self.publisher_.publish(msg)
        self.get_logger().info(f'상태 송신: {msg.data}')

def main():
    rclpy.init()
    node = RobotStatusNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()