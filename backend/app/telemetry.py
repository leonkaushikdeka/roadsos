"""
OpenTelemetry instrumentation helpers for RoadSoS critical paths.
"""

from opentelemetry import trace

tracer = trace.get_tracer("roadsos")


async def instrumented_incident_initiate(incident_id: str, severity: str | None, response_time_ms: float):
    with tracer.start_as_current_span("incident_initiate") as span:
        span.set_attribute("incident_id", incident_id)
        if severity:
            span.set_attribute("severity", severity)
        span.set_attribute("response_time_ms", response_time_ms)


async def instrumented_triage_step(step: str, incident_id: str, response_time_ms: float):
    with tracer.start_as_current_span("triage_step") as span:
        span.set_attribute("step", step)
        span.set_attribute("incident_id", incident_id)
        span.set_attribute("response_time_ms", response_time_ms)


async def instrumented_dispatch_confirm(incident_id: str, severity: str | None, response_time_ms: float):
    with tracer.start_as_current_span("dispatch_confirm") as span:
        span.set_attribute("incident_id", incident_id)
        if severity:
            span.set_attribute("severity", severity)
        span.set_attribute("response_time_ms", response_time_ms)
