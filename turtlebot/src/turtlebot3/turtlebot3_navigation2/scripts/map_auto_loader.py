#~/ROS2_project_ws/turtlebot/src/turtlebot3/turtlebot3_navigation2/scripts/map_auto_loader.py

#!/usr/bin/env python3

import os
import time

import rclpy
from rclpy.node import Node
from nav2_msgs.srv import LoadMap


class MapAutoLoader(Node):
    def __init__(self):
        super().__init__('map_auto_loader')

        self.declare_parameter('map_yaml_path', '/home/kj/ROS2_project_ws/map/test.yaml')
        self.declare_parameter('load_map_service', '/map_server/load_map')
        self.declare_parameter('check_period_sec', 1.0)
        self.declare_parameter('stable_check_sec', 1.0)
        self.declare_parameter('load_once', True)

        self.map_yaml_path = self.get_parameter('map_yaml_path').value
        self.load_map_service = self.get_parameter('load_map_service').value
        self.check_period_sec = float(self.get_parameter('check_period_sec').value)
        self.stable_check_sec = float(self.get_parameter('stable_check_sec').value)
        self.load_once = bool(self.get_parameter('load_once').value)

        self.loaded = False

        self.client = self.create_client(LoadMap, self.load_map_service)

        self.get_logger().info('map_auto_loader started.')
        self.get_logger().info(f'Watching map yaml: {self.map_yaml_path}')
        self.get_logger().info(f'LoadMap service: {self.load_map_service}')

        self.timer = self.create_timer(self.check_period_sec, self.timer_callback)

    def timer_callback(self):
        if self.load_once and self.loaded:
            return

        if not os.path.exists(self.map_yaml_path):
            self.get_logger().info(f'Waiting for map file: {self.map_yaml_path}')
            return

        if not self.is_file_stable(self.map_yaml_path):
            self.get_logger().warn('Map yaml exists, but file is still changing. Waiting...')
            return

        if not self.client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn(f'Waiting for service: {self.load_map_service}')
            return

        self.get_logger().info(f'Map file detected. Loading map: {self.map_yaml_path}')

        request = LoadMap.Request()
        request.map_url = self.map_yaml_path

        future = self.client.call_async(request)
        future.add_done_callback(self.load_map_done_callback)

        self.loaded = True

    def is_file_stable(self, path):
        try:
            size1 = os.path.getsize(path)
            mtime1 = os.path.getmtime(path)

            time.sleep(self.stable_check_sec)

            size2 = os.path.getsize(path)
            mtime2 = os.path.getmtime(path)

            return size1 == size2 and mtime1 == mtime2
        except Exception as e:
            self.get_logger().error(f'Failed to check file stability: {e}')
            return False

    def load_map_done_callback(self, future):
        try:
            response = future.result()
        except Exception as e:
            self.get_logger().error(f'LoadMap service call failed: {e}')
            self.loaded = False
            return

        result = response.result

        if result == LoadMap.Response.RESULT_SUCCESS:
            self.get_logger().info('Map loaded successfully.')
            self.get_logger().info('Now re-set initial poses for tb3 and wf2 in RViz.')
        else:
            self.get_logger().error(f'Failed to load map. result code: {result}')
            self.loaded = False


def main(args=None):
    rclpy.init(args=args)
    node = MapAutoLoader()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()