import rclpy
from pinky_interfaces.srv import Agent
from rclpy.node import Node
import readline

# service client 노드 생성
# /llm_agent 서비스 뜰때까지 'waiting for the service'
# Agent = 커스텀 메세지, 밑 참고
class AgentClient(Node):
    def __init__(self):
        super().__init__('agent_client')
        self.cli = self.create_client(Agent, 'llm_agent')
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for the service...')

        self.req = Agent.Request()
		
		# send request (터미널 --> agent_service)
		# future = 당장은 없는 미래의 "결과"
    def ask(self, question: str) -> str:
        self.req.question = question
        # 내 입력을 question 필드에 담아 비동기(call_async)로 요청
        future = self.cli.call_async(self.req)
        
        # 결과 (agent_service 로부터의 응답) 기다림
        rclpy.spin_until_future_complete(self, future)
        
        # future 이 들어오면 (모델이 대답하면) 값 return
        return future.result().answer

# 터미널 ui
def main():
    rclpy.init()
    client = AgentClient()

    try:
        while True:
            q = input("💬 질문: ")
            answer = client.ask(q)
            print("🤖:", answer, "\n")
    finally:
        client.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()