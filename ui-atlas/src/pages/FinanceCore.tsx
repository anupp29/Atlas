export function FinanceCore() {
  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      {/* Header Stats Bar */}
      <div className="grid grid-cols-4 gap-px bg-outline-variant/15 border-b border-outline-variant/15 bg-surface">
        {[
          { label: 'Active Clusters', value: '1,204' },
          { label: 'CPU Load avg', value: '42.8%', color: 'text-tertiary' },
          { label: 'Memory Usage', value: '68.2 GB' },
          { label: 'Alerts (24H)', value: '12', color: 'text-error' },
        ].map((stat) => (
          <div key={stat.label} className="bg-surface p-4 flex flex-col">
            <span className="text-[10px] uppercase font-bold text-secondary tracking-widest mb-1">{stat.label}</span>
            <span className={`font-mono text-xl font-medium ${stat.color || 'text-primary'}`}>{stat.value}</span>
          </div>
        ))}
      </div>

      {/* Main Grid */}
      <div className="flex-1 flex overflow-hidden">
        {/* Live Log Stream */}
        <section className="flex-1 flex flex-col bg-surface-container-low border-r border-outline-variant/15">
          <div className="flex items-center justify-between px-4 py-2 bg-surface-container border-b border-outline-variant/15">
            <h3 className="font-headline text-[11px] font-bold uppercase tracking-wider text-primary">Live Operations Log</h3>
            <div className="flex gap-2">
              <span className="text-[10px] font-mono bg-surface-container-highest px-2 py-0.5 rounded text-secondary">Filter: ALL</span>
              <span className="text-[10px] font-mono bg-surface-container-highest px-2 py-0.5 rounded text-secondary">ID: 0x4f2a</span>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto font-mono text-[11px] leading-tight p-4 flex flex-col gap-1">
            {[
              { time: '12:44:59.001', level: 'INFO', msg: 'Initializing FinanceCore primary ledger sync...', color: 'text-tertiary' },
              { time: '12:45:00.124', level: 'INFO', msg: 'Connection established with node 192.168.1.45', color: 'text-tertiary' },
              { time: '12:45:02.887', level: 'ERR', msg: 'Timeout error: Authentication handshake failed for user: retail_admin_01', color: 'text-error', bg: 'bg-error/5' },
              { time: '12:45:03.012', level: 'INFO', msg: 'Retrying connection via secondary gateway...', color: 'text-tertiary' },
              { time: '12:45:05.441', level: 'WARN', msg: 'Latency spike detected in Frankfurt-1 region (145ms)', color: 'text-yellow-600', bg: 'bg-yellow-400/10' },
              { time: '12:45:06.112', level: 'INFO', msg: 'FinanceCore Database: Query optimization routine scheduled.', color: 'text-tertiary' },
              { time: '12:45:07.509', level: 'INFO', msg: 'Resource cleanup: 14 stale processes terminated.', color: 'text-tertiary' },
              { time: '12:45:08.002', level: 'ERR', msg: 'Storage alert: FinanceCore /var/log/app partition at 92% capacity.', color: 'text-error', bg: 'bg-error/5' },
            ].map((log, i) => (
              <div key={i} className={`flex gap-4 p-1 hover:bg-white/50 ${log.bg || ''}`}>
                <span className="text-slate-400 shrink-0">{log.time}</span>
                <span className={`w-12 font-bold ${log.color}`}>[{log.level}]</span>
                <span className="text-on-surface">{log.msg}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Activity Feed */}
        <section className="w-80 flex flex-col bg-surface border-l border-outline-variant/15">
          <div className="px-4 py-2 bg-surface-container border-b border-outline-variant/15">
            <h3 className="font-headline text-[11px] font-bold uppercase tracking-wider text-primary">System Events</h3>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {[
              { type: 'success', title: 'Node Deployment Success', desc: 'New validator node added to EMEA cluster.', time: '02m ago' },
              { type: 'error', title: 'Critical Security Alert', desc: 'Unauthorized login attempt from IP: 185.2.4.11 (Moscow, RU).', time: '14m ago' },
              { type: 'warning', title: 'Maintenance Warning', desc: 'Scheduled maintenance for RetailMax DB cluster starting in 4 hours.', time: '45m ago' },
              { type: 'success', title: 'Capacity Balanced', desc: 'Workload rebalancing completed for FinanceCore.', time: '1h ago' },
            ].map((event, i) => (
              <div key={i} className="p-3 bg-surface-container-lowest ghost-border rounded-sm">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`w-2 h-2 rounded-full ${
                    event.type === 'success' ? 'bg-tertiary' : event.type === 'error' ? 'bg-error' : 'bg-yellow-500'
                  }`}></span>
                  <span className={`text-[10px] font-bold uppercase tracking-tighter ${
                    event.type === 'success' ? 'text-primary' : event.type === 'error' ? 'text-error' : 'text-on-secondary-container'
                  }`}>{event.title}</span>
                </div>
                <p className="text-[11px] text-on-surface-variant leading-normal mb-2">{event.desc}</p>
                <div className="flex justify-between items-center">
                  <span className="text-[9px] font-mono text-slate-400">{event.time}</span>
                  <button className="text-[9px] font-bold text-primary hover:underline uppercase">
                    {event.type === 'error' ? 'Audit Log' : 'View'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Footer */}
      <footer className="h-8 bg-surface-container border-t border-outline-variant/15 px-6 flex items-center justify-between">
        <div className="flex items-center gap-4 text-[9px] font-mono text-slate-500">
          <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-tertiary"></span> SYSTEM NOMINAL</span>
          <span>SESSION: ATOS-0089-PRD</span>
          <span>UPTIME: 142D 04H 12M</span>
        </div>
        <div className="flex items-center gap-4 text-[9px] font-mono text-slate-500 uppercase tracking-widest">
          <span>Build v4.2.0-STABLE</span>
          <span className="text-primary font-bold">FinanceCore Context Active</span>
        </div>
      </footer>
    </div>
  );
}
