import React, { useState } from 'react';
import { mockAuditLog } from '@/data/mock';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronRight, Download, Search } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function AuditLog() {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterClient, setFilterClient] = useState('all');
  const [filterAction, setFilterAction] = useState('all');

  const clients = [...new Set(mockAuditLog.map(e => e.client))];
  const actionTypes = [...new Set(mockAuditLog.map(e => e.actionType))];

  const filtered = mockAuditLog.filter(entry => {
    if (filterClient !== 'all' && entry.client !== filterClient) return false;
    if (filterAction !== 'all' && entry.actionType !== filterAction) return false;
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      return entry.incidentId.toLowerCase().includes(q) || entry.actor.toLowerCase().includes(q) || entry.client.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[16px] font-semibold text-foreground">Audit Log</h1>
          <p className="text-[12px] text-muted-foreground mt-0.5">
            Immutable record of all ATLAS and human actions — {filtered.length} entries
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="gap-1.5 text-[11px] h-7">
            <Download className="h-3 w-3" /> CSV
          </Button>
          <Button variant="outline" size="sm" className="gap-1.5 text-[11px] h-7">
            <Download className="h-3 w-3" /> PDF
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative">
          <Search className="absolute left-2 top-1.5 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Search..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-7 w-[200px] h-7 text-[11px]"
          />
        </div>
        <Select value={filterClient} onValueChange={setFilterClient}>
          <SelectTrigger className="w-[180px] h-7 text-[11px]">
            <SelectValue placeholder="All clients" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All clients</SelectItem>
            {clients.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={filterAction} onValueChange={setFilterAction}>
          <SelectTrigger className="w-[160px] h-7 text-[11px]">
            <SelectValue placeholder="All actions" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All actions</SelectItem>
            {actionTypes.map(a => <SelectItem key={a} value={a}>{a}</SelectItem>)}
          </SelectContent>
        </Select>
        {(filterClient !== 'all' || filterAction !== 'all' || searchTerm) && (
          <button className="text-[10px] text-accent hover:underline" onClick={() => { setFilterClient('all'); setFilterAction('all'); setSearchTerm(''); }}>
            Clear
          </button>
        )}
      </div>

      {/* Table */}
      <div className="bg-card border border-border rounded-lg shadow-atlas overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="w-7 px-2 py-2"></th>
              <th className="text-left px-3 py-2 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Time</th>
              <th className="text-left px-3 py-2 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Incident</th>
              <th className="text-left px-3 py-2 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Client</th>
              <th className="text-left px-3 py-2 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Action</th>
              <th className="text-left px-3 py-2 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Actor</th>
              <th className="text-left px-3 py-2 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Outcome</th>
              <th className="text-left px-3 py-2 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Conf.</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((entry) => (
              <React.Fragment key={entry.id}>
                <tr
                  className="border-b border-border row-highlight cursor-pointer"
                  onClick={() => setExpandedId(expandedId === entry.id ? null : entry.id)}
                >
                  <td className="w-7 px-2 py-2">
                    {entry.details ? (
                      expandedId === entry.id ? <ChevronDown className="h-3 w-3 text-muted-foreground" /> : <ChevronRight className="h-3 w-3 text-muted-foreground" />
                    ) : <span className="w-3" />}
                  </td>
                  <td className="px-3 py-2 font-mono text-[10px] text-muted-foreground tabular-nums whitespace-nowrap">{entry.timestamp}</td>
                  <td className="px-3 py-2 font-mono text-[11px] text-accent">{entry.incidentId}</td>
                  <td className="px-3 py-2 text-[11px] text-foreground">{entry.client}</td>
                  <td className="px-3 py-2 text-[11px] text-foreground">{entry.actionType}</td>
                  <td className="px-3 py-2 text-[11px] text-muted-foreground">
                    {entry.actor === 'ATLAS' ? <span className="font-mono text-accent text-[10px]">ATLAS</span> : entry.actor}
                  </td>
                  <td className="px-3 py-2">
                    <span className={cn('text-[10px] font-medium',
                      entry.outcome === 'Success' && 'text-status-healthy',
                      entry.outcome === 'Failed' && 'text-status-critical',
                      entry.outcome === 'Rolled Back' && 'text-status-warning',
                    )}>{entry.outcome}</span>
                  </td>
                  <td className="px-3 py-2 font-mono text-[10px] text-muted-foreground tabular-nums">
                    {entry.confidence ? `${entry.confidence}%` : '—'}
                  </td>
                </tr>
                {expandedId === entry.id && entry.details && (
                  <tr className="border-b border-border">
                    <td colSpan={8} className="bg-muted/20 px-6 py-4">
                      <div className="space-y-3 text-[11px] max-w-3xl">
                        <div>
                          <p className="font-semibold text-foreground text-[10px] uppercase tracking-wider mb-1">AI Reasoning Chain</p>
                          <p className="text-muted-foreground leading-relaxed">{entry.details.reasoningChain}</p>
                        </div>
                        {entry.details.vetoes.length > 0 && (
                          <div>
                            <p className="font-semibold text-foreground text-[10px] uppercase tracking-wider mb-1">Governance Vetoes</p>
                            {entry.details.vetoes.map((v, i) => <p key={i} className="text-status-warning">• {v}</p>)}
                          </div>
                        )}
                        <div>
                          <p className="font-semibold text-foreground text-[10px] uppercase tracking-wider mb-1">Playbook Steps Executed</p>
                          <ol className="list-decimal list-inside space-y-0.5">
                            {entry.details.playbookSteps.map((s, i) => <li key={i} className="text-muted-foreground">{s}</li>)}
                          </ol>
                        </div>
                        <div>
                          <p className="font-semibold text-foreground text-[10px] uppercase tracking-wider mb-1">Metrics at Decision Point</p>
                          <div className="flex gap-4">
                            {Object.entries(entry.details.metricValues).map(([k, v]) => (
                              <span key={k}>
                                <span className="text-muted-foreground">{k.replace(/_/g, ' ')}: </span>
                                <span className="font-mono font-medium text-foreground">{v}</span>
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="py-10 text-center">
            <p className="text-[12px] text-muted-foreground">No audit records match the current filters.</p>
          </div>
        )}
      </div>
    </div>
  );
}
