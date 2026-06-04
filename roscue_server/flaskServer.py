import asyncio
import json
import threading
from flask import Flask, jsonify, request, render_template_string
import rclpy
from rclpy.node import Node
from roscue_interface.srv import TaskCommandSrv
from roscue_dto import RoscueTaskDTO, TaskAction

app = Flask(__name__)

# --- 웹 브라우저에 보여줄 인라인 HTML 템플릿 ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>로봇 플릿 매니저 컨트롤러</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; background-color: #f5f7fa; color: #333; }
        .card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h2 { margin-top: 0; color: #2c3e50; border-bottom: 2px solid #edf2f7; padding-bottom: 10px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; font-weight: bold; margin-bottom: 8px; color: #4a5568; }
        input, select, textarea { width: 100%; padding: 10px; border: 1px solid #cbd5e0; border-radius: 6px; box-sizing: border-box; font-size: 14px; }
        textarea { height: 80px; font-family: monospace; resize: none; }
        button { width: 100%; padding: 12px; background-color: #3182ce; color: white; border: none; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer; transition: background 0.2s; }
        button:hover { background-color: #2b6cb0; }
        #result { margin-top: 25px; padding: 15px; border-radius: 6px; display: none; font-weight: bold; white-space: pre-wrap; }
        .success { background-color: #c6f6d5; color: #22543d; border: 1px solid #9ae6b4; }
        .fail { background-color: #fed7d7; color: #742a2a; border: 1px solid #feb2b2; }
    </style>
</head>
<body>

<div class="card">
    <h2>🤖 로봇 명령 전송기</h2>
    
    <div class="form-group">
        <label for="robot_name">로봇 이름</label>
        <input type="text" id="robot_name" value="waffle1" placeholder="예: waffle1, waffle2">
    </div>

    <div class="form-group">
        <label for="task_name">작업(Task) 이름</label>
        <input type="text" id="task_name" value="camera_position" placeholder="예: move_to, patrol">
    </div>

    <div class="form-group">
        <label for="action">액션 (Action)</label>
        <select id="action">
            <option value="start">START (시작)</option>
            <option value="stop">STOP (중지)</option>
            <option value="restart">RESTART (재시작)</option>
            <option value="status">STATUS (상태 확인)</option>
        </select>
    </div>


    <button onclick="sendCommand()">명령 보내기 🚀</button>

    <div id="result"></div>
</div>

<script>
async function sendCommand() {
    const resultDiv = document.getElementById('result');
    resultDiv.style.display = 'none';
    
    // 1. 입력값 가져오기
    const robot_name = document.getElementById('robot_name').value;
    const task_name = document.getElementById('task_name').value;
    const action = document.getElementById('action').value;


    // 2. 백엔드 API에 POST 요청 날리기
    try {
        const response = await fetch('/api/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ robot_name, task_name, action })
        });

        const resData = await response.json();
        
        // 3. 화면에 결과 표시
        if (response.ok && resData.result === 'success') {
            resultDiv.className = 'success';
            resultDiv.innerText = `✅ 성공!\\n메시지: ${resData.message}`;
        } else {
            resultDiv.className = 'fail';
            resultDiv.innerText = `❌ 실패!\\n사유: ${resData.message}`;
        }
    } catch (error) {
        resultDiv.className = 'fail';
        resultDiv.innerText = `🚨 통신 에러: ${error.message}`;
    }
    
    resultDiv.style.display = 'block';
}
</script>

</body>
</html>
"""

# --- ROS 2 클라이언트 노드 설정 ---
class FlaskRosClient(Node):
    def __init__(self):
        super().__init__("flask_ros_client")
        self.cli = self.create_client(TaskCommandSrv, "/fleet/task_command")

    async def call_fleet_manager(self, dto: RoscueTaskDTO):
        if not self.cli.wait_for_service(timeout_sec=3.0):
            return False, "Fleet Manager Service unavailable"

        req = TaskCommandSrv.Request()
        req.robot_name = dto.robot_name
        req.task_name = dto.task_name
        req.action = dto.action.value


        resp = await self.cli.call_async(req)
        return resp.accepted, resp.message

ros_client_node = None

def ros_loop():
    rclpy.spin(ros_client_node)

# --- Flask 라우트 설정 ---

@app.route("/", methods=["GET"])
def index():
    """웹 브라우저로 접속했을 때 HTML 화면을 띄워주는 라우트"""
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/command", methods=["POST"])
def handle_http_request():
    global ros_client_node
    data = request.get_json() or {}

    try:
        task_dto = RoscueTaskDTO(
            robot_name=data.get("robot_name", ""),
            task_name=data.get("task_name", ""),
            action=TaskAction(data.get("action", "status"))
        )

    except ValueError as e:
        return jsonify({"result": "fail", "message": f"Invalid Action: {e}"}), 400

    future = asyncio.run_coroutine_threadsafe(
        ros_client_node.call_fleet_manager(task_dto),
        ros_client_node.executor.create_task.__self__._loop
    )

    try:
        accepted, message = future.result(timeout=5.0)
        status_code = 200 if accepted else 400
        return jsonify({
            "result": "success" if accepted else "fail",
            "message": message
        }), status_code
    except Exception as e:
        return jsonify({"result": "fail", "message": f"Communication error: {e}"}), 500

if __name__ == "__main__":
    rclpy.init()
    ros_client_node = FlaskRosClient()

    t = threading.Thread(target=ros_loop, daemon=True)
    t.start()

    try:
        app.run(host="127.0.0.1", port=5000, debug=False)
    finally:
        rclpy.shutdown()