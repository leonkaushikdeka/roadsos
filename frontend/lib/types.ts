// TypeScript interfaces and types for RoadSoS

// Incident
export interface Incident {
  id: string;
  session_id: string;
  status: "active" | "ambulance_dispatched" | "hospital_notified" | "closed";
  severity?: "RED" | "YELLOW" | "GREEN" | "BLACK";
  severity_confidence?: number;
  victim_count: number;
  location: { lat: number; lng: number; accuracy?: number };
  dispatched_services: DispatchRecord[];
  triage_transcript: TranscriptEntry[];
  ambulance_eta_min?: number;
  started_at: string;
}

export interface TranscriptEntry {
  step: string;
  question: string;
  answer: string;
  timestamp: string;
  instruction?: string;
  severity?: string;
}

export interface DispatchRecord {
  type: "ambulance" | "police" | "fire";
  service_id: string;
  service_name: string;
  dispatched_at: string;
}

export interface EmergencyService {
  id: string;
  name: string;
  service_type: "hospital" | "ambulance" | "police" | "fire" | "blood_bank";
  trauma_grade?: number;
  distance_km: number;
  eta_min: number;
  phone?: string;
  address?: string;
  has_icu?: boolean;
  has_ventilator?: boolean;
  capacity?: Record<string, unknown>;
}

export interface TriageResponse {
  incident_id: string;
  next_question?: string;
  instruction?: string;
  severity?: string;
  severity_confidence?: number;
  triage_complete: boolean;
  dispatch_options?: {
    hospitals?: EmergencyService[];
    ambulances?: EmergencyService[];
    police?: EmergencyService[];
  };
  session_complete?: boolean;
}

// Fraud
export interface FraudCheckResult {
  allowed: boolean;
  risk_level: "low" | "medium" | "high" | "critical";
  reasons: string[];
  threat_score: number;
  action_required: "review" | "soft_block" | "hard_block" | null;
}

// Coordinates
export interface Coordinates {
  lat: number;
  lng: number;
  accuracy?: number;
}