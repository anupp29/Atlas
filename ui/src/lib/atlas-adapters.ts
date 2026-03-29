import type { ActiveIncidentRecord, AuditRecordDto, IncidentStageTimelineRecord } from '@/lib/atlas-api';
import type {
  ActivityFeedEntry,
  AuditEntry,
  Client,
  HealthStatus,
  Incident,
  IncidentPipelineStage,
  IncidentStageTimelineEntry,
  IncidentPriority,
  IncidentStatus,
  ServiceNode,
  TrustLevel,
} from '@/types/atlas';

interface ClientMeta {
  frontendId: string;
  frontendName: string;
  backendName: string;
}

export const ATLAS_CLIENT_META: Record<string, ClientMeta> = {
  FINCORE_UK_001: {
    frontendId: 'client-financecore',
    frontendName: 'FinanceCore Holdings',
    backendName: 'FinanceCore Ltd',
  },
  RETAILMAX_EU_002: {
    frontendId: 'client-retailmax',
    frontendName: 'RetailMax Group',
    backendName: 'RetailMax EU',
  },
};

export const knownBackendClientIds = Object.keys(ATLAS_CLIENT_META);

const TRUST_LABELS: TrustLevel[] = [
  'Observation',
  'L1 Assistance',
  'L1 Automation',
  'L2 Assistance',
  'L2 Automation',
];

function normalizePriority(value: string | undefined): IncidentPriority {
  if (value === 'P1' || value === 'P2' || value === 'P3') return value;
  return 'P2';
}

function statusFromBackendState(
  routingDecision: string | undefined,
  executionStatus: string | undefined,
  humanAction: string | undefined,
  resolutionOutcome: string | undefined,
): IncidentStatus {
  if (resolutionOutcome === 'success' || executionStatus === 'success') return 'Resolved';
  if (executionStatus === 'failed' || resolutionOutcome === 'failure') return 'Failed';
  if (humanAction === 'rejected') return 'L3 Manual Resolution';
  if (humanAction === 'escalated') return 'Escalated to L2';
  if (executionStatus === 'executing') return 'Executing';
  if (routingDecision === 'L1_HUMAN_REVIEW') return 'Awaiting L1';
  if (routingDecision === 'L2_L3_ESCALATION') return 'Awaiting L2';
  if (routingDecision === 'AUTO_EXECUTE') return executionStatus === 'pending' ? 'ATLAS Analyzing' : 'Executing';
  return 'ATLAS Analyzing';
}

function timeNowPlusMinutes(minutes: number): string {
  return new Date(Date.now() + minutes * 60 * 1000).toISOString();
}

// SLA minutes by priority — configurable via env if needed
const SLA_MINUTES: Record<string, number> = {
  P1: Number(typeof window !== 'undefined' ? (window as any).__ATLAS_SLA_P1_MINS : undefined) || 15,
  P2: Number(typeof window !== 'undefined' ? (window as any).__ATLAS_SLA_P2_MINS : undefined) || 45,
  P3: Number(typeof window !== 'undefined' ? (window as any).__ATLAS_SLA_P3_MINS : undefined) || 120,
};

function inferSlaDeadline(priority: IncidentPriority, slaBreachTime?: string, fallback?: string): string {
  if (slaBreachTime) return slaBreachTime;
  if (fallback) return fallback;
  return timeNowPlusMinutes(SLA_MINUTES[priority] ?? 60);
}

function confidenceToPercent(value: number | undefined, fallback = 82): number {
  if (typeof value !== 'number' || Number.isNaN(value)) return fallback;
  if (value > 1) return Math.round(value);
  return Math.round(value * 100);
}

function parseFactorValue(value: unknown, fallback: number): number {
  if (typeof value !== 'number' || Number.isNaN(value)) return fallback;
  return confidenceToPercent(value, fallback);
}

function toServiceNode(name: string, criticality: ServiceNode['criticality'] = 'Medium'): ServiceNode {
  const slug = name.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean).join('-') || 'service';
  return {
    id: `svc-${slug}`,
    name,
    technology: 'Live service telemetry',
    health: criticality === 'High' ? 'warning' : 'healthy',
    criticality,
    triggerMetric: 'Incident confidence',
    triggerValue: 'See active incident context',
  };
}

function collectServicesFromState(state: Record<string, any> | undefined, fallback: Incident | undefined): string[] {
  const fromEvidence = Array.isArray(state?.evidence_packages)
    ? state.evidence_packages.map((pkg: Record<string, any>) => String(pkg.service_name || '')).filter(Boolean)
    : [];

  const fromBlastRadius = Array.isArray(state?.blast_radius)
    ? state.blast_radius.map((node: Record<string, any>) => String(node.name || node.service_name || '')).filter(Boolean)
    : [];

  const combined = Array.from(new Set([...fromEvidence, ...fromBlastRadius]));
  if (combined.length > 0) return combined;
  if (fallback?.affectedServices?.length) return fallback.affectedServices;
  return ['Service under investigation'];
}

function incidentHealthFromPriority(priority: IncidentPriority): HealthStatus {
  if (priority === 'P1') return 'critical';
  if (priority === 'P2') return 'warning';
  return 'healthy';
}

function displayClientName(backendClientId: string | undefined, fallback?: Incident): string {
  if (backendClientId && ATLAS_CLIENT_META[backendClientId]) {
    return ATLAS_CLIENT_META[backendClientId].frontendName;
  }
  return fallback?.clientName || 'Unknown Client';
}

function frontendClientId(backendClientId: string | undefined, fallback?: Incident): string {
  if (backendClientId && ATLAS_CLIENT_META[backendClientId]) {
    return ATLAS_CLIENT_META[backendClientId].frontendId;
  }
  return fallback?.clientId || 'client-unknown';
}

function mttrLabel(seconds: number | undefined, fallback?: string): string | undefined {
  if (typeof seconds === 'number' && seconds > 0) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs.toString().padStart(2, '0')}s`;
  }
  return fallback;
}

function inferRecommendedAction(state: Record<string, any> | undefined, fallback?: Incident): Incident['recommendedAction'] {
  const actionId = state?.recommended_action_id || 'ATLAS-ACTION-PENDING';
  return {
    playbookName: String(actionId),
    description: state?.explanation_for_engineer || 'Recommendation pending. ATLAS is finalizing remediation selection from live evidence.',
    estimatedTime: '5 minutes',
    riskClass: 'Low',
    rollbackAvailable: true,
  };
}

function inferDeploymentCorrelation(state: Record<string, any> | undefined, fallback?: Incident): Incident['deploymentCorrelation'] | undefined {
  const latestChange = Array.isArray(state?.recent_deployments) ? state.recent_deployments[0] : undefined;
  if (!latestChange) return undefined;

  return {
    changeId: String(latestChange.change_id || latestChange.id || 'UNKNOWN_CHANGE'),
    description: String(latestChange.description || latestChange.change_description || 'Recent deployment detected on affected services.'),
    deployedBy: String(latestChange.deployed_by || 'ATLAS'),
    deployedAt: String(latestChange.timestamp || ''),
    cabRiskRating: 'Low',
    daysAgo: 0,
  };
}

function inferHistoricalMatch(state: Record<string, any> | undefined): Incident['historicalMatch'] | undefined {
  const semantic = Array.isArray(state?.semantic_matches) ? state.semantic_matches : [];
  if (semantic.length === 0) return undefined;

  const top = semantic[0] || {};
  let similarityRaw = 0;
  if (typeof top.similarity_score === 'number') {
    similarityRaw = top.similarity_score;
  } else if (typeof top.score === 'number') {
    similarityRaw = top.score;
  }
  const similarity = similarityRaw > 1 ? Math.round(similarityRaw) : Math.round(similarityRaw * 100);

  return {
    incidentId: String(top.incident_id || top.id || 'HISTORICAL_MATCH'),
    occurredAt: String(top.timestamp || top.occurred_at || 'unknown'),
    similarity,
    rootCause: String(top.root_cause || top.summary || 'Historical pattern match available.'),
    resolution: String(top.resolution || top.recommendation || 'Review historical incident details.'),
  };
}

function inferAlternativeHypotheses(state: Record<string, any> | undefined): Incident['alternativeHypotheses'] {
  const alternatives = Array.isArray(state?.alternative_hypotheses) ? state.alternative_hypotheses : [];

  const normalizeEvidence = (value: unknown): string[] => {
    if (Array.isArray(value)) {
      return value.map((item) => {
        if (typeof item === 'object' && item !== null) {
          return JSON.stringify(item);
        }
        return String(item);
      });
    }
    if (value === undefined || value === null || value === '') {
      return [];
    }
    if (typeof value === 'object') {
      return [JSON.stringify(value)];
    }
    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
      return [String(value)];
    }
    return [JSON.stringify(value)];
  };

  return alternatives.map((item: Record<string, any>) => {
    const evidenceFor = normalizeEvidence(item.evidence_for);
    const evidenceAgainst = normalizeEvidence(item.evidence_against);

    return {
      hypothesis: String(item.hypothesis || 'Alternative hypothesis'),
      evidenceFor,
      evidenceAgainst,
    };
  });
}

function inferRootCauseFactors(state: Record<string, any> | undefined, confidence: number): Incident['rootCause']['factors'] {
  const factors = state?.factor_scores || {};
  const llmFactors = state?.confidence_factors || {};

  return {
    historicalAccuracy: parseFactorValue(factors.f1 ?? llmFactors.historical_accuracy, 0),
    rootCauseCertainty: parseFactorValue(factors.f2 ?? llmFactors.root_cause_certainty, confidence),
    actionSafetyClass: parseFactorValue(factors.f3 ?? llmFactors.action_safety, 0),
    evidenceFreshness: parseFactorValue(factors.f4 ?? llmFactors.evidence_freshness, 0),
  };
}

function inferPipelineStage(state: Record<string, any> | undefined, status: IncidentStatus): IncidentPipelineStage {
  const executionStatus = String(state?.execution_status || '').toLowerCase();
  const resolution = String(state?.resolution_outcome || '').toLowerCase();

  if (resolution === 'success' || status === 'Resolved') return 'learn';
  if (executionStatus === 'executing' || executionStatus === 'success' || executionStatus === 'failed') return 'act';
  if (state?.routing_decision) return 'route';
  if (state?.recommended_action_id) return 'select';
  if (state?.root_cause) return 'reason';
  if (Array.isArray(state?.semantic_matches) && state.semantic_matches.length > 0) return 'search';
  if (state?.no_historical_precedent) return 'search';
  if ((Array.isArray(state?.blast_radius) && state.blast_radius.length > 0) || state?.graph_unavailable) return 'correlate';
  if (state?.incident_priority || status !== 'ATLAS Analyzing') return 'detect';
  return 'ingest';
}

function mapStageTimeline(state: Record<string, any> | undefined): IncidentStageTimelineEntry[] | undefined {
  const timeline = state?.stage_timeline;
  if (!Array.isArray(timeline)) return undefined;
  const validStatuses = new Set(['completed', 'active', 'pending', 'blocked']);
  const normalizeChangedField = (field: unknown): string => {
    if (field === null || field === undefined) return '';
    if (typeof field === 'string') return field;
    if (typeof field === 'number' || typeof field === 'boolean' || typeof field === 'bigint') return `${field}`;
    if (typeof field === 'symbol') return field.description ? `symbol:${field.description}` : 'symbol';
    if (typeof field === 'function') return field.name ? `function:${field.name}` : 'function';
    if (typeof field === 'object') {
      try {
        return JSON.stringify(field);
      } catch {
        return 'object';
      }
    }
    return '';
  };

  return timeline
    .map((entry: IncidentStageTimelineRecord): IncidentStageTimelineEntry | null => {
      if (!entry || typeof entry !== 'object') return null;
      const stage = String(entry.stage || '').trim() as IncidentPipelineStage;
      if (!stage) return null;

      return {
        stage,
        label: String(entry.label || stage.toUpperCase()),
        status: validStatuses.has(String(entry.status)) ? (String(entry.status) as IncidentStageTimelineEntry['status']) : 'pending',
        timestamp: entry.timestamp,
        reason: String(entry.reason || ''),
        changedFields: Array.isArray(entry.changed_fields)
          ? entry.changed_fields.map((field) => normalizeChangedField(field)).filter(Boolean)
          : [],
      };
    })
    .filter((entry): entry is IncidentStageTimelineEntry => !!entry);
}

export function adaptActiveIncident(
  record: ActiveIncidentRecord,
  stateByThread: Record<string, Record<string, any>>,
  fallbackByIncidentId: Record<string, Incident>,
): Incident {
  const fallback = fallbackByIncidentId[record.incident_id];
  const liveState = {
    ...(record as unknown as Record<string, any>),
    ...stateByThread[record.thread_id],
  };

  const priority = normalizePriority(liveState?.incident_priority || record.priority || fallback?.priority);
  const status = statusFromBackendState(
    liveState?.routing_decision || record.routing_decision,
    liveState?.execution_status || record.execution_status,
    liveState?.human_action,
    liveState?.resolution_outcome,
  );

  const services = collectServicesFromState(liveState, fallback);
  const confidence = confidenceToPercent(
    liveState?.composite_confidence_score ?? record.composite_confidence_score,
    0,
  );

  const rootCauseDiagnosis = String(
    liveState?.root_cause || 'Root cause pending. ATLAS is still building evidence and causal ranking.',
  );

  const statusWithFallback = status || 'ATLAS Analyzing';
  const pipelineStage = inferPipelineStage(liveState, statusWithFallback);
  const stageTimeline = mapStageTimeline(liveState);

  return {
    id: record.incident_id,
    clientId: frontendClientId(record.client_id, fallback),
    clientName: displayClientName(record.client_id, fallback),
    priority,
    status,
    affectedServices: services,
    detectedAt: liveState?.mttr_start_time || fallback?.detectedAt || new Date().toISOString(),
    slaDeadline: inferSlaDeadline(priority, liveState?.sla_breach_time || record.sla_breach_time, fallback?.slaDeadline),
    summary: String(
      liveState?.situation_summary
        || `${priority} anomaly detected by ATLAS. Incident routing: ${record.routing_decision || 'under analysis'}.`,
    ),
    businessImpact: String(
      liveState?.technical_evidence_summary
        || 'Technical evidence summary pending while live reasoning completes.',
    ),
    services: services.map((name, index) => toServiceNode(name, index === 0 ? 'High' : 'Medium')),
    deploymentCorrelation: inferDeploymentCorrelation(liveState, fallback),
    historicalMatch: inferHistoricalMatch(liveState),
    rootCause: {
      diagnosis: rootCauseDiagnosis,
      confidence,
      factors: inferRootCauseFactors(liveState, confidence),
      vetoes: Array.isArray(liveState?.active_veto_conditions) ? liveState.active_veto_conditions : [],
    },
    alternativeHypotheses: inferAlternativeHypotheses(liveState),
    recommendedAction: inferRecommendedAction(liveState, fallback),
    executionSteps: fallback?.executionSteps,
    resolvedAt: fallback?.resolvedAt,
    mttr: mttrLabel(liveState?.mttr_seconds, fallback?.mttr),
    approvedBy: String(liveState?.human_modifier || fallback?.approvedBy || 'ATLAS'),
    threadId: record.thread_id,
    backendClientId: record.client_id,
    pipelineStage,
    stageTimeline,
    engineerExplanation: String(liveState?.explanation_for_engineer || ''),
    serviceNowTicketId: String(liveState?.servicenow_ticket_id || record.servicenow_ticket_id || ''),
  };
}

export function trustLabelFromLevel(level: number | undefined, fallback: TrustLevel): TrustLevel {
  if (typeof level !== 'number') return fallback;
  if (level < 0 || level >= TRUST_LABELS.length) return fallback;
  return TRUST_LABELS[level];
}

export function backendClientIdFromFrontend(frontendId: string): string | undefined {
  return Object.entries(ATLAS_CLIENT_META).find(([, meta]) => meta.frontendId === frontendId)?.[0];
}

export function frontendClientIdFromBackend(backendClientId: string): string | undefined {
  return ATLAS_CLIENT_META[backendClientId]?.frontendId;
}

export function frontendClientNameFromBackend(backendClientId: string): string {
  return ATLAS_CLIENT_META[backendClientId]?.frontendName || backendClientId;
}

export function buildClientsFromLiveData(
  baseClients: readonly Client[],
  activeIncidents: Incident[],
  trustByBackendClientId: Record<string, number>,
): Client[] {
  const activeByFrontendClient = new Map<string, Incident[]>();

  activeIncidents.forEach((incident) => {
    if (!activeByFrontendClient.has(incident.clientId)) {
      activeByFrontendClient.set(incident.clientId, []);
    }
    activeByFrontendClient.get(incident.clientId)?.push(incident);
  });

  return baseClients.map((client) => {
    const activeIncidentsForClient = activeByFrontendClient.get(client.id) || [];
    const backendClientId = backendClientIdFromFrontend(client.id);
    const updatedTrust = backendClientId
      ? trustLabelFromLevel(trustByBackendClientId[backendClientId], client.trustLevel)
      : client.trustLevel;

    const hasP1 = activeIncidentsForClient.some((incident) => incident.priority === 'P1' && incident.status !== 'Resolved');
    let health: HealthStatus = 'healthy';
    if (activeIncidentsForClient.length > 0) {
      health = hasP1 ? 'critical' : 'warning';
    }

    return {
      ...client,
      health,
      activeIncidents: activeIncidentsForClient.filter((incident) => incident.status !== 'Resolved').length,
      trustLevel: updatedTrust,
      lastActivity: activeIncidentsForClient.length > 0 ? 'Live now' : client.lastActivity,
    };
  });
}

function toDisplayTimestamp(input: string | undefined): string {
  if (!input) return new Date().toLocaleTimeString('en-GB', { hour12: false });
  const parsed = new Date(input);
  if (Number.isNaN(parsed.getTime())) return input;
  return parsed.toLocaleTimeString('en-GB', { hour12: false });
}

function inferActivityDescription(event: Record<string, any>): string {
  if (event.message) return String(event.message);
  if (event.type === 'orchestrator_node') {
    const stage = String(event?.meta?.stage || '').toUpperCase();
    const changed = Array.isArray(event?.meta?.changed_fields)
      ? event.meta.changed_fields.map((field: unknown) => {
          if (field === null || field === undefined) return '';
          if (typeof field === 'string') return field;
          if (typeof field === 'number' || typeof field === 'boolean' || typeof field === 'bigint') {
            return `${field}`;
          }
          if (typeof field === 'symbol') {
            return field.description ? `symbol:${field.description}` : 'symbol';
          }
          if (typeof field === 'function') {
            return field.name ? `function:${field.name}` : 'function';
          }
          if (typeof field === 'object') {
            try {
              return JSON.stringify(field);
            } catch {
              return 'object';
            }
          }
          return '';
        }).filter(Boolean)
      : [];
    const changedPreview = changed.slice(0, 4).join(', ');
    if (stage && changedPreview) {
      return `${stage}: ${String(event?.meta?.node || 'node')} updated ${changedPreview}.`;
    }
    if (stage) {
      return `${stage}: ${String(event?.meta?.node || 'node')} completed.`;
    }
  }
  if (event.type === 'incident_created') {
    return `Incident ${event.incident_id || ''} created with routing ${event.routing || 'pending'}.`;
  }
  if (event.type === 'human_action') {
    return `Human action: ${event.action || 'updated'} on incident ${event.incident_id || ''}.`;
  }
  if (event.type === 'cmdb_change') {
    return `CMDB change ${event.change_id || ''} detected for ${event.service || 'service'}.`;
  }
  return `ATLAS event: ${event.type || 'update'}.`;
}

export function adaptActivityEvent(event: Record<string, any>): ActivityFeedEntry | null {
  if (!event || event.type === 'ping') return null;

  const backendClientId = String(event.client_id || '');
  const priority = normalizePriority(event.priority);
  const health = event.priority ? incidentHealthFromPriority(priority) : 'healthy';

  return {
    id: String(event.id || `${event.type || 'activity'}-${event.incident_id || Date.now()}`),
    timestamp: toDisplayTimestamp(event.timestamp),
    clientName: backendClientId ? frontendClientNameFromBackend(backendClientId) : 'ATLAS Platform',
    clientHealth: health,
    description: inferActivityDescription(event),
    priority: event.priority ? priority : undefined,
  };
}

function normalizeAuditOutcome(outcome: string | undefined): AuditEntry['outcome'] {
  const value = (outcome || '').toLowerCase();
  if (value.includes('rollback')) return 'Rolled Back';
  if (value.includes('fail') || value.includes('error')) return 'Failed';
  return 'Success';
}

function normalizeAuditConfidence(raw: number | null | undefined): number | undefined {
  if (typeof raw !== 'number' || Number.isNaN(raw)) return undefined;
  if (raw > 1) return Math.round(raw);
  return Math.round(raw * 100);
}

function normalizeAuditTimestamp(timestamp: string): string {
  if (!timestamp) return new Date().toISOString();
  // Handle both ISO (with T) and space-separated formats
  const normalized = timestamp.includes('T') ? timestamp : timestamp.replace(' ', 'T');
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) return timestamp;
  // Return full ISO string — display formatting happens in the UI
  return parsed.toISOString();
}

export function adaptAuditRecord(record: AuditRecordDto): AuditEntry {
  const frameworks = Array.isArray(record.compliance_frameworks_applied)
    ? record.compliance_frameworks_applied
    : [];

  return {
    id: record.record_id,
    timestamp: normalizeAuditTimestamp(record.timestamp),
    incidentId: record.incident_id,
    client: frontendClientNameFromBackend(record.client_id),
    actionType: record.action_type,
    actor: record.actor || 'ATLAS',
    outcome: normalizeAuditOutcome(record.outcome || undefined),
    confidence: normalizeAuditConfidence(record.confidence_score_at_time),
    details: record.reasoning_summary
      ? {
          reasoningChain: record.reasoning_summary,
          vetoes: frameworks.map((framework) => `${framework} policy applied`),
          playbookSteps: [record.action_description],
          metricValues: {},
        }
      : undefined,
  };
}
