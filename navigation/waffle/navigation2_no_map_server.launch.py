#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    params_file = LaunchConfiguration('params_file')
    autostart = LaunchConfiguration('autostart')

    configured_params = RewrittenYaml(
        source_file=params_file,
        root_key='',
        param_rewrites={
            'use_sim_time': use_sim_time,
        },
        convert_types=True,
    )

    lifecycle_nodes = [
        'amcl',
        'controller_server',
        'planner_server',
        'behavior_server',
        'bt_navigator',
        'smoother_server',
        'velocity_smoother',
    ]

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),

        DeclareLaunchArgument(
            'params_file',
            default_value=os.path.join(
                get_package_share_directory('roscue_nav'),
                'param',
                'waffle.yaml'
            )
        ),

        DeclareLaunchArgument('autostart', default_value='true'),


        # map_server는 실행하지 않음.
        # Pinky domain 13 -> PC domain 10 -> Waffle domains 14/15 로 bridge된 /map을 사용한다.

        Node(
            package='nav2_amcl',
            executable='amcl',
            name='amcl',
            output='screen',
            parameters=[configured_params],
        ),

        Node(
            package='nav2_controller',
            executable='controller_server',
            name='controller_server',
            output='screen',
            parameters=[configured_params],
        ),

        Node(
            package='nav2_planner',
            executable='planner_server',
            name='planner_server',
            output='screen',
            parameters=[configured_params],
        ),

        Node(
            package='nav2_behaviors',
            executable='behavior_server',
            name='behavior_server',
            output='screen',
            parameters=[configured_params],
        ),

        Node(
            package='nav2_bt_navigator',
            executable='bt_navigator',
            name='bt_navigator',
            output='screen',
            parameters=[configured_params],
        ),

        Node(
            package='nav2_smoother',
            executable='smoother_server',
            name='smoother_server',
            output='screen',
            parameters=[configured_params],
        ),

        Node(
            package='nav2_velocity_smoother',
            executable='velocity_smoother',
            name='velocity_smoother',
            output='screen',
            parameters=[configured_params],
        ),

        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_navigation',
            output='screen',
            parameters=[
                {
                    'use_sim_time': use_sim_time,
                    'autostart': autostart,
                    'node_names': lifecycle_nodes,
                }
            ],
        ),

        # PC에서 bridge된 목표는 /goal_pose가 아니라 /pending_goal_pose로 받는다.
        # 와플 서버는 /driving_command를 구독하지 않는다.
        # PC가 stop 명령을 받으면 /cancel_navigation만 bridge해서 현재 Nav2 action을 cancel한다.
        Node(
            package='roscue_nav',
            executable='driving_command_goal_gate.py',
            name='driving_command_goal_gate',
            output='screen',
            parameters=[
                {
                    'pending_goal_topic': '/pending_goal_pose',
                    'cancel_navigation_topic': '/cancel_navigation',
                    'navigate_action_name': '/navigate_to_pose',
                    'same_goal_tolerance': 0.001,
                    'use_sim_time': use_sim_time,
                }
            ],
        ),
    ])
