#!/usr/bin/env python3

import math
from typing import Optional

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import Empty


class DrivingCommandGoalGate(Node):
    """
    Robot-domain Nav2 goal gate.

    변경된 역할:
      - 와플 서버에서는 더 이상 /driving_command를 구독하지 않는다.
      - PC가 start 상태일 때만 /pending_goal_pose를 bridge로 보내므로,
        이 노드는 들어온 pending goal을 NavigateToPose action으로 전달한다.
      - PC가 stop을 받으면 /cancel_navigation(Empty)을 1회 bridge로 보내고,
        이 노드는 현재 NavigateToPose goal만 cancel한다.
      - stop 상태에서 0 속도를 계속 publish하지 않는다.
    """

    def __init__(self):
        super().__init__('driving_command_goal_gate')

        self.declare_parameter('pending_goal_topic', '/pending_goal_pose')
        self.declare_parameter('cancel_navigation_topic', '/cancel_navigation')
        self.declare_parameter('navigate_action_name', '/navigate_to_pose')
        self.declare_parameter('same_goal_tolerance', 0.001)

        self.pending_goal_topic = self.get_parameter('pending_goal_topic').value
        self.cancel_navigation_topic = self.get_parameter('cancel_navigation_topic').value
        self.navigate_action_name = self.get_parameter('navigate_action_name').value
        self.same_goal_tolerance = float(self.get_parameter('same_goal_tolerance').value)

        self.latest_goal: Optional[PoseStamped] = None
        self.active_goal_handle = None
        self.active_goal_pose: Optional[PoseStamped] = None
        self.cancel_in_progress = False
        self.send_latest_after_cancel = False

        self.goal_sub = self.create_subscription(
            PoseStamped,
            self.pending_goal_topic,
            self.pending_goal_callback,
            10,
        )

        self.cancel_sub = self.create_subscription(
            Empty,
            self.cancel_navigation_topic,
            self.cancel_navigation_callback,
            10,
        )

        self.nav_client = ActionClient(self, NavigateToPose, self.navigate_action_name)

        self.get_logger().info('Driving command goal gate started in goal/cancel mode.')
        self.get_logger().info(f'pending_goal_topic: {self.pending_goal_topic}')
        self.get_logger().info(f'cancel_navigation_topic: {self.cancel_navigation_topic}')
        self.get_logger().info(f'navigate_action_name: {self.navigate_action_name}')

    def pending_goal_callback(self, msg: PoseStamped):
        self.latest_goal = msg
        self.get_logger().info(
            f'Received pending goal: x={msg.pose.position.x:.3f}, y={msg.pose.position.y:.3f}'
        )
        self.try_send_latest_goal()

    def cancel_navigation_callback(self, _msg: Empty):
        self.get_logger().info('Received cancel_navigation. Cancel active Nav2 goal and clear latest pending goal.')
        self.latest_goal = None
        self.send_latest_after_cancel = False
        self.cancel_active_goal()

    def try_send_latest_goal(self):
        if self.latest_goal is None:
            return

        if self.active_goal_handle is not None and self.active_goal_pose is not None:
            if self.is_same_goal(self.active_goal_pose, self.latest_goal):
                return
            self.get_logger().info('New goal differs from active goal. Cancel old goal first.')
            self.send_latest_after_cancel = True
            self.cancel_active_goal()
            return

        if not self.nav_client.server_is_ready():
            self.get_logger().warn('NavigateToPose action server is not ready yet. Waiting...')
            self.nav_client.wait_for_server(timeout_sec=1.0)
            if not self.nav_client.server_is_ready():
                return

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = self.latest_goal

        self.get_logger().info(
            f'Sending goal to Nav2: x={goal_msg.pose.pose.position.x:.3f}, '
            f'y={goal_msg.pose.pose.position.y:.3f}'
        )
        send_future = self.nav_client.send_goal_async(goal_msg)
        send_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn('NavigateToPose goal was rejected.')
            self.active_goal_handle = None
            self.active_goal_pose = None
            return

        self.active_goal_handle = goal_handle
        self.active_goal_pose = self.latest_goal
        self.cancel_in_progress = False
        self.send_latest_after_cancel = False
        self.get_logger().info('NavigateToPose goal accepted.')

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.goal_result_callback)

    def goal_result_callback(self, future):
        result = future.result()
        status = result.status
        self.get_logger().info(f'NavigateToPose finished. status={status}')
        self.active_goal_handle = None
        self.active_goal_pose = None
        self.cancel_in_progress = False

        # 다음 목표 선택과 재발행은 PC dispatcher가 AMCL 도착 판정 후 결정한다.

    def cancel_active_goal(self):
        if self.active_goal_handle is None:
            self.active_goal_pose = None
            self.cancel_in_progress = False
            self.get_logger().info('No active NavigateToPose goal to cancel.')
            return

        if self.cancel_in_progress:
            return

        self.cancel_in_progress = True
        self.get_logger().info('Canceling active NavigateToPose goal.')
        cancel_future = self.active_goal_handle.cancel_goal_async()
        cancel_future.add_done_callback(self.cancel_done_callback)

    def cancel_done_callback(self, future):
        self.cancel_in_progress = False
        self.active_goal_handle = None
        self.active_goal_pose = None
        self.get_logger().info('Cancel request completed.')

        if self.send_latest_after_cancel and self.latest_goal is not None:
            self.send_latest_after_cancel = False
            self.try_send_latest_goal()

    def is_same_goal(self, a: PoseStamped, b: PoseStamped) -> bool:
        dx = a.pose.position.x - b.pose.position.x
        dy = a.pose.position.y - b.pose.position.y
        dist = math.hypot(dx, dy)
        return dist <= self.same_goal_tolerance


def main(args=None):
    rclpy.init(args=args)
    node = DrivingCommandGoalGate()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
