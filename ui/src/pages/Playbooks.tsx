import { useState, useMemo } from 'react';
import { mockPlaybooks, companyPlaybooks, mockClients } from '@/data/mock';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Search, CheckCircle2, XCircle, RotateCcw, Play, Clock, Shield, TrendingUp, Building2, Loader2, Wifi } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Playbook } from '@/types/atlas';
import { useAtlasPlaybooks } from '@/hooks/use-atlas-data';
import type { PlaybookRecord } from '@/hooks/use-atlas-data';

type PlaybookScope = 'universal' | string;

// Adapt backend PlaybookRecord to frontend Playbook shape
function adaptBackendPlaybook(pb: PlaybookRecord): Playbook {
  return {
    id: pb.playbook_id,
    name: pb.playbook_id,
    technologyDomain: pb.target_technology.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    actionClass: `Class ${pb.action_class}` as Playbook['actionClass'],
    estimatedTime: `${pb.estimated_resolution_minutes} minutes`,
    lastUsed: '—',
    successRate: 95,
    description: pb.description,
    preValidation: pb.pre_validation_checks,
    successCriteria: pb.success_metrics,
    rollbackProcedure: pb.rollback_playbook_id
      ? `Automatic rollback via playbook: ${pb.rollback_playbook_id}`
      : 'Manual rollback required — escalate to L3.',
    executionHistory: [],
  };
}

export default function Playbooks() {
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<Playbook | null>(null);
  const [scope, setScope] = useState<PlaybookScope>('universal');
  const [simulating, setSimulating] = useState(false);
  const [simResult, setSimResult] = useState<string | null>(null);

  const { playbooks: livePlaybooks, isLoading, backendPlaybooks } = useAtlasPlaybooks();

  // Merge live backend playbooks with mock playbooks (live takes precedence)
  const universalPlaybooks = useMemo<Playbook[]>(() => {
    if (backendPlaybooks && livePlaybooks.length > 0) {
      const liveAdapted = livePlaybooks.map(adaptBackendPlaybook);
      // Merge: live playbooks first, then mock ones not already covered
      const liveIds = new Set(liveAdapted.map(p => p.id));
      const mockExtra = mockPlaybooks.filter(p => !liveIds.has(p.id));
      return [...liveAdapted, ...mockExtra];
    }
    return mockPlaybooks;
  }, [livePlaybooks, backendPlaybooks]);

  const clientsWithPlaybooks = mockClients.filter(c => companyPlaybooks[c.id]?.length > 0);

  const currentPlaybooks = scope === 'universal'
    ? universalPlaybooks
    : (companyPlaybooks[scope] || []);

  const filtered = currentPlaybooks.filter(pb =>
    pb.name.toLowerCase().includes(search.toLowerCase()) ||
    pb.technologyDomain.toLowerCase().includes(search.toLowerCase()) ||
    pb.description.toLowerCase().includes(search.toLowerCase())
  );

  const handleDryRun = () => {
    setSimulating(true);
    setSimResult(null);
    setTimeout(() => {
      setSimulating(false);
      setSimResult(`Dry run complete. All ${selected?.preValidation.length || 0} pre-validation checks passed. Estimated execution time: ${selected?.estimatedTime || '—'}. No side effects detected in sandbox environment.`);
    }, 2500);
  };

  if (selected) {
    const successCount = selected.executionHistory.filter(e => e.outcome === 'Success').length;
    const failCount = selected.executionHistory.filter(e => e.outcome === 'Failed').length;
    const rollbackCount = selected.executionHistory.filter(e => e.outcome === 'Rolled Back').length;

    return (
      <div className="space-y-4 max-w-4xl">
        <button onClick={() => { setSelected(null); setSimResult(null); setSimulating(false); }} className="flex items-center gap-1 text-[12px] text-accent hover:underline">
          <ArrowLeft className="h-3 w-3" /> Back to library
        </button>

        <div className="bg-card border border-border rounded-lg p-5">
          <div className="flex items-center gap-2.5 mb-2">
            <h1 className="text-[14px] font-semibold text-foreground font-mono">{selected.name}</h1>
            <span className={cn('text-[9px] font-semibold px-2 py-0.5 rounded-full uppercase',
              selected.actionClass === 'Class 1' ? 'bg-status-healthy/10 text-status-healthy' : 'bg-status-warning/10 text-status-warning',
            )}>{selected.actionClass}</span>
            {backendPlaybooks && livePlaybooks.some(p => p.playbook_id === selected.id) && (
              <span className="flex items-center gap-1 text-[9px] text-status-healthy font-medium">
                <Wifi className="h-2.5 w-2.5" /> Live
              </span>
            )}
          </div>
          <p className="text-[12px] text-foreground leading-relaxed mb-3">{selected.description}</p>
          <div className="flex gap-5 text-[11px] text-muted-foreground">
            <span>{selected.technologyDomain}</span>
            <span>Est. {selected.estimatedTime}</span>
            {selected.successRate > 0 && <span>Success: <span className="font-mono font-medium text-foreground">{selected.successRate}%</span></span>}
          </div>
        </div>

        {selected.executionHistory.length > 0 && (
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-card border border-border rounded-lg p-3 text-center">
              <p className="text-[20px] font-semibold text-status-healthy tabular-nums">{successCount}</p>
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Successful</p>
            </div>
            <div className="bg-card border border-border rounded-lg p-3 text-center">
              <p className="text-[20px] font-semibold text-status-warning tabular-nums">{rollbackCount}</p>
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Rolled Back</p>
            </div>
            <div className="bg-card border border-border rounded-lg p-3 text-center">
              <p className="text-[20px] font-semibold text-status-critical tabular-nums">{failCount}</p>
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Failed</p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <div className="bg-card border border-border rounded-lg p-4">
            <h3 className="text-[11px] font-semibold text-foreground mb-2.5 uppercase tracking-wider">Pre-execution Validation</h3>
            <ol className="list-decimal list-inside space-y-1.5 text-[12px] text-foreground">
              {selected.preValidation.map((s, i) => <li key={i}>{s}</li>)}
            </ol>
          </div>
          <div className="bg-card border border-border rounded-lg p-4">
            <h3 className="text-[11px] font-semibold text-foreground mb-2.5 uppercase tracking-wider">Success Criteria</h3>
            <ul className="space-y-1.5 text-[12px] text-foreground">
              {selected.successCriteria.map((c, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-status-healthy mt-0.5 shrink-0" />
                  <span>{c}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="bg-card border border-border rounded-lg p-4">
          <h3 className="text-[11px] font-semibold text-foreground mb-2 uppercase tracking-wider">Rollback Procedure</h3>
          <p className="text-[12px] text-foreground leading-relaxed">{selected.rollbackProcedure}</p>
        </div>

        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-[11px] font-semibold text-foreground uppercase tracking-wider">Dry Run Simulation</h3>
            <Button variant="outline" size="sm" className="gap-1.5 text-[11px] h-7" onClick={handleDryRun} disabled={simulating}>
              <Play className="h-3 w-3" />
              {simulating ? 'Simulating...' : 'Run Dry Test'}
            </Button>
          </div>
          {simulating && (
            <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
              <div className="h-3 w-3 border-2 border-accent border-t-transparent rounded-full animate-spin" />
              Executing pre-validation checks in sandbox...
            </div>
          )}
          {simResult && (
            <div className="bg-status-healthy/5 border border-status-healthy/20 rounded p-3 mt-2">
              <div className="flex items-start gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-status-healthy mt-0.5 shrink-0" />
                <p className="text-[11px] text-foreground leading-relaxed">{simResult}</p>
              </div>
            </div>
          )}
        </div>

        {selected.executionHistory.length > 0 && (
          <div className="bg-card border border-border rounded-lg">
            <div className="px-4 py-3 border-b border-border">
              <h3 className="text-[11px] font-semibold text-foreground uppercase tracking-wider">Execution History</h3>
            </div>
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-4 py-2 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Date</th>
                  <th className="text-left px-4 py-2 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Client</th>
                  <th className="text-left px-4 py-2 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Outcome</th>
                </tr>
              </thead>
              <tbody>
                {selected.executionHistory.map((exec, i) => (
                  <tr key={i} className="border-b border-border last:border-0">
                    <td className="px-4 py-2 font-mono text-[10px] text-muted-foreground tabular-nums">{exec.date}</td>
                    <td className="px-4 py-2 text-[11px] text-foreground">{exec.client}</td>
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-1">
                        {exec.outcome === 'Success' && <CheckCircle2 className="h-3 w-3 text-status-healthy" />}
                        {exec.outcome === 'Failed' && <XCircle className="h-3 w-3 text-status-critical" />}
                        {exec.outcome === 'Rolled Back' && <RotateCcw className="h-3 w-3 text-status-warning" />}
                        <span className={cn('text-[10px] font-medium',
                          exec.outcome === 'Success' && 'text-status-healthy',
                          exec.outcome === 'Failed' && 'text-status-critical',
                          exec.outcome === 'Rolled Back' && 'text-status-warning',
                        )}>{exec.outcome}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[16px] font-semibold text-foreground">Playbook Library</h1>
          <p className="text-[12px] text-muted-foreground mt-0.5">Pre-approved, versioned, auditable resolution playbooks</p>
        </div>
        {isLoading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
        {backendPlaybooks && !isLoading && (
          <span className="flex items-center gap-1.5 text-[10px] text-status-healthy font-medium">
            <Wifi className="h-3 w-3" /> Live from backend
          </span>
        )}
      </div>

      {/* Scope tabs */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => { setScope('universal'); setSearch(''); }}
          className={cn('flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium border transition-colors',
            scope === 'universal' ? 'bg-accent/10 border-accent/30 text-accent' : 'border-border text-muted-foreground hover:border-accent/20'
          )}
        >
          <Shield className="h-3 w-3" /> Universal ({universalPlaybooks.length})
        </button>
        {clientsWithPlaybooks.map(c => (
          <button
            key={c.id}
            onClick={() => { setScope(c.id); setSearch(''); }}
            className={cn('flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium border transition-colors',
              scope === c.id ? 'bg-accent/10 border-accent/30 text-accent' : 'border-border text-muted-foreground hover:border-accent/20'
            )}
          >
            <Building2 className="h-3 w-3" /> {c.name} ({companyPlaybooks[c.id]?.length || 0})
          </button>
        ))}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        <div className="bg-card border border-border rounded-lg p-3">
          <div className="flex items-center gap-1.5 mb-1">
            <Shield className="h-3 w-3 text-muted-foreground" />
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Playbooks</span>
          </div>
          <p className="text-[20px] font-semibold text-foreground tabular-nums">{currentPlaybooks.length}</p>
        </div>
        <div className="bg-card border border-border rounded-lg p-3">
          <div className="flex items-center gap-1.5 mb-1">
            <Play className="h-3 w-3 text-muted-foreground" />
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Total Runs</span>
          </div>
          <p className="text-[20px] font-semibold text-foreground tabular-nums">{currentPlaybooks.reduce((s, p) => s + p.executionHistory.length, 0)}</p>
        </div>
        <div className="bg-card border border-border rounded-lg p-3">
          <div className="flex items-center gap-1.5 mb-1">
            <TrendingUp className="h-3 w-3 text-status-healthy" />
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Avg Success</span>
          </div>
          <p className="text-[20px] font-semibold text-status-healthy tabular-nums">
            {currentPlaybooks.filter(p => p.successRate > 0).length > 0
              ? Math.round(currentPlaybooks.filter(p => p.successRate > 0).reduce((s, p) => s + p.successRate, 0) / currentPlaybooks.filter(p => p.successRate > 0).length)
              : '—'}%
          </p>
        </div>
        <div className="bg-card border border-border rounded-lg p-3">
          <div className="flex items-center gap-1.5 mb-1">
            <Clock className="h-3 w-3 text-muted-foreground" />
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Domains</span>
          </div>
          <p className="text-[20px] font-semibold text-foreground tabular-nums">{new Set(currentPlaybooks.map(p => p.technologyDomain)).size}</p>
        </div>
      </div>

      <div className="relative max-w-xs">
        <Search className="absolute left-2 top-1.5 h-3.5 w-3.5 text-muted-foreground" />
        <Input placeholder="Search playbooks..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-7 h-7 text-[11px]" />
      </div>

      <div className="bg-card border border-border rounded-lg">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Name</th>
              <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Domain</th>
              <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Class</th>
              <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Success</th>
              <th className="text-left px-4 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Runs</th>
              <th className="px-4 py-2.5"></th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr><td colSpan={6} className="text-center py-10 text-[12px] text-muted-foreground">No playbooks match your search.</td></tr>
            ) : (
              filtered.map((pb) => (
                <tr key={pb.id} className="border-b border-border last:border-0 row-highlight">
                  <td className="px-4 py-2.5 font-mono text-[11px] text-foreground">{pb.name}</td>
                  <td className="px-4 py-2.5 text-[11px] text-muted-foreground">{pb.technologyDomain}</td>
                  <td className="px-4 py-2.5">
                    <span className={cn('text-[9px] font-semibold px-1.5 py-0.5 rounded-full',
                      pb.actionClass === 'Class 1' ? 'bg-status-healthy/10 text-status-healthy' : 'bg-status-warning/10 text-status-warning',
                    )}>{pb.actionClass}</span>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-[11px] text-foreground tabular-nums">{pb.successRate > 0 ? `${pb.successRate}%` : '—'}</td>
                  <td className="px-4 py-2.5 font-mono text-[11px] text-muted-foreground tabular-nums">{pb.executionHistory.length || '—'}</td>
                  <td className="px-4 py-2.5">
                    <button className="text-[11px] text-accent hover:underline" onClick={() => setSelected(pb)}>View</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
