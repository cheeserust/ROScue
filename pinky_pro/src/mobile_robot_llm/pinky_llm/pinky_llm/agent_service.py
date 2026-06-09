import rclpy
from rclpy.node import Node
from pinky_llm.robot_tools import ToolSet, create_tools
from pinky_interfaces.srv import Agent
from pathlib import Path
from ament_index_python.packages import get_package_share_directory

import yaml
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

# 패키지 로딩
llm_dir = get_package_share_directory('pinky_llm')
nav2_dir = get_package_share_directory('pinky_navigation')
env_file_path = Path(llm_dir) / '.env' # API 키 .env 에서 로드
load_dotenv(dotenv_path=env_file_path)

prompt_file = Path(llm_dir) / 'params/prompt.yaml' # 시스템 프롬프트 로드
with open(prompt_file, 'r', encoding='utf-8') as f:
    prompt_data = yaml.safe_load(f)    

class AgentLLM(Node):
    def __init__(self):
        super().__init__('agent_llm')
				# LLM + Prompt 설정
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_data["system"]),  # 로봇 역할 정의
            ("placeholder", "{chat_history}"),  # 대화 기록
            ("human", "{input}"),               # 유저 질문
            ("placeholder", "{agent_scratchpad}") # Tool 호출하는 동안 내부 추론과정을 저장하는 공간
				])
				
        self.srv = self.create_service(Agent, 'llm_agent', self.handle_question)
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
		    
		    # tools 설정
        yaml_file = Path(llm_dir) / 'params/points.yaml' # 장소 좌표 로드
        with open(yaml_file, 'r') as f:
            config = yaml.safe_load(f)
				
				# YAML 파일에 따라 {"장소1": (x, y, qz, qw), "장소2": (x, y, qz, qw) ...} 로 저장
				# (x, y) = 위치 / (qz, qw) = 회전 쿼터니언 (yaw)
        places = {name: (info["x"], info["y"], info["qz"], info["qw"]) for name, info in config["places"].items()}
        # location 들 ToolSet 으로 전달, 
        tool_set = ToolSet(places) # ToolSet -> get_pos / move_to 등과 같은 메소드 있음
        tool_list = create_tools(tool_set) # create_tools 가 LLM 이 호출가능한 Langchain 의 Tool 객체로 wrappnio
				
				# Agent + 대화 기록
				# LLM + Tools + prompt into agent --> 어떤 tool 있는지 어떻게 호출할지 앎
        self.agent = create_tool_calling_agent(self.llm, tool_list, self.prompt)
        # Langchain 의 AgentExecutor 호출 --> agent 를 실행 루프로 감쌈
        # LLM says "call move_to" → executor runs it → feeds result back → LLM decides next step
        self.agent_executor = AgentExecutor(agent=self.agent, tools=tool_list, verbose=True)
				# 대화 버퍼 비움
        self.chat_history = ChatMessageHistory()
        # 대화 기록 유지 --> 문맥 이해 가능
        self.agent_with_history = RunnableWithMessageHistory(
            self.agent_executor,
            lambda sid: self.chat_history,
            input_messages_key="input",
            history_messages_key="chat_history"
        )
        
        self.get_logger().info("agent service start")
	
		# 유저가 입력한 질문으로 invoke 함
		# invoke = 멀티스레드 환경에서 데이터 보호를 위해 쓴다는데?
		# "실행해" 라는 뜻의 LangChain 표준 메서드??
    def process_query(self, query):
        resp = self.agent_with_history.invoke({"input": query}, config={"configurable": {"session_id": "pinky"}})
        return resp["output"] if "output" in resp else str(resp)

    def handle_question(self, request, response):
        self.get_logger().info(f"💬: {request.question}"+"\n")
        try:
            answer = self.process_query(request.question)
            # response_match = re.search(r"ANSWER:\s*([\s\S]*)", answer, re.IGNORECASE)
            # response.answer = response_match.group(1).strip() if response_match else "[ERR] No answer parsed"
            response.answer = answer
        except Exception as e:
            self.get_logger().info(e)
            response.answer = "잘 이해하지 못했어요.. 자세하게 물어봐 주시겠어요?"
        return response
    
def main(args=None):
    rclpy.init(args=args)
    agent = AgentLLM()
    try:
        rclpy.spin(agent) 
    finally:
        agent.destroy_node()
        rclpy.shutdown()
