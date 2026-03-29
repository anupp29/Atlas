import { useState, useEffect, useMemo } from 'react';
import { cn } from '@/lib/utils';
import { Check, X, Loader2, AlertTriangle } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, ReferenceLine, ResponsiveContainer } from 'recharts';

export interface ExecutionStepData {
  id: string;
  description: string;
  status: 'pending' | 'running' | 'complete' | 'failed';
  timestamp?: string;
}

interface ExecutionTraceProps {
  playbookName: string;
  onComplete?: () => void;
  /** Optional: override steps for specific playbook types */
  customSteps?: { id: string; description: string }[];
}

// Build playbook-specific steps
function buildSteps(playbookName: string): { id: string; description: string }[] {
  const name = playbookName.toLowerCase();

  if (name.includes('connection-pool')) {
    return [
      { id: 'pre', description: 'Pre-validation: checking Spring Actuator endpoint reachability and current pool configuration' },
      { id: 'exec', description: 'Executing: PATCH /actuator/env — setting hikari.maximum-pool-size=150 on PaymentGateway' },
      { id: 'monitor', description: 'Monitoring recovery: tracking connection pool utilization, p99 latency, and FraudEngine throughput' },
      { id: 'resolve', description: 'Resolution confirmed: all success criteria met — pool utilization <70%, latency <500ms' },
    ];
  }

  if (name.includes('redis')) {
    return [
      { id: 'pre', description: 'Pre-validation: sampling Redis MEMORY USAGE, confirming PostgreSQL replica health' },
      { id: 'exec', description: 'Executing: flushing analytics:* namespace (~6.2GB), setting maxmemory-policy=volatile-lru' },
      { id: 'monitor', description: 'Monitoring recovery: tracking cache hit ratio, ProductCatalog p95 latency, eviction rate' },
      { id: 'resolve', description: 'Resolution confirmed: cache hit ratio >85%, latency <300ms, eviction rate <200 keys/min' },
    ];
  }

  if (name.includes('tls') || name.includes('cert')) {
    return [
      { id: 'pre', description: 'Pre-validation: verifying ACME client configuration and certificate authority reachability' },
      { id: 'exec', description: 'Executing: ACME DNS-01 challenge, issuing new TLS certificate (90-day validity)' },
      { id: 'monitor', description: 'Monitoring: Nginx configuration validation and zero-downtime reload' },
      { id: 'resolve', description: 'Resolution confirmed: new certificate active, TLS handshake successful on all domains' },
    ];
  }

  if (name.includes('kafka')) {
    return [
      { id: 'pre', description: 'Pre-validation: verifying Kafka broker connectivity and consumer group state' },
      { id: 'exec', description: 'Executing: resetting consumer group offsets to last committed position, triggering rebalance' },
      { id: 'monitor', description: 'Monitoring recovery: tracking consumer lag, partition assignment, and message processing rate' },
      { id: 'resolve', description: 'Resolution confirmed: consumer lag 0, all partitions assigned, processing rate at baseline' },
    ];
  }

  if (name.includes('k8s') || name.includes('pod')) {
    return [
      { id: 'pre', description: 'Pre-validation: checking cluster capacity, PodDisruptionBudget, and active deployments' },
      { id: 'exec', description: 'Executing: graceful pod termination and rescheduling on healthy nodes' },
      { id: 'monitor', description: 'Monitoring: pod startup, health check readiness, and service endpoint updates' },
      { id: 'resolve', description: 'Resolution confirmed: all pods Running, health checks passing, traffic routing correctly' },
    ];
  }

  // Generic fallback
  return [
    { id: 'pre', description: 'Pre-validation: checking service endpoints and prerequisites' },
    { id: 'exec', description: `Executing playbook: ${playbookName}` },
    { id: 'monitor', description: 'Monitoring recovery: tracking key metrics and success criteria' },
    { id: 'resolve', description: 'Resolution confirmed: all success criteria met' },
  ];
}

// Build metric chart data based on playbook type
function buildChartConfig(playbookName: string): {
  label: string;
  threshold: number;
  thresholdLabel: string;
  unit: string;
  preValue: number;
  postValue: number;
} {
  const name = playbookName.toLowerCase();

  if (name.includes('connection-pool')) {
    return { label: 'Connection Pool Utilization', threshold: 70, thresholdLabel: 'Safe threshold', unit: '%', preValue: 94, postValue: 42 };
  }
  if (name.includes('redis')) {
    return { label: 'Cache Hit Ratio', threshold: 85, thresholdLabel: 'Target', unit: '%', preValue: 41, postValue: 93 };
  }
  if (name.includes('kafka')) {
    return { label: 'Consumer Lag (messages)', threshold: 100, thresholdLabel: 'Alert threshold', unit: '', preValue: 8400, postValue: 0 };
  }
  return { label: 'Service Health Score', threshold: 80, thresholdLabel: 'Healthy threshold', unit: '%', preValue: 35, postValue: 92 };
}

function generateRecoveryData(phase: number, preValue: number, postValue: number) {
  const data = [];
  const isRecovery = postValue > preValue; // cache hit ratio goes up; pool util goes down

  for (let i = 0; i <= 20; i++) {
    let value: number;
    if (i <= 8) {
      value = preValue + (Math.random() - 0.5) * 4;
    } else if (i <= 12) {
      const progress = (i - 8) / 4;
      value = preValue + (postValue - preValue) * progress + (Math.random() - 0.5) * 3;
    } else {
      value = postValue + (Math.random() - 0.5) * 3;
    }
    if (phase < 2 && i > 12) continue;
    if (phase < 1 && i > 8) continue;
    data.push({ time: `${i * 15}s`, value: Math.max(0, Math.min(100, value)) });
  }
  return data;
}

export function ExecutionTrace({ playbookName, onComplete, customSteps }: ExecutionTraceProps) {
  const stepDefs = useMemo(() => customSteps || buildSteps(playbookName), [playbookName, customSteps]);
  const chartConfig = useMemo(() => buildChartConfig(playbookName), [playbookName]);

  const [steps, setSteps] = useState<ExecutionStepData[]>(
    stepDefs.map((s) => ({ ...s, status: 'pending' as const })),
  );
  const [recoveryPhase, setRecoveryPhase] = useState(0);

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];

    timers.push(setTimeout(() => {
      setSteps((prev) => prev.map((s, i) => i === 0 ? { ...s, status: 'running' } : s));
    }, 400));
    timers.push(setTimeout(() => {
      setSteps((prev) => prev.map((s, i) => i === 0 ? { ...s, status: 'complete', timestamp: new Date().toLocaleTimeString('en-GB') } : s));
    }, 2200));
    timers.push(setTimeout(() => {
      setSteps((prev) => prev.map((s, i) => i === 1 ? { ...s, status: 'running' } : s));
    }, 2600));
    timers.push(setTimeout(() => {
      setSteps((prev) => prev.map((s, i) => i === 1 ? { ...s, status: 'complete', timestamp: new Date().toLocaleTimeString('en-GB') } : s));
      setRecoveryPhase(1);
    }, 4800));
    timers.push(setTimeout(() => {
      setSteps((prev) => prev.map((s, i) => i === 2 ? { ...s, status: 'running' } : s));
    }, 5200));
    timers.push(setTimeout(() => setRecoveryPhase(2), 7200));
    timers.push(setTimeout(() => {
      setSteps((prev) => prev.map((s, i) => i === 2 ? { ...s, status: 'complete', timestamp: new Date().toLocaleTimeString('en-GB') } : s));
    }, 9200));
    timers.push(setTimeout(() => {
      setSteps((prev) => prev.map((s, i) => i === 3 ? { ...s, status: 'running' } : s));
    }, 9600));
    timers.push(setTimeout(() => {
      setSteps((prev) => prev.map((s, i) => i === 3 ? { ...s, status: 'complete', timestamp: new Date().toLocaleTimeString('en-GB') } : s));
      onComplete?.();
    }, 11200));

    return () => timers.forEach(clearTimeout);
  }, [onComplete]);

  const recoveryData = generateRecoveryData(recoveryPhase, chartConfig.preValue, chartConfig.postValue);
  const monitoringStep = steps.find((s) => s.id === 'monitor');
  const showChart = monitoringStep?.status === 'running' || monitoringStep?.status === 'complete';
  const isRecoveryUp = chartConfig.postValue > chartConfig.preValue;

  return (
    <div className="bg-card border border-border rounded-lg p-5 shadow-atlas">
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">Executing playbook</p>
          <h3 className="text-[13px] font-semibold text-foreground font-mono">{playbookName}</h3>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-accent atlas-pulse" />
          <span className="text-[10px] text-accent font-medium">Live execution</span>
        </div>
      </div>

      <div className="space-y-0">
        {steps.map((step) => (
          <div key={step.id} className="flex items-start gap-3 py-2.5 border-b border-border/50 last:border-0">
            <div className="mt-0.5 shrink-0">
              {step.status === 'complete' && (
                <div className="h-5 w-5 rounded-full bg-status-healthy/10 border border-status-healthy/30 flex items-center justify-center">
                  <Check className="h-3 w-3 text-status-healthy" />
                </div>
              )}
              {step.status === 'failed' && (
                <div className="h-5 w-5 rounded-full bg-status-critical/10 border border-status-critical/30 flex items-center justify-center">
                  <X className="h-3 w-3 text-status-critical" />
                </div>
              )}
              {step.status === 'running' && (
                <div className="h-5 w-5 rounded-full bg-accent/10 border border-accent/30 flex items-center justify-center">
                  <Loader2 className="h-3 w-3 text-accent animate-spin" />
                </div>
              )}
              {step.status === 'pending' && (
                <div className="h-5 w-5 rounded-full bg-muted border border-border" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className={cn(
                'text-[12px] leading-relaxed',
                step.status === 'complete' && 'text-foreground',
                step.status === 'running' && 'text-foreground font-medium',
                step.status === 'pending' && 'text-muted-foreground',
                step.status === 'failed' && 'text-status-critical',
              )}>
                {step.description}
              </p>
            </div>
            {step.timestamp && (
              <span className="font-mono text-[10px] text-muted-foreground shrink-0 tabular-nums">{step.timestamp}</span>
            )}
          </div>
        ))}
      </div>

      {showChart && (
        <div className="mt-4 pt-4 border-t border-border">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[11px] font-medium text-muted-foreground">{chartConfig.label} {chartConfig.unit && `(${chartConfig.unit})`}</p>
            {recoveryPhase >= 2 && (
              <span className="text-[10px] font-medium text-status-healthy flex items-center gap-1">
                <Check className="h-3 w-3" /> Recovered
              </span>
            )}
          </div>
          <div className="h-[130px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={recoveryData}>
                <XAxis dataKey="time" tick={{ fontSize: 9, fill: 'hsl(215, 16%, 47%)' }} tickLine={false} axisLine={{ stroke: 'hsl(214, 32%, 91%)' }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 9, fill: 'hsl(215, 16%, 47%)' }} tickLine={false} axisLine={false} width={28} />
                <ReferenceLine
                  y={chartConfig.threshold}
                  stroke={isRecoveryUp ? 'hsl(142, 72%, 35%)' : 'hsl(32, 95%, 44%)'}
                  strokeDasharray="4 4"
                  label={{ value: chartConfig.thresholdLabel, position: 'right', fill: 'hsl(215, 16%, 47%)', fontSize: 9 }}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="hsl(211, 100%, 40%)"
                  strokeWidth={2}
                  dot={false}
                  animationDuration={400}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
