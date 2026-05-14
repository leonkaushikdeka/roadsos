# RoadSoS — Software Package Document

## How to Run Locally in 5 Minutes

### Prerequisites
- Node.js v20+
- Python 3.12+
- Docker Desktop (for PostgreSQL + PostGIS)
- npm or yarn

### Quick Start

```bash
# 1. Start infrastructure (PostgreSQL + PostGIS, Redis)
docker compose -f infra/docker-compose.yml up -d postgres redis

# 2. Install backend dependencies
cd backend
pip install -r requirements.txt

# 3. Seed the database (TN region hospitals, ambulances, etc.)
python -m app.seed.run

# 4. Start the backend API
uvicorn app.main:app --reload --port 8000

# In a new terminal:

# 5. Install frontend dependencies
cd frontend
npm install

# 6. Start the frontend
npm run dev

# 7. Open http://localhost:3000
```

### Run Everything (Docker)
```bash
docker compose -f infra/docker-compose.yml up -d
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## Dependencies

### Backend (Python)

| Package | Version | License | Purpose |
|---------|---------|---------|---------|
| fastapi | 0.115.0 | MIT | Async web framework |
| uvicorn | 0.30.6 | BSD-3 | ASGI server |
| sqlalchemy | 2.0.35 | MIT | ORM for database access |
| asyncpg | 0.30.0 | Apache-2.0 | Async PostgreSQL driver |
| geoalchemy2 | 0.15.1 | MIT | PostGIS spatial ORM |
| pydantic | 2.9.2 | MIT | Data validation (FastAPI native) |
| pydantic-settings | 2.5.2 | MIT | Settings management |
| redis | 5.1.1 | MIT | Caching (triage sessions, rate limits) |
| celery | 5.4.0 | BSD-3 | Async task queue for dispatch jobs |
| httpx | 0.27.2 | BSD-3 | HTTP client for external APIs |
| python-multipart | 0.0.12 | Apache-2.0 | File uploads (scene photos/audio) |
| twilio | 9.3.0 | MIT | SMS and IVR voice integration |
| opentelemetry-api | 1.27.0 | Apache-2.0 | Distributed tracing |
| opentelemetry-sdk | 1.27.0 | Apache-2.0 | Telemetry SDK |
| langgraph | 0.3.6 | MIT | LLM agent state machine (triage flow) |
| langchain-core | 0.3.38 | MIT | LangGraph runtime & primitives |
| sentence-transformers | 3.1.0 | Apache-2.0 | Protocol embedding for RAG |
| python-dotenv | 1.0.1 | BSD-3 | Environment variable loading |

### Frontend (Node.js)

| Package | Version | License | Purpose |
|---------|---------|---------|---------|
| next | 14.2.15 | MIT | React framework with PWA support |
| react | 18.3.1 | MIT | UI library |
| typescript | 5.6.2 | Apache-2.0 | Type safety |
| tailwindcss | 3.4.13 | MIT | Utility-first CSS framework |
| leaflet | 1.9.4 | BSD-2 | Maps rendering (optional, canvas fallback available) |

### Infrastructure

| Tool | Version | License | Purpose |
|------|---------|---------|---------|
| PostgreSQL 16 | 16 | PostgreSQL | Primary database |
| PostGIS 3.4 | 3.4 | GPL-2 | Geospatial queries |
| Redis 7 | 7 | BSD-3 | Caching + task queue broker |
| Docker | 24+ | Apache-2.0 | Containerisation |

---

## Project Structure

```
roadsos/
├── frontend/               # Next.js PWA (Progressive Web App)
│   ├── app/                # Pages (SOS splash, triage chat, dispatch)
│   ├── components/         # TriageChat, ServiceMap, AROverlay
│   ├── lib/                # API client, geolocation utils
│   ├── public/             # PWA manifest, service worker, icons
│   └── workers/            # Service worker (offline-first caching)
├── backend/                # FastAPI Python API
│   └── app/
│       ├── routes/         # Incident, services, webhook, admin APIs
│       ├── models/         # SQLAlchemy ORM models
│       ├── schemas/        # Pydantic request/response schemas
│       ├── services/       # Triage agent, dispatch engine, notifications
│       └── seed/           # Database seeding scripts
├── agent/                  # AI triage agent (LangGraph)
│   └── triage/             # State machine, RAG protocol retrieval
├── infra/                  # Docker Compose, k8s manifests
│   ├── docker-compose.yml  # Local dev setup (PostgreSQL, Redis, backend, frontend)
│   └── init-db.sql         # PostGIS + extension setup
├── seed_data/              # Seed data CSVs and SQL dumps
│   └── tn/                 # Tamil Nadu region data
├── SOFTWARE.md             # This file
├── ASSUMPTIONS.md          # Design assumptions and limitations
└── .env.example            # Environment variable template
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /v1/incident/initiate | Start a new SOS incident |
| POST | /v1/incident/{id}/triage | Send triage answer, get next question |
| POST | /v1/incident/{id}/dispatch | Confirm dispatch to service |
| GET | /v1/incident/{id} | Get incident status |
| GET | /v1/services/nearby | Find nearby emergency services |
| GET | /v1/services/{id}/status | Get service live capacity |
| POST | /v1/webhook/whatsapp | WhatsApp message inbound |
| POST | /v1/webhook/twilio/voice | IVR voice call leg |
| GET | /v1/admin/heatmap | Anonymised incident heatmap |
| GET | /v1/admin/stats | aggregate incident statistics |
| GET | /health | Health check |

---

## License
This project is submitted for the RoadSoS track at the CoERS, IIT Madras Road Safety Hackathon 2026.
