import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { mockClients, mockIncidents, mockAuditLog } from '@/data/mock';
import { StatusIndicator } from '@/components/atlas/StatusIndicator';
import { ChevronDown, ChevronRight, CheckCircle2, Clock, Shield, AlertTriangle, ArrowUpRight, LogOut, Bell, Activity, BarChart3, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useNavigate } from 'react-router-dom';
import { CountdownTimer } from '@/components/atlas/CountdownTimer';

type PortalTab = 'overview' | 'incidents' | 'monitoring' | 'reports';

export default function ClientPortal() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const client = mockClients[0]; // In production, resolve from user's org
  const clientIncidents = mockIncidents.filter(i => i.clientId === client.id || i.clientName === client.name);
  const activeIncidents = clientIncidents.filter(i => i.status !== 'Resolved');
  const resolvedIncidents = clientIncidents.filter(i => i.status === 'Resolved');
  const [expandedIncident, setExpandedIncident] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<PortalTab>('overview');

  const clientAudit = mockAuditLog.filter(a => a.client === client.name).slice(0, 10);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const tabs: { id: PortalTab; label: string; icon: React.ElementType }[] = [
    { id: 'overview', label: 'Overview', icon: Activity },
    { id: 'incidents', label: 'Incidents', icon: AlertTriangle },
    { id: 'monitoring', label: 'Monitoring', icon: BarChart3 },
    { id: 'reports', label: 'Reports', icon: FileText },
  ];

  return (
    <div className="flex min-h-screen bg-background">
      {/* Client Sidebar */}
      <aside className="w-[240px] bg-primary flex flex-col shrink-0 h-screen sticky top-0">
        <div className="px-5 pt-5 pb-5">
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-lg bg-accent flex items-center justify-center">
              <Shield className="h-4.5 w-4.5 text-accent-foreground" />
            </div>
            <div>
              <h1 className="text-[15px] font-bold tracking-[0.15em] leading-none text-primary-foreground">ATLAS</h1>
              <p className="text-[9px] text-primary-foreground/40 mt-0.5 tracking-[0.08em] uppercase">Client Portal</p>
            </div>
          </div>
        </div>

        <div className="px-5 mb-1.5">
          <span className="text-[9px] text-primary-foreground/30 uppercase tracking-[0.12em] font-medium">Navigation</span>
        </div>

        <nav className="flex-1 px-3">
          <ul className="space-y-0.5">
            {tabs.map((tab) => (
              <li key={tab.id}>
                <button
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'w-full flex items-center gap-3 px-3 py-[9px] rounded-lg text-[13px] transition-colors duration-150',
                    activeTab === tab.id
                      ? 'bg-sidebar-accent text-primary-foreground font-medium'
                      : 'text-primary-foreground/50 hover:text-primary-foreground/80 hover:bg-sidebar-accent/40',
                  )}
                >
                  <tab.icon className="h-4 w-4" />
                  {tab.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        {/* User info + logout */}
        <div className="px-3 mb-2">
          <div className="px-3 py-2.5 rounded-lg bg-sidebar-accent/30">
            <div className="flex items-center gap-2.5 mb-2">
              <div className="h-7 w-7 rounded-full bg-accent flex items-center justify-center shrink-0">
                <span className="text-[10px] font-semibold text-accent-foreground">{user?.name?.split(' ').map(n => n[0]).join('')}</span>
              </div>
              <div className="min-w-0">
                <p className="text-[11px] font-medium text-primary-foreground truncate">{user?.name}</p>
                <p className="text-[9px] text-primary-foreground/40">Client Portal</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] text-primary-foreground/40 hover:text-primary-foreground/70 hover:bg-sidebar-accent/40 transition-colors"
            >
              <LogOut className="h-3 w-3" />
              Sign out
            </button>
          </div>
        </div>

        <div className="px-5 py-3 border-t border-sidebar-border">
          <div className="flex items-center gap-2">
            <StatusIndicator status={client.health} />
            <span className="text-[10px] text-primary-foreground/40">
              {client.health === 'healthy' ? 'All systems operational' : client.health === 'warning' ? 'Degraded performance' : 'Active incident'}
            </span>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-14 border-b border-border bg-card flex items-center justify-between px-5 shrink-0">
          <div className="flex items-center gap-3">
            <h2 className="text-[14px] font-semibold text-foreground">{client.name}</h2>
            <StatusIndicator status={client.health} />
            {activeIncidents.length > 0 && (
              <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-status-warning/10 text-status-warning">
                {activeIncidents.length} active issue{activeIncidents.length !== 1 ? 's' : ''}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-status-healthy live-dot" />
            <span>Live monitoring active</span>
          </div>
        </header>

        <main className="flex-1 p-6 overflow-auto">
          {activeTab === 'overview' && (
            <div className="max-w-5xl space-y-5">
              {/* KPIs */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <div className="bg-card border border-border rounded-lg p-4">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">SLA Compliance</p>
                  <p className="text-[24px] font-semibold text-foreground tabular-nums">{client.slaCompliance}%</p>
                  <p className="text-[10px] text-muted-foreground mt-1">Target: 99.0%</p>
                </div>
                <div className="bg-card border border-border rounded-lg p-4">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Active Issues</p>
                  <p className="text-[24px] font-semibold text-foreground tabular-nums">{activeIncidents.length}</p>
                  <p className="text-[10px] text-muted-foreground mt-1">{activeIncidents.length === 0 ? 'No active issues' : 'Being addressed'}</p>
                </div>
                <div className="bg-card border border-border rounded-lg p-4">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Autonomous Resolution</p>
                  <p className="text-[24px] font-semibold text-foreground tabular-nums">70%</p>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden max-w-[100px]">
                      <div className="h-full bg-status-healthy rounded-full" style={{ width: '70%' }} />
                    </div>
                  </div>
                </div>
                <div className="bg-card border border-border rounded-lg p-4">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Avg Resolution Time</p>
                  <p className="text-[24px] font-semibold text-status-healthy tabular-nums">3m 28s</p>
                  <p className="text-[10px] text-muted-foreground mt-1">Industry avg: 43 min</p>
                </div>
              </div>

              {/* Active issues with escalation transparency */}
              {activeIncidents.length > 0 && (
                <div className="bg-card border border-border rounded-lg">
                  <div className="px-4 py-3 border-b border-border flex items-center justify-between">
                    <h2 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Active Issues — Live Tracking</h2>
                    <span className="text-[10px] text-status-warning font-medium">{activeIncidents.length} in progress</span>
                  </div>
                  <div className="divide-y divide-border">
                    {activeIncidents.map(inc => (
                      <div key={inc.id} className="px-4 py-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <StatusIndicator status={inc.priority === 'P1' ? 'critical' : 'warning'} />
                            <span className="text-[13px] font-medium text-foreground">{inc.affectedServices.join(', ')}</span>
                            <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{inc.priority}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Clock className="h-3 w-3 text-muted-foreground" />
                            <CountdownTimer deadline={inc.slaDeadline} className="text-[11px]" />
                          </div>
                        </div>
                        <p className="text-[12px] text-muted-foreground leading-relaxed mb-3">
                          We detected a performance issue affecting {inc.affectedServices.join(' and ')}.
                          Our team is actively working on resolution. Estimated time: {inc.recommendedAction.estimatedTime}.
                        </p>

                        {/* Live escalation pipeline */}
                        <div className="bg-muted/20 rounded-lg p-3 border border-border">
                          <p className="text-[10px] font-semibold text-foreground uppercase tracking-wider mb-2">Resolution Pipeline</p>
                          <div className="flex items-center gap-2">
                            {['Detected', 'Analyzed', 'Root Cause Found', 'Team Assigned', 'Resolving'].map((stage, i) => {
                              const isComplete = i < 3;
                              const isCurrent = i === 3;
                              return (
                                <div key={stage} className="flex items-center gap-1.5">
                                  <div className={cn('h-5 w-5 rounded-full flex items-center justify-center text-[8px] font-bold',
                                    isComplete ? 'bg-status-healthy/10 text-status-healthy' : isCurrent ? 'bg-accent/10 text-accent atlas-pulse' : 'bg-muted text-muted-foreground'
                                  )}>
                                    {isComplete ? <CheckCircle2 className="h-3 w-3" /> : i + 1}
                                  </div>
                                  <span className={cn('text-[10px]', isComplete ? 'text-status-healthy' : isCurrent ? 'text-accent font-medium' : 'text-muted-foreground')}>{stage}</span>
                                  {i < 4 && <div className={cn('h-[1.5px] w-3', isComplete ? 'bg-status-healthy/30' : 'bg-border')} />}
                                </div>
                              );
                            })}
                          </div>
                        </div>

                        {/* Escalation history */}
                        <div className="mt-2 flex items-center gap-1.5 text-[10px] text-muted-foreground">
                          <span>Current status:</span>
                          <span className="font-medium text-accent">{inc.status}</span>
                          <span>·</span>
                          <span>Confidence: <span className="font-mono font-medium text-foreground">{inc.rootCause.confidence}%</span></span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recently resolved */}
              <div className="bg-card border border-border rounded-lg">
                <div className="px-4 py-3 border-b border-border">
                  <h2 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Recently Resolved</h2>
                </div>
                <div className="divide-y divide-border">
                  {resolvedIncidents.slice(0, 5).map((inc) => (
                    <div key={inc.id}>
                      <button
                        onClick={() => setExpandedIncident(expandedIncident === inc.id ? null : inc.id)}
                        className="w-full px-4 py-3.5 text-left hover:bg-muted/20 transition-colors"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            <CheckCircle2 className="h-3.5 w-3.5 text-status-healthy" />
                            <span className="text-[12px] font-medium text-foreground">{inc.affectedServices.join(', ')}</span>
                            <span className="text-[9px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{inc.priority}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] text-status-healthy font-medium">MTTR: {inc.mttr}</span>
                            {expandedIncident === inc.id ? <ChevronDown className="h-3 w-3 text-muted-foreground" /> : <ChevronRight className="h-3 w-3 text-muted-foreground" />}
                          </div>
                        </div>
                        <p className="text-[11px] text-muted-foreground line-clamp-1">{inc.summary}</p>
                      </button>

                      {expandedIncident === inc.id && (
                        <div className="px-4 pb-4">
                          <div className="bg-muted/20 rounded-lg p-3 border border-border space-y-2">
                            <p className="text-[10px] font-semibold text-foreground uppercase tracking-wider">How this was resolved</p>
                            <p className="text-[11px] text-foreground leading-relaxed">{inc.rootCause.diagnosis}</p>
                            <div className="flex items-center gap-1.5 flex-wrap">
                              {['ATLAS Detected', inc.approvedBy === 'ATLAS (Auto)' ? 'Auto-executed' : `${inc.approvedBy} approved`, 'Validated', 'Resolved'].map((step, j) => (
                                <div key={j} className="flex items-center gap-1.5">
                                  <div className="flex items-center gap-1 bg-card border border-border rounded px-2 py-1">
                                    <CheckCircle2 className="h-2.5 w-2.5 text-status-healthy" />
                                    <span className="text-[10px] text-foreground">{step}</span>
                                  </div>
                                  {j < 3 && <ArrowUpRight className="h-3 w-3 text-muted-foreground" />}
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                  {resolvedIncidents.length === 0 && (
                    <div className="px-4 py-8 text-center">
                      <CheckCircle2 className="h-5 w-5 text-status-healthy mx-auto mb-2" />
                      <p className="text-[12px] text-muted-foreground">No recent incidents.</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'incidents' && (
            <div className="max-w-5xl space-y-5">
              <h2 className="text-[16px] font-semibold text-foreground">All Incidents</h2>
              <div className="bg-card border border-border rounded-lg">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border bg-muted/30">
                      <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">ID</th>
                      <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Services</th>
                      <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Priority</th>
                      <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Status</th>
                      <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">MTTR</th>
                    </tr>
                  </thead>
                  <tbody>
                    {clientIncidents.map(inc => (
                      <tr key={inc.id} className="border-b border-border last:border-0">
                        <td className="px-4 py-2.5 font-mono text-[11px] text-muted-foreground">{inc.id}</td>
                        <td className="px-4 py-2.5 text-[12px] text-foreground">{inc.affectedServices.join(', ')}</td>
                        <td className="px-4 py-2.5">
                          <span className={cn('text-[10px] font-semibold px-1.5 py-0.5 rounded',
                            inc.priority === 'P1' ? 'bg-status-critical/10 text-status-critical' :
                            inc.priority === 'P2' ? 'bg-status-warning/10 text-status-warning' :
                            'bg-muted text-muted-foreground'
                          )}>{inc.priority}</span>
                        </td>
                        <td className="px-4 py-2.5">
                          <span className={cn('text-[10px] font-medium',
                            inc.status === 'Resolved' ? 'text-status-healthy' : 'text-status-warning'
                          )}>{inc.status}</span>
                        </td>
                        <td className="px-4 py-2.5 text-[11px] text-muted-foreground font-mono">{inc.mttr || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'monitoring' && (
            <div className="max-w-5xl space-y-5">
              <h2 className="text-[16px] font-semibold text-foreground">System Monitoring</h2>
              <p className="text-[12px] text-muted-foreground">Real-time health status of your monitored services.</p>

              {/* Service health grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {(clientIncidents[0]?.services || []).map(svc => (
                  <div key={svc.id} className="bg-card border border-border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <StatusIndicator status={svc.health} />
                        <span className="text-[13px] font-medium text-foreground">{svc.name}</span>
                      </div>
                      <span className={cn('text-[10px] font-semibold px-1.5 py-0.5 rounded',
                        svc.criticality === 'High' ? 'bg-status-critical/8 text-status-critical' : 'bg-muted text-muted-foreground'
                      )}>{svc.criticality}</span>
                    </div>
                    <p className="text-[11px] text-muted-foreground">{svc.technology}</p>
                    {svc.triggerMetric && (
                      <div className="mt-2 flex items-center justify-between text-[10px]">
                        <span className="text-muted-foreground">{svc.triggerMetric}</span>
                        <span className="font-mono text-foreground">{svc.triggerValue}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Activity timeline */}
              <div className="bg-card border border-border rounded-lg">
                <div className="px-4 py-3 border-b border-border">
                  <h3 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Activity Timeline</h3>
                </div>
                <div className="divide-y divide-border max-h-[400px] overflow-auto">
                  {clientAudit.map(entry => (
                    <div key={entry.id} className="px-4 py-2.5 flex items-start gap-3">
                      <div className={cn('h-5 w-5 rounded-full flex items-center justify-center shrink-0 mt-0.5',
                        entry.outcome === 'Success' ? 'bg-status-healthy/10' : 'bg-status-warning/10'
                      )}>
                        {entry.outcome === 'Success' ? <CheckCircle2 className="h-3 w-3 text-status-healthy" /> :
                         <AlertTriangle className="h-3 w-3 text-status-warning" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-[11px] text-foreground">
                          <span className="font-medium">{entry.actionType}</span>
                          {entry.actor === 'ATLAS' ? ' — automated' : ` — by ${entry.actor}`}
                        </p>
                        <p className="text-[10px] text-muted-foreground">{entry.incidentId} · {entry.timestamp}</p>
                      </div>
                      <span className={cn('text-[10px] font-medium', entry.outcome === 'Success' ? 'text-status-healthy' : 'text-status-warning')}>{entry.outcome}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'reports' && (
            <div className="max-w-5xl space-y-5">
              <h2 className="text-[16px] font-semibold text-foreground">Service Reports</h2>
              <p className="text-[12px] text-muted-foreground">Monthly performance and compliance reports for your environment.</p>
              <div className="bg-card border border-border rounded-lg p-5">
                <p className="text-[12px] text-foreground leading-relaxed">
                  Atos's autonomous monitoring has resolved <span className="font-semibold">14 of your last 20 incidents</span> automatically,
                  with an average resolution time of <span className="font-semibold">3 minutes 28 seconds</span>.
                  Your environment is continuously monitored across <span className="font-semibold">5 services</span>.
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-card border border-border rounded-lg p-4 text-center">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Total Incidents (30d)</p>
                  <p className="text-[28px] font-semibold text-foreground tabular-nums">{clientIncidents.length}</p>
                </div>
                <div className="bg-card border border-border rounded-lg p-4 text-center">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Resolution Rate</p>
                  <p className="text-[28px] font-semibold text-status-healthy tabular-nums">{resolvedIncidents.length > 0 ? Math.round((resolvedIncidents.length / clientIncidents.length) * 100) : 0}%</p>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
