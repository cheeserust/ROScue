import os
import signal
import subprocess

import rclpy
from rclpy.node import Node

from roscue_interface.srv import TaskCommand
import subprocess, time


# action: start, stop, restart, status
# task dlfma
TASKS = ['camera_position', 'follower', 'navigation', 'remote_controll']

TASK_PATTERNS = {
    'camera_position': 'omx_camera_position_script.py',
    'follower': 'follower_node',
    'navigation': 'nav.launch.py',
    'remote_controll': 'omx_remote_controll_receiver.py',
}

# ros2 run / launch 실행 시 공통으로 source 할 setup
SOURCE = (
    "source /opt/ros/jazzy/setup.bash && "
    "source /home/kkh/robot_ws/install/setup.bash && "
)


class RoscueProcessManagerNode(Node):
    def __init__(self):
        super().__init__('roscue_process_manager')
        self.processes = {}  # task_name -> subprocess.Popen
        self.service = self.create_service(
            TaskCommand,
            'task_command',
            self.handle_task_command
        )
        self.get_logger().info(
            f"ProcessManager ready. tasks={(TASKS)}"
        )

    def _cleanup(self):
        for pattern in TASK_PATTERNS.values():
            subprocess.run(['pkill', '-2', '-f', pattern])   # -2 = SIGINT


    def _kill_by_pattern(self, pattern):
        # SIGINT → SIGTERM → SIGKILL 순서로, 죽을 때까지 escalate
        for sig in ('-2', '-15', '-9'):
            r = subprocess.run(['pkill', sig, '-f', pattern])
            time.sleep(1)
            # 아직 살아있나 확인
            alive = subprocess.run(['pgrep', '-f', pattern],
                                stdout=subprocess.DEVNULL).returncode == 0
            self.get_logger().info(f"pkill {sig} {pattern} -> alive={alive}, rc={r.returncode}")
            if not alive:
                return True
        return False
    def _build_command(self, task_name):
        # task 이름마다 실행할 명령을 직접 하드코딩
        if task_name == TASKS[0]:
            return ['python3',
                    'src/roscue_client/roscue_client/omx_camera_position_script.py']
        if task_name == TASKS[1]:
            return ['bash', '-lc',
                    SOURCE + 'ros2 run robot_apps follower_node']
        if task_name == TASKS[2]:
            return ['bash', '-lc',
                    SOURCE + 'ros2 launch robot_apps nav.launch.py']
        if task_name == TASKS[3]:
            return ['python3',
                    'src/roscue_client/roscue_client/omx_remote_controll_receiver.py']
        return None

    def _start_task(self, task_name):
        if task_name in self.processes:
            proc = self.processes[task_name]
            if proc.poll() is None:
                return False, f'{task_name} already running'

        cmd = self._build_command(task_name)
        if cmd is None:
            return False, f'no command for {task_name}'

        # 프로세스 그룹으로 띄워야 stop 시 같이 종료하기 편함
        proc = subprocess.Popen(cmd, preexec_fn=os.setsid)
        self.processes[task_name] = proc
        return True, f'{task_name} started'

    def _stop_task(self, task_name):
        proc = self.processes.get(task_name)
        if proc is None:
            self.processes.pop(task_name, None)
            pattern = TASK_PATTERNS.get(task_name)
            if pattern:
                subprocess.run(['pkill', '-2', '-f', pattern])
            return True, f'{task_name} stopped'
        if proc.poll() is not None:
            del self.processes[task_name]
            return False, f'{task_name} already exited'
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGINT)
            proc.wait(timeout=3)
        except Exception:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                pass
        del self.processes[task_name]
        self.get_logger().info(f"stop {(task_name)}")
        return True, f'{task_name} stopped'

    def _status_task(self, task_name):
        proc = self.processes.get(task_name)
        if proc is None:
            return False, 'not running'
        running = proc.poll() is None
        return True, 'running' if running else 'stopped'

    def handle_task_command(self, request, response):
        robot_name = request.robot_name
        task_name = request.task_name
        action = request.action.lower().strip()

        if task_name not in TASKS:
            response.accepted = False
            response.message = f'unknown task: {task_name}'
            return response

        try:
            if action == 'start':
                self.get_logger().info(f"got a message: {(action)}")
                ok, msg = self._start_task(task_name)
            elif action == 'stop':
                self.get_logger().info(f"got a message: {(action)}")
                ok, msg = self._stop_task(task_name)
            elif action == 'restart':
                self.get_logger().info(f"got a message: {(action)}")
                self._stop_task(task_name)
                ok, msg = self._start_task(task_name)
            elif action == 'status':
                self.get_logger().info(f"got a message: {(action)}")
                ok, msg = self._status_task(task_name)
            else:
                ok, msg = False, f'unknown action: {action}'
        except Exception as e:
            ok, msg = False, f'error: {e}'

        response.accepted = ok
        response.message = f'[{robot_name}] {msg}'
        return response


def main():
    rclpy.init()
    node = RoscueProcessManagerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()