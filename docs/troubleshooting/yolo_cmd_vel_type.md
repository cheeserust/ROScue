# Troubleshooting: YOLO cmd_vel Type

YOLO follow server가 로봇을 움직이지 못한 문제의 원인과 해결 방법입니다.

---

## Problem

```text
/wf2/cmd_vel topic 이름은 맞지만 로봇이 움직이지 않음
```

---

## Cause

```text
Publisher:
  pc_yolo_follow_server
  type: geometry_msgs/msg/Twist

Subscriber:
  turtlebot3_node
  type: geometry_msgs/msg/TwistStamped
```

topic 이름은 같아도 메시지 타입이 다르면 통신되지 않습니다.

---

## Solution

YOLO follow server에서 `/wf2/cmd_vel`에 `geometry_msgs/msg/TwistStamped`를 publish하도록 수정합니다.

```python
from geometry_msgs.msg import TwistStamped

msg = TwistStamped()
msg.header.stamp = node.get_clock().now().to_msg()
msg.twist.linear.x = linear_x
msg.twist.angular.z = angular_z
```

---

## Check

```bash
ros2 topic info -v /wf2/cmd_vel
```

publisher와 subscriber type이 모두 `geometry_msgs/msg/TwistStamped`인지 확인합니다.
