import { atlasConfig } from '@/lib/atlas-config';

const SESSION_KEY = 'atlas_session';
const KNOWN_ROLES = new Set(['L1', 'L2', 'L3', 'SDM', 'CLIENT']);

interface SessionIdentity {
  role?: string;
  name?: string;
  email?: string;
}

export interface ActiveIncidentRecord {
  thread_id: string;
  incident_id: string;
  client_id: string;
  priority?: string;
  routing_decision?: string;
  composite_confidence_score?: number;
  execution_status?: string;
  servicenow_ticket_id?: string;
  sla_breach_time?: string;
  human_action?: string;
  human_modifier?: string;
  resolution_outcome?: string;
  mttr_start_time?: string;
  mttr_seconds?: number;
  situation_summary?: string;
  root_cause?: string;
  explanation_for_engineer?: string;
  technical_evidence_summary?: string;
  recommended_action_id?: string;
  active_veto_conditions?: string[];
  blast_radius?: Array<Record<string, unknown>>;
  recent_deployments?: Array<Record<string, unknown>>;
  semantic_matches?: Array<Record<string, unknown>>;
  alternative_hypotheses?: Array<Record<string, unknown>>;
  factor_scores?: Record<string, number>;
  confidence_factors?: Record<string, number>;
  graph_unavailable?: boolean;
  no_historical_precedent?: boolean;
  evidence_packages?: Array<Record<string, unknown>>;
  audit_trail?: Array<Record<string, unknown>>;
  stage_timeline?: IncidentStageTimelineRecord[];
}

export interface IncidentStageTimelineRecord {
  stage: 'ingest' | 'detect' | 'correlate' | 'search' | 'reason' | 'select' | 'route' | 'act' | 'learn';
  label: string;
  status: 'completed' | 'active' | 'pending' | 'blocked';
  timestamp?: string;
  reason: string;
  changed_fields?: string[];
}

export interface ActiveIncidentsResponse {
  count: number;
  incidents: ActiveIncidentRecord[];
}

export interface IncidentDetailsResponse {
  thread_id: string;
  incident: ActiveIncidentRecord;
  audit_trail_count: number;
  last_updated: string;
}

export interface AuditRecordDto {
  record_id: string;
  incident_id: string;
  client_id: string;
  timestamp: string;
  action_type: string;
  actor: string;
  action_description: string;
  confidence_score_at_time?: number | null;
  reasoning_summary?: string | null;
  outcome?: string | null;
  servicenow_ticket_id?: string | null;
  rollback_available?: number | boolean | null;
  compliance_frameworks_applied?: string[] | string | null;
}

export interface AuditResponse {
  client_id: string;
  count: number;
  records: AuditRecordDto[];
}

export interface TrustResponse {
  client_id: string;
  trust_level: number;
  progression_metrics?: {
    criteria_met?: boolean;
    incident_count?: number;
    accuracy_rate?: number;
    auto_resolution_rate?: number;
    recommendation?: string;
    [key: string]: unknown;
  };
  sla_uptime_percent?: number;
}

function buildHttpUrl(path: string, query?: Record<string, string>): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const url = new URL(normalizedPath, `${atlasConfig.apiBaseUrl}/`);
  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value) {
        url.searchParams.set(key, value);
      }
    });
  }
  return url.toString();
}

export function buildWsUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const base = atlasConfig.wsBaseUrl;
  // Ensure the base URL uses ws:// or wss:// — never http://
  const safeBase = base.replace(/^https?:\/\//, (match) => match === 'https://' ? 'wss://' : 'ws://');
  return new URL(normalizedPath, `${safeBase}/`).toString();
}

function getSessionHeaders(): Record<string, string> {
  if (globalThis.window === undefined) {
    return {};
  }

  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return {};

    const parsed = JSON.parse(raw) as SessionIdentity;
    const role = String(parsed.role || '').trim().toUpperCase();
    const actor = String(parsed.name || parsed.email || '').trim();

    const headers: Record<string, string> = {};
    if (KNOWN_ROLES.has(role)) {
      headers['X-ATLAS-ROLE'] = role;
    }
    if (actor) {
      headers['X-ATLAS-USER'] = actor;
    }
    return headers;
  } catch {
    return {};
  }
}

async function atlasGet<T>(path: string, query?: Record<string, string>): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15_000); // 15s timeout
  try {
    const response = await fetch(buildHttpUrl(path, query), {
      headers: getSessionHeaders(),
      signal: controller.signal,
    });
    if (!response.ok) {
      let detail = response.statusText;
      try { const body = await response.json(); detail = body?.detail || body?.message || detail; } catch { /* ignore */ }
      throw new Error(`ATLAS API ${response.status}: ${detail}`);
    }
    return response.json() as Promise<T>;
  } finally {
    clearTimeout(timeout);
  }
}

export function fetchActiveIncidents(clientId?: string): Promise<ActiveIncidentsResponse> {
  return atlasGet<ActiveIncidentsResponse>('/api/incidents/active', clientId ? { client_id: clientId } : undefined);
}

export function fetchIncidentDetails(threadId: string, clientId?: string): Promise<IncidentDetailsResponse> {
  return atlasGet<IncidentDetailsResponse>(
    `/api/incidents/details/${threadId}`,
    clientId ? { client_id: clientId } : undefined,
  );
}

export function fetchAuditLog(clientId: string, fromTime?: string, toTime?: string): Promise<AuditResponse> {
  return atlasGet<AuditResponse>('/api/audit', {
    client_id: clientId,
    ...(fromTime ? { from_time: fromTime } : {}),
    ...(toTime ? { to_time: toTime } : {}),
  });
}

export function fetchTrustLevel(clientId: string): Promise<TrustResponse> {
  return atlasGet<TrustResponse>(`/api/trust/${clientId}`);
}

// ─── Mutation helpers ────────────────────────────────────────────────────────

async function atlasPost<T>(path: string, body: unknown): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15_000);
  try {
    const response = await fetch(buildHttpUrl(path), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getSessionHeaders(),
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!response.ok) {
      let detail = response.statusText;
      try { const errBody = await response.json(); detail = errBody?.detail || errBody?.message || detail; } catch { /* ignore */ }
      throw new Error(`ATLAS API ${response.status}: ${detail}`);
    }
    return response.json() as Promise<T>;
  } finally {
    clearTimeout(timeout);
  }
}

export interface ApprovalPayload {
  thread_id: string;
  incident_id: string;
  client_id: string;
  approver: string;
  token?: string;
}

export interface RejectionPayload {
  thread_id: string;
  incident_id: string;
  client_id: string;
  rejector: string;
  reason: string;
}

export interface ModifyPayload {
  thread_id: string;
  incident_id: string;
  client_id: string;
  modifier: string;
  modified_parameters: Record<string, unknown>;
}

export interface ApprovalResponse {
  status: string;
  incident_id: string;
  execution_status?: string;
  resolution_outcome?: string;
}

export interface RejectionResponse {
  status: string;
  incident_id: string;
  reason: string;
}

export function approveIncident(payload: ApprovalPayload): Promise<ApprovalResponse> {
  return atlasPost<ApprovalResponse>('/api/incidents/approve', payload);
}

export function rejectIncident(payload: RejectionPayload): Promise<RejectionResponse> {
  return atlasPost<RejectionResponse>('/api/incidents/reject', payload);
}

export function modifyIncident(payload: ModifyPayload): Promise<ApprovalResponse> {
  return atlasPost<ApprovalResponse>('/api/incidents/modify', payload);
}

// ─── Playbook library ────────────────────────────────────────────────────────

export interface PlaybookRecord {
  playbook_id: string;
  name: string;
  description: string;
  action_class: number;
  auto_execute_eligible: boolean;
  estimated_resolution_minutes: number;
  target_technology: string;
  anomaly_types_addressed: string[];
  pre_validation_checks: string[];
  success_metrics: string[];
  rollback_playbook_id: string | null;
  parameters: Record<string, unknown>;
  version: string;
}

export interface PlaybookLibraryResponse {
  count: number;
  playbooks: PlaybookRecord[];
}

export function fetchPlaybookLibrary(): Promise<PlaybookLibraryResponse> {
  return atlasGet<PlaybookLibraryResponse>('/api/playbooks');
}

// ─── Trust management ────────────────────────────────────────────────────────

export interface TrustUpgradeResponse {
  client_id: string;
  new_stage?: number;
  previous_stage?: number;
  confirmed_by?: string;
  message?: string;
}

export function confirmTrustUpgrade(clientId: string): Promise<TrustUpgradeResponse> {
  return atlasPost<TrustUpgradeResponse>(`/api/trust/${clientId}/confirm-upgrade`, {});
}
