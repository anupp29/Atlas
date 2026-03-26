import { useState } from 'react';
import { mockClients, mockIncidents } from '@/data/mock';
import { StatusIndicator } from '@/components/atlas/StatusIndicator';
import { PriorityBadge } from '@/components/atlas/PriorityBadge';
import { cn } from '@/lib/utils';
import { CheckCircle2, Clock, AlertCircle, TrendingUp, Shield, ChevronDown, ChevronRight, ArrowUpRight, Activity, Server, Settings } from 'lucide-react';

const incidentTimeline = [
  { time: '09:42:18', event: 'Anomaly detected', detail: 'PaymentGateway HikariCP connection pool at 94% utilization', level: 'detection' as const },
  { time: '09:42:20', event: 'Automated analysis initiated', detail: 'ATLAS AI analyzing service dependencies and deployment history', level: 'analysis' as const },
  { time: '09:42:25', event: 'Root cause identified', detail: 'Configuration change reduced connection pool capacity below production requirements', level: 'analysis' as const },
  { time: '09:42:30', event: 'Resolution plan selected', detail: 'Automated recovery playbook identified with rollback capability', level: 'action' as const },
  { time: '09:42:35', event: 'Assigned to operations team', detail: 'Awaiting engineer approval before executing automated fix', level: 'action' as const },
];

export default function ClientPortal() {
  const client = mockClients[0];
  const clientIncidents = mockIncidents.filter(i => i.clientId === client.id);
  const activeIncidents = clientIncidents.filter(i => i.status !== 'Resolved');
  const [expandedIncident, setExpandedIncident] = useState<string | null>(activeIncidents[0]?.id || null);
  const resolvedCount = 14;
  const totalRecent = 20;

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[16px] font-semibold text-foreground">{client.name}</h1>
          <p className="text-[12px] text-muted-foreground mt-0.5">Environment Health & Service Transparency</p>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
          <span className="h-1.5 w-1.5 rounded-full bg-status-healthy live-dot" />
          <span>Live — updated {new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}</span>
        </div>
      </div>

      {/* Health overview cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">System Status</span>
            <StatusIndicator status={client.health} className="h-2.5 w-2.5" />
          </div>
          <p className="text-[14px] font-semibold text-foreground">
            {client.health === 'healthy' ? 'All Operational' : client.health === 'warning' ? 'Degraded' : 'Service Disruption'}
          </p>
          <p className="text-[10px] text-muted-foreground mt-1">
            {client.health === 'healthy' ? 'No issues detected' : 'Our team is responding'}
          </p>
        </div>
        <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">SLA Compliance</span>
            <TrendingUp className="h-3.5 w-3.5 text-status-healthy" />
          </div>
          <p className="text-[22px] font-bold text-foreground leading-none tabular-nums">{client.slaCompliance}%</p>
          <p className="text-[10px] text-muted-foreground mt-1">Target: 99.0%</p>
        </div>
        <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Active Issues</span>
            <AlertCircle className={cn('h-3.5 w-3.5', activeIncidents.length > 0 ? 'text-status-warning' : 'text-muted-foreground')} />
          </div>
          <p className="text-[22px] font-bold text-foreground leading-none tabular-nums">{activeIncidents.length}</p>
          <p className="text-[10px] text-muted-foreground mt-1">{activeIncidents.length === 0 ? 'No open issues' : 'Being addressed'}</p>
        </div>
        <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Avg Resolution</span>
            <Clock className="h-3.5 w-3.5 text-muted-foreground" />
          </div>
          <p className="text-[22px] font-bold text-foreground leading-none tabular-nums">3m 28s</p>
          <p className="text-[10px] text-status-healthy font-medium mt-1">10× faster than industry</p>
        </div>
      </div>

      {/* Trust statement */}
      <div className="bg-card border border-border rounded-lg p-4 shadow-atlas flex items-center gap-3">
        <Shield className="h-5 w-5 text-accent shrink-0" />
        <p className="text-[12px] text-foreground leading-relaxed">
          Atos's autonomous monitoring has resolved <span className="font-semibold">{resolvedCount} of your last {totalRecent} incidents</span> automatically,
          with an average resolution time of <span className="font-semibold">3 minutes 28 seconds</span>.
        </p>
        <div className="shrink-0 ml-auto">
          <div className="flex items-center gap-2">
            <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
              <div className="h-full bg-status-healthy rounded-full" style={{ width: `${(resolvedCount / totalRecent) * 100}%` }} />
            </div>
            <span className="text-[11px] font-mono font-medium text-foreground tabular-nums">{Math.round((resolvedCount / totalRecent) * 100)}%</span>
          </div>
        </div>
      </div>

      {/* Active issues with lifecycle */}
      <div className="bg-card border border-border rounded-lg shadow-atlas">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <h2 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Active Issues</h2>
          <span className="text-[10px] text-muted-foreground">{activeIncidents.length} issue{activeIncidents.length !== 1 ? 's' : ''}</span>
        </div>
        {activeIncidents.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <CheckCircle2 className="h-5 w-5 text-status-healthy mx-auto mb-2" />
            <p className="text-[13px] font-medium text-foreground">No active issues</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">All services are operating normally.</p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {activeIncidents.map(inc => (
              <div key={inc.id}>
                <button
                  onClick={() => setExpandedIncident(expandedIncident === inc.id ? null : inc.id)}
                  className="w-full px-4 py-3.5 text-left hover:bg-muted/20 transition-colors flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <StatusIndicator status={inc.priority === 'P1' ? 'critical' : 'warning'} className="h-2.5 w-2.5" />
                    <div>
                      <p className="text-[12px] font-medium text-foreground">{inc.affectedServices.join(', ')} — Performance Issue</p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">
                        Detected {new Date(inc.detectedAt).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })} · Est. resolution: {inc.recommendedAction.estimatedTime}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-accent/8 text-accent">In Progress</span>
                    {expandedIncident === inc.id ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" /> : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
                  </div>
                </button>

                {expandedIncident === inc.id && (
                  <div className="px-4 pb-4 border-t border-border bg-muted/10">
                    {/* Plain-English summary */}
                    <div className="py-3">
                      <p className="text-[12px] text-foreground leading-relaxed">
                        We detected a performance issue affecting {inc.affectedServices.join(' and ')}. Our team identified the cause
                        and is working on an automated fix. Your data and transactions remain secure throughout this process.
                      </p>
                    </div>

                    {/* Affected services */}
                    <div className="mb-3">
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">Affected services</p>
                      <div className="flex flex-wrap gap-2">
                        {inc.services.filter(s => s.health !== 'healthy').map(s => (
                          <div key={s.id} className="flex items-center gap-1.5 border border-border rounded px-2.5 py-1.5">
                            <StatusIndicator status={s.health} />
                            <span className="text-[11px] text-foreground">{s.name}</span>
                          </div>
                        ))}
                        {inc.services.filter(s => s.health === 'healthy').map(s => (
                          <div key={s.id} className="flex items-center gap-1.5 border border-border rounded px-2.5 py-1.5 opacity-60">
                            <StatusIndicator status={s.health} />
                            <span className="text-[11px] text-muted-foreground">{s.name}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Event timeline */}
                    <div>
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">Event timeline</p>
                      <div className="relative">
                        {incidentTimeline.map((item, i) => (
                          <div key={i} className="flex gap-3 pb-3 last:pb-0">
                            <div className="flex flex-col items-center">
                              <div className={cn(
                                'h-2.5 w-2.5 rounded-full shrink-0 mt-1',
                                item.level === 'detection' ? 'bg-status-warning' : item.level === 'analysis' ? 'bg-accent' : 'bg-status-healthy'
                              )} />
                              {i < incidentTimeline.length - 1 && <div className="w-px flex-1 bg-border mt-1" />}
                            </div>
                            <div className="pb-2">
                              <div className="flex items-center gap-2">
                                <span className="font-mono text-[10px] text-muted-foreground tabular-nums">{item.time}</span>
                                <span className="text-[11px] font-medium text-foreground">{item.event}</span>
                              </div>
                              <p className="text-[11px] text-muted-foreground mt-0.5">{item.detail}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Your Services Monitoring & Configuration */}
      <div className="bg-card border border-border rounded-lg shadow-atlas">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <h2 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Your Managed Services</h2>
          <span className="text-[10px] text-muted-foreground">Connected to TESMA</span>
        </div>
        <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { name: 'Core Banking API', id: 'SRV-001', health: 'healthy', metrics: { latency: '45ms', uptime: '99.99%', rpm: '12.4k' }, connected: true },
            { name: 'Payment Gateway', id: 'SRV-002', health: 'warning', metrics: { latency: '210ms', uptime: '99.95%', rpm: '8.2k' }, connected: true },
            { name: 'Customer Portal Backend', id: 'SRV-003', health: 'healthy', metrics: { latency: '85ms', uptime: '100%', rpm: '5.1k' }, connected: true },
            { name: 'Identity & Access Mgt', id: 'SRV-004', health: 'healthy', metrics: { latency: '32ms', uptime: '99.99%', rpm: '45.8k' }, connected: true },
            { name: 'Analytics Data Warehouse', id: 'SRV-005', health: 'healthy', metrics: { latency: 'N/A', uptime: '99.9%', rpm: 'N/A' }, connected: false },
          ].map((service) => (
            <div key={service.id} className="border border-border rounded-lg p-3 hover:bg-muted/10 transition-colors flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <StatusIndicator status={service.health as 'healthy' | 'warning' | 'critical'} />
                    <span className="text-[13px] font-semibold text-foreground">{service.name}</span>
                  </div>
                  <button className="text-muted-foreground hover:text-foreground transition-colors">
                    <Settings className="h-3.5 w-3.5" />
                  </button>
                </div>
                <div className="flex items-center gap-1.5 mb-3">
                  <span className="text-[10px] font-mono text-muted-foreground">{service.id}</span>
                  <span className="text-muted-foreground/30">•</span>
                  <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                    <Activity className="h-3 w-3" />
                    {service.connected ? 'TESMA Sync Active' : 'Unmanaged'}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div className="flex flex-col">
                    <span className="text-[9px] text-muted-foreground uppercase tracking-wider mb-0.5">Latency</span>
                    <span className="text-[11px] font-medium text-foreground">{service.metrics.latency}</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[9px] text-muted-foreground uppercase tracking-wider mb-0.5">Uptime</span>
                    <span className="text-[11px] font-medium text-foreground">{service.metrics.uptime}</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[9px] text-muted-foreground uppercase tracking-wider mb-0.5">Traffic</span>
                    <span className="text-[11px] font-medium text-foreground">{service.metrics.rpm}</span>
                  </div>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-border flex justify-between items-center">
                <button className="text-[11px] font-medium text-accent hover:text-accent/80 transition-colors flex items-center gap-1">
                  <Server className="h-3 w-3" />
                  View Telemetry
                </button>
                <button className="text-[11px] font-medium text-foreground bg-secondary/50 hover:bg-secondary px-2 py-1 rounded transition-colors">
                  Configure
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recently resolved */}
      <div className="bg-card border border-border rounded-lg shadow-atlas">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <h2 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Recently Resolved — Last 30 Days</h2>
          <span className="text-[10px] text-muted-foreground">5 incidents</span>
        </div>
        <div className="divide-y divide-border">
          {[
            { service: 'FraudDetection — Latency Spike', time: 'Today, 09:01', desc: 'Brief inference latency spike was detected and automatically resolved. No transactions were affected.', mttr: '4m 12s', escalation: 'Auto-resolved by L2' },
            { service: 'TicketingGateway — Certificate Renewal', time: 'Today, 09:30', desc: 'A security certificate was automatically renewed before expiration. No service impact.', mttr: '1m 45s', escalation: 'Auto-resolved (Class 1)' },
            { service: 'BillingEngine — Response Time', time: 'Yesterday, 15:22', desc: 'Brief performance degradation was detected and resolved. No transactions affected.', mttr: '3m 28s', escalation: 'L1 approved, auto-executed' },
            { service: 'AuthService — Memory Optimization', time: 'Yesterday, 11:05', desc: 'Routine memory optimization completed. No user impact.', mttr: '2m 15s', escalation: 'Auto-resolved (Class 1)' },
            { service: 'ReportingAPI — Connection Reset', time: 'Mar 23, 14:40', desc: 'Intermittent connection resets resolved by recycling stale connections.', mttr: '1m 52s', escalation: 'L1 approved, auto-executed' },
          ].map((item, i) => (
            <div key={i} className="px-4 py-3.5">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-status-healthy" />
                  <span className="text-[12px] font-medium text-foreground">{item.service}</span>
                </div>
                <span className="text-[10px] text-muted-foreground">{item.time}</span>
              </div>
              <p className="text-[12px] text-muted-foreground leading-relaxed pl-5.5 ml-[22px]">{item.desc}</p>
              <div className="flex items-center gap-3 mt-1.5 ml-[22px]">
                <span className="text-[10px] text-status-healthy font-medium">Resolved in {item.mttr}</span>
                <span className="text-[10px] text-muted-foreground">· {item.escalation}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
