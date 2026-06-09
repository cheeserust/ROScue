# ~/ROS2_project_ws/turtlebot/src/turtlebot3/turtlebot3_navigation2/launch/map_saver.launch.py

from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='nav2_map_server',
            executable='map_saver_server',
            name='map_saver',
            output='screen',
            remappings=[('map', '/pinky/map')],
            parameters=[{
                'save_map_timeout': 5.0,
                'free_thresh_default': 0.25,
                'occupied_thresh_default': 0.65,
                'map_subscribe_transient_local': True,
            }],
        ),
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_map_saver',
            output='screen',
            parameters=[{
                'autostart': True,
                'node_names': ['map_saver'],
            }],
        ),
    ])