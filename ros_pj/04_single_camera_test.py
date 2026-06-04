# 카메라 1개 정상 동작 확인
import cv2

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("카메라 열기 실패")
    exit()

while True:

    ret, frame = cap.read()

    if not ret:
        break

    cv2.imshow("CAMERA TEST", frame)

    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()

# 종료 : ESC