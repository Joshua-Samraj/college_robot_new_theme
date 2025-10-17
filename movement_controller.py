import serial
import time

ser = serial.Serial('Com23', 9600, timeout=1)  # Change COM6 to your Arduino's port
time.sleep(2)  # Wait for' the serial connection to initialize

def send_command(command):
    command_str = str(command)
    print(f"Sending command: {command_str}")
    ser.write(command_str.encode())    # Send command to Arduino
# # # # ==========================================================================================
# def send_command(command):
#     print(command)


# ==========================================================================================
# try:
#     while True:
#         user_input = input("Enter 'b' to blink, 'r' for random reaction, or 'q' to quit: ")
#         if user_input == 'f':
#             send_command('f')  # Send blink command
#         elif user_input == 'r':
#             send_command('r')  # Send random reaction command
#         elif user_input == 'q':
#             break  # Exit the loop
#         elif user_input == 'h':
#             send_command('h')
#         elif user_input == 's':
#             send_command('s')
#         elif user_input == 'l':
#             send_command('l')
#         else:
#             print("Invalid input! Please try again.")
        

# except KeyboardInterrupt:
#     print("Exiting...")

# finally:
#     ser.close()  # Close the serial port
