from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # Waffle 1 Master Node
        Node(
            package='my_robot_pkg',
            executable='leader_node',
            namespace='waffle1',
            parameters=[{'port': '/dev/ttyACM0'}],
            output='screen'
        ),
        # Waffle 2 Master Node
        Node(
            package='my_robot_pkg',
            executable='leader_node',
            namespace='waffle2',
            parameters=[{'port': '/dev/ttyACM1'}],
            output='screen'
        ),
    ])