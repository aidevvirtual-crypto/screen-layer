"""Camera tracker: finds ArUco markers shown on device screens and maps them to table coordinates (cm).

Table calibration markers (print them, see /markers): id 0=top-left, 1=top-right, 2=bottom-right, 3=bottom-left.
The table size given on the command line is the distance between those marker CENTERS.
Device markers start at id 10 and are drawn centered and upright on each screen.
"""
import math
import threading
import time

import cv2
import numpy as np

DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
TABLE_IDS = (0, 1, 2, 3)


def marker_png(marker_id, size=400):
    img = cv2.aruco.generateImageMarker(DICT, int(marker_id), size)
    return cv2.imencode(".png", img)[1].tobytes()


class Tracker(threading.Thread):
    def __init__(self, source, table_w, table_h, on_detect):
        super().__init__(daemon=True)
        self.source = int(source) if str(source).isdigit() else source
        self.table_w, self.table_h = table_w, table_h
        self.on_detect = on_detect  # called from this thread with list of detections
        self.H = None               # image px -> table cm
        self.table_locked = False   # True once the 4 table markers were seen
        self.jpeg = None
        self.lock = threading.Lock()
        params = cv2.aruco.DetectorParameters()
        params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        self.detector = cv2.aruco.ArucoDetector(DICT, params)

    def run(self):
        while True:
            cap = cv2.VideoCapture(self.source)
            if not cap.isOpened():
                print(f"[tracker] cannot open camera {self.source!r}, retrying in 2s")
                time.sleep(2)
                continue
            print(f"[tracker] camera {self.source!r} opened")
            while True:
                ok, frame = cap.read()
                if not ok:
                    print("[tracker] camera read failed, reopening")
                    break
                self.process(frame)
            cap.release()
            time.sleep(1)

    def process(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)
        found = {} if ids is None else {int(i): c.reshape(4, 2) for i, c in zip(ids.flatten(), corners)}

        # Table homography from the 4 corner markers (cached once seen).
        if all(i in found for i in TABLE_IDS):
            src = np.float32([found[i].mean(axis=0) for i in TABLE_IDS])
            dst = np.float32([[0, 0], [self.table_w, 0], [self.table_w, self.table_h], [0, self.table_h]])
            self.H = cv2.getPerspectiveTransform(src, dst)
            self.table_locked = True
        if self.H is None:  # fallback: whole camera frame == table width, no perspective correction
            s = self.table_w / frame.shape[1]
            self.H = np.float64([[s, 0, 0], [0, s, 0], [0, 0, 1]])

        dets = []
        for mid, c in found.items():
            if mid in TABLE_IDS:
                continue
            t = cv2.perspectiveTransform(c.reshape(-1, 1, 2).astype(np.float64), self.H).reshape(4, 2)
            center = t.mean(axis=0)
            vx, vy = t[1] - t[0]  # marker top edge (TL->TR) == screen +x axis
            side = float(np.mean([np.linalg.norm(t[k] - t[(k + 1) % 4]) for k in range(4)]))
            dets.append({"id": mid, "x": float(center[0]), "y": float(center[1]),
                         "a": math.atan2(vy, vx), "side": side})
        if dets:
            self.on_detect(dets)

        # Debug preview
        if ids is not None:
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)
        label = "table: calibrated" if self.table_locked else "table: NOT calibrated (show markers 0-3)"
        cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        small = cv2.resize(frame, (640, int(640 * frame.shape[0] / frame.shape[1])))
        with self.lock:
            self.jpeg = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 70])[1].tobytes()

    def latest_jpeg(self):
        with self.lock:
            return self.jpeg
