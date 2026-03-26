import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { mockClients, mockIncidents, mockActivityFeed } from '@/data/mock';
import { StatusIndicator } from '@/components/atlas/StatusIndicator';
import { ActivityFeed } from '@/components/atlas/ActivityFeed';
import { cn } from '@/lib/utils';
import { TrendingUp, AlertCircle, Activity, ArrowUpRight, Clock, Zap, Shield, BarChart3 } from 'lucide-react';

export default function Portfolio() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const totalClients = mockClients.length;
  const totalIncidents = mockClients.reduce((sum, c) => sum + c.activeIncidents, 0);
  const autoResolved = 14;
  const humanIntervention = 6;
  const avgMTTR = '3m 28s';

  const trustLevelOrder = ['Observation', 'L1 Assistance', 'L1 Automation', 'L2 Assistance', 'L2 Automation'];

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[16px] font-semibold text-foreground">Portfolio Overview</h1>
          <p className="text-[12px] text-muted-foreground mt-0.5">
            {user?.role === 'SDM' ? 'Service delivery health across all managed clients' : 'Client environment health and incident status'}
          </p>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
          <span className="h-1.5 w-1.5 rounded-full bg-status-healthy live-dot" />
          <span>Last updated: {new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}</span>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Managed Clients</span>
            <Activity className="h-3.5 w-3.5 text-muted-foreground" />
          </div>
          <p className="text-[28px] font-semibold text-foreground leading-none tabular-nums">{totalClients}</p>
          <p className="text-[10px] text-muted-foreground mt-1.5">All environments connected</p>
        </div>
        <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Active Incidents</span>
            <AlertCircle className={cn('h-3.5 w-3.5', totalIncidents > 0 ? 'text-status-warning' : 'text-muted-foreground')} />
          </div>
          <p className="text-[28px] font-semibold text-foreground leading-none tabular-nums">{totalIncidents}</p>
          <p className="text-[10px] text-muted-foreground mt-1.5">
            {mockIncidents.filter(i => i.priority === 'P1' && i.status !== 'Resolved').length} P1 · {mockIncidents.filter(i => i.priority === 'P2' && i.status !== 'Resolved').length} P2
          </p>
        </div>
        <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">24h Resolution</span>
            <Zap className="h-3.5 w-3.5 text-status-healthy" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-[28px] font-semibold text-foreground leading-none tabular-nums">{autoResolved}</span>
            <span className="text-[10px] text-muted-foreground">auto</span>
            <span className="text-muted-foreground/30 mx-0.5">/</span>
            <span className="text-[28px] font-semibold text-foreground leading-none tabular-nums">{humanIntervention}</span>
            <span className="text-[10px] text-muted-foreground">manual</span>
          </div>
          <p className="text-[10px] text-status-healthy mt-1.5 font-medium">70% autonomous resolution</p>
        </div>
        <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">Avg MTTR</span>
            <Clock className="h-3.5 w-3.5 text-muted-foreground" />
          </div>
          <p className="text-[28px] font-semibold text-foreground leading-none tabular-nums">{avgMTTR}</p>
          <p className="text-[10px] text-status-healthy mt-1.5 font-medium">10.2× faster than industry avg</p>
        </div>
        <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">SLA Avg</span>
            <BarChart3 className="h-3.5 w-3.5 text-muted-foreground" />
          </div>
          <p className="text-[28px] font-semibold text-foreground leading-none tabular-nums">
            {(mockClients.reduce((s, c) => s + c.slaCompliance, 0) / mockClients.length).toFixed(1)}%
          </p>
          <p className="text-[10px] text-muted-foreground mt-1.5">Across all clients</p>
        </div>
      </div>

      {/* Client table */}
      <div className="bg-card border border-border rounded-lg overflow-hidden shadow-atlas">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <h2 className="text-[13px] font-semibold text-foreground">Managed Clients</h2>
          <span className="text-[10px] text-muted-foreground">{totalClients} clients</span>
        </div>
        <div className="overflow-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Client</th>
                <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Health</th>
                <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Incidents</th>
                <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">SLA</th>
                <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Trust Level</th>
                <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Compliance</th>
                <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Last Activity</th>
              </tr>
            </thead>
            <tbody>
              {mockClients.map((client) => (
                <tr
                  key={client.id}
                  className="border-b border-border last:border-0 row-highlight cursor-pointer group"
                  onClick={() => navigate('/incidents')}
                >
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <span className="text-[13px] font-medium text-foreground">{client.name}</span>
                      <ArrowUpRight className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <StatusIndicator status={client.health} />
                      <span className="text-[12px] text-muted-foreground capitalize">{client.health}</span>
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-[12px] text-muted-foreground tabular-nums">{client.activeIncidents || '—'}</td>
                  <td className="px-4 py-2.5">
                    <span className={cn('text-[12px] font-mono tabular-nums', client.slaCompliance >= 99.5 ? 'text-status-healthy' : client.slaCompliance >= 98 ? 'text-foreground' : 'text-status-warning')}>
                      {client.slaCompliance}%
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <span className="text-[12px] text-muted-foreground">{client.trustLevel}</span>
                      <div className="flex gap-0.5">
                        {trustLevelOrder.map((_, i) => (
                          <div key={i} className={cn('h-1 w-3 rounded-full', i <= trustLevelOrder.indexOf(client.trustLevel) ? 'bg-accent' : 'bg-muted')} />
                        ))}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    {client.complianceFlags && client.complianceFlags.length > 0 ? (
                      <div className="flex gap-1">
                        {client.complianceFlags.map(flag => (
                          <span key={flag} className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-muted text-muted-foreground uppercase tracking-wide">{flag}</span>
                        ))}
                      </div>
                    ) : <span className="text-[12px] text-muted-foreground">—</span>}
                  </td>
                  <td className="px-4 py-2.5 text-[11px] text-muted-foreground">{client.lastActivity}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Mobile activity feed */}
      <div className="2xl:hidden bg-card border border-border rounded-lg shadow-atlas">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <h2 className="text-[13px] font-semibold text-foreground">Activity Feed</h2>
          <div className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-status-healthy live-dot" />
            <span className="text-[10px] text-muted-foreground">Live</span>
          </div>
        </div>
        <ActivityFeed entries={mockActivityFeed} />
      </div>
    </div>
  );
}
