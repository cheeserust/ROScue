cmake_minimum_required(VERSION 3.10)
project(roscue_interface)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(geometry_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  # Messages
  "msg/YoloEvent.msg"
  "msg/RobotStatus.msg"
  "msg/ArmPositions.msg"
  "msg/MainToNavMsg.msg"
  # Services
  "srv/TaskCommandSrv.srv"
  "srv/SetYoloMode.srv"
  "srv/MissionCommand.srv"
  "srv/ManualDone.srv"
  "srv/ArmPose.srv"
  DEPENDENCIES
    builtin_interfaces
    geometry_msgs
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
