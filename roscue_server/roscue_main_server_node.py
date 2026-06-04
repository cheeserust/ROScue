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
        self.clients = {}
        for robot_name, service_name in ROBOT_SERVICES.items():
            self.clients[robot_name] = self.create_client(TaskCommandSrv, service_name)

        # 2. 외부(Flask 등) 요청을 받을 서비스 서버 생성
        self.create_service(
            TaskCommandSrv, "/fleet/task_command", self.handle_fleet_command
        )

        self.get_logger().info(f"roscue_main_server 시작 (Async 모드). 등록 로봇: {list(self.robot_services.keys())}")

        self.get_logger().info(f'roscue_main_server ready. robots={list(ROBOT_SERVICES.keys())}')

    def send_command(self, robot_name, task_name, action, timeout_sec=5.0):
        if robot_name not in self.clients:
            self.get_logger().error(f'unknown robot: {robot_name}')
            return False, 'unknown robot'

        client = self.clients[robot_name]
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
        """외부에서 들어오는 명령을 처리하는 서비스 콜백 (Async)"""
        robot_name = request.robot_name.strip()
        task_name = request.task_name.strip()
        action = request.action.strip().lower()

        self.get_logger().info(
            f"명령 수신 -> 로봇: {robot_name}, 작업: {task_name}, 액션: {action}"
        )

        # 핵심: 내부의 send_command 비동기 함수를 await로 호출합니다.
        ok, msg = await self.send_command(robot_name, task_name, action)

        # 결과를 응답 객체에 담아 리턴
        response.accepted = ok
        response.message = msg
        return response
    
    def _dto_from_request(self, request: TaskCommandSrv.Request) -> RoscueTaskDTO:
        return RoscueTaskDTO(
            robot_name=request.robot_name.strip(),
            task_name=request.task_name.strip(),
            action=TaskAction(request.action.strip().lower()),
        )

    def _request_from_dto(self, dto: RoscueTaskDTO) -> TaskCommandSrv.Request:
        req = TaskCommandSrv.Request()
        req.robot_name = dto.robot_name
        req.task_name = dto.task_name
        req.action = dto.action.value
        return req
    

    async def send_command2(
        self, robot_name, task_name, action, timeout_sec=5.0
    ):
        """실제 로봇에게 비동기로 명령을 전달하는 핵심 함수 (Async)"""

        # 1. 등록된 로봇인지 확인 후 클라이언트 동적 생성 (캐싱)
        if robot_name not in self.clients:
            if robot_name not in self.robot_services:
                self.get_logger().error(f"알 수 없는 로봇: {robot_name}")
                return False, "unknown robot"

            service_name = self.robot_services[robot_name].get("task_service")
            if not service_name:
                return False, "invalid service configuration in yaml"

            # 클라이언트 생성 및 저장
            self.clients[robot_name] = self.create_client(
                TaskCommandSrv, service_name
            )

        client = self.clients[robot_name]

        # 2. 로봇 서비스가 준비되었는지 확인
        if not client.wait_for_service(timeout_sec=2.0):
            self.get_logger().error(
                f"로봇 서비스 연결 불가: {robot_name} ({client.srv_name})"
            )
            return False, "service unavailable"

        # 3. 로봇에게 보낼 Request 객체 생성
        req = TaskCommandSrv.Request()
        req.robot_name = robot_name
        req.task_name = task_name
        req.action = action

        # 4. 핵심 변경점: 중복 spin 없이 await로 결과를 기다림
        try:
            self.get_logger().info(
                f"로봇 [{robot_name}]에게 서비스 요청 중..."
            )

            # call_async() 뒤에 바로 await를 붙이면, 응답이 올 때까지
            # 메인 스레드를 블러킹하지 않고(양보하고) 얌전히 기다립니다.
            resp = await client.call_async(req)

            return bool(resp.accepted), resp.message

        except Exception as e:
            self.get_logger().error(f"서비스 호출 중 예외 발생: {e}")
            return False, f"call failed: {e}"

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