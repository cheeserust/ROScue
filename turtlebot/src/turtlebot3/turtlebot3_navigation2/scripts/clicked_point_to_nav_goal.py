#!/usr/bin/env python3

import math

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from geometry_msgs.msg import PointStamped
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose


def yaw_to_quaternion(yaw: float):
    qz = math.sin(yaw * 0.5)
    qw = math.cos(yaw * 0.5)
    return qz, qw


class ClickedPointToNavGoal(Node):
    def __init__(self):
        super().__init__('clicked_point_to_nav_goal')

        # ---- parameters (must match launch file) ----
        self.declare_parameter('clicked_point_topic', '/clicked_point')
        self.declare_parameter('default_yaw', 0.0)
        self.declare_parameter('ignore_non_map_frame', True)
        self.declare_parameter('burger_robot_name', 'tb3')
        self.declare_parameter('waffle_robot_name', 'wf2')
        self.declare_parameter('burger_action_name', '/tb3/navigate_to_pose')
        self.declare_parameter('waffle_action_name', '/wf2/navigate_to_pose')
        self.declare_parameter('server_wait_timeout_sec', 3.0)

        self.clicked_point_topic = (
            self.get_parameter('clicked_point_topic')
            .get_parameter_value().string_value
        )
        self.default_yaw = (
            self.get_parameter('default_yaw')
            .get_parameter_value().double_value
        )
        self.ignore_non_map_frame = (
            self.get_parameter('ignore_non_map_frame')
            .get_parameter_value().bool_value
        )
        self.burger_robot_name = (
            self.get_parameter('burger_robot_name')
            .get_parameter_value().string_value
        )
        self.waffle_robot_name = (
            self.get_parameter('waffle_robot_name')
            .get_parameter_value().string_value
        )
        self.burger_action_name = (
            self.get_parameter('burger_action_name')
            .get_parameter_value().string_value
        )
        self.waffle_action_name = (
            self.get_parameter('waffle_action_name')
            .get_parameter_value().string_value
        )
        self.server_wait_timeout_sec = (
            self.get_parameter('server_wait_timeout_sec')
            .get_parameter_value().double_value
        )

        # ---- one action client per robot ----
        self.burger_client = ActionClient(
            self, NavigateToPose, self.burger_action_name
        )
        self.waffle_client = ActionClient(
            self, NavigateToPose, self.waffle_action_name
        )

        # odd click -> burger(tb3), even click -> waffle(wf2)
        self.click_count = 0

        self.sub = self.create_subscription(
            PointStamped,
            self.clicked_point_topic,
            self.clicked_point_callback,
            10
        )

        self.get_logger().info('clicked_point_to_nav_goal started.')
        self.get_logger().info(f'Subscribing topic: {self.clicked_point_topic}')
        self.get_logger().info(
            f'odd click -> {self.burger_robot_name} ({self.burger_action_name}), '
            f'even click -> {self.waffle_robot_name} ({self.waffle_action_name})'
        )
        self.get_logger().info('Waiting for clicked point from Pinky or RViz...')

    def clicked_point_callback(self, msg: PointStamped):
        frame_id = msg.header.frame_id

        if self.ignore_non_map_frame and frame_id != 'map':
            self.get_logger().warn(
                f'Ignored clicked point because frame_id is "{frame_id}", not "map".'
            )
            return

        x = msg.point.x
        y = msg.point.y
        z = msg.point.z

        # decide target robot by click parity BEFORE sending
        self.click_count += 1
        if self.click_count % 2 == 1:
            client = self.burger_client
            robot_name = self.burger_robot_name
            action_name = self.burger_action_name
        else:
            client = self.waffle_client
            robot_name = self.waffle_robot_name
            action_name = self.waffle_action_name

        self.get_logger().info(
            f'Click #{self.click_count} -> {robot_name} | '
            f'frame={frame_id}, x={x:.3f}, y={y:.3f}, z={z:.3f}'
        )

        self.send_nav_goal(client, robot_name, action_name,
                           frame_id, x, y, self.default_yaw)

    def send_nav_goal(self, client, robot_name, action_name,
                      frame_id, x, y, yaw):
        self.get_logger().info(
            f'Checking Nav2 action server for {robot_name} ({action_name})...'
        )

        if not client.wait_for_server(timeout_sec=self.server_wait_timeout_sec):
            self.get_logger().error(
                f'Nav2 action server {action_name} is not available. '
                f'Check if {robot_name} Nav2 stack is running and active.'
            )
            # do not consume the click on failure: revert counter so the next
            # click retries the same robot
            self.click_count -= 1
            return

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = PoseStamped()
        goal_msg.pose.header.frame_id = frame_id
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = float(x)
        goal_msg.pose.pose.position.y = float(y)
        goal_msg.pose.pose.position.z = 0.0

        qz, qw = yaw_to_quaternion(yaw)
        goal_msg.pose.pose.orientation.z = qz
        goal_msg.pose.pose.orientation.w = qw

        self.get_logger().info(
            f'Sending Nav2 goal to {robot_name}: frame={frame_id}, '
            f'x={x:.3f}, y={y:.3f}, yaw={yaw:.3f}'
        )

        send_future = client.send_goal_async(
            goal_msg,
            feedback_callback=lambda fb, rn=robot_name: self.feedback_callback(fb, rn)
        )
        send_future.add_done_callback(
            lambda fut, rn=robot_name: self.goal_response_callback(fut, rn)
        )

    def goal_response_callback(self, future, robot_name):
        try:
            goal_handle = future.result()
        except Exception as e:
            self.get_logger().error(f'[{robot_name}] Goal send failed: {e}')
            return

        if goal_handle is None:
            self.get_logger().error(f'[{robot_name}] Goal handle is None.')
            return

        if not goal_handle.accepted:
            self.get_logger().error(f'[{robot_name}] Goal rejected by Nav2.')
            return

        self.get_logger().info(f'[{robot_name}] Goal accepted by Nav2.')

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda fut, rn=robot_name: self.result_callback(fut, rn)
        )

    def feedback_callback(self, feedback_msg, robot_name):
        distance = feedback_msg.feedback.distance_remaining
        self.get_logger().info(f'[{robot_name}] Distance remaining: {distance:.2f} m')

    def result_callback(self, future, robot_name):
        try:
            result = future.result()
        except Exception as e:
            self.get_logger().error(f'[{robot_name}] Navigation result error: {e}')
            return

        self.get_logger().info(
            f'[{robot_name}] Navigation finished. status={result.status}'
        )


def main(args=None):
    rclpy.init(args=args)
    node = ClickedPointToNavGoal()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()