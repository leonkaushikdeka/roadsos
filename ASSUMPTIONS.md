# RoadSoS — Assumptions & Limitations

## Data Assumptions

1. **Hospital coordinates** are accurate as of the OpenStreetMap Q1 2026 snapshot for Tamil Nadu. Actual coordinates may drift over time as facilities relocate.

2. **Hospital trauma grades** (1–4) are assigned based on published government classifications (NHA, state health department bulletins) where available. Where not published, trauma grade is inferred from bed count, ICU availability, and specialist coverage. This inference may not reflect actual trauma certification.

3. **Ambulance dispatch points** are modelled as static hub locations based on GVK EMRI 108 network data. Actual ambulance positions are dynamic — a real deployment would use real-time GPS telemetry.

4. **Bed availability** is seeded as static capacity. Live FHIR-based bed data requires hospital API integration which is not available in all BIMSTEC regions. The system gracefully falls back to static capacity with an `available_beds: unknown` status.

5. **Traffic-based ETA calculations** use OSRM routing with default speed profiles. Real-time traffic data integration (via Mapbox/GMap) is stubbed — in production, ETAs will vary with actual road conditions.

6. **Phone numbers** for emergency services are sourced from public directories and OpenStreetMap. They have not been individually verified for every listing. The seed data includes a `verified` flag; only ~60% of seed entries are marked verified.

## Connectivity Assumptions

7. **Offline mode**: The PWA caches first-aid protocols and a local copy of the top 100 hospitals by state. SMS dispatch uses a deterministic 160-character incident grammar. This works with 1 bar of GSM signal. No internet is required for the initial SOS trigger via SMS.

8. **WhatsApp API**: The WhatsApp Business Cloud API is free for service-to-user messaging within the 24-hour service window. The webhook handler assumes standard Meta webhook verification and message formats.

9. **IVR fallback**: Twilio Programmable Voice with speech recognition. Assumes the user speaks one of the supported languages (EN, HI, BN, TA, SI, MY, NE, DZ, TH). Unrecognised speech retries once then routes to a `conscious/not-conscious` DTMF menu.

## Regulatory & Liability Assumptions

10. **No medical diagnosis**: RoadSoS explicitly states "I am an AI assistant" at the start of every session. It provides first-aid instructions, never medical diagnoses. All instructions are retrieved from a vetted protocol corpus using RAG, never generated freely.

11. **Data retention**: Location data is auto-purged 24 hours after incident closure. Health observations are stored only with explicit post-incident consent and auto-purged after 30 days. Aligned with DPDP Act 2023 and GDPR principles.

12. **Human escalation**: Any incident classified as RED severity, or where LLM confidence falls below 0.78, is immediately routed to a human dispatcher. In the MVP, this triggers a notification — in production it would ring a dispatch console.

13. **Emergency override**: The SOS button and WhatsApp trigger bypass all authentication. Identity capture is deferred to post-incident. This is intentional — requiring login during an emergency costs lives.

## Technical Limitations

14. **Mock LLM**: The triage agent uses a deterministic state machine by default (`USE_MOCK_LLM=true`). Switching to `USE_MOCK_LLM=false` requires a running vLLM instance with Llama 3.1 8B (A10G GPU recommended). The RAG protocol retrieval pipeline uses sentence-transformers for embedding — this works CPU-only but benefits from GPU.

15. **AR overlay**: The camera-based AR first-aid assistant is implemented as a canvas overlay with pose detection stubs. Full MediaPipe Pose integration for real-time body tracking requires a device with WebGL2 support.

16. **Multi-language**: ASR uses Whisper-small fine-tuned on BIMSTEC accents (stub — uses English model by default). Translation uses IndicTrans2 where available, falls back to Google Translate API. Code-mixed input (e.g. "bachao, blood aa raha hai") is handled by treating the dominant language as the session language.

17. **Highway dead zones**: SMS-based dispatch via deterministic grammar works with any SMS-capable network. The grammar encodes: incident_id (8 chars), lat/lng (12 chars each), severity (1 char), victim_count (2 chars), service_type (1 char). Total: ~36 chars, well within 160-char SMS limit.

18. **Scalability**: The current stack handles ~100 concurrent triage sessions on a single A10G GPU with vLLM. Horizontal scaling requires Kubernetes + Redis session sharding.

## Deployment Assumptions

19. The system is deployed as Docker containers. Production deployment uses k3s on edge nodes at state control centres.

20. The seed database covers Tamil Nadu as a demonstrable region. Extending to other BIMSTEC states/countries requires updating the seed scripts with local hospital, ambulance, and police data.

21. OSM + OSRM routing engine is self-hosted. For a first-time deploy, expect ~2 hours to download the India region OSM extract and build the routing graph.

---

*Last updated: May 2026*
*RoadSoS — CoERS, IIT Madras Hackathon Submission*
