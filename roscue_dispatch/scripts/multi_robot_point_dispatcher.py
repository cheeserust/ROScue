#!/usr/bin/env python3

import math
import os
import random
import sqlite3
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from rosidl_runtime_py.utilities import get_message

from geometry_msgs.msg import PointStamped, PoseStamped, PoseWithCovarianceStamped
from nav_msgs.msg import OccupancyGrid
from std_msgs.msg import Empty

try:
    from map_msgs.msg import OccupancyGridUpdate
except ImportError:
    OccupancyGridUpdate = None


@dataclass
class SavedPoint:
    x: float
    y: float
    z: float
    frame_id: str
    order: int
    source: str = 'clicked'


class RobotState:
    IDLE = 'IDLE'
    NAVIGATING = 'NAVIGATING'
    WAITING = 'WAITING'
    STOPPED = 'STOPPED'

    def __init__(self, key: str, name: str, pose_topic: str, goal_topic: str, cancel_topic: str):
        self.key = key
        self.name = name
        self.pose_topic = pose_topic
        self.goal_topic = goal_topic
        self.cancel_topic = cancel_topic

        self.latest_xy: Optional[Tuple[float, float]] = None
        self.latest_pose_recv_time: Optional[float] = None

        # start/stop 상태는 PC dispatcher 내부에서만 관리한다.
        self.driving_command = 'stop'
        self.state = self.STOPPED

        self.current_goal: Optional[SavedPoint] = None
        self.wait_start_time: Optional[float] = None
        self.goal_start_time: Optional[float] = None
        self.last_goal_publish_time: float = 0.0
        self.last_status_log_time: float = 0.0
        self.last_distance_to_goal: Optional[float] = None

        self.goal_pub = None
        self.cancel_pub = None
        self.last_cancel_publish_time: float = 0.0

        # 각 로봇이 실제로 도착 완료한 goal 개수.
        # 랜덤 goal 생성은 wf1/wf2가 각각 첫 번째 goal에 도착한 뒤부터 시작한다.
        self.completed_goal_count: int = 0

    def has_pose(self) -> bool:
        return self.latest_xy is not None

    def is_available(self) -> bool:
        # start command를 받은 IDLE 로봇만 새 goal을 받을 수 있다.
        return self.driving_command == 'start' and self.state == self.IDLE


class MultiRobotPointDispatcher(Node):
    """
    command 구조:
      - PC가 중앙서버의 /driving_command(roscue_interface/msg/MainToNavMsg)를 직접 구독한다.
      - MainToNavMsg.robot_name: "waffle1" | "waffle2"
      - MainToNavMsg.command: "start" | "stop"
      - stop 수신 시 PC는 해당 로봇으로 goal publish를 중단하고, robot domain의 gate에
        /cancel_navigation(Empty)을 1회 publish해서 현재 NavigateToPose action만 cancel한다.

    DB:
      - clicked point와 random free-space point는 수신/생성 즉시 SQLite DB에 저장된다.
      - dispatch, requeue, complete 상태도 즉시 DB에 반영한다.
    """

    def __init__(self):
        super().__init__('multi_robot_point_dispatcher')

        self.declare_parameter('clicked_point_topic', '/pinky/clicked_point')
        self.declare_parameter('map_topic', '/pinky/map')
        self.declare_parameter('map_update_topic', '/pinky/map_updates')

        self.declare_parameter('wf1_pose_topic', '/wf1/amcl_pose')
        self.declare_parameter('wf2_pose_topic', '/wf2/amcl_pose')

        self.declare_parameter('wf1_goal_topic', '/wf1/goal_pose')
        self.declare_parameter('wf2_goal_topic', '/wf2/goal_pose')

        # 중앙서버가 PC domain 10에 publish하는 command topic.
        # 예: ros2 topic pub --once /driving_command roscue_interface/msg/MainToNavMsg "{robot_name: 'waffle1', command: 'start'}"
        self.declare_parameter('driving_command_topic', '/driving_command')
        self.declare_parameter('driving_command_type', 'roscue_interface/msg/MainToNavMsg')
        self.declare_parameter('initial_driving_command', 'stop')

        # PC -> robot domain cancel 신호. 각 bridge가 robot local /cancel_navigation으로 remap한다.
        self.declare_parameter('wf1_cancel_topic', '/wf1/cancel_navigation')
        self.declare_parameter('wf2_cancel_topic', '/wf2/cancel_navigation')

        # clicked/random 좌표와 상태를 저장할 SQLite DB.
        self.declare_parameter('db_path', '/home/user/NEWrosproject/turtlebot/roscue_nav_points.db') # 경로 수정 필요
        self.declare_parameter('load_pending_from_db_on_start', True)

        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('goal_wait_sec', 5.0)
        self.declare_parameter('arrival_tolerance', 0.25)
        self.declare_parameter('default_yaw', 0.0)
        self.declare_parameter('timer_period_sec', 0.2)
        self.declare_parameter('require_pose_before_dispatch', True)

        self.declare_parameter('goal_republish_sec', 1.0)
        self.declare_parameter('status_log_sec', 2.0)
        self.declare_parameter('pose_timeout_sec', 10.0)

        # Random goal generation.
        # wf1/wf2가 각각 첫 번째 goal에 도착한 뒤부터, 최신 /pinky/map에서
        # 장애물/unknown과 일정 거리 이상 떨어진 free cell을 30초마다 뽑아 pending_points에 저장한다.
        self.declare_parameter('random_goal_enabled', True)
        self.declare_parameter('random_goal_period_sec', 30.0)
        self.declare_parameter('random_goal_min_clearance_m', 0.45)
        self.declare_parameter('random_goal_occupied_threshold', 50)
        self.declare_parameter('random_goal_unknown_is_obstacle', True)
        self.declare_parameter('random_goal_max_attempts', 2000)
        self.declare_parameter('random_goal_border_margin_cells', 2)
        self.declare_parameter('random_goal_max_pending', 0)
        self.declare_parameter('random_goal_seed', 0)
        self.declare_parameter('random_goal_use_map_updates', True)

        self.clicked_point_topic = self.get_parameter('clicked_point_topic').value
        self.map_topic = self.get_parameter('map_topic').value
        self.map_update_topic = self.get_parameter('map_update_topic').value
        self.map_frame = self.get_parameter('map_frame').value

        self.goal_wait_sec = float(self.get_parameter('goal_wait_sec').value)
        self.arrival_tolerance = float(self.get_parameter('arrival_tolerance').value)
        self.default_yaw = float(self.get_parameter('default_yaw').value)
        self.timer_period_sec = float(self.get_parameter('timer_period_sec').value)

        self.require_pose_before_dispatch = bool(
            self.get_parameter('require_pose_before_dispatch').value
        )

        self.goal_republish_sec = float(self.get_parameter('goal_republish_sec').value)
        self.status_log_sec = float(self.get_parameter('status_log_sec').value)
        self.pose_timeout_sec = float(self.get_parameter('pose_timeout_sec').value)

        self.random_goal_enabled = bool(self.get_parameter('random_goal_enabled').value)
        self.random_goal_period_sec = float(self.get_parameter('random_goal_period_sec').value)
        self.random_goal_min_clearance_m = float(self.get_parameter('random_goal_min_clearance_m').value)
        self.random_goal_occupied_threshold = int(self.get_parameter('random_goal_occupied_threshold').value)
        self.random_goal_unknown_is_obstacle = bool(
            self.get_parameter('random_goal_unknown_is_obstacle').value
        )
        self.random_goal_max_attempts = int(self.get_parameter('random_goal_max_attempts').value)
        self.random_goal_border_margin_cells = int(
            self.get_parameter('random_goal_border_margin_cells').value
        )
        self.random_goal_max_pending = int(self.get_parameter('random_goal_max_pending').value)
        self.random_goal_seed = int(self.get_parameter('random_goal_seed').value)
        self.random_goal_use_map_updates = bool(
            self.get_parameter('random_goal_use_map_updates').value
        )
        self.random_generator = random.Random()
        if self.random_goal_seed != 0:
            self.random_generator.seed(self.random_goal_seed)

        self.driving_command_topic = self.get_parameter('driving_command_topic').value
        self.driving_command_type_str = self.get_parameter('driving_command_type').value
        self.command_msg_type = get_message(self.driving_command_type_str)
        self.initial_driving_command = str(self.get_parameter('initial_driving_command').value).strip().lower()
        if self.initial_driving_command not in ('start', 'stop'):
            self.get_logger().warn(
                f'Invalid initial_driving_command={self.initial_driving_command!r}. Use stop.'
            )
            self.initial_driving_command = 'stop'
        self.db_path = self.get_parameter('db_path').value
        self.load_pending_from_db_on_start = bool(self.get_parameter('load_pending_from_db_on_start').value)

        self.command_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )

        self.robots: Dict[str, RobotState] = {
            'wf1': RobotState(
                key='wf1',
                name='Waffle/WF1',
                pose_topic=self.get_parameter('wf1_pose_topic').value,
                goal_topic=self.get_parameter('wf1_goal_topic').value,
                cancel_topic=self.get_parameter('wf1_cancel_topic').value,
            ),
            'wf2': RobotState(
                key='wf2',
                name='Waffle/WF2',
                pose_topic=self.get_parameter('wf2_pose_topic').value,
                goal_topic=self.get_parameter('wf2_goal_topic').value,
                cancel_topic=self.get_parameter('wf2_cancel_topic').value,
            ),
        }

        for robot in self.robots.values():
            robot.driving_command = self.initial_driving_command
            robot.state = RobotState.IDLE if self.initial_driving_command == 'start' else RobotState.STOPPED

        self.pending_points: List[SavedPoint] = []
        self.point_count = 0
        self.first_goal_dispatched = False

        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self.db_conn = sqlite3.connect(self.db_path, timeout=5.0)
        self.db_conn.row_factory = sqlite3.Row
        self.init_db()
        self.reset_unfinished_db_points_on_startup()
        if self.load_pending_from_db_on_start:
            self.load_pending_points_from_db()
        self.load_runtime_counts_from_db()

        self.latest_map: Optional[OccupancyGrid] = None
        self.latest_map_recv_time: Optional[float] = None
        self.random_goal_generation_started = False
        self.last_random_goal_time: Optional[float] = None
        self._last_random_wait_log_time = 0.0

        self.pose_subs = []

        self.driving_command_sub = self.create_subscription(
            self.command_msg_type,
            self.driving_command_topic,
            self.driving_command_callback,
            self.command_qos,
        )

        self.clicked_sub = self.create_subscription(
            PointStamped,
            self.clicked_point_topic,
            self.clicked_point_callback,
            100,
        )

        map_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.map_sub = self.create_subscription(
            OccupancyGrid,
            self.map_topic,
            self.map_callback,
            map_qos,
        )

        self.map_update_sub = None
        if self.random_goal_use_map_updates and OccupancyGridUpdate is not None:
            map_update_qos = QoSProfile(
                history=HistoryPolicy.KEEP_LAST,
                depth=10,
                reliability=ReliabilityPolicy.RELIABLE,
                durability=DurabilityPolicy.VOLATILE,
            )
            self.map_update_sub = self.create_subscription(
                OccupancyGridUpdate,
                self.map_update_topic,
                self.map_update_callback,
                map_update_qos,
            )
        elif self.random_goal_use_map_updates:
            self.get_logger().warn(
                'map_msgs is not available, so /pinky/map_updates will not be applied. '
                'Random goals will still use the latest full /pinky/map message.'
            )

        for key, robot in self.robots.items():
            pose_sub = self.create_subscription(
                PoseWithCovarianceStamped,
                robot.pose_topic,
                lambda msg, robot_key=key: self.robot_pose_callback(robot_key, msg),
                30,
            )
            self.pose_subs.append(pose_sub)

            # PC domain 10에서 /wf1/goal_pose, /wf2/goal_pose publish.
            # pc10_to_wf1_14 / pc10_to_wf2_15 bridge가 각 로봇 domain의 /pending_goal_pose로 전달한다.
            robot.goal_pub = self.create_publisher(
                PoseStamped,
                robot.goal_topic,
                10,
            )

            # PC domain 10에서 /wf1/cancel_navigation, /wf2/cancel_navigation publish.
            # pc10_to_wf1_14 / pc10_to_wf2_15 bridge가 각 로봇 domain의 /cancel_navigation으로 전달한다.
            robot.cancel_pub = self.create_publisher(
                Empty,
                robot.cancel_topic,
                10,
            )

        self.timer = self.create_timer(self.timer_period_sec, self.main_loop)

        self.get_logger().info('PC multi robot point dispatcher started.')
        self.get_logger().info(f'clicked_point_topic: {self.clicked_point_topic}')
        self.get_logger().info(f'map_topic: {self.map_topic}')
        self.get_logger().info(f'map_update_topic: {self.map_update_topic}')
        self.get_logger().info(f'driving_command_topic: {self.driving_command_topic}')
        self.get_logger().info(f'driving_command_type: {self.driving_command_type_str}')
        self.get_logger().info(f'arrival_tolerance: {self.arrival_tolerance:.2f} m')
        self.get_logger().info(f'goal_wait_sec: {self.goal_wait_sec:.1f} sec')
        self.get_logger().info(f'require_pose_before_dispatch: {self.require_pose_before_dispatch}')
        self.get_logger().info(f'goal_republish_sec: {self.goal_republish_sec:.1f} sec')
        self.get_logger().info(f'status_log_sec: {self.status_log_sec:.1f} sec')
        self.get_logger().info(f'pose_timeout_sec: {self.pose_timeout_sec:.1f} sec')
        self.get_logger().info(f'initial driving command: {self.initial_driving_command}')
        self.get_logger().info(f'db_path: {self.db_path}')
        self.get_logger().info(f'load_pending_from_db_on_start: {self.load_pending_from_db_on_start}')
        self.get_logger().info(f'random_goal_enabled: {self.random_goal_enabled}')
        self.get_logger().info(f'random_goal_period_sec: {self.random_goal_period_sec:.1f} sec')
        self.get_logger().info(f'random_goal_min_clearance_m: {self.random_goal_min_clearance_m:.2f} m')
        self.get_logger().info(f'random_goal_occupied_threshold: {self.random_goal_occupied_threshold}')
        self.get_logger().info(f'random_goal_unknown_is_obstacle: {self.random_goal_unknown_is_obstacle}')
        self.get_logger().info(f'random_goal_max_attempts: {self.random_goal_max_attempts}')
        self.get_logger().info(f'random_goal_border_margin_cells: {self.random_goal_border_margin_cells}')
        self.get_logger().info(f'random_goal_max_pending: {self.random_goal_max_pending} (0 means unlimited)')
        self.get_logger().info(f'random_goal_use_map_updates: {self.random_goal_use_map_updates}')

        for robot in self.robots.values():
            self.get_logger().info(
                f'{robot.name}: pose_topic={robot.pose_topic}, '
                f'goal_topic={robot.goal_topic}, cancel_topic={robot.cancel_topic}, '
                f'initial_state={robot.state}, initial_command={robot.driving_command}'
            )

    def init_db(self):
        self.db_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nav_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                point_order INTEGER NOT NULL UNIQUE,
                x REAL NOT NULL,
                y REAL NOT NULL,
                z REAL NOT NULL,
                frame_id TEXT NOT NULL,
                source TEXT NOT NULL,
                status TEXT NOT NULL,
                assigned_robot TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                dispatched_at REAL,
                completed_at REAL
            )
            """
        )
        self.db_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nav_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                robot_key TEXT,
                robot_name TEXT,
                command TEXT,
                point_order INTEGER,
                detail TEXT,
                created_at REAL NOT NULL
            )
            """
        )
        self.db_conn.commit()

    def reset_unfinished_db_points_on_startup(self):
        # 이전 실행이 주행 중 종료되었다면 navigating/waiting 좌표는 다시 pending으로 되돌린다.
        now = time.time()
        self.db_conn.execute(
            """
            UPDATE nav_points
               SET status='pending', assigned_robot=NULL, updated_at=?
             WHERE status IN ('navigating', 'waiting')
            """,
            (now,),
        )
        self.db_conn.commit()

    def load_pending_points_from_db(self):
        rows = self.db_conn.execute(
            """
            SELECT point_order, x, y, z, frame_id, source
              FROM nav_points
             WHERE status='pending'
             ORDER BY point_order ASC
            """
        ).fetchall()

        self.pending_points = [
            SavedPoint(
                x=float(row['x']),
                y=float(row['y']),
                z=float(row['z']),
                frame_id=str(row['frame_id']),
                order=int(row['point_order']),
                source=str(row['source']),
            )
            for row in rows
        ]
        max_order_row = self.db_conn.execute(
            'SELECT COALESCE(MAX(point_order), 0) AS max_order FROM nav_points'
        ).fetchone()
        self.point_count = int(max_order_row['max_order']) if max_order_row else 0

        if self.pending_points:
            self.get_logger().info(
                f'Loaded {len(self.pending_points)} pending point(s) from DB. '
                f'point_count starts at {self.point_count}.'
            )

    def load_runtime_counts_from_db(self):
        rows = self.db_conn.execute(
            """
            SELECT assigned_robot, COUNT(*) AS cnt
              FROM nav_points
             WHERE status='completed' AND assigned_robot IS NOT NULL
             GROUP BY assigned_robot
            """
        ).fetchall()
        for row in rows:
            key = str(row['assigned_robot'])
            if key in self.robots:
                self.robots[key].completed_goal_count = int(row['cnt'])

        dispatched_or_completed = self.db_conn.execute(
            """
            SELECT COUNT(*) AS cnt
              FROM nav_points
             WHERE status IN ('navigating', 'waiting', 'completed')
            """
        ).fetchone()
        if dispatched_or_completed and int(dispatched_or_completed['cnt']) > 0:
            self.first_goal_dispatched = True

    def save_point_to_db(self, point: SavedPoint, status: str = 'pending'):
        now = time.time()
        self.db_conn.execute(
            """
            INSERT INTO nav_points (
                point_order, x, y, z, frame_id, source, status,
                assigned_robot, created_at, updated_at, dispatched_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, NULL, NULL)
            ON CONFLICT(point_order) DO UPDATE SET
                x=excluded.x,
                y=excluded.y,
                z=excluded.z,
                frame_id=excluded.frame_id,
                source=excluded.source,
                status=excluded.status,
                assigned_robot=NULL,
                updated_at=excluded.updated_at,
                dispatched_at=NULL,
                completed_at=NULL
            """,
            (
                point.order,
                point.x,
                point.y,
                point.z,
                point.frame_id,
                point.source,
                status,
                now,
                now,
            ),
        )
        self.db_conn.commit()

    def update_point_status(self, point: Optional[SavedPoint], status: str, robot: Optional[RobotState] = None):
        if point is None:
            return
        now = time.time()
        assigned_robot = None if robot is None else robot.key
        dispatched_at = now if status == 'navigating' else None
        completed_at = now if status == 'completed' else None
        self.db_conn.execute(
            """
            UPDATE nav_points
               SET status=?,
                   assigned_robot=?,
                   updated_at=?,
                   dispatched_at=CASE WHEN ? IS NOT NULL THEN ? ELSE dispatched_at END,
                   completed_at=CASE WHEN ? IS NOT NULL THEN ? ELSE completed_at END
             WHERE point_order=?
            """,
            (
                status,
                assigned_robot,
                now,
                dispatched_at,
                dispatched_at,
                completed_at,
                completed_at,
                point.order,
            ),
        )
        self.db_conn.commit()

    def log_event_to_db(
        self,
        event_type: str,
        robot: Optional[RobotState] = None,
        command: Optional[str] = None,
        point: Optional[SavedPoint] = None,
        detail: str = '',
    ):
        self.db_conn.execute(
            """
            INSERT INTO nav_events (
                event_type, robot_key, robot_name, command, point_order, detail, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                None if robot is None else robot.key,
                None if robot is None else robot.name,
                command,
                None if point is None else point.order,
                detail,
                time.time(),
            ),
        )
        self.db_conn.commit()

    def clicked_point_callback(self, msg: PointStamped):
        frame_id = msg.header.frame_id if msg.header.frame_id else self.map_frame

        if frame_id != self.map_frame:
            self.get_logger().warn(
                f'Clicked point frame is "{frame_id}", expected "{self.map_frame}". '
                'This dispatcher assumes map-frame clicked points.'
            )

        self.point_count += 1
        point = SavedPoint(
            x=msg.point.x,
            y=msg.point.y,
            z=msg.point.z,
            frame_id=frame_id,
            order=self.point_count,
        )
        self.save_point_to_db(point, status='pending')
        self.log_event_to_db('point_saved', point=point, detail='clicked point saved')
        self.pending_points.append(point)

        self.get_logger().info(
            f'Saved clicked point #{point.order} to DB and pending_points: '
            f'x={point.x:.3f}, y={point.y:.3f}, frame={point.frame_id}, '
            f'pending={len(self.pending_points)}'
        )

        # 새 point가 들어왔을 때 이미 start 상태인 로봇이 있으면 바로 배정 시도.
        self.dispatch_pending_points()

    def map_callback(self, msg: OccupancyGrid):
        frame_id = msg.header.frame_id if msg.header.frame_id else self.map_frame

        if frame_id != self.map_frame:
            self.get_logger().warn(
                f'Map frame is "{frame_id}", expected "{self.map_frame}". '
                'Random goal generation assumes map-frame OccupancyGrid.'
            )

        expected_size = msg.info.width * msg.info.height
        if len(msg.data) != expected_size:
            self.get_logger().warn(
                f'Received malformed map: data={len(msg.data)}, '
                f'width*height={expected_size}. Ignore this map.'
            )
            return

        self.latest_map = msg
        self.latest_map_recv_time = time.time()

    def map_update_callback(self, msg):
        if self.latest_map is None:
            return

        map_width = int(self.latest_map.info.width)
        map_height = int(self.latest_map.info.height)

        if msg.x < 0 or msg.y < 0 or msg.width <= 0 or msg.height <= 0:
            self.get_logger().warn(
                f'Ignoring invalid map update: x={msg.x}, y={msg.y}, '
                f'width={msg.width}, height={msg.height}'
            )
            return

        if msg.x + msg.width > map_width or msg.y + msg.height > map_height:
            self.get_logger().warn(
                f'Ignoring out-of-range map update: update=({msg.x},{msg.y},{msg.width},{msg.height}), '
                f'map=({map_width},{map_height})'
            )
            return

        expected_size = int(msg.width * msg.height)
        if len(msg.data) != expected_size:
            self.get_logger().warn(
                f'Ignoring malformed map update: data={len(msg.data)}, expected={expected_size}'
            )
            return

        # OccupancyGrid.data는 환경에 따라 array/list 형태가 다를 수 있어 list로 복사 후 갱신한다.
        updated_data = list(self.latest_map.data)
        update_width = int(msg.width)
        update_height = int(msg.height)
        update_x = int(msg.x)
        update_y = int(msg.y)

        for row in range(update_height):
            src_start = row * update_width
            src_end = src_start + update_width
            dst_start = (update_y + row) * map_width + update_x
            dst_end = dst_start + update_width
            updated_data[dst_start:dst_end] = list(msg.data[src_start:src_end])

        self.latest_map.data = updated_data
        self.latest_map.header = msg.header
        self.latest_map_recv_time = time.time()

    def robot_pose_callback(self, robot_key: str, msg: PoseWithCovarianceStamped):
        robot = self.robots[robot_key]
        frame_id = msg.header.frame_id if msg.header.frame_id else self.map_frame

        if frame_id != self.map_frame:
            self.get_logger().warn(
                f'{robot.name} pose frame is "{frame_id}", expected "{self.map_frame}". '
                'Distance calculation assumes map-frame AMCL pose.'
            )

        robot.latest_xy = (
            msg.pose.pose.position.x,
            msg.pose.pose.position.y,
        )
        robot.latest_pose_recv_time = time.time()

    def driving_command_callback(self, msg):
        robot_name = self.extract_robot_name(msg)
        command = self.extract_command(msg)
        robot_key = self.normalize_robot_name(robot_name)

        self.get_logger().info(
            f'Received central driving command: robot_name={robot_name!r}, '
            f'normalized={robot_key!r}, command={command!r}'
        )

        if robot_key not in self.robots:
            self.get_logger().warn(
                f'Ignoring command with unknown robot_name={robot_name!r}. '
                'Expected "waffle1" or "waffle2".'
            )
            return

        if command not in ('start', 'stop'):
            self.get_logger().warn(
                f'Ignoring unknown command={command!r} for robot_name={robot_name!r}. '
                'Valid commands are "start" and "stop".'
            )
            return

        robot = self.robots[robot_key]
        self.log_event_to_db('command_received', robot=robot, command=command)

        if command == 'stop':
            self.handle_stop_command(robot)
        else:
            self.handle_start_command(robot)

        # start가 들어왔을 때 timer tick을 기다리지 않고 바로 pending point 배정 시도.
        self.dispatch_pending_points()

    def extract_robot_name(self, msg) -> str:
        if hasattr(msg, 'robot_name'):
            return str(msg.robot_name).strip().lower()
        return ''

    def normalize_robot_name(self, robot_name: str) -> str:
        name = robot_name.strip().lower()
        aliases = {
            'waffle1': 'wf1',
            'wf1': 'wf1',
            'w1': 'wf1',
            'waffle_1': 'wf1',
            'waffle2': 'wf2',
            'wf2': 'wf2',
            'w2': 'wf2',
            'waffle_2': 'wf2',
        }
        return aliases.get(name, name)

    def extract_command(self, msg) -> str:
        if hasattr(msg, 'command'):
            return str(msg.command).strip().lower()
        if hasattr(msg, 'data'):
            return str(msg.data).strip().lower()
        return ''

    def handle_stop_command(self, robot: RobotState):
        if (
            robot.driving_command == 'stop'
            and robot.current_goal is None
            and robot.state == RobotState.STOPPED
        ):
            self.get_logger().info(
                f'{robot.name} is already STOPPED. Send cancel once more to clear any stale Nav2 goal.'
            )
            self.publish_cancel_navigation(robot)
            return

        self.get_logger().info(f'{robot.name} handling STOP command.')
        robot.driving_command = 'stop'

        # stop이 목표 도착 전에 들어오면, 현재 목표를 DB/pending list로 되돌리고 current_goal을 비운다.
        if robot.current_goal is not None:
            self.requeue_current_goal(robot)

        robot.current_goal = None
        robot.state = RobotState.STOPPED
        robot.wait_start_time = None
        robot.goal_start_time = None
        robot.last_distance_to_goal = None

        # 속도 0을 계속 publish하지 않는다. Nav2 action만 cancel하고 이후 goal publish를 중단한다.
        self.publish_cancel_navigation(robot)
        self.log_event_to_db('robot_stopped', robot=robot, command='stop')

        self.get_logger().info(
            f'{robot.name} state changed to STOPPED. Goal publishing is now blocked. '
            f'pending={len(self.pending_points)}'
        )

    def handle_start_command(self, robot: RobotState):
        if robot.driving_command == 'start' and robot.state != RobotState.STOPPED:
            self.get_logger().info(
                f'{robot.name} is already in command=start, state={robot.state}. '
                'No state reset needed.'
            )
            return

        self.get_logger().info(f'{robot.name} handling START command.')
        robot.driving_command = 'start'

        # stop 상태에서 start가 오면 예전 goal을 직접 재개하지 않는다.
        # IDLE로만 바꾸고, pending_points 전체를 현재 pose 기준으로 다시 비교한다.
        if robot.state == RobotState.STOPPED:
            robot.state = RobotState.IDLE
            robot.wait_start_time = None
            robot.goal_start_time = None
            robot.last_distance_to_goal = None

        self.log_event_to_db('robot_started', robot=robot, command='start')
        self.get_logger().info(
            f'{robot.name} state changed after START: command={robot.driving_command}, '
            f'state={robot.state}, pending={len(self.pending_points)}, has_pose={robot.has_pose()}'
        )

    def requeue_current_goal(self, robot: RobotState):
        goal = robot.current_goal
        if goal is None:
            return

        if any(point.order == goal.order for point in self.pending_points):
            self.get_logger().warn(
                f'{robot.name} current goal #{goal.order} is already in pending_points. '
                'Skip duplicate requeue.'
            )
            self.update_point_status(goal, 'pending')
            return

        self.pending_points.append(goal)
        self.update_point_status(goal, 'pending')
        self.log_event_to_db('goal_requeued_by_stop', robot=robot, point=goal)
        self.get_logger().info(
            f'{robot.name} current goal #{goal.order} returned to pending_points because STOP arrived. '
            f'pending={len(self.pending_points)}'
        )

    def main_loop(self):
        self.warn_if_pose_stale()
        self.update_robot_arrival_and_waiting()
        self.maybe_generate_random_goal()
        self.republish_active_goals()
        self.log_active_goal_status()
        self.dispatch_pending_points()

    def publish_cancel_navigation(self, robot: RobotState):
        if robot.cancel_pub is None:
            self.get_logger().error(
                f'Cannot publish cancel for {robot.name}: cancel publisher is not initialized.'
            )
            return

        robot.cancel_pub.publish(Empty())
        robot.last_cancel_publish_time = time.time()
        self.get_logger().info(
            f'Published cancel_navigation to {robot.name}: topic={robot.cancel_topic}'
        )

    def warn_if_pose_stale(self):
        if self.pose_timeout_sec <= 0.0:
            return

        now = time.time()
        for robot in self.robots.values():
            if robot.latest_pose_recv_time is None:
                continue

            age = now - robot.latest_pose_recv_time
            if age > self.pose_timeout_sec:
                if now - robot.last_status_log_time >= self.status_log_sec:
                    self.get_logger().warn(
                        f'{robot.name} pose is stale: last {age:.1f} sec ago on {robot.pose_topic}. '
                        'Check AMCL and domain bridge.'
                    )
                    robot.last_status_log_time = now

    def update_robot_arrival_and_waiting(self):
        now = time.time()

        for robot in self.robots.values():
            if robot.state == RobotState.NAVIGATING:
                reached, dist = self.goal_distance(robot)
                robot.last_distance_to_goal = dist

                if reached:
                    point = robot.current_goal
                    if point is None:
                        continue

                    robot.completed_goal_count += 1

                    self.update_point_status(point, 'completed', robot)
                    self.log_event_to_db('goal_completed', robot=robot, point=point)

                    self.get_logger().info(
                        f'{robot.name} reached goal #{point.order} '
                        f'within {self.arrival_tolerance:.2f} m. Wait '
                        f'{self.goal_wait_sec:.1f} sec before next dispatch. '
                        f'completed_goal_count={robot.completed_goal_count}'
                    )
                    self.maybe_activate_random_goal_generation()
                    robot.current_goal = None
                    robot.state = RobotState.WAITING
                    robot.wait_start_time = now
                    robot.goal_start_time = None
                    robot.last_distance_to_goal = None

                continue

            if robot.state == RobotState.WAITING:
                if robot.wait_start_time is None:
                    robot.wait_start_time = now

                elapsed = now - robot.wait_start_time
                if elapsed >= self.goal_wait_sec:
                    if robot.driving_command == 'start':
                        robot.state = RobotState.IDLE
                        self.get_logger().info(f'{robot.name} wait finished. Robot is IDLE.')
                    else:
                        robot.state = RobotState.STOPPED
                        self.get_logger().info(
                            f'{robot.name} wait finished, but command is stop. Robot is STOPPED.'
                        )
                    robot.wait_start_time = None

    def maybe_activate_random_goal_generation(self):
        if not self.random_goal_enabled:
            return
        if self.random_goal_generation_started:
            return

        # 조건: wf1, wf2가 각각 최소 1개 goal에 실제 도착해야 한다.
        # 이 goal이 clicked point인지 random point인지는 중요하지 않지만,
        # random은 이 조건 이전에는 생성되지 않으므로 첫 도착은 기존/수동 goal이다.
        if not all(robot.completed_goal_count >= 1 for robot in self.robots.values()):
            return

        self.random_goal_generation_started = True
        self.last_random_goal_time = time.time()
        counts = ', '.join(
            f'{robot.key}:{robot.completed_goal_count}' for robot in self.robots.values()
        )
        self.get_logger().info(
            'Random goal generation activated because every robot reached its first goal. '
            f'completed_goal_counts=({counts}). First random sampling will happen after '
            f'{self.random_goal_period_sec:.1f} sec.'
        )

    def maybe_generate_random_goal(self):
        if not self.random_goal_enabled:
            return

        self.maybe_activate_random_goal_generation()
        if not self.random_goal_generation_started:
            return

        now = time.time()
        if self.last_random_goal_time is None:
            self.last_random_goal_time = now
            return

        if now - self.last_random_goal_time < self.random_goal_period_sec:
            return

        # sampling 시도를 한 번 했으면 성공/실패와 관계없이 다음 30초 주기로 넘긴다.
        # 그렇지 않으면 맵/clearance 조건이 안 맞을 때 0.2초마다 warning이 반복된다.
        self.last_random_goal_time = now

        if self.random_goal_max_pending > 0 and len(self.pending_points) >= self.random_goal_max_pending:
            self.get_logger().warn(
                f'Skip random goal generation: pending_points={len(self.pending_points)} >= '
                f'random_goal_max_pending={self.random_goal_max_pending}'
            )
            return

        if self.latest_map is None:
            self.log_random_goal_wait_reason('No map has been received yet. Waiting for /pinky/map bridge.')
            return

        point = self.sample_random_free_point()
        if point is None:
            self.get_logger().warn(
                'Failed to sample a safe random free-space point. '
                f'clearance={self.random_goal_min_clearance_m:.2f} m, '
                f'max_attempts={self.random_goal_max_attempts}. '
                'Try lowering random_goal_min_clearance_m only if the map is very narrow.'
            )
            return

        self.save_point_to_db(point, status='pending')
        self.log_event_to_db('point_saved', point=point, detail='random free-space point saved')
        self.pending_points.append(point)
        map_age = 0.0 if self.latest_map_recv_time is None else now - self.latest_map_recv_time
        self.get_logger().info(
            f'Saved random free-space point #{point.order} to DB and pending_points: '
            f'x={point.x:.3f}, y={point.y:.3f}, frame={point.frame_id}, '
            f'clearance>={self.random_goal_min_clearance_m:.2f} m, '
            f'map_age={map_age:.1f} sec, pending={len(self.pending_points)}'
        )
        self.dispatch_pending_points()

    def log_random_goal_wait_reason(self, reason: str):
        now = time.time()
        if now - self._last_random_wait_log_time < 5.0:
            return
        self._last_random_wait_log_time = now
        self.get_logger().warn(f'Random goal generation is active, but cannot sample yet: {reason}')

    def sample_random_free_point(self) -> Optional[SavedPoint]:
        map_msg = self.latest_map
        if map_msg is None:
            return None

        width = int(map_msg.info.width)
        height = int(map_msg.info.height)
        resolution = float(map_msg.info.resolution)
        data = map_msg.data

        if width <= 0 or height <= 0 or resolution <= 0.0:
            self.get_logger().warn(
                f'Invalid map metadata: width={width}, height={height}, resolution={resolution}'
            )
            return None

        if len(data) != width * height:
            self.get_logger().warn(
                f'Invalid map data size: data={len(data)}, width*height={width * height}'
            )
            return None

        clearance_cells = int(math.ceil(self.random_goal_min_clearance_m / resolution))
        border_margin = max(self.random_goal_border_margin_cells, clearance_cells)

        min_x = border_margin
        max_x = width - border_margin - 1
        min_y = border_margin
        max_y = height - border_margin - 1

        if min_x > max_x or min_y > max_y:
            self.get_logger().warn(
                'Map is too small for the requested random_goal_min_clearance_m. '
                f'width={width}, height={height}, resolution={resolution:.3f}, '
                f'clearance_cells={clearance_cells}'
            )
            return None

        for _ in range(max(1, self.random_goal_max_attempts)):
            mx = self.random_generator.randint(min_x, max_x)
            my = self.random_generator.randint(min_y, max_y)

            if not self.is_safe_free_cell(map_msg, mx, my, clearance_cells):
                continue

            wx, wy = self.map_cell_to_world(map_msg, mx, my)
            self.point_count += 1
            return SavedPoint(
                x=wx,
                y=wy,
                z=0.0,
                frame_id=self.map_frame,
                order=self.point_count,
                source='random_free_space',
            )

        return None

    def is_safe_free_cell(self, map_msg: OccupancyGrid, mx: int, my: int, clearance_cells: int) -> bool:
        width = int(map_msg.info.width)
        height = int(map_msg.info.height)
        data = map_msg.data

        center_index = my * width + mx
        if not self.is_free_value(data[center_index]):
            return False

        radius_sq = clearance_cells * clearance_cells
        for dy in range(-clearance_cells, clearance_cells + 1):
            yy = my + dy
            if yy < 0 or yy >= height:
                return False

            for dx in range(-clearance_cells, clearance_cells + 1):
                if dx * dx + dy * dy > radius_sq:
                    continue

                xx = mx + dx
                if xx < 0 or xx >= width:
                    return False

                value = data[yy * width + xx]
                if self.is_blocking_value(value):
                    return False

        return True

    def is_free_value(self, value: int) -> bool:
        # OccupancyGrid에서 0은 확실한 free space이다.
        # 1~49 같은 확률 셀은 로봇이 지나갈 수 있다고 볼 수도 있지만,
        # 랜덤 goal은 안전해야 하므로 중심점은 0만 허용한다.
        return int(value) == 0

    def is_blocking_value(self, value: int) -> bool:
        value = int(value)
        if value < 0:
            return self.random_goal_unknown_is_obstacle
        return value >= self.random_goal_occupied_threshold

    def map_cell_to_world(self, map_msg: OccupancyGrid, mx: int, my: int) -> Tuple[float, float]:
        resolution = float(map_msg.info.resolution)
        origin = map_msg.info.origin

        local_x = (mx + 0.5) * resolution
        local_y = (my + 0.5) * resolution

        yaw = self.yaw_from_quaternion(origin.orientation)
        cos_yaw = math.cos(yaw)
        sin_yaw = math.sin(yaw)

        world_x = origin.position.x + local_x * cos_yaw - local_y * sin_yaw
        world_y = origin.position.y + local_x * sin_yaw + local_y * cos_yaw
        return world_x, world_y

    @staticmethod
    def yaw_from_quaternion(q) -> float:
        # geometry_msgs/Quaternion -> yaw
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        return math.atan2(siny_cosp, cosy_cosp)

    def republish_active_goals(self):
        if self.goal_republish_sec <= 0.0:
            return

        now = time.time()
        for robot in self.robots.values():
            if robot.driving_command != 'start':
                continue
            if robot.state != RobotState.NAVIGATING or robot.current_goal is None:
                continue

            if now - robot.last_goal_publish_time >= self.goal_republish_sec:
                self.publish_goal(robot, robot.current_goal)
                dist = robot.last_distance_to_goal
                dist_text = 'unknown' if dist is None else f'{dist:.3f} m'
                self.get_logger().info(
                    f'Republished current goal #{robot.current_goal.order} to {robot.name} '
                    f'on {robot.goal_topic}. distance={dist_text}'
                )

    def log_active_goal_status(self):
        if self.status_log_sec <= 0.0:
            return

        now = time.time()
        for robot in self.robots.values():
            if robot.state != RobotState.NAVIGATING or robot.current_goal is None:
                continue

            if now - robot.last_status_log_time < self.status_log_sec:
                continue

            elapsed = 0.0 if robot.goal_start_time is None else now - robot.goal_start_time
            dist = robot.last_distance_to_goal
            dist_text = 'unknown' if dist is None else f'{dist:.3f} m'
            self.get_logger().info(
                f'{robot.name} still navigating goal #{robot.current_goal.order}: '
                f'distance={dist_text}, elapsed={elapsed:.1f} sec, '
                f'pending={len(self.pending_points)}, command={robot.driving_command}'
            )
            robot.last_status_log_time = now

    def dispatch_pending_points(self):
        if not self.pending_points:
            return

        available_keys = [
            robot.key for robot in self.robots.values()
            if robot.is_available() and (robot.has_pose() or not self.require_pose_before_dispatch)
        ]

        if not available_keys:
            now = time.time()
            if not hasattr(self, '_last_no_available_log_time'):
                self._last_no_available_log_time = 0.0

            if now - self._last_no_available_log_time >= 2.0:
                states = ', '.join(
                    [
                        f'{r.key}:command={r.driving_command},state={r.state},has_pose={r.has_pose()}'
                        for r in self.robots.values()
                    ]
                )
                self.get_logger().info(
                    f'Pending points exist ({len(self.pending_points)}), but no robot is available yet. {states}'
                )
                self._last_no_available_log_time = now
            return

        while self.pending_points:
            if not self.first_goal_dispatched:
                if not self.try_dispatch_first_point_to_wf1():
                    return
                continue

            if not self.try_dispatch_nearest_pending_point_to_nearest_available_robot():
                return

    def try_dispatch_first_point_to_wf1(self) -> bool:
        robot = self.robots['wf1']

        if not robot.is_available():
            return False

        if self.require_pose_before_dispatch and not robot.has_pose():
            self.get_logger().warn(
                'First point must go to Waffle/WF1, but no /wf1/amcl_pose has been received yet. '
                'Waiting for pose bridge...'
            )
            return False

        point = self.pending_points.pop(0)
        self.first_goal_dispatched = True
        self.send_goal(robot, point, reason='first clicked point is forced to Waffle/WF1')
        return True

    def try_dispatch_nearest_pending_point_to_nearest_available_robot(self) -> bool:
        available_robots = [robot for robot in self.robots.values() if robot.is_available()]

        if not available_robots:
            return False

        if self.require_pose_before_dispatch:
            available_robots = [robot for robot in available_robots if robot.has_pose()]

        if not available_robots:
            self.get_logger().warn(
                'There are pending points, but no available robot has AMCL pose yet. '
                'Waiting for pose bridge...'
            )
            return False

        selected_robot = None
        selected_point_index = None
        selected_dist = float('inf')

        for idx, point in enumerate(self.pending_points):
            for robot in available_robots:
                if robot.latest_xy is None:
                    continue

                rx, ry = robot.latest_xy
                dist = math.hypot(point.x - rx, point.y - ry)

                if dist < selected_dist:
                    selected_dist = dist
                    selected_robot = robot
                    selected_point_index = idx

        if selected_robot is None or selected_point_index is None:
            self.get_logger().warn(
                'Cannot select nearest pending point because no robot pose is available.'
            )
            return False

        point = self.pending_points.pop(selected_point_index)
        self.send_goal(
            selected_robot,
            point,
            reason=(
                f'nearest pending point among all pending_points, '
                f'distance={selected_dist:.3f} m'
            ),
        )
        return True

    def send_goal(self, robot: RobotState, point: SavedPoint, reason: str):
        if robot.driving_command != 'start':
            self.get_logger().warn(
                f'Tried to send goal #{point.order} to {robot.name}, '
                f'but command is {robot.driving_command}. Requeue.'
            )
            self.pending_points.append(point)
            self.update_point_status(point, 'pending')
            return

        if robot.goal_pub is None:
            self.get_logger().error(
                f'Cannot send goal #{point.order} to {robot.name}: goal publisher is not initialized.'
            )
            self.pending_points.append(point)
            self.update_point_status(point, 'pending')
            return

        robot.current_goal = point
        robot.state = RobotState.NAVIGATING
        robot.wait_start_time = None
        robot.goal_start_time = time.time()
        robot.last_status_log_time = 0.0
        robot.last_distance_to_goal = None

        self.update_point_status(point, 'navigating', robot)
        self.log_event_to_db('goal_dispatched', robot=robot, point=point, detail=reason)
        self.publish_goal(robot, point)

        self.get_logger().info(
            f'Dispatched goal #{point.order} to {robot.name}: '
            f'x={point.x:.3f}, y={point.y:.3f}, topic={robot.goal_topic}, '
            f'source={point.source}, reason={reason}, pending={len(self.pending_points)}'
        )

    def publish_goal(self, robot: RobotState, point: SavedPoint):
        pose_msg = self.make_pose_stamped(point)
        robot.goal_pub.publish(pose_msg)
        robot.last_goal_publish_time = time.time()

    def goal_distance(self, robot: RobotState) -> Tuple[bool, Optional[float]]:
        if robot.current_goal is None or robot.latest_xy is None:
            return False, None

        rx, ry = robot.latest_xy
        goal = robot.current_goal
        dist = math.hypot(goal.x - rx, goal.y - ry)

        return dist <= self.arrival_tolerance, dist

    def make_pose_stamped(self, point: SavedPoint) -> PoseStamped:
        pose = PoseStamped()
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.header.frame_id = self.map_frame

        pose.pose.position.x = point.x
        pose.pose.position.y = point.y
        pose.pose.position.z = 0.0

        qz = math.sin(self.default_yaw / 2.0)
        qw = math.cos(self.default_yaw / 2.0)

        pose.pose.orientation.x = 0.0
        pose.pose.orientation.y = 0.0
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw

        return pose


def main(args=None):
    rclpy.init(args=args)
    node = MultiRobotPointDispatcher()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    try:
        node.db_conn.close()
    except Exception:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
