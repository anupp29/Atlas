// FinanceCore Ltd — ATLAS Knowledge Graph Seed
// client_id: FINCORE_UK_001
// Run in Neo4j Browser. Idempotent via MERGE.

// ── Constraints ──────────────────────────────────────────────────────────────
CREATE CONSTRAINT IF NOT EXISTS FOR (s:Service) REQUIRE (s.name, s.client_id) IS NODE KEY;
CREATE CONSTRAINT IF NOT EXISTS FOR (d:Deployment) REQUIRE (d.change_id, d.client_id) IS NODE KEY;
CREATE CONSTRAINT IF NOT EXISTS FOR (i:Incident) REQUIRE (i.incident_id, i.client_id) IS NODE KEY;

// ── Services ─────────────────────────────────────────────────────────────────
MERGE (payapi:Service {name: 'PaymentAPI', client_id: 'FINCORE_UK_001'})
SET payapi += {
  tech_type: 'java-spring-boot',
  version: '3.1.2',
  criticality: 'P1',
  namespace: 'financecore-prod',
  health_endpoint: 'http://payment-api:8080/actuator/health',
  max_pool_size: 40
};

MERGE (txdb:Service {name: 'TransactionDB', client_id: 'FINCORE_UK_001'})
SET txdb += {
  tech_type: 'postgresql',
  version: '14.8',
  criticality: 'P1',
  namespace: 'financecore-prod',
  max_connections: 100
};

MERGE (auth:Service {name: 'AuthService', client_id: 'FINCORE_UK_001'})
SET auth += {
  tech_type: 'java-spring-boot',
  version: '2.7.14',
  criticality: 'P2',
  namespace: 'financecore-prod'
};

MERGE (notif:Service {name: 'NotificationService', client_id: 'FINCORE_UK_001'})
SET notif += {
  tech_type: 'java-spring-boot',
  version: '2.7.14',
  criticality: 'P3',
  namespace: 'financecore-prod'
};

MERGE (gw:Service {name: 'APIGateway', client_id: 'FINCORE_UK_001'})
SET gw += {
  tech_type: 'kong',
  version: '3.4.0',
  criticality: 'P2',
  namespace: 'financecore-prod'
};

// ── Infrastructure ────────────────────────────────────────────────────────────
MERGE (eks:Infrastructure {name: 'financecore-eks-prod', client_id: 'FINCORE_UK_001'})
SET eks += {type: 'kubernetes', provider: 'aws', region: 'eu-west-2'};

MERGE (rds_primary:Infrastructure {name: 'financecore-rds-primary', client_id: 'FINCORE_UK_001'})
SET rds_primary += {type: 'rds', provider: 'aws', region: 'eu-west-2', instance_class: 'db.r6g.xlarge'};

MERGE (rds_replica:Infrastructure {name: 'financecore-rds-replica', client_id: 'FINCORE_UK_001'})
SET rds_replica += {type: 'rds_replica', provider: 'aws', region: 'eu-west-2'};

MERGE (alb:Infrastructure {name: 'financecore-alb', client_id: 'FINCORE_UK_001'})
SET alb += {type: 'load_balancer', provider: 'aws', region: 'eu-west-2'};

// ── Teams ─────────────────────────────────────────────────────────────────────
MERGE (payments_team:Team {name: 'payments-l2-team', client_id: 'FINCORE_UK_001'})
SET payments_team += {tier: 'L2', contact: 'payments-l2@atos.com'};

MERGE (dba_team:Team {name: 'dba-l2-team', client_id: 'FINCORE_UK_001'})
SET dba_team += {tier: 'L2', contact: 'dba-l2@atos.com'};

MERGE (platform_team:Team {name: 'platform-l3-team', client_id: 'FINCORE_UK_001'})
SET platform_team += {tier: 'L3', contact: 'platform-l3@atos.com'};

// ── SLA Nodes ─────────────────────────────────────────────────────────────────
MERGE (sla_p1:SLA {service_name: 'PaymentAPI', client_id: 'FINCORE_UK_001'})
SET sla_p1 += {breach_threshold_minutes: 15, tier: 'P1'};

MERGE (sla_txdb:SLA {service_name: 'TransactionDB', client_id: 'FINCORE_UK_001'})
SET sla_txdb += {breach_threshold_minutes: 15, tier: 'P1'};

MERGE (sla_auth:SLA {service_name: 'AuthService', client_id: 'FINCORE_UK_001'})
SET sla_auth += {breach_threshold_minutes: 30, tier: 'P2'};

// ── Compliance Rules ──────────────────────────────────────────────────────────
MERGE (pci:ComplianceRule {framework: 'PCI-DSS', client_id: 'FINCORE_UK_001'})
SET pci += {rule_description: 'Production database config changes require dual sign-off during business hours', enforcement: 'mandatory'};

MERGE (sox:ComplianceRule {framework: 'SOX', client_id: 'FINCORE_UK_001'})
SET sox += {rule_description: 'All financial system changes require audit trail and dual approval', enforcement: 'mandatory'};

// ── Deployments (8 total, CHG0089234 is the critical one) ────────────────────
MERGE (chg1:Deployment {change_id: 'CHG0089234', client_id: 'FINCORE_UK_001'})
SET chg1 += {
  change_description: 'Cost optimisation: reduced HikariCP maxPoolSize from 100 to 40 on PaymentAPI to reduce RDS connection overhead',
  deployed_by: 'raj.kumar@atos.com',
  timestamp: datetime('2026-03-18T14:23:00Z'),
  cab_approved_by: 'sarah.chen@atos.com',
  cab_risk_rating: 'LOW',
  change_type: 'config_change'
};

MERGE (chg2:Deployment {change_id: 'CHG0088901', client_id: 'FINCORE_UK_001'})
SET chg2 += {
  change_description: 'Upgraded AuthService from 2.7.12 to 2.7.14 — security patch',
  deployed_by: 'priya.sharma@atos.com',
  timestamp: datetime('2026-03-15T10:00:00Z'),
  cab_approved_by: 'sarah.chen@atos.com',
  cab_risk_rating: 'LOW',
  change_type: 'version_upgrade'
};

MERGE (chg3:Deployment {change_id: 'CHG0088456', client_id: 'FINCORE_UK_001'})
SET chg3 += {
  change_description: 'Scaled PaymentAPI replicas from 3 to 5 for Q1 peak traffic',
  deployed_by: 'james.okafor@atos.com',
  timestamp: datetime('2026-03-10T09:00:00Z'),
  cab_approved_by: 'sarah.chen@atos.com',
  cab_risk_rating: 'LOW',
  change_type: 'scaling'
};

MERGE (chg4:Deployment {change_id: 'CHG0087234', client_id: 'FINCORE_UK_001'})
SET chg4 += {
  change_description: 'Updated Kong API Gateway rate limiting rules',
  deployed_by: 'raj.kumar@atos.com',
  timestamp: datetime('2026-03-05T11:30:00Z'),
  cab_approved_by: 'sarah.chen@atos.com',
  cab_risk_rating: 'MEDIUM',
  change_type: 'config_change'
};

MERGE (chg5:Deployment {change_id: 'CHG0086789', client_id: 'FINCORE_UK_001'})
SET chg5 += {
  change_description: 'PostgreSQL 14.7 to 14.8 minor version upgrade',
  deployed_by: 'priya.sharma@atos.com',
  timestamp: datetime('2026-02-28T08:00:00Z'),
  cab_approved_by: 'sarah.chen@atos.com',
  cab_risk_rating: 'MEDIUM',
  change_type: 'version_upgrade'
};

MERGE (chg6:Deployment {change_id: 'CHG0085432', client_id: 'FINCORE_UK_001'})
SET chg6 += {
  change_description: 'Added Redis caching layer for session tokens in AuthService',
  deployed_by: 'james.okafor@atos.com',
  timestamp: datetime('2026-02-20T14:00:00Z'),
  cab_approved_by: 'sarah.chen@atos.com',
  cab_risk_rating: 'LOW',
  change_type: 'feature'
};

MERGE (chg7:Deployment {change_id: 'CHG0084123', client_id: 'FINCORE_UK_001'})
SET chg7 += {
  change_description: 'EKS node group upgrade to Kubernetes 1.28',
  deployed_by: 'priya.sharma@atos.com',
  timestamp: datetime('2026-02-10T07:00:00Z'),
  cab_approved_by: 'sarah.chen@atos.com',
  cab_risk_rating: 'HIGH',
  change_type: 'infrastructure'
};

MERGE (chg8:Deployment {change_id: 'CHG0083456', client_id: 'FINCORE_UK_001'})
SET chg8 += {
  change_description: 'Updated NotificationService email template engine',
  deployed_by: 'raj.kumar@atos.com',
  timestamp: datetime('2026-02-01T10:00:00Z'),
  cab_approved_by: 'sarah.chen@atos.com',
  cab_risk_rating: 'LOW',
  change_type: 'feature'
};

// ── Historical Incidents (10 total, INC-2024-0847 is the critical match) ─────
MERGE (inc1:Incident {incident_id: 'INC-2024-0847', client_id: 'FINCORE_UK_001'})
SET inc1 += {
  title: 'TransactionDB connection pool exhaustion — HikariCP maxPoolSize misconfiguration',
  anomaly_type: 'CONNECTION_POOL_EXHAUSTED',
  occurred_at: datetime('2025-11-14T09:15:00Z'),
  root_cause: 'Deployment CHG0071892 reduced HikariCP maxPoolSize from 150 to 40 on PaymentAPI. Under peak load, the pool was exhausted causing HTTP 503 errors and PostgreSQL connection count reaching 94% of max_connections.',
  resolution: 'Restored HikariCP maxPoolSize to 150 via actuator PATCH endpoint. Restarted connection manager pod. Connection count normalised within 4 minutes.',
  mttr_minutes: 23,
  resolved_by: 'priya.sharma@atos.com',
  playbook_used: 'connection-pool-recovery-v2',
  resolution_outcome: 'success'
};

MERGE (inc2:Incident {incident_id: 'INC-2024-0612', client_id: 'FINCORE_UK_001'})
SET inc2 += {
  title: 'AuthService memory leak — heap exhaustion after 72h uptime',
  anomaly_type: 'JVM_MEMORY_CRITICAL',
  occurred_at: datetime('2025-09-22T03:40:00Z'),
  root_cause: 'Memory leak in session cache not releasing expired tokens. JVM heap reached 95% after 72 hours of uptime.',
  resolution: 'Rolling restart of AuthService pods. Permanent fix: added TTL eviction to session cache.',
  mttr_minutes: 18,
  resolved_by: 'james.okafor@atos.com',
  playbook_used: 'jvm-restart-v1',
  resolution_outcome: 'success'
};

MERGE (inc3:Incident {incident_id: 'INC-2024-0445', client_id: 'FINCORE_UK_001'})
SET inc3 += {
  title: 'TransactionDB deadlock storm during batch settlement',
  anomaly_type: 'DB_DEADLOCK',
  occurred_at: datetime('2025-07-08T22:15:00Z'),
  root_cause: 'Concurrent batch settlement jobs acquiring row locks in inconsistent order causing deadlock cascade.',
  resolution: 'Killed long-running transactions. Serialised batch jobs. Added index on settlement_date column.',
  mttr_minutes: 45,
  resolved_by: 'priya.sharma@atos.com',
  playbook_used: 'manual-l3',
  resolution_outcome: 'success'
};

MERGE (inc4:Incident {incident_id: 'INC-2024-0389', client_id: 'FINCORE_UK_001'})
SET inc4 += {
  title: 'PaymentAPI 5xx spike — downstream TransactionDB latency',
  anomaly_type: 'CONNECTION_POOL_EXHAUSTED',
  occurred_at: datetime('2025-06-15T10:30:00Z'),
  root_cause: 'Slow query on TransactionDB caused connection hold time to increase, exhausting HikariCP pool.',
  resolution: 'Identified and killed slow query. Added query timeout of 30s to HikariCP config.',
  mttr_minutes: 31,
  resolved_by: 'james.okafor@atos.com',
  playbook_used: 'connection-pool-recovery-v2',
  resolution_outcome: 'success'
};

MERGE (inc5:Incident {incident_id: 'INC-2024-0201', client_id: 'FINCORE_UK_001'})
SET inc5 += {
  title: 'APIGateway rate limit misconfiguration — legitimate traffic blocked',
  anomaly_type: 'NODE_DOWNSTREAM_REFUSED',
  occurred_at: datetime('2025-04-03T14:00:00Z'),
  root_cause: 'Kong rate limit plugin configured with per-second limit instead of per-minute after CHG0087234.',
  resolution: 'Updated Kong rate limit configuration. Cleared rate limit counters.',
  mttr_minutes: 12,
  resolved_by: 'raj.kumar@atos.com',
  playbook_used: 'manual-l2',
  resolution_outcome: 'success'
};

MERGE (inc6:Incident {incident_id: 'INC-2023-1847', client_id: 'FINCORE_UK_001'})
SET inc6 += {
  title: 'NotificationService OOM — email queue backlog',
  anomaly_type: 'JVM_MEMORY_CRITICAL',
  occurred_at: datetime('2025-02-18T08:45:00Z'),
  root_cause: 'Email queue backlog caused in-memory buffer to grow unbounded. JVM heap exhausted.',
  resolution: 'Restarted NotificationService. Implemented bounded queue with dead-letter handling.',
  mttr_minutes: 27,
  resolved_by: 'priya.sharma@atos.com',
  playbook_used: 'jvm-restart-v1',
  resolution_outcome: 'success'
};

MERGE (inc7:Incident {incident_id: 'INC-2023-1654', client_id: 'FINCORE_UK_001'})
SET inc7 += {
  title: 'TransactionDB replica lag — read queries returning stale data',
  anomaly_type: 'DB_DEADLOCK',
  occurred_at: datetime('2024-12-10T16:20:00Z'),
  root_cause: 'RDS replica fell behind primary by 45 seconds during high write load. Read queries routed to replica returned stale balances.',
  resolution: 'Temporarily routed all reads to primary. Investigated and resolved replication lag.',
  mttr_minutes: 38,
  resolved_by: 'james.okafor@atos.com',
  playbook_used: 'manual-l3',
  resolution_outcome: 'success'
};

MERGE (inc8:Incident {incident_id: 'INC-2023-1423', client_id: 'FINCORE_UK_001'})
SET inc8 += {
  title: 'AuthService StackOverflow — recursive token validation',
  anomaly_type: 'JVM_STACK_OVERFLOW',
  occurred_at: datetime('2024-10-05T11:00:00Z'),
  root_cause: 'Circular dependency in token validation chain caused StackOverflowError under specific JWT formats.',
  resolution: 'Hotfix deployed to break circular validation. Rolling restart.',
  mttr_minutes: 52,
  resolved_by: 'priya.sharma@atos.com',
  playbook_used: 'manual-l3',
  resolution_outcome: 'success'
};

MERGE (inc9:Incident {incident_id: 'INC-2023-1102', client_id: 'FINCORE_UK_001'})
SET inc9 += {
  title: 'PaymentAPI connection pool exhaustion — Black Friday peak',
  anomaly_type: 'CONNECTION_POOL_EXHAUSTED',
  occurred_at: datetime('2024-11-29T09:00:00Z'),
  root_cause: 'Black Friday traffic 3x normal volume exhausted HikariCP pool. Pool size was not pre-scaled for peak.',
  resolution: 'Emergency pool size increase to 200. Post-incident: added auto-scaling trigger for pool size.',
  mttr_minutes: 19,
  resolved_by: 'raj.kumar@atos.com',
  playbook_used: 'connection-pool-recovery-v2',
  resolution_outcome: 'success'
};

MERGE (inc10:Incident {incident_id: 'INC-2023-0891', client_id: 'FINCORE_UK_001'})
SET inc10 += {
  title: 'EKS node failure — pod eviction cascade',
  anomaly_type: 'NODE_DOWNSTREAM_REFUSED',
  occurred_at: datetime('2024-09-12T02:30:00Z'),
  root_cause: 'EKS worker node ran out of disk space causing kubelet to evict pods. PaymentAPI pods evicted.',
  resolution: 'Drained and replaced affected node. Added disk pressure alerts.',
  mttr_minutes: 34,
  resolved_by: 'james.okafor@atos.com',
  playbook_used: 'manual-l3',
  resolution_outcome: 'success'
};

// ── Service Dependencies ──────────────────────────────────────────────────────
MATCH (gw:Service {name: 'APIGateway', client_id: 'FINCORE_UK_001'})
MATCH (payapi:Service {name: 'PaymentAPI', client_id: 'FINCORE_UK_001'})
MERGE (gw)-[:DEPENDS_ON {weight: 'critical'}]->(payapi);

MATCH (payapi:Service {name: 'PaymentAPI', client_id: 'FINCORE_UK_001'})
MATCH (txdb:Service {name: 'TransactionDB', client_id: 'FINCORE_UK_001'})
MERGE (payapi)-[:DEPENDS_ON {weight: 'critical'}]->(txdb);

MATCH (payapi:Service {name: 'PaymentAPI', client_id: 'FINCORE_UK_001'})
MATCH (auth:Service {name: 'AuthService', client_id: 'FINCORE_UK_001'})
MERGE (payapi)-[:DEPENDS_ON {weight: 'high'}]->(auth);

MATCH (payapi:Service {name: 'PaymentAPI', client_id: 'FINCORE_UK_001'})
MATCH (notif:Service {name: 'NotificationService', client_id: 'FINCORE_UK_001'})
MERGE (payapi)-[:DEPENDS_ON {weight: 'low'}]->(notif);

// ── Infrastructure Hosting ────────────────────────────────────────────────────
MATCH (payapi:Service {name: 'PaymentAPI', client_id: 'FINCORE_UK_001'})
MATCH (eks:Infrastructure {name: 'financecore-eks-prod', client_id: 'FINCORE_UK_001'})
MERGE (payapi)-[:HOSTED_ON]->(eks);

MATCH (txdb:Service {name: 'TransactionDB', client_id: 'FINCORE_UK_001'})
MATCH (rds:Infrastructure {name: 'financecore-rds-primary', client_id: 'FINCORE_UK_001'})
MERGE (txdb)-[:HOSTED_ON]->(rds);

MATCH (auth:Service {name: 'AuthService', client_id: 'FINCORE_UK_001'})
MATCH (eks:Infrastructure {name: 'financecore-eks-prod', client_id: 'FINCORE_UK_001'})
MERGE (auth)-[:HOSTED_ON]->(eks);

MATCH (notif:Service {name: 'NotificationService', client_id: 'FINCORE_UK_001'})
MATCH (eks:Infrastructure {name: 'financecore-eks-prod', client_id: 'FINCORE_UK_001'})
MERGE (notif)-[:HOSTED_ON]->(eks);

// ── Deployment → Service Relationships ───────────────────────────────────────
MATCH (chg1:Deployment {change_id: 'CHG0089234', client_id: 'FINCORE_UK_001'})
MATCH (payapi:Service {name: 'PaymentAPI', client_id: 'FINCORE_UK_001'})
MERGE (chg1)-[:MODIFIED_CONFIG_OF]->(payapi);

MATCH (chg2:Deployment {change_id: 'CHG0088901', client_id: 'FINCORE_UK_001'})
MATCH (auth:Service {name: 'AuthService', client_id: 'FINCORE_UK_001'})
MERGE (chg2)-[:DEPLOYED_TO]->(auth);

MATCH (chg3:Deployment {change_id: 'CHG0088456', client_id: 'FINCORE_UK_001'})
MATCH (payapi:Service {name: 'PaymentAPI', client_id: 'FINCORE_UK_001'})
MERGE (chg3)-[:DEPLOYED_TO]->(payapi);

MATCH (chg4:Deployment {change_id: 'CHG0087234', client_id: 'FINCORE_UK_001'})
MATCH (gw:Service {name: 'APIGateway', client_id: 'FINCORE_UK_001'})
MERGE (chg4)-[:MODIFIED_CONFIG_OF]->(gw);

MATCH (chg5:Deployment {change_id: 'CHG0086789', client_id: 'FINCORE_UK_001'})
MATCH (txdb:Service {name: 'TransactionDB', client_id: 'FINCORE_UK_001'})
MERGE (chg5)-[:DEPLOYED_TO]->(txdb);

// ── Incident → Service Relationships ─────────────────────────────────────────
MATCH (inc1:Incident {incident_id: 'INC-2024-0847', client_id: 'FINCORE_UK_001'})
MATCH (txdb:Service {name: 'TransactionDB', client_id: 'FINCORE_UK_001'})
MERGE (inc1)-[:AFFECTED]->(txdb);

MATCH (inc1:Incident {incident_id: 'INC-2024-0847', client_id: 'FINCORE_UK_001'})
MATCH (payapi:Service {name: 'PaymentAPI', client_id: 'FINCORE_UK_001'})
MERGE (inc1)-[:AFFECTED]->(payapi);

MATCH (inc4:Incident {incident_id: 'INC-2024-0389', client_id: 'FINCORE_UK_001'})
MATCH (payapi:Service {name: 'PaymentAPI', client_id: 'FINCORE_UK_001'})
MERGE (inc4)-[:AFFECTED]->(payapi);

MATCH (inc9:Incident {incident_id: 'INC-2023-1102', client_id: 'FINCORE_UK_001'})
MATCH (payapi:Service {name: 'PaymentAPI', client_id: 'FINCORE_UK_001'})
MERGE (inc9)-[:AFFECTED]->(payapi);

// ── SLA Relationships ─────────────────────────────────────────────────────────
MATCH (payapi:Service {name: 'PaymentAPI', client_id: 'FINCORE_UK_001'})
MATCH (sla:SLA {service_name: 'PaymentAPI', client_id: 'FINCORE_UK_001'})
MERGE (payapi)-[:COVERED_BY]->(sla);

MATCH (txdb:Service {name: 'TransactionDB', client_id: 'FINCORE_UK_001'})
MATCH (sla:SLA {service_name: 'TransactionDB', client_id: 'FINCORE_UK_001'})
MERGE (txdb)-[:COVERED_BY]->(sla);

// ── Team Ownership ────────────────────────────────────────────────────────────
MATCH (payapi:Service {name: 'PaymentAPI', client_id: 'FINCORE_UK_001'})
MATCH (team:Team {name: 'payments-l2-team', client_id: 'FINCORE_UK_001'})
MERGE (payapi)-[:OWNED_BY]->(team);

MATCH (txdb:Service {name: 'TransactionDB', client_id: 'FINCORE_UK_001'})
MATCH (team:Team {name: 'dba-l2-team', client_id: 'FINCORE_UK_001'})
MERGE (txdb)-[:OWNED_BY]->(team);

// ── Compliance Governance ─────────────────────────────────────────────────────
MATCH (payapi:Service {name: 'PaymentAPI', client_id: 'FINCORE_UK_001'})
MATCH (pci:ComplianceRule {framework: 'PCI-DSS', client_id: 'FINCORE_UK_001'})
MERGE (payapi)-[:GOVERNED_BY]->(pci);

MATCH (txdb:Service {name: 'TransactionDB', client_id: 'FINCORE_UK_001'})
MATCH (sox:ComplianceRule {framework: 'SOX', client_id: 'FINCORE_UK_001'})
MERGE (txdb)-[:GOVERNED_BY]->(sox);
