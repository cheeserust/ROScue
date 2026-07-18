#!/usr/bin/env python3

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

db_path = os.path.expanduser('~/NEWrosproject/turtlebot/coord_list/roscue_nav_points.db') # 경로 수정 필요

def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
        ),

        Node(
            package='roscue_dispatch',
            executable='multi_robot_point_dispatcher.py',
            name='multi_robot_point_dispatcher',
            output='screen',
            parameters=[
                {
                    # Pinky domain 13 -> PC domain 10 bridge로 받은 clicked point
                    'clicked_point_topic': '/pinky/clicked_point',

                    # Pinky domain 13 -> PC domain 10 bridge로 받은 최신 OccupancyGrid.
                    # 랜덤 goal은 이 맵에서 free space만 샘플링한다.
                    'map_topic': '/pinky/map',
                    'map_update_topic': '/pinky/map_updates',

                    # WF1/WF2 domain -> PC domain 10 bridge로 받은 AMCL pose
                    'wf1_pose_topic': '/wf1/amcl_pose',
                    'wf2_pose_topic': '/wf2/amcl_pose',

                    # PC domain 10에서 발행 후
                    # pc10_to_wf1_14 / pc10_to_wf2_15 bridge가
                    # 각 로봇 domain의 /goal_pose 또는 /pending_goal_pose로 전달
                    'wf1_goal_topic': '/wf1/goal_pose',
                    'wf2_goal_topic': '/wf2/goal_pose',

                    # 중앙서버 -> PC domain 10 command topic.
                    # ros2 topic pub --once /driving_command roscue_interface/msg/MainToNavMsg \
                    #   "{robot_name: 'waffle1', command: 'start'}"
                    'driving_command_topic': '/driving_command',
                    'driving_command_type': 'roscue_interface/msg/MainToNavMsg',
                    'initial_driving_command': 'stop',

                    # PC -> WF domain cancel 신호. bridge가 robot local /cancel_navigation으로 remap한다.
                    'wf1_cancel_topic': '/wf1/cancel_navigation',
                    'wf2_cancel_topic': '/wf2/cancel_navigation',

                    # clicked/random 좌표와 dispatch 상태를 실시간 저장할 DB.
                    'db_path': db_path,
                    'load_pending_from_db_on_start': True,

                    'map_frame': 'map',
                    'goal_wait_sec': 5.0,
                    'arrival_tolerance': 0.25,
                    'default_yaw': 0.0,
                    'timer_period_sec': 0.2,

                    # 같은 목표를 주기적으로 다시 발행한다.
                    # /goal_pose 1회 publish가 bridge/Nav2 쪽에서 누락되거나
                    # Nav2가 중간에 abort된 경우에도 같은 목표를 다시 넣기 위한 안전장치.
                    'goal_republish_sec': 1.0,

                    # 주행 중 남은 거리 로그 출력 주기
                    'status_log_sec': 2.0,

                    # AMCL pose가 갱신되지 않을 때 경고 기준
                    'pose_timeout_sec': 10.0,

                    # True이면 AMCL pose가 들어오기 전에는 목표를 보내지 않음
                    'require_pose_before_dispatch': True,

                    # wf1/wf2가 각각 첫 번째 목표에 도착한 뒤부터
                    # 최신 /pinky/map의 free space에서 30초마다 랜덤 goal을 추가한다.
                    'random_goal_enabled': True,
                    'random_goal_period_sec': 30.0,

                    # TurtleBot3 Waffle 기준으로 장애물/unknown 주변을 피하기 위한 여유 거리.
                    # 맵이 좁아서 샘플링 실패가 반복되면 0.35 정도로 낮춰볼 수 있다.
                    'random_goal_min_clearance_m': 0.45,
                    'random_goal_occupied_threshold': 50,
                    'random_goal_unknown_is_obstacle': True,
                    'random_goal_max_attempts': 2000,
                    'random_goal_border_margin_cells': 2,

                    # 0이면 pending_points 개수 제한 없이 계속 저장한다.
                    'random_goal_max_pending': 0,
                    'random_goal_seed': 0,
                    'random_goal_use_map_updates': True,

                    'use_sim_time': use_sim_time,
                }
            ],
        ),
    ])
