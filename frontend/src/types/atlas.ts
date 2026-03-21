// ─────────────────────────────────────────────────────────────────────────────
// ATLAS Frontend Type Contracts
// Mirrors the Python dataclasses in the backend data contracts exactly.
// Every field name matches the backend schema — no aliasing.
// ─────────────────────────────────────────────────────────────────────────────

export interface EvidencePackage {
  evidence_id: string
  agent_id: string
  client_id: string
  service_name: string
  anomaly_type: string
  detection_confidence: number
  shap_feature_values: Record<string, number>
  conformal_interval: { lower: number; upper: number; confidence_level: number }
  baseline_mean: number
  baseline_stddev: number
  current_value: number
  deviation_sigma: number
  supporting_log_samples: string[]
  preliminary_hypothesis: string
  severity_classification: 'P1' | 'P2' | 'P3'
  detection_timestamp: string
}

export interface AlternativeHypothesis {
  hypothesis: string
  evidence_for: string
  evidence_against: string
  confidence: number
}

export interface BlastRadiusNode {
  name: string
  criticality: string
  breach_threshold_minutes: number | null
  tech_type?: string
}

export interface DeploymentRecord {
  change_id: string
  change_description: string
  deployed_by: string
  timestamp: string
  cab_risk_rating: string
}

export interface HistoricalMatch {
  incident_id: string
  root_cause: string
  resolution: string
  mttr_minutes: number
  resolution_playbook: string
  resolved_by: string
  similarity_score: number
  double_confirmed: boolean
}

export interface EarlyWarningSignal {
  service_name: string
  deviation_sigma: number
  trend: 'rising' | 'stable' | 'falling'
  detected_at: string
}

export interface AuditEntry {
  timestamp: string
  action_type: string
  actor: string
  action_description: string
  outcome: string
}

// Full incident state — mirrors AtlasState TypedDict from backend
export interface AtlasState {
  client_id: string
  incident_id: string
  thread_id: string
  evidence_packages: EvidencePackage[]
  correlation_type: 'CASCADE_INCIDENT' | 'ISOLATED_ANOMALY'
  blast_radius: BlastRadiusNode[]
  recent_deployments: DeploymentRecord[]
  historical_graph_matches: HistoricalMatch[]
  semantic_matches: HistoricalMatch[]
  root_cause: string
  recommended_action_id: string
  alternative_hypotheses: AlternativeHypothesis[]
  composite_confidence_score: number
  active_veto_conditions: string[]
  routing_decision: 'AUTO_EXECUTE' | 'L1_HUMAN_REVIEW' | 'L2_L3_ESCALATION' | ''
  servicenow_ticket_id: string
  execution_status: string
  audit_trail: AuditEntry[]
  mttr_start_time: string
  mttr_seconds: number
  sla_breach_time: string
  early_warning_signals: EarlyWarningSignal[]
  human_action: string
  human_modifier: string
  human_rejection_reason: string
  resolution_outcome: 'success' | 'failure' | 'partial' | ''
  recurrence_check_due_at: string
  // UI-derived fields
  incident_priority?: 'P1' | 'P2' | 'P3' | 'P4'
  situation_summary?: string
  graph_traversal_path?: GraphNode[]
}

export interface GraphNode {
  id: string
  name: string
  type: 'service' | 'deployment' | 'incident' | 'infrastructure'
  status: 'normal' | 'warning' | 'affected' | 'critical'
  properties: Record<string, string | number | boolean>
}

export interface GraphEdge {
  source: string
  target: string
  relationship: string
}

// Activity feed entry — from WS /ws/activity
export interface ActivityEntry {
  id: string
  type:
    | 'agent_detection'
    | 'orchestrator_node'
    | 'human_action'
    | 'veto_fired'
    | 'resolution'
    | 'early_warning'
    | 'execution'
    | 'cmdb_change'
    | 'incident_created'
  timestamp: string
  component: string
  message: string
  client_id?: string
  meta?: Record<string, string | number | boolean>
}

// Client health — from WS /ws/incidents/{client_id}
export interface ClientHealth {
  client_id: string
  client_name: string
  region: string
  health_status: 'healthy' | 'warning' | 'incident'
  active_incident_count: number
  sla_uptime_percent: number
  trust_level: number
  trust_stage_name: string
  incidents_to_next_stage: number
  compliance_frameworks: string[]
  tech_stack: string[]
}

// WebSocket message envelope
export type WSMessage =
  | { type: 'ping' }
  | { type: 'new_incident'; thread_id: string; incident_id: string; priority: string; routing_decision: string; composite_confidence_score: number; timestamp: string; client_id: string }
  | { type: 'incident_approved'; incident_id: string; thread_id: string; execution_status: string; timestamp: string }
  | { type: 'active_incidents'; incidents: AtlasState[] }
  | { type: 'log_line'; client_id: string; line: string; severity: string; timestamp: string; source: string }
  | ActivityEntry

export type ConnectionStatus = 'connected' | 'reconnecting' | 'disconnected'
