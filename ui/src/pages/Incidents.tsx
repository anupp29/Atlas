import { useState, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useSearchParams } from 'react-router-dom';
import { mockIncidents, mockClients } from '@/data/mock';
import { PriorityBadge } from '@/components/atlas/PriorityBadge';
import { CountdownTimer } from '@/components/atlas/CountdownTimer';
import { IncidentBriefing } from '@/components/atlas/IncidentBriefing';
import { StatusIndicator } from '@/components/atlas/StatusIndicator';
import { cn } from '@/lib/utils';
import type { Incident } from '@/types/atlas';
import { ArrowLeft, ArrowRight, BrainCircuit, FileCode2, ShieldCheck, Terminal, Activity, ShieldAlert } from 'lucide-react';

export default function Incidents() {
  const { user } = useAuth();
  const role = user?.role || 'L2';
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedClientId = searchParams.get('client');
  const selectedClient = selectedClientId ? mockClients.find(c => c.id === selectedClientId) : null;
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);

  const filteredIncidents = useMemo(() => {
    let incidents = mockIncidents;

    if (selectedClientId) {
      incidents = incidents.filter(i => i.clientId === selectedClientId);
    }

    // Strict escalation: L1 sees only Awaiting L1, L2 sees only Awaiting L2 / Escalated to L2
    return incidents.filter((inc) => {
      if (role === 'L1') return inc.status === 'Awaiting L1';
      if (role === 'L2') return ['Awaiting L2', 'Escalated to L2'].includes(inc.status);
      if (role === 'L3') return ['Awaiting L3', 'Escalated to L3'].includes(inc.status) || inc.status !== 'Resolved';
      if (role === 'SDM') return true;
      return true;
    });
  }, [role, selectedClientId]);

  const timeSince = (ts: string) => {
    const mins = Math.floor((Date.now() - new Date(ts).getTime()) / 60000);
    if (mins < 1) return '<1m';
    if (mins < 60) return `${mins}m`;
    return `${Math.floor(mins / 60)}h ${mins % 60}m`;
  };

  const roleConfig = {
    L1: { title: 'L1 Triage Queue', subtitle: 'Validate AI recommendations. Approve or escalate.', icon: ShieldCheck, accentClass: 'bg-status-healthy/8 border-status-healthy/20 text-status-healthy' },
    L2: { title: 'L2 Investigation Queue', subtitle: 'Root cause analysis, confidence scoring.', icon: BrainCircuit, accentClass: 'bg-accent/8 border-accent/20 text-accent' },
    L3: { title: 'L3 Engineering Queue', subtitle: 'Code-level debugging, configuration diffs.', icon: Terminal, accentClass: 'bg-status-critical/8 border-status-critical/20 text-status-critical' },
    SDM: { title: 'Portfolio Incidents', subtitle: 'Cross-client oversight.', icon: Activity, accentClass: 'bg-primary/8 border-primary/20 text-primary' },
    CLIENT: { title: 'Active Issues', subtitle: 'Read-only view.', icon: ShieldAlert, accentClass: 'bg-muted border-border text-muted-foreground' },
  } as const;

  const config = roleConfig[role as keyof typeof roleConfig] || roleConfig.L2;
  const RoleIcon = config.icon;

  const renderQueueItem = (incident: Incident) => {
    const isSelected = selectedIncident?.id === incident.id;
    const isResolved = incident.status === 'Resolved';

    return (
      <div
        key={incident.id}
        onClick={() => setSelectedIncident(incident)}
        className={cn(
          'px-4 py-3 border-b border-border cursor-pointer transition-all duration-150',
          isSelected ? 'bg-muted/40 border-l-[3px] border-l-accent' : 'hover:bg-muted/20 border-l-[3px] border-l-transparent',
          isResolved && 'opacity-50',
        )}
      >
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-2">
            <PriorityBadge priority={incident.priority} />
            <span className="text-[13px] font-medium text-foreground">{incident.clientName}</span>
          </div>
          {!isResolved ? <CountdownTimer deadline={incident.slaDeadline} className="text-[11px]" /> : <span className="text-[10px] text-status-healthy font-medium">{incident.mttr}</span>}
        </div>
        <p className="text-[12px] text-muted-foreground mb-1.5 line-clamp-1">{incident.affectedServices.join(' · ')}</p>
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] text-muted-foreground">{incident.id}</span>
          <span className={cn('text-[10px] font-medium px-1.5 py-0.5 rounded',
            incident.status === 'Resolved' ? 'bg-status-healthy/10 text-status-healthy' :
            incident.status.includes('Awaiting') ? 'bg-accent/8 text-accent' :
            'bg-status-warning/10 text-status-warning'
          )}>{incident.status}</span>
        </div>
      </div>
    );
  };

  return (
    <div className="flex gap-0 -m-6 h-[calc(100vh-56px)]">
      <div className={cn(
        'border-r border-border overflow-hidden shrink-0 transition-all duration-200 flex flex-col bg-card',
        selectedIncident ? 'w-[360px]' : 'w-full max-w-5xl',
      )}>
        <div className="px-4 py-3.5 border-b border-border shrink-0 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              {selectedClientId && (
                <button onClick={() => { setSearchParams({}); setSelectedIncident(null); }} className="text-[11px] text-accent hover:underline font-medium flex items-center gap-1">
                  <ArrowLeft className="h-3 w-3" /> All clients
                </button>
              )}
              <div>
                <h1 className="text-[15px] font-semibold text-foreground">
                  {selectedClient ? `${selectedClient.name} — ${config.title}` : config.title}
                </h1>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  {filteredIncidents.length} incident{filteredIncidents.length !== 1 ? 's' : ''} in scope
                </p>
              </div>
            </div>
            {selectedIncident && (
              <button onClick={() => setSelectedIncident(null)} className="text-[11px] text-accent hover:underline font-medium">Clear</button>
            )}
          </div>
          <div className={cn('rounded-lg border px-3 py-2.5 flex items-center gap-3', config.accentClass)}>
            <RoleIcon className="h-4 w-4 shrink-0" />
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider">{config.title}</p>
              <p className="text-[10px] opacity-75 mt-0.5">{config.subtitle}</p>
            </div>
          </div>
        </div>

        {filteredIncidents.length === 0 ? (
          <div className="flex-1 flex items-center justify-center px-5">
            <div className="text-center">
              <StatusIndicator status="healthy" className="h-3 w-3 mx-auto mb-2" />
              <p className="text-[13px] text-foreground font-medium">All clear</p>
              <p className="text-[11px] text-muted-foreground mt-0.5 max-w-[240px]">
                {role === 'L1' ? 'No incidents require L1 triage.' :
                 role === 'L2' ? 'No incidents escalated to L2.' :
                 role === 'L3' ? 'No engineering faults pending.' :
                 'All services operating normally.'}
              </p>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-auto">
            {filteredIncidents.map(renderQueueItem)}
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
