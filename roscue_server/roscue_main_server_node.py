import json

import rclpy
from rclpy.node import Node

from roscue_interface.srv import TaskCommandSrv
from roscue_dto import RoscueTaskDTO, TaskAction, TaskResultDTO


ROBOT_SERVICES = {
    'robot1': '/robot1/task_command',
    'robot2': '/robot2/task_command',
}


class RoscueMainServerNode(Node):
    def __init__(self):
        super().__init__('roscue_main_server')
        self.robot_clients = {}
        self.robot_services = {}
        
        for robot_name, service_name in ROBOT_SERVICES.items():
            self.robot_clients[robot_name] = self.create_client(TaskCommandSrv, service_name)

        # 2. 외부(Flask 등) 요청을 받을 서비스 서버 생성
        self.create_service(
            TaskCommandSrv, "/roscue/task_command", self.handle_fleet_command
        )

        self.get_logger().info(f"roscue_main_server 시작 (Async 모드). 등록 로봇: {list(self.robot_services.keys())}")

        self.get_logger().info(f'roscue_main_server ready. robots={list(ROBOT_SERVICES.keys())}')

    def send_command(self, robot_name, task_name, action, timeout_sec=5.0):
        if robot_name not in self.robot_clients:
            self.get_logger().error(f'unknown robot: {robot_name}')
            return False, 'unknown robot'

        client = self.robot_clients[robot_name]
        if not client.wait_for_service(timeout_sec=2.0):
            self.get_logger().error(f'service unavailable: {robot_name}')
            return False, 'service unavailable'

        req = TaskCommandSrv.Request()
        req.robot_name = robot_name
        req.task_name = task_name
        req.action = action
  
        future = client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout_sec)

        if not future.done():
            return False, 'timeout'
        try:
            resp = future.result()
            return bool(resp.accepted), resp.message
        except Exception as e:
            return False, f'call failed: {e}'
        
    async def handle_fleet_command(self, request, response):
        """Flask가 보낸 ROS 2 요청을 처리하는 콜백 (Async)"""
        robot_name = request.robot_name.strip()
        task_name = request.task_name.strip()
        action = request.action.strip().lower()

        # 실제 로봇 서비스 호출 (비동기 await)
        result_dto = await self.send_to_robot(robot_name, task_name, action)

        # 서비스 응답 채우기
        response.accepted = result_dto.accepted
        response.message = result_dto.message
        return response
    

    async def send_to_robot(
        self, robot_name, task_name, action, params
    ) -> TaskResultDTO:
        """실제 개별 로봇에게 명령을 토스하는 함수"""
        if robot_name not in self.robot_clients:
            if robot_name not in self.robot_services:
                return TaskResultDTO(False, f"Unknown robot: {robot_name}")

            srv_name = self.robot_services[robot_name]["task_service"]
            self.robot_clients[robot_name] = self.create_client(TaskCommandSrv, srv_name)

        client = self.robot_clients[robot_name]

        if not client.wait_for_service(timeout_sec=2.0):
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

    # # 예시: robot1의 camera_ai 시작
    # ok, msg = node.send_command(
    #     robot_name='waffle1',
    #     task_name='camera_position',
    #     action='start',         # action: start, stop, restart, status
    #     params={''}
    # )
    # node.get_logger().info(f'result: {ok}, {msg}')

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()