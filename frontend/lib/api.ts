/**
 * RoadSoS API Client — typed fetch wrapper for all API calls.
 *
 * Supports offline fallback, retry logic, and request tracing.
 */

const API_BASE = typeof window !== "undefined"
  ? (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
  : (process.env.API_URL || "http://localhost:8000");

const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 1000;

type Method = "GET" | "POST" | "PUT" | "DELETE" | "PATCH";

interface ApiOptions extends Omit<RequestInit, "method"> {
  retries?: number;
}

/**
 * Core fetch with retry, timeout, and offline detection.
 */
async function apiFetch<T>(
  path: string,
  options: ApiOptions & { method?: Method } = {},
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const method = options.method || "GET";
  const retries = options.retries ?? MAX_RETRIES;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000);

      const response = await fetch(url, {
        ...options,
        method,
        headers: {
          "Content-Type": "application/json",
          "X-Client": "RoadSoS-Web",
          "X-Request-ID": crypto.randomUUID(),
          ...options.headers,
        },
        signal: controller.signal,
        credentials: "omit",
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorBody = await response.text().catch(() => "");
        const error = new Error(
          errorBody ? JSON.stringify(JSON.parse(errorBody).error || errorBody) : `HTTP ${response.status}`,
        );
        (error as any).status = response.status;

        if (response.status >= 500 && attempt < retries) {
          await delay(Math.pow(2, attempt) * RETRY_DELAY_MS);
          continue; // Retry on server errors
        }
        throw error;
      }

      // Handle 204 No Content
      if (response.status === 204) return null as unknown as T;

      const text = await response.text();
      if (!text) return null as unknown as T;
      return JSON.parse(text) as T;
    } catch (err: any) {
      if (err.name === "AbortError" && attempt < retries) {
        console.warn(`[RoadSoS] Request timeout, retry ${attempt + 1}/${retries}: ${path}`);
        continue;
      }

      // Offline detection
      if (err.message?.includes("Failed to fetch") || err.message?.includes("ERR_")) {
        console.error(`[RoadSoS] Network error on ${path}:`, err.message);
        throw new Error("No network connection. Please check your connection and try again.");
      }

      throw err;
    }
  }

  throw new Error("Too many retries. Please try again.");
}

function delay(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

// ─── Exported client methods ────────────────────────────────────────────────

export const roadsosApi = {
  /** Start a new SOS incident */
  initiateIncident: (data: {
    lat: number;
    lng: number;
    location_accuracy_m: number;
    channel: string;
    language: string;
    phone?: string;
    victim_count?: number;
  }) =>
    apiFetch<{
      incident_id: string;
      session_id: string;
      triage_state: string;
      first_question: string;
      language: string;
    }>("/v1/incident/initiate", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Start triage for an existing incident (get first question) */
  startTriage: (incidentId: string) =>
    apiFetch<{
      incident_id: string;
      session_id: string;
      triage_state: string;
      first_question: string;
      language: string;
    }>(`/v1/incident/${incidentId}/start`, {
      method: "GET",
    }),

  /** Send a triage answer and get the next step */
  sendTriage: (incidentId: string, answer: string) =>
    apiFetch<{
      incident_id: string;
      next_question?: string;
      instruction?: string;
      severity?: string;
      severity_confidence?: number;
      triage_complete: boolean;
      dispatch_options?: {
        hospitals?: any[];
        ambulances?: any[];
        police?: any[];
      };
      session_complete?: boolean;
    }>(`/v1/incident/${incidentId}/triage`, {
      method: "POST",
      body: JSON.stringify({ incident_id: incidentId, answer }),
    }),

  /** Confirm dispatch to a specific service */
  confirmDispatch: (incidentId: string, serviceId: string) =>
    apiFetch<{
      incident_id: string;
      service_id: string;
      service_name: string;
      eta_min: number;
      status: string;
      message: string;
    }>(`/v1/incident/${incidentId}/dispatch`, {
      method: "POST",
      body: JSON.stringify({
        incident_id: incidentId,
        service_id: serviceId,
        confirm: true,
      }),
    }),

  /** Get incident status */
  getIncidentStatus: (incidentId: string) =>
    apiFetch<{
      incident_id: string;
      status: string;
      severity?: string;
      victim_count?: number;
      dispatched_services: any[];
      dispatch_options?: any;
      ambulance_eta_min?: number;
      hospital_eta_min?: number;
      triage_transcript: any[];
      started_at: string;
      closed_at?: string;
      lat?: number;
      lng?: number;
    }>(`/v1/incident/${incidentId}`),

  /** Search nearby emergency services */
  getNearbyServices: (lat: number, lng: number, serviceType: string, radius?: number) =>
    apiFetch<{
      services: any[];
      total: number;
    }>(
      `/v1/services/nearby?lat=${lat}&lng=${lng}&service_type=${serviceType}&radius_km=${radius || 25}`,
    ),

  /** Get service live status */
  getServiceStatus: (serviceId: string) =>
    apiFetch<{
      service_id: string;
      service_name: string;
      available_beds?: number;
      available_icu_beds?: number;
      ambulances_available?: number;
      avg_wait_min?: number;
      status: string;
      last_updated?: string;
    }>(`/v1/services/${serviceId}/status`),

  /** Get offline protocol bundle for SW precaching */
  getOfflineBundle: (lang: string = "en") =>
    apiFetch<{
      lang: string;
      count: number;
      protocols: Array<{
        id: number;
        source: string;
        language: string;
        type: string;
        text: string;
        tags: string[];
      }>;
    }>(`/v1/protocols/offline-bundle?lang=${lang}`),

  /** Get incident heatmap data (admin) */
  getHeatmap: (days?: number) =>
    apiFetch<{ incidents: any[]; total: number }>(
      `/v1/admin/heatmap?days=${days || 30}`,
    ),

  /** Get aggregate stats (admin) */
  getStats: (days?: number) =>
    apiFetch<{
      total_incidents: number;
      red_count: number;
      yellow_count: number;
      green_count: number;
      closed_count: number;
      avg_eta_min: number;
      period_days: number;
    }>(`/v1/admin/stats?days=${days || 30}`),

  /** Fetch ALL service types near a location in one call */
  getAllNearbyServices: (lat: number, lng: number, radius?: number) =>
    apiFetch<{
      services: Record<string, any[]>;
      total: number;
      radius_km: number;
    }>(`/v1/services/all-nearby?lat=${lat}&lng=${lng}&radius_km=${radius || 25}`),

  /** Get emergency numbers for a country or all countries */
  getEmergencyNumbers: (countryCode?: string) =>
    apiFetch<any>(
      `/v1/services/emergency-numbers${countryCode ? `?country_code=${countryCode}` : ""}`,
    ),
};