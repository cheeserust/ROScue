# robot: roscue_state_publisher_node.py
# State Publisher Node
# 로봇의 배터리/위치/속도/미션상태를 주기적으로 /<robot_name>/state 로 발행한다.

import math

import rclpy
from rclpy.node import Node

from nav_msgs.msg import Odometry
from sensor_msgs.msg import BatteryState
from roscue_interface.msg import RobotStateMsg


class RoscueStatePublisherNode(Node):
    def __init__(self):
        super().__init__('roscue_state_publisher')

        # 로봇 이름은 파라미터로 받는다.
        # 예: ros2 run <pkg> roscue_state_publisher --ros-args -p robot_name:=waffle2
        self.declare_parameter('robot_name', 'waffle1')
        self.robot_name = self.get_parameter('robot_name').value

        # 최신값 보관
        self.battery = 0.0
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.linear_velocity = 0.0
        self.angular_velocity = 0.0
        self.mission_status = 'idle'   # TODO: 실제 미션 상태와 연결 필요

        # 터틀봇 표준 토픽 구독
        self.create_subscription(Odometry, 'odom', self.on_odom, 10)
        self.create_subscription(BatteryState, 'battery_state', self.on_battery, 10)

        # 상태 발행 (1초 주기)
        self.pub = self.create_publisher(RobotStateMsg, f'/{self.robot_name}/state', 10)
        self.create_timer(1.0, self.publish_state)

        self.get_logger().info(f'state publisher ready: {self.robot_name}')

    def on_odom(self, msg):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y
        self.yaw = self._yaw_from_quaternion(msg.pose.pose.orientation)
        self.linear_velocity = msg.twist.twist.linear.x
        self.angular_velocity = msg.twist.twist.angular.z

    def on_battery(self, msg):
        # 드라이버에 따라 0.0~1.0 또는 0~100 으로 들어온다
        self.battery = msg.percentage

    def publish_state(self):
        msg = RobotStateMsg()
        msg.robot_name = self.robot_name
        msg.battery = float(self.battery)
        msg.x = float(self.x)
        msg.y = float(self.y)
        msg.yaw = float(self.yaw)
        msg.linear_velocity = float(self.linear_velocity)
        msg.angular_velocity = float(self.angular_velocity)
        msg.mission_status = self.mission_status
        self.pub.publish(msg)

    def _yaw_from_quaternion(self, q):
        # 쿼터니언 -> yaw(z축 회전). 외부 모듈 없이 직접 계산.
        siny = 2.0 * (q.w * q.z + q.x * q.y)
        cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        return math.atan2(siny, cosy)


def main():
    rclpy.init()
    node = RoscueStatePublisherNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
