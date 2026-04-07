# Smart Attendance System — How to Run

## Quick Start

### 1. Frontend (React + Vite)
```bash
cd frontend
npm install        # only first time
npm run dev        # starts at http://localhost:3000
```

### 2. Backend (Python + DeepFace) — Optional but recommended
```bash
# Install dependencies (only first time)
pip install -r requirements_backend.txt

# Start backend
python start_backend.py
# → Runs at http://localhost:8000
# → API docs at http://localhost:8000/docs
```

> **Note:** The frontend works WITHOUT the backend.
> If backend is offline, face recognition uses local fallback mode.
> For real DeepFace (Facenet512 + RetinaFace) accuracy, start the backend.

---

## How It Works

### Session Flow
1. **Login** → go to Dashboard
2. **Start Session** → enter Class ID (e.g. `CS301`) → click Start
3. **Go to Classroom Camera** → click the green badge in the header
4. **Start Camera** → click **Start Attendance Capture**
5. The system captures a frame every 5 seconds and:
   - Detects faces using **RetinaFace**
   - Recognizes students using **Facenet512** embeddings
   - Analyzes emotions using **DeepFace** (`happy`, `sad`, `neutral`, etc.)
   - Maps emotions to engagement: `interested`, `bored`, `confused`, `sleepy`
6. **End Session** (on Dashboard) → see summary with average emotion analysis
7. **Reports** → view full attendance + emotion history

### Register Students (for face recognition to work)
1. Go to **Register Student** page
2. Fill in student details
3. Click **Capture Photo** → system stores face descriptors
4. During classroom capture, these are matched against detected faces

---

## File Structure (cleaned up)
```
caps-final/
├── start_backend.py          ← Run this for backend
├── requirements_backend.txt  ← Backend dependencies
├── frontend/
│   ├── src/
│   │   ├── store/
│   │   │   ├── authStore.ts      ← Login/signup state
│   │   │   └── sessionStore.ts   ← Session + emotion tracking (NEW)
│   │   ├── services/
│   │   │   ├── faceService.ts    ← DeepFace API client (NEW)
│   │   │   └── api.ts            ← Reports API
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx     ← Session control + live emotions
│   │   │   └── ClassroomCamera.tsx ← Capture + recognition + emotions
│   │   └── hooks/
│   │       └── useAttendanceSession.ts ← Thin wrapper over sessionStore
```

---

## Tech Stack
| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, Tailwind CSS, Zustand |
| Face Recognition | DeepFace (Facenet512) |
| Face Detection | RetinaFace |
| Emotion Analysis | DeepFace Analyze |
| Backend | FastAPI + Uvicorn |
| Data Storage | localStorage (auth, students, sessions) |
