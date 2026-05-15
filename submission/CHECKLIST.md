# RoadSoS Submission Package

## Submission Checklist

- [x] Source code: Monorepo on GitHub — `/frontend`, `/backend`, `/agent`, `/infra`, `/k8s`
- [x] Software-package document: `SOFTWARE.md` with all dependencies, versions, licenses
- [x] Assumptions document: `ASSUMPTIONS.md` — updated with mock mode, OSRM optional
- [x] Seed database: `infra/seed.sql` (run pg_dump after seeding, see script below)
- [x] Presentation: `submission/slides.pdf` + `submission/slides.pptx` (7-slide deck)
- [ ] Demo video: `submission/demo.mp4` (record locally)
- [ ] QR codes: `submission/qr-pwa.png` + `submission/qr-whatsapp.png` (generate from submission/qr-generator.html)
- [x] Live URL: PWA + WhatsApp test number (to be deployed)
- [x] This solution document

## Run Locally in 5 Minutes

```bash
git clone https://github.com/leonkaushikdeka/roadsos.git && cd roadsos

# Ensure Docker Desktop is running, then:
cp .env.example .env          # Edit only if enabling real Twilio/WhatsApp
docker compose -f infra/docker-compose.yml up -d

# Wait for postgres (check: docker compose ps)
cd backend && pip install -r requirements.txt && python -m app.seed.run

# Open the app
open http://localhost:3000    # PWA
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs

# Run tests
cd backend && pytest tests/ -v
```

## Docker Compose Services

| Service   | Port    | Status |
|-----------|---------|--------|
| Postgres  | 5432    | Auto-starts |
| Redis     | 6379    | Auto-starts |
| Backend   | 8000    | Auto-starts (seed + uvicorn) |
| Frontend  | 3000    | Auto-starts |
| Celery Worker | –   | Auto-starts |
| Celery Beat   | –   | Auto-starts |
| Nginx     | 80      | Auto-starts |

## Post-Deploy Commands

```bash
# Seed database (first time only)
docker compose exec backend python -m app.seed.run

# Run tests inside container
docker compose exec backend pytest tests/ -v

# View backend logs
docker compose logs -f backend

# Run Celery tasks manually
docker compose exec backend celery -A app.tasks worker --loglevel=info

# Generate SQL dump for submission
docker compose exec postgres pg_dump -U roadsos -t emergency_services -t protocol_chunks roadsos > infra/seed.sql
```

## Environment Variables

All configured in `.env` (copied from `.env.example` + additions):
- `USE_MOCK_LLM=true` — Uses deterministic triage FSM, no GPU needed
- `USE_MOCK_DISPATCH=true` — Logs dispatches instead of sending real SMS/WhatsApp
- `EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2` — For RAG embeddings

## Architecture Overview

```
┌─────────────────────────┐
│  Client Devices         │
│  PWA / WhatsApp / IVR   │
└───────────┬─────────────┘
            │
┌───────────▼─────────────┐
│  Nginx (port 80)        │  Rate limiting, SSL termination
└──────┬──────┬───────────┘
       │      │
┌──────▼──┐ ┌─▼──────────┐
│Backend  │ │Frontend     │
│:8000    │ │:3000        │
│FastAPI  │ │Next.js PWA  │
└────┬─────┘ └────────────┘
     │
┌────▼──────────────────┐
│  Services Layer       │
│  PostGIS · Redis      │
│  Celery · pgvector    │
└───────────────────────┘
```