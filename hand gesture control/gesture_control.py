import pyautogui
import numpy as np
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

pyautogui.FAILSAFE = False

try:
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    vol_range = volume.GetVolumeRange()
    vol_min, vol_max = vol_range[0], vol_range[1]
except Exception:
    volume = None
    vol_min, vol_max = -65.25, 0.0

screen_w, screen_h = pyautogui.size()

click_lock = False

prev_x = prev_y = None

def reset_cursor():
    global prev_x, prev_y
    prev_x = prev_y = None

def control_cursor(lm_index, frame_w, frame_h, reacquired=False):
    global prev_x, prev_y
    x = lm_index[1]
    y = lm_index[2]
    if prev_x is None or reacquired:
        prev_x, prev_y = x, y
        if reacquired:
            return
    dx = (x - prev_x) * screen_w / frame_w
    dy = (y - prev_y) * screen_h / frame_h
    prev_x, prev_y = x, y
    pyautogui.moveRel(int(dx), int(dy))

def pinch_click(dist, threshold=35, side="left"):
    global click_lock
    if dist < threshold and not click_lock:
        click_lock = True
        if side == "left":
            pyautogui.click()
        else:
            pyautogui.rightClick()
        return "click"
    elif dist >= threshold:
        click_lock = False
    return None

def set_volume(dist, min_dist=20, max_dist=150):
    if volume is None:
        return
    vol = np.interp(dist, (min_dist, max_dist), (vol_min, vol_max))
    volume.SetMasterVolumeLevel(vol, None)
    return np.interp(dist, (min_dist, max_dist), (0, 100))

def scroll(fingers_up, prev_fingers_up=None):
    if prev_fingers_up == [0, 1, 1, 0, 0]:
        pyautogui.scroll(-3)
        return "scrolling down"
    elif prev_fingers_up == [0, 1, 0, 0, 0]:
        pyautogui.scroll(3)
        return "scrolling up"
    return None

def take_screenshot():
    ss = pyautogui.screenshot()
    ss.save(f"screenshot.png")
    return "screenshot taken!"
