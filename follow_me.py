import flask
import numpy as np
import cv2
import base64
import time

# Initialize the Flask application
app = flask.Flask(__name__)

# --- MODEL LOADING (remains the same) ---
prototxt_path = "deploy.prototxt"
caffe_model_path = "res10_300x300_ssd_iter_140000.caffemodel"
net = cv2.dnn.readNetFromCaffe(prototxt_path, caffe_model_path)

# --- State Management Variables ---
STATE = "SEARCHING"
lock_start_time = None
tracker = None # NEW: This will hold the CSRT tracker object
LOCK_DURATION = 3  # seconds

@app.route("/")
def index():
    return flask.render_template("index.html")

@app.route("/deselect", methods=["POST"])
def deselect():
    """Resets the state back to SEARCHING."""
    global STATE, lock_start_time, tracker
    STATE = "SEARCHING"
    lock_start_time = None
    tracker = None # Reset the tracker object
    print("State reset to SEARCHING")
    return flask.jsonify({"status": "reset successful"})

@app.route("/process-image", methods=["POST"])
def process_image():
    global STATE, lock_start_time, tracker
    
    data = flask.request.get_json()
    image_data_url = data['image']
    header, encoded_data = image_data_url.split(',', 1)
    decoded_image = base64.b64decode(encoded_data)
    nparr = np.frombuffer(decoded_image, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    (h, w) = img.shape[:2]

    # Define the central selection box
    select_w, select_h = 150, 200
    select_x = (w - select_w) // 2
    select_y = (h - select_h) // 2
    selection_box = (select_x, select_y, select_x + select_w, select_y + select_h)

    if STATE == "SEARCHING" or STATE == "LOCKING":
        # Face detection logic remains the same
        blob = cv2.dnn.blobFromImage(cv2.resize(img, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))
        net.setInput(blob)
        detections = net.forward()
        all_faces = []
        for i in range(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > 0.5:
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                all_faces.append(box.astype("int"))

        if STATE == "SEARCHING":
            cv2.rectangle(img, (selection_box[0], selection_box[1]), (selection_box[2], selection_box[3]), (0, 0, 255), 2)
            face_in_box = False
            for (startX, startY, endX, endY) in all_faces:
                cv2.rectangle(img, (startX, startY), (endX, endY), (0, 255, 0), 2)
                face_center_x = (startX + endX) // 2
                face_center_y = (startY + endY) // 2
                if selection_box[0] < face_center_x < selection_box[2] and selection_box[1] < face_center_y < selection_box[3]:
                    face_in_box = True
            if face_in_box:
                STATE = "LOCKING"
                lock_start_time = time.time()

        elif STATE == "LOCKING":
            elapsed_time = time.time() - lock_start_time
            cv2.rectangle(img, (selection_box[0], selection_box[1]), (selection_box[2], selection_box[3]), (0, 255, 255), 2)
            cv2.putText(img, f"Locking... {int(elapsed_time)}s", (selection_box[0], selection_box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            face_in_box = False
            potential_tracked_box = None
            for (startX, startY, endX, endY) in all_faces:
                cv2.rectangle(img, (startX, startY), (endX, endY), (0, 255, 0), 2)
                face_center_x = (startX + endX) // 2
                face_center_y = (startY + endY) // 2
                if selection_box[0] < face_center_x < selection_box[2] and selection_box[1] < face_center_y < selection_box[3]:
                    face_in_box = True
                    potential_tracked_box = (startX, startY, endX, endY)
            if not face_in_box:
                STATE = "SEARCHING"
                lock_start_time = None
            elif elapsed_time >= LOCK_DURATION:
                STATE = "LOCKED"
                # --- NEW: Initialize the CSRT Tracker ---
                (x1, y1, x2, y2) = potential_tracked_box
                face_box_wh = (x1, y1, x2 - x1, y2 - y1) # Convert to (x, y, w, h)
                tracker = cv2.TrackerCSRT_create()
                tracker.init(img, face_box_wh)

    # --- State: LOCKED (Completely new CSRT tracking logic) ---
    elif STATE == "LOCKED":
        if tracker is None:
            STATE = "SEARCHING" # Safety check
        else:
            # Update the tracker
            success, bbox = tracker.update(img)
            
            if success:
                # Draw the bounding box
                (x, y, w, h) = [int(v) for v in bbox]
                cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
                cv2.putText(img, "LOCKED (CSRT)", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            else:
                # If tracking fails, go back to searching for a new face
                print("CSRT tracking failed.")
                STATE = "SEARCHING"
                tracker = None

    # --- Encode and send the final image and state ---
    _, buffer = cv2.imencode('.jpg', img)
    processed_image_b64 = base64.b64encode(buffer).decode('utf-8')
    processed_image_data_url = f"data:image/jpeg;base64,{processed_image_b64}"
    return flask.jsonify({
        "processed_image": processed_image_data_url,
        "state": STATE
    })

if __name__ == "__main__":
    app.run(debug=True)