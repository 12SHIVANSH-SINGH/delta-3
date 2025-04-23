import os
import time
import json
import cv2
import numpy as np

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from detection import sample_cycle, detector
from optimizer import optimizer

app = FastAPI()

# 🛡️ CORS (optional if everything is same‑origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

camera_sources = {
    "North": "videos/north.mp4",
    "South": "videos/south.mp4",
    "East":  "videos/east.mp4",
    "West":  "videos/west.mp4",
}

@app.get("/traffic_feed")
async def traffic_feed():
    def stream():
        while True:
            data    = sample_cycle(camera_sources)
            timings = optimizer.compute_green_time(data)
            payload = {
                "lanes":        data,
                "signal_times": timings,
                "timestamp":    time.strftime("%H:%M:%S")
            }
            yield f"data: {json.dumps(payload)}\n\n"
            time.sleep(1.5)
    return StreamingResponse(stream(), media_type="text/event-stream")

@app.post("/upload_image")
async def upload_image(file: UploadFile = File(...)):
    contents = await file.read()
    npimg     = np.frombuffer(contents, np.uint8)
    frame     = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    count, emergency, image = detector.detect_objects(frame)
    return JSONResponse({"count": count, "emergency": emergency, "image": image})

# ────────────────────────────────────────────────────────────
# Serve your frontend as static *after* all API routes

BASE_DIR      = os.path.dirname(os.path.dirname(__file__))
FRONTEND_DIR  = os.path.join(BASE_DIR, "frontend")

app.mount(
    "/", 
    StaticFiles(directory=FRONTEND_DIR, html=True), 
    name="frontend"
)
