import React, { useState, useMemo } from 'react';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronRight, Download, Search, Loader2, AlertTriangle, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAtlasAuditLog } from '@/hooks/use-atlas-data';
import { useQueryClient } from '@tanstack/react-query';

function exportCsv(entries: ReturnType<typeof useAtlasAuditLog>['auditLog']) {
  const headers = ['Timestamp', 'Incident ID', 'Client', 'Action Type', 'Actor', 'Outcome', 'Confidence', 'Reasoning'];
  const escapeCsv = (v: string) => `"${v.replace(/"/g, '""')}"`;
  const rows = entries.map((e) => [
    e.timestamp,
    e.incidentId,
    e.client,
    e.actionType,
    e.actor,
    e.outcome,
    e.confidence ? `${e.confidence}%` : '',
    e.details?.reasoningChain || '',
  ].map(String).map(escapeCsv));
  const csv = [headers.map(escapeCsv), ...rows].map((r) => r.join(',')).join('\n');
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `atlas-audit-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function SkeletonRow() {
  return (
    <tr className="border-b border-border">
      <td className="w-7 px-2 py-2.5" />
      {[80, 100, 90, 120, 80, 70, 60, 40].map((w, i) => (
        <td key={i} className="px-3 py-2.5">
          <div className="h-3 rounded bg-muted animate-pulse" style={{ width: `${w}px` }} />
        </td>
      ))}
    </tr>
  );
}

function safeFormatTimestamp(ts: string): string {
  if (!ts) return '—';
  // Handle both ISO and space-separated formats
  const normalized = ts.includes('T') ? ts : ts.replace(' ', 'T');
  const d = new Date(normalized);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleString('en-GB', { hour12: false, dateStyle: 'short', timeStyle: 'medium' });
}

export default function AuditLog() {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterClient, setFilterClient] = useState('all');
  const [filterAction, setFilterAction] = useState('all');
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 25;

  const { auditLog, isLoading, isError } = useAtlasAuditLog();
  const queryClient = useQueryClient();

  const clients = useMemo(() => [...new Set(auditLog.map((e) => e.client))].sort(), [auditLog]);
  const actionTypes = useMemo(() => [...new Set(auditLog.map((e) => e.actionType))].sort(), [auditLog]);

  const filtered = useMemo(() => auditLog.filter((entry) => {
    if (filterClient !== 'all' && entry.client !== filterClient) return false;
    if (filterAction !== 'all' && entry.actionType !== filterAction) return false;
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      return (
        entry.incidentId.toLowerCase().includes(q) ||
        entry.actor.toLowerCase().includes(q) ||
        entry.client.toLowerCase().includes(q) ||
        entry.actionType.toLowerCase().includes(q)
      );
    }
    return true;
  }), [auditLog, filterClient, filterAction, searchTerm]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  // Reset page when filters change
  const handleFilterChange = (setter: (v: string) => void) => (v: string) => {
    setter(v);
    setPage(0);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[16px] font-semibold text-foreground">Audit Log</h1>
          <p className="text-[12px] text-muted-foreground mt-0.5">
            Immutable record of all ATLAS and human actions
            {isLoading ? (
              <span className="inline-flex items-center gap-1 ml-1"><Loader2 className="h-2.5 w-2.5 animate-spin" /> loading…</span>
            ) : isError ? (
              <span className="text-status-warning ml-1">— showing cached data</span>
            ) : (
              <span className="ml-1">— {filtered.length} entries</span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isError && (
            <Button
              variant="ghost"
              size="sm"
              className="gap-1.5 text-[11px] h-7 text-muted-foreground"
              onClick={() => queryClient.invalidateQueries({ queryKey: ['atlas', 'audit-log'] })}
            >
              <RefreshCw className="h-3 w-3" /> Retry
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 text-[11px] h-7"
            onClick={() => exportCsv(filtered)}
            disabled={filtered.length === 0}
          >
            <Download className="h-3 w-3" /> CSV
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative">
          <Search className="absolute left-2 top-1.5 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Search incidents, actors, clients…"
            value={searchTerm}
            onChange={(e) => { setSearchTerm(e.target.value); setPage(0); }}
            className="pl-7 w-[220px] h-7 text-[11px]"
          />
        </div>
        <Select value={filterClient} onValueChange={handleFilterChange(setFilterClient)}>
          <SelectTrigger className="w-[180px] h-7 text-[11px]">
            <SelectValue placeholder="All clients" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All clients</SelectItem>
            {clients.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={filterAction} onValueChange={handleFilterChange(setFilterAction)}>
          <SelectTrigger className="w-[160px] h-7 text-[11px]">
            <SelectValue placeholder="All actions" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All actions</SelectItem>
            {actionTypes.map((a) => <SelectItem key={a} value={a}>{a}</SelectItem>)}
          </SelectContent>
        </Select>
        {(filterClient !== 'all' || filterAction !== 'all' || searchTerm) && (
          <button
            className="text-[10px] text-accent hover:underline"
            onClick={() => { setFilterClient('all'); setFilterAction('all'); setSearchTerm(''); setPage(0); }}
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Error banner */}
      {isError && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-status-warning/5 border border-status-warning/20 text-[11px] text-status-warning">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          Backend unavailable — showing cached audit data. Live records may be missing.
        </div>
      )}

      {/* Table */}
      <div className="bg-card border border-border rounded-lg shadow-atlas overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border bg-muted/30">
              <th className="w-7 px-2 py-2.5" />
              <th className="text-left px-3 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Time</th>
              <th className="text-left px-3 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Incident</th>
              <th className="text-left px-3 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Client</th>
              <th className="text-left px-3 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Action</th>
              <th className="text-left px-3 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Actor</th>
              <th className="text-left px-3 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Outcome</th>
              <th className="text-left px-3 py-2.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Conf.</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} />)
            ) : paginated.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-12 text-center text-[12px] text-muted-foreground">
                  No audit records match the current filters.
                </td>
              </tr>
            ) : (
              paginated.map((entry) => (
                <React.Fragment key={entry.id}>
                  <tr
                    className="border-b border-border row-highlight cursor-pointer"
                    onClick={() => setExpandedId(expandedId === entry.id ? null : entry.id)}
                  >
                    <td className="w-7 px-2 py-2.5">
                      {entry.details ? (
                        expandedId === entry.id
                          ? <ChevronDown className="h-3 w-3 text-muted-foreground" />
                          : <ChevronRight className="h-3 w-3 text-muted-foreground" />
                      ) : <span className="w-3 inline-block" />}
                    </td>
                    <td className="px-3 py-2.5 font-mono text-[10px] text-muted-foreground tabular-nums whitespace-nowrap">
                      {safeFormatTimestamp(entry.timestamp)}
                    </td>
                    <td className="px-3 py-2.5 font-mono text-[11px] text-accent">{entry.incidentId}</td>
                    <td className="px-3 py-2.5 text-[11px] text-foreground">{entry.client}</td>
                    <td className="px-3 py-2.5 text-[11px] text-foreground">{entry.actionType}</td>
                    <td className="px-3 py-2.5 text-[11px] text-muted-foreground">
                      {entry.actor === 'ATLAS'
                        ? <span className="font-mono text-accent text-[10px] font-medium">ATLAS</span>
                        : entry.actor}
                    </td>
                    <td className="px-3 py-2.5">
                      <span className={cn('text-[10px] font-medium',
                        entry.outcome === 'Success' && 'text-status-healthy',
                        entry.outcome === 'Failed' && 'text-status-critical',
                        entry.outcome === 'Rolled Back' && 'text-status-warning',
                      )}>{entry.outcome}</span>
                    </td>
                    <td className="px-3 py-2.5 font-mono text-[10px] text-muted-foreground tabular-nums">
                      {entry.confidence ? `${entry.confidence}%` : '—'}
                    </td>
                  </tr>
                  {expandedId === entry.id && entry.details && (
                    <tr className="border-b border-border">
                      <td colSpan={8} className="bg-muted/20 px-6 py-4">
                        <div className="space-y-3 text-[11px] max-w-4xl">
                          <div>
                            <p className="font-semibold text-foreground text-[10px] uppercase tracking-wider mb-1.5">AI Reasoning Chain</p>
                            <p className="text-muted-foreground leading-relaxed">{entry.details.reasoningChain}</p>
                          </div>
                          {entry.details.vetoes.length > 0 && (
                            <div>
                              <p className="font-semibold text-foreground text-[10px] uppercase tracking-wider mb-1.5">Governance Vetoes Applied</p>
                              <div className="space-y-1">
                                {entry.details.vetoes.map((v, i) => (
                                  <p key={i} className="flex items-start gap-1.5 text-status-warning">
                                    <span className="shrink-0 mt-0.5">⚠</span> {v}
                                  </p>
                                ))}
                              </div>
                            </div>
                          )}
                          {entry.details.playbookSteps.length > 0 && (
                            <div>
                              <p className="font-semibold text-foreground text-[10px] uppercase tracking-wider mb-1.5">Execution Steps</p>
                              <ol className="list-decimal list-inside space-y-0.5">
                                {entry.details.playbookSteps.map((s, i) => (
                                  <li key={i} className="text-muted-foreground">{s}</li>
                                ))}
                              </ol>
                            </div>
                          )}
                          {Object.keys(entry.details.metricValues).length > 0 && (
                            <div>
                              <p className="font-semibold text-foreground text-[10px] uppercase tracking-wider mb-1.5">Metrics at Decision Point</p>
                              <div className="flex flex-wrap gap-4">
                                {Object.entries(entry.details.metricValues).map(([k, v]) => (
                                  <span key={k} className="text-[10px]">
                                    <span className="text-muted-foreground">{k.replace(/_/g, ' ')}: </span>
                                    <span className="font-mono font-medium text-foreground">{v}</span>
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))
            )}
          </tbody>
        </table>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-4 py-2.5 border-t border-border flex items-center justify-between">
            <span className="text-[10px] text-muted-foreground">
              Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, filtered.length)} of {filtered.length}
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="px-2 py-1 text-[10px] rounded border border-border text-muted-foreground hover:text-foreground disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Prev
              </button>
              {Array.from({ length: Math.min(totalPages, 5) }).map((_, i) => {
                const pageNum = Math.max(0, Math.min(page - 2, totalPages - 5)) + i;
                return (
                  <button
                    key={pageNum}
                    onClick={() => setPage(pageNum)}
                    className={cn(
                      'px-2 py-1 text-[10px] rounded border transition-colors',
                      pageNum === page
                        ? 'bg-accent text-accent-foreground border-accent'
                        : 'border-border text-muted-foreground hover:text-foreground',
                    )}
                  >
                    {pageNum + 1}
                  </button>
                );
              })}
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="px-2 py-1 text-[10px] rounded border border-border text-muted-foreground hover:text-foreground disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
