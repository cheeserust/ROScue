# ~/ROS2_project_ws/turtlebot/src/turtlebot3/turtlebot3_navigation2/launch/navigation2_live_clicked_point.launch.py

# 구조:
# 1. 단일 글로벌 map_server를 placeholder/dummy map으로 먼저 실행
# 2. tb3, wf2 각각 AMCL + Nav2 실행
# 3. map_auto_loader.py가 final_map_yaml 파일 생성을 감시
# 4. pinky_map_saver.py가 최종 맵을 저장하면 /map_server/load_map으로 자동 교체
# 5. clicked_point_saver.py가 RViz Publish Point 좌표를 YAML에 순서대로 저장
#
# 주의:
# - 맵이 자동 교체된 뒤에도 tb3/wf2의 2D Pose Estimate는 다시 넣어야 함
# - final_map_yaml 파일이 이미 존재하면 launch 직후 바로 로드됨
# - clicked_point_saver.py는 좌표 저장만 하고, 로봇 주행 goal은 보내지 않음

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
    clicked_points_yaml = LaunchConfiguration('clicked_points_yaml')
    map_yaml = LaunchConfiguration('map')
    final_map_yaml = LaunchConfiguration('final_map_yaml')

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
        # root_key='tb3',
        param_rewrites={'use_sim_time': use_sim_time},
        convert_types=True,
    )

    waffle_configured_params = RewrittenYaml(
        source_file=waffle_params_file,
        # root_key='wf2',
        param_rewrites={'use_sim_time': use_sim_time},
        convert_types=True,
    )

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

        # placeholder/dummy map으로 시동
        # 실제 Pinky 최종맵은 final_map_yaml 파일이 생기면 자동 load_map으로 교체
        DeclareLaunchArgument(
            'map',
            default_value='/home/user/ROS2_project_ws/map/401.yaml',
            description='Placeholder map yaml; real map is loaded later by map_auto_loader'
        ),

        # pinky_map_saver.py가 저장할 최종 맵 yaml 경로
        # 이 파일이 생기면 map_auto_loader.py가 /map_server/load_map을 자동 호출
        DeclareLaunchArgument(
            'final_map_yaml',
            default_value='/home/kj/ROS2_project_ws/map/test.yaml',
            description='Final Pinky map yaml path to auto-load when the file appears'
        ),

        DeclareLaunchArgument(
            'clicked_point_topic',
            default_value='/clicked_point',
            description='Topic name for RViz Publish Point'
        ),

        # RViz Publish Point로 찍은 좌표들을 저장할 YAML 파일
        DeclareLaunchArgument(
            'clicked_points_yaml',
            default_value='/home/user/ROS2_project_ws/pinky_box_target.yaml',
            description='YAML file path for saving clicked points in order'
        ),

        # ── 글로벌 map_server: namespace 밖, 단일 /map 발행 ──────────────
        Node(
            package='nav2_map_server',
            executable='map_server',
            name='map_server',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'yaml_filename': map_yaml,
            }],
        ),

        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_map',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'autostart': True,
                'node_names': ['map_server'],
            }],
        ),

        # ── 최종 Pinky map 자동 로더 ─────────────────────────────────────
        # final_map_yaml 파일이 생기면 /map_server/load_map 호출
        Node(
            package='turtlebot3_navigation2',
            executable='map_auto_loader.py',
            name='map_auto_loader',
            output='screen',
            parameters=[{
                'map_yaml_path': final_map_yaml,
                'load_map_service': '/map_server/load_map',
                'check_period_sec': 1.0,
                'stable_check_sec': 1.0,
                'load_once': True,
            }],
        ),

        Node(
            package='turtlebot3_navigation2',
            executable='saved_points_to_nav_goal.py',
            name='saved_points_to_nav_goal',
            output='screen',
            parameters=[{
                'points_yaml': clicked_points_yaml,
                'burger_namespace': 'tb3',
                'waffle_namespace': 'wf2',
            }],
        ),

        # Node(
        #     package='turtlebot3_navigation2',
        #     executable='waypoint_grid_dispatcher.py',
        #     name='waypoint_grid_dispatcher',
        #     output='screen',
        #     parameters=[{
        #         'map_yaml': '/home/user/maps/pinky_map.yaml',
        #         'grid_size_m': 1.0,
        #         'robot_radius_m': 0.20,
        #         'burger_namespace': 'tb3',
        #         'waffle_namespace': 'wf2',
        #     }]
        # ),

        # ── RViz Publish Point 좌표 저장 노드 ─────────────────────────────
        # /clicked_point를 받아서 clicked_points_yaml에 순서대로 저장
        # 이 노드는 로봇을 주행시키지 않고 좌표만 저장함
        Node(
            package='pinky_navigation',
            executable='clicked_point_saver.py',
            name='clicked_point_saver',
            output='screen',
            parameters=[{
                'save_path': clicked_points_yaml,
            }],
            remappings=[
                ('/clicked_point', clicked_point_topic),
            ],
        ),

        # ── Burger(tb3): AMCL + Nav2 ─────────────────────────────────────
        GroupAction([
            PushRosNamespace('tb3'),

            Node(
                package='nav2_amcl',
                executable='amcl',
                name='amcl',
                output='screen',
                parameters=[
                    burger_configured_params,
                    {
                        'use_sim_time': use_sim_time,
                        'map_topic': '/map',
                        'global_frame_id': 'map',
                        'odom_frame_id': 'tb3/odom',
                        'base_frame_id': 'tb3/base_footprint',
                        'scan_topic': 'scan',
                        'tf_broadcast': True,
                    }
                ],
            ),

            Node(
                package='nav2_lifecycle_manager',
                executable='lifecycle_manager',
                name='lifecycle_manager_localization',
                output='screen',
                parameters=[{
                    'use_sim_time': use_sim_time,
                    'autostart': True,
                    'node_names': ['amcl'],
                }],
            ),

            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(navigation_launch_path),
                launch_arguments={
                    'namespace': 'tb3',
                    'use_sim_time': use_sim_time,
                    'params_file': burger_configured_params,
                    'autostart': 'true',
                }.items()
            ),
        ]),

        # ── Waffle(wf2): AMCL + Nav2 ─────────────────────────────────────
        GroupAction([
            PushRosNamespace('wf2'),

            Node(
                package='nav2_amcl',
                executable='amcl',
                name='amcl',
                output='screen',
                parameters=[
                    waffle_configured_params,
                    {
                        'use_sim_time': use_sim_time,
                        'map_topic': '/map',
                        'global_frame_id': 'map',
                        'odom_frame_id': 'wf2/odom',
                        'base_frame_id': 'wf2/base_footprint',
                        'scan_topic': 'scan',
                        'tf_broadcast': True,
                    }
                ],
            ),

            Node(
                package='nav2_lifecycle_manager',
                executable='lifecycle_manager',
                name='lifecycle_manager_localization',
                output='screen',
                parameters=[{
                    'use_sim_time': use_sim_time,
                    'autostart': True,
                    'node_names': ['amcl'],
                }],
            ),

            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(navigation_launch_path),
                launch_arguments={
                    'namespace': 'wf2',
                    'use_sim_time': use_sim_time,
                    'params_file': waffle_configured_params,
                    'autostart': 'true',
                }.items()
            ),
        ]),

        # ── RViz ─────────────────────────────────────────────────────────
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_config_file],
            parameters=[{'use_sim_time': use_sim_time}],
            output='screen'
        ),
    ])