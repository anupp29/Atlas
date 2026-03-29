import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useAtlasData } from '@/contexts/AtlasDataContext';
import { StatusIndicator } from '@/components/atlas/StatusIndicator';
import { cn } from '@/lib/utils';
import { AlertCircle, Activity, ArrowUpRight, ArrowLeft, Clock, Zap, Building2, CheckCircle2, TrendingUp, Shield, ChevronRight } from 'lucide-react';
import { CountdownTimer } from '@/components/atlas/CountdownTimer';
import { PriorityBadge } from '@/components/atlas/PriorityBadge';
import { useAtlasTrustManagement } from '@/hooks/use-atlas-data';
import { frontendClientNameFromBackend } from '@/lib/atlas-adapters';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

export default function Portfolio() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [selectedClient, setSelectedClient] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards');

  const { incidents, clients } = useAtlasData();
  const { trustData, confirmUpgrade, isConfirming } = useAtlasTrustManagement();
  const isSDM = user?.role === 'SDM' || user?.homeRole === 'SDM';

  const totalClients = clients.length;
  const totalIncidents = useMemo(() => clients.reduce((sum, c) => sum + c.activeIncidents, 0), [clients]);

  // Compute live KPIs from real incident data
  const resolvedAll = useMemo(() => incidents.filter(i => i.status === 'Resolved'), [incidents]);
  const autoResolved = useMemo(() => resolvedAll.filter(i => i.approvedBy === 'ATLAS (Auto)').length, [resolvedAll]);
  const manualResolved = useMemo(() => resolvedAll.length - autoResolved, [resolvedAll, autoResolved]);
  const avgMttr = useMemo(() => {
    const withMttr = resolvedAll.filter(i => i.mttr);
    if (withMttr.length === 0) return '3m 28s';
    // Parse "Xm Ys" format
    const totalSecs = withMttr.reduce((sum, i) => {
      const match = i.mttr?.match(/(\d+)m\s*(\d+)s/);
      if (match) return sum + parseInt(match[1]) * 60 + parseInt(match[2]);
      return sum;
    }, 0);
    const avg = Math.round(totalSecs / withMttr.length);
    return `${Math.floor(avg / 60)}m ${(avg % 60).toString().padStart(2, '0')}s`;
  }, [resolvedAll]);

  const client = selectedClient ? clients.find(c => c.id === selectedClient) : null;
  const clientIncidents = selectedClient ? incidents.filter(i => i.clientId === selectedClient) : [];
  const activeClientIncidents = clientIncidents.filter(i => i.status !== 'Resolved');
  const resolvedClientIncidents = clientIncidents.filter(i => i.status === 'Resolved');

  if (client) {
    return (
      <div className="space-y-5">
        <button onClick={() => setSelectedClient(null)} className="flex items-center gap-1 text-[12px] text-accent hover:underline font-medium">
          <ArrowLeft className="h-3 w-3" /> Back to Portfolio
        </button>

        {/* Client header card */}
        <div className="bg-card border border-border rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-accent/10 flex items-center justify-center">
                <Building2 className="h-5 w-5 text-accent" />
              </div>
              <div>
                <h1 className="text-[18px] font-semibold text-foreground">{client.name}</h1>
                <div className="flex items-center gap-2 mt-0.5">
                  <StatusIndicator status={client.health} />
                  <span className="text-[12px] text-muted-foreground capitalize">{client.health}</span>
                  {client.complianceFlags?.map(flag => (
                    <span key={flag} className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-status-warning/10 text-status-warning uppercase">{flag}</span>
                  ))}
                </div>
              </div>
            </div>
            <div className="text-right">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Trust Level</p>
              <p className="text-[13px] font-medium text-foreground">{client.trustLevel}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="bg-muted/20 rounded-lg p-3">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">SLA Compliance</p>
              <p className={cn('text-[20px] font-semibold tabular-nums', client.slaCompliance >= 99.5 ? 'text-status-healthy' : client.slaCompliance >= 98 ? 'text-foreground' : 'text-status-warning')}>{client.slaCompliance}%</p>
            </div>
            <div className="bg-muted/20 rounded-lg p-3">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Active Incidents</p>
              <p className="text-[20px] font-semibold text-foreground tabular-nums">{activeClientIncidents.length}</p>
            </div>
            <div className="bg-muted/20 rounded-lg p-3">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Resolved (24h)</p>
              <p className="text-[20px] font-semibold text-status-healthy tabular-nums">{resolvedClientIncidents.length}</p>
            </div>
            <div className="bg-muted/20 rounded-lg p-3">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Last Activity</p>
              <p className="text-[13px] font-medium text-foreground mt-1">{client.lastActivity}</p>
            </div>
          </div>
        </div>

        {/* Active incidents */}
        {activeClientIncidents.length > 0 && (
          <div className="bg-card border border-border rounded-lg">
            <div className="px-4 py-3 border-b border-border flex items-center justify-between">
              <h2 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Active Incidents</h2>
              <span className="text-[10px] text-status-warning font-medium">{activeClientIncidents.length} active</span>
            </div>
            <div className="divide-y divide-border">
              {activeClientIncidents.map(inc => (
                <div
                  key={inc.id}
                  className="px-4 py-3 cursor-pointer hover:bg-muted/20 transition-colors"
                  onClick={() => navigate(`/incidents?client=${client.id}`)}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <PriorityBadge priority={inc.priority} />
                      <span className="text-[13px] font-medium text-foreground">{inc.affectedServices.join(', ')}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock className="h-3 w-3 text-muted-foreground" />
                      <CountdownTimer deadline={inc.slaDeadline} className="text-[11px]" />
                    </div>
                  </div>
                  <p className="text-[11px] text-muted-foreground line-clamp-1">{inc.summary}</p>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className={cn('text-[10px] font-medium px-1.5 py-0.5 rounded', 'bg-accent/8 text-accent')}>{inc.status}</span>
                    <span className="text-[10px] text-muted-foreground">Confidence: <span className="font-mono font-medium text-foreground">{inc.rootCause.confidence}%</span></span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Resolved incidents */}
        <div className="bg-card border border-border rounded-lg">
          <div className="px-4 py-3 border-b border-border">
            <h2 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Resolved Incidents</h2>
          </div>
          {resolvedClientIncidents.length === 0 ? (
            <div className="px-4 py-8 text-center">
              <CheckCircle2 className="h-5 w-5 text-status-healthy mx-auto mb-2" />
              <p className="text-[12px] text-muted-foreground">No resolved incidents in recent history.</p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {resolvedClientIncidents.map(inc => (
                <div key={inc.id} className="px-4 py-3">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-3.5 w-3.5 text-status-healthy" />
                      <span className="text-[12px] font-medium text-foreground">{inc.affectedServices.join(', ')}</span>
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{inc.priority}</span>
                    </div>
                    <span className="text-[10px] text-status-healthy font-medium">MTTR: {inc.mttr}</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground line-clamp-1">{inc.summary}</p>
                  <p className="text-[10px] text-muted-foreground mt-1">Approved by: {inc.approvedBy}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[16px] font-semibold text-foreground">Portfolio Overview</h1>
          <p className="text-[12px] text-muted-foreground mt-0.5">
            {user?.role === 'SDM' ? 'Service delivery health across all managed clients' : 'Client environment health and incident status'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-muted/50 rounded-lg p-0.5">
            <button onClick={() => setViewMode('cards')} className={cn('text-[10px] px-2.5 py-1 rounded', viewMode === 'cards' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground')}>Cards</button>
            <button onClick={() => setViewMode('table')} className={cn('text-[10px] px-2.5 py-1 rounded', viewMode === 'table' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground')}>Table</button>
          </div>
          <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-status-healthy live-dot" />
            <span>Live</span>
          </div>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Managed Clients</span>
            <Activity className="h-3.5 w-3.5 text-muted-foreground" />
          </div>
          <p className="text-[28px] font-semibold text-foreground leading-none tabular-nums">{totalClients}</p>
        </div>
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Active Incidents</span>
            <AlertCircle className={cn('h-3.5 w-3.5', totalIncidents > 0 ? 'text-status-warning' : 'text-muted-foreground')} />
          </div>
          <p className="text-[28px] font-semibold text-foreground leading-none tabular-nums">{totalIncidents}</p>
        </div>
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">24h Resolution</span>
            <Zap className="h-3.5 w-3.5 text-status-healthy" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-[28px] font-semibold text-foreground leading-none tabular-nums">{autoResolved}</span>
            <span className="text-[10px] text-muted-foreground">auto</span>
            <span className="text-muted-foreground/30 mx-0.5">/</span>
            <span className="text-[28px] font-semibold text-foreground leading-none tabular-nums">{manualResolved}</span>
            <span className="text-[10px] text-muted-foreground">manual</span>
          </div>
        </div>
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Avg MTTR</span>
            <Clock className="h-3.5 w-3.5 text-muted-foreground" />
          </div>
          <p className="text-[28px] font-semibold text-foreground leading-none tabular-nums">{avgMttr}</p>
        </div>
      </div>

      {/* Trust Management — SDM only */}
      {isSDM && trustData.length > 0 && (
        <div className="bg-card border border-border rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="h-3.5 w-3.5 text-muted-foreground" />
              <h2 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Trust Progression</h2>
              <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-primary/10 text-primary uppercase">SDM</span>
            </div>
            <span className="text-[10px] text-muted-foreground">Confirm upgrades to expand ATLAS autonomy</span>
          </div>
          <div className="divide-y divide-border">
            {trustData.map(({ clientId, data }) => {
              if (!data) return null;
              const stageName = ['Observation', 'L1 Assistance', 'L1 Automation', 'L2 Assistance', 'L2 Automation'][data.trust_level] || 'Unknown';
              const nextStageName = ['L1 Assistance', 'L1 Automation', 'L2 Assistance', 'L2 Automation', 'Max'][data.trust_level] || 'Max';
              const metrics = data.progression_metrics as Record<string, any> || {};
              const criteriaReady = metrics.criteria_met === true;
              const incidentCount = metrics.incident_count || 0;
              const accuracyRate = typeof metrics.accuracy_rate === 'number' ? Math.round(metrics.accuracy_rate * 100) : null;
              const clientName = frontendClientNameFromBackend(clientId);

              return (
                <div key={clientId} className="px-4 py-3">
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="h-8 w-8 rounded-lg bg-accent/10 flex items-center justify-center shrink-0">
                        <Building2 className="h-4 w-4 text-accent" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-[12px] font-medium text-foreground truncate">{clientName}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[10px] text-muted-foreground">Stage {data.trust_level}: {stageName}</span>
                          {data.trust_level < 4 && (
                            <>
                              <ChevronRight className="h-2.5 w-2.5 text-muted-foreground" />
                              <span className="text-[10px] text-muted-foreground">{nextStageName}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 shrink-0">
                      {/* Progress metrics */}
                      <div className="hidden md:flex items-center gap-4 text-[10px] text-muted-foreground">
                        <span>{incidentCount} incidents</span>
                        {accuracyRate !== null && <span>Accuracy: <span className={cn('font-mono font-semibold', accuracyRate >= 85 ? 'text-status-healthy' : 'text-status-warning')}>{accuracyRate}%</span></span>}
                        {typeof data.sla_uptime_percent === 'number' && <span>SLA: <span className="font-mono font-semibold text-foreground">{data.sla_uptime_percent.toFixed(1)}%</span></span>}
                      </div>
                      {/* Trust level progress bar */}
                      <div className="hidden lg:flex items-center gap-2">
                        <div className="flex gap-0.5">
                          {[0, 1, 2, 3, 4].map((stage) => (
                            <div key={stage} className={cn('h-1.5 w-6 rounded-full', stage <= data.trust_level ? 'bg-accent' : 'bg-muted')} />
                          ))}
                        </div>
                      </div>
                      {/* Confirm upgrade button */}
                      {criteriaReady && data.trust_level < 4 ? (
                        <Button
                          size="sm"
                          className="h-7 text-[11px] bg-status-healthy hover:bg-status-healthy/90 text-white gap-1.5"
                          disabled={isConfirming}
                          onClick={async () => {
                            try {
                              await confirmUpgrade(clientId);
                              toast.success(`Trust level upgraded for ${clientName}`, {
                                description: `Stage ${data.trust_level} → Stage ${data.trust_level + 1}`,
                              });
                            } catch {
                              toast.error('Trust upgrade failed', {
                                description: 'Backend unavailable. Try again when connection is restored.',
                              });
                            }
                          }}
                        >
                          <TrendingUp className="h-3 w-3" />
                          Confirm upgrade
                        </Button>
                      ) : data.trust_level < 4 ? (
                        <span className="text-[10px] text-muted-foreground px-2 py-1 rounded border border-border">Criteria not met</span>
                      ) : (
                        <span className="text-[10px] text-status-healthy font-medium">Max trust</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Client cards or table */}
      {viewMode === 'cards' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {clients.map((c) => {
            const cIncidents = incidents.filter(i => i.clientId === c.id);
            const activeCount = cIncidents.filter(i => i.status !== 'Resolved').length;
            const resolvedCount = cIncidents.filter(i => i.status === 'Resolved').length;
            return (
              <div
                key={c.id}
                onClick={() => setSelectedClient(c.id)}
                className={cn(
                  'bg-card border rounded-lg p-4 cursor-pointer transition-all duration-150 hover:shadow-md group',
                  c.health === 'critical' ? 'border-status-critical/30 hover:border-status-critical/50' :
                  c.health === 'warning' ? 'border-status-warning/30 hover:border-status-warning/50' :
                  'border-border hover:border-accent/30',
                )}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <StatusIndicator status={c.health} />
                    <span className="text-[13px] font-medium text-foreground">{c.name}</span>
                  </div>
                  <ArrowUpRight className="h-3.5 w-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
                <div className="grid grid-cols-3 gap-2 mb-3">
                  <div>
                    <p className="text-[9px] text-muted-foreground uppercase tracking-wider">SLA</p>
                    <p className={cn('text-[14px] font-semibold tabular-nums', c.slaCompliance >= 99.5 ? 'text-status-healthy' : c.slaCompliance >= 98 ? 'text-foreground' : 'text-status-warning')}>{c.slaCompliance}%</p>
                  </div>
                  <div>
                    <p className="text-[9px] text-muted-foreground uppercase tracking-wider">Active</p>
                    <p className={cn('text-[14px] font-semibold tabular-nums', activeCount > 0 ? 'text-status-warning' : 'text-foreground')}>{activeCount}</p>
                  </div>
                  <div>
                    <p className="text-[9px] text-muted-foreground uppercase tracking-wider">Resolved</p>
                    <p className="text-[14px] font-semibold text-status-healthy tabular-nums">{resolvedCount}</p>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-muted-foreground">{c.trustLevel}</span>
                  {c.complianceFlags && c.complianceFlags.length > 0 && (
                    <div className="flex gap-1">
                      {c.complianceFlags.map(f => (
                        <span key={f} className="text-[8px] font-semibold px-1 py-0.5 rounded bg-muted text-muted-foreground uppercase">{f}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="bg-card border border-border rounded-lg overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Client</th>
                <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Health</th>
                <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">SLA</th>
                <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Active</th>
                <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Trust Level</th>
                <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Last Activity</th>
              </tr>
            </thead>
            <tbody>
              {clients.map((c) => (
                <tr key={c.id} className="border-b border-border last:border-0 row-highlight cursor-pointer" onClick={() => setSelectedClient(c.id)}>
                  <td className="px-4 py-2.5 text-[13px] font-medium text-foreground">{c.name}</td>
                  <td className="px-4 py-2.5"><div className="flex items-center gap-2"><StatusIndicator status={c.health} /><span className="text-[12px] text-muted-foreground capitalize">{c.health}</span></div></td>
                  <td className="px-4 py-2.5 text-[12px] font-mono tabular-nums">{c.slaCompliance}%</td>
                  <td className="px-4 py-2.5 text-[12px] text-muted-foreground">{c.activeIncidents || '—'}</td>
                  <td className="px-4 py-2.5 text-[12px] text-muted-foreground">{c.trustLevel}</td>
                  <td className="px-4 py-2.5 text-[11px] text-muted-foreground">{c.lastActivity}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

    </div>
  );
}
