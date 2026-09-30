/**
 * Core type definitions for IBVAP Vision Assurance Platform (SIH26228)
 */

export type Role = "VIEWER" | "OPERATOR" | "SUPERVISOR" | "ADMIN" | "AUDITOR" | "SYSTEM";

export interface UserInfo {
  username: string;
  role: string;
  auth_mode: string;
  dev_mode?: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: string;
  username: string;
  expires_in_minutes: number;
}

export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface Detection {
  target_id: string;
  class_id: number;
  class_name: string;
  confidence: number;
  bbox: [number, number, number, number]; // [x1, y1, x2, y2]
  track_id?: number;
  provenance_ref?: string;
  assurance_status?: "VERIFIED" | "REVIEW" | "QUARANTINED";
}

export interface TelemetryFrame {
  type: string;
  camera_id: string;
  timestamp: number | string;
  measured_fps?: number;
  latency_ms?: number;
  preprocessing_ms?: number;
  inference_ms?: number;
  binding_ms?: number;
  detections: Detection[];
  tracks_count?: number;
  sequence_id?: number;
  frame_hash?: string;
  sealed_block_hash?: string;
  nonce?: string;
}

export interface Camera {
  id: string;
  name: string;
  type: string;
  rtsp_url?: string;
  status: "ONLINE" | "STANDBY" | "OFFLINE" | "ERROR";
  fps?: number;
  resolution?: string;
}

export interface ProvenanceRecord {
  sequence_id: number;
  timestamp: string;
  nonce: string;
  input_frame_hash: string;
  model_id: string;
  model_sha256: string;
  config_hash: string;
  preprocessing_hash: string;
  output_digest: string;
  previous_record_hash: string;
  provenance_hash: string;
  status: "VERIFIED" | "QUARANTINED" | "TAMPERED" | "REPLAY";
  tampered?: boolean;
  detections_count?: number;
  raw_detections?: Detection[];
}

export interface InferenceProvenanceRecord {
  record_id?: string;
  frame_id?: string;
  sequence_id?: number;
  timestamp?: string;
  input_hash?: string;
  model_hash?: string;
  previous_hash?: string;
  provenance_hash?: string;
  nonce?: string | number;
  status?: string;
  detections?: any[];
}

export interface ProvenanceVerifyResponse {
  valid: boolean;
  status: "VERIFIED" | "TAMPERED" | "REPLAY_DETECTED" | "MISMATCH";
  tampered: boolean;
  record_hash: string;
  recomputed_hash: string;
  chain_linkage_intact?: boolean;
  anomalies: string[];
  recommended_disposition: "ACCEPT" | "REVIEW" | "QUARANTINE";
  details?: Record<string, any>;
}

export interface ProvenanceChainVerificationResult {
  valid: boolean;
  records_checked?: number;
  reason?: string;
}

export interface LedgerBlock {
  sequence_id?: number;
  index?: number;
  block_id?: string;
  timestamp: string;
  camera_id?: string;
  event_type?: string;
  severity?: string;
  frame_hash?: string;
  previous_hash?: string;
  previous_block_hash?: string;
  block_hash?: string;
  merkle_root: string;
  signature?: string;
  records?: any[];
  metadata_json?: string;
  recommended_disposition?: "ACCEPT" | "REVIEW" | "QUARANTINE" | string;
  disposition?: "ACCEPT" | "REVIEW" | "QUARANTINE" | "QUARANTINED" | string | null;
}

export interface LedgerIntegrityResult {
  valid: boolean;
  total_blocks_checked?: number;
  faults?: number;
}

export interface ContributorModelManifest {
  manifest_version: string;
  manifest_id: string;
  contributor: {
    id: string;
    name: string;
    organization: string;
  };
  model: {
    model_id: string;
    architecture: string;
    format: string;
    file_name: string;
    sha256: string;
    parameter_count?: number;
  };
  preprocessing: {
    config_hash: string;
  };
  behavioral_fingerprint: {
    profile_id: string;
    digest: string;
  };
  created_at: string;
  signature?: {
    algorithm: string;
    public_key: string;
    signature: string;
  };
}

export interface ModelManifest {
  model_name: string;
  version: string;
  sha256: string;
  signature?: string;
  contributor?: any;
}

export interface ManifestVerifyResponse {
  valid: boolean;
  manifest_id: string;
  model_id: string;
  contributor_id: string;
  contributor_org: string;
  manifest_digest: string;
  checks: {
    signature: boolean;
    manifest_structure: boolean;
    model_digest_format: boolean;
    physical_file_digest?: boolean | null;
    preprocessing_binding: boolean;
    behavioral_fingerprint_binding: boolean;
    aibom_binding?: boolean | null;
  };
  failures: string[];
  limitations: string[];
}

export interface DatasetAuditResponse {
  status: string;
  verdict: "ACCEPTED" | "REVIEW" | "QUARANTINED";
  description: string;
  dataset_name: string;
  dataset_path: string;
  total_samples: number;
  corrupted_samples: number;
  near_duplicates: number;
  coordinate_anomalies: number;
  mean_sharpness_laplacian: number;
  stages: Array<{
    stage: string;
    status: string;
    detail: string;
  }>;
  timestamp: string;
}

export interface DatasetAuditResult {
  dataset_name?: string;
  format?: string;
  intake_timestamp?: string;
  total_samples?: number;
  total_bounding_boxes?: number;
  mean_sharpness?: number;
  corrupted_samples?: number;
  verdict?: "ACCEPT" | "REVIEW" | "QUARANTINE" | string;
  summary?: string;
  runtime_seconds?: number;
  contributor_key?: string;
  sample_inspections?: any[];
}

export interface AssuranceFinding {
  title?: string;
  category?: string;
  severity: "CRITICAL" | "WARNING" | "INFO" | string;
  description?: string;
  message?: string;
  target?: string;
  timestamp?: string;
}

export interface DriftReport {
  mmd_score?: number;
  ks_p_value?: number;
  verdict?: string;
}

export interface SystemTelemetry {
  backend_status?: string;
  active_streams?: number;
  inference_worker?: string;
  ledger_synced?: boolean;
}

export interface EvidenceVerifyResponse {
  incident_id?: string;
  file_path?: string;
  recorded_sha256: string;
  computed_sha256: string;
  integrity_verified: boolean;
  status: string;
  message: string;
}

export interface SystemHealth {
  status: string;
  version: string;
  services?: Record<string, any>;
}

export interface RecordedBenchmark {
  hardware: string;
  raw_fps: number;
  secured_fps: number;
  secured_latency_ms: number;
  overhead_ms: number;
  overhead_pct: number;
  hashing_latency_ms: number;
  label: string;
}

export const VERIFIED_BENCHMARK: RecordedBenchmark = {
  hardware: "RTX 5050 Laptop GPU",
  raw_fps: 66.92,
  secured_fps: 53.69,
  secured_latency_ms: 18.13,
  overhead_ms: 3.19,
  overhead_pct: 21.4,
  hashing_latency_ms: 0.562,
  label: "RECORDED BENCHMARK DATA",
};
