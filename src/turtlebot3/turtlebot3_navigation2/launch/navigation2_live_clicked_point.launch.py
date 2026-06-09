#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    burger_params_file = LaunchConfiguration('burger_params_file')
    waffle_params_file = LaunchConfiguration('waffle_params_file')
    clicked_point_topic = LaunchConfiguration('clicked_point_topic')
    default_yaw = LaunchConfiguration('default_yaw')

    nav2_launch_dir = os.path.join(
        get_package_share_directory('nav2_bringup'),
        'launch'
    )
    navigation_launch_path = os.path.join(nav2_launch_dir, 'navigation_launch.py')

    rviz_config_file = os.path.join(
        get_package_share_directory('turtlebot3_navigation2'),
        'rviz',
        'tb3_navigation2.rviz'
    )

    default_burger_params_file = os.path.join(
        get_package_share_directory('turtlebot3_navigation2'),
        'param',
        'burger.yaml'
    )

    default_waffle_params_file = os.path.join(
        get_package_share_directory('turtlebot3_navigation2'),
        'param',
        'waffle.yaml'
    )

    burger_configured_params = RewrittenYaml(
        source_file=burger_params_file,
        root_key='tb3',
        param_rewrites={'use_sim_time': use_sim_time},
        convert_types=True,
    )

    waffle_configured_params = RewrittenYaml(
        source_file=waffle_params_file,
        root_key='wf2',
        param_rewrites={'use_sim_time': use_sim_time},
        convert_types=True,
    )

    tf_remaps = [
        ('/tf', 'tf'),
        ('/tf_static', 'tf_static'),
    ]

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation clock if true'
        ),

        DeclareLaunchArgument(
            'burger_params_file',
            default_value=default_burger_params_file,
            description='Full path to Burger(tb3) Nav2 params file'
        ),

        DeclareLaunchArgument(
            'waffle_params_file',
            default_value=default_waffle_params_file,
            description='Full path to Waffle(wf2) Nav2 params file'
        ),

        DeclareLaunchArgument(
            'clicked_point_topic',
            default_value='/clicked_point',
            description='Topic name for RViz/Pinky Publish Point'
        ),

        DeclareLaunchArgument(
            'default_yaw',
            default_value='0.0',
            description='Default yaw angle for Nav2 goal'
        ),

        # Burger Nav2 + map -> tb3/odom TF in the same namespace TF topic.
        GroupAction([
            PushRosNamespace('tb3'),

            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(navigation_launch_path),
                launch_arguments={
                    'use_sim_time': use_sim_time,
                    'params_file': burger_configured_params,
                    'autostart': 'true',
                    'use_namespace': 'false',
                }.items()
            ),

            Node(
                package='tf2_ros',
                executable='static_transform_publisher',
                name='map_to_tb3_odom_static_tf',
                arguments=[
                    '0', '0', '0',
                    '0', '0', '0',
                    'map',
                    'odom'
                ],
                remappings=tf_remaps,
                output='screen'
            ),
        ]),

        # Waffle Nav2 + map -> wf2/odom TF in the same namespace TF topic.
        GroupAction([
            PushRosNamespace('wf2'),

            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(navigation_launch_path),
                launch_arguments={
                    'use_sim_time': use_sim_time,
                    'params_file': waffle_configured_params,
                    'autostart': 'true',
                    'use_namespace': 'false',
                }.items()
            ),

            Node(
                package='tf2_ros',
                executable='static_transform_publisher',
                name='map_to_wf2_odom_static_tf',
                arguments=[
                    '0', '0', '0',
                    '0', '0', '0',
                    'map',
                    'odom'
                ],
                remappings=tf_remaps,
                output='screen'
            ),
        ]),

        # /clicked_point:
        # 1st/odd click  -> /tb3/navigate_to_pose
        # 2nd/even click -> /wf2/navigate_to_pose
        Node(
            package='turtlebot3_navigation2',
            executable='clicked_point_to_nav_goal.py',
            name='clicked_point_to_nav_goal',
            output='screen',
            parameters=[{
                'clicked_point_topic': clicked_point_topic,
                'default_yaw': default_yaw,
                'ignore_non_map_frame': True,
                'burger_robot_name': 'tb3',
                'waffle_robot_name': 'wf2',
                'burger_action_name': '/tb3/navigate_to_pose',
                'waffle_action_name': '/wf2/navigate_to_pose',
                'server_wait_timeout_sec': 3.0,
            }]
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_config_file],
            parameters=[{'use_sim_time': use_sim_time}],
            output='screen'
        ),
    ])
