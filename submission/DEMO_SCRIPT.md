# RoadSoS — Demo Script for IIT Madras Road Safety Hackathon 2026

## Duration: ~3 minutes

---

### Opening (15 sec)

> "Good morning, judges. I'm [name], and this is **RoadSoS** — an AI-powered emergency response system designed to reduce road accident fatalities in Tamil Nadu."

---

### Problem Statement (20 sec)

> "Every year, over 1.5 lakh people die on Indian roads. The biggest reason? **Delayed response.** Bystanders don't know what to do, dispatchers can't find the nearest trauma center, and emergency lines get clogged with false alarms."

> "We built RoadSoS to solve all three problems — guided triage, smart dispatch, and fraud detection."

---

### Live Demo — PWA SOS Flow (60 sec)

> "Let me show you the core experience. I'm opening the PWA on a phone — no app install needed."

**Steps to walk through:**
1. **Tap the SOS button** — GPS is captured automatically
2. **AI Triage Agent starts** — asks "Are you the victim or a helper?"
3. **Walk through the triage flow:**
   - "No, not responding at all" → unconscious
   - "No, not breathing" → airway emergency
   - "Yes, heavy bleeding" → severe bleeding
   - "done" → classification complete
4. **Result: RED severity** — highest priority classification
5. **Auto-dispatch:** system finds nearest hospital (Rajiv Gandhi GMH, 3km), ambulance (108 hub, 2.1km), police
6. **ETA shown:** ambulance 6 min, hospital 8 min
7. **ICE contacts notified** automatically

> "The entire triage took 30 seconds. In a real scenario, that could be the difference between life and death."

---

### Demo — Multilingual Support (20 sec)

> "Tamil Nadu has language diversity. RoadSoS supports **5 languages** — English, Hindi, Tamil, Bengali, and Sinhala."

- Switch language to Tamil → show Tamil protocol instructions
- Show how the triage questions adapt to the selected language

> "All 7 protocol types — bleeding control, CPR, spinal precautions, shock management, fracture care, recovery position, burns first aid — are available in all 5 languages."

---

### Demo — Fraud Detection (20 sec)

> "Abuse of emergency systems is a real problem. RoadSoS has a **multi-layer fraud engine** that prevents misuse without blocking genuine emergencies."

- Open a second browser, make 4 rapid SOS requests from same phone
- Show the 403 block after threat score exceeds threshold
- Explain: rate limiting, geohash duplicate detection, impossible travel velocity

> "It's non-blocking by design — genuine emergencies always get through."

---

### Demo — Offline Mode (20 sec)

> "What if there's no network at the accident site? RoadSoS works offline."

- Toggle airplane mode on
- Show the offline indicator banner
- Open the PWA again — triage flow still works with cached protocols
- Explain service worker architecture

> "Protocols are cached on first visit. The triage FSM runs entirely client-side."

---

### Architecture Overview (15 sec)

> "On the backend, we use:"
- **FastAPI** with async PostgreSQL + PostGIS for spatial queries
- **LangGraph** for the triage decision graph with conditional edges
- **Redis** for sessions and rate limiting
- **Celery** for background tasks (data retention purge)
- **OpenTelemetry** for full observability

> "The frontend is a **Next.js PWA** with Tailwind CSS — works on any modern phone browser."

---

### Closing (15 sec)

> "To try it yourself, scan the PWA QR code. No install needed — it's a progressive web app."

> "The WhatsApp QR lets you start triage by just messaging 'SOS' to our number."

> "We believe technology should save lives, not just look impressive. Thank you."

---

## Key Talking Points for Q&A

1. **Why LangGraph?** — Deterministic FSM with LLM hooks. Can run fully mock (no GPU) or with a real model. Conditional edges handle complex triage logic.

2. **Why no paid APIs?** — All routing via OSRM (open-source). Embeddings via sentence-transformers. Fraud engine is pure algorithm.

3. **Scalability?** — Async PostgreSQL handles 10K+ concurrent incidents. Redis sessions scale horizontally. Celery workers auto-scale.

4. **Privacy?** — DPDP-compliant. Data auto-purges after retention window. Location anonymized on cleanup.

5. **Deployment?** — Railway config included (`railway.toml`). Docker Compose for local dev. Kubernetes manifests in `/k8s/`.