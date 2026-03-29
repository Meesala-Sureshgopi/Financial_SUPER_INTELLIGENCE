# FinSI Financial Super Intelligence

FinSI is an AI-powered investment copilot for Indian equities. It combines live market data, technical analysis, portfolio awareness, recent contextual signals, and a multi-agent reasoning pipeline into a dashboard-led decision workflow.

This repository contains a working full-stack product:

- a Vite + React frontend
- a FastAPI backend
- a multi-agent orchestration flow
- SQLite-backed persistence
- a demo portfolio system
- an embedded Gemini-powered copilot chat

## What The Application Does

FinSI is built to help a user move from raw market inputs to a clearer decision.

The application allows a user to:

- search a company or ticker
- run an AI-assisted stock analysis
- inspect broker-style line and candlestick charts
- see a verdict and confidence score
- understand portfolio relevance
- add or remove stocks from a demo portfolio
- monitor an autonomous signal stream
- ask follow-up questions through an embedded copilot

## Product Modules

### 1. Intelligence Dashboard

Main frontend file:

- [Dashboard.tsx](AI_Investment_Copilot/frontend/src/components/Dashboard.tsx)

The dashboard provides:

- company-aware search suggestions
- manual stock analysis
- expert verdict
- portfolio relevance
- decision synthesis
- market intelligence terminal
- autonomous signal stream

### 2. Market Intelligence Terminal

Main frontend file:

- [StockChart.tsx](AI_Investment_Copilot/frontend/src/components/StockChart.tsx)

Current chart features:

- line mode
- candlestick mode
- `30D`, `45D`, `3M`, `6M`, `1Y` ranges
- compact portfolio chart mode
- OHLC metrics

### 3. Portfolio Intelligence

Main frontend file:

- [PortfolioView.jsx](AI_Investment_Copilot/frontend/src/components/PortfolioView.jsx)

The portfolio view provides:

- portfolio totals
- holding list
- holding detail panel
- live price / P&L view
- full chart for the selected holding

### 4. Embedded Copilot

Active frontend file:

- [CopilotChat.tsx](AI_Investment_Copilot/frontend/src/components/CopilotChat.tsx)
Main backend route:

- [main.py](AI_Investment_Copilot/backend/api/main.py#L257)

The copilot currently uses:

- Gemini 3.1 Flash-Lite only
- matched stock context
- latest saved analysis snapshot
- technical context
- portfolio context
- recent web/news context

## Backend Architecture

### API Layer

Main file:

- [main.py](AI_Investment_Copilot/backend/api/main.py)

Important endpoints:

- `POST /api/analyze`
- `POST /api/query`
- `GET /api/alerts/history`
- `POST /api/alerts/live-refresh`
- `GET /api/tickers/search`
- `GET /api/portfolio`
- `POST /api/portfolio/holdings`
- `POST /api/portfolio/holdings/remove`
- `GET /api/chart/{ticker}`
- `GET /api/price/{ticker}`
- `GET /api/stock/{ticker}`
- `GET /api/health`

### Orchestration Layer

Main file:

- [orchestrator.py](AI_Investment_Copilot/backend/graph/orchestrator.py)

Current agent sequence:

1. Signal Radar
2. Chart Intel
3. Context Enrich
4. Conflict Resolver
5. Portfolio Agent
6. Impact Quantifier when relevance is high
7. Action Generator

### Data Layer

Main files:

- [schema.sql](AI_Investment_Copilot/backend/db/schema.sql)
- [session.py](AI_Investment_Copilot/backend/db/session.py)

Persisted entities:

- users
- holdings
- signals
- alerts
- pattern backtest cache

### Autonomous Monitoring Layer

Main file:

- [jobs.py](AI_Investment_Copilot/backend/scheduler/jobs.py)

Current behavior:

- autonomous monitoring is disabled by default
- manual refresh can trigger live signal refresh
- bulk-deal polling is the main scheduled source
- universal market scan is gated behind env configuration

## Model Strategy

Main files:

- [config.py](AI_Investment_Copilot/backend/config.py)
- [llm_provider.py](AI_Investment_Copilot/backend/tools/llm_provider.py)

Current routing:

- Gemini 3.1 Flash-Lite Preview is primary
- Groq is fallback
- HuggingFace is additional fallback
- embedded copilot chat uses Gemini-only calls

## Context Sources

FinSI pulls context from multiple sources:

- `yfinance` for price/history/fundamentals
- Google News RSS for recent contextual headlines
- NSE snapshot APIs
- BSE/NSE event sources
- SQLite-persisted analysis history
- ChromaDB + embeddings for filing retrieval

## Current State Of The Codebase

The project is fully usable as a demo product, but it is still evolving.

Current strengths:

- strong end-to-end feature coverage
- useful portfolio-aware reasoning
- good chart UX
- real persistence and analysis history
- embedded copilot is context-aware

Current known gaps:

- some legacy `Avalon` branding still remains in the UI
- some backend logic is heuristic and not fully hardened
- deployment is best handled as split frontend/backend hosting

For setup instructions, see:

- [SETUP.md](AI_Investment_Copilot/SETUP.md)

## Project Structure

```text
AI_Investment_Copilot/
├── backend/
│   ├── agents/
│   ├── api/
│   ├── data/
│   ├── db/
│   ├── graph/
│   ├── scheduler/
│   ├── tools/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── Dockerfile
│   ├── package.json
│   └── .env.example
├── docker-compose.yml
├── docker-compose.prod.yml
├── vercel.json
├── README.md
└── SETUP.md
```

## Deployment Reality

### Recommended

- frontend on Vercel
- backend on Railway / Render / Fly.io / Azure / VM / Docker host

### Why Not Single-Platform Vercel For Everything

The backend currently relies on:

- FastAPI
- background jobs
- SSE-style alert streaming
- persistent local data assumptions
- Python model/tooling stack

That makes it better suited to a Python/container host than a frontend-only platform workflow.

## Environment Variables

### Backend Example

```env
GEMINI_API_KEY=your_key
GROQ_API_KEY=your_key
HUGGINGFACE_API_TOKEN=your_token
LLM_PRIORITY=gemini,groq,huggingface
GEMINI_MODEL_PRIMARY=gemini-3.1-flash-lite-preview
GEMINI_MODEL_FAST=gemini-3.1-flash-lite-preview
GEMINI_MODEL_CODER=gemini-3.1-flash-lite-preview
ENABLE_AUTONOMOUS_MONITORING=false
ENABLE_UNIVERSAL_SCAN=false
```

### Frontend Example

```env
VITE_API_BASE_URL=https://your-backend-domain.com
```

## Disclaimer

FinSI is a demo investment intelligence application. It is not licensed financial advice and should not be treated as a substitute for regulated professional guidance.
