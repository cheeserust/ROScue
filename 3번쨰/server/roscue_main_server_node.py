# roscue_main_server_node.py
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from std_msgs.msg import String

import threading
import socket
import json
import subprocess


from roscue_interface.srv import TaskCommandSrv
from rclpy.action import ActionClient
from roscue_interface.action import MoveTaskAction
import os


'''
PC에서 실행할 독립 프로그램 추가
웹 브라우저(Flask) 접속 후:
로봇 이름
Task 이름: joypad_controller (파일 이름에서 .py만 뺀 이름)
Action: START
Main Server가 알아서 joypad_controller.py를 실행하고 관리

케이스 2: 로봇(waffle1, 2)이 직접 수행해야 하는 기능 추가할 때


# 기존 코드
REMOTE_ROBOT_TASKS = ['camera_position'] 
# 수정 후 (명령어 추가)
REMOTE_ROBOT_TASKS = ['camera_position', 'move_to_goal', 'lift_arm']

'''

TCP_HOST = '0.0.0.0'
TCP_PORT = 9999

# 로봇들에게 직접 명령(SRV)을 넘겨줘야 하는 Task 이름 목록
REMOTE_ROBOT_TASKS = ['camera_position', 'move_to_goal'] 

# 메인 서버(PC)가 통신할 로봇들 목록
ROBOT_LIST = ['waffle1', 'waffle2']

class RoscueMainServerNode(Node):
    def __init__(self):
        super().__init__('roscue_main_server')
        
        # 🌟 서비스 안에서 다른 서비스를 부르기 위해 ReentrantCallbackGroup 사용 (데드락 방지)
        self.cb_group = ReentrantCallbackGroup()

        # 1. 로컬 프로세스 관리를 위한 딕셔너리 (omx_manual_control 등)
        self.running_processes = {}

        # 2. 각 로봇에게 명령을 전달할 Client 생성 (/waffle1/task_command 등)
        self.robot_clients = {}
        for robot in ROBOT_LIST:
            self.robot_clients[robot] = self.create_client(
                TaskCommandSrv, 
                f'/{robot}/task_command', 
                callback_group=self.cb_group
            )

        # 3. Flask로부터 명령을 받을 Server 생성 (/roscue/command_server)
        self.create_service(
            TaskCommandSrv, 
            "/roscue/command_server", 
            self.handle_fleet_command,
            callback_group=self.cb_group
        )

        # 4. 하위 노드(자율주행 등)로 데이터를 하달하는 Publisher
        self.nav_cmd_publisher = self.create_publisher(String, '/roscue/nav_cmd', 10)

        # 5. yolo 부터 데이ㅓㅌ 받는 TCP 서버 스레드
        self.tcp_thread = threading.Thread(target=self.run_tcp_server, daemon=True)
        self.tcp_thread.start()


        # Topic 예시
        # 로봇 상태 구독
        self.status_sub = self.create_subscription(
            String,
            '/roscue/robot_status',
            self.robot_status_callback,
            10
        )
        self.fleet_status = {} # 로봇들의 상태를 저장 딕셔너리
        # END

        # Action 예시
        self.robot_progress = {}
        self.action_clients = {}
        for robot in ROBOT_LIST:
            self.action_clients[robot] = ActionClient(self, MoveTaskAction, f'/{robot}/move_action')



        # YOLO로 부터 받아온 값
        self.detection_count = {}



        self.get_logger().info('🚀 메인 컨트롤 노드 시작 (라우팅 & 프로세스 관리 준비 완료)')


    
    # Topic
    # 로봇 상태 구독 콜백
    def robot_status_callback(self, msg):
        try:
            data = json.loads(msg.data)
            robot_name = data['robot_name']
            
            # 최신 상태 업데이트 (나중에 Flask가 요청하면 이 딕셔너리를 던져주면 됨)
            self.fleet_status[robot_name] = data
            
            # 배터리가 20% 이하면 경고!
            if data['battery'] < 20.0:
                self.get_logger().warning(f"{robot_name} 배터리 부족! 충전 필요!")
        except Exception as e:
            self.get_logger().error(f"상태 파싱 에러: {e}")

    # Action
    def send_move_command(self, robot_name, target_name):
        # 1. 딕셔너리에 해당 로봇이 있는지 확인
        if robot_name not in self.move_clients:
            self.get_logger().error(f"등록되지 않은 로봇입니다: {robot_name}")
            return

        # 2. 딕셔너리에서 요청받은 로봇의 액션 클라이언트를 꺼냄 🌟
        client = self.move_clients[robot_name]

        # 3. 해당 로봇의 서버가 켜져 있는지 확인
        if not client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error(f"{robot_name}의 액션 서버가 응답하지 않습니다.")
            return

        goal_msg = MoveTask.Goal()
        goal_msg.target = target_name

        self.get_logger().info(f"[{robot_name}]에게 목적지({target_name}) 전송 완료!")
        
        # 4. 액션 전송
        client.send_goal_async(
            goal_msg, 
            feedback_callback=lambda msg: self.feedback_callback(robot_name, msg) # 어떤 로봇인지 태그 달아서 피드백 함수로 보냄
        )

    # 로봇이 중간중간 보내는 "진행률"을 받는 콜백
    def feedback_callback(self, robot_name, feedback_msg):
        percent = feedback_msg.feedback.percent_complete
        
        # 🌟 로봇 이름을 Key로 하여 최신 퍼센트를 딕셔너리에 덮어쓰기 저장
        self.robot_progress[robot_name] = percent
        self.get_logger().info(f"[{robot_name}] 진행률 갱신: {percent}%")

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('로봇이 명령을 거절했습니다.')
            return

        # 명령이 수락되면 끝날 때까지 기다림
        self.get_result_future = goal_handle.get_result_async()
        self.get_result_future.add_done_callback(self.get_result_callback)

    # 최종 도착했을 때 호출됨
    def get_result_callback(self, future):
        result = future.result().result
        if result.success:
            self.get_logger().info('🎉 로봇이 목적지에 무사히 도착했습니다!')



    def handle_fleet_command(self, request, response):
        """ Flask에서 온 요청을 분류하여 로봇에게 전달하거나, 로컬에서 실행합니다. """
        robot_name = request.robot_name.strip()
        task_name = request.task_name.strip()
        action = request.action.strip().lower()

        self.get_logger().info(f'웹 요청 수신: [{robot_name}] Task: {task_name}, Action: {action}')

        # ---------------------------------------------------------
        # Case A: 로봇이 직접 실행해야 하는 Task (예: camera_position)
        # ---------------------------------------------------------
        if task_name in REMOTE_ROBOT_TASKS:
            if robot_name not in self.robot_clients:
                response.accepted = False
                response.message = f"등록되지 않은 로봇입니다: {robot_name}"
                return response
            
            # 딕셔너리에서 로봇(waffle1) 가져옴
            client = self.robot_clients[robot_name]
            
            # 로봇의 서비스가 켜져 있는지 확인
            if not client.wait_for_service(timeout_sec=3.0):
                response.accepted = False
                response.message = f"로봇 [{robot_name}]의 서비스가 응답하지 않습니다."
                return response

            self.get_logger().info(f"로봇 [{robot_name}]으로 명령 전달 중...")
            

            # 로봇에게 보낼 Request를 작성
            req_to_robot = TaskCommandSrv.Request()
            req_to_robot.robot_name = robot_name
            req_to_robot.task_name = task_name
            req_to_robot.action = action

            try:
                # 동기 호출이지만 ReentrantCallbackGroup 덕분에 안전함
                resp_from_robot = client.call(req_to_robot)
                
                # 로봇의 응답을 그대로 Flask에 반환
                response.accepted = resp_from_robot.accepted
                response.message = resp_from_robot.message
            except Exception as e:
                response.accepted = False
                response.message = f"로봇 명령 전달 실패: {str(e)}"
            
            return response

        # ---------------------------------------------------------
        # Case B: 메인 PC에서 직접 실행해야 하는 Task (예: omx_manual_control)
        # ---------------------------------------------------------
        else:
            try:
                if action == 'start':
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    script_path = os.path.join(current_dir, f"{task_name}.py")
                    
                    
                    if task_name in self.running_processes and self.running_processes[task_name].poll() is None:
                        response.accepted = False
                        response.message = f"이미 실행 중인 로컬 작업입니다: {task_name}"
                    else:
                        proc = subprocess.Popen(['python3', script_path])
                        self.running_processes[task_name] = proc
                        response.accepted = True
                        response.message = f"로컬 프로세스 시작됨: {task_name} (PID: {proc.pid})"

                elif action == 'stop':
                    if task_name in self.running_processes:
                        proc = self.running_processes[task_name]
                        proc.terminate()
                        proc.wait(timeout=2)
                        del self.running_processes[task_name]
                        response.accepted = True
                        response.message = f"로컬 프로세스 종료됨: {task_name}"
                    else:
                        response.accepted = False
                        response.message = "종료할 로컬 작업이 없습니다."
                # ---------------------------------------------------------
                # Case C: 진행률 상태 물어보기 (Flask가 주기적으로 질문함)
                # ---------------------------------------------------------
                elif action == 'status' and task_name == 'move_to_goal': # task_name은 예시
                        # 딕셔너리에 값이 있으면 꺼내고, 없으면 0을 줍니다.
                        current_progress = self.robot_progress.get(robot_name, 0)
                        
                        response.accepted = True
                        response.message = str(current_progress) # "45" 같은 숫자 문자열로 대답
                        return response
    
                elif action == 'status':
                    response.accepted = True
                    response.message = f"실행 중인 로컬 작업: {list(self.running_processes.keys())}"
                
                

            except Exception as e:
                response.accepted = False
                response.message = f"로컬 프로세스 관리 에러: {str(e)}"

            return response


    # =========================================================
    # 아래는 TCP / yolo 데이터 수신 루프 (이전과 동일)
    # =========================================================
    def run_tcp_server(self):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((TCP_HOST, TCP_PORT))
        server_sock.listen(5)

        while True:
            try:
                client_sock, addr = server_sock.accept()
                self.handle_ai_client(client_sock)
            except Exception as e:
                self.get_logger().error(f"TCP 서버 에러: {e}")

    def handle_ai_client(self, client_sock):
        buffer = ""
        while True:
            try:
                data = client_sock.recv(1024) # recv수신 대기(Blocking)
                if not data: break
                buffer += data.decode('utf-8')
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        yolo_data = json.loads(line)
                        self.process_yolo_data(yolo_data)
            except Exception:
                break
        client_sock.close()

    def process_yolo_data(self, data):
        """YOLO(AI 서버)에서 TCP로 받은 JSON 한 줄이 여기로 들어온다."""
        msg_type = data.get("type")

        if msg_type == "count":
            camera = data.get("camera")
            value = data.get("count")
            self.detection_count[camera] = value     # 최신 값 저장 (서비스는 나중에 이걸 읽음)
            self.get_logger().info(f"📥 [{camera}] count = {value}")

        else:
            # 아직 정의 안 한 메시지 타입은 그냥 로그만
            self.get_logger().warn(f"알 수 없는 데이터: {data}")

def main():
    rclpy.init()
    node = RoscueMainServerNode()

    # 쓰레드가 4개인 Executor 사용 (TCP, Service 콜백, Client 등 멀티스레딩)
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        for name, proc in node.running_processes.items():
            proc.terminate()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()