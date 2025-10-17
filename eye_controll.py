import serial
import time

ser = serial.Serial('Com12', 9600, timeout=1)  # Change COM6 to your Arduino's port
time.sleep(2)  # Wait for' the serial connection to initialize

def send_command(command):
    command_str = str(command)
    print(f"Sending command: {command_str}")
    ser.write(command_str.encode())    # Send command to Arduino