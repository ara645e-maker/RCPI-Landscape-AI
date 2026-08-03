# Rahega Landscape AI Deployment Guide

## Overview
This project contains:
- `backend/` — FastAPI SaaS backend with auth, payment simulation, local RAG, and Stable Diffusion render generation
- `frontend/` — React + Vite + Tailwind user interface
- `docker-compose.yml` and `Dockerfile` — containerized deployment for backend and frontend

---

## Prerequisites

### Required software
- Python 3.12
- Git (optional)
- Node.js 20+ and npm
- Docker Engine + Docker Compose (for containerized deployment)
- Ollama CLI (optional but recommended for local vision/model inference)

### Optional but recommended
- GPU with CUDA support for Stable Diffusion and transformers
- `ollama` installed and a local model pulled

---

## Local Backend Deployment

### 1. Create and activate a Python virtual environment
PowerShell:
```powershell
cd "c:\Users\DELL\Desktop\K R AI"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install backend dependencies
```powershell
pip install --upgrade pip
pip install -r backend/requirements.txt
```

### 3. Set environment variables
Create a `.env` file in the project root or set these in your shell.
Example `.env` content:
```env
JWT_SECRET=supersecretkey
DATABASE_URL=sqlite:///./backend/saas.db
OLLAMA_MODEL=llava
SD_MODEL_ID=runwayml/stable-diffusion-v1-5
DEFAULT_ADMIN_EMAIL=admin@rahega.ai
DEFAULT_ADMIN_PASSWORD=AdminPass123
```

> Note: `JWT_SECRET` should be replaced with a strong secret in production.

### 4. Install Ollama and local models
If you want the backend to use Ollama for local vision/text inference:
- Install Ollama from https://ollama.com
- Pull the model referenced by `OLLAMA_MODEL`:
```powershell
ollama pull llava
```

### 5. Run the backend server
```powershell
cd "c:\Users\DELL\Desktop\K R AI"
setx DATABASE_URL "sqlite:///./backend/saas.db"
setx JWT_SECRET "supersecretkey"
setx OLLAMA_MODEL "llava"
setx SD_MODEL_ID "runwayml/stable-diffusion-v1-5"
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

If you use PowerShell and want variables only for the current session:
```powershell
$env:DATABASE_URL = "sqlite:///./backend/saas.db"
$env:JWT_SECRET = "supersecretkey"
$env:OLLAMA_MODEL = "llava"
$env:SD_MODEL_ID = "runwayml/stable-diffusion-v1-5"
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Verify backend health
Open:
- `http://127.0.0.1:8000/docs`

---

## Local Frontend Deployment

### 1. Install frontend dependencies
```powershell
cd "c:\Users\DELL\Desktop\K R AI\frontend"
npm install
```

### 2. Start the frontend
```powershell
npm run dev -- --host 0.0.0.0
```

### 3. Visit the app
Open:
- `http://127.0.0.1:5173`

---

## Docker Deployment

### 1. Build and run with Docker Compose
From the project root:
```powershell
cd "c:\Users\DELL\Desktop\K R AI"
docker compose up --build
```

### 2. Services exposed
- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:5173`

### 3. Notes for Docker
- The backend container uses `sqlite:///./backend/saas.db` by default.
- The frontend container installs dependencies on startup.
- If you need Ollama support inside Docker, install Ollama on the host and ensure the CLI is available to the container, or adjust the Dockerfile/service accordingly.

---

## Model and Inference Setup

### Ollama
If `ollama` is installed, the backend will attempt to use it in `backend/llm_client.py`.
- Confirm availability:
```powershell
ollama version
ollama list
```
- Pull the model:
```powershell
ollama pull llava
```

### Stable Diffusion
The backend uses `runwayml/stable-diffusion-v1-5` by default.
- First launch may download weights and take time.
- GPU is strongly recommended.
- If your environment has no GPU, inference will run on CPU but may be slow.

---

## Database and Persistence

### SQLite
By default, the app uses SQLite via `DATABASE_URL=sqlite:///./backend/saas.db`.
- The file is created automatically on startup.
- Data persists between restarts if the same file path is used.

### Admin user
The project includes admin bootstrap values in `docker-compose.yml`.
If you run locally instead of Docker, create users through the API or update the app to add a default admin.

---

## End-to-End Test Checklist

1. Start backend and confirm `http://127.0.0.1:8000/docs` loads.
2. Start frontend and confirm `http://127.0.0.1:5173` loads.
3. Register or login via the frontend or `POST /api/auth/register`.
4. Create a project via `POST /api/projects`.
5. Upload an image with `POST /api/projects/{project_id}/analyze` and verify response includes `plant_selection`, `boq`, and `render_base64`.
6. Confirm the generated `layout_blueprint` and cost summary appear in the analysis payload.

---

## Troubleshooting

### Backend fails to start
- Confirm Python 3.12 is installed.
- Confirm `.venv` is activated and dependencies installed.
- Check for missing environment variables.
- If `torch` or `diffusers` errors appear, verify your CUDA/cuDNN installation or use CPU mode.

### Stable Diffusion failure
- Ensure `torch` and `diffusers` are installed.
- On CPU, expect slower image generation.
- If run fails due to model download, allow time for the model to cache.

### Ollama model failure
- Confirm `ollama` is installed and on PATH.
- Confirm the model name matches `OLLAMA_MODEL`.
- Test with `ollama run llava --no-stream --prompt "hello"`.

---

## Notes
- This guide assumes the current workspace root is `c:\Users\DELL\Desktop\K R AI`.
- For production deployment, replace the default `JWT_SECRET`, use a proper database, and secure the backend/frontend hosts.
- If you want a pure container deployment, use `docker compose up --build` and expose the app behind a reverse proxy.
