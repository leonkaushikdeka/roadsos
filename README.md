# RoadSoS — AI-Powered Emergency Response System

> The AI Companion that turns every bystander into a first responder.

**1.19 million** lives are lost on roads every year — half within 60 minutes. RoadSoS is a multi-modal AI emergency companion that orchestrates the entire chain of survival: from a single SOS tap through voice-guided triage to ambulance dispatch and hospital pre-alert.

Accessible via **PWA**, **WhatsApp**, **IVR voice call**, and **SMS fallback** — no app download, no login walls.

## Live Demo

| Surface | URL |
|---------|-----|
| PWA | [frontend-ten-gamma-78.vercel.app](https://frontend-ten-gamma-78.vercel.app) |
| API Docs (Swagger) | [rare-adventure-production-984a.up.railway.app/docs](https://rare-adventure-production-984a.up.railway.app/docs) |
| Backend Health | [rare-adventure-production-984a.up.railway.app/health](https://rare-adventure-production-984a.up.railway.app/health) |
| GitHub | [github.com/leonkaushikdeka/roadsos](https://github.com/leonkaushikdeka/roadsos) |

**Demo video:** [`submission/demo.mp4`](submission/demo.mp4)

## Quick Start

### Prerequisites

- Python 3.12+, Node.js v20+, Docker Desktop

### Run Locally

```bash
git clone https://github.com/leonkaushikdeka/roadsos.git
cd roadsos
cp .env.example .env

# Start PostgreSQL + Redis
docker compose -f infra/docker-compose.yml up -d postgres redis

# Backend
cd backend
pip install -r requirements.txt
python -m app.seed.run          # Seed TN hospitals, ambulances, police
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

The system uses a **deterministic triage FSM** by default (`USE_MOCK_LLM=true`). No GPU or model download needed. Set WhatsApp/Twilio credentials in `.env` for real messaging.

## How It Works

```
 Ravi stops at a crash on NH-37 at 11 PM

 0:00  Taps SOS on PWA (or sends "SOS" on WhatsApp)
 0:05  GPS locked. AI asks triage questions in Assamese
 0:20  HIGH severity → Ambulance, hospital, police dispatched
 0:35  Voice + AR guides bleeding control
 1:10  Scene photos uploaded. ICE contacts notified
11:20  Ambulance arrives. ER pre-warned. Golden Hour intact.
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              PRESENTATION LAYER                      │
│  Next.js PWA  ·  WhatsApp Bot  ·  IVR  ·  SMS       │
├─────────────────────────────────────────────────────┤
│              AI ORCHESTRATION LAYER                   │
│  LangGraph Agent  ·  RAG (WHO/ATLS)  ·  ASR/TTS     │
├─────────────────────────────────────────────────────┤
│                  SERVICES LAYER                       │
│  Dispatch  ·  Hospital Ranking  ·  Fraud Detection   │
├─────────────────────────────────────────────────────┤
│              DATA LAYER                               │
│  PostgreSQL (Railway)  ·  Haversine geo  ·  Redis    │
└─────────────────────────────────────────────────────┘
```

## Features

- **One-Tap SOS** — No login, no friction. Works on any browser.
- **AI Triage Agent** — LangGraph FSM trained on START + CRAMS protocols with negation-aware severity classification
- **Smart Dispatch** — Haversine-based multi-criteria ranking (trauma grade, distance, bed availability)
- **RAG Protocol Guidance** — Every first-aid instruction grounded in vetted WHO/ATLS corpus. Confidence < 0.78 → human dispatcher.
- **Voice & Vernacular** — 8+ BIMSTEC languages with code-mixed speech support (Whisper ASR + IndicTrans2)
- **Multi-Channel** — PWA, WhatsApp, IVR voice, SMS fallback
- **Offline-First** — Service worker caches protocols. SMS dispatch grammar for GSM dead zones.
- **Non-Blocking Fraud Detection** — Rate limiting + velocity checks flag abuse without blocking genuine emergencies
- **Visual First-Aid** — Canvas-based AR overlay for pressure points and spinal precautions
- **Privacy by Design** — Auto-purge 24h post-incident, DPDP Act 2023 aligned

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS (PWA) |
| Backend | FastAPI, SQLAlchemy (async), Pydantic v2 |
| Database | PostgreSQL 16 (Railway) |
| AI/ML | LangGraph, Llama 3.1 8B (mock FSM default), Whisper ASR, IndicTrans2 |
| Messaging | WhatsApp Business Cloud API, Twilio (SMS/IVR) |
| Observability | OpenTelemetry |
| Hosting | Vercel (frontend), Railway (backend + PostgreSQL) |

## Project Structure

```
roadsos/
├── frontend/               # Next.js PWA
│   ├── app/                # Pages: SOS, triage chat, dispatch, admin
│   ├── components/         # TriageChat, ServiceMap, AROverlay
│   ├── lib/                # API client, geolocation utils
│   └── public/             # Service worker, manifest, icons
├── backend/                # FastAPI API
│   └── app/
│       ├── routes/         # Incident, services, webhooks, admin
│       ├── schemas/        # Pydantic request/response models
│       ├── services/       # Triage, dispatch, fraud, notifications, RAG
│       ├── models/         # SQLAlchemy ORM
│       └── seed/           # TN seed data (240+ hospitals, 1200+ ambulances)
├── agent/                  # LangGraph triage agent
│   └── triage/             # State machine, RAG protocol retrieval
├── infra/                  # Docker Compose, k8s manifests
├── seed_data/              # Seed CSVs and SQL
├── submission/             # Hackathon deliverables
│   ├── RoadSoS_Presentation.pptx
│   ├── RoadSoS_Solution_Document.docx
│   ├── slides_final.pdf
│   └── demo.mp4
├── ASSUMPTIONS.md          # Design assumptions and limitations
├── SOFTWARE.md             # Dependencies and setup guide
└── .env.example            # Environment template
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/incident/initiate` | Start a new SOS incident |
| `POST` | `/v1/incident/{id}/triage` | Send triage answer, get next question |
| `POST` | `/v1/incident/{id}/dispatch` | Confirm dispatch to a service |
| `GET` | `/v1/incident/{id}` | Get incident status + dispatch options |
| `GET` | `/v1/services/nearby` | Find nearby emergency services |
| `POST` | `/v1/webhook/whatsapp` | WhatsApp inbound webhook |
| `POST` | `/v1/webhook/twilio/voice` | IVR voice call handler |
| `GET` | `/v1/admin/heatmap` | Anonymised incident heatmap |
| `GET` | `/v1/admin/stats` | Aggregate statistics |
| `GET` | `/health` | Health check |

## Submission

- **Hackathon**: Road Safety Hackathon 2026 — CoERS, IIT Madras
- **Track**: Emergency Response & Trauma Care (BIMSTEC)
- **Team**: RBG Labs

| Deliverable | File |
|-------------|------|
| 7-Slide Presentation | [`submission/RoadSoS_Presentation.pptx`](submission/RoadSoS_Presentation.pptx) / [`slides_final.pdf`](slides_final.pdf) |
| Solution Document | [`submission/RoadSoS_Solution_Document.docx`](submission/RoadSoS_Solution_Document.docx) |
| Demo Video | [`submission/demo.mp4`](submission/demo.mp4) |
| Assumptions | [`ASSUMPTIONS.md`](ASSUMPTIONS.md) |
| Software & Dependencies | [`SOFTWARE.md`](SOFTWARE.md) |

## License

MIT License. See [LICENSE](LICENSE).
