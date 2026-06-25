#!/usr/bin/env python3
"""
Standalone Flask <-> ROS2 map GUI gateway.

기능:
  - /pinky/map 실시간 구독 후 웹 Canvas로 전송
  - /pinky/clicked_point 발행
  - /wf1/amcl_pose, /wf2/amcl_pose 구독 후 로봇 위치 전송
  - dispatcher SQLite DB(nav_points)를 읽어 clicked/random 좌표를 지도 위에 표시

이 파일은 기존 웹서버/dispatcher 코드에 합치지 않고 독립 실행하는 용도다.
"""

from __future__ import annotations

import base64
import json
import math
import os
import queue
import sqlite3
import threading
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

from geometry_msgs.msg import PointStamped, PoseWithCovarianceStamped
from nav_msgs.msg import OccupancyGrid

try:
    from map_msgs.msg import OccupancyGridUpdate
except Exception:  # map_msgs가 설치되어 있지 않아도 전체 웹서버는 실행 가능하게 처리
    OccupancyGridUpdate = None


# -----------------------------
# 환경 변수 기반 설정
# -----------------------------
ROS_DOMAIN_ID = int(os.environ.get("ROS_DOMAIN_ID", os.environ.get("ROSCUE_ROS_DOMAIN_ID", "10")))

MAP_TOPIC = os.environ.get("ROSCUE_MAP_TOPIC", "/pinky/map")
MAP_UPDATE_TOPIC = os.environ.get("ROSCUE_MAP_UPDATE_TOPIC", "/pinky/map_updates")
CLICKED_POINT_TOPIC = os.environ.get("ROSCUE_CLICKED_POINT_TOPIC", "/pinky/clicked_point")
WF1_POSE_TOPIC = os.environ.get("ROSCUE_WF1_POSE_TOPIC", "/wf1/amcl_pose")
WF2_POSE_TOPIC = os.environ.get("ROSCUE_WF2_POSE_TOPIC", "/wf2/amcl_pose")

# DB 경로 수정 필요
DB_PATH = os.environ.get("ROSCUE_NAV_DB_PATH", "/home/user/NEWrosproject/turtlebot/coord_list/roscue_nav_points.db")
DB_POLL_SEC = float(os.environ.get("ROSCUE_DB_POLL_SEC", "1.0"))
MAP_EMIT_MIN_PERIOD_SEC = float(os.environ.get("ROSCUE_MAP_EMIT_MIN_PERIOD_SEC", "0.4"))

MAP_FRAME = os.environ.get("ROSCUE_MAP_FRAME", "map")
MAX_EVENT_QUEUE_SIZE = int(os.environ.get("ROSCUE_MAX_EVENT_QUEUE_SIZE", "200"))


@dataclass
class MapMeta:
    width: int
    height: int
    resolution: float
    origin_x: float
    origin_y: float
    frame_id: str


class GuiState:
    """Flask 요청 스레드와 ROS spin 스레드가 공유하는 상태."""

    def __init__(self):
        self._lock = threading.RLock()
        self._subscribers: List[queue.Queue] = []

        self.map_version = 0
        self.map_payload: Optional[Dict[str, Any]] = None

        self.robot_poses: Dict[str, Dict[str, Any]] = {}
        self.points_version = 0
        self.points: List[Dict[str, Any]] = []
        self.local_clicked_points: List[Dict[str, Any]] = []

        self.status: Dict[str, Any] = {
            "ros_domain_id": ROS_DOMAIN_ID,
            "map_topic": MAP_TOPIC,
            "map_update_topic": MAP_UPDATE_TOPIC,
            "clicked_point_topic": CLICKED_POINT_TOPIC,
            "wf1_pose_topic": WF1_POSE_TOPIC,
            "wf2_pose_topic": WF2_POSE_TOPIC,
            "db_path": DB_PATH,
            "db_available": False,
            "last_db_error": "",
            "last_map_time": None,
            "last_points_time": None,
        }

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=MAX_EVENT_QUEUE_SIZE)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def _broadcast_locked(self, event: str, data: Dict[str, Any]) -> None:
        dead: List[queue.Queue] = []
        payload = {"event": event, "data": data}
        for q in self._subscribers:
            try:
                q.put_nowait(payload)
            except queue.Full:
                # 오래된 클라이언트 큐가 꽉 차면 가장 오래된 항목 하나를 버리고 최신값 유지
                try:
                    _ = q.get_nowait()
                    q.put_nowait(payload)
                except Exception:
                    dead.append(q)
        for q in dead:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "map": self.map_payload,
                "map_version": self.map_version,
                "robot_poses": self.robot_poses,
                "points": self._merged_points_locked(),
                "points_version": self.points_version,
                "status": dict(self.status),
            }

    def set_status(self, **kwargs: Any) -> None:
        with self._lock:
            self.status.update(kwargs)
            self._broadcast_locked("status", dict(self.status))

    def set_map(self, payload: Dict[str, Any]) -> None:
        with self._lock:
            self.map_version += 1
            payload["version"] = self.map_version
            self.map_payload = payload
            self.status["last_map_time"] = time.time()
            self._broadcast_locked("map", payload)

    def set_robot_pose(self, robot_name: str, pose: Dict[str, Any]) -> None:
        with self._lock:
            self.robot_poses[robot_name] = pose
            self._broadcast_locked("robot_pose", {"robot_name": robot_name, **pose})

    def set_points_from_db(self, points: List[Dict[str, Any]], db_available: bool, error: str = "") -> None:
        with self._lock:
            self.points_version += 1
            self.points = points
            self.status["db_available"] = db_available
            self.status["last_db_error"] = error
            self.status["last_points_time"] = time.time()
            self._broadcast_locked("points", {
                "version": self.points_version,
                "points": self._merged_points_locked(),
            })
            self._broadcast_locked("status", dict(self.status))

    def add_local_clicked_point(self, x: float, y: float) -> None:
        """DB가 아직 갱신되지 않았거나 dispatcher가 꺼져 있어도 웹에서 클릭한 점을 즉시 표시."""
        with self._lock:
            now = time.time()
            self.local_clicked_points.append({
                "id": f"local-{int(now * 1000)}",
                "order": None,
                "x": x,
                "y": y,
                "z": 0.0,
                "source": "web_clicked_local",
                "status": "local",
                "assigned_robot": None,
                "created_at": now,
            })
            # 너무 오래 쌓이지 않게 최근 200개만 유지
            self.local_clicked_points = self.local_clicked_points[-200:]
            self.points_version += 1
            self._broadcast_locked("points", {
                "version": self.points_version,
                "points": self._merged_points_locked(),
            })

    def _merged_points_locked(self) -> List[Dict[str, Any]]:
        """DB point와 local click point를 합치되, 좌표가 거의 같은 local point는 숨김."""
        merged = list(self.points)
        for lp in self.local_clicked_points:
            duplicate = False
            for p in self.points:
                if p.get("source", "").startswith("clicked") or p.get("source") == "clicked":
                    if abs(float(p.get("x", 9999)) - lp["x"]) < 0.03 and abs(float(p.get("y", 9999)) - lp["y"]) < 0.03:
                        duplicate = True
                        break
            if not duplicate:
                merged.append(lp)
        return merged


STATE = GuiState()


class StandaloneMapGuiNode(Node):
    def __init__(self, state: GuiState):
        super().__init__("roscue_standalone_map_gui")
        self.state = state

        self.latest_map_msg: Optional[OccupancyGrid] = None
        self.latest_map_data: Optional[List[int]] = None
        self.last_map_emit_time = 0.0
        self.last_points_signature = ""

        map_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )

        map_update_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )

        self.map_sub = self.create_subscription(OccupancyGrid, MAP_TOPIC, self.on_map, map_qos)

        self.map_update_sub = None
        if OccupancyGridUpdate is not None:
            self.map_update_sub = self.create_subscription(
                OccupancyGridUpdate,
                MAP_UPDATE_TOPIC,
                self.on_map_update,
                map_update_qos,
            )

        self.clicked_point_pub = self.create_publisher(PointStamped, CLICKED_POINT_TOPIC, 10)

        self.wf1_pose_sub = self.create_subscription(
            PoseWithCovarianceStamped,
            WF1_POSE_TOPIC,
            lambda msg: self.on_robot_pose("wf1", msg),
            30,
        )
        self.wf2_pose_sub = self.create_subscription(
            PoseWithCovarianceStamped,
            WF2_POSE_TOPIC,
            lambda msg: self.on_robot_pose("wf2", msg),
            30,
        )

        self.db_timer = self.create_timer(DB_POLL_SEC, self.poll_points_db)

        self.get_logger().info("Standalone map GUI ROS node started.")
        self.get_logger().info(f"ROS_DOMAIN_ID={ROS_DOMAIN_ID}")
        self.get_logger().info(f"map_topic={MAP_TOPIC}")
        self.get_logger().info(f"map_update_topic={MAP_UPDATE_TOPIC}")
        self.get_logger().info(f"clicked_point_topic={CLICKED_POINT_TOPIC}")
        self.get_logger().info(f"wf1_pose_topic={WF1_POSE_TOPIC}")
        self.get_logger().info(f"wf2_pose_topic={WF2_POSE_TOPIC}")
        self.get_logger().info(f"db_path={DB_PATH}")

        self.state.set_status(
            ros_domain_id=ROS_DOMAIN_ID,
            map_topic=MAP_TOPIC,
            map_update_topic=MAP_UPDATE_TOPIC,
            clicked_point_topic=CLICKED_POINT_TOPIC,
            wf1_pose_topic=WF1_POSE_TOPIC,
            wf2_pose_topic=WF2_POSE_TOPIC,
            db_path=DB_PATH,
        )

    # -----------------------------
    # ROS callbacks
    # -----------------------------
    def on_map(self, msg: OccupancyGrid) -> None:
        width = int(msg.info.width)
        height = int(msg.info.height)
        expected = width * height
        if width <= 0 or height <= 0 or len(msg.data) != expected:
            self.get_logger().warn(
                f"Ignore malformed map: width={width}, height={height}, data={len(msg.data)}"
            )
            return

        self.latest_map_msg = msg
        self.latest_map_data = list(msg.data)
        self.emit_map_if_needed(force=True)

    def on_map_update(self, msg: Any) -> None:
        if self.latest_map_msg is None or self.latest_map_data is None:
            return

        map_width = int(self.latest_map_msg.info.width)
        map_height = int(self.latest_map_msg.info.height)

        update_x = int(msg.x)
        update_y = int(msg.y)
        update_width = int(msg.width)
        update_height = int(msg.height)

        if update_width <= 0 or update_height <= 0:
            return
        if update_x < 0 or update_y < 0 or update_x + update_width > map_width or update_y + update_height > map_height:
            self.get_logger().warn(
                f"Ignore out-of-range map update: ({update_x},{update_y},{update_width},{update_height})"
            )
            return
        if len(msg.data) != update_width * update_height:
            self.get_logger().warn("Ignore malformed map update data length.")
            return

        updated = self.latest_map_data
        for row in range(update_height):
            src_start = row * update_width
            dst_start = (update_y + row) * map_width + update_x
            updated[dst_start:dst_start + update_width] = list(msg.data[src_start:src_start + update_width])

        self.latest_map_msg.header = msg.header
        self.emit_map_if_needed(force=False)

    def on_robot_pose(self, robot_name: str, msg: PoseWithCovarianceStamped) -> None:
        q = msg.pose.pose.orientation
        yaw = quaternion_to_yaw(q.x, q.y, q.z, q.w)
        self.state.set_robot_pose(robot_name, {
            "x": float(msg.pose.pose.position.x),
            "y": float(msg.pose.pose.position.y),
            "z": float(msg.pose.pose.position.z),
            "yaw": yaw,
            "frame_id": msg.header.frame_id or MAP_FRAME,
            "stamp_sec": int(msg.header.stamp.sec),
            "stamp_nanosec": int(msg.header.stamp.nanosec),
            "recv_time": time.time(),
        })

    # -----------------------------
    # Public API from Flask routes
    # -----------------------------
    def publish_clicked_point(self, x: float, y: float, z: float = 0.0) -> Tuple[bool, str]:
        msg = PointStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = MAP_FRAME
        msg.point.x = float(x)
        msg.point.y = float(y)
        msg.point.z = float(z)
        self.clicked_point_pub.publish(msg)

        self.state.add_local_clicked_point(float(x), float(y))
        return True, f"{CLICKED_POINT_TOPIC} publish 완료: x={x:.3f}, y={y:.3f}"

    # -----------------------------
    # Map encoding
    # -----------------------------
    def emit_map_if_needed(self, force: bool = False) -> None:
        now = time.time()
        if not force and now - self.last_map_emit_time < MAP_EMIT_MIN_PERIOD_SEC:
            return
        self.last_map_emit_time = now

        if self.latest_map_msg is None or self.latest_map_data is None:
            return

        msg = self.latest_map_msg
        width = int(msg.info.width)
        height = int(msg.info.height)
        resolution = float(msg.info.resolution)
        origin = msg.info.origin.position
        frame_id = msg.header.frame_id or MAP_FRAME

        gray_bytes = occupancy_to_flipped_gray_bytes(self.latest_map_data, width, height)
        encoded = base64.b64encode(gray_bytes).decode("ascii")

        self.state.set_map({
            "width": width,
            "height": height,
            "resolution": resolution,
            "origin_x": float(origin.x),
            "origin_y": float(origin.y),
            "frame_id": frame_id,
            "encoding": "gray8-flipped-y-base64",
            "gray": encoded,
            "stamp_sec": int(msg.header.stamp.sec),
            "stamp_nanosec": int(msg.header.stamp.nanosec),
        })

    # -----------------------------
    # DB polling
    # -----------------------------
    def poll_points_db(self) -> None:
        if not DB_PATH:
            self.state.set_points_from_db([], db_available=False, error="ROSCUE_NAV_DB_PATH is empty")
            return
        if not os.path.exists(DB_PATH):
            self.state.set_points_from_db([], db_available=False, error=f"DB file not found: {DB_PATH}")
            return

        try:
            uri = f"file:{DB_PATH}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, timeout=0.2)
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """
                    SELECT point_order, x, y, z, frame_id, source, status,
                           assigned_robot, created_at, updated_at, dispatched_at, completed_at
                      FROM nav_points
                     ORDER BY point_order ASC
                    """
                ).fetchall()
            finally:
                conn.close()

            points = []
            for row in rows:
                source = str(row["source"] or "")
                # clicked point와 random point 지도 표시가 목적이므로 둘 다 포함한다.
                # 다른 source가 추가되어도 지도에서 참고 가능하게 그대로 둔다.
                points.append({
                    "id": f"db-{row['point_order']}",
                    "order": int(row["point_order"]),
                    "x": float(row["x"]),
                    "y": float(row["y"]),
                    "z": float(row["z"]),
                    "frame_id": str(row["frame_id"] or MAP_FRAME),
                    "source": source,
                    "status": str(row["status"] or ""),
                    "assigned_robot": None if row["assigned_robot"] is None else str(row["assigned_robot"]),
                    "created_at": None if row["created_at"] is None else float(row["created_at"]),
                    "updated_at": None if row["updated_at"] is None else float(row["updated_at"]),
                    "dispatched_at": None if row["dispatched_at"] is None else float(row["dispatched_at"]),
                    "completed_at": None if row["completed_at"] is None else float(row["completed_at"]),
                })

            signature = json.dumps(points, sort_keys=True, separators=(",", ":"))
            if signature != self.last_points_signature:
                self.last_points_signature = signature
                self.state.set_points_from_db(points, db_available=True, error="")
            else:
                self.state.set_status(db_available=True, last_db_error="")

        except sqlite3.Error as e:
            self.state.set_points_from_db([], db_available=False, error=f"SQLite error: {e}")
        except Exception as e:
            self.state.set_points_from_db([], db_available=False, error=f"DB polling error: {e}")


def occupancy_to_flipped_gray_bytes(data: List[int], width: int, height: int) -> bytes:
    """
    OccupancyGrid data를 Canvas에서 바로 그릴 수 있는 gray8 bytes로 변환한다.

    ROS OccupancyGrid:
      data[0] = map grid의 좌하단 셀
    Canvas:
      y=0 = 화면 위쪽

    그래서 row 순서를 flip해서 보낸다.
    """
    out = bytearray(width * height)
    for y in range(height):
        src_y = height - 1 - y
        src_base = src_y * width
        dst_base = y * width
        for x in range(width):
            v = int(data[src_base + x])
            if v < 0:
                g = 190       # unknown
            elif v == 0:
                g = 255       # free
            elif v >= 65:
                g = 0         # occupied
            else:
                # 1~64는 중간 점유 확률. 낮을수록 밝고 높을수록 어둡게 표현.
                g = max(40, min(230, 255 - int(v * 2.2)))
            out[dst_base + x] = g
    return bytes(out)


def quaternion_to_yaw(x: float, y: float, z: float, w: float) -> float:
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def start_ros_thread() -> StandaloneMapGuiNode:
    if not rclpy.ok():
        rclpy.init(domain_id=ROS_DOMAIN_ID)
    node = StandaloneMapGuiNode(STATE)
    thread = threading.Thread(target=lambda: rclpy.spin(node), daemon=True)
    thread.start()
    return node
