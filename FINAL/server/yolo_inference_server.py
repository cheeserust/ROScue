import cv2
import json
import socket
import time
from multiprocessing import Process, Queue, Event, Value
import threading
from ultralytics import YOLO

# ===== 메인 서버(roscue_main_server_node) 설정 =====
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 9999

def publish_data(camera, value):
    """독립된 소켓 전송 함수 (필요할 때만 연결 후 닫기 또는 유지)"""
    payload = (json.dumps({"type": "count", "camera": camera, "count": value}) + "\n").encode("utf-8")
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(2.0)
        client_socket.connect((SERVER_HOST, SERVER_PORT))
        client_socket.sendall(payload)
        client_socket.close()
    except OSError as e:
        print(f"[{camera}] 메인 서버 전송 실패:", e)


def camera_worker(index, name, model_path_a, model_path_b, current_model_flag, global_count, stop_event, frame_queue):
    """
    각 카메라는 완전히 독립된 프로세스에서 작동합니다.
    """

    print(f"[{name}] 모델 로딩 중...")
    model_a = YOLO(model_path_a)
    model_b = YOLO(model_path_b)
    
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        print(f"[{name}] 카메라를 열 수 없습니다.")
        return

    TARGET_CLASS = "open"
    THRESHOLD = 15
    streak = 0
    triggered = False
    
    # 마지막으로 사용한 모델 상태 추적
    last_flag = current_model_flag.value 
    current_model = model_a if last_flag == 0 else model_b

    print(f"[{name}] 추론 시작")
    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)
            continue

        # 메인 프로세스에서 바꾼 모델 신호를 확인
        active_flag = current_model_flag.value
        if active_flag != last_flag:
            current_model = model_a if active_flag == 0 else model_b
            last_flag = active_flag
            print(f"[{name}] 모델이 변경되었습니다! (현재: {'Model A' if active_flag==0 else 'Model B'})")

        # 추론 진행
        result = current_model(frame, verbose=False)[0]
        
        # 메인 화면으로 보낼 이미지 큐에 넣기 (큐가 가득 차면 오래된 것 버림)
        if frame_queue.qsize() < 2:
            frame_queue.put((name, result.plot()))

        # 클래스 카운팅 로직
        detected = {current_model.names[int(c)] for c in result.boxes.cls.tolist()}
        if TARGET_CLASS in detected:
            streak += 1
            if streak >= THRESHOLD and not triggered:
                with global_count.get_lock(): # 멀티프로세스용 Lock 코드
                    global_count.value += 1
                    current_val = global_count.value
                triggered = True
                print(f"[{name}] {TARGET_CLASS} 감지! count = {current_val}")
                publish_data(name, current_val)
        else:
            streak = 0
            triggered = False

    cap.release()
    print(f"[{name}] 프로세스 종료")


def terminal_input_worker(stop_event, cam1_model_flag):
    """터미널 입력을 독립적으로 기다리는 스레드"""
    print("\n[터미널 제어] 명령어 입력 후 Enter를 누르세요. (q: 종료 / a: Model A / b: Model B)")
    while not stop_event.is_set():
        cmd = input().strip().lower()
        if cmd == 'q':
            stop_event.set()
            break
        elif cmd == 'b':
            if cam1_model_flag.value != 1:
                cam1_model_flag.value = 1
                print("[Main] 명령 수신: CAM1을 Model B로 전환합니다.")
        elif cmd == 'a':
            if cam1_model_flag.value != 0:
                cam1_model_flag.value = 0
                print("[Main] 명령 수신: CAM1을 Model A로 전환합니다.")

if __name__ == "__main__":
    # 멀티프로세스 동기화를 위한 객체들
    stop_event = Event()
    global_count = Value('i', 0)          # 공유 정수형 카운터
    cam1_model_flag = Value('i', 0)       # 0: model_a, 1: model_b 의미
    cam0_model_flag = Value('i', 0)       # CAM0도 언제든 바꿀 수 있게 분리 (항상 0 고정 가능)

    # 이미지를 메인으로 받아올 큐
    cam0_queue = Queue(maxsize=2)
    cam1_queue = Queue(maxsize=2)

    model_a_path = "best.pt"
    model_b_path = "best.pt"

    # 프로세스 생성 및 시작
    p0 = Process(TARGET_CLASS=camera_worker, args=(0, "CAM0", model_a_path, model_b_path, cam0_model_flag, global_count, stop_event, cam0_queue))
    p1 = Process(TARGET_CLASS=camera_worker, args=(2, "CAM1", model_a_path, model_b_path, cam1_model_flag, global_count, stop_event, cam1_queue))
    
    p0.start()
    p1.start()


    # 터미널 입력 전용 스레드 시작
    input_thread = threading.Thread(TARGET_CLASS=terminal_input_worker, args=(stop_event, cam1_model_flag), daemon=True)
    input_thread.start()


    print("\n[프로그램 가이드] 'q': 종료 / 'a': CAM1을 Model A로 / 'b': CAM1을 Model B로\n")

    frames = {"CAM0": None, "CAM1": None}

    try:
        while not stop_event.is_set():
            while not cam0_queue.empty():
                _, frames["CAM0"] = cam0_queue.get()
            while not cam1_queue.empty():
                _, frames["CAM1"] = cam1_queue.get()

            for name, img in frames.items():
                if img is not None:
                    cv2.imshow(name, img)

            cv2.waitKey(1)

    except KeyboardInterrupt:
        stop_event.set()

    # 프로세스 종료 대기
    p0.join()
    p1.join()
    
    cv2.destroyAllWindows()
    print("최종 count =", global_count.value)