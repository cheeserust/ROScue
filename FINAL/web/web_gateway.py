# ros_gateway.py
import threading
import rclpy
from rclpy.node import Node
from roscue_interface.srv import TaskCommandSrv
from roscue_dto import RoscueTaskDTO

ROS_DOMAIN_ID = 14

class FlaskRosClient(Node):
    def __init__(self):
        super().__init__("flask_ros_client")
        # 메인 서버에서 바꾼 서비스 이름 /api/web_command 로 매핑
        self.web_command_client = self.create_client(TaskCommandSrv, "/api/web_command")

    def call_main_server(self, dto: RoscueTaskDTO, timeout_sec=20.0):
        # 서비스가 살아있는지 3초 기다려봄
        if not self.web_command_client.wait_for_service(timeout_sec=3.0):
            return False, "Main Server unavailable"

        # 요청 만들기
        req = TaskCommandSrv.Request()
        req.robot_name = dto.robot_name
        req.task_name = dto.task_name
        req.action = dto.action.value

        # 비동기로 호출 (결과는 나중에 future 안에 들어옴)
        future = self.web_command_client.call_async(req)

        # "응답이 도착했다"는 신호를 받을 이벤트
        done_event = threading.Event()

        # future가 끝나면 호출될 콜백 함수
        # add_done_callback이 future 자신을 인자로 넘겨주므로 finished_future를 받음
        def on_response_done(finished_future):
            done_event.set()   # 신호 켜기

        future.add_done_callback(on_response_done)

        # 응답이 올 때까지 기다림. timeout 안에 신호가 안 켜지면 False 반환
        if not done_event.wait(timeout=timeout_sec):
            return False, "ROS service timeout"

        # 여기 왔다는 건 응답이 도착했다는 뜻
        try:
            resp = future.result()
            return resp.accepted, resp.message
        except Exception as e:
            return False, f"Execution error: {e}"


# ROS2 spin을 백그라운드 스레드에서 돌려주는 함수
def start_ros_thread():
    rclpy.init(domain_id=ROS_DOMAIN_ID)
    node = FlaskRosClient()

    # 스레드가 실행할 함수 (지금 실행하지 않고, 함수 자체를 넘김)
    def spin_node():
        rclpy.spin(node)

    t = threading.Thread(target=spin_node, daemon=True)
    t.start()
    return node