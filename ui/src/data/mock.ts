import type { Client, Incident, ActivityFeedEntry, AuditEntry, Playbook } from '@/types/atlas';

// ─── Helpers ─────────────────────────────────────────────────────────────────

const ago = (mins: number) => new Date(Date.now() - mins * 60_000).toISOString();
const fromNow = (mins: number) => new Date(Date.now() + mins * 60_000).toISOString();
const ts = (offsetMins: number) => {
  const d = new Date(Date.now() - offsetMins * 60_000);
  return d.toLocaleTimeString('en-GB', { hour12: false });
};
const isoTs = (offsetMins: number) => new Date(Date.now() - offsetMins * 60_000).toISOString();

// ─── Clients ─────────────────────────────────────────────────────────────────

export const mockClients: Client[] = [
  { id: 'client-financecore', name: 'FinanceCore Holdings', health: 'critical', activeIncidents: 1, slaCompliance: 97.8, trustLevel: 'L2 Automation', lastActivity: '2 min ago', complianceFlags: ['PCI-DSS', 'SOX'] },
  { id: 'client-retailmax', name: 'RetailMax Group', health: 'warning', activeIncidents: 1, slaCompliance: 98.5, trustLevel: 'L1 Automation', lastActivity: '6 min ago' },
  { id: 'client-3', name: 'Deutsche Kredit Bank', health: 'healthy', activeIncidents: 0, slaCompliance: 99.8, trustLevel: 'L2 Automation', lastActivity: '14 min ago', complianceFlags: ['PCI-DSS', 'SOX'] },
  { id: 'client-4', name: 'Eurostar Rail Operations', health: 'healthy', activeIncidents: 0, slaCompliance: 99.9, trustLevel: 'L2 Assistance', lastActivity: '22 min ago' },
  { id: 'client-5', name: 'Marseille Port Authority', health: 'healthy', activeIncidents: 0, slaCompliance: 99.4, trustLevel: 'Observation', lastActivity: '31 min ago' },
  { id: 'client-6', name: 'Bundesamt für Sicherheit', health: 'healthy', activeIncidents: 0, slaCompliance: 100, trustLevel: 'L1 Automation', lastActivity: '45 min ago', complianceFlags: ['SOX'] },
  { id: 'client-7', name: 'Swiss Federal Railways', health: 'healthy', activeIncidents: 0, slaCompliance: 99.7, trustLevel: 'L1 Automation', lastActivity: '18 min ago' },
  { id: 'client-8', name: 'National Health Trust', health: 'healthy', activeIncidents: 0, slaCompliance: 99.5, trustLevel: 'L2 Assistance', lastActivity: '27 min ago' },
  { id: 'client-9', name: 'UK Border Agency', health: 'healthy', activeIncidents: 0, slaCompliance: 99.1, trustLevel: 'L1 Assistance', lastActivity: '12 min ago' },
  { id: 'client-10', name: 'Rijkswaterstaat', health: 'healthy', activeIncidents: 0, slaCompliance: 99.6, trustLevel: 'Observation', lastActivity: '38 min ago' },
];

// ─── Active Incidents ─────────────────────────────────────────────────────────

export const financeCoreIncident: Incident = {
  id: 'INC0041827',
  clientId: 'client-financecore',
  clientName: 'FinanceCore Holdings',
  priority: 'P1',
  status: 'Awaiting L1',
  affectedServices: ['PaymentGateway', 'TransactionProcessor', 'FraudEngine'],
  detectedAt: ago(8),
  slaDeadline: fromNow(12),
  summary: 'HikariCP connection pool on PaymentGateway has reached 94% utilization (47/50 connections). Cascading latency to TransactionProcessor (p99: 4.2s, threshold: 500ms) and degraded FraudEngine scoring throughput. ~23% of payment requests timing out.',
  businessImpact: 'Real-time payment processing degraded for corporate clients. 23% transaction timeout rate affecting ~£2.4M/hour in payment volume. FraudEngine scoring delayed — all transactions queued, none bypassed.',
  services: [
    { id: 'fc-s1', name: 'PaymentGateway', technology: 'Java Spring Boot / HikariCP', health: 'critical', criticality: 'High', triggerMetric: 'Connection pool utilization', triggerValue: '94% (47/50)', lastDeployment: '3 days ago' },
    { id: 'fc-s2', name: 'TransactionProcessor', technology: 'Java Spring Boot', health: 'warning', criticality: 'High', triggerMetric: 'Response time (p99)', triggerValue: '4.2s (threshold: 500ms)' },
    { id: 'fc-s3', name: 'FraudEngine', technology: 'Python / TensorFlow Serving', health: 'warning', criticality: 'High', triggerMetric: 'Scoring throughput', triggerValue: '340/s (baseline: 1,200/s)' },
    { id: 'fc-s4', name: 'PostgreSQL Primary', technology: 'PostgreSQL 15', health: 'healthy', criticality: 'High', triggerMetric: 'Active connections', triggerValue: '142/200' },
    { id: 'fc-s5', name: 'Redis Cache', technology: 'Redis 7.2', health: 'healthy', criticality: 'Medium', triggerMetric: 'Memory usage', triggerValue: '62% (3.1GB/5GB)' },
  ],
  deploymentCorrelation: {
    changeId: 'CHG0008834',
    description: 'Updated HikariCP connection pool configuration — reduced maxPoolSize from 100 to 50 for memory optimisation during off-peak maintenance window',
    deployedBy: 'M. Chen',
    deployedAt: ago(3 * 24 * 60),
    cabRiskRating: 'Low',
    daysAgo: 3,
  },
  historicalMatch: {
    incidentId: 'INC0038291',
    occurredAt: '2024-11-14',
    similarity: 91,
    rootCause: 'Connection pool exhaustion after pool size reduction during maintenance window. Monday morning transaction volume exceeded reduced capacity.',
    resolution: 'Restored maxPoolSize to 100 via Spring Actuator PATCH endpoint, validated recovery over 5-minute window.',
  },
  rootCause: {
    diagnosis: 'HikariCP connection pool exhaustion caused by CHG0008834 reducing maxPoolSize from 100 to 50. Current weekday transaction volume requires minimum 85 concurrent connections. The reduced pool size is insufficient, causing connection wait timeouts that cascade to TransactionProcessor and FraudEngine.',
    confidence: 94,
    factors: { historicalAccuracy: 96, rootCauseCertainty: 92, actionSafetyClass: 98, evidenceFreshness: 90 },
    vetoes: [],
  },
  alternativeHypotheses: [
    {
      hypothesis: 'Database connection leak in TransactionProcessor service',
      evidenceFor: ['TransactionProcessor response time degraded', 'PostgreSQL active connections elevated at 142/200'],
      evidenceAgainst: ['PaymentGateway pool exhausted first (timeline correlation)', 'No connection leak pattern in TransactionProcessor logs', 'PostgreSQL connections within safe range at 71%'],
    },
    {
      hypothesis: 'Increased transaction volume exceeding system capacity',
      evidenceFor: ['Monday morning typically shows 15–20% higher transaction volume'],
      evidenceAgainst: ['Transaction volume within 1σ of Monday baseline', 'No promotional event active', 'Issue correlates precisely with pool size change deployment, not traffic spike'],
    },
  ],
  recommendedAction: {
    playbookName: 'connection-pool-recovery-v2',
    description: 'Restore HikariCP maxPoolSize to 150 via Spring Actuator PATCH endpoint on PaymentGateway. Monitor connection pool utilization, TransactionProcessor p99 latency, and FraudEngine scoring throughput for 5-minute validation window.',
    estimatedTime: '4 minutes',
    riskClass: 'Low',
    rollbackAvailable: true,
  },
  engineerExplanation: 'CHG0008834 reduced maxPoolSize from 100→50 three days ago. Monday peak volume (avg 82 concurrent connections) now exceeds pool capacity, causing HikariCP to queue requests. Queue depth is growing at ~3 connections/minute. Immediate fix: PATCH /actuator/config with maxPoolSize=150. Rollback: connection-pool-recovery-v2-rollback restores previous value.',
  serviceNowTicketId: 'INC0041827',
};

export const retailMaxIncident: Incident = {
  id: 'INC0041830',
  clientId: 'client-retailmax',
  clientName: 'RetailMax Group',
  priority: 'P2',
  status: 'Awaiting L2',
  affectedServices: ['ProductCatalog', 'Redis Cache Cluster', 'SearchService'],
  detectedAt: ago(22),
  slaDeadline: fromNow(38),
  summary: 'Redis cache cluster serving ProductCatalog has triggered OOM warnings at 94% memory utilization. Cache eviction rate spiked to 8,400 keys/min (baseline: 120/min), causing cache hit ratio to drop from 96% to 41%. ProductCatalog response times increased from 80ms to 2.8s.',
  businessImpact: 'Product browsing severely degraded. Page load times 3–4× slower for 340K daily active users. Search results contain stale pricing on ~12% of displayed products. No checkout or payment impact — separate cache layer.',
  services: [
    { id: 'rm-s1', name: 'Redis Cache Cluster', technology: 'Redis 7.2 Cluster (3 nodes)', health: 'critical', criticality: 'High', triggerMetric: 'Memory utilization', triggerValue: '94% (15.04GB/16GB)' },
    { id: 'rm-s2', name: 'ProductCatalog', technology: 'Node.js / Express', health: 'warning', criticality: 'High', triggerMetric: 'Response time (p95)', triggerValue: '2.8s (threshold: 300ms)' },
    { id: 'rm-s3', name: 'SearchService', technology: 'Elasticsearch 8.11', health: 'warning', criticality: 'Medium', triggerMetric: 'Stale result rate', triggerValue: '12% (threshold: 1%)' },
    { id: 'rm-s4', name: 'PostgreSQL Replica', technology: 'PostgreSQL 15 (read replica)', health: 'healthy', criticality: 'High', triggerMetric: 'Query load', triggerValue: '2,340 qps (capacity: 5,000)' },
  ],
  deploymentCorrelation: {
    changeId: 'CHG0009012',
    description: 'Deployed analytics data pipeline that caches intermediate aggregation results in the same Redis cluster used by ProductCatalog',
    deployedBy: 'T. Rodriguez',
    deployedAt: ago(18 * 60),
    cabRiskRating: 'Low',
    daysAgo: 1,
  },
  historicalMatch: {
    incidentId: 'INC0039445',
    occurredAt: '2024-12-08',
    similarity: 84,
    rootCause: 'Background batch job consuming excessive Redis memory, causing eviction of frequently-accessed product cache entries.',
    resolution: 'Terminated batch job, flushed analytics namespace, pre-warmed product cache from database.',
  },
  rootCause: {
    diagnosis: 'Redis OOM caused by CHG0009012 deploying an analytics pipeline that writes intermediate aggregation results to the ProductCatalog Redis cluster. Analytics keys consuming ~6.2GB (41% of total capacity), displacing product cache entries and triggering a cache eviction storm. Eviction policy (allkeys-lru) is removing frequently-accessed product data in favour of analytics keys with longer TTLs.',
    confidence: 87,
    factors: { historicalAccuracy: 84, rootCauseCertainty: 89, actionSafetyClass: 92, evidenceFreshness: 82 },
    vetoes: [],
  },
  alternativeHypotheses: [
    {
      hypothesis: 'Sudden spike in unique product views causing natural cache growth',
      evidenceFor: ['Flash sale event scheduled for next week might have early traffic', 'Product view count 8% above daily average'],
      evidenceAgainst: ['8% traffic increase cannot explain 40× eviction rate spike', 'Memory growth timeline correlates with analytics pipeline deployment', 'Analytics namespace keys account for 41% of memory — confirmed via MEMORY USAGE sampling'],
    },
    {
      hypothesis: 'Redis memory fragmentation causing inflated memory reporting',
      evidenceFor: ['mem_fragmentation_ratio at 1.12 (slightly elevated)'],
      evidenceAgainst: ['Fragmentation ratio of 1.12 accounts for only ~1.8GB overhead', 'Key-level analysis confirms analytics keys are primary consumer', 'Eviction rate increase directly follows analytics pipeline deployment'],
    },
  ],
  recommendedAction: {
    playbookName: 'redis-memory-policy-rollback-v1',
    description: 'Terminate the analytics data pipeline process, flush the "analytics:*" Redis namespace (~6.2GB), then pre-warm the product cache from PostgreSQL replica for the top 10,000 SKUs by access frequency. Monitor cache hit ratio recovery and ProductCatalog response times.',
    estimatedTime: '6 minutes',
    riskClass: 'Low',
    rollbackAvailable: true,
  },
  engineerExplanation: 'CHG0009012 (18h ago) deployed an analytics pipeline writing to the shared ProductCatalog Redis cluster without a dedicated namespace TTL policy. Analytics keys now occupy 6.2GB of 16GB total. The allkeys-lru eviction policy is evicting hot product cache entries to make room. Fix: flush analytics:* namespace and set maxmemory-policy to volatile-lru to protect non-expiring product keys.',
  serviceNowTicketId: 'INC0041830',
};

// ─── Resolved Incidents ───────────────────────────────────────────────────────

const resolvedIncidents: Incident[] = [
  {
    id: 'INC0041835', clientId: 'client-3', clientName: 'Deutsche Kredit Bank', priority: 'P1', status: 'Resolved',
    affectedServices: ['FraudDetection', 'TransactionProcessor'],
    detectedAt: ago(45), slaDeadline: ago(20),
    summary: 'FraudDetection ML model pipeline experienced elevated inference latency causing delayed transaction scoring.',
    businessImpact: 'Transaction scoring delayed by ~8 seconds. No fraudulent transactions missed — fallback rule engine active.',
    services: [
      { id: 's7', name: 'FraudDetection', technology: 'Python / TensorFlow', health: 'healthy', criticality: 'High', triggerMetric: 'Inference latency', triggerValue: '45ms (recovered)' },
      { id: 's8', name: 'TransactionProcessor', technology: 'Java Spring Boot', health: 'healthy', criticality: 'High', triggerMetric: 'Queue depth', triggerValue: '12 (recovered)' },
    ],
    rootCause: { diagnosis: 'GPU memory pressure from concurrent model retraining job caused inference latency spike. Retraining job was not resource-capped and consumed 94% of GPU VRAM.', confidence: 88, factors: { historicalAccuracy: 85, rootCauseCertainty: 90, actionSafetyClass: 92, evidenceFreshness: 84 } },
    alternativeHypotheses: [],
    recommendedAction: { playbookName: 'ml-pipeline-priority-v1', description: 'Deprioritize background retraining job, clear GPU memory allocation, restore inference pipeline priority.', estimatedTime: '3 minutes', riskClass: 'Low', rollbackAvailable: true },
    resolvedAt: ago(41), mttr: '4m 12s', approvedBy: 'S. Weber',
  },
  {
    id: 'INC0041825', clientId: 'client-4', clientName: 'Eurostar Rail Operations', priority: 'P3', status: 'Resolved',
    affectedServices: ['TicketingGateway'],
    detectedAt: ago(50), slaDeadline: ago(10),
    summary: 'TLS certificate on TicketingGateway expires in 48 hours. Auto-renewal initiated via ACME protocol.',
    businessImpact: 'No current impact. Preventive action — certificate would have expired causing service outage.',
    services: [{ id: 's11', name: 'TicketingGateway', technology: 'Nginx', health: 'healthy', criticality: 'High', triggerMetric: 'Cert expiry', triggerValue: '48h remaining' }],
    rootCause: { diagnosis: 'Scheduled TLS certificate approaching expiration threshold. ACME auto-renewal triggered.', confidence: 99, factors: { historicalAccuracy: 100, rootCauseCertainty: 100, actionSafetyClass: 100, evidenceFreshness: 98 } },
    alternativeHypotheses: [],
    recommendedAction: { playbookName: 'tls-cert-renewal-v3', description: 'Automated TLS certificate renewal via ACME protocol.', estimatedTime: '2 minutes', riskClass: 'Low', rollbackAvailable: true },
    resolvedAt: ago(48), mttr: '1m 45s', approvedBy: 'ATLAS (Auto)',
  },
  {
    id: 'INC0041801', clientId: 'client-financecore', clientName: 'FinanceCore Holdings', priority: 'P2', status: 'Resolved',
    affectedServices: ['AuthService', 'CoreBanking API'],
    detectedAt: ago(3 * 60), slaDeadline: ago(150),
    summary: 'OAuth token refresh storm on AuthService causing elevated CPU and delayed CoreBanking API responses.',
    businessImpact: 'Login latency increased 3× for ~5 minutes. No data loss or security breach.',
    services: [{ id: 'fc-r1', name: 'AuthService', technology: 'Node.js / Passport', health: 'healthy', criticality: 'High', triggerMetric: 'CPU usage', triggerValue: '28% (recovered)' }],
    rootCause: { diagnosis: 'Token cache TTL misconfiguration after deployment caused mass simultaneous token refresh. 4,200 concurrent refresh requests overwhelmed AuthService.', confidence: 91, factors: { historicalAccuracy: 88, rootCauseCertainty: 93, actionSafetyClass: 95, evidenceFreshness: 89 } },
    alternativeHypotheses: [],
    recommendedAction: { playbookName: 'connection-pool-recovery-v2', description: 'Reset token cache TTL to 3600s, flush expired token store, restore rate limiting.', estimatedTime: '2 minutes', riskClass: 'Low', rollbackAvailable: true },
    resolvedAt: ago(174), mttr: '2m 34s', approvedBy: 'A. Petrov',
  },
  {
    id: 'INC0041818', clientId: 'client-retailmax', clientName: 'RetailMax Group', priority: 'P3', status: 'Resolved',
    affectedServices: ['CDN Origin', 'ProductCatalog'],
    detectedAt: ago(5 * 60), slaDeadline: ago(4 * 60),
    summary: 'CDN cache purge triggered by stale product image URLs. Brief spike in origin requests.',
    businessImpact: 'Slightly slower image load for ~90 seconds. No checkout impact.',
    services: [{ id: 'rm-r1', name: 'CDN Origin', technology: 'CloudFront', health: 'healthy', criticality: 'Medium', triggerMetric: 'Origin requests/s', triggerValue: '120/s (recovered)' }],
    rootCause: { diagnosis: 'Bulk product image update triggered cache invalidation storm. 18,000 cache keys invalidated simultaneously, causing origin request spike.', confidence: 95, factors: { historicalAccuracy: 92, rootCauseCertainty: 96, actionSafetyClass: 98, evidenceFreshness: 91 } },
    alternativeHypotheses: [],
    recommendedAction: { playbookName: 'redis-memory-policy-rollback-v1', description: 'Rate-limit cache purge operations to 500 keys/second.', estimatedTime: '1 minute', riskClass: 'Low', rollbackAvailable: true },
    resolvedAt: ago(299), mttr: '1m 22s', approvedBy: 'ATLAS (Auto)',
  },
  {
    id: 'INC0041810', clientId: 'client-7', clientName: 'Swiss Federal Railways', priority: 'P2', status: 'Resolved',
    affectedServices: ['ScheduleService', 'PassengerInfo'],
    detectedAt: ago(7 * 60), slaDeadline: ago(6 * 60),
    summary: 'Schedule data feed delay causing stale departure information on passenger displays.',
    businessImpact: 'Passenger information boards showed 3-minute-old data for ~8 minutes.',
    services: [{ id: 'sr-r1', name: 'ScheduleService', technology: 'Go / gRPC', health: 'healthy', criticality: 'High', triggerMetric: 'Feed delay', triggerValue: '0s (recovered)' }],
    rootCause: { diagnosis: 'Upstream data feed provider experienced transient connectivity issue. Consumer group rebalance triggered by network partition.', confidence: 82, factors: { historicalAccuracy: 78, rootCauseCertainty: 85, actionSafetyClass: 90, evidenceFreshness: 80 } },
    alternativeHypotheses: [],
    recommendedAction: { playbookName: 'kafka-consumer-reset-v1', description: 'Reset data feed consumer and re-sync from last committed offset.', estimatedTime: '3 minutes', riskClass: 'Low', rollbackAvailable: true },
    resolvedAt: ago(408), mttr: '3m 15s', approvedBy: 'S. Weber',
  },
  {
    id: 'INC0041805', clientId: 'client-8', clientName: 'National Health Trust', priority: 'P2', status: 'Resolved',
    affectedServices: ['PatientPortal', 'AppointmentScheduler'],
    detectedAt: ago(10 * 60), slaDeadline: ago(9 * 60),
    summary: 'Patient portal login timeout due to LDAP directory service overload during morning shift change.',
    businessImpact: 'Staff login delayed ~15 seconds for 4 minutes. No patient data affected.',
    services: [{ id: 'nht-r1', name: 'PatientPortal', technology: 'React / .NET Core', health: 'healthy', criticality: 'High', triggerMetric: 'Auth latency', triggerValue: '180ms (recovered)' }],
    rootCause: { diagnosis: 'LDAP connection pool saturated during peak shift change logins. 847 concurrent authentication requests exceeded pool capacity of 200.', confidence: 90, factors: { historicalAccuracy: 87, rootCauseCertainty: 92, actionSafetyClass: 94, evidenceFreshness: 86 } },
    alternativeHypotheses: [],
    recommendedAction: { playbookName: 'connection-pool-recovery-v2', description: 'Expand LDAP connection pool to 500, add connection timeout of 5s.', estimatedTime: '2 minutes', riskClass: 'Low', rollbackAvailable: true },
    resolvedAt: ago(594), mttr: '2m 48s', approvedBy: 'A. Petrov',
  },
  {
    id: 'INC0041798', clientId: 'client-9', clientName: 'UK Border Agency', priority: 'P3', status: 'Resolved',
    affectedServices: ['PassportVerification'],
    detectedAt: ago(12 * 60), slaDeadline: ago(11 * 60),
    summary: 'PassportVerification OCR model slight accuracy degradation after image preprocessing library update.',
    businessImpact: 'Manual verification fallback triggered for ~2% of scans. No traveller delays.',
    services: [{ id: 'ukb-r1', name: 'PassportVerification', technology: 'Python / OpenCV', health: 'healthy', criticality: 'High', triggerMetric: 'OCR accuracy', triggerValue: '99.7% (recovered)' }],
    rootCause: { diagnosis: 'Image preprocessing library update changed default colour space conversion from BGR to RGB. OCR model trained on BGR input, causing 2.3% accuracy degradation.', confidence: 93, factors: { historicalAccuracy: 90, rootCauseCertainty: 95, actionSafetyClass: 96, evidenceFreshness: 88 } },
    alternativeHypotheses: [],
    recommendedAction: { playbookName: 'k8s-pod-reschedule-v2', description: 'Rollback preprocessing library to v2.4.1, redeploy PassportVerification pods.', estimatedTime: '4 minutes', riskClass: 'Low', rollbackAvailable: true },
    resolvedAt: ago(708), mttr: '3m 52s', approvedBy: 'J. Nakamura',
  },
  {
    id: 'INC0041792', clientId: 'client-6', clientName: 'Bundesamt für Sicherheit', priority: 'P3', status: 'Resolved',
    affectedServices: ['AuditTrailService'],
    detectedAt: ago(15 * 60), slaDeadline: ago(14 * 60),
    summary: 'Audit trail log rotation failed due to disk space threshold breach on logging partition.',
    businessImpact: 'No data loss — audit logs buffered in memory. Rotation resumed after cleanup.',
    services: [{ id: 'bfs-r1', name: 'AuditTrailService', technology: 'Java / Log4j2', health: 'healthy', criticality: 'High', triggerMetric: 'Disk usage', triggerValue: '62% (recovered)' }],
    rootCause: { diagnosis: 'Archived logs not rotated due to cron job misconfiguration after server migration. 14GB of uncompressed logs accumulated over 6 days.', confidence: 97, factors: { historicalAccuracy: 95, rootCauseCertainty: 98, actionSafetyClass: 99, evidenceFreshness: 93 } },
    alternativeHypotheses: [],
    recommendedAction: { playbookName: 'k8s-pod-reschedule-v2', description: 'Fix cron schedule, compress and archive logs, restore rotation policy.', estimatedTime: '2 minutes', riskClass: 'Low', rollbackAvailable: true },
    resolvedAt: ago(894), mttr: '1m 18s', approvedBy: 'ATLAS (Auto)',
  },
  {
    id: 'INC0041788', clientId: 'client-5', clientName: 'Marseille Port Authority', priority: 'P3', status: 'Resolved',
    affectedServices: ['IoT Data Ingestion', 'Alert Manager'],
    detectedAt: ago(18 * 60), slaDeadline: ago(17 * 60),
    summary: 'IoT sensor data ingestion lag due to Kafka consumer group rebalance after node restart.',
    businessImpact: 'Sensor telemetry delayed by ~45 seconds during rebalance. No operational impact.',
    services: [{ id: 'mp-r1', name: 'IoT Data Ingestion', technology: 'Kafka Streams', health: 'healthy', criticality: 'Medium', triggerMetric: 'Consumer lag', triggerValue: '0 (recovered)' }],
    rootCause: { diagnosis: 'Kafka consumer group rebalance after scheduled node maintenance restart. Rebalance took 43 seconds due to large partition count (240 partitions across 3 consumers).', confidence: 96, factors: { historicalAccuracy: 94, rootCauseCertainty: 97, actionSafetyClass: 98, evidenceFreshness: 92 } },
    alternativeHypotheses: [],
    recommendedAction: { playbookName: 'kafka-consumer-reset-v1', description: 'Verified auto-recovery. No action needed — consumer group rebalanced successfully.', estimatedTime: '1 minute', riskClass: 'Low', rollbackAvailable: true },
    resolvedAt: ago(1079), mttr: '0m 58s', approvedBy: 'ATLAS (Auto)',
  },
  {
    id: 'INC0041782', clientId: 'client-10', clientName: 'Rijkswaterstaat', priority: 'P3', status: 'Resolved',
    affectedServices: ['Water Level Monitor'],
    detectedAt: ago(20 * 60), slaDeadline: ago(19 * 60),
    summary: 'Water level monitoring dashboard data refresh intermittently stalling due to WebSocket connection drops.',
    businessImpact: 'Dashboard data stale for ~30 seconds per drop. Automatic reconnect resolved each instance.',
    services: [{ id: 'rw-r1', name: 'Water Level Monitor', technology: 'Python / FastAPI / WebSocket', health: 'healthy', criticality: 'Medium', triggerMetric: 'WS reconnects/hr', triggerValue: '0 (recovered)' }],
    rootCause: { diagnosis: 'Load balancer idle timeout (60s) shorter than WebSocket heartbeat interval (90s). Connections dropped silently after 60s of inactivity.', confidence: 94, factors: { historicalAccuracy: 91, rootCauseCertainty: 96, actionSafetyClass: 97, evidenceFreshness: 90 } },
    alternativeHypotheses: [],
    recommendedAction: { playbookName: 'k8s-pod-reschedule-v2', description: 'Increase LB idle timeout to 120s to match WebSocket heartbeat interval.', estimatedTime: '1 minute', riskClass: 'Low', rollbackAvailable: true },
    resolvedAt: ago(1198), mttr: '1m 05s', approvedBy: 'ATLAS (Auto)',
  },
];

export const mockIncidents: Incident[] = [
  financeCoreIncident,
  retailMaxIncident,
  ...resolvedIncidents,
];

// ─── Activity Feed ────────────────────────────────────────────────────────────

export const mockActivityFeed: ActivityFeedEntry[] = [
  { id: 'af1', timestamp: ts(0.1), clientName: 'FinanceCore Holdings', clientHealth: 'critical', description: 'P1 ACTIVE — PaymentGateway HikariCP pool at 94% (47/50). Cascade confirmed to TransactionProcessor (p99: 4.2s) and FraudEngine (340/s). Routing to L1 triage.', priority: 'P1' },
  { id: 'af2', timestamp: ts(0.5), clientName: 'FinanceCore Holdings', clientHealth: 'critical', description: 'N6 confidence scoring complete: 94% composite score. Factor breakdown — historical: 96%, certainty: 92%, safety: 98%, freshness: 90%. No vetoes fired.' },
  { id: 'af3', timestamp: ts(1.2), clientName: 'FinanceCore Holdings', clientHealth: 'critical', description: 'N5 LLM reasoning complete. Root cause locked: CHG0008834 pool reduction (100→50) insufficient for Monday peak volume. Recommended: connection-pool-recovery-v2.' },
  { id: 'af4', timestamp: ts(2.1), clientName: 'FinanceCore Holdings', clientHealth: 'critical', description: 'N4 semantic search: INC0038291 matched at 91% similarity (2024-11-14). Same root cause pattern — pool exhaustion post-maintenance. Historical resolution: 4m 12s.' },
  { id: 'af5', timestamp: ts(3.0), clientName: 'FinanceCore Holdings', clientHealth: 'critical', description: 'N3 graph correlation: blast radius confirmed — PaymentGateway → TransactionProcessor → FraudEngine. CHG0008834 deployment node linked.' },
  { id: 'af6', timestamp: ts(4.2), clientName: 'FinanceCore Holdings', clientHealth: 'critical', description: 'N1 classifier: P1 assigned. SLA breach in 12 minutes. ServiceNow ticket INC0041827 created. ITSM notification sent to on-call L1 team.' },
  { id: 'af7', timestamp: ts(5.5), clientName: 'FinanceCore Holdings', clientHealth: 'critical', description: 'Java agent detected CONNECTION_POOL_EXHAUSTED on PaymentGateway. Detection confidence: 97%. Evidence package dispatched to correlation engine.' },
  { id: 'af8', timestamp: ts(6.0), clientName: 'RetailMax Group', clientHealth: 'warning', description: 'P2 ACTIVE — Redis cache cluster OOM at 94% memory. Eviction rate 8,400 keys/min (baseline: 120). ProductCatalog p95 latency: 2.8s. Routing to L2.', priority: 'P2' },
  { id: 'af9', timestamp: ts(7.3), clientName: 'RetailMax Group', clientHealth: 'warning', description: 'N5 reasoning: analytics pipeline (CHG0009012) consuming 6.2GB of 16GB Redis capacity. allkeys-lru evicting product cache. 87% confidence. Novel pattern elements — L2 review required.' },
  { id: 'af10', timestamp: ts(8.1), clientName: 'RetailMax Group', clientHealth: 'warning', description: 'N4 semantic search: INC0039445 matched at 84% similarity (2024-12-08). Background batch job pattern. Cross-client federated search returned 3 additional matches.' },
  { id: 'af11', timestamp: ts(9.0), clientName: 'UK Border Agency', clientHealth: 'healthy', description: 'Early warning: PassportVerification service trending 1.8σ above baseline response time. No threshold crossed. Monitoring elevated — will auto-escalate at 2.5σ.' },
  { id: 'af12', timestamp: ts(14), clientName: 'Deutsche Kredit Bank', clientHealth: 'healthy', description: 'INC0041835 resolved — FraudDetection inference latency recovered. MTTR: 4m 12s. Decision record written. Recalibration triggered for java-spring-boot pattern.' },
  { id: 'af13', timestamp: ts(22), clientName: 'Eurostar Rail Operations', clientHealth: 'healthy', description: 'INC0041825 auto-resolved — TLS certificate renewal on TicketingGateway completed. New cert valid until 2026-03-29. MTTR: 1m 45s.' },
  { id: 'af14', timestamp: ts(28), clientName: 'Swiss Federal Railways', clientHealth: 'healthy', description: 'Detection heartbeat: all 12 monitored services within normal parameters. Anomaly score: 0.02 (threshold: 2.5σ).' },
  { id: 'af15', timestamp: ts(31), clientName: 'Marseille Port Authority', clientHealth: 'healthy', description: 'Detection heartbeat: all 8 monitored services within normal parameters. IoT ingestion lag: 0ms.' },
  { id: 'af16', timestamp: ts(35), clientName: 'National Health Trust', clientHealth: 'healthy', description: 'INC0041805 resolved — PatientPortal LDAP pool expanded. Auth latency: 180ms (recovered from 4.2s). MTTR: 2m 48s. Approved by A. Petrov.' },
  { id: 'af17', timestamp: ts(40), clientName: 'Bundesamt für Sicherheit', clientHealth: 'healthy', description: 'INC0041792 auto-resolved — AuditTrailService log rotation restored. Disk usage: 62% (recovered from 89%). MTTR: 1m 18s.' },
  { id: 'af18', timestamp: ts(45), clientName: 'Rijkswaterstaat', clientHealth: 'healthy', description: 'INC0041782 auto-resolved — WebSocket LB timeout corrected. WS reconnect rate: 0/hr (recovered). MTTR: 1m 05s.' },
  { id: 'af19', timestamp: ts(50), clientName: 'UK Border Agency', clientHealth: 'healthy', description: 'INC0041798 resolved — PassportVerification OCR accuracy restored to 99.7%. Library rollback successful. MTTR: 3m 52s. Approved by J. Nakamura.' },
  { id: 'af20', timestamp: ts(55), clientName: 'FinanceCore Holdings', clientHealth: 'healthy', description: 'Knowledge base updated: INC0041801 resolution record added. Token cache TTL pattern indexed. Vector embedding stored for future similarity matching.' },
];

// ─── Audit Log ────────────────────────────────────────────────────────────────

export const mockAuditLog: AuditEntry[] = [
  {
    id: 'au1', timestamp: isoTs(0.1), incidentId: 'INC0041827', client: 'FinanceCore Holdings',
    actionType: 'Detection', actor: 'ATLAS', outcome: 'Success', confidence: 94,
    details: { reasoningChain: 'Java agent detected CONNECTION_POOL_EXHAUSTED on PaymentGateway (confidence: 97%). Correlation engine confirmed cascade to TransactionProcessor and FraudEngine. N1 classifier assigned P1 priority. N3 graph traversal linked CHG0008834 deployment. N4 semantic search matched INC0038291 at 91%. N5 LLM reasoning locked root cause at 94% confidence.', vetoes: [], playbookSteps: ['Signal ingestion from Java agent', 'Anomaly threshold breach confirmed', 'Dependency graph traversal', 'Historical pattern matching', 'LLM root cause reasoning', 'Confidence scoring', 'L1 routing decision'], metricValues: { 'pool_utilization': 94, 'p99_latency_ms': 4200, 'fraud_throughput': 340 } },
  },
  {
    id: 'au2', timestamp: isoTs(0.5), incidentId: 'INC0041827', client: 'FinanceCore Holdings',
    actionType: 'Classification', actor: 'ATLAS', outcome: 'Success', confidence: 94,
    details: { reasoningChain: 'N1 classifier assigned P1 priority based on: payment processing impact (£2.4M/hour), cascade to 3 critical services, SLA breach in 12 minutes. ServiceNow ticket INC0041827 created via REST API.', vetoes: [], playbookSteps: ['Priority assignment: P1', 'SLA timer started: 20 minutes', 'ServiceNow ticket created: INC0041827', 'On-call L1 team notified'], metricValues: { 'sla_minutes_remaining': 12, 'affected_services': 3 } },
  },
  {
    id: 'au3', timestamp: isoTs(1.0), incidentId: 'INC0041827', client: 'FinanceCore Holdings',
    actionType: 'Routing', actor: 'ATLAS', outcome: 'Success', confidence: 94,
    details: { reasoningChain: 'N7 router: composite confidence 94% exceeds L1 threshold (70%). Trust level L2 Automation. Routing to L1_HUMAN_REVIEW — PCI-DSS compliance requires human approval for production changes. Dual-approval not required for Class 1 playbooks.', vetoes: ['PCI-DSS: human approval required for production changes'], playbookSteps: ['Confidence threshold check: PASS (94% > 70%)', 'Trust level check: L2 Automation', 'Compliance check: PCI-DSS human approval required', 'Routing decision: L1_HUMAN_REVIEW'], metricValues: { 'confidence': 94, 'trust_level': 3 } },
  },
  {
    id: 'au4', timestamp: isoTs(22), incidentId: 'INC0041830', client: 'RetailMax Group',
    actionType: 'Detection', actor: 'ATLAS', outcome: 'Success', confidence: 87,
    details: { reasoningChain: 'Redis agent detected REDIS_OOM on ProductCatalog cache cluster. Memory utilization: 94%. Eviction rate: 8,400 keys/min (70× baseline). N3 graph linked CHG0009012 analytics pipeline deployment. N4 semantic search matched INC0039445 at 84%. N5 reasoning identified analytics namespace as root cause.', vetoes: [], playbookSteps: ['Redis OOM signal ingested', 'Memory utilization threshold breach', 'Deployment correlation: CHG0009012', 'Historical match: INC0039445 (84%)', 'Root cause: analytics namespace overflow'], metricValues: { 'memory_pct': 94, 'eviction_rate': 8400, 'cache_hit_ratio': 41 } },
  },
  {
    id: 'au5', timestamp: isoTs(45), incidentId: 'INC0041835', client: 'Deutsche Kredit Bank',
    actionType: 'Resolution', actor: 'S. Weber', outcome: 'Success', confidence: 88,
    details: { reasoningChain: 'L2 engineer S. Weber approved connection-pool-recovery-v2 playbook. Pre-validation: GPU memory check passed. Execution: retraining job deprioritized (nice +19), GPU memory cleared. Post-validation: inference latency recovered to 45ms within 3 minutes.', vetoes: [], playbookSteps: ['Pre-validation: GPU memory check', 'Deprioritize retraining job (nice +19)', 'Clear GPU memory allocation', 'Restore inference pipeline priority', 'Post-validation: latency monitoring', 'Resolution confirmed: 45ms latency'], metricValues: { 'inference_latency_ms': 45, 'gpu_memory_pct': 42, 'throughput': 1180 } },
  },
  {
    id: 'au6', timestamp: isoTs(50), incidentId: 'INC0041825', client: 'Eurostar Rail Operations',
    actionType: 'Auto-Resolution', actor: 'ATLAS', outcome: 'Success', confidence: 99,
    details: { reasoningChain: 'P3 TLS certificate expiry detected 48h before expiry. Trust level L2 Assistance — auto-execute eligible for Class 1 playbooks. ACME renewal initiated automatically. Certificate renewed successfully. No human intervention required.', vetoes: [], playbookSteps: ['Certificate expiry detection: 48h threshold', 'ACME challenge initiated', 'DNS-01 challenge completed', 'Certificate issued: valid 90 days', 'Nginx reload: zero-downtime'], metricValues: { 'cert_validity_days': 90, 'renewal_time_seconds': 105 } },
  },
  {
    id: 'au7', timestamp: isoTs(3 * 60), incidentId: 'INC0041801', client: 'FinanceCore Holdings',
    actionType: 'Resolution', actor: 'A. Petrov', outcome: 'Success', confidence: 91,
    details: { reasoningChain: 'L1 engineer A. Petrov approved token cache TTL reset. Pre-validation: AuthService health check passed. Execution: token cache TTL set to 3600s, expired token store flushed, rate limiting restored. Post-validation: login latency recovered to 180ms.', vetoes: [], playbookSteps: ['Pre-validation: AuthService health check', 'Set token cache TTL: 3600s', 'Flush expired token store', 'Restore rate limiting: 100 req/s', 'Post-validation: latency monitoring'], metricValues: { 'auth_latency_ms': 180, 'token_refresh_rate': 12, 'cpu_pct': 28 } },
  },
  {
    id: 'au8', timestamp: isoTs(5 * 60), incidentId: 'INC0041818', client: 'RetailMax Group',
    actionType: 'Auto-Resolution', actor: 'ATLAS', outcome: 'Success', confidence: 95,
    details: { reasoningChain: 'P3 CDN cache purge storm detected. Trust level L1 Automation — auto-execute eligible. Rate limiting applied to cache purge operations (500 keys/second). Origin request rate recovered within 90 seconds.', vetoes: [], playbookSteps: ['CDN purge storm detected', 'Rate limit applied: 500 keys/s', 'Origin request monitoring', 'Recovery confirmed: 120/s origin requests'], metricValues: { 'origin_requests_per_s': 120, 'cache_hit_ratio': 94 } },
  },
  {
    id: 'au9', timestamp: isoTs(7 * 60), incidentId: 'INC0041810', client: 'Swiss Federal Railways',
    actionType: 'Resolution', actor: 'S. Weber', outcome: 'Success', confidence: 82,
    details: { reasoningChain: 'Kafka consumer group rebalance detected after node restart. Consumer group reset initiated. Rebalance completed in 43 seconds. Feed delay recovered to 0ms.', vetoes: [], playbookSteps: ['Consumer group rebalance detected', 'Reset consumer group offsets', 'Rebalance triggered: 43s', 'Feed delay: 0ms (recovered)'], metricValues: { 'consumer_lag': 0, 'feed_delay_ms': 0 } },
  },
  {
    id: 'au10', timestamp: isoTs(10 * 60), incidentId: 'INC0041805', client: 'National Health Trust',
    actionType: 'Resolution', actor: 'A. Petrov', outcome: 'Success', confidence: 90,
    details: { reasoningChain: 'LDAP connection pool saturation during shift change. Pool expanded from 200 to 500 connections. Connection timeout set to 5s. Auth latency recovered to 180ms within 2 minutes.', vetoes: [], playbookSteps: ['LDAP pool expansion: 200→500', 'Connection timeout: 5s', 'Auth latency monitoring', 'Recovery confirmed: 180ms'], metricValues: { 'auth_latency_ms': 180, 'ldap_pool_utilization': 34 } },
  },
  {
    id: 'au11', timestamp: isoTs(12 * 60), incidentId: 'INC0041798', client: 'UK Border Agency',
    actionType: 'Resolution', actor: 'J. Nakamura', outcome: 'Success', confidence: 93,
    details: { reasoningChain: 'OCR accuracy degradation caused by library colour space change. Library rolled back to v2.4.1. PassportVerification pods redeployed. OCR accuracy restored to 99.7%.', vetoes: [], playbookSteps: ['Library rollback: v2.4.2→v2.4.1', 'Pod restart: PassportVerification', 'OCR accuracy validation: 99.7%', 'Manual verification fallback disabled'], metricValues: { 'ocr_accuracy_pct': 99.7, 'manual_fallback_rate': 0 } },
  },
  {
    id: 'au12', timestamp: isoTs(15 * 60), incidentId: 'INC0041792', client: 'Bundesamt für Sicherheit',
    actionType: 'Auto-Resolution', actor: 'ATLAS', outcome: 'Success', confidence: 97,
    details: { reasoningChain: 'Log rotation failure detected. Cron job misconfiguration identified. Logs compressed and archived. Rotation policy restored. Disk usage reduced from 89% to 62%.', vetoes: [], playbookSteps: ['Cron job fix: 0 2 * * * /usr/bin/logrotate', 'Compress archived logs: 14GB→2.1GB', 'Restore rotation policy', 'Disk usage: 62% (recovered)'], metricValues: { 'disk_usage_pct': 62, 'log_size_gb': 2.1 } },
  },
  {
    id: 'au13', timestamp: isoTs(18 * 60), incidentId: 'INC0041788', client: 'Marseille Port Authority',
    actionType: 'Auto-Resolution', actor: 'ATLAS', outcome: 'Success', confidence: 96,
    details: { reasoningChain: 'Kafka consumer group rebalance after scheduled maintenance. Auto-recovery confirmed — no action required. Consumer lag: 0. Feed delay: 0ms.', vetoes: [], playbookSteps: ['Rebalance monitoring: 43s', 'Consumer lag: 0 (auto-recovered)', 'No intervention required'], metricValues: { 'consumer_lag': 0, 'rebalance_duration_s': 43 } },
  },
  {
    id: 'au14', timestamp: isoTs(20 * 60), incidentId: 'INC0041782', client: 'Rijkswaterstaat',
    actionType: 'Auto-Resolution', actor: 'ATLAS', outcome: 'Success', confidence: 94,
    details: { reasoningChain: 'LB idle timeout corrected from 60s to 120s. WebSocket connections stable. Reconnect rate: 0/hr.', vetoes: [], playbookSteps: ['LB idle timeout: 60s→120s', 'WebSocket stability monitoring', 'Reconnect rate: 0/hr (recovered)'], metricValues: { 'ws_reconnects_per_hr': 0, 'lb_timeout_s': 120 } },
  },
];

// ─── Playbooks ────────────────────────────────────────────────────────────────

export const mockPlaybooks: Playbook[] = [
  {
    id: 'connection-pool-recovery-v2',
    name: 'connection-pool-recovery-v2',
    technologyDomain: 'Java Spring Boot / HikariCP',
    actionClass: 'Class 1',
    estimatedTime: '4 minutes',
    lastUsed: isoTs(45),
    successRate: 97,
    description: 'Restores HikariCP connection pool configuration via Spring Actuator PATCH endpoint. Validates service recovery over a 5-minute monitoring window. Automatic rollback if success criteria not met within timeout.',
    preValidation: [
      'Verify Spring Actuator endpoint is reachable (/actuator/health returns 200)',
      'Confirm current maxPoolSize is below target value',
      'Check PostgreSQL max_connections allows the new pool size',
      'Validate no active database migrations are running',
    ],
    successCriteria: [
      'Connection pool utilization drops below 70% within 3 minutes',
      'TransactionProcessor p99 latency returns below 500ms',
      'FraudEngine scoring throughput recovers above 1,000/s',
      'No new connection timeout errors in 2-minute window',
    ],
    rollbackProcedure: 'Automatic rollback via playbook: connection-pool-recovery-v2-rollback. Restores previous maxPoolSize value from pre-execution snapshot.',
    executionHistory: [
      { date: isoTs(45), client: 'Deutsche Kredit Bank', outcome: 'Success' },
      { date: isoTs(3 * 60), client: 'FinanceCore Holdings', outcome: 'Success' },
      { date: isoTs(7 * 24 * 60), client: 'National Health Trust', outcome: 'Success' },
      { date: isoTs(14 * 24 * 60), client: 'FinanceCore Holdings', outcome: 'Success' },
      { date: isoTs(21 * 24 * 60), client: 'Deutsche Kredit Bank', outcome: 'Rolled Back' },
      { date: isoTs(28 * 24 * 60), client: 'FinanceCore Holdings', outcome: 'Success' },
    ],
  },
  {
    id: 'redis-memory-policy-rollback-v1',
    name: 'redis-memory-policy-rollback-v1',
    technologyDomain: 'Redis',
    actionClass: 'Class 1',
    estimatedTime: '6 minutes',
    lastUsed: isoTs(5 * 60),
    successRate: 94,
    description: 'Terminates offending processes consuming Redis memory, flushes the identified namespace, and pre-warms the product cache from the PostgreSQL replica. Monitors cache hit ratio recovery.',
    preValidation: [
      'Identify offending namespace via MEMORY USAGE sampling',
      'Confirm PostgreSQL replica is healthy and reachable',
      'Verify Redis cluster has sufficient memory for pre-warm operation',
      'Check no active transactions depend on the namespace being flushed',
    ],
    successCriteria: [
      'Redis memory utilization drops below 70% within 4 minutes',
      'Cache hit ratio recovers above 85% within 5 minutes',
      'ProductCatalog p95 latency returns below 300ms',
      'Eviction rate drops below 200 keys/min',
    ],
    rollbackProcedure: 'Automatic rollback via playbook: redis-memory-policy-rollback-v1-rollback. Restores previous eviction policy and memory limits.',
    executionHistory: [
      { date: isoTs(5 * 60), client: 'RetailMax Group', outcome: 'Success' },
      { date: isoTs(10 * 24 * 60), client: 'RetailMax Group', outcome: 'Success' },
      { date: isoTs(18 * 24 * 60), client: 'RetailMax Group', outcome: 'Failed' },
      { date: isoTs(25 * 24 * 60), client: 'RetailMax Group', outcome: 'Success' },
    ],
  },
  {
    id: 'tls-cert-renewal-v3',
    name: 'tls-cert-renewal-v3',
    technologyDomain: 'Nginx / TLS',
    actionClass: 'Class 1',
    estimatedTime: '2 minutes',
    lastUsed: isoTs(50),
    successRate: 99,
    description: 'Automated TLS certificate renewal via ACME protocol (Let\'s Encrypt or internal CA). Performs DNS-01 or HTTP-01 challenge, issues new certificate, and reloads Nginx with zero downtime.',
    preValidation: [
      'Verify ACME client (certbot) is installed and configured',
      'Confirm DNS propagation for DNS-01 challenge (if applicable)',
      'Check certificate authority is reachable',
      'Validate Nginx configuration syntax before reload',
    ],
    successCriteria: [
      'New certificate issued with validity > 60 days',
      'Nginx reload completes without downtime',
      'TLS handshake succeeds on all configured domains',
      'Certificate expiry monitoring updated',
    ],
    rollbackProcedure: 'Manual rollback: restore previous certificate from /etc/letsencrypt/archive/. Nginx reload required.',
    executionHistory: [
      { date: isoTs(50), client: 'Eurostar Rail Operations', outcome: 'Success' },
      { date: isoTs(90 * 24 * 60), client: 'Eurostar Rail Operations', outcome: 'Success' },
      { date: isoTs(180 * 24 * 60), client: 'Swiss Federal Railways', outcome: 'Success' },
    ],
  },
  {
    id: 'kafka-consumer-reset-v1',
    name: 'kafka-consumer-reset-v1',
    technologyDomain: 'Apache Kafka',
    actionClass: 'Class 1',
    estimatedTime: '3 minutes',
    lastUsed: isoTs(7 * 60),
    successRate: 91,
    description: 'Resets Kafka consumer group offsets to the last committed position and triggers a controlled rebalance. Monitors consumer lag recovery and partition assignment.',
    preValidation: [
      'Verify Kafka broker connectivity and cluster health',
      'Confirm consumer group is in a stable state (not mid-rebalance)',
      'Check last committed offset is valid and not expired',
      'Validate consumer application is healthy and ready to consume',
    ],
    successCriteria: [
      'Consumer lag returns to 0 within 2 minutes',
      'All partitions assigned to healthy consumers',
      'No consumer group rebalance errors in 1-minute window',
      'Message processing rate returns to baseline',
    ],
    rollbackProcedure: 'Manual rollback: reset consumer group to earliest offset and replay messages. Requires L3 approval for production.',
    executionHistory: [
      { date: isoTs(7 * 60), client: 'Swiss Federal Railways', outcome: 'Success' },
      { date: isoTs(18 * 60), client: 'Marseille Port Authority', outcome: 'Success' },
      { date: isoTs(5 * 24 * 60), client: 'Rijkswaterstaat', outcome: 'Success' },
    ],
  },
  {
    id: 'k8s-pod-reschedule-v2',
    name: 'k8s-pod-reschedule-v2',
    technologyDomain: 'Kubernetes',
    actionClass: 'Class 2',
    estimatedTime: '5 minutes',
    lastUsed: isoTs(12 * 60),
    successRate: 88,
    description: 'Gracefully terminates and reschedules Kubernetes pods on healthy nodes. Respects PodDisruptionBudgets and rolling update policies. Validates pod health before marking complete.',
    preValidation: [
      'Verify cluster has sufficient capacity on healthy nodes',
      'Check PodDisruptionBudget allows the operation',
      'Confirm no active deployments or rollouts in progress',
      'Validate pod health checks are configured correctly',
    ],
    successCriteria: [
      'All pods rescheduled and in Running state within 4 minutes',
      'No PodDisruptionBudget violations',
      'Service endpoints updated and traffic routing correctly',
      'Application health checks passing on new pods',
    ],
    rollbackProcedure: 'Automatic rollback: restore previous pod spec from deployment history. kubectl rollout undo deployment/<name>.',
    executionHistory: [
      { date: isoTs(12 * 60), client: 'UK Border Agency', outcome: 'Success' },
      { date: isoTs(15 * 60), client: 'Bundesamt für Sicherheit', outcome: 'Success' },
      { date: isoTs(20 * 60), client: 'Rijkswaterstaat', outcome: 'Success' },
      { date: isoTs(3 * 24 * 60), client: 'National Health Trust', outcome: 'Rolled Back' },
    ],
  },
  {
    id: 'ml-pipeline-priority-v1',
    name: 'ml-pipeline-priority-v1',
    technologyDomain: 'Python / TensorFlow',
    actionClass: 'Class 2',
    estimatedTime: '3 minutes',
    lastUsed: isoTs(45),
    successRate: 92,
    description: 'Deprioritizes background ML training jobs to restore inference pipeline performance. Adjusts process nice values, GPU memory allocation, and CUDA compute priority.',
    preValidation: [
      'Identify offending training job PID and GPU memory usage',
      'Confirm inference pipeline is healthy and accepting requests',
      'Verify GPU memory can be safely reclaimed without data loss',
      'Check no model checkpoints are being written',
    ],
    successCriteria: [
      'Inference latency returns below 50ms within 2 minutes',
      'GPU memory utilization drops below 60%',
      'Training job continues at reduced priority (nice +19)',
      'No inference errors in 1-minute window',
    ],
    rollbackProcedure: 'Manual rollback: restore training job priority and GPU allocation. Requires L3 approval.',
    executionHistory: [
      { date: isoTs(45), client: 'Deutsche Kredit Bank', outcome: 'Success' },
      { date: isoTs(7 * 24 * 60), client: 'Deutsche Kredit Bank', outcome: 'Success' },
    ],
  },
];

// ─── Company-specific playbooks ───────────────────────────────────────────────

export const companyPlaybooks: Record<string, Playbook[]> = {
  'client-financecore': [
    {
      ...mockPlaybooks[0],
      id: 'fc-connection-pool-recovery-v2',
      name: 'fc-connection-pool-recovery-v2',
      description: 'FinanceCore-specific variant: includes PCI-DSS dual-approval workflow and SOX audit trail generation. Targets PaymentGateway HikariCP pool with compliance-grade logging.',
      executionHistory: [
        { date: isoTs(3 * 60), client: 'FinanceCore Holdings', outcome: 'Success' },
        { date: isoTs(14 * 24 * 60), client: 'FinanceCore Holdings', outcome: 'Success' },
        { date: isoTs(28 * 24 * 60), client: 'FinanceCore Holdings', outcome: 'Success' },
      ],
    },
  ],
  'client-retailmax': [
    {
      ...mockPlaybooks[1],
      id: 'rm-redis-memory-policy-rollback-v1',
      name: 'rm-redis-memory-policy-rollback-v1',
      description: 'RetailMax-specific variant: includes ProductCatalog cache pre-warm from PostgreSQL replica for top 10,000 SKUs by access frequency. Monitors SearchService stale result rate.',
      executionHistory: [
        { date: isoTs(5 * 60), client: 'RetailMax Group', outcome: 'Success' },
        { date: isoTs(10 * 24 * 60), client: 'RetailMax Group', outcome: 'Success' },
      ],
    },
  ],
};
