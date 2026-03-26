import { useState, useCallback, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { PriorityBadge } from '@/components/atlas/PriorityBadge';
import { CountdownTimer } from '@/components/atlas/CountdownTimer';
import { StatusIndicator } from '@/components/atlas/StatusIndicator';
import { ExecutionTrace } from '@/components/atlas/ExecutionTrace';
import { PipelineIndicator } from '@/components/atlas/PipelineIndicator';
import { ConfirmationDialog } from '@/components/atlas/ConfirmationDialog';
import { AIReasoningPanel } from '@/components/atlas/AIReasoningPanel';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { ChevronDown, ChevronRight, AlertTriangle, CheckCircle2, Clock, ExternalLink, Shield, Brain, FileCode2, GitCommitHorizontal, Wrench, ArrowRight, Terminal, Bug, Code2, Database, Cpu, Activity, TrendingDown, Zap, ShieldCheck, Users } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Incident } from '@/types/atlas';
import type { PipelineStage } from '@/components/atlas/PipelineIndicator';
import { mockClients } from '@/data/mock';

interface Props {
  incident: Incident;
}

function getEngineeringContext(incident: Incident) {
  if (incident.clientName === 'FinanceCore Holdings') {
    return {
      title: 'Configuration regression in connection pool sizing',
      issue: 'Recent change reduced PaymentGateway HikariCP maxPoolSize below required production concurrency.',
      severity: 'Config regression',
      files: [
        '/services/payment-gateway/src/main/resources/application-prod.yml',
        '/services/payment-gateway/src/main/java/com/atos/payment/HikariConfig.java',
        '/deploy/helm/payment-gateway/values-prod.yaml',
      ],
      signature: [
        'com.zaxxer.hikari.pool.HikariPool$PoolEntryCreator - Connection is not available, request timed out after 30001ms.',
        'PaymentGateway WARN pool.active=47 pool.max=50 wait.ms.p95=1820',
        'TransactionProcessor WARN downstream=PaymentGateway p99=4.2s error_rate=23%',
      ],
      diff: {
        before: 'maximumPoolSize: 100\nminimumIdle: 30\nconnectionTimeoutMs: 30000',
        after: 'maximumPoolSize: 50\nminimumIdle: 10\nconnectionTimeoutMs: 30000',
      },
      stackTrace: `java.sql.SQLTransientConnectionException: HikariPool-1 - Connection is not available, request timed out after 30001ms.
    at com.zaxxer.hikari.pool.HikariPool.createTimeoutException(HikariPool.java:695)
    at com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:197)
    at com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:162)
    at com.atos.payment.service.PaymentProcessor.processTransaction(PaymentProcessor.java:89)
    at com.atos.payment.controller.PaymentController.submitPayment(PaymentController.java:42)`,
      remediation: 'Revert pool size to a safe production value, redeploy the config package, and open a permanent problem record for capacity guardrails.',
      metrics: {
        activeConnections: 47,
        maxConnections: 50,
        waitingThreads: 23,
        avgAcquireMs: 1820,
        p99LatencyMs: 4200,
        errorRate: 23,
      },
    };
  }

  return {
    title: 'Shared Redis cluster contaminated by analytics workload',
    issue: 'Analytics pipeline introduced memory-heavy keys into the same Redis cluster used by ProductCatalog caching.',
    severity: 'Runtime + config issue',
    files: [
      '/services/analytics-pipeline/config/redis.targets.yml',
      '/services/product-catalog/src/cache/redisClient.ts',
      '/deploy/helm/shared-redis/values-prod.yaml',
    ],
    signature: [
      'redis-server WARNING maxmemory reached, evicting keys using allkeys-lru',
      'ProductCatalog WARN cache_hit_ratio=41% p95=2.8s namespace=product:*',
      'analytics-pipeline INFO namespace=analytics:* footprint=6.2GB ttl=86400',
    ],
    diff: {
      before: 'cacheTarget: redis-product-catalog\nkeyNamespace: analytics_temp\nmaxDatasetMb: 512',
      after: 'cacheTarget: redis-product-catalog\nkeyNamespace: analytics\nmaxDatasetMb: 6200',
    },
    stackTrace: `Error: Redis OOM command not allowed when used memory > 'maxmemory'.
    at RedisClient.handleError (/services/product-catalog/src/cache/redisClient.ts:44:11)
    at CacheManager.get (/services/product-catalog/src/cache/cacheManager.ts:28:9)
    at ProductService.getProduct (/services/product-catalog/src/services/productService.ts:67:22)
    at Router.handle (/services/product-catalog/node_modules/express/lib/router/index.js:174:12)`,
    remediation: 'Move analytics writes to a separate Redis target, flush analytics:* keys from the shared cluster, and enforce namespace isolation in deployment validation.',
    metrics: {
      activeConnections: 0,
      maxConnections: 0,
      waitingThreads: 0,
      avgAcquireMs: 0,
      p99LatencyMs: 2800,
      errorRate: 12,
    },
  };
}

export function IncidentBriefing({ incident }: Props) {
  const { user } = useAuth();
  const role = user?.role || 'L2';
  const [showAlternatives, setShowAlternatives] = useState(false);
  const [showConfidence, setShowConfidence] = useState(false);
  const [showEscalate, setShowEscalate] = useState(false);
  const [showModify, setShowModify] = useState(false);
  const [showReject, setShowReject] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [showRawEvidence, setShowRawEvidence] = useState(false);
  const [showConfigDiff, setShowConfigDiff] = useState(false);
  const [escalateReason, setEscalateReason] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [modifyValue, setModifyValue] = useState('200');
  const [modifyReason, setModifyReason] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [isResolved, setIsResolved] = useState(false);
  const [pipelineStage, setPipelineStage] = useState<PipelineStage>('ingest');
  const [isEscalated, setIsEscalated] = useState(false);
  const [isRejected, setIsRejected] = useState(false);

  const isL1 = role === 'L1';
  const isL2 = role === 'L2';
  const isL3 = role === 'L3';
  const isSDM = role === 'SDM';

  const client = mockClients.find(c => c.id === incident.clientId);
  const needsDualApproval = client?.complianceFlags && client.complianceFlags.length > 0;
  const engineeringContext = getEngineeringContext(incident);

  useEffect(() => {
    if (isExecuting || isResolved || isEscalated || isRejected) return;
    const stages: PipelineStage[] = ['ingest', 'detect', 'correlate', 'search', 'reason', 'select', 'route'];
    setPipelineStage('ingest');
    const timers = stages.map((stage, index) =>
      window.setTimeout(() => setPipelineStage(stage), index * 450)
    );
    return () => timers.forEach(window.clearTimeout);
  }, [incident.id, role, isExecuting, isResolved, isEscalated, isRejected]);

  const handleApproveClick = () => setShowConfirmation(true);
  const handleConfirmApprove = useCallback(() => {
    setShowConfirmation(false);
    setIsExecuting(true);
    setPipelineStage('act');
  }, []);
  const handleExecutionComplete = useCallback(() => {
    setPipelineStage('learn');
    setTimeout(() => setIsResolved(true), 800);
  }, []);
  const handleEscalate = () => { setIsEscalated(true); setShowEscalate(false); };
  const handleReject = () => { setIsRejected(true); setShowReject(false); };

  const confidenceLabel = incident.rootCause.confidence >= 85 ? 'High' : incident.rootCause.confidence >= 70 ? 'Medium' : 'Low';

  // ─── RESOLVED STATE ───
  if (isResolved) {
    return (
      <div className="space-y-4 max-w-5xl">
        <PipelineIndicator currentStage="learn" />
        <div className="bg-card border border-border rounded-lg p-5 shadow-atlas border-l-4 border-l-status-healthy">
          <div className="flex items-center gap-3 mb-4">
            <CheckCircle2 className="h-5 w-5 text-status-healthy" />
            <span className="text-[15px] font-semibold text-foreground">Incident Resolved</span>
            <span className="font-mono text-[11px] text-muted-foreground">{incident.id}</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div><p className="text-[10px] text-muted-foreground uppercase tracking-wider">Client</p><p className="text-[13px] font-medium text-foreground mt-0.5">{incident.clientName}</p></div>
            <div><p className="text-[10px] text-muted-foreground uppercase tracking-wider">MTTR</p><p className="text-[13px] font-semibold text-status-healthy mt-0.5">4m 12s</p></div>
            <div><p className="text-[10px] text-muted-foreground uppercase tracking-wider">Playbook</p><p className="font-mono text-[11px] text-foreground mt-0.5">{incident.recommendedAction.playbookName}</p></div>
            <div><p className="text-[10px] text-muted-foreground uppercase tracking-wider">Approved by</p><p className="text-[13px] text-foreground mt-0.5">{user?.name}</p></div>
          </div>
        </div>
        <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[12px] text-muted-foreground">Industry average MTTR: <span className="font-semibold text-foreground">43 minutes</span></p>
              <p className="text-[12px] text-muted-foreground mt-0.5">ATLAS resolution: <span className="font-semibold text-status-healthy">4 minutes 12 seconds</span></p>
            </div>
            <div className="text-right">
              <p className="text-[24px] font-bold text-status-healthy leading-none">10.2×</p>
              <p className="text-[10px] text-muted-foreground mt-0.5">faster than industry avg</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ─── ESCALATED STATE ───
  if (isEscalated) {
    const nextLevel = isL1 ? 'L2' : 'L3';
    return (
      <div className="space-y-4 max-w-4xl">
        <PipelineIndicator currentStage="route" />
        <div className="bg-card border border-border rounded-lg p-5 shadow-atlas border-l-4 border-l-status-warning">
          <div className="flex items-center gap-3 mb-3">
            <AlertTriangle className="h-5 w-5 text-status-warning" />
            <span className="text-[15px] font-semibold text-foreground">Escalated to {nextLevel}</span>
          </div>
          <p className="text-[13px] text-muted-foreground mb-2">{incident.id} — {incident.clientName}. Awaiting {nextLevel} response.</p>
          <div className="bg-muted/30 rounded p-3 mt-2">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Escalation reason</p>
            <p className="text-[12px] text-foreground">"{escalateReason}"</p>
          </div>
        </div>
      </div>
    );
  }

  // ─── REJECTED STATE (L3) ───
  if (isRejected) {
    return (
      <div className="space-y-4 max-w-5xl">
        <PipelineIndicator currentStage="route" />
        <div className="bg-card border border-border rounded-lg p-5 shadow-atlas border-l-4 border-l-status-critical">
          <div className="flex items-center gap-3 mb-3">
            <Shield className="h-5 w-5 text-status-critical" />
            <span className="text-[15px] font-semibold text-foreground">L3 Manual Resolution</span>
            <span className="font-mono text-[11px] text-muted-foreground">{incident.id}</span>
          </div>
          <p className="text-[13px] text-muted-foreground">AI recommendation rejected. L3 engineering diagnosis has taken ownership.</p>
          <div className="bg-muted/30 rounded p-3 mt-3">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">L3 diagnosis</p>
            <p className="text-[12px] text-foreground leading-relaxed">{rejectReason}</p>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <Button className="bg-status-healthy hover:bg-status-healthy/90 text-white text-[12px] h-8" onClick={() => setIsResolved(true)}>Mark Resolved</Button>
            <span className="text-[10px] text-muted-foreground">Stored as 3× weight training data.</span>
          </div>
        </div>
      </div>
    );
  }

  // ════════════════════════════════════════════════
  //  L1 — TRIAGE CONSOLE (Compact, Decision-focused)
  // ════════════════════════════════════════════════
  if (isL1) {
    return (
      <div className="space-y-4 max-w-3xl">
        <PipelineIndicator currentStage={pipelineStage} compact />

        {/* Header strip */}
        <div className="bg-card border border-border rounded-lg shadow-atlas overflow-hidden">
          <div className="px-4 py-3 bg-accent/[0.04] border-b border-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-accent" />
              <span className="text-[11px] font-semibold text-accent uppercase tracking-wider">L1 Triage Console</span>
            </div>
            <div className="flex items-center gap-2">
              <PriorityBadge priority={incident.priority} />
              <CountdownTimer deadline={incident.slaDeadline} className="text-[13px] font-mono" />
            </div>
          </div>
          <div className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-[11px] text-muted-foreground">{incident.id}</span>
              <span className="text-[10px] text-muted-foreground">·</span>
              <span className="text-[13px] font-semibold text-foreground">{incident.clientName}</span>
              {needsDualApproval && <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-status-warning/10 text-status-warning">{client?.complianceFlags?.join(' · ')}</span>}
            </div>
            <p className="text-[13px] text-foreground leading-relaxed">{incident.summary}</p>
          </div>
        </div>

        {/* Quick decision signals — 3 cards */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-card border border-border rounded-lg p-3 shadow-atlas text-center">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">AI Confidence</p>
            <p className={cn('text-[22px] font-bold leading-none', confidenceLabel === 'High' ? 'text-status-healthy' : confidenceLabel === 'Medium' ? 'text-status-warning' : 'text-status-critical')}>
              {confidenceLabel}
            </p>
            <p className="text-[10px] text-muted-foreground mt-1">for first-line approval</p>
          </div>
          <div className="bg-card border border-border rounded-lg p-3 shadow-atlas text-center">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Risk Level</p>
            <p className="text-[22px] font-bold text-foreground leading-none">{incident.recommendedAction.riskClass}</p>
            <p className="text-[10px] text-muted-foreground mt-1">{incident.recommendedAction.rollbackAvailable ? 'Rollback available' : 'Manual rollback'}</p>
          </div>
          <div className="bg-card border border-border rounded-lg p-3 shadow-atlas text-center">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Est. Resolution</p>
            <p className="text-[22px] font-bold text-foreground leading-none">{incident.recommendedAction.estimatedTime.replace(' minutes', 'm')}</p>
            <p className="text-[10px] text-muted-foreground mt-1">automated playbook</p>
          </div>
        </div>

        {/* Operator checklist */}
        <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
          <h3 className="text-[11px] font-semibold text-foreground mb-3 uppercase tracking-wider flex items-center gap-2">
            <Activity className="h-3.5 w-3.5 text-accent" /> Pre-approval checklist
          </h3>
          <div className="space-y-2">
            {[
              { label: 'Primary service impact', value: `${incident.affectedServices[0]} — ${incident.services[0]?.triggerValue || 'degraded'}`, ok: true },
              { label: 'Deployment correlation', value: incident.deploymentCorrelation ? `${incident.deploymentCorrelation.changeId} (${incident.deploymentCorrelation.daysAgo}d ago)` : 'No recent change detected', ok: !!incident.deploymentCorrelation },
              { label: 'Historical precedent', value: incident.historicalMatch ? `${incident.historicalMatch.similarity}% match — resolved before` : 'Novel pattern', ok: !!incident.historicalMatch },
              { label: 'Business impact', value: incident.businessImpact, ok: false },
            ].map((item, i) => (
              <div key={i} className="flex items-start gap-3 rounded-lg border border-border p-3">
                <div className={cn('h-5 w-5 rounded-full flex items-center justify-center shrink-0 text-[10px] font-bold', item.ok ? 'bg-status-healthy/10 text-status-healthy' : 'bg-muted text-muted-foreground')}>
                  {i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">{item.label}</p>
                  <p className="text-[12px] text-foreground mt-0.5 leading-relaxed">{item.value}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Service health - compact */}
        <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
          <h3 className="text-[11px] font-semibold text-foreground mb-2 uppercase tracking-wider">Affected services</h3>
          <div className="flex flex-wrap gap-2">
            {incident.services.slice(0, 4).map(s => (
              <div key={s.id} className="flex items-center gap-2 border border-border rounded-md px-3 py-2">
                <StatusIndicator status={s.health} />
                <span className="text-[12px] font-medium text-foreground">{s.name}</span>
                <span className="text-[10px] text-muted-foreground">{s.technology}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Action area */}
        {isExecuting ? (
          <ExecutionTrace playbookName={incident.recommendedAction.playbookName} onComplete={handleExecutionComplete} />
        ) : (
          <div className="bg-card border border-border rounded-lg p-5 shadow-atlas border-l-4 border-l-accent">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-[14px] font-semibold text-foreground">Recommended action</h3>
                <p className="font-mono text-[11px] text-accent mt-0.5">{incident.recommendedAction.playbookName}</p>
              </div>
            </div>
            <p className="text-[12px] text-foreground leading-relaxed mb-4">{incident.recommendedAction.description}</p>

            <div className="flex items-center gap-3">
              <Button onClick={handleApproveClick} className="bg-accent hover:bg-accent/90 text-accent-foreground px-8 h-11 text-[14px] font-semibold shadow-sm">
                {needsDualApproval ? 'Submit for Dual Approval' : 'Approve'}
              </Button>
              <Button variant="ghost" className="text-muted-foreground text-[12px] h-9" onClick={() => setShowEscalate(!showEscalate)}>
                Escalate to L2
              </Button>
            </div>

            {showEscalate && (
              <div className="mt-4 pt-3 border-t border-border space-y-2.5">
                <p className="text-[11px] font-medium text-foreground">Why does this need deeper investigation?</p>
                <Textarea placeholder="Brief reason for escalation..." value={escalateReason} onChange={(e) => setEscalateReason(e.target.value)} className="h-16 text-[12px]" />
                <Button className="bg-accent hover:bg-accent/90 text-accent-foreground text-[12px] h-8" disabled={!escalateReason.trim()} onClick={handleEscalate}>Confirm escalation</Button>
              </div>
            )}
          </div>
        )}

        <ConfirmationDialog open={showConfirmation} onConfirm={handleConfirmApprove} onCancel={() => setShowConfirmation(false)} playbookName={incident.recommendedAction.playbookName} description={incident.recommendedAction.description} affectedService={incident.affectedServices[0]} />
      </div>
    );
  }

  // ════════════════════════════════════════════════
  //  L2 — ANALYSIS WORKSPACE (Full 8-section briefing)
  // ════════════════════════════════════════════════
  const l2AnalysisView = (
    <div className="space-y-4">
      <PipelineIndicator currentStage={pipelineStage} />

      {/* Section 1: Situation Header */}
      <div className="bg-card border border-border rounded-lg p-5 shadow-atlas">
        <div className="flex items-center justify-between mb-3 gap-4">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="px-2 py-1 rounded bg-accent/10 text-accent text-[10px] font-semibold uppercase tracking-wider">L2 Analysis Workspace</span>
            <span className="font-mono text-[11px] text-muted-foreground">{incident.id}</span>
            <span className="text-[13px] font-medium text-foreground">{incident.clientName}</span>
            <PriorityBadge priority={incident.priority} />
            {needsDualApproval && <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-status-warning/10 text-status-warning uppercase">{client?.complianceFlags?.join(' · ')}</span>}
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            <Clock className="h-3 w-3 text-muted-foreground" />
            <span className="text-[10px] text-muted-foreground mr-1">SLA</span>
            <CountdownTimer deadline={incident.slaDeadline} className="text-[12px]" />
          </div>
        </div>
        <p className="text-[13px] text-foreground leading-relaxed">{incident.summary}</p>
        <div className="mt-3 pt-3 border-t border-border">
          <p className="text-[12px]"><span className="font-medium text-foreground">Business impact: </span><span className="text-muted-foreground">{incident.businessImpact}</span></p>
        </div>
      </div>

      {/* Section 2: AI Reasoning (expandable) */}
      <AIReasoningPanel incident={incident} showFullDetail />

      {/* Section 3: Service Health Snapshot */}
      <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
        <h3 className="text-[12px] font-semibold text-foreground mb-3 uppercase tracking-wider">Service health snapshot</h3>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
          {incident.services.map(service => (
            <div key={service.id} className={cn('border rounded-md p-3', service.health === 'critical' ? 'border-status-critical/30 bg-destructive/[0.02]' : service.health === 'warning' ? 'border-status-warning/25 bg-status-warning/[0.02]' : 'border-border')}>
              <div className="flex items-center gap-1.5 mb-1"><StatusIndicator status={service.health} /><span className="text-[12px] font-medium text-foreground">{service.name}</span></div>
              <p className="text-[10px] text-muted-foreground">{service.technology}</p>
              {service.triggerMetric && <p className="text-[10px] text-foreground mt-1.5 font-mono leading-tight">{service.triggerMetric}: {service.triggerValue}</p>}
              {service.lastDeployment && <p className="text-[9px] text-muted-foreground mt-1">Deploy: {service.lastDeployment}</p>}
            </div>
          ))}
        </div>
      </div>

      {/* Section 4: What Changed */}
      {incident.deploymentCorrelation && (
        <div className="bg-card border border-border rounded-lg p-4 shadow-atlas border-l-[3px] border-l-status-warning">
          <h3 className="text-[12px] font-semibold text-foreground mb-1.5 uppercase tracking-wider">What changed</h3>
          <p className="text-[13px] text-foreground">A deployment was made {incident.deploymentCorrelation.daysAgo} day{incident.deploymentCorrelation.daysAgo !== 1 ? 's' : ''} ago that modified this service.</p>
          <div className="mt-2.5 flex items-start gap-3 text-[12px]"><span className="font-mono text-accent font-medium shrink-0">{incident.deploymentCorrelation.changeId}</span><span className="text-muted-foreground">{incident.deploymentCorrelation.description}</span></div>
          <p className="text-[10px] text-muted-foreground mt-2">By {incident.deploymentCorrelation.deployedBy} · CAB risk: {incident.deploymentCorrelation.cabRiskRating}</p>
        </div>
      )}

      {/* Section 5: Dependency Graph */}
      <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
        <h3 className="text-[12px] font-semibold text-foreground mb-3 uppercase tracking-wider">Dependency graph</h3>
        <div className="h-[220px] border border-border rounded bg-muted/5 relative overflow-hidden">
          <svg className="w-full h-full" viewBox="0 0 800 200">
            <line x1="130" y1="100" x2="280" y2="65" stroke="hsl(211 100% 40%)" strokeWidth="2" opacity="0.6" />
            <line x1="130" y1="100" x2="280" y2="135" stroke="hsl(var(--border))" strokeWidth="1.5" strokeDasharray="4 3" />
            <line x1="340" y1="65" x2="480" y2="50" stroke="hsl(211 100% 40%)" strokeWidth="2" opacity="0.6" />
            <line x1="340" y1="65" x2="480" y2="100" stroke="hsl(211 100% 40%)" strokeWidth="2" opacity="0.6" />
            <line x1="340" y1="65" x2="480" y2="155" stroke="hsl(var(--border))" strokeWidth="1.5" strokeDasharray="4 3" />
            <g transform="translate(110,100)"><rect x="-16" y="-16" width="32" height="32" rx="2" transform="rotate(45)" fill="hsl(var(--status-warning) / 0.08)" stroke="hsl(var(--status-warning))" strokeWidth="1.5" /><text y="34" textAnchor="middle" fill="hsl(var(--muted-foreground))" fontSize="8" fontFamily="IBM Plex Mono">{incident.deploymentCorrelation?.changeId || 'CHG'}</text></g>
            {incident.services.map((s, i) => {
              const positions = [{ x: 310, y: 65 }, { x: 500, y: 50 }, { x: 500, y: 100 }, { x: 500, y: 155 }, { x: 310, y: 135 }];
              const pos = positions[i] || { x: 310 + (i % 3) * 100, y: 65 + Math.floor(i / 3) * 60 };
              const color = s.health === 'critical' ? 'hsl(var(--status-critical))' : s.health === 'warning' ? 'hsl(var(--status-warning))' : 'hsl(var(--status-healthy))';
              return (
                <g key={s.id} transform={`translate(${pos.x},${pos.y})`}>
                  <circle r="18" fill="white" stroke={color} strokeWidth="2" />
                  <circle r="4" fill={color} />
                  <text y="28" textAnchor="middle" fill="hsl(var(--foreground))" fontSize="8" fontFamily="IBM Plex Sans" fontWeight="500">{s.name}</text>
                </g>
              );
            })}
          </svg>
        </div>
        <p className="text-[9px] text-muted-foreground mt-2">Causal path highlighted in blue. Deployment change shown as diamond node.</p>
      </div>

      {/* Section 6: Historical Match */}
      <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
        <h3 className="text-[12px] font-semibold text-foreground mb-2 uppercase tracking-wider">Historical match</h3>
        {incident.historicalMatch ? (
          <>
            <div className="flex items-center gap-3 mb-2 flex-wrap">
              <span className="font-mono text-[11px] text-muted-foreground">{incident.historicalMatch.incidentId}</span>
              <span className="text-[11px] text-muted-foreground">{incident.historicalMatch.occurredAt}</span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-accent/8 text-accent">{incident.historicalMatch.similarity}% match</span>
            </div>
            <p className="text-[12px] text-foreground"><span className="font-medium">Root cause:</span> {incident.historicalMatch.rootCause}</p>
            <p className="text-[12px] text-foreground mt-1"><span className="font-medium">Resolution:</span> {incident.historicalMatch.resolution}</p>
            <button className="flex items-center gap-1 text-[11px] text-accent hover:underline mt-2"><ExternalLink className="h-3 w-3" /> View full record</button>
          </>
        ) : (
          <p className="text-[12px] text-muted-foreground">No strong historical precedent found — pattern flagged as novel.</p>
        )}
      </div>

      {/* Section 7: Root Cause Assessment */}
      <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
        <h3 className="text-[12px] font-semibold text-foreground mb-2 uppercase tracking-wider">Root cause assessment</h3>
        <p className="text-[12px] text-foreground mb-3 leading-relaxed">{incident.rootCause.diagnosis}</p>
        <div className="flex items-center gap-3 mb-1.5">
          <span className="text-[11px] text-muted-foreground shrink-0 w-20">Confidence</span>
          <div className="flex-1 max-w-[220px] h-1.5 bg-muted rounded-full overflow-hidden"><div className="h-full bg-accent rounded-full transition-all" style={{ width: `${incident.rootCause.confidence}%` }} /></div>
          <span className="text-[12px] font-mono font-semibold text-foreground tabular-nums">{incident.rootCause.confidence}%</span>
        </div>
        <button onClick={() => setShowConfidence(!showConfidence)} className="flex items-center gap-1 text-[11px] text-accent hover:underline mt-2">
          {showConfidence ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />} Why this confidence?
        </button>
        {showConfidence && (
          <div className="mt-3 space-y-1.5 pl-3 border-l-2 border-border">
            {Object.entries(incident.rootCause.factors).map(([key, value]) => (
              <div key={key} className="flex items-center gap-2">
                <span className="text-[10px] text-muted-foreground w-36 shrink-0">{key.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase())}</span>
                <div className="flex-1 max-w-[140px] h-1 bg-muted rounded-full overflow-hidden"><div className="h-full bg-accent/60 rounded-full" style={{ width: `${value}%` }} /></div>
                <span className="text-[10px] font-mono text-foreground tabular-nums">{value}%</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Section 8: Alternative Hypotheses */}
      {incident.alternativeHypotheses.length > 0 && (
        <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
          <button onClick={() => setShowAlternatives(!showAlternatives)} className="flex items-center gap-2 text-[12px] font-semibold text-foreground w-full text-left">
            {showAlternatives ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />} {incident.alternativeHypotheses.length} alternative hypotheses considered
          </button>
          {showAlternatives && (
            <div className="mt-3 space-y-3">
              {incident.alternativeHypotheses.map((alt, i) => (
                <div key={i} className="border border-border rounded-md p-3">
                  <p className="text-[12px] font-medium text-foreground mb-2">{alt.hypothesis}</p>
                  <div className="grid grid-cols-2 gap-3">
                    <div><p className="text-[10px] font-semibold text-status-healthy mb-1">Evidence for</p>{alt.evidenceFor.map((e, j) => <p key={j} className="text-[11px] text-muted-foreground">• {e}</p>)}</div>
                    <div><p className="text-[10px] font-semibold text-status-critical mb-1">Evidence against</p>{alt.evidenceAgainst.map((e, j) => <p key={j} className="text-[11px] text-muted-foreground">• {e}</p>)}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Recommended Action + Buttons */}
      {isExecuting ? (
        <ExecutionTrace playbookName={incident.recommendedAction.playbookName} onComplete={handleExecutionComplete} />
      ) : (
        <div className="bg-card border border-border rounded-lg p-5 shadow-atlas border-l-4 border-l-accent">
          <h3 className="text-[14px] font-semibold text-foreground mb-1">Recommended action</h3>
          <p className="font-mono text-[11px] text-accent mb-2">{incident.recommendedAction.playbookName}</p>
          <p className="text-[12px] text-foreground leading-relaxed mb-3">{incident.recommendedAction.description}</p>
          <div className="flex items-center gap-4 text-[11px] text-muted-foreground mb-4">
            <span>Est. {incident.recommendedAction.estimatedTime}</span>
            <span>Risk: <span className="font-medium text-foreground">{incident.recommendedAction.riskClass}</span></span>
            {incident.recommendedAction.rollbackAvailable && <span className="text-status-healthy font-medium">✓ Rollback available</span>}
          </div>
          {!isSDM && (
            <div className="flex items-center gap-2.5 flex-wrap">
              <Button onClick={handleApproveClick} className="bg-accent hover:bg-accent/90 text-accent-foreground px-8 h-11 text-[14px] font-semibold shadow-sm">{needsDualApproval ? 'Submit for Dual Approval' : 'Approve'}</Button>
              <Button variant="outline" className="h-9 text-[12px]" onClick={() => { setShowModify(!showModify); setShowEscalate(false); setShowReject(false); }}>Modify</Button>
              {isL2 && <Button variant="ghost" className="text-muted-foreground text-[12px]" onClick={() => { setShowEscalate(!showEscalate); setShowModify(false); }}>Escalate to L3</Button>}
              {isL3 && <Button variant="ghost" className="text-status-critical text-[12px]" onClick={() => { setShowReject(!showReject); setShowModify(false); }}>Reject</Button>}
            </div>
          )}
          {showEscalate && (
            <div className="mt-4 pt-3 border-t border-border space-y-2.5">
              <p className="text-[11px] font-medium text-foreground">Escalation to L3</p>
              <Textarea placeholder="Reason for escalation..." value={escalateReason} onChange={e => setEscalateReason(e.target.value)} className="h-16 text-[12px]" />
              <Button className="bg-accent hover:bg-accent/90 text-accent-foreground text-[12px] h-8" disabled={!escalateReason.trim()} onClick={handleEscalate}>Confirm escalation</Button>
            </div>
          )}
          {showModify && (
            <div className="mt-4 pt-3 border-t border-border space-y-2.5">
              <p className="text-[11px] font-medium text-foreground">Modify playbook parameters</p>
              <div className="flex items-center gap-2.5"><label className="text-[11px] text-muted-foreground shrink-0">maxPoolSize</label><Input value={modifyValue} onChange={e => setModifyValue(e.target.value)} className="w-20 h-8 text-[12px] font-mono" /><span className="text-[10px] text-muted-foreground">AI recommended 150 → you: {modifyValue}</span></div>
              <Textarea placeholder="Reason for modification..." value={modifyReason} onChange={e => setModifyReason(e.target.value)} className="h-14 text-[12px]" />
              <Button className="bg-accent hover:bg-accent/90 text-accent-foreground text-[12px] h-8" disabled={!modifyReason.trim()} onClick={handleApproveClick}>Confirm modified approval</Button>
            </div>
          )}
          {showReject && (
            <div className="mt-4 pt-3 border-t border-border space-y-2.5">
              <p className="text-[11px] font-medium text-foreground">Reject AI recommendation</p>
              <p className="text-[10px] text-muted-foreground">State the real root cause and intended engineering fix. This becomes 3× weight training data.</p>
              <Textarea placeholder="Explain the correct diagnosis and intended resolution approach..." value={rejectReason} onChange={e => setRejectReason(e.target.value)} className="h-24 text-[12px]" />
              <Button className="bg-status-critical hover:bg-status-critical/90 text-destructive-foreground text-[12px] h-8" disabled={!rejectReason.trim()} onClick={handleReject}>Confirm rejection</Button>
            </div>
          )}
        </div>
      )}

      {/* Raw evidence (collapsed) */}
      <div className="bg-card border border-border rounded-lg shadow-atlas">
        <button onClick={() => setShowRawEvidence(!showRawEvidence)} className="w-full px-4 py-3 flex items-center gap-2 text-left hover:bg-muted/20 transition-colors">
          {showRawEvidence ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" /> : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
          <span className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Raw evidence</span>
          <span className="text-[10px] text-muted-foreground">— metric snapshots & log excerpts</span>
        </button>
        {showRawEvidence && (
          <div className="px-4 pb-4 border-t border-border pt-3">
            <div className="bg-muted/30 rounded p-3 font-mono text-[10px] text-muted-foreground space-y-1 max-h-[200px] overflow-auto">
              <p>[{new Date(incident.detectedAt).toISOString()}] ANOMALY_DETECTED service={incident.services[0]?.name} metric={incident.services[0]?.triggerMetric} value={incident.services[0]?.triggerValue}</p>
              {incident.services.slice(1).map((s, i) => <p key={i}>[{new Date(new Date(incident.detectedAt).getTime() + (i + 1) * 2000).toISOString()}] CASCADE_CHECK service={s.name} health={s.health}</p>)}
              {incident.deploymentCorrelation && <p>[CORRELATION] change_id={incident.deploymentCorrelation.changeId} deployed_by={incident.deploymentCorrelation.deployedBy}</p>}
              <p>[DECISION] playbook={incident.recommendedAction.playbookName} confidence={incident.rootCause.confidence}%</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  // ════════════════════════════════════════════════
  //  L3 — ENGINEERING DEBUG WORKSPACE (Split layout)
  // ════════════════════════════════════════════════
  if (isL3) {
    return (
      <div className="grid gap-4 grid-cols-1 lg:grid-cols-[minmax(0,1fr)_340px]">
        {/* Left: Analysis stack (same as L2) */}
        {l2AnalysisView}

        {/* Right: Engineering sidebar */}
        <aside className="space-y-4 lg:sticky lg:top-6 self-start">
          {/* Fault identification */}
          <div className="bg-card border border-border rounded-lg shadow-atlas overflow-hidden">
            <div className="px-4 py-3 bg-status-critical/[0.04] border-b border-border flex items-center gap-2">
              <Bug className="h-4 w-4 text-status-critical" />
              <span className="text-[11px] font-semibold text-status-critical uppercase tracking-wider">Engineering Fault</span>
            </div>
            <div className="p-4 space-y-3">
              <div>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Identified issue</p>
                <p className="text-[12px] font-medium text-foreground">{engineeringContext.title}</p>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Severity classification</p>
                <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded border border-status-critical/20 bg-status-critical/5 text-[10px] text-status-critical font-medium">
                  <AlertTriangle className="h-3 w-3" /> {engineeringContext.severity}
                </span>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Remediation</p>
                <p className="text-[11px] text-foreground leading-relaxed">{engineeringContext.remediation}</p>
              </div>
            </div>
          </div>

          {/* Suspected files */}
          <div className="bg-card border border-border rounded-lg shadow-atlas overflow-hidden">
            <div className="px-4 py-3 border-b border-border flex items-center gap-2">
              <Code2 className="h-4 w-4 text-accent" />
              <span className="text-[11px] font-semibold text-foreground uppercase tracking-wider">Suspected files</span>
            </div>
            <div className="p-3 space-y-1.5">
              {engineeringContext.files.map(file => (
                <div key={file} className="px-3 py-2 border border-border rounded bg-muted/20">
                  <p className="font-mono text-[10px] text-foreground break-all">{file}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Config diff */}
          <div className="bg-card border border-border rounded-lg shadow-atlas overflow-hidden">
            <button onClick={() => setShowConfigDiff(!showConfigDiff)} className="w-full px-4 py-3 border-b border-border flex items-center justify-between hover:bg-muted/20 transition-colors">
              <div className="flex items-center gap-2">
                <GitCommitHorizontal className="h-4 w-4 text-status-warning" />
                <span className="text-[11px] font-semibold text-foreground uppercase tracking-wider">Config diff</span>
              </div>
              {showConfigDiff ? <ChevronDown className="h-3 w-3 text-muted-foreground" /> : <ChevronRight className="h-3 w-3 text-muted-foreground" />}
            </button>
            {showConfigDiff && (
              <div className="p-3 space-y-2">
                <div className="border border-status-healthy/20 rounded overflow-hidden">
                  <div className="px-3 py-1.5 bg-status-healthy/5 border-b border-status-healthy/10 text-[9px] font-semibold text-status-healthy uppercase tracking-wider">Previous (known-good)</div>
                  <pre className="p-3 text-[10px] font-mono text-foreground whitespace-pre-wrap bg-muted/10">{engineeringContext.diff.before}</pre>
                </div>
                <div className="border border-status-critical/20 rounded overflow-hidden">
                  <div className="px-3 py-1.5 bg-status-critical/5 border-b border-status-critical/10 text-[9px] font-semibold text-status-critical uppercase tracking-wider">Current (suspect)</div>
                  <pre className="p-3 text-[10px] font-mono text-foreground whitespace-pre-wrap bg-muted/10">{engineeringContext.diff.after}</pre>
                </div>
              </div>
            )}
          </div>

          {/* Stack trace */}
          <div className="bg-card border border-border rounded-lg shadow-atlas overflow-hidden">
            <div className="px-4 py-3 border-b border-border flex items-center gap-2">
              <Terminal className="h-4 w-4 text-muted-foreground" />
              <span className="text-[11px] font-semibold text-foreground uppercase tracking-wider">Stack trace</span>
            </div>
            <div className="p-3">
              <pre className="p-3 bg-primary text-primary-foreground rounded font-mono text-[9px] leading-relaxed whitespace-pre-wrap overflow-auto max-h-[240px]">{engineeringContext.stackTrace}</pre>
            </div>
          </div>

          {/* Runtime metrics */}
          <div className="bg-card border border-border rounded-lg shadow-atlas overflow-hidden">
            <div className="px-4 py-3 border-b border-border flex items-center gap-2">
              <Cpu className="h-4 w-4 text-muted-foreground" />
              <span className="text-[11px] font-semibold text-foreground uppercase tracking-wider">Runtime metrics</span>
            </div>
            <div className="p-3 grid grid-cols-2 gap-2">
              {[
                { label: 'p99 Latency', value: `${engineeringContext.metrics.p99LatencyMs}ms`, warn: engineeringContext.metrics.p99LatencyMs > 1000 },
                { label: 'Error Rate', value: `${engineeringContext.metrics.errorRate}%`, warn: engineeringContext.metrics.errorRate > 5 },
                ...(engineeringContext.metrics.activeConnections > 0 ? [
                  { label: 'Active Conn', value: `${engineeringContext.metrics.activeConnections}/${engineeringContext.metrics.maxConnections}`, warn: true },
                  { label: 'Waiting', value: `${engineeringContext.metrics.waitingThreads} threads`, warn: engineeringContext.metrics.waitingThreads > 10 },
                ] : []),
              ].map((m, i) => (
                <div key={i} className="border border-border rounded p-2 text-center">
                  <p className="text-[9px] text-muted-foreground uppercase tracking-wider">{m.label}</p>
                  <p className={cn('text-[14px] font-mono font-bold tabular-nums mt-0.5', m.warn ? 'text-status-critical' : 'text-foreground')}>{m.value}</p>
                </div>
              ))}
            </div>
          </div>
        </aside>

        <ConfirmationDialog open={showConfirmation} onConfirm={handleConfirmApprove} onCancel={() => setShowConfirmation(false)} playbookName={incident.recommendedAction.playbookName} description={incident.recommendedAction.description} affectedService={incident.affectedServices[0]} />
      </div>
    );
  }

  // ════════════════════════════════════════════════
  //  L2 / SDM — Standard analysis view
  // ════════════════════════════════════════════════
  return (
    <div>
      {l2AnalysisView}
      <ConfirmationDialog open={showConfirmation} onConfirm={handleConfirmApprove} onCancel={() => setShowConfirmation(false)} playbookName={incident.recommendedAction.playbookName} description={incident.recommendedAction.description} affectedService={incident.affectedServices[0]} />
    </div>
  );
}
