# server pc: service_client_manager.py
# ROS2 Interface Layer
# 비즈니스 로직(main_server)이 ROS2 서비스 클라이언트를 직접 다루지 않도록 감싼다.

from roscue_interface.srv import TaskCommandSrv
from roscue_dto import TaskResultDTO


class ServiceClientManager:
    def __init__(self, node, robot_services, callback_group=None):
        # node          : 클라이언트를 만들 ROS2 노드
        # robot_services: { 'waffle1': '/waffle1/task_command', ... }
        # callback_group: main_server 와 같은 그룹을 넘겨받는다 (데드락 방지)
        self._node = node
        self._clients = {}
        for robot_name, service_name in robot_services.items():
            self._clients[robot_name] = node.create_client(
                TaskCommandSrv, service_name, callback_group=callback_group
            )

    def has_robot(self, robot_name):
        return robot_name in self._clients

    async def send_command(self, robot_name, task_name, action):
        client = self._clients.get(robot_name)
        if client is None:
            return TaskResultDTO(False, f'unknown robot: {robot_name}')

        if not client.wait_for_service(timeout_sec=10.0):
            return TaskResultDTO(False, f'robot [{robot_name}] service unavailable')

        req = TaskCommandSrv.Request()
        req.robot_name = robot_name
        req.task_name = task_name
        req.action = action

        try:
            # await 로 호출 -> 데드락 없이 응답을 기다린다.
            resp = await client.call_async(req)
            return TaskResultDTO(bool(resp.accepted), resp.message)
        except Exception as e:
            return TaskResultDTO(False, f'robot call failed: {e}')