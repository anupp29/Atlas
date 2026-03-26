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
import { ChevronDown, ChevronRight, AlertTriangle, CheckCircle2, Clock, ExternalLink, Shield, Brain, FileCode2, GitCommitHorizontal, Wrench, ArrowRight } from 'lucide-react';
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
      remediation: 'Revert pool size to a safe production value, redeploy the config package, and open a permanent problem record for capacity guardrails.',
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
    remediation: 'Move analytics writes to a separate Redis target, flush analytics:* keys from the shared cluster, and enforce namespace isolation in deployment validation.',
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

  const handleEscalate = () => {
    setIsEscalated(true);
    setShowEscalate(false);
  };

  const handleReject = () => {
    setIsRejected(true);
    setShowReject(false);
  };

  const confidenceLabel = incident.rootCause.confidence >= 85 ? 'High' : incident.rootCause.confidence >= 70 ? 'Medium' : 'Low';

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
            <div>
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Client</p>
              <p className="text-[13px] font-medium text-foreground mt-0.5">{incident.clientName}</p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">MTTR</p>
              <p className="text-[13px] font-semibold text-status-healthy mt-0.5">4m 12s</p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Playbook</p>
              <p className="font-mono text-[11px] text-foreground mt-0.5">{incident.recommendedAction.playbookName}</p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Approved by</p>
              <p className="text-[13px] text-foreground mt-0.5">{user?.name}</p>
            </div>
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
          <p className="text-[13px] text-muted-foreground">AI recommendation rejected. L3 engineering diagnosis has taken ownership of the incident.</p>
          <div className="bg-muted/30 rounded p-3 mt-3">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">L3 diagnosis</p>
            <p className="text-[12px] text-foreground leading-relaxed">{rejectReason}</p>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <Button className="bg-status-healthy hover:bg-status-healthy/90 text-white text-[12px] h-8" onClick={() => setIsResolved(true)}>
              Mark Resolved
            </Button>
            <span className="text-[10px] text-muted-foreground">Stored as high-weight training data.</span>
          </div>
        </div>
      </div>
    );
  }

  if (isL1) {
    return (
      <div className="space-y-4 max-w-4xl">
        <PipelineIndicator currentStage={pipelineStage} compact />

        <div className="bg-card border border-border rounded-lg p-5 shadow-atlas">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="px-2 py-1 rounded bg-accent/10 text-accent text-[10px] font-semibold uppercase tracking-wider">L1 triage console</span>
                <span className="font-mono text-[11px] text-muted-foreground">{incident.id}</span>
                <PriorityBadge priority={incident.priority} />
              </div>
              <h2 className="text-[15px] font-semibold text-foreground">{incident.clientName}</h2>
              <p className="text-[12px] text-muted-foreground mt-1">First-line operator view — approve or escalate.</p>
            </div>
            <div className="text-right">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">SLA remaining</p>
              <CountdownTimer deadline={incident.slaDeadline} className="text-[14px] font-mono" />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="md:col-span-2 border border-border rounded-lg p-4 bg-muted/20">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">Situation summary</p>
              <p className="text-[13px] text-foreground leading-relaxed">{incident.summary}</p>
            </div>
            <div className="border border-border rounded-lg p-4">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">Decision signal</p>
              <p className={cn('text-[16px] font-semibold', confidenceLabel === 'High' ? 'text-status-healthy' : confidenceLabel === 'Medium' ? 'text-status-warning' : 'text-status-critical')}>
                {confidenceLabel}
              </p>
              <p className="text-[11px] text-muted-foreground mt-1">ATLAS confidence for first-line approval</p>
            </div>
          </div>
        </div>

        <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
          <h3 className="text-[12px] font-semibold text-foreground mb-3 uppercase tracking-wider">Operator checklist</h3>
          <div className="space-y-2.5">
            {[
              `Primary impact confirmed on ${incident.affectedServices[0]}`,
              incident.deploymentCorrelation ? `Recent change detected: ${incident.deploymentCorrelation.changeId}` : 'No recent deployment detected',
              `Recommended action is ${incident.recommendedAction.riskClass.toLowerCase()} risk with ${incident.recommendedAction.rollbackAvailable ? 'rollback available' : 'manual rollback'}`,
              `Business impact: ${incident.businessImpact}`,
            ].map((item, index) => (
              <div key={item} className="flex items-start gap-3 border border-border rounded-lg p-3">
                <div className="h-5 w-5 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-[10px] font-semibold shrink-0">{index + 1}</div>
                <p className="text-[12px] text-foreground leading-relaxed">{item}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
          <h3 className="text-[12px] font-semibold text-foreground mb-3 uppercase tracking-wider">Service health snapshot</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {incident.services.slice(0, 4).map((service) => (
              <div key={service.id} className="border border-border rounded-md p-3 flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-1.5">
                    <StatusIndicator status={service.health} />
                    <span className="text-[12px] font-medium text-foreground">{service.name}</span>
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-1">{service.technology}</p>
                </div>
                <p className="text-[10px] font-mono text-foreground text-right max-w-[140px]">{service.triggerValue}</p>
              </div>
            ))}
          </div>
        </div>

        {incident.deploymentCorrelation && (
          <div className="bg-card border border-border rounded-lg p-4 shadow-atlas border-l-[3px] border-l-status-warning">
            <h3 className="text-[12px] font-semibold text-foreground mb-1.5 uppercase tracking-wider">What changed</h3>
            <p className="text-[12px] text-foreground leading-relaxed">{incident.deploymentCorrelation.description}</p>
            <p className="text-[10px] text-muted-foreground mt-2">{incident.deploymentCorrelation.changeId} · deployed by {incident.deploymentCorrelation.deployedBy} · {incident.deploymentCorrelation.daysAgo} day(s) ago</p>
          </div>
        )}

        {isExecuting ? (
          <ExecutionTrace playbookName={incident.recommendedAction.playbookName} onComplete={handleExecutionComplete} />
        ) : (
          <div className="bg-card border border-border rounded-lg p-5 shadow-atlas border-l-4 border-l-accent">
            <div className="flex items-start justify-between gap-4 mb-3">
              <div>
                <h3 className="text-[14px] font-semibold text-foreground">Recommended action</h3>
                <p className="font-mono text-[11px] text-accent mt-1">{incident.recommendedAction.playbookName}</p>
              </div>
              <div className="text-right text-[10px] text-muted-foreground">
                <p>Est. {incident.recommendedAction.estimatedTime}</p>
                <p className="mt-1">Risk: {incident.recommendedAction.riskClass}</p>
              </div>
            </div>
            <p className="text-[12px] text-foreground leading-relaxed mb-4">{incident.recommendedAction.description}</p>

            <div className="flex items-center gap-2.5">
              <Button onClick={handleApproveClick} className="bg-accent hover:bg-accent/90 text-accent-foreground px-7 h-10 text-[13px] font-semibold">
                {needsDualApproval ? 'Submit for Dual Approval' : 'Approve'}
              </Button>
              <Button variant="ghost" className="text-muted-foreground text-[12px]" onClick={() => setShowEscalate(!showEscalate)}>
                Escalate to L2
              </Button>
            </div>

            {showEscalate && (
              <div className="mt-4 pt-3 border-t border-border space-y-2.5">
                <p className="text-[11px] font-medium text-foreground">Escalation to L2</p>
                <Textarea placeholder="Why does this need deeper investigation?" value={escalateReason} onChange={(e) => setEscalateReason(e.target.value)} className="h-16 text-[12px]" />
                <Button className="bg-accent hover:bg-accent/90 text-accent-foreground text-[12px] h-8" disabled={!escalateReason.trim()} onClick={handleEscalate}>
                  Confirm escalation
                </Button>
              </div>
            )}
          </div>
        )}

        <ConfirmationDialog
          open={showConfirmation}
          onConfirm={handleConfirmApprove}
          onCancel={() => setShowConfirmation(false)}
          playbookName={incident.recommendedAction.playbookName}
          description={incident.recommendedAction.description}
          affectedService={incident.affectedServices[0]}
        />
      </div>
    );
  }

  const analysisStack = (
    <div className="space-y-4">
      <PipelineIndicator currentStage={pipelineStage} />

      <div className="bg-card border border-border rounded-lg p-5 shadow-atlas">
        <div className="flex items-center justify-between mb-3 gap-4">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className={cn('px-2 py-1 rounded text-[10px] font-semibold uppercase tracking-wider', isL2 ? 'bg-accent/10 text-accent' : 'bg-primary text-primary-foreground')}>
              {isL2 ? 'L2 analysis workspace' : 'L3 engineering workspace'}
            </span>
            <span className="font-mono text-[11px] text-muted-foreground">{incident.id}</span>
            <span className="text-[13px] font-medium text-foreground">{incident.clientName}</span>
            <PriorityBadge priority={incident.priority} />
            {needsDualApproval && (
              <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-status-warning/10 text-status-warning uppercase">{client?.complianceFlags?.join(' · ')}</span>
            )}
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

      <AIReasoningPanel incident={incident} showFullDetail />

      <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
        <h3 className="text-[12px] font-semibold text-foreground mb-3 uppercase tracking-wider">Service health snapshot</h3>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
          {incident.services.map((service) => (
            <div key={service.id} className={cn('border rounded-md p-3', service.health === 'critical' ? 'border-status-critical/30 bg-destructive/[0.02]' : service.health === 'warning' ? 'border-status-warning/25 bg-status-warning/[0.02]' : 'border-border')}>
              <div className="flex items-center gap-1.5 mb-1"><StatusIndicator status={service.health} /><span className="text-[12px] font-medium text-foreground">{service.name}</span></div>
              <p className="text-[10px] text-muted-foreground">{service.technology}</p>
              {service.triggerMetric && <p className="text-[10px] text-foreground mt-1.5 font-mono leading-tight">{service.triggerMetric}: {service.triggerValue}</p>}
              {service.lastDeployment && <p className="text-[9px] text-muted-foreground mt-1">Deploy: {service.lastDeployment}</p>}
            </div>
          ))}
        </div>
      </div>

      {incident.deploymentCorrelation && (
        <div className="bg-card border border-border rounded-lg p-4 shadow-atlas border-l-[3px] border-l-status-warning">
          <h3 className="text-[12px] font-semibold text-foreground mb-1.5 uppercase tracking-wider">What changed</h3>
          <p className="text-[13px] text-foreground">A deployment was made {incident.deploymentCorrelation.daysAgo} day{incident.deploymentCorrelation.daysAgo !== 1 ? 's' : ''} ago that modified this service.</p>
          <div className="mt-2.5 flex items-start gap-3 text-[12px]"><span className="font-mono text-accent font-medium shrink-0">{incident.deploymentCorrelation.changeId}</span><span className="text-muted-foreground">{incident.deploymentCorrelation.description}</span></div>
          <p className="text-[10px] text-muted-foreground mt-2">By {incident.deploymentCorrelation.deployedBy} · CAB risk: {incident.deploymentCorrelation.cabRiskRating}</p>
        </div>
      )}

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
        <p className="text-[9px] text-muted-foreground mt-2">Causal path highlighted in blue. Deployment change is shown as a diamond node.</p>
      </div>

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
          <p className="text-[12px] text-muted-foreground">No strong historical precedent found.</p>
        )}
      </div>

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

      {(isExecuting ? (
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
              <Button onClick={handleApproveClick} className="bg-accent hover:bg-accent/90 text-accent-foreground px-7 h-10 text-[13px] font-semibold">{needsDualApproval ? 'Submit for Dual Approval' : 'Approve'}</Button>
              <Button variant="outline" className="h-9 text-[12px]" onClick={() => { setShowModify(!showModify); setShowEscalate(false); setShowReject(false); }}>Modify</Button>
              {isL2 && <Button variant="ghost" className="text-muted-foreground text-[12px]" onClick={() => { setShowEscalate(!showEscalate); setShowModify(false); }}>Escalate to L3</Button>}
              {isL3 && <Button variant="ghost" className="text-status-critical text-[12px]" onClick={() => { setShowReject(!showReject); setShowModify(false); }}>Reject</Button>}
            </div>
          )}
          {showEscalate && (
            <div className="mt-4 pt-3 border-t border-border space-y-2.5">
              <p className="text-[11px] font-medium text-foreground">Escalation to L3</p>
              <Textarea placeholder="Reason for escalation..." value={escalateReason} onChange={(e) => setEscalateReason(e.target.value)} className="h-16 text-[12px]" />
              <Button className="bg-accent hover:bg-accent/90 text-accent-foreground text-[12px] h-8" disabled={!escalateReason.trim()} onClick={handleEscalate}>Confirm escalation</Button>
            </div>
          )}
          {showModify && (
            <div className="mt-4 pt-3 border-t border-border space-y-2.5">
              <p className="text-[11px] font-medium text-foreground">Modify playbook parameters</p>
              <div className="flex items-center gap-2.5"><label className="text-[11px] text-muted-foreground shrink-0">maxPoolSize</label><Input value={modifyValue} onChange={(e) => setModifyValue(e.target.value)} className="w-20 h-8 text-[12px] font-mono" /><span className="text-[10px] text-muted-foreground">AI recommended 150 → you: {modifyValue}</span></div>
              <Textarea placeholder="Reason for modification..." value={modifyReason} onChange={(e) => setModifyReason(e.target.value)} className="h-14 text-[12px]" />
              <Button className="bg-accent hover:bg-accent/90 text-accent-foreground text-[12px] h-8" disabled={!modifyReason.trim()} onClick={handleApproveClick}>Confirm modified approval</Button>
            </div>
          )}
          {showReject && (
            <div className="mt-4 pt-3 border-t border-border space-y-2.5">
              <p className="text-[11px] font-medium text-foreground">Reject AI recommendation</p>
              <p className="text-[10px] text-muted-foreground">State the real root cause and intended engineering fix.</p>
              <Textarea placeholder="Explain the correct diagnosis and intended resolution approach..." value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} className="h-24 text-[12px]" />
              <Button className="bg-status-critical hover:bg-status-critical/90 text-destructive-foreground text-[12px] h-8" disabled={!rejectReason.trim()} onClick={handleReject}>Confirm rejection</Button>
            </div>
          )}
        </div>
      ))}

      {(isL2 || isL3) && (
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
                {incident.services.slice(1).map((s, i) => <p key={i}>[{new Date(new Date(incident.detectedAt).getTime() + (i + 1) * 2000).toISOString()}] CASCADE_CHECK service={s.name} health={s.health} metric={s.triggerMetric || 'N/A'} value={s.triggerValue || 'normal'}</p>)}
                {incident.deploymentCorrelation && <p>[CORRELATION] change_id={incident.deploymentCorrelation.changeId} deployed_by={incident.deploymentCorrelation.deployedBy} days_ago={incident.deploymentCorrelation.daysAgo} cab_risk={incident.deploymentCorrelation.cabRiskRating}</p>}
                {incident.historicalMatch && <p>[KB_MATCH] incident={incident.historicalMatch.incidentId} similarity={incident.historicalMatch.similarity}% date={incident.historicalMatch.occurredAt}</p>}
                <p>[DECISION] playbook={incident.recommendedAction.playbookName} confidence={incident.rootCause.confidence}% risk={incident.recommendedAction.riskClass}</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );

  const l3Sidebar = isL3 ? (
    <aside className="space-y-4 lg:sticky lg:top-6 self-start">
      <div className="bg-card border border-border rounded-lg p-4 shadow-atlas border-l-[3px] border-l-status-critical">
        <div className="flex items-center gap-2 mb-3">
          <FileCode2 className="h-4 w-4 text-status-critical" />
          <h3 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Code / config fault</h3>
        </div>
        <p className="text-[12px] text-foreground leading-relaxed">{engineeringContext.issue}</p>
        <div className="mt-3 inline-flex items-center gap-2 px-2.5 py-1.5 rounded border border-status-critical/20 bg-status-critical/5 text-[10px] text-status-critical font-medium">
          <AlertTriangle className="h-3 w-3" /> {engineeringContext.severity}
        </div>
      </div>

      <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
        <div className="flex items-center gap-2 mb-3">
          <GitCommitHorizontal className="h-4 w-4 text-accent" />
          <h3 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Engineering investigation</h3>
        </div>
        <div className="space-y-2">
          {engineeringContext.files.map((file) => (
            <div key={file} className="border border-border rounded-md px-3 py-2">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Suspected file</p>
              <p className="font-mono text-[11px] text-foreground mt-1 break-all">{file}</p>
            </div>
          ))}
        </div>
        <div className="mt-3 flex flex-col gap-2">
          <Button variant="outline" className="justify-between text-[12px]" onClick={() => setShowConfigDiff(!showConfigDiff)}>
            Open suspected config diff <ArrowRight className="h-3 w-3" />
          </Button>
          <Button variant="outline" className="justify-between text-[12px]" onClick={() => setShowRawEvidence(true)}>
            Open runtime evidence <ArrowRight className="h-3 w-3" />
          </Button>
        </div>
      </div>

      <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
        <div className="flex items-center gap-2 mb-3">
          <Wrench className="h-4 w-4 text-accent" />
          <h3 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Failure signature</h3>
        </div>
        <div className="bg-muted/30 rounded-lg p-3 font-mono text-[10px] text-muted-foreground space-y-1.5">
          {engineeringContext.signature.map((line) => <p key={line}>{line}</p>)}
        </div>
        <p className="text-[10px] text-muted-foreground mt-3">{engineeringContext.remediation}</p>
      </div>

      {showConfigDiff && (
        <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
          <h3 className="text-[12px] font-semibold text-foreground uppercase tracking-wider mb-3">Suspected config diff</h3>
          <div className="grid grid-cols-1 gap-3">
            <div className="border border-border rounded-lg overflow-hidden">
              <div className="px-3 py-2 bg-muted/20 border-b border-border text-[10px] uppercase tracking-wider text-muted-foreground">Previous known-good</div>
              <pre className="p-3 text-[10px] font-mono text-foreground whitespace-pre-wrap">{engineeringContext.diff.before}</pre>
            </div>
            <div className="border border-border rounded-lg overflow-hidden">
              <div className="px-3 py-2 bg-muted/20 border-b border-border text-[10px] uppercase tracking-wider text-muted-foreground">Current suspect change</div>
              <pre className="p-3 text-[10px] font-mono text-foreground whitespace-pre-wrap">{engineeringContext.diff.after}</pre>
            </div>
          </div>
        </div>
      )}
    </aside>
  ) : null;

  return (
    <div className={cn('grid gap-4', isL3 ? 'grid-cols-1 lg:grid-cols-[minmax(0,1fr)_320px]' : 'grid-cols-1')}>
      {analysisStack}
      {l3Sidebar}
      <ConfirmationDialog
        open={showConfirmation}
        onConfirm={handleConfirmApprove}
        onCancel={() => setShowConfirmation(false)}
        playbookName={incident.recommendedAction.playbookName}
        description={incident.recommendedAction.description}
        affectedService={incident.affectedServices[0]}
      />
    </div>
  );
}
