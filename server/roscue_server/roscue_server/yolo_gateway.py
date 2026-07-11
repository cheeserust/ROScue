# yolo_gateway.py
#
# 역할: yolo_server(추론 프로세스)와 ROS2 사이의 브리지.
#   - TCP 서버: 추론 결과 수신 (이벤트, 제어값)
#   - ROS publisher: /yolo/event, /{robot}/cmd_vel
#   - ROS service: /yolo/set_mode → 추론 서버에 모드 변경 명령 중계
#
# ──────────────────────────────────────────────────────────────
# 추론 서버 ↔ 게이트웨이 TCP 프로토콜 (줄바꿈 구분 JSON)
#
#  추론서버 → 게이트웨이:
#    {"type":"hello",   "robot_name":"wf1"}
#    {"type":"event",   "robot_name":"wf1", "event_type":"BOX_FOUND"}
#    {"type":"control", "robot_name":"wf1", "linear_x":0.12, "angular_z":0.3,
#                       "arrived":false, "control_active":true}
#
#  게이트웨이 → 추론:
#    {"cmd":"set_mode", "robot_name":"wf1", "stream":"wrist_cam", "mode":"EXPLOSIVE_DETECTION_MODEL"}
#
#  event_type 값: BOX_FOUND | ARRIVED | BOX_COVER_OPEN | EXPLOSIVE_FOUND | EMPTY
#  mode 값:       BOX_DETECTION_MODEL | EXPLOSIVE_DETECTION_MODEL | OFF
# ──────────────────────────────────────────────────────────────

import json
import socket
import threading
import time

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from geometry_msgs.msg import TwistStamped

from roscue_interface.msg import YoloEvent
from roscue_interface.srv import SetYoloMode

ROS_DOMAIN_ID = 10     # 서버 전용 도메인 (코디네이터와 동일). cmd_vel 은 브릿지가 로봇 도메인으로 전달
ROBOT_LIST    = ['wf1', 'wf2']

TCP_HOST = '0.0.0.0'
TCP_PORT = 9999  # inference server가 연결하는 포트


class YoloGatewayNode(Node):
    def __init__(self):
        super().__init__('yolo_gateway')

        # 로봇별 현재 모드 (BOX_DETECTION_MODEL | EXPLOSIVE_DETECTION_MODEL | OFF)
        self._modes: dict[str, str] = {r: 'OFF' for r in ROBOT_LIST}
        self._mode_lock = threading.Lock()

        # 추론 서버와의 영속 소켓 (hello 메시지로 등록됨)
        self._inference_socks: dict[str, socket.socket] = {}
        self._sock_lock = threading.Lock()

        # ROS Publishers
        self.event_pub = self.create_publisher(YoloEvent, '/yolo/event', 10)
        # cmd_vel 은 TwistStamped 로 통일 (Jazzy/TurtleBot3 기준, web_gateway·브릿지와 일치)
        self.cmd_vel_pubs: dict[str, object] = {
            r: self.create_publisher(TwistStamped, f'/{r}/cmd_vel', 10)
            for r in ROBOT_LIST
        }



        # ROS Service
        self.create_service(SetYoloMode, '/yolo/set_mode', self._handle_set_mode)

        # TCP 서버 (데몬 스레드)
        threading.Thread(target=self._run_tcp_server, daemon=True).start()

        self.get_logger().info(f'YoloGateway 시작 — TCP :{TCP_PORT}')

    # =========================================================
    # ROS: /yolo/set_mode 서비스 핸들러
    # =========================================================
    def _handle_set_mode(self, req: SetYoloMode.Request, resp: SetYoloMode.Response):
        robot = req.robot_name
        mode  = req.mode.upper()

        with self._mode_lock:
            self._modes[robot] = mode

        self.get_logger().info(f'[{robot}:{req.stream}] 모드 → {mode}')

        cmd = {'cmd': 'set_mode', 'robot_name': robot, 'stream': req.stream, 'mode': mode}
        self._send_to_inference(robot, cmd)

        if mode == 'OFF':
            time.sleep(1.0)  # inference server가 OFF 처리 후 상태 정리할 시간

        resp.accepted = True
        resp.message  = f'[{robot}:{req.stream}] 모드 변경 완료: {mode}'
        return resp

    def _send_to_inference(self, robot_name: str, data: dict):
        with self._sock_lock:
            sock = self._inference_socks.get(robot_name)
        if not sock:
            self.get_logger().warning(f'[{robot_name}] 추론 서버 미연결 — 명령 전송 불가')
            return
        try:
            sock.sendall((json.dumps(data) + '\n').encode('utf-8'))
        except OSError as e:
            self.get_logger().error(f'[{robot_name}] 추론 서버 전송 실패: {e}')

    # =========================================================
    # TCP 서버 — 추론 서버 연결 수신
    # =========================================================
    def _run_tcp_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((TCP_HOST, TCP_PORT))
        server.listen(5)
        self.get_logger().info(f'TCP 대기 중 ({TCP_HOST}:{TCP_PORT})')

        while True:
            try:
                client_sock, addr = server.accept()
                self.get_logger().info(f'추론 서버 연결: {addr}')
                threading.Thread(
                    target=self._handle_inference_client,
                    args=(client_sock,),
                    daemon=True,
                ).start()
            except Exception as e:
                self.get_logger().error(f'TCP accept 에러: {e}')

    def _handle_inference_client(self, sock: socket.socket):
        robot_name = None
        buffer = ''

        try:
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                buffer += data.decode('utf-8')
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                        robot_name = msg.get('robot_name', robot_name)

                        msg_type = msg.get('type')
                        if msg_type == 'hello':
                            with self._sock_lock:
                                self._inference_socks[robot_name] = sock
                            self.get_logger().info(f'[{robot_name}] 추론 서버 등록 완료')

                        elif msg_type == 'event':
                            self._publish_event(msg)

                        elif msg_type == 'control':
                            self._publish_control(msg)

                        else:
                            self.get_logger().warning(f'알 수 없는 메시지 타입: {msg_type}')

                    except json.JSONDecodeError as e:
                        self.get_logger().warning(f'JSON 파싱 에러: {e} / line={line!r}')

        except Exception as e:
            self.get_logger().warning(f'추론 서버 연결 종료: {e}')
        finally:
            if robot_name:
                with self._sock_lock:
                    self._inference_socks.pop(robot_name, None)
                self.get_logger().info(f'[{robot_name}] 추론 서버 연결 해제')
            sock.close()

    # =========================================================
    # ROS 발행
    # =========================================================
    def _publish_control(self, data: dict):
        robot = data.get('robot_name', '')
        if robot not in ROBOT_LIST:
            return
        if not data.get('control_active', False):
            return

        twist = TwistStamped()
        twist.header.stamp    = self.get_clock().now().to_msg()
        twist.twist.linear.x  = float(data.get('linear_x', 0.0))
        twist.twist.angular.z = float(data.get('angular_z', 0.0))
        self.cmd_vel_pubs[robot].publish(twist)

    def _publish_event(self, data: dict):
        robot      = data.get('robot_name', '')
        event_type = data.get('event_type', '')

        with self._mode_lock:
            if self._modes.get(robot) == 'OFF':
                return

        msg            = YoloEvent()
        msg.stamp      = self.get_clock().now().to_msg()
        msg.robot_name = robot
        msg.event_type = event_type

        self.event_pub.publish(msg)
        self.get_logger().info(f'[{robot}] 이벤트 발행: {event_type}')


# =========================================================
# main
# =========================================================
def main():
    rclpy.init(domain_id=ROS_DOMAIN_ID)
    node = YoloGatewayNode()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
