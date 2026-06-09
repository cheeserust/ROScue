# ~/ROS2_project_ws/pinky_pro/src/pinky_pro/pinky_navigation/scripts
# !/usr/bin/env python3

import os
import yaml

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PointStamped


class ClickedPointSaver(Node):
    def __init__(self):
        super().__init__('clicked_point_saver')

        self.declare_parameter('save_path', '/home/kj/ROS2_project_ws/pinky_box_target.yaml')
        self.save_path = self.get_parameter('save_path').get_parameter_value().string_value

        self.subscription = self.create_subscription(
            PointStamped,
            '/clicked_point',
            self.clicked_point_callback,
            10
        )

        self.get_logger().info('clicked_point_saver started.')
        self.get_logger().info(f'Save path: {self.save_path}')
        self.get_logger().info('In RViz, set Fixed Frame to "map" and use Publish Point.')
        self.get_logger().info('All clicked points will be saved in order.')

    def load_existing_data(self):
        """
        기존 YAML 파일이 있으면 읽어서 반환한다.
        파일이 없거나 형식이 잘못되어 있으면 points 리스트를 새로 만든다.
        """
        if not os.path.exists(self.save_path):
            return {'points': []}

        try:
            with open(self.save_path, 'r') as f:
                data = yaml.safe_load(f)

            if data is None:
                return {'points': []}

            if not isinstance(data, dict):
                self.get_logger().warn(
                    'Existing YAML data is not a dictionary. Reinitializing file.'
                )
                return {'points': []}

            if 'points' not in data:
                data['points'] = []

            if not isinstance(data['points'], list):
                self.get_logger().warn(
                    'Existing "points" field is not a list. Reinitializing points.'
                )
                data['points'] = []

            return data

        except Exception as e:
            self.get_logger().error(f'Failed to read existing YAML file: {e}')
            self.get_logger().warn('Reinitializing points list.')
            return {'points': []}

    def save_data(self, data):
        
        # points 리스트를 YAML 파일에 저장
        save_dir = os.path.dirname(self.save_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)

        with open(self.save_path, 'w') as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True
            )

    def clicked_point_callback(self, msg: PointStamped):
        frame_id = msg.header.frame_id
        x = float(msg.point.x)
        y = float(msg.point.y)
        z = float(msg.point.z)

        data = self.load_existing_data()

        point_id = len(data['points']) + 1

        new_point = {
            'id': point_id,
            'frame_id': frame_id,
            'x': x,
            'y': y,
            'z': z,
            'yaw': 0.0
        }

        data['points'].append(new_point)
        self.save_data(data)

        self.get_logger().info(
            f'Saved clicked point #{point_id}: '
            f'frame={frame_id}, x={x:.3f}, y={y:.3f}, z={z:.3f}, yaw=0.0'
        )

        if frame_id != 'map':
            self.get_logger().warn(
                f'Clicked point frame is "{frame_id}", not "map". '
                'For Nav2 goals, RViz Fixed Frame should usually be "map".'
            )


def main(args=None):
    rclpy.init(args=args)
    node = ClickedPointSaver()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
