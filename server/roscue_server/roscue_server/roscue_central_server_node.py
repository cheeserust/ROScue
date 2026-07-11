# roscue_central_server_node.py
# 역할: 로봇별 FSM 구동, 박스 레지스트리, 폭발물 큐, 중재 알고리즘. 실제 Nav2/YOLO/Imitation 구현은 동료 담당.
# 레이어 구분:
#   [CONTROLLER]  웹/토픽 진입점 — 요청 수신 및 위임만 담당
#   [SERVICE]     중재 알고리즘 + FSM 전이 — 핵심 비즈니스 로직
#   [ROS I/O]     로봇 서비스·액션 호출 래퍼 — 아웃바운드 어댑터

import json
import math
import os
import queue
import signal
import socket as _socket
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, Pose

from roscue_interface.msg import YoloEvent, MainToNavMsg
from roscue_interface.srv import (
    ArmPose, SetYoloMode, TaskCommandSrv
)

# =========================================================
# 설정
# =========================================================
ROS_DOMAIN_ID   = 10                              # 서버 전용 도메인 (코디네이터·게이트웨이 등 서버 내부 노드)
DOMAIN          = {'pinky':13, 'wf1': 14, 'wf2': 15}  # 로봇별 ROS_DOMAIN_ID (브릿지가 서버 도메인과 중계)
ROBOT_IP        = {'wf1': '192.168.0.14', 'wf2': '192.168.0.15'}
OPEN_BOX_PORT   = 9100
CAM_CONTROL_PORT = {'wf1': 5010, 'wf2': 5011}
ROBOT_LIST      = list(DOMAIN)
MANIPULATOR_ROBOTS = ['wf1', 'wf2']  # 협동 해체 가능한 매니퓰레이터 로봇 (pinky는 수동 SLAM 전용)

# 중앙 서버에 꽂힌 리더암 USB 포트 (로봇 순서와 맞춰야 함)
LEADER_PORTS    = {'wf1': '/dev/ttyACM4', 'wf2': '/dev/ttyACM5'}

_ROS_SOURCE = (
    "source /opt/ros/jazzy/setup.bash && "
    "source install/setup.bash"
)

DEBUG_POSE      = 1  # amcl_pose 미수신 시 (0,0) 기본값으로 진행 (디버그 전용)

T_BOX_SCAN          = 20.0   # 스캔 타임아웃 (초)
T_PARTNER       = 120.0  # 파트너 대기 타임아웃 (초)
SUMMON_FINISH_RADIUS    = 0.3    # 박스 중복 제거 반경 (m)
IMITATION_TIMEOUT = 100.0 #모방학습 (로봇 최대 대기 )

class _BoxOpenSession:
    """취소 가능한 소켓 세션. cancel() 호출 시 소켓 close → 로봇 루프에서 감지."""
    def __init__(self):
        self.sock: Optional[_socket.socket] = None
        self._cancelled = False

    def cancel(self):
        self._cancelled = True
        if self.sock:
            try: self.sock.close()
            except Exception: pass


# =========================================================
# 열거형
# =========================================================
class RobotState(Enum):
    IDLE           = 'IDLE'
    EXPLORE        = 'EXPLORE'
    APPROACH       = 'APPROACH'
    OPEN_BOX_COVER = 'OPEN_BOX_COVER'
    BOX_SCAN           = 'BOX_SCAN'
    WAIT_PARTNER   = 'WAIT_PARTNER'
    SUMMON       = 'SUMMON'
    DUAL_MANUAL    = 'DUAL_MANUAL'
    RECOVER        = 'RECOVER'
    YOLO_DEBUG = 'YOLO_DEBUG'

class BoxStatus(Enum):
    DETECTED          = 'DETECTED'
    INSPECTING        = 'INSPECTING'
    CLEAR             = 'CLEAR'
    EXPLOSIVE_PENDING = 'EXPLOSIVE_PENDING'
    HANDLING          = 'HANDLING'
    RESOLVED          = 'RESOLVED'
    OPEN_FAILED       = 'OPEN_FAILED'
    REVISIT           = 'REVISIT'

# =========================================================
# 데이터 모델
# =========================================================
@dataclass
class BoxEntry:
    box_id:        str
    pose:          Dict[str, float]   # {'x': float, 'y': float}
    status:        BoxStatus
    discovered_by: str
    first_stamp:   float              # time.time()

@dataclass
class RobotEntry:
    state:          RobotState = RobotState.IDLE
    pose:           Dict[str, float] = field(default_factory=lambda: {'x': 0.0, 'y': 0.0, 'theta': 0.0})
    last_amcl_pose: Optional[Pose] = None   # amcl_pose 최신 전체 pose (위치+방향) 캐시
    assigned_box:   Optional[str] = None
    summon_target:    Dict[str, float] = field(default_factory=lambda: {'x': 0.0, 'y': 0.0})
    # 진행 중인 액션 goal handle (선점 시 cancel() 호출용)
    open_box_cover_handle:  Optional[object] = None
    # 타이머 handle (cancel 용)
    box_scan_timer:       Optional[object] = None
    partner_timer:    Optional[object] = None
    is_summoned:      bool = False        # DUAL_MANUAL 진입 시 소환된 쪽이면 True


# =========================================================
# 코디네이터 노드
# =========================================================
class RoscueCentralServerNode(Node):

    def __init__(self):
        super().__init__('roscue_central_server')
        self.cb = ReentrantCallbackGroup()

        # 데이터 모델
        self.box_registry:    Dict[str, BoxEntry]  = {}
        self.explosive_queue: List[str]            = []  # box_id 리스트 (first_stamp 오름차순)
        self.robot_table: Dict[str, RobotEntry] = {}
        for r in ROBOT_LIST:
            self.robot_table[r] = RobotEntry()
        self._lock = threading.Lock()

        # 서버 쪽 리더암 프로세스 (DUAL_MANUAL 진입 시 시작, 종료 시 정리)
        self._leader_processs: Dict[str, subprocess.Popen] = {}

        self._init_subscribers()
        self._init_service_servers()
        self._init_publishers()
        self._init_service_clients()

        # 모든 FSM 전이·블로킹 ROS 호출을 단일 워커 스레드에서 직렬 실행한다.
        # executor 스레드에서 직접 client.call() 하면
        #   ① 같은 클라이언트를 여러 스레드가 동시 사용 → sequence_number 충돌로 영구 hang
        #   ② 모든 executor 스레드가 call()에 묶이면 응답 처리할 스레드가 없어 starvation 데드락
        # 워커 1개로 직렬화하면 ①이 원천 차단되고, 블로킹이 워커에만 있어 executor 스레드는
        # 항상 서비스 응답을 처리할 수 있어 ②도 해소된다.
        self._jobs: "queue.Queue" = queue.Queue()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()
        self.get_logger().info('CentralServer 시작. /api/web_command 으로 명령 대기.')

    # ---------------------------------------------------------
    # 초기화 helpers
    # ---------------------------------------------------------

    # Topic
    def _init_subscribers(self):

        # YOLO추론 TOPIC 받아옴 (BOX_FOUND / BOX_COVER_OPEN / EXPLOSIVE_FOUND / EMPTY)
        self.create_subscription(
            YoloEvent, '/yolo/event', self._yolo_event_callback, 10,
            callback_group=self.cb,
        )

        # 로봇 amcl_pose (위치+방향) — pose 단일 소스. 주행팀이 도메인10으로 브릿지 (reliable)
        for robot in MANIPULATOR_ROBOTS:
            self.create_subscription(
                PoseWithCovarianceStamped, f'/{robot}/amcl_pose',
                lambda msg, r=robot: self._amcl_pose_callback(r, msg),
                10,
                callback_group=self.cb,
            )

    # Topic
    def _init_publishers(self):

        # wf2 목표 좌표 전송 (주행팀 구독 해야함)
        self.goal_pose_pubs = {}
        for r in MANIPULATOR_ROBOTS:
            self.goal_pose_pubs[r] = self.create_publisher(PoseStamped, f'/{r}/goal_pose', 10)


        # 주행서버로 메시지 pub
        '''
        string robot_name   # "wf1" | "wf2"
        string command   # "start" | "stop"
        '''
        self.main_to_nav_pub = {}
        for r in ROBOT_LIST:
            self.main_to_nav_pub[r] = self.create_publisher(MainToNavMsg, '/driving_command', 10)

    # Service
    # Flask로부터 명령 받음
    def _init_service_servers(self):
        self.create_service(TaskCommandSrv, '/api/web_command',
                            self._web_command_handler, callback_group=self.cb)

    # ROS로 로봇이나 다른 서버한태 명령 보냄
    def _init_service_clients(self):

        # Service 클라이언트
        self.yolo_mode_client = self.create_client(
            SetYoloMode, '/yolo/set_mode', callback_group=self.cb)
        
        self.task_command_clients = {}
        for r in ROBOT_LIST:
            self.task_command_clients[r] = self.create_client(TaskCommandSrv, f'/{r}/task_command', callback_group=self.cb)

        self.arm_pose_clients = {}
        for r in ROBOT_LIST:
            self.arm_pose_clients[r] = self.create_client(ArmPose, f'/{r}/arm_pose', callback_group=self.cb)

        # 모방학습 open_box_cover 는 TCP 소켓으로 직접 호출 (_send_open_box_cover_goal)

    # =========================================================
    # [CONTROLLER] 웹/토픽 → 중앙서버 진입점
    # =========================================================
    def _web_command_handler(self, req: TaskCommandSrv.Request, res: TaskCommandSrv.Response):
        """서비스 콜백(executor 스레드) — 실제 처리는 워커에서 직렬 실행하고 결과만 기다림."""
        result = self._run_sync(lambda: self._dispatch_web_command(req, res))
        if result is None:
            res.accepted = False
            res.message  = '코디네이터가 다른 작업 처리 중 — 잠시 후 재시도'
            return res
        return result

    def _dispatch_web_command(self, req: TaskCommandSrv.Request, res: TaskCommandSrv.Response):
        """
        Flask /api/command 단일 엔드포인트.

        task_name           action / box_id 예시
        ──────────────────  ──────────────────────────────
        mission             start | stop | pause | resume
        manual_done         box_id 필드 사용
        navigation          start | stop | restart
        robot_omx_manual_control  start | stop
        arm_pose            HOME | CAMERA_VIEW | BOX_VIEW
        yolo_mode           BOX_DETECTION_MODEL | EXPLOSIVE_DETECTION_MODEL | OFF
        """
        task   = req.task_name.strip()
        action = req.action.strip()
        robot  = req.robot_name.strip()
        if not task == 'list_boxes':
            self.get_logger().info(f'web_command: robot={robot} task={task} action={action}')

        if task == 'mission':
            return self._handle_mission(action, res)

        if task == 'manual_done':
            return self._handle_manual_done(req.box_id.strip(), res)

        DIRECT_COMMAND_LIST = {'robot_arm_pose_server'}

        if task in DIRECT_COMMAND_LIST:
            ok, msg = self._call_task_command(robot, task, action.lower())
            res.accepted = ok
            res.message  = msg

        elif task == 'robot_omx_manual_control':
            if action.lower() == 'start':
                self._call_task_command(robot, 'robot_arm_pose_server', 'stop')
                ok, msg = self._call_task_command(robot, 'robot_omx_manual_control', 'start')
                if ok:
                    self._start_leader_arm(robot)
            elif action.lower() == 'stop':
                ok, msg = self._call_task_command(robot, 'robot_omx_manual_control', 'stop')
                self._stop_leader_arm(robot)
            else:
                ok, msg = False, f'지원하지 않는 action: {action}'
            res.accepted = ok
            res.message  = msg

        elif task == 'arm_pose':
            self._call_arm_pose(robot, action.upper())
            res.accepted = True
            res.message  = f'arm_pose → {action.upper()}'

        elif task == 'yolo_mode':
            self._call_set_yolo_mode(robot, 'wrist_cam', action.upper())
            res.accepted = True
            res.message  = f'yolo_mode → {action.upper()}'

        elif task == 'debug_yolo':
            return self._handle_debug_yolo(robot, res)

        elif task == 'debug_idle':
            return self._handle_debug_idle(robot, res)

        elif task == 'debug_explore':
            return self._handle_debug_explore(robot, res)

        elif task == 'debug_recover':
            return self._handle_debug_recover(robot, res)

        elif task == 'debug_pinky_task':
            return self._handle_debug_pinky_task(robot, res)

        elif task == 'debug_approach':
            return self._handle_debug_approach(robot, req.box_id.strip(), res)

        elif task == 'debug_open_box_cover':
            return self._handle_debug_open_box_cover(robot, req.box_id.strip(), res)

        elif task == 'debug_box_scan':
            return self._handle_debug_box_scan(robot, req.box_id.strip(), res)

        elif task == 'debug_wait_partner':
            return self._handle_debug_wait_partner(robot, req.box_id.strip(), res)

        elif task == 'debug_summon':
            return self._handle_debug_summon(robot, req.box_id.strip(), res)

        elif task == 'debug_dual_manual':
            return self._handle_debug_dual_manual(robot, req.box_id.strip(), res)

        elif task == 'debug_arrived':
            return self._handle_debug_arrived(robot, res)

        elif task == 'debug_explosive_found':
            return self._handle_debug_explosive_found(robot, res)

        elif task == 'debug_add_box':
            return self._handle_debug_add_box(robot, req.box_id.strip(), res)

        elif task == 'debug_remove_box':
            return self._handle_debug_remove_box(req.box_id.strip(), res)

        elif task == 'debug_reset_boxes':
            return self._handle_debug_reset_boxes(res)

        elif task == 'list_boxes':
            with self._lock:
                payload = [
                    {'box_id': e.box_id, 'pose': e.pose,
                     'status': e.status.name,
                     'discovered_by': e.discovered_by,
                     'first_stamp': e.first_stamp}
                    for e in self.box_registry.values()
                ]
            res.accepted = True
            res.message  = json.dumps(payload)

        else:
            res.accepted = False
            res.message  = f'지원하지 않는 task: {task}'

        return res

    def _handle_mission(self, action: str, res: TaskCommandSrv.Response):
        action = action.lower()
        if action == 'start':
            # pinky는 수동 SLAM 전용 — 미션(탐색·박스 처리)은 매니퓰레이터 로봇만
            for robot in MANIPULATOR_ROBOTS:
                if self.robot_table[robot].state == RobotState.IDLE:
                    print(f'{robot} 자율주행 시작 명령 받음')
                    # 각 로봇을 별도 워커 잡으로 → 빠른 응답 + 병렬 시작
                    self._run_async(lambda r=robot: self._transition_to_self_driving(r))
            res.accepted = True
            res.message  = '미션 시작'
        elif action == 'stop':
            for robot in MANIPULATOR_ROBOTS:
                if self.robot_table[robot].state != RobotState.IDLE:
                    self._transition_to_idle(robot)
            res.accepted = True
            res.message  = '미션 정지'
        elif action in ('pause', 'resume'):
            res.accepted = False
            res.message  = f'{action} 미구현'
        else:
            res.accepted = False
            res.message  = f'지원하지 않는 action: {action}'
        return res

    def _handle_manual_done(self, box_id: str, res: TaskCommandSrv.Response):
        """관리자가 수동 처리 완료 버튼 클릭."""

        with self._lock:
            if box_id not in self.box_registry:
                res.accepted = False
                res.message  = f'알 수 없는 box_id: {box_id}'
                return res
            del self.box_registry[box_id]
            if box_id in self.explosive_queue:
                self.explosive_queue.remove(box_id)
            next_box  = self.explosive_queue[0] if self.explosive_queue else None
            dual_bots = [r for r in ROBOT_LIST
                         if self.robot_table[r].state == RobotState.DUAL_MANUAL]

        self.get_logger().info(f'MANUAL_DONE: box={box_id} → RESOLVED, 큐 남음={next_box}')

        for r in dual_bots:
            self._call_task_command(r, 'robot_omx_manual_control', 'stop')
            self._stop_leader_arm(r)

        if next_box:
            # discoverer 먼저 출발, partner는 IDLE 대기 (discoverer 도착 후 자동 소환)
            box_entry = self.box_registry[next_box]
            discoverer = box_entry.discovered_by
            if discoverer not in dual_bots:
                discoverer = dual_bots[0]
            partner = next(r for r in dual_bots if r != discoverer)
            self.get_logger().info(
                f'큐에 폭발물 남음: {next_box} → {discoverer} 먼저 출발, {partner} 대기')
            with self._lock:
                self.robot_table[partner].state = RobotState.IDLE
            self._transition_to_summon(discoverer, box_entry.pose['x'], box_entry.pose['y'])
        else:
            self.get_logger().info('잔여 폭발물 없음 → 두 로봇 EXPLORE 복귀')
            for r in dual_bots:
                self._transition_to_self_driving(r)

        res.accepted = True
        res.message  = f'box {box_id} 처리 완료'
        return res

    # ---------------------------------------------------------
    # 디버그 핸들러 (web debug_* task 전용)
    # ---------------------------------------------------------

    def _handle_debug_yolo(self, robot: str, res: TaskCommandSrv.Response):
        self._transition_to_yolo_debug(robot)
        res.accepted = True
        res.message  = f'[{robot}] debug: → YOLO_DEBUG'
        return res

    def _handle_debug_idle(self, robot: str, res: TaskCommandSrv.Response):
        self._transition_to_idle(robot)
        res.accepted = True
        res.message  = f'[{robot}] debug: → IDLE'
        return res

    def _handle_debug_explore(self, robot: str, res: TaskCommandSrv.Response):
        self._transition_to_self_driving(robot)
        res.accepted = True
        res.message  = f'[{robot}] debug: → EXPLORE'
        return res

    def _handle_debug_recover(self, robot: str, res: TaskCommandSrv.Response):
        with self._lock:
            self.robot_table[robot].state = RobotState.RECOVER
        res.accepted = True
        res.message  = f'[{robot}] debug: → RECOVER'
        return res

    def _handle_debug_pinky_task(self, robot: str, res: TaskCommandSrv.Response):
        res.accepted = True
        res.message  = f'[{robot}] debug: → PINKY_TASK'
        return res

    def _handle_debug_approach(self, robot: str, box_id: str, res: TaskCommandSrv.Response):
        if not box_id:
            res.accepted = False
            res.message  = 'box_id 필요'
            return res
        self._transition_to_approach(robot, box_id)
        res.accepted = True
        res.message  = f'[{robot}] debug: → APPROACH (box={box_id})'
        return res

    def _handle_debug_wait_partner(self, robot: str, box_id: str, res: TaskCommandSrv.Response):
        if not box_id:
            res.accepted = False
            res.message  = 'box_id 필요'
            return res
        self._transition_to_wait_partner(robot, box_id)
        res.accepted = True
        res.message  = f'[{robot}] debug: → WAIT_PARTNER (box={box_id})'
        return res

    def _handle_debug_summon(self, robot: str, coord_str: str, res: TaskCommandSrv.Response):
        try:
            x, y = map(float, coord_str.split(','))
        except Exception:
            res.accepted = False
            res.message  = 'box_id 필드에 "x,y" 형식으로 좌표 입력'
            return res
        self._transition_to_summon(robot, x, y)
        res.accepted = True
        res.message  = f'[{robot}] debug: → SUMMON ({x:.2f}, {y:.2f})'
        return res

    def _handle_debug_dual_manual(self, robot: str, robot2: str, res: TaskCommandSrv.Response):
        if not robot2:
            res.accepted = False
            res.message  = 'robot2 이름 필요'
            return res
        self._transition_to_dual_manual_control(robot, robot2)
        res.accepted = True
        res.message  = f'debug: → DUAL_MANUAL ({robot}, {robot2})'
        return res

    def _handle_debug_arrived(self, robot: str, res: TaskCommandSrv.Response):
        self._handle_box_arrived(robot)
        res.accepted = True
        res.message  = f'[{robot}] debug: _handle_box_arrived 실행'
        return res

    def _handle_debug_explosive_found(self, robot: str, res: TaskCommandSrv.Response):
        self._handle_explosive_found(robot)
        res.accepted = True
        res.message  = f'[{robot}] debug: _handle_explosive_found 실행'
        return res

    def _handle_debug_open_box_cover(self, robot: str, box_id: str, res: TaskCommandSrv.Response):
        if not box_id:
            res.accepted = False
            res.message  = 'box_id 필요'
            return res
        self._transition_to_open_box_cover(robot, box_id)
        res.accepted = True
        res.message  = f'[{robot}] debug: _transition_to_open_box_cover 실행 (box={box_id})'
        return res
    
    def _handle_debug_box_scan(self, robot: str, box_id: str, res: TaskCommandSrv.Response):
        if not box_id:
            res.accepted = False
            res.message  = 'box_id 필요'
            return res
        self._transition_to_box_scan(robot, box_id)
        res.accepted = True
        res.message  = f'[{robot}] debug: _transition_to_box_scan 실행 (box={box_id})'
        return res

    def _handle_debug_add_box(self, robot: str, arg: str, res: TaskCommandSrv.Response):
        """박스를 레지스트리에 수동 추가 (디버그).
        box_id 필드 형식:
          ""                       → id 자동생성, 좌표는 로봇 현재 pose
          "<box_id>"               → 좌표는 로봇 현재 pose
          "<box_id>,<x>,<y>"       → 좌표 지정
          ",<x>,<y>"               → id 자동생성, 좌표 지정
        """
        parts  = [p.strip() for p in arg.split(',')] if arg else []
        box_id = parts[0] if parts and parts[0] else str(uuid.uuid4())[:4]
        with self._lock:
            if len(parts) >= 3 and parts[1] and parts[2]:
                try:
                    x, y = float(parts[1]), float(parts[2])
                except ValueError:
                    res.accepted = False
                    res.message  = 'box_id 필드 형식: "<box_id>" 또는 "<box_id>,<x>,<y>"'
                    return res
            else:
                rp = self.robot_table[robot].pose
                x, y = rp['x'], rp['y']
            if box_id in self.box_registry:
                res.accepted = False
                res.message  = f'이미 존재하는 box_id: {box_id}'
                return res
            self.box_registry[box_id] = BoxEntry(
                box_id=box_id,
                pose={'x': x, 'y': y},
                status=BoxStatus.DETECTED,
                discovered_by=robot,
                first_stamp=time.time(),
            )
        self.get_logger().info(f'[debug] 박스 수동 추가: {box_id} @ ({x:.2f}, {y:.2f})')
        res.accepted = True
        res.message  = f'박스 추가됨: {box_id} @ ({x:.2f}, {y:.2f})'
        return res

    def _handle_debug_remove_box(self, box_id: str, res: TaskCommandSrv.Response):
        """레지스트리에서 박스 1개 삭제 (디버그). box_id 필드 사용."""
        if not box_id:
            res.accepted = False
            res.message  = 'box_id 필요'
            return res
        with self._lock:
            if box_id not in self.box_registry:
                res.accepted = False
                res.message  = f'존재하지 않는 box_id: {box_id}'
                return res
            del self.box_registry[box_id]
            if box_id in self.explosive_queue:
                self.explosive_queue.remove(box_id)
            for entry in self.robot_table.values():
                if entry.assigned_box == box_id:
                    entry.assigned_box = None
        self.get_logger().info(f'[debug] 박스 삭제: {box_id}')
        res.accepted = True
        res.message  = f'박스 삭제됨: {box_id}'
        return res

    def _handle_debug_reset_boxes(self, res: TaskCommandSrv.Response):
        """박스 레지스트리·폭발물 큐 전체 초기화 (디버그)."""
        with self._lock:
            n = len(self.box_registry)
            self.box_registry.clear()
            self.explosive_queue.clear()
            for entry in self.robot_table.values():
                entry.assigned_box = None
        self.get_logger().info(f'[debug] 박스 레지스트리 초기화 ({n}개 삭제)')
        res.accepted = True
        res.message  = f'박스 {n}개 전체 삭제됨'
        return res

    def _yolo_event_callback(self, msg: YoloEvent):
        # 콜백은 즉시 반환하고, 블로킹 전이는 워커에서 직렬 실행 (state는 워커에서 재확인)
        self._run_async(lambda r=msg.robot_name, e=msg.event_type: self._on_yolo_event(r, e))

    def _on_yolo_event(self, robot: str, event: str):
        with self._lock:
            state = self.robot_table[robot].state

        self.get_logger().info(
            f'YOLO 이벤트: [{robot}/{state.value}] {event}'
        )
        # 디버그 #########################
        if state == RobotState.YOLO_DEBUG:
            if event == 'BOX_FOUND':
                self.get_logger().info(f'[debug] 박스 찾음')
            if event == 'ARRIVED':
                self.get_logger().info(f'[debug] 도착함')
            if event in ('EMPTY', 'BOX_COVER_OPEN'):
                self.get_logger().info(f'[debug] {event} ')
        # 디버그 끝 ###########################

        if event == 'BOX_FOUND' and state == RobotState.EXPLORE:
            self._handle_box_found(robot)

        elif event == 'ARRIVED' and state == RobotState.APPROACH:
            self._handle_box_arrived(robot)

        elif event == 'ARRIVED' and state == RobotState.EXPLORE:
            # 박스가 처음부터 가까워서 BOX_FOUND 없이 바로 ARRIVED가 오는 경우
            self._handle_arrived_without_box_found(robot)

        elif event == 'EXPLOSIVE_FOUND' and state == RobotState.BOX_SCAN:
            self._handle_explosive_found(robot)

        # BOX_SCAN에서는 EXPLOSIVE 모델이 '열린 뚜껑(open)'을 계속 BOX_COVER_OPEN으로 보고하므로
        # 그것으로 스캔을 끝내면 안 된다. EMPTY(빈 박스 확정)일 때만 CLEAR.
        # 결론이 안 나면 T_BOX_SCAN 타임아웃이 CLEAR 처리한다.
        elif event == 'EMPTY' and state == RobotState.BOX_SCAN:
            with self._lock:
                box_id = self.robot_table[robot].assigned_box
                if box_id:
                    self.box_registry[box_id].status = BoxStatus.CLEAR
            self._cancel_timers(robot)
            self.get_logger().info(f'[{robot}] {event} → CLEAR (box={box_id})')
            self._call_arm_pose(robot, 'HOME')
            self._transition_to_self_driving(robot)

    def _amcl_pose_callback(self, robot: str, msg: PoseWithCovarianceStamped):
        """amcl_pose → pose 단일 소스. 전체 pose 캐시 + (x,y,theta) 갱신 + SUMMON 도착 판정."""
        p = msg.pose.pose
        q = p.orientation
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        theta = math.atan2(siny_cosp, cosy_cosp)
        arrived = False
        with self._lock:
            entry = self.robot_table[robot]
            entry.last_amcl_pose = p
            entry.pose = {'x': p.position.x, 'y': p.position.y, 'theta': theta}
            # SUMMON: 목표 좌표 근접 시 도착 처리
            if entry.state == RobotState.SUMMON:
                dx = entry.summon_target['x'] - p.position.x
                dy = entry.summon_target['y'] - p.position.y
                if math.sqrt(dx*dx + dy*dy) < SUMMON_FINISH_RADIUS:
                    arrived = True
                    entry.state = RobotState.IDLE
        if arrived:
            self._run_async(lambda: self._handle_robot_arrived(robot))

    def _worker_loop(self):
        """단일 워커 스레드 — 큐에 쌓인 FSM 작업을 직렬로 실행. 블로킹 client.call()은 전부 여기서만."""
        while True:
            job = self._jobs.get()
            try:
                job()
            except Exception as e:
                self.get_logger().error(f'worker 작업 오류: {e}')

    def _run_async(self, fn):
        """콜백 컨텍스트(executor·데몬 스레드)에서 FSM 작업을 워커로 넘기고 즉시 반환."""
        self._jobs.put(fn)

    def _run_sync(self, fn, timeout_sec: float = 30.0):
        """워커에서 fn을 실행하고 결과를 기다림 (웹 응답용).

        블로킹은 워커에서 일어나므로 다른 executor 스레드는 서비스 응답 처리에 자유롭다.
        timeout 초과 시 None 반환(작업 자체는 워커 큐에 남아 계속 실행됨).
        """
        box: Dict[str, object] = {}
        done = threading.Event()

        def job():
            try:
                box['result'] = fn()
            except Exception as e:
                box['error'] = e
            finally:
                done.set()

        self._jobs.put(job)
        if not done.wait(timeout_sec):
            return None
        if 'error' in box:
            raise box['error']
        return box.get('result')

    # =========================================================
    # [SERVICE] 중재 알고리즘 + FSM 전이
    # =========================================================
    
    def _handle_box_found(self, robot: str):
        """BOX_FOUND 되면 실행 -> 이후 APPROACH"""
        if robot not in MANIPULATOR_ROBOTS:
            self.get_logger().info(f'[{robot}] 박스 발견 — 매니퓰레이터 없음 → 무시')
            return

        with self._lock:
            robot_pose = self.robot_table[robot].pose
            target_box_id = None
            is_new = False
            for entry in self.box_registry.values():
                dx = entry.pose['x'] - robot_pose['x']
                dy = entry.pose['y'] - robot_pose['y']
                if math.sqrt(dx * dx + dy * dy) < SUMMON_FINISH_RADIUS:
                    if entry.status in (BoxStatus.CLEAR, BoxStatus.RESOLVED):
                        self.get_logger().debug(f'[{robot}] 이미 처리된 박스 재검출 → 무시')
                        return
                    target_box_id = entry.box_id
                    break
            if target_box_id is None:
                target_box_id = str(uuid.uuid4())[:4]
                is_new = True
                self.box_registry[target_box_id] = BoxEntry(
                    box_id=target_box_id,
                    pose={'x': robot_pose['x'], 'y': robot_pose['y']},
                    status=BoxStatus.DETECTED,
                    discovered_by=robot,
                    first_stamp=time.time(),
                )

        if is_new:
            self.get_logger().info(f'새 박스 등록: {target_box_id}')
        self._cancel_actions(robot)
        self._transition_to_approach(robot, target_box_id)

    def _handle_arrived_without_box_found(self, robot: str):
        """박스가 처음부터 가까워서 BOX_FOUND 없이 바로 ARRIVED가 온 경우 — 박스 등록 후 도착 처리."""
        if robot not in MANIPULATOR_ROBOTS:
            return

        with self._lock:
            robot_pose = self.robot_table[robot].pose
            target_box_id = None
            for entry in self.box_registry.values():
                dx = entry.pose['x'] - robot_pose['x']
                dy = entry.pose['y'] - robot_pose['y']
                if math.sqrt(dx * dx + dy * dy) < SUMMON_FINISH_RADIUS:
                    if entry.status in (BoxStatus.CLEAR, BoxStatus.RESOLVED):
                        self.get_logger().debug(f'[{robot}] 이미 처리된 박스 재검출 → 무시')
                        return
                    target_box_id = entry.box_id
                    break
            if target_box_id is None:
                target_box_id = str(uuid.uuid4())[:4]
                self.box_registry[target_box_id] = BoxEntry(
                    box_id=target_box_id,
                    pose={'x': robot_pose['x'], 'y': robot_pose['y']},
                    status=BoxStatus.DETECTED,
                    discovered_by=robot,
                    first_stamp=time.time(),
                )
                self.get_logger().info(f'[{robot}] ARRIVED 선착 — 새 박스 등록: {target_box_id}')
            self.robot_table[robot].state = RobotState.APPROACH
            self.robot_table[robot].assigned_box = target_box_id

        self._handle_box_arrived(robot)

    # YOLO 후 박스 위치까지 이동 완료
    def _handle_box_arrived(self, robot: str):
        """박스 도착 완료 → 도착 시점 로봇 pose(amcl)로 박스 위치 고정 + INSPECTING."""
        self._call_set_yolo_mode(robot, 'wrist_cam', 'OFF')
        
        print("박스 도착 완료")
        with self._lock:
            entry  = self.robot_table[robot]
            box_id = entry.assigned_box
            if not box_id:
                return
            
            # 박스 위치를 현재 로봇 좌표로 수정
            self.box_registry[box_id].pose   = {'x': entry.pose['x'], 'y': entry.pose['y']}
            self.box_registry[box_id].status = BoxStatus.INSPECTING

        box_pose = self.box_registry[box_id].pose
        self.get_logger().info(
            f"[{robot}] 박스 도착, 위치 고정: ({box_pose['x']:.2f}, {box_pose['y']:.2f})"
        )
        self._transition_to_open_box_cover(robot, box_id)

    # 
    def _handle_explosive_found(self, robot: str):
        """
        EXPLOSIVE 이벤트 처리
          1. 박스 큐에 추가 (first_stamp 오름차순)
          2. 발견 로봇 → WAIT_PARTNER
          3. 파트너 SUMMON
        """
        self._call_set_yolo_mode(robot, 'wrist_cam', 'OFF')
        with self._lock:
            box_id = self.robot_table[robot].assigned_box
            if not box_id:
                pass
            self.box_registry[box_id].status = BoxStatus.EXPLOSIVE_PENDING
            if box_id not in self.explosive_queue:
                self.explosive_queue.append(box_id)
                self.explosive_queue.sort(
                    key=lambda bid: self.box_registry[bid].first_stamp
                )
            active_box = self.explosive_queue[0]

        self.get_logger().info(
            f'폭발물 발견! robot={robot}, box={box_id}, queue={self.explosive_queue}'
        )
        self._cancel_timers(robot)
        self._transition_to_wait_partner(robot, box_id)

        # 발견 로봇의 실제 pose(위치+방향)를 그대로 파트너 목표로 전달
        with self._lock:
            discoverer = self.box_registry[active_box].discovered_by
            partner    = next(r for r in MANIPULATOR_ROBOTS if r != discoverer)
            discoverer_pose  = self.robot_table[discoverer].last_amcl_pose   # geometry_msgs/Pose | None
        if discoverer_pose is None:
            if DEBUG_POSE:
                discoverer_pose = Pose()
                discoverer_pose.orientation.w = 1.0   # 유효 쿼터니언 (yaw=0)
                self.get_logger().warning(
                    f'[{discoverer}] amcl_pose 미수신 — DEBUG_POSE: 기본 pose(0,0) 사용')
            else:
                self.get_logger().error(f'[{discoverer}] amcl_pose 미수신 — 파트너 소환 보류')
                return
        self._transition_to_summon(
            partner, discoverer_pose.position.x, discoverer_pose.position.y, discoverer_pose.orientation)

    def _handle_robot_arrived(self, robot: str):
        """소환된 로봇이 도착 → WAIT_PARTNER 로봇 있으면 DUAL_MANUAL"""
        with self._lock:
            active_box = self.explosive_queue[0] if self.explosive_queue else None
        if not active_box:
            return

        with self._lock:
            waiting_robot = next(
                (r for r in MANIPULATOR_ROBOTS
                 if self.robot_table[r].state == RobotState.WAIT_PARTNER),
                None
            )
            if waiting_robot:
                pt = self.robot_table[waiting_robot].partner_timer
                if pt:
                    pt.cancel()
                    self.robot_table[waiting_robot].partner_timer = None

        if waiting_robot:
            self._transition_to_dual_manual_control(waiting_robot, robot, box_id=active_box or '')
        else:
            # 첫 도착: 자신 WAIT_PARTNER + IDLE 상태 파트너 자동 출발
            self._transition_to_wait_partner(robot, active_box)
            partner = next((r for r in MANIPULATOR_ROBOTS if r != robot), None)
            if partner:
                with self._lock:
                    partner_state = self.robot_table[partner].state
                if partner_state == RobotState.IDLE:
                    box_entry = self.box_registry[active_box]
                    self._transition_to_summon(
                        partner, box_entry.pose['x'], box_entry.pose['y'])

    # ---------------------------------------------------------
    # FSM 전이
    # ---------------------------------------------------------

    def _transition_to_idle(self, robot: str):
        self.get_logger().info(f'[{robot}] → IDLE')
        self._cancel_actions(robot)
        if robot in MANIPULATOR_ROBOTS:
            self._cancel_timers(robot)
            self._publish_driving_command(robot, 'stop')
            print(f'{robot} 주행서버로 stop 보냄')
            self._call_task_command(robot, 'robot_omx_manual_control', 'stop')
            self._call_set_yolo_mode(robot, 'wrist_cam', 'OFF')
            self._call_task_command(robot, 'robot_arm_pose_server', 'start')
            self._call_arm_pose(robot, 'HOME') # 팔 모터 토크 끔
            self._call_task_command(robot, 'robot_arm_pose_server', 'stop')
            self._stop_leader_arm(robot)
            self._publish_driving_command(robot, 'stop')
        with self._lock:
            self.robot_table[robot].state = RobotState.IDLE
            self.robot_table[robot].assigned_box = None
            self.robot_table[robot].is_summoned = False
    
    def _transition_to_yolo_debug(self, robot: str):
        self.get_logger().info(f'[{robot}] → yolo debug')
        self._cancel_timers(robot)

        # start 후 서버 기동까지 대기 필요 → 기본 30s 타임아웃 사용
        self._call_task_command(robot, 'robot_arm_pose_server', 'start')
        self._call_arm_pose(robot, 'CAMERA_VIEW')

        # yolo 시작
        self._call_set_yolo_mode(robot, 'wrist_cam', 'BOX_DETECTION_MODEL')

        with self._lock:
            self.robot_table[robot].state = RobotState.YOLO_DEBUG
            self.robot_table[robot].assigned_box = None


    # 자율주행 시작, 주행 서버로 명령 보내기
    def _transition_to_self_driving(self, robot: str):
        self.get_logger().info(f'[{robot}] → EXPLORE')

        # 와플 아니면 기본상태로
        if robot not in MANIPULATOR_ROBOTS:
            self._transition_to_idle(robot)
            return

        # DUAL_MANUAL 도중 FSM이 선점하는 경우 수동 제어 정리
        with self._lock:
            was_manual = self.robot_table[robot].state == RobotState.DUAL_MANUAL
        if was_manual:
            self._call_task_command(robot, 'robot_omx_manual_control', 'stop')
            self._stop_leader_arm(robot)

        self._cancel_timers(robot)

        # state를 먼저 EXPLORE로 변경해야 BOX_FOUND 이벤트를 놓치지 않음
        with self._lock:
            self.robot_table[robot].state = RobotState.EXPLORE
            self.robot_table[robot].assigned_box = None

        self._publish_driving_command(robot, 'start')
        

        # 이전 모드 결과 flush — OFF 후 BOX_DETECTION_MODEL 전환
        self._call_set_yolo_mode(robot, 'wrist_cam', 'OFF')

        # 카메라 앞을 바라보게해서 욜로 실행
        self._call_task_command(robot, 'robot_arm_pose_server', 'start')
        self._call_arm_pose(robot, 'CAMERA_VIEW')

        # 욜로 실행
        self._call_set_yolo_mode(robot, 'wrist_cam', 'BOX_DETECTION_MODEL')
        
    # 욜로에서 찾아서, 박스로 다가가기
    def _transition_to_approach(self, robot: str, box_id: str):
        self._publish_driving_command(robot, 'stop')
        print("주행서버로 멈춤 명령 보냄")
        self.get_logger().info(f'[{robot}] → APPROACH (box={box_id})')
        with self._lock:
            self.robot_table[robot].state = RobotState.APPROACH
            self.robot_table[robot].assigned_box = box_id
        # 이동은 YOLO inference gateway에서 담당

    def _transition_to_open_box_cover(self, robot: str, box_id: str):
        self.get_logger().info(f'[{robot}] → OPEN_BOX_COVER (box={box_id})')
        self._call_arm_pose(robot, 'HOME')
        self._call_task_command(robot, 'robot_arm_pose_server', 'stop')
        self._call_set_yolo_mode(robot, 'wrist_cam', 'OFF')
        with self._lock:
            self.robot_table[robot].state = RobotState.OPEN_BOX_COVER
        self._send_open_box_cover_goal(robot, box_id)

    def _transition_to_box_scan(self, robot: str, box_id: str):
        self.get_logger().info(f'[{robot}] → BOX_SCAN (box={box_id})')
        # 모방학습 직후 robot_arm_pose_server를 막 start했으므로 기동(~11s)까지 대기 필요 → 기본 30s 타임아웃 사용.
        self._call_arm_pose(robot, 'BOX_VIEW')
        self._call_set_yolo_mode(robot, 'wrist_cam', 'EXPLOSIVE_DETECTION_MODEL')
        print("폭발물 찾기 ai 모드로 변경")
        with self._lock:
            self.robot_table[robot].state = RobotState.BOX_SCAN
        timer = self.create_timer(T_BOX_SCAN, lambda r=robot, b=box_id: self._on_box_scan_timeout(r, b))
        with self._lock:
            self.robot_table[robot].box_scan_timer = timer

    def _on_box_scan_timeout(self, robot: str, box_id: str):
        self._run_async(lambda: self._box_scan_timeout_job(robot, box_id))

    def _box_scan_timeout_job(self, robot: str, box_id: str):
        with self._lock:
            if self.robot_table[robot].state != RobotState.BOX_SCAN:
                return
            self.robot_table[robot].box_scan_timer.cancel()
            self.robot_table[robot].box_scan_timer = None
            self.box_registry[box_id].status = BoxStatus.CLEAR
        self.get_logger().info(f'[{robot}] BOX_SCAN 타임아웃 → CLEAR (box={box_id})')
        self._call_arm_pose(robot, 'HOME')
        self._transition_to_self_driving(robot)

    def _transition_to_wait_partner(self, robot: str, box_id: str):
        self.get_logger().info(f'[{robot}] → WAIT_PARTNER (box={box_id})')
        self._call_set_yolo_mode(robot, 'wrist_cam', 'OFF')
        timer = self.create_timer(T_PARTNER, lambda r=robot: self._on_partner_timeout(r))
        with self._lock:
            self.robot_table[robot].state = RobotState.WAIT_PARTNER
            self.robot_table[robot].partner_timer = timer

    def _on_partner_timeout(self, robot: str):
        self._run_async(lambda: self._partner_timeout_job(robot))

    def _partner_timeout_job(self, robot: str):
        with self._lock:
            if self.robot_table[robot].state != RobotState.WAIT_PARTNER:
                return
            self.robot_table[robot].partner_timer.cancel()
            self.robot_table[robot].partner_timer = None
        self.get_logger().error(f'[{robot}] 파트너 대기 타임아웃 → IDLE')
        self._transition_to_idle(robot)

    def _transition_to_summon(self, robot: str, target_x: float, target_y: float, orientation=None):
        self.get_logger().info(f'[{robot}] → SUMMON → ({target_x:.2f}, {target_y:.2f})')
        self._cancel_actions(robot)
        self._cancel_timers(robot)
        self._publish_driving_command(robot, 'stop')
        with self._lock:
            self.robot_table[robot].state = RobotState.SUMMON
            self.robot_table[robot].summon_target = {'x': target_x, 'y': target_y}
            self.robot_table[robot].is_summoned = True
        # goal_pose를 먼저 보내 로봇이 즉시 이동 시작하도록 함
        # _call_arm_pose는 블로킹(최대 30s)이므로 이후에 실행해 goal_pose 지연을 방지
        msg = PoseStamped()
        msg.header.frame_id = 'map'
        msg.pose.position.x = target_x
        msg.pose.position.y = target_y
        msg.pose.position.z = 0.0
        if orientation is not None:
            msg.pose.orientation = orientation   # 발견 로봇의 방향(쿼터니언) 그대로 전달
        else:
            msg.pose.orientation.w = 1.0          # yaw=0
        self.goal_pose_pubs[robot].publish(msg)
        # 이후 _amcl_pose_callback 에서 summon_target 거리 체크 후 SUMMON_FINISH_RADIUS가 0.5m 이내면 다음단계
        self._call_arm_pose(robot, 'HOME')   # 이동 중 팔 정리 (블로킹이지만 goal은 이미 전송됨)
        

    def _transition_to_dual_manual_control(self, robot1: str, robot2: str, box_id: str = ''):
        self.get_logger().info(f'→ DUAL_MANUAL ({robot1}, {robot2}) box={box_id!r}')

        # 로봇 동시에 조정 가능하게 2개한테 보냄
        for r in (robot1, robot2):
            pose = 'CAMERA_VIEW' if self.robot_table[r].is_summoned else 'HOME'
            self._call_arm_pose(r, pose)
            self._call_task_command(r, 'robot_arm_pose_server', 'stop')
            ok, msg = self._call_task_command(r, 'robot_omx_manual_control', 'start')
            self.get_logger().info(f'[{r}] follower 시작: {msg}')
            self._start_leader_arm(r)
            with self._lock:
                self.robot_table[r].state = RobotState.DUAL_MANUAL
                self.robot_table[r].assigned_box = box_id or None

    # =========================================================
    # [ROS I/O] 로봇 서비스 / 액션 호출 래퍼
    # =========================================================

    def _call_task_command(self, robot: str, task: str, action: str, timeout_sec: float = 5.0) -> tuple:
        """/{robot}/task_command 서비스 호출 (동기). 반환: (accepted, message)"""
        client = self.task_command_clients[robot]
        if not client.wait_for_service(timeout_sec=2.0):
            self.get_logger().warning(f'[{robot}] task_command 서비스 없음')
            return False, 'service unavailable'
        req = TaskCommandSrv.Request()
        req.robot_name = robot
        req.task_name  = task
        req.action     = action
        res = client.call(req, timeout_sec=timeout_sec)
        if res is None:
            self.get_logger().warning(f'[{robot}] task_command {task}/{action} 타임아웃 ({timeout_sec}s)')
            return False, 'timeout'
        self.get_logger().debug(f'[{robot}] task_command {task}/{action} → {res.message}')
        return res.accepted, res.message

    def _publish_driving_command(self, robot: str, command: str):
        msg = MainToNavMsg()
        msg.robot_name = robot
        msg.command = command
        self.main_to_nav_pub[robot].publish(msg)
        print(f"{robot}: 주행 서버로 {command} 보냄")

    def _call_set_yolo_mode(self, robot: str, stream: str, mode: str, timeout_sec: float = 5.0):
        """/yolo/set_mode 서비스 호출 (동기). mode: 'BOX_DETECTION_MODEL' | 'EXPLOSIVE_DETECTION_MODEL' | 'OFF'"""
        if not self.yolo_mode_client.wait_for_service(timeout_sec=2.0):
            self.get_logger().warning('YOLO set_mode 서비스 없음')
            return
        req = SetYoloMode.Request()
        req.robot_name = robot
        req.stream     = stream
        req.mode       = mode
        res = self.yolo_mode_client.call(req, timeout_sec=timeout_sec)
        if res is None:
            self.get_logger().warning(f'YOLO set_mode {robot}/{stream}/{mode} 타임아웃 ({timeout_sec}s)')
            return
        self.get_logger().debug(f'YOLO mode [{robot}:{stream}] → {mode}')

    def _call_arm_pose(self, robot: str, pose: str, timeout_sec: float = 30.0):
        """/{robot}/arm_pose 서비스 호출 (동기). pose: 'HOME' | 'CAMERA_VIEW' | 'BOX_VIEW'

        timeout이 길어야 하는 이유:
          - 로봇 핸들러가 자세마다 SETTLE_SEC(3s) sleep → 응답이 항상 3s+ (3s면 무조건 타임아웃).
          - arm_pose_server 재기동 직후엔 릴레이가 서비스 등장까지 최대 15s 대기 + 호출 10s (총 ~25s).
        릴레이가 ~25s 내에 (성공/실패) 응답을 돌려주므로 정상 호출은 ~4~6s에 반환되어 이 timeout을 다 쓰지 않는다."""
        client = self.arm_pose_clients[robot]
        if not client.wait_for_service(timeout_sec=timeout_sec):
            self.get_logger().warning(f'[{robot}] arm_pose 서비스 없음 ({timeout_sec}s 타임아웃)')
            return
        req = ArmPose.Request()
        req.pose = pose
        res = client.call(req, timeout_sec=timeout_sec)
        if res is None:
            self.get_logger().warning(f'[{robot}] arm_pose {pose} 타임아웃 ({timeout_sec}s)')
            return
        self.get_logger().debug(f'[{robot}] arm_pose → {pose}')

    #===================#
    # 박스 열기
    #===================#

    def _send_open_box_cover_goal(self, robot: str, box_id: str):
        """TCP 소켓으로 로봇에 box_id 전송, 스레드에서 결과 수신."""
        session = _BoxOpenSession()
        with self._lock:
            self.robot_table[robot].open_box_cover_handle = session
        threading.Thread(
            target=self._run_box_open, args=(robot, box_id, session), daemon=True
        ).start()

    def _run_box_open(self, robot: str, box_id: str, session: _BoxOpenSession):
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        success = False
        
        try:
            s.settimeout(2.0)
            s.connect((ROBOT_IP[robot], OPEN_BOX_PORT))
            session.sock = s
            s.settimeout(IMITATION_TIMEOUT)
            s.sendall(f'{box_id}\n'.encode())
            line = s.makefile().readline().strip()
            if session._cancelled:
                return
            success = (line == 'OK')
            if not success:
                self.get_logger().warning(f'[{robot}] OPEN_BOX_COVER 실패: {line}')
        except Exception as e:
            if session._cancelled:
                return
            self.get_logger().error(f'[{robot}] box open 소켓 오류: {e}')
        finally:
            try: s.close()
            except Exception: pass

        if session._cancelled:
            return
        time.sleep(3.0)

        _success = success
        def _handle_result():
            with self._lock:
                if self.robot_table[robot].state != RobotState.OPEN_BOX_COVER:
                    return
            
            self._call_task_command(robot, 'robot_arm_pose_server', 'start')
            if _success:
                self.get_logger().info(f'[{robot}] 박스 열기 성공)')
                self._transition_to_box_scan(robot, box_id)
            else:
                self.get_logger().info(f'[{robot}] 박스 열기 실패)')
                self._on_open_box_cover_fail(robot, box_id)
        self._run_async(_handle_result)

    def _on_open_box_cover_fail(self, robot: str, box_id: str):
        
        with self._lock:
            if box_id in self.box_registry:
                self.box_registry[box_id].status = BoxStatus.OPEN_FAILED

        self._publish_driving_command(robot, 'stop')
        self._transition_to_self_driving(robot)

    # 박스 열기 끝

    def _cancel_actions(self, robot: str):
        """진행 중인 OPEN_BOX_COVER 세션을 취소 (선점 시 사용)."""
        entry = self.robot_table[robot]
        handle = entry.open_box_cover_handle
        if handle:
            handle.cancel()  # 소켓 close → 로봇 recv 빈 바이트 감지
            entry.open_box_cover_handle = None

    def _cancel_timers(self, robot: str):
        """로봇 관련 타이머 취소."""
        entry = self.robot_table[robot]
        for attr in ('box_scan_timer', 'partner_timer'):
            timer = getattr(entry, attr)
            if timer:
                timer.cancel()
                setattr(entry, attr, None)

    def _start_leader_arm(self, robot: str):
        """서버 쪽 리더암 읽기 프로세스 시작 → /{robot}/goal_positions 토픽 발행"""
        port = LEADER_PORTS.get(robot)
        if not port:
            self.get_logger().error(f'[{robot}] LEADER_PORTS에 포트 미등록')
            return
        if robot in self._leader_processs and self._leader_processs[robot].poll() is None:
            self.get_logger().warning(f'[{robot}] 리더암 프로세스 이미 실행 중')
            return
        cmd = (
            f"{_ROS_SOURCE} && "
            f"ROS_DOMAIN_ID={DOMAIN[robot]} "          # 리더암을 로봇 도메인에 직접 참여시킴 (goal_positions 브릿지 불필요)
            f"ros2 run roscue_server server_omx_manual_control "
            f"--ros-args -p port:={port}"
        )
        proc = subprocess.Popen(['bash', '-lc', cmd], start_new_session=True)
        self._leader_processs[robot] = proc
        self.get_logger().info(f'[{robot}] 리더암 시작 (port={port}, PID={proc.pid})')

    def _stop_leader_arm(self, robot: str):
        """해당 로봇의 서버 쪽 리더암 프로세스 종료."""
        proc = self._leader_processs.pop(robot, None)
        if proc and proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGINT)
                proc.wait(timeout=2.0)
            except Exception:
                proc.kill()

    def _stop_leader_arms(self):
        """실행 중인 모든 리더암 프로세스 종료."""
        for robot, proc in list(self._leader_processs.items()):
            if proc.poll() is None:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGINT)
                    proc.wait(timeout=2.0)
                except Exception:
                    proc.kill()
            self.get_logger().info(f'[{robot}] 리더암 종료')
        self._leader_processs.clear()


# =========================================================
# main
# =========================================================
def main():
    rclpy.init(domain_id=ROS_DOMAIN_ID)
    node = RoscueCentralServerNode()

    executor = MultiThreadedExecutor(num_threads=8)
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info('종료: 모든 로봇 IDLE 전환 중...')
        for robot in ROBOT_LIST:
            node._transition_to_idle(robot)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
