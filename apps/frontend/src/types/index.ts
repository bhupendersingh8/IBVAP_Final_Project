export interface Camera {
  id: string;
  name: string;
  scenario: string;
  enabled: boolean;
  created_at: string;
}

export interface Incident {
  id: string;
  camera_id: string;
  timestamp: string;
  event_type: string;
  severity: 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  confidence: number;
  explanation?: string;
  evidence_reference?: string | null;
  sha256?: string | null;
  status?: 'NEW' | 'ACKNOWLEDGED' | 'INVESTIGATING' | 'RESOLVED';
  acknowledged: boolean;
  acknowledged_by?: string | null;
  acknowledged_at?: string | null;
}

export interface Feedback {
  incident_id: string;
  label: 'TRUE_INTRUSION' | 'FALSE_ALARM' | 'UNSURE';
  notes?: string;
}

export interface ANPRObservationRecord {
  id: string;
  camera_id: string;
  track_id: number;
  vehicle_class: string;
  plate_text: string | null;
  plate_confidence: number;
  status: string;
  consistent_readings: number;
  timestamp: string;
  evidence_path?: string | null;
  evidence_sha256?: string | null;
  model_version: string;
  ocr_engine: string;
}

export interface ZonePoint {
  x: number;
  y: number;
}

export interface Zone {
  zone_id: string;
  name: string;
  camera_id: string;
  zone_type: string;
  enabled: boolean;
  color: string;
  points: ZonePoint[];
}

export interface LedgerAuditResult {
  ledger_verified: boolean;
  corrupted_sequence_id: number | null;
  audit_message: string;
  timestamp: string;
}
