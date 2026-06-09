#!/usr/bin/env python3

import math
import yaml
import rclpy

from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose


def yaw_to_quaternion(yaw):
    qz = math.sin(yaw / 2.0)
    qw = math.cos(yaw / 2.0)
    return qz, qw


class SavedPointsToNavGoal(Node):
    def __init__(self):
        super().__init__('saved_points_to_nav_goal')

        self.declare_parameter('yaml_file', '/home/kj/ROS2_project_ws/pinky_box_target.yaml')
        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('default_yaw', 0.0)

        self.yaml_file = self.get_parameter('yaml_file').value
        self.map_frame = self.get_parameter('map_frame').value
        self.default_yaw = float(self.get_parameter('default_yaw').value)

        self.tb3_client = ActionClient(
            self,
            NavigateToPose,
            '/tb3/navigate_to_pose'
        )

        self.wf2_client = ActionClient(
            self,
            NavigateToPose,
            '/wf2/navigate_to_pose'
        )

        self.get_logger().info(f'Load saved points from: {self.yaml_file}')

        points = self.load_points()

        if len(points) < 2:
            self.get_logger().error(
                f'Need at least 2 points, but loaded {len(points)} point(s).'
            )
            return

        self.get_logger().info('Waiting for /tb3/navigate_to_pose action server...')
        self.tb3_client.wait_for_server()

        self.get_logger().info('Waiting for /wf2/navigate_to_pose action server...')
        self.wf2_client.wait_for_server()

        self.send_goal(self.tb3_client, points[0], 'tb3')
        self.send_goal(self.wf2_client, points[1], 'wf2')

    def load_points(self):
        with open(self.yaml_file, 'r') as f:
            data = yaml.safe_load(f)

        points = []

        if data is None:
            return points

        # 형식 1:
        # - x: 1.0
        #   y: 2.0
        if isinstance(data, list):
            raw_points = data

        # 형식 2:
        # points:
        #   - x: 1.0
        #     y: 2.0
        elif isinstance(data, dict) and 'points' in data:
            raw_points = data['points']

        # 형식 3:
        # saved_points:
        #   - x: 1.0
        #     y: 2.0
        elif isinstance(data, dict) and 'saved_points' in data:
            raw_points = data['saved_points']

        else:
            self.get_logger().error('Unsupported YAML format.')
            return points

        for p in raw_points:
            try:
                x = float(p['x'])
                y = float(p['y'])
                yaw = float(p.get('yaw', self.default_yaw))

                points.append({
                    'x': x,
                    'y': y,
                    'yaw': yaw
                })

            except Exception as e:
                self.get_logger().warn(f'Skip invalid point: {p}, error: {e}')

        self.get_logger().info(f'Loaded {len(points)} valid point(s).')
        return points

    def make_goal(self, point):
        goal_msg = NavigateToPose.Goal()

        pose = PoseStamped()
        pose.header.frame_id = self.map_frame
        pose.header.stamp = self.get_clock().now().to_msg()

        pose.pose.position.x = point['x']
        pose.pose.position.y = point['y']
        pose.pose.position.z = 0.0

        qz, qw = yaw_to_quaternion(point['yaw'])
        pose.pose.orientation.x = 0.0
        pose.pose.orientation.y = 0.0
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw

        goal_msg.pose = pose
        return goal_msg

    def send_goal(self, client, point, robot_name):
        goal_msg = self.make_goal(point)

        self.get_logger().info(
            f'Send goal to {robot_name}: '
            f'x={point["x"]:.3f}, y={point["y"]:.3f}, yaw={point["yaw"]:.3f}'
        )

        future = client.send_goal_async(
            goal_msg,
            feedback_callback=lambda feedback_msg:
                self.feedback_callback(feedback_msg, robot_name)
        )

        future.add_done_callback(
            lambda future_result:
                self.goal_response_callback(future_result, robot_name)
        )

    def goal_response_callback(self, future, robot_name):
        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().error(f'{robot_name} goal rejected.')
            return

        self.get_logger().info(f'{robot_name} goal accepted.')

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda future_result:
                self.result_callback(future_result, robot_name)
        )

    def feedback_callback(self, feedback_msg, robot_name):
        feedback = feedback_msg.feedback
        distance = feedback.distance_remaining

        self.get_logger().info(
            f'{robot_name} distance remaining: {distance:.3f} m'
        )

    def result_callback(self, future, robot_name):
        result = future.result().result
        status = future.result().status

        self.get_logger().info(
            f'{robot_name} navigation finished. status={status}, result={result}'
        )


def main(args=None):
    rclpy.init(args=args)

    node = SavedPointsToNavGoal()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()