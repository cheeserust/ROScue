# 웹캠 2개를 동시에 사용할 수 있는지 확인 (가장 중요)
import cv2

cam1 = cv2.VideoCapture(0)
cam2 = cv2.VideoCapture(1)

while True:

    ret1, frame1 = cam1.read()
    ret2, frame2 = cam2.read()

    if ret1:
        cv2.imshow("CAM1", frame1)

    if ret2:
        cv2.imshow("CAM2", frame2)

    if cv2.waitKey(1) == 27:
        break

cam1.release()
cam2.release()

cv2.destroyAllWindows()

# 정상 출력
# CAM1 영상 출력
# CAM2 영상 출력
# 성공시 USB 허브 대역폭은 일단 통과