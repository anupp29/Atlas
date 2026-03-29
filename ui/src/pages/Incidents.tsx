import { useState, useMemo, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useSearchParams } from 'react-router-dom';
import { PriorityBadge } from '@/components/atlas/PriorityBadge';
import { CountdownTimer } from '@/components/atlas/CountdownTimer';
import { IncidentBriefing } from '@/components/atlas/IncidentBriefing';
import { StatusIndicator } from '@/components/atlas/StatusIndicator';
import { cn } from '@/lib/utils';
import type { Incident } from '@/types/atlas';
import { ArrowLeft, BrainCircuit, ShieldCheck, Terminal, Activity, ShieldAlert, Loader2, Search, AlertTriangle, RefreshCw, Wifi, WifiOff } from 'lucide-react';
import { useAtlasData } from '@/contexts/AtlasDataContext';
import { useQueryClient } from '@tanstack/react-query';
import { Input } from '@/components/ui/input';

export default function Incidents() {
  const { user } = useAuth();
  const role = user?.role || 'L2';
  const { incidents, clients, isLoading, isError, backendConnected, lastUpdated } = useAtlasData();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedClientId = searchParams.get('client');
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [secondsSinceUpdate, setSecondsSinceUpdate] = useState(0);
  const queryClient = useQueryClient();

  // Debounce search input — 200ms
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 200);
    return () => clearTimeout(t);
  }, [search]);

  // Tick seconds-since-update every second
  useEffect(() => {
    if (!lastUpdated) return;
    const interval = setInterval(() => {
      setSecondsSinceUpdate(Math.floor((Date.now() - lastUpdated.getTime()) / 1000));
    }, 1000);
    setSecondsSinceUpdate(0);
    return () => clearInterval(interval);
  }, [lastUpdated]);
  const selectedClient = selectedClientId ? clients.find(c => c.id === selectedClientId) : null;

  const filteredIncidents = useMemo(() => {
    let all = incidents;
    if (selectedClientId) all = all.filter(i => i.clientId === selectedClientId);
    all = all.filter((inc) => {
      if (role === 'L1') return inc.status === 'Awaiting L1';
      if (role === 'L2') return ['Awaiting L2', 'Escalated to L2', 'ATLAS Analyzing'].includes(inc.status);
      if (role === 'L3') return ['Awaiting L3', 'Escalated to L3', 'L3 Manual Resolution'].includes(inc.status) || (inc.status !== 'Resolved' && inc.priority === 'P1');
      return true; // SDM, CLIENT see all
    });
    if (search) {
      const q = debouncedSearch.toLowerCase();
      all = all.filter(i =>
        i.id.toLowerCase().includes(q) ||
        i.clientName.toLowerCase().includes(q) ||
        i.affectedServices.some(s => s.toLowerCase().includes(q)) ||
        i.summary.toLowerCase().includes(q),
      );
    }
    return all;
  }, [role, selectedClientId, incidents, debouncedSearch]);

  const roleConfig = {
    L1: { title: 'L1 Triage Queue', subtitle: 'Validate AI recommendations. Approve or escalate.', icon: ShieldCheck, accentClass: 'bg-status-healthy/8 border-status-healthy/20 text-status-healthy' },
    L2: { title: 'L2 Investigation Queue', subtitle: 'Root cause analysis, confidence scoring, parameter modification.', icon: BrainCircuit, accentClass: 'bg-accent/8 border-accent/20 text-accent' },
    L3: { title: 'L3 Engineering Queue', subtitle: 'Code-level debugging, configuration diffs, manual override.', icon: Terminal, accentClass: 'bg-status-critical/8 border-status-critical/20 text-status-critical' },
    SDM: { title: 'Portfolio Incidents', subtitle: 'Cross-client oversight — all active and resolved incidents.', icon: Activity, accentClass: 'bg-primary/8 border-primary/20 text-primary' },
    CLIENT: { title: 'Active Issues', subtitle: 'Read-only service transparency view.', icon: ShieldAlert, accentClass: 'bg-muted border-border text-muted-foreground' },
  } as const;

  const config = roleConfig[role as keyof typeof roleConfig] || roleConfig.L2;
  const RoleIcon = config.icon;

  const renderQueueItem = (incident: Incident) => {
    const isSelected = selectedIncident?.id === incident.id;
    const isResolved = incident.status === 'Resolved';
    const isActive = !isResolved;

    return (
      <div
        key={incident.id}
        onClick={() => setSelectedIncident(incident)}
        className={cn(
          'px-4 py-3 border-b border-border cursor-pointer transition-all duration-150',
          isSelected ? 'bg-muted/40 border-l-[3px] border-l-accent' : 'hover:bg-muted/20 border-l-[3px] border-l-transparent',
          isResolved && 'opacity-60',
        )}
      >
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-2">
            <PriorityBadge priority={incident.priority} />
            <span className="text-[13px] font-medium text-foreground">{incident.clientName}</span>
          </div>
          {isActive
            ? <CountdownTimer deadline={incident.slaDeadline} className="text-[11px]" />
            : <span className="text-[10px] text-status-healthy font-medium">{incident.mttr || 'Resolved'}</span>}
        </div>
        <p className="text-[12px] text-muted-foreground mb-1.5 line-clamp-1">{incident.affectedServices.join(' · ')}</p>
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] text-muted-foreground">{incident.id}</span>
          <span className={cn('text-[10px] font-medium px-1.5 py-0.5 rounded',
            incident.status === 'Resolved' ? 'bg-status-healthy/10 text-status-healthy' :
            incident.status.includes('Awaiting') || incident.status === 'ATLAS Analyzing' ? 'bg-accent/8 text-accent' :
            incident.status === 'Executing' ? 'bg-status-healthy/10 text-status-healthy' :
            'bg-status-warning/10 text-status-warning',
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
            <div className="flex items-center gap-3 min-w-0">
              {selectedClientId && (
                <button onClick={() => { setSearchParams({}); setSelectedIncident(null); }} className="text-[11px] text-accent hover:underline font-medium flex items-center gap-1 shrink-0">
                  <ArrowLeft className="h-3 w-3" /> All clients
                </button>
              )}
              <div className="min-w-0">
                <h1 className="text-[15px] font-semibold text-foreground truncate">
                  {selectedClient ? `${selectedClient.name} — ${config.title}` : config.title}
                </h1>
                <div className="flex items-center gap-2 mt-0.5">
                  {isLoading ? (
                    <span className="flex items-center gap-1 text-[11px] text-muted-foreground"><Loader2 className="h-2.5 w-2.5 animate-spin" /> Loading…</span>
                  ) : isError ? (
                    <span className="flex items-center gap-1 text-[11px] text-status-warning"><AlertTriangle className="h-2.5 w-2.5" /> Demo mode</span>
                  ) : (
                    <span className="text-[11px] text-muted-foreground">
                      {filteredIncidents.length} incident{filteredIncidents.length !== 1 ? 's' : ''}
                    </span>
                  )}
                  {backendConnected && (
                    <span className="flex items-center gap-1 text-[10px] text-status-healthy">
                      <Wifi className="h-2.5 w-2.5" /> live
                    </span>
                  )}
                  {!backendConnected && !isLoading && (
                    <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                      <WifiOff className="h-2.5 w-2.5" /> demo
                    </span>
                  )}
                  {lastUpdated && backendConnected && (
                    <span className="text-[9px] text-muted-foreground/60">
                      · updated {secondsSinceUpdate}s ago
                    </span>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {isError && (
                <button
                  onClick={() => queryClient.invalidateQueries({ queryKey: ['atlas', 'active-incidents'] })}
                  className="text-[10px] text-muted-foreground hover:text-foreground flex items-center gap-1"
                >
                  <RefreshCw className="h-3 w-3" />
                </button>
              )}
              {selectedIncident && (
                <button onClick={() => setSelectedIncident(null)} className="text-[11px] text-accent hover:underline font-medium">Clear</button>
              )}
            </div>
          </div>

          <div className={cn('rounded-lg border px-3 py-2.5 flex items-center gap-3', config.accentClass)}>
            <RoleIcon className="h-4 w-4 shrink-0" />
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider">{config.title}</p>
              <p className="text-[10px] opacity-75 mt-0.5">{config.subtitle}</p>
            </div>
          </div>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              placeholder="Search by ID, client, service…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 h-8 text-[11px]"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mx-auto mb-2" />
              <p className="text-[12px] text-muted-foreground">Loading incidents…</p>
            </div>
          </div>
        ) : filteredIncidents.length === 0 ? (
          <div className="flex-1 flex items-center justify-center px-5">
            <div className="text-center">
              <StatusIndicator status="healthy" className="h-3 w-3 mx-auto mb-2" />
              <p className="text-[13px] text-foreground font-medium">
                {search ? 'No matches' : 'All clear'}
              </p>
              <p className="text-[11px] text-muted-foreground mt-0.5 max-w-[240px]">
                {search ? `No incidents match "${search}"` :
                 role === 'L1' ? 'No incidents require L1 triage.' :
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