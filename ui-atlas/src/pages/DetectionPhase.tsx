import { Link } from 'react-router-dom';

export function DetectionPhase() {
  return (
    <div className="max-w-7xl mx-auto">
      {/* Header Section */}
      <div className="flex justify-between items-end mb-8">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="bg-error/10 text-error px-2 py-0.5 rounded text-[10px] font-bold tracking-widest flex items-center gap-1">
              <span className="w-1.5 h-1.5 bg-error rounded-full animate-pulse"></span>
              DETECTION PHASE
            </span>
            <span className="text-slate-400 font-mono text-[10px]">ID: EVT-992-004</span>
          </div>
          <h1 className="text-4xl font-extrabold text-[#191c1e] tracking-tight leading-none">Anomalous Activity Detected</h1>
        </div>
        <div className="flex gap-2">
          <button className="ghost-border px-4 py-2 text-xs font-bold text-secondary hover:bg-surface-container transition-colors uppercase tracking-widest">
            Export Logs
          </button>
          <Link
            to="/incidents"
            className="bg-primary text-white px-4 py-2 text-xs font-bold rounded hover:bg-primary-container transition-colors uppercase tracking-widest shadow-md inline-block"
          >
            Acknowledge Incident
          </Link>
        </div>
      </div>

      {/* Bento Grid Layout */}
      <div className="grid grid-cols-12 gap-6">
        {/* SHAP Feature Attribution */}
        <div className="col-span-8 bg-surface-container-lowest rounded-lg p-6 ghost-border shadow-sm">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h3 className="text-sm font-bold uppercase tracking-widest text-[#004d7c]">SHAP Feature Attribution</h3>
              <p className="text-xs text-slate-500 mt-1">Impact contribution by feature variable</p>
            </div>
            <span className="material-symbols-outlined text-slate-400 cursor-help">info</span>
          </div>
          
          <div className="space-y-6">
            {[
              { name: 'connection_count', value: 67.42, color: 'bg-error', textColor: 'text-error' },
              { name: 'query_latency', value: 21.18, color: 'bg-orange-500', textColor: 'text-orange-500' },
              { name: 'memory_utilization', value: 8.10, color: 'bg-slate-400', textColor: 'text-slate-500' },
              { name: 'disk_io_wait', value: 3.30, color: 'bg-slate-400', textColor: 'text-slate-500' },
            ].map((feature) => (
              <div key={feature.name} className="space-y-2">
                <div className="flex justify-between text-[11px] font-mono">
                  <span className="text-on-surface font-bold">{feature.name}</span>
                  <span className={`${feature.textColor} font-bold`}>
                    {feature.value.toFixed(2)}%
                    {feature.name !== 'memory_utilization' && feature.name !== 'disk_io_wait' && (
                      <span className="material-symbols-outlined text-[12px] ml-1">trending_up</span>
                    )}
                  </span>
                </div>
                <div className="h-4 bg-surface-container-high rounded-full overflow-hidden flex">
                  <div className={`h-full ${feature.color}`} style={{ width: `${feature.value}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Status Indicators */}
        <div className="col-span-4 flex flex-col gap-6">
          <div className="bg-surface-container-lowest rounded-lg p-5 ghost-border shadow-sm flex-1">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-4">Real-time Telemetry</h3>
            <div className="space-y-4">
              {[
                { name: 'Core Engine', status: 'CRITICAL', color: 'bg-error', textColor: 'text-error' },
                { name: 'Auth-Gateway', status: 'DEGRADED', color: 'bg-orange-500', textColor: 'text-orange-500' },
                { name: 'CDN Nodes', status: 'HEALTHY', color: 'bg-tertiary', textColor: 'text-tertiary' },
              ].map((item) => (
                <div key={item.name} className="flex items-center justify-between p-3 bg-surface rounded ghost-border">
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${item.color}`}></div>
                    <span className="text-xs font-bold text-on-surface-variant">{item.name}</span>
                  </div>
                  <span className={`font-mono text-xs font-bold ${item.textColor}`}>{item.status}</span>
                </div>
              ))}
            </div>
          </div>

          {/* AI Confidence Card */}
          <div className="bg-primary p-5 rounded-lg shadow-xl flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start mb-2">
                <span className="material-symbols-outlined text-white/50 text-3xl">psychology</span>
                <span className="bg-white/10 text-white text-[10px] px-2 py-0.5 rounded">ML-CORE v4.2</span>
              </div>
              <h4 className="text-white text-sm font-bold">Inference Confidence</h4>
            </div>
            <div className="mt-4">
              <span className="text-4xl font-black text-white font-mono">94.2%</span>
              <p className="text-white/60 text-[10px] mt-1 leading-tight">Match with previous 'PostgreSQL-Agent' injection pattern.</p>
            </div>
          </div>
        </div>

        {/* Activity Feed */}
        <div className="col-span-12 bg-surface-container-lowest rounded-lg ghost-border overflow-hidden">
          <div className="px-6 py-4 border-b border-[#c0c7d1]/10 flex justify-between items-center bg-surface-container-low">
            <h3 className="text-sm font-bold uppercase tracking-widest text-[#004d7c]">Anomalous Event Stream</h3>
            <div className="flex items-center gap-4 text-[10px] font-bold text-slate-500">
              <span className="flex items-center gap-1"><span className="w-2 h-2 bg-error rounded-full"></span> 12 CRITICAL</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 bg-orange-500 rounded-full"></span> 08 WARNING</span>
            </div>
          </div>
          <div className="max-h-64 overflow-y-auto">
            <table className="w-full text-left font-['Inter']">
              <thead>
                <tr className="text-[10px] uppercase text-slate-400 font-bold border-b border-[#c0c7d1]/10">
                  <th className="px-6 py-3">Timestamp</th>
                  <th className="px-6 py-3">Entity</th>
                  <th className="px-6 py-3">Signature</th>
                  <th className="px-6 py-3">Payload Hash</th>
                  <th className="px-6 py-3 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="font-mono text-[11px] divide-y divide-[#c0c7d1]/5">
                <tr className="bg-error/5">
                  <td className="px-6 py-3 text-slate-500">12:44:59.002</td>
                  <td className="px-6 py-3 text-on-surface font-bold">PostgreSQL-Agent-01</td>
                  <td className="px-6 py-3 text-error">UNUSUAL_QUERY_PATTERN</td>
                  <td className="px-6 py-3 text-slate-400">0x7F4A2211C</td>
                  <td className="px-6 py-3 text-right">
                    <span className="bg-error text-white px-2 py-0.5 rounded text-[9px] font-bold">BLOCK</span>
                  </td>
                </tr>
                <tr className="bg-orange-500/5">
                  <td className="px-6 py-3 text-slate-500">12:44:58.871</td>
                  <td className="px-6 py-3 text-on-surface font-bold">PostgreSQL-Agent-02</td>
                  <td className="px-6 py-3 text-orange-600">LATENCY_SPIKE_DETECTED</td>
                  <td className="px-6 py-3 text-slate-400">0x22E811F0A</td>
                  <td className="px-6 py-3 text-right">
                    <span className="bg-orange-500 text-white px-2 py-0.5 rounded text-[9px] font-bold">WARN</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="fixed bottom-8 right-8">
        <Link
          to="/incidents"
          className="w-14 h-14 bg-gradient-to-br from-primary to-primary-container text-white rounded-full shadow-lg hover:shadow-xl active:scale-95 transition-all flex items-center justify-center"
        >
          <span className="material-symbols-outlined !text-3xl">arrow_forward</span>
        </Link>
      </div>
    </div>
  );
}
