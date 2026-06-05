# server pc: roscue_main_server_node.py

import rclpy
from rclpy.node import Node

from roscue_interface.srv import TaskCommandSrv
from roscue_dto import RoscueTaskDTO, TaskAction, TaskResultDTO


ROBOT_SERVICES = {
    'waffle1': '/waffle1/task_command',
    'waffle2': '/waffle2/task_command',
}


class RoscueMainServerNode(Node):
    def __init__(self):
        super().__init__('roscue_main_server')
        self.robot_clients = {}

        for robot_name, service_name in ROBOT_SERVICES.items():
            self.robot_clients[robot_name] = self.create_client(TaskCommandSrv, service_name)
            print(self.robot_clients[robot_name])
        
        # 2. 외부(Flask 등) 요청을 받을 서비스 서버 생성
        self.create_service(
            TaskCommandSrv, "/roscue/command_server", self.handle_fleet_command
        )

        self.get_logger().info(f'사용 가능 로봇 robots={list(ROBOT_SERVICES.keys())}')

        
    async def handle_fleet_command(self, request, response):
        """Flask가 보낸 ROS 2 요청을 처리하는 콜백 (Async)"""
        self.get_logger().info(f'got a request')

        robot_name = request.robot_name.strip()
        task_name = request.task_name.strip()
        action = request.action.strip().lower()

        # 실제 로봇 서비스 호출 (비동기 await)
        result_dto = await self.send_to_robot(robot_name, task_name, action)

        # 서비스 응답 채우기
        response.accepted = result_dto.accepted
        response.message = result_dto.message
        return response
    
    async def send_to_robot(self, robot_name, task_name, action) -> TaskResultDTO:
        if robot_name not in self.robot_clients:
            return TaskResultDTO(False, f"Unknown robot: {robot_name}")

        client = self.robot_clients[robot_name]
        print(f'{robot_name}, {task_name}, {action}')

        if not client.wait_for_service(timeout_sec=10.0):
            return TaskResultDTO(
                False, f"Robot [{robot_name}] service unavailable"
            )

        req = TaskCommandSrv.Request()
        req.robot_name = robot_name
        req.task_name = task_name
        req.action = action
        
        try:
            # await를 통해 싱글 스레드 데드락 없이 대기
            resp = await client.call_async(req)
            return TaskResultDTO(accepted=bool(resp.accepted), message=resp.message)
        except Exception as e:
            return TaskResultDTO(False, f"Robot call failed: {e}")
def main():
    rclpy.init()
    node = RoscueMainServerNode()


    executor = rclpy.executors.MultiThreadedExecutor(num_threads=4)
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