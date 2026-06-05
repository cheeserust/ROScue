# robot: roscue_process_manager_node.py
# 서버(main_server)로부터 task 명령을 받아 로봇 안에서 프로세스를 켜고 끈다.

import os
import time
import signal
import subprocess

import rclpy
from rclpy.node import Node

from roscue_interface.srv import TaskCommandSrv


# 다룰 수 있는 task 목록
TASKS = ['camera_position', 'follower', 'navigation', 'remote_controll']

# ros2 run / launch 를 실행할 때 공통으로 source 할 setup
SOURCE = (
    "source /opt/ros/jazzy/setup.bash && "
    "source /home/kkh/robot_ws/install/setup.bash && "
)


class RoscueProcessManagerNode(Node):
    def __init__(self):
        super().__init__('roscue_process_manager')

        # task_name -> subprocess.Popen
        # 우리가 직접 띄운 프로세스만 관리한다.
        self.processes = {}

        self.create_service(
            TaskCommandSrv, 'task_command', self.handle_task_command
        )
        self.get_logger().info(f'process manager ready. tasks={TASKS}')

    # --- task 별 실행 명령 (하드코딩) ---
    def _build_command(self, task_name):
        # 주의: 아래 python3 경로는 상대경로다.
        # 이 노드를 워크스페이스 루트에서 실행해야 경로가 맞는다.
        if task_name == 'camera_position':
            return ['python3',
                    'src/roscue_client/roscue_client/omx_camera_position_script.py']
        if task_name == 'follower':
            return ['bash', '-lc', SOURCE + 'ros2 run robot_apps follower_node']
        if task_name == 'navigation':
            return ['bash', '-lc', SOURCE + 'ros2 launch robot_apps nav.launch.py']
        if task_name == 'remote_controll':
            return ['python3',
                    'src/roscue_client/roscue_client/omx_remote_controll_receiver.py']
        return None

    # --- start ---
    def _start_task(self, task_name):
        proc = self.processes.get(task_name)
        if proc is not None and proc.poll() is None:
            return False, f'{task_name} already running'

        cmd = self._build_command(task_name)
        if cmd is None:
            return False, f'no command for {task_name}'

        # 새 프로세스 그룹으로 띄운다.
        # -> 종료할 때 os.killpg 로 자식까지 한 번에 끌 수 있다.
        proc = subprocess.Popen(cmd, preexec_fn=os.setsid)
        self.processes[task_name] = proc
        return True, f'{task_name} started (pid={proc.pid})'

    # --- stop ---
    def _stop_task(self, task_name):
        proc = self.processes.get(task_name)
        if proc is None:
            return False, f'{task_name} is not running'

        if proc.poll() is not None:
            # 이미 죽어 있으면 기록만 정리한다
            del self.processes[task_name]
            return True, f'{task_name} already exited'

        pgid = os.getpgid(proc.pid)

        # 1) SIGINT: 스크립트의 finally(KeyboardInterrupt) 블록이 돌아
        #    모터 disconnect 같은 정리가 안전하게 끝난다.
        os.killpg(pgid, signal.SIGINT)
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            # 2) 5초 안에 안 죽으면 강제 종료
            self.get_logger().warn(f'{task_name} did not stop, sending SIGKILL')
            os.killpg(pgid, signal.SIGKILL)
            proc.wait()

        del self.processes[task_name]
        self.get_logger().info(f'{task_name} stopped')
        return True, f'{task_name} stopped'

    # --- status ---
    def _status_task(self, task_name):
        proc = self.processes.get(task_name)
        if proc is None or proc.poll() is not None:
            return True, f'{task_name} is stopped'
        return True, f'{task_name} is running (pid={proc.pid})'

    # --- restart ---
    def _restart_task(self, task_name):
        self._stop_task(task_name)
        # 모터 스크립트의 경우, USB 시리얼 포트가 풀릴 시간을 잠깐 준다.
        time.sleep(1.0)
        return self._start_task(task_name)

    # --- 서비스 콜백 ---
    def handle_task_command(self, request, response):
        robot_name = request.robot_name
        task_name = request.task_name
        action = request.action.lower().strip()

        if task_name not in TASKS:
            response.accepted = False
            response.message = f'[{robot_name}] unknown task: {task_name}'
            return response

        self.get_logger().info(f'got command: {task_name} / {action}')

        try:
            if action == 'start':
                ok, msg = self._start_task(task_name)
            elif action == 'stop':
                ok, msg = self._stop_task(task_name)
            elif action == 'restart':
                ok, msg = self._restart_task(task_name)
            elif action == 'status':
                ok, msg = self._status_task(task_name)
            else:
                ok, msg = False, f'unknown action: {action}'
        except Exception as e:
            ok, msg = False, f'error: {e}'

        response.accepted = ok
        response.message = f'[{robot_name}] {msg}'
        return response

    # --- 노드가 꺼질 때 우리가 띄운 프로세스 전부 정리 ---
    def shutdown_all(self):
        for task_name in list(self.processes.keys()):
            self._stop_task(task_name)


def main():
    rclpy.init()
    node = RoscueProcessManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown_all()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
