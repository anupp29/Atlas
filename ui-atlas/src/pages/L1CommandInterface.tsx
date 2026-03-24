import { Link } from 'react-router-dom';

export function L1CommandInterface() {
  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-20">
      {/* Hero Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="bg-error/10 text-error px-2 py-0.5 rounded-full text-[10px] font-bold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-error"></span> CRITICAL INCIDENT
            </span>
            <span className="font-mono text-[10px] text-on-surface-variant">ID: 882-QX-ALPHA</span>
          </div>
          <h1 className="text-4xl font-extrabold text-on-surface tracking-tight font-headline leading-none">L1 Command Interface</h1>
          <p className="text-on-surface-variant mt-2 max-w-xl font-medium">Simplified operational view for rapid decision-making on active telemetry anomalies.</p>
        </div>
        <div className="flex flex-col items-end">
          <span className="text-[10px] font-bold text-outline uppercase tracking-widest">Active Node</span>
          <span className="font-mono text-lg font-bold text-primary">US-EAST-04_CLUSTER</span>
        </div>
      </div>

      {/* Bento Logic Grid */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        {/* Summary Card */}
        <div className="md:col-span-8 bg-surface-container-lowest rounded-lg ghost-border p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-6">
            <span className="material-symbols-outlined text-primary">summarize</span>
            <h2 className="font-bold text-lg uppercase tracking-tight">Executive Summary</h2>
          </div>
          <div className="space-y-6">
            <div className="bg-surface-container-low p-4 rounded border-l-4 border-error">
              <h3 className="font-bold text-on-surface text-sm uppercase tracking-wide mb-2">The Situation</h3>
              <p className="text-on-surface-variant text-sm leading-relaxed">
                Unexpected 42% spike in latency detected across <span className="font-mono bg-surface-container-highest px-1">payment-gateway-v3</span>. 
                Internal buffers are nearing 88% capacity.
              </p>
            </div>
            <div className="bg-primary/5 p-4 rounded border-l-4 border-primary">
              <h3 className="font-bold text-primary text-sm uppercase tracking-wide mb-2">ATLAS Recommendation</h3>
              <div className="flex items-start gap-3">
                <span className="material-symbols-outlined text-primary">auto_awesome</span>
                <p className="text-on-surface-variant text-sm leading-relaxed">
                  Execute <span className="font-bold text-on-surface">Emergency Sharding Protocol (ESP-09)</span>. 
                  This will isolate the rogue subnet traffic to a sandboxed container cluster.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Metrics */}
        <div className="md:col-span-4 space-y-6">
          <div className="bg-surface-container-lowest rounded-lg ghost-border p-5 shadow-sm">
            <h3 className="font-bold text-xs text-outline uppercase tracking-widest mb-4">Live Telemetry</h3>
            <div className="space-y-4">
              <div className="flex justify-between items-end border-b border-surface-container pb-2">
                <span className="text-xs font-bold text-on-surface-variant">CPU UTILIZATION</span>
                <span className="font-mono text-xl font-bold text-error">94.2%</span>
              </div>
              <div className="flex justify-between items-end border-b border-surface-container pb-2">
                <span className="text-xs font-bold text-on-surface-variant">REQUESTS / SEC</span>
                <span className="font-mono text-xl font-bold text-on-surface">12.8k</span>
              </div>
              <div className="flex justify-between items-end border-b border-surface-container pb-2">
                <span className="text-xs font-bold text-on-surface-variant">ERRORS (5xx)</span>
                <span className="font-mono text-xl font-bold text-error">4.1%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Decision Matrix */}
        <div className="md:col-span-12 flex flex-col md:flex-row gap-6">
          <Link
            to="/incidents/approval"
            className="flex-1 group relative overflow-hidden bg-gradient-to-b from-primary to-primary-container text-white py-10 px-8 rounded-lg shadow-xl hover:shadow-primary/20 transition-all active:scale-95 text-left"
          >
            <div className="flex justify-between items-start mb-4">
              <span className="material-symbols-outlined text-4xl">verified</span>
              <span className="font-mono text-[10px] opacity-70 tracking-widest uppercase">Action Code: 01</span>
            </div>
            <h2 className="text-3xl font-black uppercase tracking-tighter leading-none mb-2">APPROVE</h2>
            <p className="text-sm font-medium opacity-80 max-w-xs">Authorize ATLAS to execute the ESP-09 isolation protocol immediately.</p>
            <div className="mt-8 flex items-center gap-2 text-[10px] font-bold tracking-widest uppercase bg-white/10 w-fit px-3 py-1 rounded">
              <span className="w-2 h-2 rounded-full bg-white animate-pulse"></span> Rapid Response Recommended
            </div>
          </Link>
          
          <Link
            to="/incidents/veto"
            className="flex-1 group bg-surface-container-highest text-on-surface py-10 px-8 rounded-lg ghost-border hover:bg-surface-container-high transition-all active:scale-95 text-left"
          >
            <div className="flex justify-between items-start mb-4">
              <span className="material-symbols-outlined text-4xl text-outline">gavel</span>
              <span className="font-mono text-[10px] text-outline tracking-widest uppercase">Action Code: 03</span>
            </div>
            <h2 className="text-3xl font-black uppercase tracking-tighter leading-none mb-2">VETO / ESCALATE</h2>
            <p className="text-sm font-medium text-on-surface-variant max-w-xs">Raise compliance flag and require manual approval.</p>
            <div className="mt-8 flex items-center gap-2 text-[10px] font-bold tracking-widest uppercase text-outline px-3 py-1">
              Compliance Review Required
            </div>
          </Link>
        </div>
      </div>

      {/* Navigation FAB */}
      <Link
        to="/incidents/approval"
        className="fixed bottom-8 right-8 w-14 h-14 bg-gradient-to-br from-primary to-primary-container text-white rounded-full shadow-lg hover:shadow-xl active:scale-95 transition-all flex items-center justify-center"
      >
        <span className="material-symbols-outlined !text-3xl">arrow_forward</span>
      </Link>
    </div>
  );
}
