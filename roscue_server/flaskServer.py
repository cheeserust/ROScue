import asyncio
from flask import Flask, jsonify, request
import rclpy
from rclpy.executors import SingleThreadedExecutor
import threading
'''
curl -X POST http://127.0.0.1:5000/api/command \
     -H "Content-Type: application/json" \
     -d '{
           "robot_name": "waffle1",
           "task_name": "camera_position",
           "action": "start",
           "params": {"angle": 90}
         }'

'''
# 앞서 만든 ROS 2 노드 클래스 가져오기
# (파일명이 fleet_manager_node.py 라고 가정)
from roscue_main_server_node import FleetManagerNode

app = Flask(__name__)

# 전역 변수로 노드 선언
ros_node = None


def run_ros_loop(node):
    """Flask와 별개로 ROS 2 백그라운드 스레드에서 이벤트를 처리하는 함수"""
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    finally:
        executor.remove_node(node)
        node.destroy_node()


@app.route("/api/command", methods=["POST"])
def post_command():
    """Flask로 들어오는 HTTP POST 요청을 처리하는 라우트"""
    global ros_node

    # 1. Flask 요청 데이터(JSON) 파싱
    data = request.get_json() or {}
    robot_name = data.get("robot_name")
    task_name = data.get("task_name")
    action = data.get("action")
    params = data.get("params", {})

    # 필수 인자 검증
    if not robot_name or not task_name or not action:
        return (
            jsonify(
                {"result": "fail", "message": "Missing required parameters"}
            ),
            400,
        )

    # 2. 핵심: Flask(동기 스레드)에서 ROS 2 노드의 비동기(async) 함수 호출하기
    # asyncio.run_coroutine_threadsafe를 사용하면 백그라운드 ROS 스레드에 안전하게 작업을 던질 수 있습니다.
    future = asyncio.run_coroutine_threadsafe(
        ros_node.send_command(robot_name, task_name, action, params),
        ros_node.executor.create_task.__self__._loop,  # ROS 2 노드가 사용하는 이벤트 루프 추출
    )

    try:
        # ROS 2 노드 내부에서 응답이 올 때까지 최대 5초 대기
        ok, msg = future.result(timeout=5.0)

        if ok:
            return jsonify({"result": "success", "message": msg}), 200
        else:
            return jsonify({"result": "fail", "message": msg}), 400

    except asyncio.TimeoutError:
        return jsonify({"result": "fail", "message": "ROS service timeout"}), 504
    except Exception as e:
        return (
            jsonify({"result": "fail", "message": f"An error occurred: {e}"}),
            500,
        )


if __name__ == "__main__":
    # 1. ROS 2 초기화 및 노드 생성
    rclpy.init()
    ros_node = FleetManagerNode()

    # 2. ROS 2 스핀을 별도의 백그라운드 스레드에서 실행
    # 이렇게 해야 Flask 서버와 ROS 2 시스템이 서로 방해하지 않고 동시에 돌아갑니다.
    ros_thread = threading.Thread(
        target=run_ros_loop, args=(ros_node,), daemon=True
    )
    ros_thread.start()

    try:
        # 3. Flask 서버 시작
        print("Flask 서버를 시작합니다. http://127.0.0.1:5000")
        app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
    finally:
        # Flask 종료 시 ROS 2 깔끔하게 끄기
        rclpy.shutdown()