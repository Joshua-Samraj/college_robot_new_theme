import serial
import time

# --- Configuration (CHANGE THESE) ---
# 1. Replace 'COM3' with the correct port for your Arduino (e.g., 'COM4' on Windows, or '/dev/ttyUSB0' on Linux/Mac)
# 2. Ensure the baudrate matches the one set in the Arduino code (e.g., 9600)
SERIAL_PORT = 'COM12'
BAUD_RATE = 9600
# ------------------------------------

try:
    # Open the serial port connection
    # A small delay is often necessary for the Arduino to reset after the connection opens
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print(f"Connected to Arduino on {SERIAL_PORT} at {BAUD_RATE} baud.")

    # The signal you want to send (e.g., '1' to turn something ON)
    signal_to_send = 'H'
    
    # Send the signal to the Arduino. It must be converted to bytes first.
    ser.write(signal_to_send.encode('utf-8'))
    print(f"Sent signal: '{signal_to_send}'")

    # (Optional) You can listen for a response from the Arduino here
    # response = ser.readline().decode('utf-8').strip()
    # print(f"Arduino response: {response}")

except serial.SerialException as e:
    print(f"Error: Could not open serial port {SERIAL_PORT}. Make sure the port is correct and not in use.")
    print(f"Details: {e}")

finally:
    # Always close the serial port
    if 'ser' in locals() and ser.is_open:
        ser.close()
        print("Serial connection closed.")