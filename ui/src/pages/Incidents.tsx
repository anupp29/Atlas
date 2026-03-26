import { useState, useEffect, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { mockIncidents } from '@/data/mock';
import { PriorityBadge } from '@/components/atlas/PriorityBadge';
import { CountdownTimer } from '@/components/atlas/CountdownTimer';
import { IncidentBriefing } from '@/components/atlas/IncidentBriefing';
import { StatusIndicator } from '@/components/atlas/StatusIndicator';
import { cn } from '@/lib/utils';
import type { Incident } from '@/types/atlas';
import { ArrowRight, BrainCircuit, FileCode2, ShieldAlert, ShieldCheck, Bug, LayoutDashboard } from 'lucide-react';

export default function Incidents() {
  const { user } = useAuth();
  const role = user?.role || 'L2';
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);

  const filteredIncidents = useMemo(() => {
    return mockIncidents.filter((inc) => {
      if (role === 'L1') return inc.status === 'Awaiting L1';
      if (role === 'L2') return ['Awaiting L2', 'Escalated to L2', 'Awaiting L1'].includes(inc.status);
      if (role === 'L3') return inc.status !== 'Resolved';
      if (role === 'SDM') return true;
      return true;
    });
  }, [role]);

  useEffect(() => {
    if (filteredIncidents.length > 0) {
      setSelectedIncident(filteredIncidents[0]);
    } else {
      setSelectedIncident(null);
    }
  }, [role, filteredIncidents]);

  const timeSince = (ts: string) => {
    const mins = Math.floor((Date.now() - new Date(ts).getTime()) / 60000);
    if (mins < 1) return '<1m';
    if (mins < 60) return `${mins}m`;
    return `${Math.floor(mins / 60)}h ${mins % 60}m`;
  };

  const roleMeta = {
    L1: {
      label: 'L1 Triage Queue',
      subtitle: 'Fast approve-or-escalate decisions. Simplified briefing.',
      icon: ShieldCheck,
      accent: 'text-accent',
      panel: 'bg-accent/5 border-accent/15',
    },
    L2: {
      label: 'L2 Investigation Queue',
      subtitle: 'Full analysis workspace with dependency graphs, hypotheses, and modification controls.',
      icon: BrainCircuit,
      accent: 'text-accent',
      panel: 'bg-accent/5 border-accent/15',
    },
    L3: {
      label: 'L3 Engineering Queue',
      subtitle: 'Code-level debugging workspace with stack traces, config diffs, and runtime metrics.',
      icon: Bug,
      accent: 'text-status-critical',
      panel: 'bg-status-critical/5 border-status-critical/15',
    },
    SDM: {
      label: 'Portfolio Incident View',
      subtitle: 'Cross-role oversight. All incidents visible.',
      icon: LayoutDashboard,
      accent: 'text-foreground',
      panel: 'bg-muted/40 border-border',
    },
    CLIENT: {
      label: 'Incident View',
      subtitle: 'Read-only environment status.',
      icon: ShieldAlert,
      accent: 'text-foreground',
      panel: 'bg-muted/40 border-border',
    },
  } as const;

  const currentRoleMeta = roleMeta[role as keyof typeof roleMeta] || roleMeta.L2;
  const RoleIcon = currentRoleMeta.icon;

  return (
    <div className="flex gap-0 -m-6 h-[calc(100vh-56px)]">
      <div className={cn('border-r border-border bg-card overflow-hidden shrink-0 transition-all duration-200 flex flex-col', selectedIncident ? 'w-[360px]' : 'w-full max-w-5xl')}>
        <div className="px-4 py-3.5 border-b border-border shrink-0 bg-card space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h1 className="text-[15px] font-semibold text-foreground">Incident Queue</h1>
              <p className="text-[11px] text-muted-foreground mt-0.5">{filteredIncidents.length} incident{filteredIncidents.length !== 1 ? 's' : ''} in scope</p>
            </div>
            {selectedIncident && (
              <button onClick={() => setSelectedIncident(null)} className="text-[11px] text-accent hover:underline font-medium">
                Clear selection
              </button>
            )}
          </div>

          <div className={cn('rounded-lg border px-3 py-3 flex items-start gap-3', currentRoleMeta.panel)}>
            <div className="h-8 w-8 rounded-lg bg-card border border-border flex items-center justify-center shrink-0">
              <RoleIcon className={cn('h-4 w-4', currentRoleMeta.accent)} />
            </div>
            <div>
              <p className="text-[11px] font-semibold text-foreground uppercase tracking-wider">{currentRoleMeta.label}</p>
              <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed">{currentRoleMeta.subtitle}</p>
            </div>
          </div>
        </div>

        {filteredIncidents.length === 0 ? (
          <div className="flex-1 flex items-center justify-center px-5">
            <div className="text-center">
              <StatusIndicator status="healthy" className="h-3 w-3 mx-auto mb-2" />
              <p className="text-[13px] text-foreground font-medium">All clear</p>
              <p className="text-[11px] text-muted-foreground mt-0.5 max-w-[240px]">
                {role === 'L1' ? 'No incidents require L1 approval.' : role === 'L2' ? 'No incidents require L2 investigation.' : 'All monitored services operating within normal parameters.'}
              </p>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-auto">
            {filteredIncidents.map((incident) => {
              const roleCue = role === 'L1'
                ? { label: 'Decision needed', detail: 'Approve or escalate', icon: ShieldCheck, color: 'text-accent' }
                : role === 'L2'
                ? { label: 'Analysis ready', detail: `${incident.rootCause.confidence}% confidence · ${incident.historicalMatch?.similarity || 0}% match`, icon: BrainCircuit, color: 'text-accent' }
                : role === 'L3'
                ? { label: 'Engineering fault', detail: incident.deploymentCorrelation?.changeId || 'Config review required', icon: Bug, color: 'text-status-critical' }
                : { label: 'Oversight', detail: `${incident.status}`, icon: LayoutDashboard, color: 'text-foreground' };

              const CueIcon = roleCue.icon;

              return (
                <div
                  key={incident.id}
                  onClick={() => setSelectedIncident(incident)}
                  className={cn(
                    'px-4 py-3.5 border-b border-border cursor-pointer transition-colors duration-150',
                    selectedIncident?.id === incident.id ? 'bg-accent/[0.06] border-l-[3px] border-l-accent' : 'hover:bg-muted/40 border-l-[3px] border-l-transparent',
                    incident.status === 'Resolved' && 'opacity-60',
                  )}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <PriorityBadge priority={incident.priority} />
                      <span className="text-[13px] font-medium text-foreground">{incident.clientName}</span>
                      {incident.status === 'Resolved' && <CheckIcon className="h-3.5 w-3.5 text-status-healthy" />}
                    </div>
                    {incident.status !== 'Resolved' ? <CountdownTimer deadline={incident.slaDeadline} className="text-[11px]" /> : <span className="text-[10px] text-status-healthy font-medium">Resolved</span>}
                  </div>

                  <p className="text-[12px] text-muted-foreground mb-1.5 line-clamp-1">{incident.affectedServices.join(' · ')}</p>

                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-[10px] text-muted-foreground">{incident.id}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-muted-foreground">{timeSince(incident.detectedAt)} ago</span>
                      <span className={cn('text-[10px] font-medium px-1.5 py-0.5 rounded', incident.status.includes('Awaiting') ? 'bg-accent/8 text-accent' : incident.status.includes('Escalated') ? 'bg-status-warning/10 text-status-warning' : incident.status === 'Resolved' ? 'bg-status-healthy/10 text-status-healthy' : 'bg-muted text-muted-foreground')}>
                        {incident.status}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between rounded-md border border-border bg-muted/20 px-2.5 py-2">
                    <div className="flex items-center gap-2">
                      <CueIcon className={cn('h-3.5 w-3.5', roleCue.color)} />
                      <div>
                        <p className="text-[10px] font-medium text-foreground">{roleCue.label}</p>
                        <p className="text-[10px] text-muted-foreground">{roleCue.detail}</p>
                      </div>
                    </div>
                    <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />
                  </div>

                  {incident.mttr && <p className="text-[10px] text-status-healthy mt-1.5 font-medium">MTTR: {incident.mttr}</p>}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {selectedIncident && (
        <div className="flex-1 overflow-auto p-6 bg-background">
          <IncidentBriefing key={`${selectedIncident.id}-${role}`} incident={selectedIncident} />
        </div>
      )}
    </div>
  );
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="currentColor">
      <path fillRule="evenodd" d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z" />
    </svg>
  );
}
