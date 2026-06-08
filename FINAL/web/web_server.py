# web_server.py
from flask import Flask, jsonify, request, render_template
from roscue_dto import RoscueTaskDTO, TaskAction
import web_gateway

app = Flask(__name__)

# 서버 시작 시 ROS2 게이트웨이 노드 백그라운드 실행 및 참조 인스턴스 획득
ros_client_node = web_gateway.start_ros_thread()

@app.route("/", methods=["GET"])
def index():
    # templates/index.html 파일을 자동으로 찾아서 보여줌
    return render_template("index.html")

@app.route("/api/command", methods=["POST"])
def handle_http_request():
    data = request.get_json() or {}

    try:
        task_dto = RoscueTaskDTO(
            robot_name=data.get("robot_name", ""),
            task_name=data.get("task_name", ""),
            action=TaskAction(data.get("action", "status"))
        )
    except ValueError as e:
        return jsonify({"result": "fail", "message": f"Invalid Action: {e}"}), 400

    try:
        # 분리된 ROS2 게이트웨이를 통해 메인 서버 호출
        accepted, message = ros_client_node.call_main_server(task_dto)
        status_code = 200 if accepted else 400
        return jsonify({
            "result": "success" if accepted else "fail",
            "message": message
        }), status_code
        
    except Exception as e:
        return jsonify({"result": "fail", "message": f"Communication error: {e}"}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)