// RetailMax EU — ATLAS Knowledge Graph Seed
// client_id: RETAILMAX_EU_002
// Run in Neo4j Browser. Idempotent via MERGE.

// ── Constraints ───────────────────────────────────────────────────────────────
CREATE CONSTRAINT IF NOT EXISTS FOR (s:Service) REQUIRE (s.name, s.client_id) IS NODE KEY;
CREATE CONSTRAINT IF NOT EXISTS FOR (d:Deployment) REQUIRE (d.change_id, d.client_id) IS NODE KEY;
CREATE CONSTRAINT IF NOT EXISTS FOR (i:Incident) REQUIRE (i.incident_id, i.client_id) IS NODE KEY;

// ── Services ──────────────────────────────────────────────────────────────────
MERGE (prod:Service {name: 'ProductAPI', client_id: 'RETAILMAX_EU_002'})
SET prod += {tech_type: 'nodejs', version: '18.17.0', criticality: 'P2', namespace: 'retailmax-prod'};

MERGE (cart:Service {name: 'CartService', client_id: 'RETAILMAX_EU_002'})
SET cart += {tech_type: 'nodejs', version: '18.17.0', criticality: 'P2', namespace: 'retailmax-prod'};

MERGE (redis:Service {name: 'RedisCache', client_id: 'RETAILMAX_EU_002'})
SET redis += {tech_type: 'redis', version: '7.0.12', criticality: 'P2', namespace: 'retailmax-prod', maxmemory_policy: 'noeviction'};

MERGE (mongo:Service {name: 'MongoDB', client_id: 'RETAILMAX_EU_002'})
SET mongo += {tech_type: 'mongodb', version: '6.0.8', criticality: 'P2', namespace: 'retailmax-prod'};

MERGE (cdn:Service {name: 'CDN', client_id: 'RETAILMAX_EU_002'})
SET cdn += {tech_type: 'cloudflare', version: 'latest', criticality: 'P3', namespace: 'global'};

// ── Infrastructure ────────────────────────────────────────────────────────────
MERGE (k8s:Infrastructure {name: 'retailmax-k8s-prod', client_id: 'RETAILMAX_EU_002'})
SET k8s += {type: 'kubernetes', provider: 'gcp', region: 'europe-west4'};

MERGE (redis_infra:Infrastructure {name: 'retailmax-redis-cluster', client_id: 'RETAILMAX_EU_002'})
SET redis_infra += {type: 'redis_cluster', provider: 'gcp', region: 'europe-west4'};

// ── Teams ─────────────────────────────────────────────────────────────────────
MERGE (backend_team:Team {name: 'retailmax-backend-l2', client_id: 'RETAILMAX_EU_002'})
SET backend_team += {tier: 'L2', contact: 'backend-l2@atos.com'};

MERGE (infra_team:Team {name: 'retailmax-infra-l3', client_id: 'RETAILMAX_EU_002'})
SET infra_team += {tier: 'L3', contact: 'infra-l3@atos.com'};

// ── SLA Nodes ─────────────────────────────────────────────────────────────────
MERGE (sla_cart:SLA {service_name: 'CartService', client_id: 'RETAILMAX_EU_002'})
SET sla_cart += {breach_threshold_minutes: 60, tier: 'P2'};

MERGE (sla_redis:SLA {service_name: 'RedisCache', client_id: 'RETAILMAX_EU_002'})
SET sla_redis += {breach_threshold_minutes: 60, tier: 'P2'};

// ── Compliance Rules ──────────────────────────────────────────────────────────
MERGE (gdpr:ComplianceRule {framework: 'GDPR', client_id: 'RETAILMAX_EU_002'})
SET gdpr += {rule_description: 'Personal data processing requires audit trail and data minimisation', enforcement: 'mandatory'};

// ── Deployments (DEP-20250316-003 is the critical one — Redis policy change) ─
MERGE (dep1:Deployment {change_id: 'DEP-20250316-003', client_id: 'RETAILMAX_EU_002'})
SET dep1 += {
  change_description: 'Changed Redis maxmemory-policy from allkeys-lru to noeviction to prevent cache eviction during flash sale. Intended to preserve all cached product data.',
  deployed_by: 'tom.bradley@atos.com',
  timestamp: datetime('2026-03-19T16:45:00Z'),
  cab_approved_by: 'anna.kowalski@atos.com',
  cab_risk_rating: 'LOW',
  change_type: 'config_change'
};

MERGE (dep2:Deployment {change_id: 'DEP-20250314-001', client_id: 'RETAILMAX_EU_002'})
SET dep2 += {
  change_description: 'Node.js 18.16.0 to 18.17.0 security patch for CartService and ProductAPI',
  deployed_by: 'anna.kowalski@atos.com',
  timestamp: datetime('2026-03-14T10:00:00Z'),
  cab_approved_by: 'tom.bradley@atos.com',
  cab_risk_rating: 'LOW',
  change_type: 'version_upgrade'
};

MERGE (dep3:Deployment {change_id: 'DEP-20250310-002', client_id: 'RETAILMAX_EU_002'})
SET dep3 += {
  change_description: 'Increased CartService replicas from 2 to 4 for spring sale period',
  deployed_by: 'tom.bradley@atos.com',
  timestamp: datetime('2026-03-10T09:00:00Z'),
  cab_approved_by: 'anna.kowalski@atos.com',
  cab_risk_rating: 'LOW',
  change_type: 'scaling'
};

// ── Historical Incidents (6 total — deliberately NO REDIS_OOM match) ──────────
MERGE (rinc1:Incident {incident_id: 'RINC-2025-0234', client_id: 'RETAILMAX_EU_002'})
SET rinc1 += {
  title: 'CartService unhandled promise rejections — MongoDB connection timeout',
  anomaly_type: 'NODE_UNHANDLED_REJECTION',
  occurred_at: datetime('2026-01-15T14:30:00Z'),
  root_cause: 'MongoDB Atlas connection pool timeout during maintenance window caused unhandled promise rejections in CartService.',
  resolution: 'Increased MongoDB connection timeout. Added retry logic with exponential backoff.',
  mttr_minutes: 22,
  resolved_by: 'anna.kowalski@atos.com',
  playbook_used: 'manual-l2',
  resolution_outcome: 'success'
};

MERGE (rinc2:Incident {incident_id: 'RINC-2025-0189', client_id: 'RETAILMAX_EU_002'})
SET rinc2 += {
  title: 'ProductAPI 5xx spike — downstream MongoDB slow queries',
  anomaly_type: 'NODE_DOWNSTREAM_REFUSED',
  occurred_at: datetime('2025-12-20T11:00:00Z'),
  root_cause: 'Missing index on product_category field caused full collection scans under high read load.',
  resolution: 'Added compound index on product_category and price fields. Query time dropped from 4s to 12ms.',
  mttr_minutes: 35,
  resolved_by: 'tom.bradley@atos.com',
  playbook_used: 'manual-l2',
  resolution_outcome: 'success'
};

MERGE (rinc3:Incident {incident_id: 'RINC-2025-0098', client_id: 'RETAILMAX_EU_002'})
SET rinc3 += {
  title: 'CDN cache purge failure — stale product images served',
  anomaly_type: 'NODE_DOWNSTREAM_REFUSED',
  occurred_at: datetime('2025-11-05T09:15:00Z'),
  root_cause: 'Cloudflare API rate limit hit during bulk cache purge after product image update.',
  resolution: 'Implemented batched cache purge with rate limiting. Stale images cleared within 30 minutes.',
  mttr_minutes: 30,
  resolved_by: 'anna.kowalski@atos.com',
  playbook_used: 'manual-l1',
  resolution_outcome: 'success'
};

MERGE (rinc4:Incident {incident_id: 'RINC-2024-0876', client_id: 'RETAILMAX_EU_002'})
SET rinc4 += {
  title: 'CartService memory leak — session objects not garbage collected',
  anomaly_type: 'NODE_UNHANDLED_REJECTION',
  occurred_at: datetime('2025-09-18T16:45:00Z'),
  root_cause: 'Event listener not removed on session close causing memory leak. Node.js heap grew to 85% over 48 hours.',
  resolution: 'Hotfix to remove event listeners on session close. Rolling restart.',
  mttr_minutes: 28,
  resolved_by: 'tom.bradley@atos.com',
  playbook_used: 'manual-l2',
  resolution_outcome: 'success'
};

MERGE (rinc5:Incident {incident_id: 'RINC-2024-0654', client_id: 'RETAILMAX_EU_002'})
SET rinc5 += {
  title: 'MongoDB Atlas connection pool exhaustion during flash sale',
  anomaly_type: 'NODE_DOWNSTREAM_REFUSED',
  occurred_at: datetime('2025-07-04T12:00:00Z'),
  root_cause: 'Flash sale traffic 5x normal volume exhausted MongoDB Atlas connection pool. CartService requests queued and timed out.',
  resolution: 'Increased Atlas connection pool size. Added circuit breaker to CartService.',
  mttr_minutes: 41,
  resolved_by: 'anna.kowalski@atos.com',
  playbook_used: 'manual-l2',
  resolution_outcome: 'success'
};

MERGE (rinc6:Incident {incident_id: 'RINC-2024-0412', client_id: 'RETAILMAX_EU_002'})
SET rinc6 += {
  title: 'ProductAPI ECONNREFUSED — Redis connection refused during restart',
  anomaly_type: 'NODE_DOWNSTREAM_REFUSED',
  occurred_at: datetime('2025-05-22T08:30:00Z'),
  root_cause: 'Redis cluster rolling restart caused brief connection refused errors in ProductAPI. No retry logic in place.',
  resolution: 'Added Redis connection retry with backoff to ProductAPI. Implemented health check before cache reads.',
  mttr_minutes: 15,
  resolved_by: 'tom.bradley@atos.com',
  playbook_used: 'manual-l1',
  resolution_outcome: 'success'
};

// ── Service Dependencies ──────────────────────────────────────────────────────
MATCH (cart:Service {name: 'CartService', client_id: 'RETAILMAX_EU_002'})
MATCH (redis:Service {name: 'RedisCache', client_id: 'RETAILMAX_EU_002'})
MERGE (cart)-[:DEPENDS_ON {weight: 'high'}]->(redis);

MATCH (cart:Service {name: 'CartService', client_id: 'RETAILMAX_EU_002'})
MATCH (mongo:Service {name: 'MongoDB', client_id: 'RETAILMAX_EU_002'})
MERGE (cart)-[:DEPENDS_ON {weight: 'critical'}]->(mongo);

MATCH (prod:Service {name: 'ProductAPI', client_id: 'RETAILMAX_EU_002'})
MATCH (mongo:Service {name: 'MongoDB', client_id: 'RETAILMAX_EU_002'})
MERGE (prod)-[:DEPENDS_ON {weight: 'critical'}]->(mongo);

MATCH (prod:Service {name: 'ProductAPI', client_id: 'RETAILMAX_EU_002'})
MATCH (redis:Service {name: 'RedisCache', client_id: 'RETAILMAX_EU_002'})
MERGE (prod)-[:DEPENDS_ON {weight: 'medium'}]->(redis);

MATCH (prod:Service {name: 'ProductAPI', client_id: 'RETAILMAX_EU_002'})
MATCH (cdn:Service {name: 'CDN', client_id: 'RETAILMAX_EU_002'})
MERGE (prod)-[:DEPENDS_ON {weight: 'low'}]->(cdn);

// ── Deployment → Service ──────────────────────────────────────────────────────
MATCH (dep1:Deployment {change_id: 'DEP-20250316-003', client_id: 'RETAILMAX_EU_002'})
MATCH (redis:Service {name: 'RedisCache', client_id: 'RETAILMAX_EU_002'})
MERGE (dep1)-[:MODIFIED_CONFIG_OF]->(redis);

MATCH (dep2:Deployment {change_id: 'DEP-20250314-001', client_id: 'RETAILMAX_EU_002'})
MATCH (cart:Service {name: 'CartService', client_id: 'RETAILMAX_EU_002'})
MERGE (dep2)-[:DEPLOYED_TO]->(cart);

MATCH (dep3:Deployment {change_id: 'DEP-20250310-002', client_id: 'RETAILMAX_EU_002'})
MATCH (cart:Service {name: 'CartService', client_id: 'RETAILMAX_EU_002'})
MERGE (dep3)-[:DEPLOYED_TO]->(cart);

// ── Incident → Service ────────────────────────────────────────────────────────
MATCH (rinc1:Incident {incident_id: 'RINC-2025-0234', client_id: 'RETAILMAX_EU_002'})
MATCH (cart:Service {name: 'CartService', client_id: 'RETAILMAX_EU_002'})
MERGE (rinc1)-[:AFFECTED]->(cart);

MATCH (rinc2:Incident {incident_id: 'RINC-2025-0189', client_id: 'RETAILMAX_EU_002'})
MATCH (prod:Service {name: 'ProductAPI', client_id: 'RETAILMAX_EU_002'})
MERGE (rinc2)-[:AFFECTED]->(prod);

MATCH (rinc5:Incident {incident_id: 'RINC-2024-0654', client_id: 'RETAILMAX_EU_002'})
MATCH (cart:Service {name: 'CartService', client_id: 'RETAILMAX_EU_002'})
MERGE (rinc5)-[:AFFECTED]->(cart);

// ── SLA Relationships ─────────────────────────────────────────────────────────
MATCH (cart:Service {name: 'CartService', client_id: 'RETAILMAX_EU_002'})
MATCH (sla:SLA {service_name: 'CartService', client_id: 'RETAILMAX_EU_002'})
MERGE (cart)-[:COVERED_BY]->(sla);

MATCH (redis:Service {name: 'RedisCache', client_id: 'RETAILMAX_EU_002'})
MATCH (sla:SLA {service_name: 'RedisCache', client_id: 'RETAILMAX_EU_002'})
MERGE (redis)-[:COVERED_BY]->(sla);

// ── Team Ownership ────────────────────────────────────────────────────────────
MATCH (cart:Service {name: 'CartService', client_id: 'RETAILMAX_EU_002'})
MATCH (team:Team {name: 'retailmax-backend-l2', client_id: 'RETAILMAX_EU_002'})
MERGE (cart)-[:OWNED_BY]->(team);

MATCH (redis:Service {name: 'RedisCache', client_id: 'RETAILMAX_EU_002'})
MATCH (team:Team {name: 'retailmax-infra-l3', client_id: 'RETAILMAX_EU_002'})
MERGE (redis)-[:OWNED_BY]->(team);

// ── Compliance Governance ─────────────────────────────────────────────────────
MATCH (mongo:Service {name: 'MongoDB', client_id: 'RETAILMAX_EU_002'})
MATCH (gdpr:ComplianceRule {framework: 'GDPR', client_id: 'RETAILMAX_EU_002'})
MERGE (mongo)-[:GOVERNED_BY]->(gdpr);
