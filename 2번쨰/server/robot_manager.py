# server pc: robot_manager.py
# Robot Management Layer
# 각 로봇의 /<name>/state 토픽을 구독해서 로봇별 최신 상태를 보관한다.

from roscue_interface.msg import RobotState


class RobotInfo:
    """로봇 한 대의 상태."""
    def __init__(self, robot_name):
        self.robot_name = robot_name
        self.battery = 0.0
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.linear_velocity = 0.0
        self.angular_velocity = 0.0
        self.mission_status = 'unknown'
        self.last_update_sec = 0.0  # 마지막으로 상태를 받은 시각(초)

    def is_online(self, now_sec, timeout_sec=5.0):
        # 최근 timeout_sec 안에 상태를 받았으면 온라인으로 본다
        return (now_sec - self.last_update_sec) < timeout_sec


class RobotManager:
    def __init__(self, node, robot_names):
        self._node = node
        self._robots = {}
        for name in robot_names:
            self._robots[name] = RobotInfo(name)
            # 각 로봇의 상태 토픽을 구독한다. 콜백은 하나를 공용으로 쓰고,
            # 어느 로봇인지는 메시지 안의 robot_name 으로 구분한다.
            node.create_subscription(RobotState, f'/{name}/state', self._on_state, 10)

    def _on_state(self, msg):
        info = self._robots.get(msg.robot_name)
        if info is None:
            return
        info.battery = msg.battery
        info.x = msg.x
        info.y = msg.y
        info.yaw = msg.yaw
        info.linear_velocity = msg.linear_velocity
        info.angular_velocity = msg.angular_velocity
        info.mission_status = msg.mission_status
        info.last_update_sec = self._node.get_clock().now().nanoseconds / 1e9

    def get(self, robot_name):
        return self._robots.get(robot_name)

    def all(self):
        return list(self._robots.values())