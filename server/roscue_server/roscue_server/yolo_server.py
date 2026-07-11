#!/usr/bin/env python3
"""
yolo_server.py

역할
- Raspberry Pi MJPEG wrist camera을 PC/GPU에서 읽는다.
- YOLO BOX / EXPLOSIVE 모델을 모드에 따라 실행한다.
- yolo_gateway.py의 TCP 프로토콜에 맞춰 hello / event JSON line을 전송한다.
- TurtleBot3 Jazzy용 TwistStamped /cmd_vel을 직접 발행해 박스 close 추종을 수행한다.

Gateway 프로토콜
- 추론 → 게이트웨이:
    {"type":"hello", "robot_name":"wf1"}
    {"type":"event", "robot_name":"wf1", "event_type":"BOX_FOUND"}
- 게이트웨이 → 추론:
    {"cmd":"set_mode", "robot_name":"wf1", "camera":"wrist_cam", "mode":"EXPLOSIVE_DETECTION_MODEL"}

CentralServer와 맞춘 event_type
- BOX close 탐지: BOX_FOUND
- BOX close에 충분히 접근: ARRIVED
- 박스 뚜껑 열림 확인: BOX_COVER_OPEN
- EXPLOSIVE 모델 Empty: EMPTY
- EXPLOSIVE 모델 Bomb_A/Bomb_B/bomb/explosive: EXPLOSIVE_FOUND
"""

import json
import socket
import sys
import threading
import time
from pathlib import Path
from typing import List, Optional

import cv2
from flask import Flask, Response, jsonify
from ultralytics import YOLO


# =========================================================
# 1. 기본 설정 — 여기만 수정
# =========================================================
EVENT_COOLDOWN_SEC = 1.0
FRAME_WAIT         = 30


# 로봇별 카메라 URL — 실행: python3 yolo_server.py wf1  또는  wf2
_ROBOT_CAMERA_URLS = {
    "wf1": "http://192.168.0.14:5000/camera",
    "wf2": "http://192.168.0.15:5001/camera",
}
ROBOT_NAME = sys.argv[1] if len(sys.argv) > 1 else "wf1"
if ROBOT_NAME not in _ROBOT_CAMERA_URLS:
    raise ValueError(f"알 수 없는 로봇 이름: {ROBOT_NAME!r}. 사용 가능: {list(_ROBOT_CAMERA_URLS)}")

CAMERA_URL         = _ROBOT_CAMERA_URLS[ROBOT_NAME]

YOLO_GATEWAY_HOST  = "127.0.0.1"
YOLO_GATEWAY_PORT  = 9999

BOX_MODEL_PATH     = str(Path(__file__).resolve().parent / "box.pt")
BOMB_MODEL_PATH    = str(Path(__file__).resolve().parent / "bomb.pt")

INITIAL_MODE       = "OFF"   # OFF | BOX_DETECTION_MODEL | EXPLOSIVE_DETECTION_MODEL

IMG_SIZE           = 640
CONF_THRES         = 0.5
DEVICE             = 0       # GPU 번호, CPU면 "cpu"

ARRIVE_AREA_RATIO  = 0.25    # 이 면적비에 도달하면 '최종 전진(nudge)' 시작
FINAL_NUDGE_SEC    = 2.5    # 도달 후 박스에 더 붙기 위해 추가로 직진하는 시간 (초)
FINAL_NUDGE_SPEED  = 0.1    # 추가 직진 속도 (m/s)
CENTER_TOL         = 0.15
FORWARD_SPEED      = 0.12
TURN_FORWARD_SPEED = 0.05
ANGULAR_GAIN       = 0.1
MAX_ANGULAR_SPEED  = 0.2
TARGET_TIMEOUT_SEC = 0.7
EVENT_COOLDOWN_SEC = 1.0

DEBUG_HOST         = "0.0.0.0"
_ROBOT_DEBUG_PORTS = {
    "wf1": 5055,
    "wf2": 5056,
}
DEBUG_PORT          = _ROBOT_DEBUG_PORTS[ROBOT_NAME]
JPEG_QUALITY        = 80


# =========================================================
# 2. 모드 / 상태
# =========================================================

_VALID_MODES = {"BOX_DETECTION_MODEL", "EXPLOSIVE_DETECTION_MODEL", "OFF"}


def normalize_mode(mode: str) -> str:
    m = str(mode or "").strip().upper()
    return m if m in _VALID_MODES else "OFF"


def mode_key(mode: str) -> str:
    mode = normalize_mode(mode)
    if mode == "BOX_DETECTION_MODEL":
        return "BOX"
    if mode == "EXPLOSIVE_DETECTION_MODEL":
        return "EXPLOSIVE"
    return "OFF"


current_mode = normalize_mode(INITIAL_MODE)
mode_lock = threading.Lock()

frame_lock = threading.Lock()
latest_debug_frame = None
latest_status = {}

model_lock = threading.Lock()
model_cache: dict[str, YOLO] = {}


# =========================================================
# 3. 유틸 함수
# =========================================================

def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def get_current_mode() -> str:
    with mode_lock:
        return current_mode


def set_current_mode(mode: str) -> str:
    global current_mode
    normalized = normalize_mode(mode)
    with mode_lock:
        current_mode = normalized
    print(f"[INFO] mode changed: {normalized}")
    return normalized


def get_model_for_mode(mode: str) -> Optional[YOLO]:
    key = mode_key(mode)
    if key == "OFF":
        return None

    path = BOX_MODEL_PATH if key == "BOX" else BOMB_MODEL_PATH
    if not Path(path).exists():
        raise FileNotFoundError(f"model file not found for {mode}: {path}")

    with model_lock:
        if key not in model_cache:
            print(f"[INFO] YOLO model loading for {key}: {path}")
            model_cache[key] = YOLO(path)
            print(f"[INFO] YOLO model loaded for {key}: {model_cache[key].names}")
        return model_cache[key]


def class_event_candidates(mode: str, target_class: str, arrived: bool) -> List[str]:
    if not target_class:
        return []

    key = mode_key(mode)
    name = str(target_class).strip().lower()

    if key == "BOX":
        if name == "close":
            events = ["BOX_FOUND"]
            if arrived:
                events.append("ARRIVED")
            return events
        if name in {"open", "box_cover_open", "cover_open", "lid_open"}:
            return ["BOX_COVER_OPEN"]
        return []

    if key == "EXPLOSIVE":
        if name == "empty":
            return ["EMPTY"]
        if name in {"bomb_a", "bomb_b", "bomb", "explosive", "danger"}:
            return ["EXPLOSIVE_FOUND"]
        if name in {"open", "box_cover_open", "cover_open", "lid_open"}:
            return ["BOX_COVER_OPEN"]
        return []

    return []


def make_base_status(mode: str, command: str = "WAITING") -> dict:
    return {
        "robot_name": ROBOT_NAME,
        "gateway_mode": normalize_mode(mode),
        "model_mode": mode_key(mode),
        "valid": False,
        "target_class": "",
        "confidence": 0.0,
        "command": command,
        "arrived": False,
        "reached_arrive": False,
        "area": 0.0,
        "cx": 0.0,
        "cy": 0.0,
        "cx_norm": 0.5,
        "cy_norm": 0.5,
        "linear_x": 0.0,
        "angular_z": 0.0,
        "event_type": "",
        "event_types": [],
        "camera_url": CAMERA_URL,
        "gateway_host": YOLO_GATEWAY_HOST,
        "gateway_port": YOLO_GATEWAY_PORT,
        "gateway_connected": False,
        "control_active": False,
    }


def select_best_box(results, model, mode: str):
    boxes = results[0].boxes
    if boxes is None or len(boxes) == 0:
        return None

    best_close_box = None
    best_close_conf = -1.0
    best_any_box = None
    best_any_conf = -1.0

    for box in boxes:
        conf = float(box.conf[0])
        if conf > best_any_conf:
            best_any_conf = conf
            best_any_box = box

        if mode_key(mode) == "BOX" and model is not None:
            cls_id = int(box.cls[0])
            class_name = str(model.names[cls_id]).strip().lower()
            if class_name == "close" and conf > best_close_conf:
                best_close_conf = conf
                best_close_box = box

    if mode_key(mode) == "BOX" and best_close_box is not None:
        return best_close_box
    return best_any_box


def make_follow_status(frame, results, model, mode: str) -> dict:
    h, w = frame.shape[:2]
    status = make_base_status(mode, command="STOP_NO_TARGET")

    best_box = select_best_box(results, model, mode)
    if best_box is None:
        return status

    cls_id = int(best_box.cls[0])
    target_class = str(model.names[cls_id])
    confidence = float(best_box.conf[0])
    target_name = target_class.strip().lower()

    x1, y1, x2, y2 = map(float, best_box.xyxy[0].tolist())
    bbox_w = max(0.0, x2 - x1)
    bbox_h = max(0.0, y2 - y1)
    bbox_area = bbox_w * bbox_h
    frame_area = max(1.0, float(w * h))
    area_ratio = bbox_area / frame_area

    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    cx_norm = clamp(cx / max(1.0, float(w)), 0.0, 1.0)
    cy_norm = clamp(cy / max(1.0, float(h)), 0.0, 1.0)

    center_x = w / 2.0
    error_x = cx - center_x
    error_norm = error_x / max(1.0, center_x)

    status.update({
        "valid": True,
        "target_class": target_class,
        "confidence": confidence,
        "area": float(area_ratio),
        "cx": float(cx),
        "cy": float(cy),
        "cx_norm": float(cx_norm),
        "cy_norm": float(cy_norm),
    })

    key = mode_key(mode)

    if key == "EXPLOSIVE":
        events = class_event_candidates(mode, target_class, arrived=False)
        status["event_types"] = events
        status["event_type"] = ",".join(events)
        status["command"] = "BOX_SCAN_DETECTED" if events else "BOX_SCAN_IGNORE_CLASS"
        status["control_active"] = False
        return status

    if key == "BOX" and target_name != "close":
        events = class_event_candidates(mode, target_class, arrived=False)
        status["event_types"] = events
        status["event_type"] = ",".join(events)
        status["command"] = "IGNORE_OPEN" if target_name == "open" else "IGNORE_NOT_CLOSE"
        status["control_active"] = False
        return status

    # BOX close: Gateway에는 target을 보내고, 옵션에 따라 /cmd_vel 추종도 수행.
    status["control_active"] = True

    if area_ratio >= ARRIVE_AREA_RATIO:
        # 도달 거리 진입. 정지 시점 박스가 멀어서, 실제 정지/ARRIVED 발행은
        # yolo_loop의 최종 전진(nudge) 단계에서 처리한다 (잠깐 더 직진 후 정지).
        status.update({
            "reached_arrive": True,
            "command": "ARRIVE_REACHED",
            "arrived": False,
            "linear_x": 0.0,
            "angular_z": 0.0,
        })
        return status

    events = class_event_candidates(mode, target_class, arrived=False)
    status["event_types"] = events
    status["event_type"] = ",".join(events)

    if abs(error_norm) > CENTER_TOL:
        linear_x = TURN_FORWARD_SPEED
        angular_z = clamp(-ANGULAR_GAIN * error_norm, -MAX_ANGULAR_SPEED, MAX_ANGULAR_SPEED)
        status.update({
            "linear_x": float(linear_x),
            "angular_z": float(angular_z),
            "arrived": False,
            "command": "TURN_RIGHT" if error_norm > 0 else "TURN_LEFT",
        })
        return status

    status.update({
        "command": "FORWARD",
        "arrived": False,
        "linear_x": float(FORWARD_SPEED),
        "angular_z": 0.0,
    })
    return status


def draw_debug(frame, results, status):
    annotated = results[0].plot() if results is not None else frame.copy()
    h, w = annotated.shape[:2]

    cv2.line(annotated, (w // 2, 0), (w // 2, h), (255, 255, 0), 2)
    left_tol = int((0.5 - CENTER_TOL / 2.0) * w)
    right_tol = int((0.5 + CENTER_TOL / 2.0) * w)
    cv2.line(annotated, (left_tol, 0), (left_tol, h), (100, 100, 255), 1)
    cv2.line(annotated, (right_tol, 0), (right_tol, h), (100, 100, 255), 1)

    lines = [
        f"robot: {status.get('robot_name', ROBOT_NAME)}",
        f"mode: {status.get('gateway_mode', '')}",
        f"gateway: {status.get('gateway_connected', False)}",
        f"event: {status.get('event_type', '')}",
        f"command: {status.get('command', '')}",
        f"control: {status.get('control_active', False)}",
        f"arrived: {status.get('arrived', False)}",
        f"class: {status.get('target_class', '')}",
        f"conf: {status.get('confidence', 0.0):.2f}",
        f"area: {status.get('area', 0.0):.3f}",
        f"cx/cy: {status.get('cx_norm', 0.5):.2f}, {status.get('cy_norm', 0.5):.2f}",
        f"linear_x: {status.get('linear_x', 0.0):.2f}",
        f"angular_z: {status.get('angular_z', 0.0):.2f}",
    ]

    y = 25
    for line in lines:
        cv2.putText(annotated, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 0, 255), 2)
        y += 22

    if not status.get("valid", False):
        cv2.putText(annotated, "NO DETECTION", (10, y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

    return annotated


# =========================================================
# 4. yolo_gateway TCP client
# =========================================================

class YoloGatewayTcpClient:
    def __init__(self, host: str, port: int, robot_name: str):
        self.host = host
        self.port = port
        self.robot_name = robot_name
        self.sock: Optional[socket.socket] = None
        self.sock_lock = threading.Lock()
        self.running = True
        self.connected = False
        self.thread = threading.Thread(target=self._connect_loop, daemon=True)
        self.thread.start()

    def _connect_loop(self):
        while self.running:
            sock = None
            try:
                print(f"[INFO] connecting yolo_gateway: {self.host}:{self.port}")
                sock = socket.create_connection((self.host, self.port), timeout=5.0)
                sock.settimeout(None)
                with self.sock_lock:
                    self.sock = sock
                    self.connected = True
                print(f"[INFO] yolo_gateway connected: {self.host}:{self.port}")
                self.send({"type": "hello", "robot_name": self.robot_name})
                self._read_loop(sock)
            except OSError as e:
                print(f"[WARN] yolo_gateway connection failed/lost: {e}")
            finally:
                with self.sock_lock:
                    if self.sock is sock:
                        self.sock = None
                    self.connected = False
                if sock is not None:
                    try:
                        sock.close()
                    except OSError:
                        pass
                if self.running:
                    time.sleep(1.0)

    def _read_loop(self, sock: socket.socket):
        buffer = ""
        while self.running:
            data = sock.recv(4096)
            if not data:
                break
            buffer += data.decode("utf-8", errors="replace")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"[WARN] gateway command JSON error: {e} / line={line!r}")
                    continue
                self._handle_gateway_command(msg)

    def _handle_gateway_command(self, msg: dict):
        cmd = msg.get("cmd", "")
        robot = str(msg.get("robot_name", self.robot_name)).strip().strip("/")
        if robot and robot != self.robot_name:
            return

        if cmd == "set_mode":
            mode = normalize_mode(msg.get("mode", "OFF"))
            set_current_mode(mode)
            print(f"[INFO] gateway set_mode received: robot={robot}, mode={mode}")
        else:
            print(f"[WARN] unknown gateway command: {msg}")

    def is_connected(self) -> bool:
        with self.sock_lock:
            return bool(self.connected and self.sock)

    def send(self, data: dict) -> bool:
        payload = (json.dumps(data, ensure_ascii=False) + "\n").encode("utf-8")
        with self.sock_lock:
            sock = self.sock
        if sock is None:
            return False
        try:
            sock.sendall(payload)
            return True
        except OSError as e:
            print(f"[WARN] yolo_gateway send failed: {e}")
            with self.sock_lock:
                if self.sock is sock:
                    self.sock = None
                    self.connected = False
            return False

    def send_event(self, event_type: str) -> bool:
        return self.send({
            "type": "event",
            "robot_name": self.robot_name,
            "event_type": event_type,
        })

    def send_control(self, status: dict) -> bool:
        return self.send({
            "type": "control",
            "robot_name": self.robot_name,
            "linear_x": status.get("linear_x", 0.0),
            "angular_z": status.get("angular_z", 0.0),
            "arrived": bool(status.get("arrived", False)),
            "control_active": bool(status.get("control_active", False)),
        })

    def stop(self):
        self.running = False
        with self.sock_lock:
            sock = self.sock
            self.sock = None
            self.connected = False
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass


# =========================================================
# 5. HTTP CAMERA Reader
# =========================================================

class HttpCAMERAReader:
    def __init__(self, url: str):
        self.url = url
        self.frame = None
        self.lock = threading.Lock()
        self.running = True
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def loop(self):
        while self.running:
            print(f"[INFO] connecting camera: {self.url}")
            cap = cv2.VideoCapture(self.url)
            if not cap.isOpened():
                print(f"[WARN] camera open failed: {self.url}")
                time.sleep(1.0)
                continue
            print(f"[INFO] camera connected: {self.url}")
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    print("[WARN] camera read failed. reconnecting...")
                    break
                with self.lock:
                    self.frame = frame
            cap.release()
            time.sleep(0.5)

    def get_latest(self):
        with self.lock:
            if self.frame is None:
                return None
            return self.frame.copy()

    def stop(self):
        self.running = False


# =========================================================
# 7. YOLO Loop
# =========================================================

def yolo_loop(reader: HttpCAMERAReader, gateway: YoloGatewayTcpClient):
    global latest_status, latest_debug_frame

    last_event_time: dict[str, float] = {}
    event_streak: dict[str, int] = {}   # 이벤트별 연속 검출 프레임 수
    last_valid_time = 0.0
    nudge_start: Optional[float] = None   # 최종 전진 시작 시각 (None=미시작). BOX 모드 벗어나면 리셋.

    while True:
        frame = reader.get_latest()
        if frame is None:
            time.sleep(0.05)
            continue

        mode = get_current_mode()
        results = None

        if mode_key(mode) == "OFF":
            status = make_base_status(mode, command="OFF")
            time.sleep(0.05)
        else:
            try:
                model = get_model_for_mode(mode)
                results = model(frame, imgsz=IMG_SIZE, conf=CONF_THRES, device=DEVICE, verbose=False)
                status = make_follow_status(frame=frame, results=results, model=model, mode=mode)
            except Exception as e:
                status = make_base_status(mode, command="ERROR_MODEL_OR_INFERENCE")
                status["error"] = str(e)
                print(f"[ERROR] inference failed: {e}")
                time.sleep(0.2)

        status["gateway_connected"] = gateway.is_connected()

        if status.get("valid", False):
            last_valid_time = time.time()
        else:
            if time.time() - last_valid_time > TARGET_TIMEOUT_SEC and mode_key(mode) != "OFF":
                status["command"] = "STOP_NO_TARGET"
                status["linear_x"] = 0.0
                status["angular_z"] = 0.0
                status["arrived"] = False
                status["control_active"] = False

        # 박스 도달 후 '최종 전진(nudge)': 도달 거리에서 잠깐 더 직진해 박스에 붙인 뒤
        # 정지하고 ARRIVED를 발행한다. 한 번 시작하면 detection과 무관하게 open-loop로 진행.
        if mode_key(mode) != "BOX":
            nudge_start = None
        else:
            if nudge_start is None and status.get("reached_arrive"):
                nudge_start = time.time()
            if nudge_start is not None:
                if time.time() - nudge_start < FINAL_NUDGE_SEC:
                    status.update({
                        "command": "FINAL_NUDGE",
                        "linear_x": FINAL_NUDGE_SPEED,
                        "angular_z": 0.0,
                        "arrived": False,
                        "control_active": True,
                        "event_types": [],
                        "event_type": "",
                    })
                else:
                    # 전진 완료 → 정지 + ARRIVED (쿨다운으로 throttle, 이벤트 손실 대비 반복 발행)
                    status.update({
                        "command": "ARRIVED_STOP",
                        "linear_x": 0.0,
                        "angular_z": 0.0,
                        "arrived": True,
                        "control_active": True,
                        "event_types": ["ARRIVED"],
                        "event_type": "ARRIVED",
                    })

        # 이벤트는 FRAME_WAIT 프레임 이상 연속으로 검출되어야 게이트웨이로 전송한다.
        now = time.time()
        current_events = set(status.get("event_types", []))

        # 이번 프레임에 검출되지 않은 이벤트는 streak 리셋
        for event_type in list(event_streak.keys()):
            if event_type not in current_events:
                event_streak[event_type] = 0

        # 이번 프레임에 검출된 이벤트는 streak 증가, FRAME_WAIT 이상이면 전송
        for event_type in current_events:
            if not event_type:
                continue
            event_streak[event_type] = event_streak.get(event_type, 0) + 1

            if event_streak[event_type] >= FRAME_WAIT:
                if now - last_event_time.get(event_type, 0.0) >= EVENT_COOLDOWN_SEC:
                    last_event_time[event_type] = now
                    gateway.send_event(event_type)

        gateway.send_control(status)

        debug_frame = draw_debug(frame=frame, results=results, status=status)
        with frame_lock:
            latest_status = status
            latest_debug_frame = debug_frame

        print(
            f"[{status['command']}] "
            f"robot={ROBOT_NAME} "
            f"mode={status.get('gateway_mode')} "
            f"gateway={status.get('gateway_connected')} "
            f"events={status.get('event_type')} "
            f"control={status.get('control_active', False)} "
            f"class={status.get('target_class', '')} "
            f"area={status.get('area', 0.0):.3f} "
            f"linear={status.get('linear_x', 0.0):.2f} "
            f"angular={status.get('angular_z', 0.0):.2f} "
            f"arrived={status.get('arrived', False)}"
        )

        time.sleep(0.03)

# =========================================================
# 8. Debug Web Server
# =========================================================

app = Flask(__name__)


def encode_jpeg(frame):
    ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not ok:
        return None
    return encoded.tobytes()



def generate_debug_camera():
    while True:
        with frame_lock:
            frame = None if latest_debug_frame is None else latest_debug_frame.copy()
        if frame is None:
            time.sleep(0.05)
            continue
        jpg = encode_jpeg(frame)
        if jpg is None:
            continue
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
        time.sleep(0.03)



@app.route("/dashboard/debug")
def dashboard_debug():
    return Response(generate_debug_camera(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/dashboard")
def dashboard():
    return f"""
    <html>
    <head>
        <title>PC YOLO Follow Dashboard</title>
        <style>
            body {{ background-color: #111; color: white; font-family: Arial, sans-serif; }}
            .container {{ display: flex; gap: 20px; }}
            .panel {{ width: 48%; }}
            img {{ width: 100%; border: 2px solid #444; }}
            code {{ color: #9ef; }}
        </style>
    </head>
    <body>
        <h2>PC YOLO Follow Dashboard</h2>
        <p>Robot: <code>{ROBOT_NAME}</code></p>
        <p>Source camera: <code>{CAMERA_URL}</code></p>
        <p>Gateway: <code>{YOLO_GATEWAY_HOST}:{YOLO_GATEWAY_PORT}</code></p>
        <div class="container">
            <div class="panel"><h3>YOLO debug camera</h3><img src="/dashboard/debug"></div>
        </div>
    </body>
    </html>
    """


@app.route("/mode/<mode>", methods=["GET", "POST"])
def mode_route(mode):
    normalized = set_current_mode(mode)
    return jsonify({"accepted": True, "robot_name": ROBOT_NAME, "mode": normalized})


def start_debug_web():
    def run():
        print("====================================")
        print(f"dashboard : http://127.0.0.1:{DEBUG_PORT}/dashboard")
        print("====================================")
        app.run(host=DEBUG_HOST, port=DEBUG_PORT, threaded=True, use_reloader=False)

    threading.Thread(target=run, daemon=True).start()


# =========================================================
# 9. main
# =========================================================

def main():
    set_current_mode(INITIAL_MODE)

    print("====================================")
    print("PC/GPU YOLO Follow Server Start - Gateway Compatible")
    print("====================================")
    print(f"ROBOT_NAME        : {ROBOT_NAME}")
    print(f"CAMERA_URL        : {CAMERA_URL}")
    print(f"INITIAL_MODE      : {get_current_mode()}")
    print(f"BOX_MODEL_PATH    : {BOX_MODEL_PATH}")
    print(f"BOMB_MODEL_PATH   : {BOMB_MODEL_PATH}")
    print(f"CONF_THRES        : {CONF_THRES}")
    print(f"DEVICE            : {DEVICE}")
    print(f"GATEWAY           : {YOLO_GATEWAY_HOST}:{YOLO_GATEWAY_PORT}")
    print("====================================")


    gateway = YoloGatewayTcpClient(YOLO_GATEWAY_HOST, YOLO_GATEWAY_PORT, ROBOT_NAME)
    reader = HttpCAMERAReader(CAMERA_URL)
    start_debug_web()

    worker = threading.Thread(target=yolo_loop, args=(reader, gateway), daemon=True)
    worker.start()

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("[INFO] KeyboardInterrupt")
    finally:
        print("[INFO] stopping server")
        reader.stop()
        gateway.stop()


if __name__ == "__main__":
    main()
