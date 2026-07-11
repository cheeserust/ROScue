# web_gateway.py
# Flask ↔ ROS2 브리지. Flask 스레드에서 ROS 서비스를 비동기 호출하고 결과를 동기적으로 반환.
import threading

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist, TwistStamped
from roscue_interface.srv import TaskCommandSrv
from roscue_dto import RoscueTaskDTO

DOMAIN       = {'pinky': 13, 'wf1': 14, 'wf2': 15}  # central_server와 동일
ROBOT_LIST   = list(DOMAIN)
_TWIST_ROBOTS = {'pinky'}  # geometry_msgs/Twist 사용 (구형 펌웨어)

ROS_DOMAIN_ID = 10     # 서버 전용 도메인 (코디네이터와 동일). cmd_vel 은 브릿지가 로봇 도메인으로 전달
_CALL_TIMEOUT = 20.0   # 서비스 응답 대기 최대 시간 (초)
_SVC_TIMEOUT  = 3.0    # 서비스 존재 확인 대기 시간 (초)


class FlaskRosClient(Node):
    def __init__(self):
        super().__init__('flask_ros_client')
        self.web_command_client = self.create_client(TaskCommandSrv, '/api/web_command')
        self.cmd_vel_pubs = {
            r: self.create_publisher(Twist, f'/{r}/cmd_vel', 10)
            if r in _TWIST_ROBOTS
            else self.create_publisher(TwistStamped, f'/{r}/cmd_vel', 10)
            for r in ROBOT_LIST
        }

    def _wait_future(self, future, timeout=_CALL_TIMEOUT):
        done = threading.Event()
        future.add_done_callback(lambda _: done.set())
        if not done.wait(timeout=timeout):
            return False, 'ROS service timeout'
        try:
            resp = future.result()
            return resp.accepted, resp.message
        except Exception as e:
            return False, f'Execution error: {e}'

    def publish_teleop(self, robot_name: str, linear_x: float, angular_z: float):
        pub = self.cmd_vel_pubs.get(robot_name)
        if not pub:
            return False, f'알 수 없는 로봇: {robot_name}'
        if robot_name in _TWIST_ROBOTS:
            msg = Twist()
            msg.linear.x  = float(linear_x)
            msg.angular.z = float(angular_z)
        else:
            msg = TwistStamped()
            msg.header.stamp   = self.get_clock().now().to_msg()
            msg.twist.linear.x = float(linear_x)
            msg.twist.angular.z = float(angular_z)
        pub.publish(msg)
        return True, 'ok'

    def get_robot_status(self) -> dict:
        return {
            r: self.cmd_vel_pubs[r].get_subscription_count() > 0
            for r in ROBOT_LIST
        }

    def get_box_list(self) -> str:
        if not self.web_command_client.wait_for_service(timeout_sec=_SVC_TIMEOUT):
            return '[]'
        req = TaskCommandSrv.Request()
        req.task_name = 'list_boxes'
        _accepted, message = self._wait_future(
            self.web_command_client.call_async(req))
        return message

    def call_main_server(self, dto: RoscueTaskDTO):
        if not self.web_command_client.wait_for_service(timeout_sec=_SVC_TIMEOUT):
            return False, 'CentralServer unavailable'
        req = TaskCommandSrv.Request()
        req.robot_name = dto.robot_name
        req.task_name  = dto.task_name
        req.action     = dto.action
        req.box_id     = dto.box_id
        return self._wait_future(self.web_command_client.call_async(req))


def start_ros_thread() -> FlaskRosClient:
    """ROS2 spin을 데몬 스레드로 실행하고 노드 인스턴스 반환."""
    rclpy.init(domain_id=ROS_DOMAIN_ID)
    node = FlaskRosClient()
    threading.Thread(target=lambda: rclpy.spin(node), daemon=True).start()
    return node
