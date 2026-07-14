import os
import sys
import urllib.request
import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions,
    RunningMode,
    drawing_utils,
    drawing_styles,
    HandLandmarksConnections,
)
from mediapipe import Image as mpImage, ImageFormat
import numpy as np

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"

def ensure_model(path):
    if os.path.exists(path):
        return path
    print(f"[HGC] Downloading AI model...")
    urllib.request.urlretrieve(MODEL_URL, path)
    return path

class HandTracker:
    def __init__(self, max_hands=2, detection_con=0.5, track_con=0.5):
        base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        model = os.path.join(base, "hand_landmarker.task")
        if not os.path.exists(model):
            urllib.request.urlretrieve(MODEL_URL, model)
        opts = HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=model),
            running_mode=RunningMode.IMAGE,
            num_hands=max_hands,
            min_hand_detection_confidence=detection_con,
            min_tracking_confidence=track_con,
        )
        self.detector = HandLandmarker.create_from_options(opts)
        self.results = None

    def find_hands(self, frame, draw=True):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.results = self.detector.detect(mpImage(image_format=ImageFormat.SRGB, data=rgb))

        if draw and self.results and self.results.hand_landmarks:
            for hl in self.results.hand_landmarks:
                drawing_utils.draw_landmarks(
                    frame, hl, HandLandmarksConnections.HAND_CONNECTIONS,
                    drawing_styles.get_default_hand_landmarks_style(),
                    drawing_styles.get_default_hand_connections_style())
        return frame

    def get_positions(self, frame, hand_idx=0):
        h, w, _ = frame.shape
        out = []
        if self.results and self.results.hand_landmarks:
            if hand_idx < len(self.results.hand_landmarks):
                for i, lm in enumerate(self.results.hand_landmarks[hand_idx]):
                    out.append((i, int(lm.x * w), int(lm.y * h)))
        return out

    def get_distance(self, p1, p2):
        return np.linalg.norm(np.array(p1[1:3]) - np.array(p2[1:3]))

    def fingers_up(self, lm):
        if not lm or len(lm) < 21:
            return []
        f = [1 if lm[4][1] > lm[3][1] else 0]
        for t in [8, 12, 16, 20]:
            f.append(1 if lm[t][2] < lm[t - 2][2] else 0)
        return f