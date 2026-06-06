import rclpy
from rclpy.node import Node
from roscue_interface.msg import ArmPositions # 생성한 커스텀 메시지 임포트
from lerobot.motors.dynamixel import DynamixelMotorsBus


# ros2 run roscue_server server_omx_manual_control --ros-args -r __ns:=/waffle1 -p port:=/dev/ttyACM0




class Motor:
    def __init__(self, idx, model):
        self.id = idx
        self.model = model

class LeaderNode(Node):
    def __init__(self):
        super().__init__('server_omx_manual_control')
        
        # 1. ROS 2 파라미터 선언 (기본 포트는 /dev/ttyACM0)
        self.declare_parameter('port', '/dev/ttyACM0')
        port_name = self.get_parameter('port').get_parameter_value().string_value
        
        # 2. 토픽 퍼블리셔 생성 ('goal_positions' 라는 이름으로 발행)
        self.publisher_ = self.create_publisher(ArmPositions, 'goal_positions', 10)
        
        # 3. 60Hz 주기로 타이머 실행 (1/60초 마다 timer_callback 호출)
        self.timer = self.create_timer(1.0 / 60.0, self.timer_callback)

        # 다이나믹셀 모터 설정
        self.motors_config = {
            "m1": Motor(1, "xl330-m288"),
            "m2": Motor(2, "xl330-m288"),
            "m3": Motor(3, "xl330-m288"),
            "m4": Motor(4, "xl330-m288"),
            "m5": Motor(5, "xl330-m288"),
            "m6": Motor(6, "xl330-m077"),
        }

        self.get_logger().info(f"다이나믹셀 버스 연결 중... 포트: {port_name}")
        self.leader_bus = DynamixelMotorsBus(port=port_name, motors=self.motors_config)
        self.leader_bus.connect()

        # 토크 해제
        try:
            torque_off_dict = {k: 0 for k in self.motors_config.keys()}
            self.leader_bus.sync_write("Torque_Enable", torque_off_dict)
        except Exception as e:
            self.get_logger().warn(f"토크 해제 경고: {e}")

    def timer_callback(self):
        try:
            obs = self.leader_bus.sync_read("Present_Position", normalize=False)
            
            if isinstance(obs, dict):
                positions = [int(obs[k]) for k in self.motors_config.keys()]
            else:
                positions = [int(x) for x in obs]
            
            # 메시지 객체 생성 및 데이터 담기
            msg = ArmPositions()
            msg.positions = positions
            
            # 토픽 발행
            self.publisher_.publish(msg)
            
        except Exception as e:
            self.get_logger().error(f"다이나믹셀 읽기 실패: {e}")

    def destroy_node(self):
        self.leader_bus.disconnect()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = LeaderNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("노드를 종료합니다.")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()