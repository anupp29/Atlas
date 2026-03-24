import { Link } from 'react-router-dom';

export function IncidentBriefing() {
  return (
    <div className="max-w-7xl mx-auto pb-20">
      {/* Header Section */}
      <div className="flex justify-between items-end mb-8">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="bg-error/10 text-error px-2 py-0.5 rounded-sm text-[10px] font-bold tracking-widest flex items-center gap-1">
              <span className="w-1.5 h-1.5 bg-error rounded-full animate-pulse"></span> SEV-1 CRITICAL
            </span>
            <span className="text-on-surface-variant font-mono text-[10px] tracking-tight">INC-2024-0814-TXN</span>
          </div>
          <h1 className="text-4xl font-black font-headline text-on-surface tracking-tighter uppercase leading-none">
            Active Briefing: <span className="text-primary">Payment Latency Spike</span>
          </h1>
        </div>
        <div className="flex gap-3">
          <div className="text-right mr-4">
            <p className="text-[10px] font-bold uppercase text-on-surface-variant mb-1 tracking-widest">SLA Countdown</p>
            <div className="font-mono text-3xl font-bold text-amber-500 leading-none">21:34</div>
          </div>
          <Link
            to="/incidents/l1-command"
            className="bg-primary text-white px-5 py-2 text-xs font-bold uppercase tracking-widest rounded shadow-md hover:bg-primary-container transition-colors flex items-center gap-2"
          >
            <span>Proceed to L1</span>
            <span className="material-symbols-outlined text-sm">arrow_forward</span>
          </Link>
        </div>
      </div>

      {/* Bento Layout Grid */}
      <div className="grid grid-cols-12 gap-6 items-start">
        {/* Left Column */}
        <div className="col-span-12 lg:col-span-8 space-y-6">
          {/* Situation Summary */}
          <div className="bg-surface-container-lowest p-6 rounded-lg ghost-border shadow-sm">
            <div className="flex items-center gap-2 mb-4 border-b border-surface-container-high pb-3">
              <span className="material-symbols-outlined text-primary">summarize</span>
              <h2 className="font-bold text-sm uppercase tracking-widest">Situation Summary</h2>
            </div>
            <p className="text-on-surface-variant text-sm leading-relaxed mb-4 font-medium">
              Unexpected 450ms latency spike detected in <span className="text-on-surface font-bold">PaymentAPI v2.4</span>. 
              Root cause appears to be a locked thread pool within the <span className="text-on-surface font-bold">TransactionDB</span> instance.
            </p>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-surface-container-low p-3 rounded">
                <p className="text-[9px] uppercase font-bold text-slate-500 mb-1">Impacted Users</p>
                <p className="font-mono text-xl font-bold text-on-surface">14.2k</p>
              </div>
              <div className="bg-surface-container-low p-3 rounded">
                <p className="text-[9px] uppercase font-bold text-slate-500 mb-1">Failed Txns</p>
                <p className="font-mono text-xl font-bold text-error">1,842</p>
              </div>
              <div className="bg-surface-container-low p-3 rounded">
                <p className="text-[9px] uppercase font-bold text-slate-500 mb-1">Avg Latency</p>
                <p className="font-mono text-xl font-bold text-amber-600">842ms</p>
              </div>
            </div>
          </div>

          {/* Recommended Actions */}
          <div className="bg-surface-container-lowest rounded-lg ghost-border overflow-hidden">
            <div className="bg-primary p-4 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-white">auto_awesome</span>
                <h2 className="font-bold text-sm uppercase tracking-widest text-white">Recommended Actions</h2>
              </div>
              <span className="text-[10px] font-mono text-on-primary-container font-bold px-2 py-0.5 bg-white/10 rounded">AI-POWERED INSIGHTS</span>
            </div>
            <div className="p-4 space-y-3">
              <div className="flex items-center justify-between p-3 bg-surface-container-low rounded border-l-4 border-primary">
                <div className="flex items-center gap-4">
                  <span className="material-symbols-outlined text-primary">restart_alt</span>
                  <div>
                    <p className="text-xs font-bold text-on-surface">Reboot PaymentAPI Clusters</p>
                    <p className="text-[10px] text-on-surface-variant">Estimated recovery time: 120s</p>
                  </div>
                </div>
                <Link to="/incidents/l1-command" className="bg-primary text-white px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest rounded hover:bg-primary-container transition-all">
                  EXECUTE
                </Link>
              </div>
              <div className="flex items-center justify-between p-3 bg-surface-container-low rounded border-l-4 border-slate-300 opacity-80">
                <div className="flex items-center gap-4">
                  <span className="material-symbols-outlined text-slate-500">alt_route</span>
                  <div>
                    <p className="text-xs font-bold text-on-surface">Reroute traffic to us-west-2</p>
                    <p className="text-[10px] text-on-surface-variant">Caution: Potential 50ms baseline increase</p>
                  </div>
                </div>
                <button className="border border-outline-variant text-slate-500 px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest rounded">REVIEW</button>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="col-span-12 lg:col-span-4 space-y-6">
          {/* Dependency Topology */}
          <div className="bg-surface-container-lowest p-6 rounded-lg ghost-border">
            <h3 className="font-bold text-xs uppercase tracking-widest mb-6 flex items-center gap-2">
              <span className="material-symbols-outlined text-on-surface-variant text-sm">account_tree</span>
              Dependency Topology
            </h3>
            <div className="relative h-64 flex flex-col items-center justify-between py-4">
              <div className="z-10 bg-white border border-outline-variant p-2 rounded shadow-sm w-32 text-center">
                <span className="text-[9px] font-bold text-slate-400 block mb-1">INGRESS</span>
                <span className="font-mono text-[10px] font-bold">CloudFront-Edge</span>
              </div>
              <div className="z-10 bg-white border-2 border-error p-2 rounded shadow-md w-36 text-center">
                <span className="text-[9px] font-bold text-error block mb-1">LATENCY CRITICAL</span>
                <span className="font-mono text-[10px] font-bold">PaymentAPI</span>
              </div>
              <div className="z-10 bg-white border-2 border-error p-2 rounded shadow-md w-36 text-center">
                <span className="text-[9px] font-bold text-error block mb-1">DEADLOCK DETECTED</span>
                <span className="font-mono text-[10px] font-bold">TransactionDB</span>
              </div>
            </div>
          </div>

          {/* Blast Radius */}
          <div className="bg-surface-container-lowest p-6 rounded-lg ghost-border">
            <h3 className="font-bold text-xs uppercase tracking-widest mb-4">Blast Radius</h3>
            <div className="space-y-4">
              {[
                { name: 'CHECKOUT MICROSERVICE', value: 88, color: 'bg-error' },
                { name: 'INVENTORY LOCKS', value: 42, color: 'bg-amber-500' },
                { name: 'AUTH PROVIDER', value: 2, color: 'bg-tertiary' },
              ].map((item) => (
                <div key={item.name}>
                  <div className="flex justify-between text-[10px] font-bold mb-1">
                    <span className="text-on-surface-variant">{item.name}</span>
                    <span className={item.value > 50 ? 'text-error font-mono' : 'text-amber-500 font-mono'}>{item.value}%</span>
                  </div>
                  <div className="h-1.5 w-full bg-surface-container-high rounded-full overflow-hidden">
                    <div className={`h-full ${item.color}`} style={{ width: `${item.value}%` }}></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Navigation FAB */}
      <Link
        to="/incidents/l1-command"
        className="fixed bottom-8 right-8 w-14 h-14 bg-gradient-to-br from-primary to-primary-container text-white rounded-full shadow-lg hover:shadow-xl active:scale-95 transition-all flex items-center justify-center"
      >
        <span className="material-symbols-outlined !text-3xl">arrow_forward</span>
      </Link>
    </div>
  );
}
