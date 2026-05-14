# RoadSoS — AI-Powered Emergency Response System

> The AI Companion that turns every bystander into a first responder.
> Saving lives in the Golden Hour through AI-driven triage, location-aware emergency dispatch, and voice-first accessibility.

RoadSoS is an AI-powered emergency response system accessible through a **PWA**, **WhatsApp**, **voice call**, and **SMS fallback**. With a single tap — or even a voice command from an injured person — it orchestrates the entire chain of survival from accident to admission.

## Quick Start

### Run Locally in 5 Minutes

Prerequisites: Docker Desktop, Git

```bash
# Clone the repository
git clone https://github.com/your-org/roadsos.git
cd roadsos

# Copy the environment template and edit (only needed for WhatsApp/Twilio)
cp .env.example .env

# Start all services with Docker Compose
docker compose -f infra/docker-compose.yml up -d

# Install Python dependencies and seed the database
cd backend && pip install -r requirements.txt && python -m app.seed.run

# Open the app
# PWA: http://localhost:3000
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

**Note:** The system uses mock LLM by default (`USE_MOCK_LLM=true`), so no GPU or model download is needed. WhatsApp and Twilio integrations work in mock mode — just set your credentials in `.env` to enable real messaging.

## Architecture

```
┌─────────────────────────────────────────────────┐
│              PRESENTATION LAYER                  │
│  PWA  •  WhatsApp Bot  •  IVR  •  SMS  •  AR    │
├─────────────────────────────────────────────────┤
│              AI ORCHESTRATION LAYER               │
│  Triage LLM  •  ASR/TTS  •  Translation  •  RAG  │
├─────────────────────────────────────────────────┤
│                  SERVICES LAYER                   │
│  Dispatch  •  Geocoder  •  Hospital Index  •  …  │
├─────────────────────────────────────────────────┤
│              DATA & INTEGRATION LAYER             │
│  PostgreSQL+PostGIS  •  Redis  •  pgvector       │
│  APIs: 108/112  •  FHIR  •  OSM  •  Twilio      │
└─────────────────────────────────────────────────┘
```

## Features

- **Smart Dispatch Engine** — Multi-criteria ranking (trauma grade, ICU beds, real-time traffic)
- **AI Triage Agent** — Fine-tuned on START + CRAMS protocols with ReAct state machine
- **Voice & Vernacular** — 8+ BIMSTEC languages with code-mixed speech support
- **Location Intelligence** — GPS + Plus Codes + what3words fallback, highway-vs-urban context
- **Visual First-Aid** — Canvas-based AR overlay showing pressure points and spinal precautions
- **Multi-Channel** — PWA (no app store), WhatsApp, IVR, SMS
- **Offline-First** — Cached protocols, SMS dispatch grammar for GSM dead zones
- **Privacy by Design** — Auto-purge 24h post-incident, DPDP Act 2023 compliant
- **Public Dashboard** — Anonymised heatmaps → black-spot identification for road authorities

## Tech Stack

| Layer | Choice |
|-------|--------|
| Frontend | Next.js 14 + Tailwind + TypeScript (PWA) |
| Backend | FastAPI (Python) + Pydantic |
| Database | PostgreSQL 16 + PostGIS + pgvector |
| AI/ML | Llama 3.1 8B (LoRA) / Mistral 7B · Whisper-small · IndicTrans2 |
| LLM Serving | vLLM (A10G) |
| Voice | Twilio + AI4Bharat TTS |
| Maps | OpenStreetMap + OSRM (self-hosted) |
| Messaging | WhatsApp Business Cloud API |
| Infra | Docker · Kubernetes (k3s) · ArgoCD |

## Project Structure

```
roadsos/
├── frontend/           # Next.js PWA
├── backend/            # FastAPI API
│   └── app/
│       ├── routes/     # Incident, services, webhook, admin APIs
│       ├── models/     # SQLAlchemy ORM
│       ├── schemas/    # Pydantic DTOs
│       ├── services/   # Triage, dispatch, notifications
│       └── seed/       # TN seed data (240+ hospitals, 1200+ ambulances)
├── agent/              # LangGraph triage agent
├── infra/              # Docker Compose, k8s
└── seed_data/          # CSV + SQL dumps
```

## Submission

- **Track**: RoadSoS — Emergency Response & Trauma Care
- **Organiser**: Centre of Excellence for Road Safety (CoERS), IIT Madras
- **Stage**: Stage 1 — Solution Submission
- **Submitted via**: Unstop (deadline: 15 June 2026)

## License

Hackathon submission — CoERS, IIT Madras Road Safety Hackathon 2026.
