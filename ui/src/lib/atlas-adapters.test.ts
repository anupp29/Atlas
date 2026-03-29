import { describe, expect, it } from 'vitest';
import type { ActiveIncidentRecord } from '@/lib/atlas-api';
import { adaptActiveIncident } from '@/lib/atlas-adapters';

describe('adaptActiveIncident', () => {
  it('renders distinct reasoning and action for distinct incidents', () => {
    const finRecord: ActiveIncidentRecord = {
      thread_id: 'thread-fin-1',
      incident_id: 'INC-FIN-001',
      client_id: 'FINCORE_UK_001',
      priority: 'P1',
      routing_decision: 'L1_HUMAN_REVIEW',
      composite_confidence_score: 0.94,
      execution_status: 'pending',
    };

    const retailRecord: ActiveIncidentRecord = {
      thread_id: 'thread-retail-1',
      incident_id: 'INC-RTL-001',
      client_id: 'RETAILMAX_EU_002',
      priority: 'P2',
      routing_decision: 'L2_L3_ESCALATION',
      composite_confidence_score: 0.81,
      execution_status: 'pending',
    };

    const stateByThread: Record<string, Record<string, unknown>> = {
      'thread-fin-1': {
        thread_id: 'thread-fin-1',
        incident_priority: 'P1',
        routing_decision: 'L1_HUMAN_REVIEW',
        situation_summary: 'Payment gateway latency spike detected.',
        root_cause: 'Hikari connection pool exhausted after config drift.',
        technical_evidence_summary: 'Pool at 94% utilization with repeated timeout exceptions.',
        recommended_action_id: 'connection-pool-recovery-v2',
        factor_scores: { f1: 0.93, f2: 0.9, f3: 0.95, f4: 0.88 },
        alternative_hypotheses: [
          {
            hypothesis: 'Traffic surge only',
            evidence_for: ['p95 traffic +8%'],
            evidence_against: ['connection timeout stack traces present'],
          },
        ],
      },
      'thread-retail-1': {
        thread_id: 'thread-retail-1',
        incident_priority: 'P2',
        routing_decision: 'L2_L3_ESCALATION',
        situation_summary: 'Redis memory pressure and eviction storm observed.',
        root_cause: 'Analytics namespace flooded shared Redis cluster.',
        technical_evidence_summary: 'Evictions up 40x and catalog cache hit ratio down to 41%.',
        recommended_action_id: 'redis-memory-recovery-v1',
        factor_scores: { f1: 0.78, f2: 0.82, f3: 0.84, f4: 0.76 },
        alternative_hypotheses: [
          {
            hypothesis: 'Redis memory leak',
            evidence_for: ['steady memory climb'],
            evidence_against: ['namespace key growth matches analytics rollout'],
          },
        ],
      },
    };

    const finIncident = adaptActiveIncident(finRecord, stateByThread as Record<string, Record<string, any>>, {} as Record<string, any>);
    const retailIncident = adaptActiveIncident(retailRecord, stateByThread as Record<string, Record<string, any>>, {} as Record<string, any>);

    expect(finIncident.rootCause.diagnosis).not.toEqual(retailIncident.rootCause.diagnosis);
    expect(finIncident.summary).not.toEqual(retailIncident.summary);
    expect(finIncident.recommendedAction.playbookName).not.toEqual(retailIncident.recommendedAction.playbookName);
    expect(finIncident.alternativeHypotheses[0]?.hypothesis).not.toEqual(retailIncident.alternativeHypotheses[0]?.hypothesis);
    expect(finIncident.clientName).toEqual('FinanceCore Holdings');
    expect(retailIncident.clientName).toEqual('RetailMax Group');
  });

  it('sets act pipeline stage when execution has started', () => {
    const record: ActiveIncidentRecord = {
      thread_id: 'thread-exec-1',
      incident_id: 'INC-EXEC-001',
      client_id: 'FINCORE_UK_001',
      priority: 'P1',
      routing_decision: 'AUTO_EXECUTE',
      execution_status: 'executing',
      composite_confidence_score: 0.9,
    };

    const incident = adaptActiveIncident(
      record,
      {
        'thread-exec-1': {
          thread_id: 'thread-exec-1',
          execution_status: 'executing',
          root_cause: 'Execution in progress.',
        },
      },
      {} as Record<string, any>,
    );

    expect(incident.pipelineStage).toBe('act');
    expect(incident.status).toBe('Executing');
  });

  it('maps backend stage timeline into incident view model', () => {
    const record: ActiveIncidentRecord = {
      thread_id: 'thread-timeline-1',
      incident_id: 'INC-TIME-001',
      client_id: 'FINCORE_UK_001',
      priority: 'P1',
      routing_decision: 'L1_HUMAN_REVIEW',
      composite_confidence_score: 0.88,
      stage_timeline: [
        {
          stage: 'detect',
          label: 'Detect',
          status: 'completed',
          timestamp: '2026-03-29T10:00:00Z',
          reason: 'Priority P1 classified from incoming evidence.',
          changed_fields: ['incident_priority', 'situation_summary'],
        },
        {
          stage: 'reason',
          label: 'Reason',
          status: 'active',
          timestamp: '2026-03-29T10:00:04Z',
          reason: 'Root cause synthesis in progress.',
          changed_fields: ['root_cause'],
        },
      ],
    };

    const incident = adaptActiveIncident(record, {}, {} as Record<string, any>);

    expect(incident.stageTimeline?.length).toBe(2);
    expect(incident.stageTimeline?.[0]?.stage).toBe('detect');
    expect(incident.stageTimeline?.[0]?.changedFields).toContain('incident_priority');
    expect(incident.stageTimeline?.[1]?.status).toBe('active');
  });
});
