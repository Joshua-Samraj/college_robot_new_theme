import cv2
import numpy as np
import pyttsx3
import threading
from movement_controller import send_command
from always_top import set_window_always_on_top
import time


# ------------------------------
# Global Variables
# ------------------------------
previous_command = None
faces = []
selected_face = None
tracker = None
tracking = False
exit_requested = False
exit_button_position = (50, 50, 150, 100)
deselect_button_position = (50, 120, 150, 170)
engine = pyttsx3.init()


def speak(text):
    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[1].id)
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 1.0)
    engine.say(text)
    engine.runAndWait()


# ------------------------------
# Improved Face Detection using DNN
# ------------------------------
def detect_faces_dnn(frame, net, conf_threshold=0.6):
    """Detect faces using OpenCV DNN (SSD ResNet model)."""
    h, w = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0,
                                 (300, 300), (104.0, 177.0, 123.0))
    net.setInput(blob)
    detections = net.forward()
    faces = []
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > conf_threshold:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (x, y, x2, y2) = box.astype("int")
            faces.append((x, y, x2 - x, y2 - y))
    return faces


def initialize_tracker(frame, face_box):
    tracker = cv2.TrackerCSRT_create()
    tracker.init(frame, tuple(face_box))
    return tracker


def check_and_send_command(new_command):
    global previous_command
    if new_command != previous_command:
        print(new_command)
        send_command(new_command)
        previous_command = new_command


def select_face(event, x, y, flags, param):
    global selected_face, faces, tracking, tracker, exit_requested
    frame = param
    if event == cv2.EVENT_LBUTTONDOWN:
        # Exit Button
        if exit_button_position[0] < x < exit_button_position[2] and exit_button_position[1] < y < exit_button_position[3]:
            print("Exit button clicked!")
            exit_requested = True
            return
        # Deselect Button
        if deselect_button_position[0] < x < deselect_button_position[2] and deselect_button_position[1] < y < deselect_button_position[3]:
            print("Deselect button clicked!")
            tracking = False
            tracker = None
            selected_face = None
            threading.Thread(target=speak, args=("Face deselected. Ready to select another face.",)).start()
            check_and_send_command('s')
            return
        # Face selection
        for (fx, fy, fw, fh) in faces:
            if fx < x < fx + fw and fy < y < fy + fh:
                selected_face = (fx, fy, fw, fh)
                tracker = initialize_tracker(frame, selected_face)
                tracking = True
                break


def track_face(tracker, frame):
    success, bbox = tracker.update(frame)
    if success:
        (x, y, w, h) = [int(v) for v in bbox]
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        center_x = x + w // 2
        width = frame.shape[1]
        section_width = width // 5

        if center_x < section_width:
            check_and_send_command('5')
            return "FAR LEFT", frame
        elif center_x < 2 * section_width:
            check_and_send_command('4')
            return "LEFT", frame
        elif center_x < 3 * section_width:
            check_and_send_command('3')
            return "CENTER", frame
        elif center_x < 4 * section_width:
            check_and_send_command('2')
            return "RIGHT", frame
        else:
            check_and_send_command('1')
            return "FAR RIGHT", frame
    return "LOST", frame


# ------------------------------
# MAIN
# ------------------------------
def main():
    global faces, tracker, tracking, selected_face, exit_requested

    threading.Thread(target=speak, args=("Please select the face you want to track by clicking on it.",)).start()

    # Load DNN Model
    import os

    modelFile = os.path.join("models", "res10_300x300_ssd_iter_140000 (1).caffemodel")
    configFile = os.path.join("models", "deploy.prototxt")

    if not os.path.exists(modelFile) or not os.path.exists(configFile):
        print("❌ Model files not found! Please download them from:")
        print("https://github.com/opencv/opencv/tree/master/samples/dnn/face_detector")
        exit()
        
    net = cv2.dnn.readNetFromCaffe(configFile, modelFile)


    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cv2.namedWindow("Face Selection and Tracking")

    while True:
        ret, frame = cap.read()
        frame = cv2.flip(frame, 1)
        if not ret:
            break

        # Face Detection
        if not tracking:
            faces = detect_faces_dnn(frame, net)
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

        # Tracking
        if tracking and selected_face is not None:
            position, frame = track_face(tracker, frame)
            if position == "LOST":
                print("Lost track of the face.")
                threading.Thread(target=speak, args=("Face detection was lost. Please select again.",)).start()
                tracking = False
                tracker = None
                check_and_send_command('s')

        # Exit & Deselect Buttons
        cv2.rectangle(frame, (exit_button_position[0], exit_button_position[1]),
                      (exit_button_position[2], exit_button_position[3]), (0, 0, 255), -1)
        cv2.putText(frame, 'Exit', (exit_button_position[0] + 10, exit_button_position[1] + 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        cv2.rectangle(frame, (deselect_button_position[0], deselect_button_position[1]),
                      (deselect_button_position[2], deselect_button_position[3]), (0, 255, 0), -1)
        cv2.putText(frame, 'Deselect', (deselect_button_position[0] + 5, deselect_button_position[1] + 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow("Face Selection and Tracking", frame)
        set_window_always_on_top('Face Selection and Tracking')
        cv2.setMouseCallback("Face Selection and Tracking", select_face, frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        if exit_requested:
            print("Exiting face tracking, returning to main program...")
            threading.Thread(target=speak, args=("Thank you for using face tracking.",)).start()
            check_and_send_command('s')
            exit_requested = False
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
