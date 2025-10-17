import cv2
import win32gui
import win32con

def set_window_always_on_top(window_name):
    hwnd = win32gui.FindWindow(None, window_name)
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                         win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

# Create an OpenCV window


# Set the window always on top


cv2.waitKey(0)
cv2.destroyAllWindows()
