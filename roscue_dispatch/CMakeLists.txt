cmake_minimum_required(VERSION 3.8)
project(roscue_dispatch)

find_package(ament_cmake REQUIRED)

install(PROGRAMS
  scripts/multi_robot_point_dispatcher.py
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY launch bridge
  DESTINATION share/${PROJECT_NAME}
)

ament_package()