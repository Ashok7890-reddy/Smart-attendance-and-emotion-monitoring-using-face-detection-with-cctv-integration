#!/usr/bin/env python3
"""
Simple standalone backend for Smart Attendance System.
Uses DeepFace (Facenet512 + RetinaFace) for face recognition and emotion analysis.

Install: pip install fastapi uvicorn deepface opencv-python pillow numpy python-multipart
Run:     python start_backend.py
"""

import base64
import io
import json
import numpy as np
import logging
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image
import cv2

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("attendance_backend")

# ─── DeepFace ─────────────────────────────────────────────────────────────────
try:
    from deepface import DeepFace
    DEEPFACE_OK = True
    log.info("✅ DeepFace loaded successfully")
except ImportError:
    DEEPFACE_OK = False
    log.warning("⚠️  DeepFace not installed. Run: pip install deepface")


# ─── Emotion → engagement mapping ─────────────────────────────────────────────
EMOTION_MAP = {
    "happy":      ("interested", 0.95),
    "surprise":   ("interested", 0.85),
    "surprised":  ("interested", 0.85),
    "neutral":    ("bored",      0.50),
    "sad":        ("sleepy",     0.20),
    "angry":      ("confused",   0.30),
    "disgust":    ("bored",      0.15),
    "disgusted":  ("bored",      0.15),
    "fear":       ("confused",   0.25),
    "fearful":    ("confused",   0.25),
}


# ─── Pydantic models ──────────────────────────────────────────────────────────
class RegisteredStudent(BaseModel):
    student_id: str
    name: str
    student_type: str = "day_scholar"
    face_descriptors: List[List[float]] = []


class AnalyzeRequest(BaseModel):
    image_base64: str
    session_id: str
    registered_students: List[RegisteredStudent] = []


class EmotionRequest(BaseModel):
    image_base64: str
    student_id: str = "unknown"


# ─── Helpers ──────────────────────────────────────────────────────────────────
def decode_image(b64: str) -> np.ndarray:
    """Decode base64 string → BGR numpy array."""
    data = base64.b64decode(b64)
    pil = Image.open(io.BytesIO(data)).convert("RGB")
    arr = np.array(pil)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def analyze_emotions_deepface(img_bgr: np.ndarray) -> List[Dict[str, Any]]:
    """Run DeepFace emotion analysis; returns list of face results."""
    if not DEEPFACE_OK:
        return []
    try:
        results = DeepFace.analyze(
            img_path=img_bgr,
            actions=["emotion"],
            detector_backend="retinaface",
            enforce_detection=False,
            silent=True,
        )
        if isinstance(results, dict):
            results = [results]
        return results
    except Exception as e:
        log.warning(f"DeepFace emotion failed: {e}")
        return []


def recognize_faces_deepface(
    img_bgr: np.ndarray,
    registered: List[RegisteredStudent],
) -> Dict[str, List[Any]]:
    """
    Use DeepFace.find() / represent() to match faces in image against registered embeddings.
    Returns {"recognized": [...], "unrecognized": [...]}
    """
    if not DEEPFACE_OK:
        return {"recognized": [], "unrecognized": []}

    recognized = []
    unrecognized = []

    try:
        # Detect all faces and their embeddings
        face_results = DeepFace.represent(
            img_path=img_bgr,
            model_name="Facenet512",
            detector_backend="retinaface",
            enforce_detection=False,
        )
        if isinstance(face_results, dict):
            face_results = [face_results]

        for face in face_results:
            query_emb = np.array(face.get("embedding", []))
            if len(query_emb) == 0:
                continue

            best_match = None
            best_dist = float("inf")

            for student in registered:
                if not student.face_descriptors:
                    continue
                for desc in student.face_descriptors:
                    stored_emb = np.array(desc)
                    if len(stored_emb) != len(query_emb):
                        continue
                    # Cosine distance
                    dot = np.dot(query_emb, stored_emb)
                    norm = np.linalg.norm(query_emb) * np.linalg.norm(stored_emb)
                    dist = 1 - (dot / norm) if norm > 0 else 1.0
                    if dist < best_dist:
                        best_dist = dist
                        best_match = student

            # Facenet512 threshold ≈ 0.30 (cosine)
            bbox = face.get("facial_area", {})
            if best_match and best_dist < 0.30:
                confidence = max(0.0, 1.0 - best_dist / 0.30)
                recognized.append({
                    "student_id": best_match.student_id,
                    "name":       best_match.name,
                    "student_type": best_match.student_type,
                    "confidence": round(confidence, 3),
                    "bbox":       bbox,
                })
            else:
                # Crop face to return base64
                x, y, w, h = bbox.get("x", 0), bbox.get("y", 0), bbox.get("w", 0), bbox.get("h", 0)
                # Add 10% padding
                py = int(h * 0.1)
                px = int(w * 0.1)
                y1 = max(0, y - py)
                y2 = min(img_bgr.shape[0], y + h + py)
                x1 = max(0, x - px)
                x2 = min(img_bgr.shape[1], x + w + px)
                
                face_crop = img_bgr[y1:y2, x1:x2]
                if face_crop.size > 0:
                    _, buffer = cv2.imencode('.jpg', face_crop)
                    b64_crop = base64.b64encode(buffer).decode('utf-8')
                else:
                    b64_crop = ""
                    
                unrecognized.append({
                    "image_base64": f"data:image/jpeg;base64,{b64_crop}",
                    "bbox": bbox,
                    "confidence": round(max(0.0, 1.0 - best_dist / 0.30), 2) if best_dist != float("inf") else 0
                })

    except Exception as e:
        log.warning(f"DeepFace recognition failed: {e}")

    return {"recognized": recognized, "unrecognized": unrecognized}


# ─── App lifespan ──────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀 Smart Attendance Backend starting...")
    if DEEPFACE_OK:
        # Warm up DeepFace models
        try:
            dummy = np.zeros((112, 112, 3), dtype=np.uint8) + 128
            DeepFace.analyze(img_path=dummy, actions=["emotion"],
                             detector_backend="retinaface",
                             enforce_detection=False, silent=True)
            log.info("✅ DeepFace models warmed up")
        except Exception as e:
            log.warning(f"Warmup failed (normal on first run): {e}")
    yield
    log.info("👋 Backend shutting down")


# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Smart Attendance Backend",
    description="DeepFace (Facenet512 + RetinaFace) powered attendance and emotion system",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Routes ───────────────────────────────────────────────────────────────────
@app.get("/api/v1/health")
def health():
    return {
        "status": "healthy",
        "deepface": DEEPFACE_OK,
        "model": "Facenet512",
        "detector": "RetinaFace",
    }


@app.post("/api/v1/classroom/analyze")
async def classroom_analyze(req: AnalyzeRequest):
    """
    Main endpoint: given a frame + registered students,
    returns who is present and their emotions.
    """
    try:
        if "," in req.image_base64:
            b64str = req.image_base64.split(",")[1]
        else:
            b64str = req.image_base64
        img_bgr = decode_image(b64str)
    except Exception as e:
        raise HTTPException(400, f"Invalid image: {e}")

    # 1. Recognize faces
    match_result = recognize_faces_deepface(img_bgr, req.registered_students)
    recognized = match_result["recognized"]
    unrecognized_list = match_result["unrecognized"]

    # 2. Analyze emotions for the whole frame
    emotion_results = analyze_emotions_deepface(img_bgr)

    # 3. Map emotions to recognized students (by face index order roughly)
    recognized_with_emotions = []
    for i, rec in enumerate(recognized):
        emotion_raw = "neutral"
        if i < len(emotion_results):
            emo_data = emotion_results[i].get("emotion", {})
            if emo_data:
                emotion_raw = max(emo_data, key=emo_data.get)

        engagement, score = EMOTION_MAP.get(emotion_raw, ("bored", 0.5))
        recognized_with_emotions.append({
            **rec,
            "emotion":          emotion_raw,
            "engagement":       engagement,
            "engagement_score": score,
        })

    # 4. Frame-level emotion summary
    frame_summary = {"interested": 0, "bored": 0, "confused": 0, "sleepy": 0}
    for r in recognized_with_emotions:
        key = r["engagement"]
        if key in frame_summary:
            frame_summary[key] += 1

    total_faces = len(recognized_with_emotions) + len(unrecognized_list)

    log.info(
        f"[{req.session_id}] Faces={total_faces} Recognized={len(recognized_with_emotions)} Unknown={len(unrecognized_list)}"
    )

    return {
        "session_id":           req.session_id,
        "recognized_students":  recognized_with_emotions,
        "unrecognized_faces":   unrecognized_list,
        "unrecognized_count":   len(unrecognized_list),
        "total_faces":          total_faces,
        "frame_emotion_summary": frame_summary,
    }


@app.post("/api/v1/deepface/analyze-emotion-base64")
async def analyze_emotion_base64(req: EmotionRequest):
    """Single-image emotion analysis endpoint."""
    try:
        img_bgr = decode_image(req.image_base64)
    except Exception as e:
        raise HTTPException(400, f"Invalid image: {e}")

    results = analyze_emotions_deepface(img_bgr)
    if not results:
        return {
            "student_id":     req.student_id,
            "raw_emotion":    "neutral",
            "emotion":        "bored",
            "confidence":     0.0,
            "engagement_score": 0.5,
            "emotion_breakdown": {"raw_emotions": {"neutral": 100.0}},
        }

    emo_data = results[0].get("emotion", {})
    dominant = max(emo_data, key=emo_data.get) if emo_data else "neutral"
    confidence = emo_data.get(dominant, 0) / 100.0
    engagement, score = EMOTION_MAP.get(dominant, ("bored", 0.5))

    return {
        "student_id":     req.student_id,
        "raw_emotion":    dominant,
        "emotion":        engagement,
        "confidence":     round(confidence, 3),
        "engagement_score": score,
        "emotion_breakdown": {"raw_emotions": emo_data},
    }

# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    log.info("=" * 60)
    log.info("  Smart Attendance Backend  (DeepFace + Facenet512)")
    log.info("  API docs: http://localhost:8000/docs")
    log.info("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
