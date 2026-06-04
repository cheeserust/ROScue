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

        self.declare_parameter('clicked_point_topic', '/clicked_point')
        self.declare_parameter('default_yaw', 0.0)
        self.declare_parameter('ignore_non_map_frame', True)

        self.clicked_point_topic = (
            self.get_parameter('clicked_point_topic')
            .get_parameter_value()
            .string_value
        )

        self.default_yaw = (
            self.get_parameter('default_yaw')
            .get_parameter_value()
            .double_value
        )

        self.ignore_non_map_frame = (
            self.get_parameter('ignore_non_map_frame')
            .get_parameter_value()
            .bool_value
        )

        self.nav_client = ActionClient(
            self,
            NavigateToPose,
            'navigate_to_pose'
        )

        self.sub = self.create_subscription(
            PointStamped,
            self.clicked_point_topic,
            self.clicked_point_callback,
            10
        )

        self.get_logger().info('clicked_point_to_nav_goal started.')
        self.get_logger().info(f'Subscribing topic: {self.clicked_point_topic}')
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

        self.get_logger().info(
            f'Received clicked point: frame={frame_id}, '
            f'x={x:.3f}, y={y:.3f}, z={z:.3f}'
        )

        self.send_nav_goal(frame_id, x, y, self.default_yaw)

    def send_nav_goal(self, frame_id: str, x: float, y: float, yaw: float):
        self.get_logger().info('Checking Nav2 action server...')

        if not self.nav_client.wait_for_server(timeout_sec=3.0):
            self.get_logger().error(
                'Nav2 action server /navigate_to_pose is not available. '
                'Check if Nav2 navigation_launch.py is running.'
            )
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
            f'Sending Nav2 goal: frame={frame_id}, '
            f'x={x:.3f}, y={y:.3f}, yaw={yaw:.3f}'
        )

        send_future = self.nav_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )
        send_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        try:
            goal_handle = future.result()
        except Exception as e:
            self.get_logger().error(f'Goal send failed: {e}')
            return

        if goal_handle is None:
            self.get_logger().error('Goal handle is None.')
            return

        if not goal_handle.accepted:
            self.get_logger().error('Goal rejected by Nav2.')
            return

        self.get_logger().info('Goal accepted by Nav2.')

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.result_callback)

    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        distance = feedback.distance_remaining

        self.get_logger().info(
            f'Distance remaining: {distance:.2f} m'
        )

    def result_callback(self, future):
        try:
            result = future.result()
        except Exception as e:
            self.get_logger().error(f'Navigation result error: {e}')
            return

        self.get_logger().info(
            f'Navigation finished. status={result.status}'
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
