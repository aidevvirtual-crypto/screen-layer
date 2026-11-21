"""Camera tracker: finds ArUco markers shown on device screens and maps them to table coordinates (cm).

Table calibration: in the control panel the user clicks the 4 corners of the table area on the camera
preview (top-left, top-right, bottom-right, bottom-left) and enters its size in cm. No printed markers.
Device markers start at id 10 and are drawn centered and upright on each screen.
"""
import math
import threading
import time

import cv2
import numpy as np

DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)


def marker_png(marker_id, size=400):
    img = cv2.aruco.generateImageMarker(DICT, int(marker_id), size)
    return cv2.imencode(".png", img)[1].tobytes()


class Tracker(threading.Thread):
    def __init__(self, source, table_w, table_h, on_detect):
        super().__init__(daemon=True)
        self.source = int(source) if str(source).isdigit() else source
        self.table_w, self.table_h = table_w, table_h
        self.on_detect = on_detect  # called from this thread with list of detections
        self.corners = None         # 4 clicked table corners, normalized 0..1 in camera image (TL,TR,BR,BL)
        self.jpeg = None
        self.lock = threading.Lock()
        params = cv2.aruco.DetectorParameters()
        params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        self.detector = cv2.aruco.ArucoDetector(DICT, params)

    def set_calibration(self, corners, table_w, table_h):
        self.corners = [list(map(float, c)) for c in corners] if corners else None
        self.table_w, self.table_h = table_w, table_h

    @property
    def calibrated(self):
        return self.corners is not None

    def homography(self, fw, fh):
        """image px -> table cm"""
        if self.corners:
            src = np.float32([[x * fw, y * fh] for x, y in self.corners])
            dst = np.float32([[0, 0], [self.table_w, 0], [self.table_w, self.table_h], [0, self.table_h]])
            return cv2.getPerspectiveTransform(src, dst)
        s = self.table_w / fw  # not calibrated: whole camera frame == table width, no perspective correction
        return np.float64([[s, 0, 0], [0, s, 0], [0, 0, 1]])

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

        fh, fw = frame.shape[:2]
        H = self.homography(fw, fh)

        dets = []
        for mid, c in found.items():
            t = cv2.perspectiveTransform(c.reshape(-1, 1, 2).astype(np.float64), H).reshape(4, 2)
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
        if self.corners:
            pts = np.int32([[x * fw, y * fh] for x, y in self.corners])
            cv2.polylines(frame, [pts], True, (0, 255, 0), max(2, fw // 400))
        small = cv2.resize(frame, (640, int(640 * frame.shape[0] / frame.shape[1])))
        with self.lock:
            self.jpeg = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 70])[1].tobytes()

    def latest_jpeg(self):
        with self.lock:
            return self.jpeg
