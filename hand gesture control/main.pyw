import cv2
import pyautogui
import time
import numpy as np
import sys
from hand_tracker import HandTracker
from gesture_control import (
    control_cursor, pinch_click, set_volume, take_screenshot, reset_cursor
)

pyautogui.FAILSAFE = False

def log(msg):
    print(f"[HGC] {msg}")
    sys.stdout.flush()

log("--- Hand Gesture Control Starting ---")

try:
    val = input("  Detection confidence (0.1 - 1.0, default=0.5): ").strip()
    det_con = float(val) if val else 0.5
    det_con = max(0.1, min(1.0, det_con))
except:
    det_con = 0.5

log(f"Opening camera (confidence={det_con})...")
cap = None
for idx in range(3):
    for b in [cv2.CAP_DSHOW, cv2.CAP_MSMF, None]:
        try:
            c = cv2.VideoCapture(idx) if b is None else cv2.VideoCapture(idx, b)
            if c.isOpened():
                cap = c
                break
            c.release()
        except:
            pass
    if cap:
        break
if not cap:
    log("ERROR: Camera failed!")
    input("Press Enter...")
    sys.exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
log(f"OK - {int(cap.get(3))}x{int(cap.get(4))}")

log("Loading AI...")
tracker = HandTracker(max_hands=2, detection_con=det_con, track_con=det_con)
log("AI loaded!")

modes = ["CURSOR", "VOLUME", "MEDIA", "RECTANGLE"]
mcolors = [(0, 215, 255), (136, 255, 0), (255, 68, 255), (255, 180, 50)]
mode = 0
status = ""
status_t = 0
vol_pct = 0
ss_cd = 0
font = cv2.FONT_HERSHEY_DUPLEX
prev_t = time.time()
fps_buf = []
rect_t = 0.0
mode_cd = 0
mode_f2_held = False

log("Ready!")
print()
print("  [1] CURSOR  [2] VOLUME  [3] MEDIA  [4] RECTANGLE")
print("  [Q] quit  [S] screenshot")
print()

cv2.namedWindow("Hand Gesture Control", cv2.WINDOW_NORMAL)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    t = time.time()
    dt = t - prev_t
    prev_t = t
    if dt > 0:
        fps_buf.append(1 / dt)
        if len(fps_buf) > 15:
            fps_buf.pop(0)
    fps = sum(fps_buf) / len(fps_buf) if fps_buf else 0

    frame = tracker.find_hands(frame, draw=True)

    lm = tracker.get_positions(frame, 0)
    lm2 = tracker.get_positions(frame, 1)
    f = tracker.fingers_up(lm)
    f2 = tracker.fingers_up(lm2)
    hand_detected = len(lm) >= 21
    hand_reacquired = hand_detected and not getattr(tracker, '_hand_was', False)
    tracker._hand_was = hand_detected

    # CURSOR
    if mode == 0 and len(lm) >= 21:
        control_cursor(lm[8], w, h, hand_reacquired)
        if pinch_click(tracker.get_distance(lm[4], lm[8])) == "click":
            status, status_t = "CLICK!", t

    # VOLUME
    elif mode == 1 and len(lm) >= 21:
        v = set_volume(tracker.get_distance(lm[4], lm[8]))
        if v is not None:
            vol_pct = v
            status, status_t = f"VOL: {int(v)}%", t

    # MEDIA
    elif mode == 2 and len(lm) >= 21:
        if f[1] == 1 and f[2] == 1 and f[3] == 0 and f[4] == 0:
            pyautogui.scroll(-60)
            status, status_t = "SCROLL DOWN", t
        elif f[1] == 1 and f[2] == 0 and f[3] == 0 and f[4] == 0:
            pyautogui.scroll(60)
            status, status_t = "SCROLL UP", t
        elif sum(f) == 0 and t - ss_cd > 2:
            take_screenshot()
            status, status_t = "SCREENSHOT!", t
            ss_cd = t

    # RECTANGLE: x-ray window (thumb+index of both hands = 4 corners)
    if mode == 3 and len(lm) >= 21 and len(lm2) >= 21:
        tl = (int(lm[8][1]), int(lm[8][2]))
        tr = (int(lm2[8][1]), int(lm2[8][2]))
        br = (int(lm2[4][1]), int(lm2[4][2]))
        bl = (int(lm[4][1]), int(lm[4][2]))
        pts = np.array([tl, tr, br, bl], dtype=np.int32)
        rect_t += 0.1
        pulse = abs(np.sin(rect_t))

        # x-ray inside effect: invert + navy/cyan tint
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        cv2.fillPoly(mask, [pts], 255)
        inv = cv2.bitwise_not(frame).astype(np.float32)
        inv *= np.array([0.8, 0.55, 0.3], dtype=np.float32)
        inv = inv.astype(np.uint8)
        inside = cv2.bitwise_and(inv, inv, mask=mask)
        outside = cv2.bitwise_and(frame, frame, mask=cv2.bitwise_not(mask))
        frame = cv2.add(outside, inside)

        # glowing frame
        thick = max(2, int(3 * pulse + 1))
        cv2.polylines(frame, [pts], True, (255, 140, 20), thick)

        # corner brackets
        cl = int(22 * (0.7 + 0.3 * pulse))
        ice = (255, 255, 220)
        for sx, sy, ex, ey in [
            (tl[0], tl[1], tl[0]+cl, tl[1]), (tl[0], tl[1], tl[0], tl[1]+cl),
            (tr[0], tr[1], tr[0]-cl, tr[1]), (tr[0], tr[1], tr[0], tr[1]+cl),
            (br[0], br[1], br[0]-cl, br[1]), (br[0], br[1], br[0], br[1]-cl),
            (bl[0], bl[1], bl[0]+cl, bl[1]), (bl[0], bl[1], bl[0], bl[1]-cl),
        ]:
            cv2.line(frame, (sx, sy), (ex, ey), ice, thick)

        # scan line
        rx, ry, rw, rh = cv2.boundingRect(pts)
        scan_y = ry + int(rh * abs(np.sin(rect_t * 2)))
        cv2.line(frame, (rx, scan_y), (rx + rw, scan_y), (255, 255, 255), 2)

        # label
        cx = sum(p[0] for p in [tl, tr, br, bl]) // 4
        cy = sum(p[1] for p in [tl, tr, br, bl]) // 4
        cv2.putText(frame, "X-RAY", (cx - 25, cy + 6), font, 0.6, (255, 255, 200), 1)

    # switch mode: right hand 4+ fingers (edge trigger + cooldown)
    f2_visible = bool(lm2 and len(lm2) >= 21)
    f2_raised = f2_visible and sum(f2) >= 4
    if f2_raised and not mode_f2_held and t - mode_cd > 1.0:
        mode = (mode + 1) % len(modes)
        status, status_t = f"MODE: {modes[mode]}", t
        mode_cd = t
        if mode == 0:
            reset_cursor()
        mode_f2_held = True
    if not f2_raised:
        mode_f2_held = False

    # both index tips = screenshot
    if lm and lm2 and len(lm) > 8 and len(lm2) > 8:
        if tracker.get_distance(lm[8], lm2[8]) < 40 and t - ss_cd > 2:
            take_screenshot()
            status, status_t = "SCREENSHOT!", t
            ss_cd = t

    # HUD
    ov = frame.copy()
    cv2.rectangle(ov, (0, 0), (w, 45), (0, 0, 0), -1)
    cv2.addWeighted(ov, 0.25, frame, 0.75, 0, frame)
    cv2.putText(frame, f"MODE: {modes[mode]}", (15, 32), font, 0.65, mcolors[mode], 2)

    if t - status_t < 1.5:
        cv2.putText(frame, status, (15, h - 12), font, 0.5, (0, 255, 255), 2)

    if mode == 1:
        bx, by, bw, bh = w - 220, 6, 200, 20
        cv2.rectangle(frame, (bx, by), (bx+bw, by+bh), (40,40,40), -1)
        cv2.rectangle(frame, (bx, by), (bx+int(bw*vol_pct/100), by+bh), (0,255,136), -1)
        cv2.putText(frame, f"VOL {int(vol_pct)}%", (bx+4, by+15), font, 0.4, (255,255,255), 1)

    for i, (lbl, c) in enumerate([
        ("[1] CURSOR", (0,215,255)),
        ("[2] VOLUME", (136,255,0)),
        ("[3] MEDIA", (255,68,255)),
        ("[4] RECT", (255,200,0)),
    ]):
        x, y = w - 190, 6 + i * 16
        cv2.putText(frame, f"{'>' if i==mode else ' '} {lbl}", (x, y),
                    font, 0.38, c if i==mode else (60,60,60), 1)

    cv2.imshow("Hand Gesture Control", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('s'):
        take_screenshot()
        status, status_t = "SCREENSHOT!", t
    elif ord('1') <= key <= ord('4'):
        mode = key - ord('1')
        status, status_t = f"MODE: {modes[mode]}", t
        if mode == 0:
            reset_cursor()

cap.release()
cv2.destroyAllWindows()
log("Done")
