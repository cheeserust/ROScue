#!/usr/bin/env python3
"""
roscue_service_relay.py
domain_bridge 서비스 remap 대신 사용하는 경량 릴레이.

도메인10에 /{robot}/task_command, /{robot}/arm_pose 서버를 노출하고,
들어온 호출을 해당 로봇 도메인(14/15)의 /task_command, /arm_pose 로 전달한다.

토픽/액션 중계는 domain_bridge 가 계속 담당.
실행:
  ros2 run roscue_server roscue_service_relay
"""
import signal
import threading

import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.context import Context
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions

from roscue_interface.srv import ArmPose, TaskCommandSrv

DOMAIN = {'wf1': 14, 'wf2': 15}
SERVER_DOMAIN = 10
_ROBOT_SVC_TIMEOUT = 15.0  # 로봇 서비스 발견 대기 (초) — arm_pose_server 기동에 ~11s 필요
_CALL_TIMEOUT      = 10.0  # 로봇 서비스 응답 대기 (초)


# ──────────────────────────────────────────────────────────────────────
# 로봇 도메인 클라이언트 노드 (도메인 14 / 15)
# ──────────────────────────────────────────────────────────────────────
class RobotClientNode(Node):
    def __init__(self, robot: str, ctx: Context):
        super().__init__(f'relay_client_{robot}', context=ctx)
        self.task_client = self.create_client(TaskCommandSrv, '/task_command')
        self.arm_client  = self.create_client(ArmPose, '/arm_pose')

    def call_sync(self, client, req) -> object | None:
        """비동기 호출을 threading.Event 로 동기화해 반환. 실패 시 None."""
        if not client.wait_for_service(timeout_sec=_ROBOT_SVC_TIMEOUT):
            self.get_logger().warning(f'로봇 서비스 미발견: {client.srv_name}')
            return None
        future = client.call_async(req)
        done = threading.Event()
        future.add_done_callback(lambda _: done.set())
        if not done.wait(timeout=_CALL_TIMEOUT):
            self.get_logger().warning(f'로봇 서비스 타임아웃: {client.srv_name}')
            return None
        return future.result()


# ──────────────────────────────────────────────────────────────────────
# 서버 도메인 릴레이 노드 (도메인 10)
# ──────────────────────────────────────────────────────────────────────
class ServiceRelayNode(Node):
    def __init__(self, robot_clients: dict[str, RobotClientNode], ctx: Context):
        super().__init__('roscue_service_relay', context=ctx)
        cbg = ReentrantCallbackGroup()

        for robot, clients in robot_clients.items():
            self.create_service(
                TaskCommandSrv, f'/{robot}/task_command',
                lambda req, res, c=clients: self._relay_task(c, req, res),
                callback_group=cbg,
            )
            self.create_service(
                ArmPose, f'/{robot}/arm_pose',
                lambda req, res, c=clients: self._relay_arm(c, req, res),
                callback_group=cbg,
            )

        robots = ', '.join(f'/{r}/task_command·arm_pose' for r in robot_clients)
        self.get_logger().info(f'ServiceRelay 시작 — {robots}')

    def _relay_task(self, clients: RobotClientNode, req, res):
        result = clients.call_sync(clients.task_client, req)
        if result is None:
            res.accepted = False
            res.message  = '[relay] 로봇 task_command 응답 없음'
            return res
        return result

    def _relay_arm(self, clients: RobotClientNode, req, res):
        result = clients.call_sync(clients.arm_client, req)
        if result is None:
            res.done    = False
            res.message = '[relay] 로봇 arm_pose 응답 없음'
            return res
        return result


# ──────────────────────────────────────────────────────────────────────
# main
# ──────────────────────────────────────────────────────────────────────
def main():
    _shutdown = threading.Event()
    signal.signal(signal.SIGINT,  lambda *_: _shutdown.set())
    signal.signal(signal.SIGTERM, lambda *_: _shutdown.set())

    # ── 도메인별 컨텍스트 초기화 ─────────────────────────────────────
    ctx_server = Context()
    rclpy.init(context=ctx_server, domain_id=SERVER_DOMAIN,
               signal_handler_options=SignalHandlerOptions.NO)

    robot_ctxs = {}
    for robot, domain in DOMAIN.items():
        ctx = Context()
        rclpy.init(context=ctx, domain_id=domain,
                   signal_handler_options=SignalHandlerOptions.NO)
        robot_ctxs[robot] = ctx

    # ── 노드 생성 ───────────────────────────────────────────────────
    robot_clients = {
        robot: RobotClientNode(robot, ctx)
        for robot, ctx in robot_ctxs.items()
    }
    relay_node = ServiceRelayNode(robot_clients, ctx_server)

    # ── 익스큐터: 서버는 멀티스레드, 로봇 클라이언트는 각각 단일 스레드 ─
    exec_server = MultiThreadedExecutor(num_threads=4, context=ctx_server)
    exec_server.add_node(relay_node)

    robot_execs = []
    for clients in robot_clients.values():
        ex = MultiThreadedExecutor(num_threads=2, context=clients.context)
        ex.add_node(clients)
        robot_execs.append(ex)

    for ex in robot_execs:
        threading.Thread(target=ex.spin, daemon=True).start()

    try:
        while not _shutdown.is_set():
            exec_server.spin_once(timeout_sec=0.5)
    finally:
        exec_server.shutdown()
        for ex in robot_execs:
            ex.shutdown()
        relay_node.destroy_node()
        for clients in robot_clients.values():
            clients.destroy_node()
        rclpy.shutdown(context=ctx_server)
        for ctx in robot_ctxs.values():
            rclpy.shutdown(context=ctx)


if __name__ == '__main__':
    main()
