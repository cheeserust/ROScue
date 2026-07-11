# web_server.py
import json

from flask import Flask, jsonify, request, render_template

from roscue_dto import RoscueTaskDTO
import web_gateway as web_gateway

app = Flask(__name__)

ros_client_node = web_gateway.start_ros_thread()


def _ok(message: str):
    return jsonify({"result": "success", "message": message}), 200

def _fail(message: str, code: int = 400):
    return jsonify({"result": "fail", "message": message}), code


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/new", methods=["GET"])
def index2():
    return render_template("new.html")

@app.route("/api/command", methods=["POST"])
def handle_command():
    data = request.get_json() or {}
    dto = RoscueTaskDTO(
        robot_name=data.get("robot_name", ""),
        task_name =data.get("task_name",  ""),
        action    =data.get("action",     ""),
        box_id    =data.get("box_id",     ""),
    )
    try:
        accepted, message = ros_client_node.call_main_server(dto)
        return (_ok(message) if accepted else _fail(message))
    except Exception as e:
        return _fail(f"Communication error: {e}", 500)


@app.route('/api/status', methods=['GET'])
def get_status():
    try:
        robot_status = ros_client_node.get_robot_status()
        active_count = sum(1 for v in robot_status.values() if v)
        raw = ros_client_node.get_box_list()
        boxes = json.loads(raw)
        return jsonify({
            'robots': robot_status,
            'active_count': active_count,
            'box_count': len(boxes),
        })
    except Exception as e:
        return _fail(f'Status error: {e}', 500)


@app.route('/api/boxes', methods=['GET'])
def get_boxes():
    try:
        raw = ros_client_node.get_box_list()
        return jsonify({'boxes': json.loads(raw)})
    except Exception as e:
        return _fail(f'Box list error: {e}', 500)


@app.route('/api/teleop', methods=['POST'])
def handle_teleop():
    data      = request.get_json(force=True) or {}
    robot     = data.get('robot_name', 'wf1')
    linear_x  = data.get('linear_x',  0.0)
    angular_z = data.get('angular_z', 0.0)
    try:
        ok, msg = ros_client_node.publish_teleop(robot, linear_x, angular_z)
        return (_ok(msg) if ok else _fail(msg))
    except Exception as e:
        return _fail(f'Teleop error: {e}', 500)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
