#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node


TURTLEBOT3_MODEL = os.environ.get('TURTLEBOT3_MODEL', 'burger')
ROS_DISTRO = os.environ.get('ROS_DISTRO')


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    params_file = LaunchConfiguration('params_file')
    clicked_point_topic = LaunchConfiguration('clicked_point_topic')
    default_yaw = LaunchConfiguration('default_yaw')

    param_file_name = TURTLEBOT3_MODEL + '.yaml'

    if ROS_DISTRO == 'humble':
        default_params_file = os.path.join(
            get_package_share_directory('turtlebot3_navigation2'),
            'param',
            ROS_DISTRO,
            param_file_name
        )
    else:
        default_params_file = os.path.join(
            get_package_share_directory('turtlebot3_navigation2'),
            'param',
            param_file_name
        )

    nav2_launch_dir = os.path.join(
        get_package_share_directory('nav2_bringup'),
        'launch'
    )

    rviz_config_file = os.path.join(
        get_package_share_directory('turtlebot3_navigation2'),
        'rviz',
        'tb3_navigation2.rviz'
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation clock if true'
        ),

        DeclareLaunchArgument(
            'params_file',
            default_value=default_params_file,
            description='Full path to the Nav2 params file'
        ),

        DeclareLaunchArgument(
            'clicked_point_topic',
            default_value='/clicked_point',
            description='Topic name for RViz Publish Point'
        ),

        DeclareLaunchArgument(
            'default_yaw',
            default_value='0.0',
            description='Default yaw angle for Nav2 goal'
        ),

        # ------------------------------------------------------------
        # 저장된 map.yaml 없이 Nav2 주행 노드만 실행
        #
        # 기존 navigation2.launch.py처럼 bringup_launch.py를 쓰면
        # map_server와 AMCL이 map.yaml을 요구합니다.
        #
        # 여기서는 map이 아직 저장되지 않은 상태에서 주행해야 하므로
        # navigation_launch.py만 실행합니다.
        # ------------------------------------------------------------
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(nav2_launch_dir, 'navigation_launch.py')
            ),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'params_file': params_file
            }.items()
        ),

        # ------------------------------------------------------------
        # TurtleBot의 odom 좌표계를 map 좌표계처럼 사용하기 위한 static TF
        #
        # 전제:
        # Pinky 시작 위치와 TurtleBot 시작 위치가 같다.
        # Pinky 시작 방향과 TurtleBot 시작 방향도 같다.
        #
        # 그러면 Pinky의 map 기준 clicked point를
        # TurtleBot의 시작점 기준 좌표처럼 사용할 수 있습니다.
        # ------------------------------------------------------------
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='map_to_odom_static_tf',
            arguments=[
                '0', '0', '0',
                '0', '0', '0',
                'map',
                'tb3/odom'
            ],
            output='screen'
        ),

        # ------------------------------------------------------------
        # /clicked_point를 받으면 바로 Nav2 navigate_to_pose goal로 전송
        # ------------------------------------------------------------
        Node(
            package='turtlebot3_navigation2',
            executable='clicked_point_to_nav_goal.py',
            name='clicked_point_to_nav_goal',
            output='screen',
            parameters=[{
                'clicked_point_topic': clicked_point_topic,
                'default_yaw': default_yaw,
                'ignore_non_map_frame': True
            }]
        ),

        # RViz 실행
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_config_file],
            parameters=[{'use_sim_time': use_sim_time}],
            output='screen'
        ),
    ])
