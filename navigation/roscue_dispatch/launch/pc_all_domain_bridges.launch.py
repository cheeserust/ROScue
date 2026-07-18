#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def default_config_path(filename: str) -> str:
    return os.path.join(
        get_package_share_directory('roscue_dispatch'),
        'bridge',
        filename,
    )


def make_domain_bridge_node(name: str, config_arg_name: str) -> Node:
    return Node(
        package='domain_bridge',
        executable='domain_bridge',
        name=name,
        output='screen',
        arguments=[LaunchConfiguration(config_arg_name)],
    )


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'pinky13_to_pc10_config',
            default_value=default_config_path('pinky13_to_pc10_bridge.yaml'),
        ),
        DeclareLaunchArgument(
            'wf2_15_to_pc10_config',
            default_value=default_config_path('wf2_15_to_pc10_bridge.yaml'),
        ),
        DeclareLaunchArgument(
            'wf1_14_to_pc10_config',
            default_value=default_config_path('wf1_14_to_pc10_bridge.yaml'),
        ),
        DeclareLaunchArgument(
            'pc10_to_wf2_15_config',
            default_value=default_config_path('pc10_to_wf2_15_bridge.yaml'),
        ),
        DeclareLaunchArgument(
            'pc10_to_wf1_14_config',
            default_value=default_config_path('pc10_to_wf1_14_bridge.yaml'),
        ),

        make_domain_bridge_node('pinky13_to_pc10_bridge', 'pinky13_to_pc10_config'),
        make_domain_bridge_node('wf2_15_to_pc10_bridge', 'wf2_15_to_pc10_config'),
        make_domain_bridge_node('wf1_14_to_pc10_bridge', 'wf1_14_to_pc10_config'),
        make_domain_bridge_node('pc10_to_wf2_15_bridge', 'pc10_to_wf2_15_config'),
        make_domain_bridge_node('pc10_to_wf1_14_bridge', 'pc10_to_wf1_14_config'),
    ])