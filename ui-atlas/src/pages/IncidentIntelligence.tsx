import { Link } from 'react-router-dom';

export function IncidentIntelligence() {
  return (
    <div className="max-w-7xl mx-auto pb-20">
      {/* SLA Breach Banner */}
      <div className="bg-error-container text-on-error-container px-4 py-2.5 rounded mb-6 flex items-center justify-between ghost-border">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-error" style={{ fontVariationSettings: "'FILL' 1" }}>warning</span>
          <span className="font-headline font-bold text-sm tracking-tight uppercase">SLA Breach Imminent: P0 Incident #INC-9402</span>
        </div>
        <div className="font-mono text-sm font-bold">T-MINUS 00:14:22</div>
      </div>

      {/* Dashboard Header */}
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="font-headline text-3xl font-extrabold text-primary tracking-tight">Incident Intelligence</h1>
          <p className="text-on-surface-variant text-sm mt-1">Real-time SHAP attribution and dependency mapping</p>
        </div>
        <div className="flex gap-2 items-center">
          <div className="bg-surface-container-highest px-3 py-1.5 rounded flex items-center gap-2">
            <span className="w-2 h-2 bg-error rounded-full"></span>
            <span className="font-mono text-xs font-bold uppercase tracking-widest">Urgency: Critical</span>
          </div>
          <Link
            to="/incidents/briefing"
            className="bg-primary text-white px-4 py-2 text-xs font-bold uppercase tracking-widest rounded hover:bg-primary-container transition-colors shadow-md"
          >
            View Briefing
          </Link>
        </div>
      </div>

      {/* Bento Grid Layout */}
      <div className="grid grid-cols-12 gap-5">
        {/* Briefing Card */}
        <div className="col-span-12 lg:col-span-4 bg-surface-container-lowest p-6 rounded-lg ghost-border shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-start mb-4">
              <span className="bg-primary/10 text-primary text-[10px] font-black px-2 py-0.5 rounded uppercase tracking-widest">Briefing Card</span>
              <span className="font-mono text-[10px] text-on-surface-variant">ID: AX-992-B</span>
            </div>
            <h2 className="font-headline text-xl font-bold mb-4 leading-tight">Database latency spike across EMEA cluster-04.</h2>
            <p className="text-on-surface-variant text-sm leading-relaxed mb-6">
              Anomalous read/write patterns detected starting at <span className="font-mono bg-surface-container text-primary px-1 rounded">08:42:01 UTC</span>. 
              Correlation with deployment <span className="font-mono underline text-primary cursor-pointer">#v2.4.12-rc</span> is high (94%).
            </p>
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs py-2 bg-surface-container-low px-3 rounded">
                <span className="font-semibold text-on-secondary-container">AFFECTED USERS</span>
                <span className="font-mono font-bold text-error">14,204</span>
              </div>
              <div className="flex items-center justify-between text-xs py-2 bg-surface-container-low px-3 rounded">
                <span className="font-semibold text-on-secondary-container">AVG LATENCY</span>
                <span className="font-mono font-bold text-error">842ms (+612%)</span>
              </div>
            </div>
          </div>
          <Link to="/incidents/briefing" className="mt-8 text-primary font-bold text-xs uppercase tracking-widest flex items-center gap-2 hover:translate-x-1 transition-transform">
            View Full Diagnostics <span className="material-symbols-outlined text-sm">arrow_forward</span>
          </Link>
        </div>

        {/* SHAP Attribution Chart */}
        <div className="col-span-12 lg:col-span-8 bg-surface-container-lowest p-6 rounded-lg ghost-border shadow-sm">
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-headline text-xs font-black uppercase tracking-[0.2em] text-on-surface-variant">SHAP Feature Attribution</h3>
            <div className="flex items-center gap-4 font-mono text-[10px] font-bold">
              <div className="flex items-center gap-1.5"><span className="w-2 h-2 bg-primary rounded-full"></span>POSITIVE IMPACT</div>
              <div className="flex items-center gap-1.5"><span className="w-2 h-2 bg-error rounded-full"></span>NEGATIVE IMPACT</div>
            </div>
          </div>
          <div className="space-y-5">
            {[
              { name: 'JVM_Heap_Usage', width: 'w-3/4', value: '+0.42', color: 'bg-error' },
              { name: 'Query_Complexity', width: 'w-1/2', value: '+0.28', color: 'bg-error' },
              { name: 'Conn_Pool_Saturation', width: 'w-1/4', value: '-0.12', color: 'bg-primary' },
              { name: 'Network_Retransmit', width: 'w-1/5', value: '+0.09', color: 'bg-error' },
            ].map((row) => (
              <div key={row.name} className="grid grid-cols-12 items-center gap-4">
                <div className="col-span-3 font-mono text-[11px] text-on-surface">{row.name}</div>
                <div className="col-span-8 flex items-center">
                  <div className={`h-6 ${row.color} ${row.width} rounded-r shadow-sm`}></div>
                  <span className="ml-3 font-mono text-[10px] font-bold">{row.value}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Dependency Graph */}
        <div className="col-span-12 bg-surface-container-lowest p-6 rounded-lg ghost-border shadow-sm min-h-[400px] relative overflow-hidden">
          <div className="absolute top-6 left-6 z-10">
            <h3 className="font-headline text-xs font-black uppercase tracking-[0.2em] text-on-surface-variant">System Dependency Topology</h3>
          </div>
          <div className="absolute top-6 right-6 z-10 flex gap-2">
            <button className="p-1.5 bg-surface-container-high rounded-full hover:bg-outline-variant/20"><span className="material-symbols-outlined text-sm">zoom_in</span></button>
            <button className="p-1.5 bg-surface-container-high rounded-full hover:bg-outline-variant/20"><span className="material-symbols-outlined text-sm">zoom_out</span></button>
            <button className="p-1.5 bg-surface-container-high rounded-full hover:bg-outline-variant/20"><span className="material-symbols-outlined text-sm">fullscreen</span></button>
          </div>
        </div>
      </div>

      {/* Veto Banner */}
      <div className="fixed bottom-0 left-64 right-0 bg-[#191c1e] text-white px-8 py-4 z-50 flex items-center justify-between glass-panel">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3">
            <div className="bg-error p-1.5 rounded-full flex items-center justify-center">
              <span className="material-symbols-outlined text-white text-base">gavel</span>
            </div>
            <div>
              <h4 className="font-headline text-sm font-black tracking-tight uppercase">Veto Lock Active</h4>
              <p className="text-[10px] text-slate-400 font-mono">AUTOMATED REMEDIATION PAUSED BY OPERATOR: ADMIN_K_CHEN</p>
            </div>
          </div>
        </div>
        <div className="flex gap-3">
          <Link to="/incidents/veto" className="bg-transparent border border-white/20 hover:bg-white/5 text-white px-5 py-2 text-xs font-black uppercase tracking-widest transition-all">
            Extend Veto
          </Link>
          <Link to="/incidents/l1-command" className="bg-primary hover:bg-primary-container text-white px-5 py-2 text-xs font-black uppercase tracking-widest shadow-lg shadow-primary/20 transition-all">
            Release Control
          </Link>
        </div>
      </div>
    </div>
  );
}
