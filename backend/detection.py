# backend/detection.py

import cv2
import numpy as np
import time
import base64
import os

class TrafficDetector:
    def __init__(self,
                 conf_threshold=0.6,      # raise to cut low‑conf false positives
                 nms_threshold=0.4,
                 max_count_limit=50,
                 verbose=False):
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold

        # exact names from coco.names
        self.vehicles = {"car", "bus", "motorbike","ambulance", "fire engine", "police", "truck"}
        self.emergency_vehicles = {"ambulance", "fire engine", "police", "truck"}

        self.verbose = verbose
        self.max_count_limit = max_count_limit

        # load YOLO
        self.net = cv2.dnn.readNet("yolo/yolov3.weights", "yolo/yolov3.cfg")
        layer_names = self.net.getLayerNames()
        self.output_layers = [
            layer_names[i - 1]
            for i in self.net.getUnconnectedOutLayers().flatten()
        ]

        with open("yolo/coco.names") as f:
            self.classes = [line.strip().lower() for line in f]

        os.makedirs("debug_images", exist_ok=True)

    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        """Denoise + contrast‑enhance before detection."""
        blurred = cv2.GaussianBlur(frame, (5, 5), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        v_eq = clahe.apply(v)
        hsv_eq = cv2.merge([h, s, v_eq])
        return cv2.cvtColor(hsv_eq, cv2.COLOR_HSV2BGR)

    def detect_objects(self, frame: np.ndarray):
        # 0) preprocess
        proc = self.preprocess(frame)

        # 1) forward pass
        h, w = proc.shape[:2]
        blob = cv2.dnn.blobFromImage(proc, 1/255.0, (416, 416), swapRB=True, crop=False)
        self.net.setInput(blob)
        outs = self.net.forward(self.output_layers)

        # 2) collect detections
        boxes, confidences, class_ids = [], [], []
        for out in outs:
            for det in out:
                scores = det[5:]
                cid = int(np.argmax(scores))
                conf = float(scores[cid])
                if conf < self.conf_threshold:
                    continue
                cx, cy, bw, bh = (det[0:4] * np.array([w, h, w, h])).astype(int)
                x, y = cx - bw//2, cy - bh//2
                boxes.append([x, y, bw, bh])
                confidences.append(conf)
                class_ids.append(cid)

        # 3) non‑max suppression
        idxs = cv2.dnn.NMSBoxes(boxes, confidences,
                                self.conf_threshold,
                                self.nms_threshold)

        count, emergency = 0, False
        drawn = 0

        if len(idxs) > 0:
            for i in idxs.flatten():
                name = self.classes[class_ids[i]]
                if name not in self.vehicles:
                    continue

                count += 1
                if name in self.emergency_vehicles:
                    emergency = True

                x, y, bw, bh = map(int, boxes[i])
                # draw on original frame
                cv2.rectangle(frame, (x, y), (x + bw, y + bh), (0, 255, 0), 2)
                cv2.putText(frame, name, (x, y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            (0, 255, 0), 2)

                drawn += 1
                if drawn >= self.max_count_limit:
                    break

        if self.verbose:
            print(f"[DETECT] {count} vehicles ({drawn} drawn), emergency={emergency}")

        # cap count and optionally save debug image
        if count > self.max_count_limit:
            count = self.max_count_limit
            if self.verbose:
                ts = time.strftime("%Y%m%d-%H%M%S")
                fname = f"debug_images/spike_{ts}.jpg"
                cv2.imwrite(fname, frame)
                print(f"[DEBUG] saved spike frame to {fname}")

        # encode and return
        _, jpg = cv2.imencode('.jpg', frame)
        img_b64 = base64.b64encode(jpg).decode('utf-8')
        return count, emergency, img_b64


# expose both for main.py
detector = TrafficDetector(verbose=True)


def sample_cycle(sources: dict) -> dict:
    """Read each camera for ~1s, detect, and return per‑lane dict."""
    latest = {lane: None for lane in sources}
    caps = {lane: cv2.VideoCapture(src) for lane, src in sources.items()}
    start = time.time()

    while time.time() - start < 1.0:
        for lane, cap in caps.items():
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
            if ret:
                latest[lane] = frame

    for cap in caps.values():
        cap.release()

    return {
        lane: dict(zip(["count", "emergency", "image"],
                       detector.detect_objects(frame)))
        for lane, frame in latest.items() if frame is not None
    }
