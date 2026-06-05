# server pc: roscue_send_command_node.py
# Application Layer
# Flask가 보낸 명령을 받아 ServiceClientManager 를 통해 해당 로봇에게 전달한다.

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup

from roscue_interface.srv import TaskCommandSrv
from service_client_manager import ServiceClientManager


ROBOT_SERVICES = {
    'waffle1': '/waffle1/task_command',
    'waffle2': '/waffle2/task_command',
}


class RoscueMainServerNode(Node):
    def __init__(self):
        super().__init__('roscue_main_server')

        # ★ 핵심 ★
        # 서비스 콜백(handle_fleet_command) 안에서 다시 로봇 서비스를 await 로 부른다.
        # 기본 콜백 그룹(MutuallyExclusive)은 "한 번에 콜백 하나"라서,
        # await 로 기다리는 동안 그 응답을 처리하지 못해 멈춘다(데드락).
        # 서비스와 클라이언트를 같은 ReentrantCallbackGroup 으로 묶으면 풀린다.
        self.cb_group = ReentrantCallbackGroup()

        # ROS2 Interface Layer (같은 콜백 그룹을 넘긴다)
        self.client_manager = ServiceClientManager(self, ROBOT_SERVICES, self.cb_group)

        # --- (선택) 모니터링을 쓰려면 아래 2줄을 켜세요. ---
        # from robot_manager import RobotManager
        # self.robot_manager = RobotManager(self, list(ROBOT_SERVICES.keys()))

        # 외부(Flask) 요청을 받는 서비스 서버 (같은 콜백 그룹)
        self.create_service(
            TaskCommandSrv, '/roscue/command_server',
            self.handle_fleet_command,
            callback_group=self.cb_group,
        )

        self.get_logger().info(
            f'main server ready. robots={list(ROBOT_SERVICES.keys())}'
        )

    async def handle_fleet_command(self, request, response):
        robot_name = request.robot_name.strip()
        task_name = request.task_name.strip()
        action = request.action.strip().lower()

        self.get_logger().info(f'request: {robot_name} / {task_name} / {action}')

        result = await self.client_manager.send_command(robot_name, task_name, action)

        response.accepted = result.accepted
        response.message = result.message
        return response


def main():
    rclpy.init()
    node = RoscueMainServerNode()

    # ReentrantCallbackGroup 은 MultiThreadedExecutor 와 함께 써야 효과가 있다.
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()