# robot_action_server.py (로봇에서 실행)
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
import time


from roscue_interface.action import MoveTaskAction

class RobotActionServer(Node):
    def __init__(self, robot_name="waffle1"):
        super().__init__(f'{robot_name}_action_server')
        
        # 콜센터(액션 서버) 오픈
        self._action_server = ActionServer(
            self,
            MoveTaskAction, # Action 타입
            f'/{robot_name}/move_action',
            self.execute_callback
        )

    # 누군가(메인 서버) 목적지로 가라고 명령했을 때 실행됨
    def execute_callback(self, goal_handle):
        self.get_logger().info(f"명령 수신: {goal_handle.request.target}로 이동 시작!")
        
        feedback_msg = MoveTaskAction.Feedback()

        # 자율주행 시뮬레이션 (10초 동안 이동)
        for i in range(1, 11):
            time.sleep(1.0) # 실제로는 여기서 로봇을 움직임
            
            feedback_msg.percent_complete = i * 10
            goal_handle.publish_feedback(feedback_msg) # 메인 서버로 진행률(10%, 20%...) 전송
            self.get_logger().info(f"이동 중... {feedback_msg.percent_complete}%")

        # 이동 완료!
        goal_handle.succeed()
        result = MoveTaskAction.Result()
        result.success = True
        return result

def main():
    rclpy.init()
    node = RobotActionServer()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()