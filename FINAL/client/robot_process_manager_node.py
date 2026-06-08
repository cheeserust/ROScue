# robot: roscue_process_manager_node.py
import os
import signal
import subprocess
import time

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor

from roscue_interface.srv import TaskCommandSrv


SOURCE = "source /opt/ros/jazzy/setup.bash && source /home/kkh/turtlebot3_ws/install/setup.bash"

TASK_DICTIONARY = {
    'camera_position': {
        'cmd': ['python3', '/home/kkh/robot_ws/src/roscue_client/roscue_client/omx_camera_position_script.py'],
        'processor_name': 'omx_camera_position_script.py'
    },
    'robot_omx_manual_control': {
        'cmd': ['bash', '-lc', f"{SOURCE} && ros2 run roscue_client robot_omx_manual_control"],
        'processor_name': 'robot_omx_manual_control'
    },
    'follower': {
        'cmd': ['bash', '-lc', f"{SOURCE} && ros2 run robot_apps follower_node"],
        'processor_name': 'follower_node'
    },
    'navigation': {
        'cmd': ['bash', '-lc', f"{SOURCE} && ros2 launch robot_apps nav.launch.py"],
        'processor_name': 'nav.launch.py'
    },
    'remote_control': {
        'cmd': ['python3', '/home/kkh/robot_ws/src/roscue_client/roscue_client/omx_remote_controll_receiver.py'],
        'processor_name': 'omx_remote_controll_receiver.py'
    }
}

class RoscueProcessManagerNode(Node):
    def __init__(self, robot_name="waffle1"): # 실제 로봇 이름에 맞게 변경 가능
        super().__init__(f'{robot_name}_process_manager')
        self.active_processes_map = {}  # task_name -> subprocess.Popen 객체 저장

        self.task_command_server = self.create_service(TaskCommandSrv, f'/{robot_name}/task_command', self.task_command_callback)
        
        self.get_logger().info(f"[{robot_name}] ProcessManager Ready. Task list: {list(TASK_DICTIONARY.keys())}")

    def _spawn_task_process(self, task_name):
        # 1. 이미 실행 중인지 확인
        if task_name in self.active_processes_map:
            if self.active_processes_map[task_name].poll() is None:
                return False, f'이미 실행 중입니다: {task_name}'

        # 2. 명령어 가져오기
        task_info = TASK_DICTIONARY.get(task_name)

        if not task_info:
            return False, f'등록되지 않은 Task입니다: {task_name}'

        # 3. 프로세스 그룹 단위로 실행 (bash -lc 로 킨 자식 노드까지 나중에 한 번에 죽이기 위함)
        try:
            proc = subprocess.Popen(
                task_info['cmd'], 
                preexec_fn=os.setsid, 
            )
            self.active_processes_map[task_name] = proc
            return True, f'성공적으로 시작됨: {task_name}'
        except Exception as e:
            return False, f'실행 실패: {e}'

    def _stop_task(self, task_name):
        proc = self.active_processes_map.get(task_name)
        task_info = TASK_DICTIONARY.get(task_name)

        # 1. 프로세스 객체가 남아있을 때 안전하게 종료
        if proc and proc.poll() is None:
            try:
                # Ctrl+C (SIGINT) 시그널을 그룹 전체에 전송
                os.killpg(os.getpgid(proc.pid), signal.SIGINT)
                
                # ROS가 멈추지 않도록 최대 1초만 기다림
                try:
                    proc.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    # 1초안에 안 죽으면 강제 종료 (SIGKILL)
                    self.get_logger().warning(f"강제 종료 시도 (SIGKILL): {task_name}")
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    proc.wait(timeout=0.5)
                finally:
                    self.get_logger().warning(f"강제 종료  완료 (SIGKILL)")

            except Exception as e:
                self.get_logger().error(f"종료 중 에러: {e}")
            finally:
                del self.active_processes_map[task_name]
                self.get_logger().info(f"active_processes_map에서 지우기 완료")
        
        # 2. 혹시나 남아있는 찌꺼기(좀비) 프로세스들을 패턴으로 한 번 더 확인사살
        if task_info:
            processor_name = task_info['processor_name']
            # pkill을 백그라운드로 실행하여 ROS 딜레이 방지
            subprocess.run(['pkill', '-2', '-f', processor_name], stderr=subprocess.DEVNULL)
            
        return True, f'성공적으로 종료됨: {task_name}'

    def _status_task(self, task_name):
        proc = self.active_processes_map.get(task_name)
        if proc and proc.poll() is None:
            return True, '현재 상태: 실행 중(Running)'
        return True, '현재 상태: 정지됨(Stopped)'

    def task_command_callback(self, request, response):
        robot_name = request.robot_name.strip()
        task_name = request.task_name.strip()
        action = request.action.strip().lower()

        self.get_logger().info(f"명령 수신 - Robot: {robot_name} Task: {task_name}, Action: {action}")

        if task_name not in TASK_DICTIONARY:
            response.accepted = False
            response.message = f'알 수 없는 작업: {task_name}'
            return response

        try:
            if action == 'start':
                ok, msg = self._spawn_task_process(task_name)
            elif action == 'stop':
                ok, msg = self._stop_task(task_name)
            elif action == 'restart':
                self._stop_task(task_name)
                # 재시작 시 포트 꼬임 등을 방지하기 위해 잠시 대기
                time.sleep(1.0)
                ok, msg = self._spawn_task_process(task_name)
            elif action == 'status':
                ok, msg = self._status_task(task_name)
            else:
                ok, msg = False, f'지원하지 않는 Action: {action}'
        except Exception as e:
            ok, msg = False, f'내부 에러 발생: {e}'

        response.accepted = ok
        response.message = msg
        return response


def main():
    rclpy.init()
    node = RoscueProcessManagerNode()
    
    # 서비스 호출 중 블로킹을 방지하기 위해 멀티스레드 이그제큐터 사용
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info("종료 중...")
        # 노드가 꺼질 때 task 끄기
        for task in list(node.active_processes_map.keys()):
            node._stop_task(task)
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()