from flask import Flask, request, jsonify
from flask_cors import CORS
import serial
import time
import os


from Follow_me_function import main
from eye_controll import send_command as eye_controll
from movement_controller import send_command as motor_controll
import threading as td 

# --- CONFIGURATION (UPDATED FOR TWO ARDUINOS) ---
MOTOR_SERIAL_PORT = 'Com23'
FACE_SERIAL_PORT = 'COM12'
SERIAL_BAUDRATE = 9600
# ------------------------------------------------

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}})


ser_motor = None
ser_face = None

def blink():
    """Continuously sends a blink command 'B' to the face controller."""
    
    while True:
        try:
            eye_controll('B')
            
            time.sleep(5) 
        except Exception as e:
            print(f"⚠️ Error in blink thread: {e}")
            time.sleep(5)
            

blink_thread = td.Thread(target=blink, daemon=True) 
blink_thread.start()

try:
    ser_motor = serial.Serial(MOTOR_SERIAL_PORT, SERIAL_BAUDRATE, timeout=1)
    print(f"✅ Successfully connected to Motor Arduino on {MOTOR_SERIAL_PORT} at {SERIAL_BAUDRATE} baud.")
except serial.SerialException as e:
    print(f"⚠️ Error: Could not open Motor serial port {MOTOR_SERIAL_PORT}. Details: {e}")
    ser_motor = None

try:
    ser_face = serial.Serial(FACE_SERIAL_PORT, SERIAL_BAUDRATE, timeout=1)
    print(f"✅ Successfully connected to Face Arduino on {FACE_SERIAL_PORT} at {SERIAL_BAUDRATE} baud.")
except serial.SerialException as e:
    print(f"⚠️ Error: Could not open Face serial port {FACE_SERIAL_PORT}. Details: {e}")
    ser_face = None


MOTOR_MAP = {
    '3': '3', 
    'r': 'b', 
    '2': '4', 
    '4': '2', 
    '1': '5', 
    '5': '1'  
}

FACE_MAP = {
    'H': 'H',  
    'B': 'B', 
    'r': 'e'  
}

CONTROL_MAP = {
    's': 's'  # Start/Stop toggle (controls the motor controller)
}

# --- Helper Function for Serial Communication (FIXED) ---

def _send_serial_command(cmd, translation_map, endpoint_name, target_id):
    """
    Translates command, calls the appropriate external function (motor/eye), 
    and returns a Flask response.
    """
    
    # Translate the command from the client's simple key to the Arduino's expected character
    command_to_send = translation_map.get(cmd, cmd)
    
    try:
        if target_id == "motor":
            # Assuming motor_controll handles its own connection and returns a bool/status
            motor_controll(command_to_send) 
            message = f"Command '{command_to_send}' sent via Motor API."
            
        elif target_id == "face":
            # Assuming eye_controll handles its own connection and returns a bool/status
            eye_controll(command_to_send) 
            message = f"Command '{command_to_send}' sent via Face API."
            
        else:
            return jsonify({"status": "error", "message": f"Invalid target identifier: {target_id}"}), 500
            
        print(f"✅ Executed command: {command_to_send} (from client command '{cmd}')")
        
        # CRITICAL FIX: Ensure a JSON response is returned on success
        return jsonify({
            "status": "success",
            "message": message
        })

    except Exception as e:
        # Catch any failure from the external control functions
        print(f"⚠️ Error executing command for {target_id}: {e}")
        return jsonify({"status": "error", "message": f"Failed to execute command for {target_id}. Details: {e}"}), 500

# --- API Endpoints (ARGUMENTS FIXED) ---

@app.route('/api/motor/command', methods=['POST'])
def handle_motor_command():
    data = request.get_json()
    cmd = data.get('command')
    
    if not cmd:
        return jsonify({"status": "error", "message": "Invalid request. 'command' key missing."}), 400
    
    print("\n" + "="*30)
    print(f"⚙️ MOTOR Endpoint Hit")
    print(f"Received Command: '{cmd}'")
    print("="*30)
    
    if cmd not in MOTOR_MAP:
        return jsonify({"status": "error", "message": f"Invalid motor command: {cmd}"}), 400

    # FIX: Pass the string identifier "motor"
    return _send_serial_command(cmd, MOTOR_MAP, "Motor API", "motor")

@app.route('/api/face/command', methods=['POST'])
def handle_face_command():
    data = request.get_json()
    cmd = data.get('command')
    
    if not cmd:
        return jsonify({"status": "error", "message": "Invalid request. 'command' key missing."}), 400
    
    print("\n" + "="*30)
    print(f"😊 FACE Endpoint Hit")
    print(f"Received Command: '{cmd}'")
    print("="*30)
    
    if cmd not in FACE_MAP:
        return jsonify({"status": "error", "message": f"Invalid face command: {cmd}"}), 400

    # CORRECT: Pass the string identifier "face"
    return _send_serial_command(cmd, FACE_MAP, "Face API", "face")


@app.route('/api/command', methods=['POST'])
def handle_command():
    data = request.get_json()
    cmd = data.get('command')
    
    if not cmd:
        return jsonify({"status": "error", "message": "Invalid request. 'command' key missing."}), 400
    
    print("\n" + "="*30)
    print(f"🛰️ GENERAL Endpoint Hit")
    print(f"Received Command: '{cmd}'")
    print("="*30)

    # --- SPECIAL CASE: Start tracking window ---
    if cmd.lower() == "follow_me":
        # Check if the required serial object is available for the blocking 'main' function
        if ser_motor and ser_motor.is_open:
            try:
                # CRITICAL: Pass the active serial object 'ser_motor' to the main function.
                # If main() is blocking, this API call will block until it returns.
                main(ser_motor) 
                print("🚀 Follow Me mode activated.")
                return jsonify({"status": "success", "message": "Follow Me window launched."})
            except Exception as e:
                print(f"❌ Error launching follow_me.py: {e}")
                return jsonify({"status": "error", "message": f"Failed to launch follow_me.py: {e}"}), 500
        else:
            return jsonify({"status": "error", "message": "Serial port for Motor control is not available to start Follow Me mode."}), 503

    # --- Normal control command handling (e.g., 's' for Start/Stop) ---
    if cmd not in CONTROL_MAP:
        return jsonify({"status": "error", "message": f"Invalid control command: {cmd}"}), 400
        
    # FIX: Pass the string identifier "motor"
    return _send_serial_command(cmd, CONTROL_MAP, "Control API", "motor")


if __name__ == '__main__':
    print("🌐 Starting HTTP API server at http://127.0.0.1:5000")
    # Set debug to False for production use
    # use_reloader=False is set to prevent double initialization of serial ports
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
