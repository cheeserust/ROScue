# server pc: roscue_mode_controller_node.py
# 중앙 서버의 "모드 컨트롤러".
# - Flask 와 똑같이 main_server(/roscue/command_server)에 task 명령을 보낸다.
# - 추가로, 서버에 꽂힌 리더 암 송신기(omx_manual_control.py)를 직접 켜고 끈다.
# - 지금은 키보드 1/2/3 으로 모드를 고른다 (나중에 YOLO 로 교체).

import os
import signal
import subprocess

import rclpy
from rclpy.node import Node

from roscue_interface.srv import TaskCommandSrv


ROBOT_NAME = 'waffle1'   # 명령을 보낼 로봇 (필요하면 바꾸세요)

# 서버에 꽂힌 리더 암을 읽어 UDP 로 쏘는 스크립트.
# 경로는 이 노드를 실행하는 위치(워크스페이스 루트) 기준이다.
# 안 맞으면 절대경로로 바꾸세요.
SENDER_CMD = ['python3', '/home/a/Desktop/roscue/ROScue/2번쨰/server/omx_manual_control.py']

# 키 -> 모드 이름
KEY_TO_MODE = {
    '0': 'idle',
    '1': 'camera',
    '2': 'manual',
    '3': 'nav',
}


class RoscueModeControllerNode(Node):
    def __init__(self):
        super().__init__('roscue_mode_controller')
        self.cli = self.create_client(TaskCommandSrv, '/roscue/command_server')
        self.sender_proc = None     # 리더 암 송신 subprocess
        self.current_mode = None
        self.get_logger().info('mode controller ready')

    # --- main_server 로 task 명령 보내기 (Flask 와 같은 서비스) ---
    def send_task(self, task_name, action):
        if not self.cli.wait_for_service(timeout_sec=3.0):
            self.get_logger().warn('main_server unavailable')
            return
        req = TaskCommandSrv.Request()
        req.robot_name = ROBOT_NAME
        req.task_name = task_name
        req.action = action

        future = self.cli.call_async(req)
        # 응답이 올 때까지만 잠깐 spin 한다 (이 노드는 평소엔 안 돈다)
        rclpy.spin_until_future_complete(self, future, timeout_sec=15.0)
        resp = future.result()
        if resp is None:
            self.get_logger().warn(f'{task_name} {action} -> timeout')
        else:
            self.get_logger().info(f'{task_name} {action} -> {resp.message}')

    # --- 서버의 리더 암 송신기 켜기 ---
    def start_leader_sender(self):
        if self.sender_proc is not None and self.sender_proc.poll() is None:
            return
        # 프로세스 그룹으로 띄워서 종료할 때 한 번에 끈다
        self.sender_proc = subprocess.Popen(SENDER_CMD, preexec_fn=os.setsid)
        self.get_logger().info(f'leader sender started (pid={self.sender_proc.pid})')

    # --- 서버의 리더 암 송신기 끄기 ---
    def stop_leader_sender(self):
        proc = self.sender_proc
        self.sender_proc = None
        if proc is None or proc.poll() is not None:
            return
        pgid = os.getpgid(proc.pid)
        # SIGINT: 스크립트의 finally 가 돌아 리더 암 disconnect + 소켓 close
        os.killpg(pgid, signal.SIGINT)
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            os.killpg(pgid, signal.SIGKILL)
            proc.wait()
        self.get_logger().info('leader sender stopped')

    # --- 모드 적용 ('어떻게 실행하나' 부분. 판단과 분리되어 있다) ---
    def set_mode(self, mode):
        if mode == self.current_mode:
            self.get_logger().info(f'already in [{mode}]')
            return

        # 1) 항상 전부 끈다 (같은 팔/포트를 두 개가 쓰면 충돌하니까)
        self.stop_leader_sender()
        self.send_task('remote_controll', 'stop')
        self.send_task('camera_position', 'stop')
        self.send_task('navigation', 'stop')

        # 2) 고른 모드만 켠다
        if mode == 'manual':
            self.send_task('remote_controll', 'start')   # 로봇이 UDP 받을 준비
            self.start_leader_sender()                   # 서버가 리더 암 읽어 송신
        elif mode == 'camera':
            self.send_task('camera_position', 'start')
        elif mode == 'nav':
            self.send_task('navigation', 'start')        # 임시: nav 노드 아직 미완성
        # mode == 'idle' 이면 아무것도 안 켜고 정지 상태로 둔다

        self.current_mode = mode
        self.get_logger().info(f'mode -> [{mode}]')

    # --- 키 입력 루프 (지금은 키보드, 나중에 YOLO 판단으로 교체) ---
    def run(self):
        self._print_help()
        while True:
            key = input('mode> ').strip()
            if key in ('q', 'quit'):
                break
            mode = KEY_TO_MODE.get(key)
            if mode is None:
                print('  0=정지  1=카메라  2=수동조작  3=자율주행  q=종료')
                continue
            self.set_mode(mode)

    def _print_help(self):
        print('========================================')
        print(' ROSCUE 모드 컨트롤러')
        print('  0 = 정지 (idle)')
        print('  1 = 카메라 자세 (camera_position)')
        print('  2 = 수동 조작 (리더 암 텔레오퍼레이션)')
        print('  3 = 자율주행 (navigation, 임시)')
        print('  q = 종료')
        print('========================================')


def main():
    rclpy.init()
    node = RoscueModeControllerNode()
    try:
        node.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.stop_leader_sender()   # 종료할 때 송신기도 정리
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()