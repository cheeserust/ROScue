import json

import rclpy
from rclpy.node import Node

from my_interfaces.srv import TaskCommand


# robot_name -> 그 로봇의 task_command 서비스 이름 (직접 하드코딩)
ROBOT_SERVICES = {
    'robot1': '/robot1/task_command',
    'robot2': '/robot2/task_command',
}


class FleetManagerNode(Node):
    def __init__(self):
        super().__init__('fleet_manager')
        self.clients = {}
        for robot_name, service_name in ROBOT_SERVICES.items():
            self.clients[robot_name] = self.create_client(
                TaskCommand,
                service_name
            )
        self.get_logger().info(
            f'FleetManager ready. robots={list(ROBOT_SERVICES.keys())}'
        )

    def send_command(self, robot_name, task_name, action, params=None, timeout_sec=5.0):
        if robot_name not in self.clients:
            self.get_logger().error(f'unknown robot: {robot_name}')
            return False, 'unknown robot'

        client = self.clients[robot_name]
        if not client.wait_for_service(timeout_sec=2.0):
            self.get_logger().error(f'service unavailable: {robot_name}')
            return False, 'service unavailable'

        req = TaskCommand.Request()
        req.robot_name = robot_name
        req.task_name = task_name
        req.action = action
        req.args_json = json.dumps(params or {}, ensure_ascii=False)

        future = client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout_sec)

        if not future.done():
            return False, 'timeout'
        try:
            resp = future.result()
            return bool(resp.accepted), resp.message
        except Exception as e:
            return False, f'call failed: {e}'


def main():
    rclpy.init()
    node = FleetManagerNode()

    # 예시: robot1의 camera_ai 시작
    ok, msg = node.send_command(
        robot_name='robot1',
        task_name='camera_ai',
        action='start',
        params={'model': 'yolo'}
    )
    node.get_logger().info(f'result: {ok}, {msg}')

    # 계속 노드로 쓸 거면 spin 유지
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()