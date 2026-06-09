import pygame
import rclpy
from geometry_msgs.msg import Twist

RATE = 20.0
LINEAR = 0.5
ANGULAR = 1.0
STEP = 1.1

def main():
    rclpy.init()
    node = rclpy.create_node('teleop_wasd')
    pub = node.create_publisher(Twist, 'cmd_vel', 10)

    pygame.init()
    screen = pygame.display.set_mode((360, 200))
    pygame.display.set_caption('Pinky WASD teleop')
    font = pygame.font.SysFont(None, 28)
    clock = pygame.time.Clock()

    linear, angular = LINEAR, ANGULAR
    running = True

    try:
        while running and rclpy.ok():
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        linear *= STEP
                        angular *= STEP

                    elif event.key == pygame.K_z:
                        linear /= STEP
                        angular /= STEP

                    elif event.key == pygame.K_ESCAPE:
                        running = False

            keys = pygame.key.get_pressed()

            # =====================================================
            # Linear movement
            # w : forward
            # s : backward
            # =====================================================
            x = 0.0

            if keys[pygame.K_w]:
                x += 1.0

            if keys[pygame.K_s]:
                x -= 1.0

            # =====================================================
            # Angular movement
            # a : left turn
            # d : right turn
            #
            # ROS Twist 기준:
            # angular.z > 0 : left turn
            # angular.z < 0 : right turn
            # =====================================================
            th = 0.0

            if keys[pygame.K_a]:
                th += 1.0

            if keys[pygame.K_d]:
                th -= 1.0

            # =====================================================
            # Backward steering correction
            #
            # 후진 중에는 조향 방향이 체감상 반대로 느껴지므로
            # s+a, s+d 조합에서 회전 방향을 보정한다.
            #
            # w+a : forward left
            # w+d : forward right
            # s+a : backward left
            # s+d : backward right
            # =====================================================
            if x < 0:
                th = -th

            twist = Twist()
            twist.linear.x = x * linear
            twist.angular.z = th * angular
            pub.publish(twist)

            held = ''.join(
                k for k, p in [
                    ('W', keys[pygame.K_w]),
                    ('A', keys[pygame.K_a]),
                    ('S', keys[pygame.K_s]),
                    ('D', keys[pygame.K_d]),
                ]
                if p
            )

            screen.fill((20, 20, 25))

            lines = [
                f'held: {held or "-"}',
                f'linear.x  = {twist.linear.x:+.2f}',
                f'angular.z = {twist.angular.z:+.2f}',
                f'(speed {linear:.2f} / turn {angular:.2f})',
                'q/z speed  esc quit',
            ]

            for i, line in enumerate(lines):
                screen.blit(
                    font.render(line, True, (230, 230, 230)),
                    (20, 20 + i * 32)
                )

            pygame.display.flip()

            rclpy.spin_once(node, timeout_sec=0.0)
            clock.tick(RATE)

    finally:
        # stop on exit
        pub.publish(Twist())

        pygame.quit()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()