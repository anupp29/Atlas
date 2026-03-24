import { Link } from 'react-router-dom';

export function Dashboard() {
  return (
    <div className="max-w-[1600px] mx-auto">
      {/* Header Section */}
      <div className="flex justify-between items-end mb-10">
        <div>
          <h1 className="text-3xl font-black text-primary tracking-tighter uppercase leading-none mb-2">Detection Phase</h1>
          <div className="flex items-center gap-3">
            <span className="text-sm font-bold text-slate-500 uppercase tracking-widest">
              Active Investigation: <span className="text-primary-container">X-ALPHA-92</span>
            </span>
            <span className="h-1 w-1 bg-outline-variant rounded-full"></span>
            <span className="text-xs font-mono text-slate-400">TIMESTAMP: {new Date().toISOString()}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 border border-outline-variant/20 bg-surface-container-low text-xs font-bold uppercase tracking-wider hover:bg-surface-container-high transition-colors">
            Export Logs
          </button>
          <button className="px-4 py-2 bg-primary text-white text-xs font-bold uppercase tracking-wider shadow-sm hover:opacity-90 transition-all">
            Initiate Lockdown
          </button>
        </div>
      </div>

      {/* Bento Grid Layout */}
      <div className="grid grid-cols-12 gap-[1.3rem]">
        {/* Main Intelligence Stream */}
        <div className="col-span-8 space-y-[1.3rem]">
          {/* Health Matrix */}
          <div className="grid grid-cols-4 gap-[1.3rem]">
            <div className="bg-surface-container-lowest p-5 ghost-border">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4">Traffic Ingress</p>
              <div className="flex items-end justify-between">
                <span className="font-mono text-2xl font-bold">442.8 <span className="text-xs font-normal">GB/S</span></span>
                <div className="flex items-center text-error text-xs font-bold">
                  <span className="material-symbols-outlined text-sm">trending_up</span>
                  14%
                </div>
              </div>
              <div className="mt-4 h-1 bg-surface-container-low w-full">
                <div className="bg-error h-full" style={{ width: '82%' }}></div>
              </div>
            </div>
            
            <div className="bg-surface-container-lowest p-5 ghost-border border-l-4 border-[#F59E0B]">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4">Node Latency</p>
              <div className="flex items-end justify-between">
                <span className="font-mono text-2xl font-bold">148 <span className="text-xs font-normal">MS</span></span>
                <div className="flex items-center text-[#F59E0B] text-xs font-bold">
                  <span className="material-symbols-outlined text-sm">warning</span>
                  DEGRADED
                </div>
              </div>
            </div>
            
            <div className="bg-surface-container-lowest p-5 ghost-border">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4">API Success Rate</p>
              <div className="flex items-end justify-between">
                <span className="font-mono text-2xl font-bold">94.2 <span className="text-xs font-normal">%</span></span>
                <div className="flex items-center text-error text-xs font-bold">
                  <span className="material-symbols-outlined text-sm">trending_down</span>
                  5.8%
                </div>
              </div>
            </div>
            
            <div className="bg-surface-container-lowest p-5 ghost-border">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4">Active Threats</p>
              <div className="flex items-end justify-between">
                <span className="font-mono text-2xl font-bold">12</span>
                <span className="bg-error/10 text-error px-2 py-0.5 rounded text-[10px] font-black tracking-tighter">CRITICAL</span>
              </div>
            </div>
          </div>

          {/* High Density Logs */}
          <div className="bg-surface-container-lowest ghost-border">
            <div className="flex items-center justify-between px-5 py-3 border-b border-outline-variant/10">
              <h3 className="text-xs font-black text-primary uppercase tracking-widest">Real-time Stream</h3>
              <div className="flex gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-error"></div>
                  <span className="text-[10px] font-mono text-slate-500">22 ERROR</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-[#F59E0B]"></div>
                  <span className="text-[10px] font-mono text-slate-500">48 WARN</span>
                </div>
              </div>
            </div>
            <div className="p-0 overflow-auto max-h-[300px] font-mono text-[11px] leading-tight">
              <div className="px-5 py-2 flex gap-4 hover:bg-surface-container-low transition-colors border-b border-outline-variant/5">
                <span className="text-slate-400 shrink-0">14:42:01.002</span>
                <span className="bg-error/10 text-error px-1 font-black">ERROR</span>
                <span className="text-on-surface truncate">Connection refused: proxy_cluster_01 -&gt; auth_service_v2 [TIMEOUT]</span>
                <span className="ml-auto text-slate-400">#44921</span>
              </div>
              <div className="px-5 py-2 flex gap-4 hover:bg-surface-container-low transition-colors border-b border-outline-variant/5">
                <span className="text-slate-400 shrink-0">14:41:58.892</span>
                <span className="bg-[#F59E0B]/10 text-[#F59E0B] px-1 font-black">WARN</span>
                <span className="text-on-surface truncate">High memory pressure on pod-worker-node-88 [92.4% utilized]</span>
                <span className="ml-auto text-slate-400">#44918</span>
              </div>
              <div className="px-5 py-2 flex gap-4 hover:bg-surface-container-low transition-colors border-b border-outline-variant/5">
                <span className="text-slate-400 shrink-0">14:41:55.120</span>
                <span className="bg-error/10 text-error px-1 font-black">ERROR</span>
                <span className="text-on-surface truncate">SQL Injection Attempt Detected: Source IP 192.168.1.104 [BLOCKED]</span>
                <span className="ml-auto text-slate-400">#44915</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Utility Column */}
        <div className="col-span-4 space-y-[1.3rem]">
          {/* Incident Brief */}
          <div className="bg-surface-container-highest p-5 ghost-border">
            <h3 className="text-xs font-black text-primary uppercase tracking-widest mb-4">Active Incident</h3>
            <div className="p-4 bg-surface-container-lowest border-l-4 border-error mb-4">
              <p className="text-xs font-bold leading-tight mb-1">DDoS Attack Mitigation</p>
              <p className="text-[10px] text-slate-500 mb-3">Target: Public Endpoint API</p>
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-error"></div>
                <span className="text-[10px] font-bold text-error uppercase tracking-wider">Mitigation In Progress</span>
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between items-center text-[10px]">
                <span className="text-slate-500">Duration</span>
                <span className="font-mono font-bold">00:14:22</span>
              </div>
              <div className="flex justify-between items-center text-[10px]">
                <span className="text-slate-500">Intensity</span>
                <span className="font-mono font-bold text-error">CRITICAL</span>
              </div>
            </div>
          </div>

          {/* Node Health */}
          <div className="bg-surface-container-lowest p-5 ghost-border">
            <h3 className="text-xs font-black text-primary uppercase tracking-widest mb-4">Node Health</h3>
            <div className="flex flex-wrap gap-2">
              {['NODE-01', 'NODE-02', 'NODE-03', 'NODE-04', 'NODE-05', 'NODE-06'].map((node, i) => (
                <div
                  key={node}
                  className={`flex items-center gap-1.5 px-2 py-1 rounded ${
                    i === 3 ? 'bg-error/10' : i === 1 || i === 5 ? 'bg-[#F59E0B]/10' : 'bg-tertiary/10'
                  }`}
                >
                  <div
                    className={`w-1.5 h-1.5 rounded-full ${
                      i === 3 ? 'bg-error' : i === 1 || i === 5 ? 'bg-[#F59E0B]' : 'bg-tertiary'
                    }`}
                  ></div>
                  <span className={`text-[9px] font-bold font-mono ${
                    i === 3 ? 'text-error' : i === 1 || i === 5 ? 'text-[#F59E0B]' : 'text-tertiary'
                  }`}>
                    {node}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* FAB */}
      <Link
        to="/detection"
        className="fixed bottom-8 right-8 w-14 h-14 bg-gradient-to-br from-primary to-primary-container text-white rounded-full shadow-lg hover:shadow-xl active:scale-95 transition-all flex items-center justify-center"
      >
        <span className="material-symbols-outlined !text-3xl">add</span>
      </Link>
    </div>
  );
}
