---
inclusion: always
---

# ATLAS Data Contracts

All structured data schemas used across the system. Every module must produce and consume these exact shapes.

## EvidencePackage

Produced by every specialist agent. Consumed by correlation_engine.py.

```python
@dataclass
class EvidencePackage:
    evidence_id: str                          # uuid4
    agent_id: str                             # e.g. "java-agent", "postgres-agent"
    client_id: str                            # mandatory, immutable
    service_name: str
    anomaly_type: str                         # from ATLAS error taxonomy
    detection_confidence: float               # 0.0–1.0, from conformal prediction
    shap_feature_values: dict[str, float]     # feature_name → contribution_percentage, sums to 100
    conformal_interval: dict                  # {lower: float, upper: float, confidence_level: float}
    baseline_mean: float
    baseline_stddev: float
    current_value: float
    deviation_sigma: float
    supporting_log_samples: list[str]         # exactly 5 lines (or min 1 in Critical mode)
    preliminary_hypothesis: str
    severity_classification: str             # "P1" | "P2" | "P3"
    detection_timestamp: datetime
```

## LangGraph State (complete TypedDict)

```python
class AtlasState(TypedDict):
    client_id: str
    incident_id: str
    evidence_packages: list[EvidencePackage]
    correlation_type: str                    # "CASCADE_INCIDENT" | "ISOLATED_ANOMALY"
    blast_radius: list[dict]
    recent_deployments: list[dict]
    historical_graph_matches: list[dict]
    semantic_matches: list[dict]
    root_cause: str
    recommended_action_id: str
    alternative_hypotheses: list[dict]
    composite_confidence_score: float
    active_veto_conditions: list[str]
    routing_decision: str                    # "AUTO_EXECUTE" | "L1_HUMAN_REVIEW" | "L2_L3_ESCALATION"
    servicenow_ticket_id: str
    execution_status: str
    audit_trail: list[dict]                  # append-only
    mttr_start_time: datetime
    mttr_seconds: int
    sla_breach_time: datetime
    early_warning_signals: list[dict]
    human_action: str                        # "approved" | "modified" | "rejected" | "escalated"
    human_modifier: str
    human_rejection_reason: str
    resolution_outcome: str                  # "success" | "failure" | "partial"
    recurrence_check_due_at: datetime
```

Immutable after initial set: `client_id`, `incident_id`, `evidence_packages`, `mttr_start_time`.
`routing_decision` once set cannot be changed — new incident required for re-routing.
`audit_trail` is append-only.

## LLM Reasoning Output (internal endpoint schema)

The internal `POST /internal/llm/reason` endpoint accepts a structured context payload and returns:

```json
{
  "root_cause": "string",
  "confidence_factors": {},
  "recommended_action_id": "string",
  "alternative_hypotheses": [
    {
      "hypothesis": "string",
      "evidence_for": "string",
      "evidence_against": "string",
      "confidence": 0.0
    }
  ],
  "explanation_for_engineer": "string (min 50 chars, written at L2 level)",
  "technical_evidence_summary": "string"
}
```

`recommended_action_id` must be validated against playbook library before acceptance.
`explanation_for_engineer` rejected if under 50 characters.

## Decision History Record

```python
@dataclass
class DecisionRecord:
    record_id: str
    client_id: str
    incident_id: str
    anomaly_type: str
    service_class: str
    recommended_action_id: str
    confidence_score_at_decision: float
    routing_tier: str                        # "L1" | "L2" | "L3" | "auto"
    human_action: str                        # "approved" | "modified" | "rejected" | "escalated"
    modification_diff: dict | None
    rejection_reason: str | None
    resolution_outcome: str                  # "success" | "failure" | "partial"
    actual_mttr: int                         # seconds
    recurrence_within_48h: bool
    timestamp: datetime
```

Records are immutable after writing. No update or delete methods.

## Audit Log Record

```python
@dataclass
class AuditRecord:
    record_id: str
    incident_id: str
    client_id: str
    timestamp: datetime
    action_type: str    # "detection"|"classification"|"approval"|"execution"|"rollback"|"resolution"
    actor: str          # "ATLAS_AUTO" or engineer name
    action_description: str
    confidence_score_at_time: float
    reasoning_summary: str
    outcome: str
    servicenow_ticket_id: str
    rollback_available: bool
    compliance_frameworks_applied: list[str]
```

## Normalised Event (OTel schema)

```python
@dataclass
class NormalisedEvent:
    atlas_event_id: str
    client_id: str                           # immutable from this point forward
    timestamp: datetime                      # ISO-8601 UTC
    source_system: str
    source_type: str
    severity: str                            # "ERROR" | "WARN" | "INFO" | "DEBUG"
    error_code: str
    message: str
    raw_payload: str                         # original log line, never modified
    deployment_id: str | None
    # CMDB enrichment fields (attached by cmdb_enricher.py):
    ci_class: str | None
    ci_version: str | None
    business_service_name: str | None
    criticality_tier: str | None
    open_change_records: list[str]
    sla_breach_threshold_minutes: int | None
    owner_team: str | None
    cmdb_enrichment_status: str             # "enriched" | "not_found" | "cache_hit"
    enriched_from_cache: bool
```

## ATLAS Error Taxonomy

```
CONNECTION_POOL_EXHAUSTED   — HikariCP exhaustion, PostgreSQL 53300
DB_DEADLOCK                 — PostgreSQL 40P01
DB_PANIC                    — PostgreSQL PANIC level (always P1)
JVM_MEMORY_CRITICAL         — OutOfMemoryError
JVM_STACK_OVERFLOW          — StackOverflowError
REDIS_OOM                   — Redis maxmemory exceeded
REDIS_COMMAND_REJECTED      — Redis rejected commands
NODE_UNHANDLED_REJECTION    — UnhandledPromiseRejectionWarning spike
NODE_DOWNSTREAM_REFUSED     — ECONNREFUSED to downstream service
JAVA_UNKNOWN                — unmapped Java exception (class name preserved)
DB_UNKNOWN                  — unmapped PostgreSQL SQLSTATE (code preserved)
```

## Action Safety Classes

```
Class 1 — service restart, cache clear, config parameter tuning
          auto_execute_eligible: true (if threshold and vetoes met)
          calculate_action_safety → 1.0

Class 2 — service redeployment, infrastructure scaling
          auto_execute_eligible: false (always human)
          calculate_action_safety → 0.6

Class 3 — database operations, network changes, production data
          auto_execute_eligible: false (permanent ceiling, non-configurable)
          calculate_action_safety → 0.0
          triggers class_three veto immediately
```

## Trust Stages

```
Stage 0 — Observation:     default for new clients, all human
Stage 1 — L1 Assistance:   30 incidents + >80% confirmed correct reasoning
Stage 2 — L1 Automation:   30 more incidents + >85% auto-resolution success
Stage 3 — L2 Assistance:   demonstrated Stage 2 accuracy
Stage 4 — L2 Automation:   SDM explicit enablement required (criteria alone insufficient)
Class 3: never auto-executes at any stage. Permanent. Non-configurable.
```

## Neo4j Node Types

```
Service        {name, client_id, tech_type, version, criticality, namespace}
Infrastructure {name, client_id, type, provider, region}
Deployment     {change_id, client_id, deployed_by, change_description,
                timestamp, cab_approved_by, risk_rating}
Incident       {incident_id, client_id, title, occurred_at, root_cause,
                resolution, mttr_minutes, resolved_by, playbook_used}
Problem        {problem_id, client_id, title, root_cause, permanent_fix}
SLA            {service_name, client_id, breach_threshold_minutes, tier}
Team           {name, client_id, tier, contact}
ComplianceRule {framework, client_id, rule_description, enforcement}
```

## Neo4j Relationship Types

```
DEPENDS_ON          (Service → Service)
HOSTED_ON           (Service → Infrastructure)
MODIFIED_CONFIG_OF  (Deployment → Service)
DEPLOYED_TO         (Deployment → Infrastructure)
AFFECTED            (Incident → Service)
CAUSED_BY           (Incident → Deployment)
RESOLVED_BY         (Incident → Resolution)
COVERED_BY          (Service → SLA)
OWNED_BY            (Service → Team)
GOVERNED_BY         (Service → ComplianceRule)
```

## Demo Client IDs

```
FinanceCore:  client_id = "FINCORE_UK_001"
RetailMax:    client_id = "RETAILMAX_EU_002"
```

## Critical Demo Data Points

```
FinanceCore:
  Deployment:  CHG0089234 — HikariCP maxPoolSize reduced 100→40, 3 days ago, MODIFIED_CONFIG_OF PaymentAPI
  Incident:    INC-2024-0847 — CONNECTION_POOL_EXHAUSTED, 4 months ago, resolved by restoring pool to 150
  Expected:    confidence ~0.84, PCI-DSS veto fires, routes to L2_L3_ESCALATION
  Playbook:    connection-pool-recovery-v2

RetailMax:
  Deployment:  DEP-20250316-003 — Redis maxmemory-policy noeviction, 2 days ago
  Expected:    no strong historical match (max similarity 0.67), cold-start veto fires
  Playbook:    redis-memory-policy-rollback-v1
```
