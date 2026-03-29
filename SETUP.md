# Setup Guide

This guide explains how to run, validate, and deploy FinSI based on the current repository state.

## 1. Stack Overview

FinSI currently consists of:

- a React + Vite frontend
- a FastAPI backend
- SQLite persistence
- optional autonomous scheduler jobs
- external data/model dependencies such as Gemini, Groq, yfinance, and Google News RSS

## 2. Prerequisites

Install the following first:

- Python 3.11 recommended
- Node.js 18+
- npm
- Docker Desktop if you want the container workflow

Recommended local machine conditions:

- reliable internet connection
- access to Gemini API key
- optional Groq and HuggingFace keys for fallback

## 3. Clone And Open The Project

```powershell
cd C:\Users\sures\PROJECTS
```

Project root:

```text
C:\Users\sures\PROJECTS\AI_Investment_Copilot
```

## 4. Backend Setup

### Step 1: Create Virtual Environment

```powershell
cd C:\Users\sures\PROJECTS\AI_Investment_Copilot\backend
python -m venv .venv
.venv\Scripts\activate
```

### Step 2: Install Dependencies

```powershell
pip install -r requirements.txt
```

### Step 3: Configure Environment

Create `backend/.env` from [backend/.env.example](/C:/Users/sures/PROJECTS/AI_Investment_Copilot/backend/.env.example).

Recommended baseline:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
HUGGINGFACE_API_TOKEN=your_huggingface_token_here
LLM_PRIORITY=gemini,groq,huggingface
GEMINI_MODEL_PRIMARY=gemini-3.1-flash-lite-preview
GEMINI_MODEL_FAST=gemini-3.1-flash-lite-preview
GEMINI_MODEL_CODER=gemini-3.1-flash-lite-preview
ENABLE_AUTONOMOUS_MONITORING=false
ENABLE_UNIVERSAL_SCAN=false
```

### Step 4: Run Backend

Preferred:

```powershell
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Alternative:

```powershell
python -m api.main
```

### Step 5: Verify Backend

Open:

```text
http://localhost:8000/api/health
```

Expected:

- JSON response with status `ok`

## 5. Frontend Setup

### Step 1: Install Dependencies

```powershell
cd C:\Users\sures\PROJECTS\AI_Investment_Copilot\frontend
npm install
```

### Step 2: Optional Frontend Environment

For deployed or split-host scenarios, create `frontend/.env` using [frontend/.env.example](/C:/Users/sures/PROJECTS/AI_Investment_Copilot/frontend/.env.example):

```env
VITE_API_BASE_URL=https://your-backend-domain.com
```

For local development, this is optional because the frontend can use relative `/api` calls and the Vite proxy.

### Step 3: Run Frontend

```powershell
npm run dev
```

Open:

```text
http://localhost:5173
```

## 6. End-To-End Validation Checklist

After both services are up:

1. Open the dashboard
2. Search a stock like `INFY`
3. Select the company suggestion
4. Click `Analyze`
5. Confirm verdict, chart, and reasoning appear
6. Add the stock to the demo portfolio
7. Open the Portfolio tab and confirm the holding appears
8. Open the embedded copilot and ask about the same stock
9. Click `Refresh` in the autonomous signal stream

## 7. Important Current Behaviors

### Search

- search suggestions begin after 3 characters
- selecting a suggestion stores the selected company context

### Analysis

- analysis can be manually stopped from the UI
- the app uses cached recent analysis when available

### Copilot

- the embedded copilot uses Gemini 3.1 Flash-Lite only
- it can use saved analysis, technical context, holdings context, and recent news context

### Autonomous Monitoring

- disabled by default
- live refresh can still be triggered manually

## 8. Docker Local Run

The repository includes a local-oriented compose file:

```powershell
cd C:\Users\sures\PROJECTS\AI_Investment_Copilot
docker compose up --build
```

This is suitable for local iteration, but not the best production shape.

## 9. Production-Style Self-Hosting

For a more production-like container flow, use:

- [docker-compose.prod.yml](/C:/Users/sures/PROJECTS/AI_Investment_Copilot/docker-compose.prod.yml)

Run:

```powershell
docker compose -f docker-compose.prod.yml up --build
```

## 10. Vercel Deployment Guidance

### Recommended Split

- deploy the frontend to Vercel
- deploy the backend separately to a Python/container host

Why:

- backend uses FastAPI
- backend uses scheduler jobs
- backend uses persistent local data assumptions
- backend exposes streaming-friendly behavior

Vercel is excellent for the frontend, but not the best one-stop host for the current backend shape.

### Frontend On Vercel

Files already prepared:

- [vercel.json](/C:/Users/sures/PROJECTS/AI_Investment_Copilot/vercel.json)
- [frontend/src/api.js](/C:/Users/sures/PROJECTS/AI_Investment_Copilot/frontend/src/api.js)

Set this env var on Vercel:

```env
VITE_API_BASE_URL=https://your-backend-domain.com
```

## 11. Troubleshooting

### Frontend Loads But API Calls Fail

- confirm backend is running on `8000`
- confirm `VITE_API_BASE_URL` is correct when deployed
- confirm backend CORS is not blocked

### Chat Responses Feel Too Generic

- first run a stock analysis from the dashboard
- then ask about the same stock in chat
- this gives the chat route a saved analysis snapshot to use

### Charts Do Not Render

- check backend `/api/chart/{ticker}`
- check ticker mapping issues in market data
- some symbols may be inconsistent in yfinance

### Rate Limits

- Gemini is the primary provider now
- confirm your `.env` matches the expected Gemini-first setup

### Duplicate Frontend Files

The repository still contains both:

- `CopilotChat.jsx`
- `CopilotChat.tsx`

The live app currently resolves to the `.jsx` version. Keep that in mind while editing.

## 12. Recommended Next Cleanup

To improve maintainability after setup:

1. remove duplicate chat component file
2. finish full FinSI rebranding in app shell
3. replace blocking `time.sleep` calls in async backend agents
4. add stronger typed frontend-backend contracts
