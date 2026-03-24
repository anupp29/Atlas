import { Link } from 'react-router-dom';

export function PostResolution() {
  return (
    <div className="max-w-7xl mx-auto pb-20">
      {/* Header Section */}
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-primary tracking-tight mb-1">
            Incident Resolution: <span className="text-on-surface-variant font-medium">INC-2941-X</span>
          </h1>
          <div className="flex items-center gap-3">
            <span className="bg-[#10B981]/10 text-[#10B981] px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-widest flex items-center gap-1">
              <span className="material-symbols-outlined text-xs" style={{ fontVariationSettings: "'FILL' 1" }}>check_circle</span>
              Resolved
            </span>
            <span className="text-on-surface-variant text-xs font-mono">Last Update: 2023-11-24 14:12:05 UTC</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 ghost-border text-on-surface-variant text-[10px] font-bold uppercase tracking-widest hover:bg-surface-container transition-colors">Export Report</button>
          <Link
            to="/"
            className="px-4 py-2 bg-primary text-white text-[10px] font-bold uppercase tracking-widest hover:bg-primary-container transition-colors flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-sm">home</span>
            Return to Dashboard
          </Link>
        </div>
      </div>

      {/* Bento Grid */}
      <div className="grid grid-cols-12 gap-6 mb-8">
        {/* MTTR Score */}
        <div className="col-span-12 lg:col-span-4 bg-surface-container-lowest p-6 ghost-border relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <span className="material-symbols-outlined text-6xl">timer</span>
          </div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-on-secondary-container mb-4">Resolution Performance</p>
          <div className="flex items-baseline gap-2">
            <span className="text-6xl font-black text-primary tracking-tighter">4:12</span>
            <span className="text-on-surface-variant font-mono text-sm">MTTR (MM:SS)</span>
          </div>
          <div className="mt-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-[#10B981]">trending_down</span>
            <span className="text-[#10B981] text-xs font-mono font-bold">-18.4% vs Baseline</span>
          </div>
        </div>

        {/* Recovery Chart */}
        <div className="col-span-12 lg:col-span-8 bg-surface-container-lowest p-6 ghost-border">
          <div className="flex justify-between items-center mb-6">
            <p className="text-[10px] font-bold uppercase tracking-widest text-on-secondary-container">Throughput Recovery Stream</p>
            <div className="flex gap-4 font-mono text-[10px]">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 bg-[#10B981]"></div>
                <span>Current</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 bg-outline-variant/30"></div>
                <span>P95 Baseline</span>
              </div>
            </div>
          </div>
          <div className="h-48 w-full relative">
            <svg className="w-full h-full" viewBox="0 0 800 200">
              <path d="M0 160 Q 100 155, 200 162 T 400 158 T 600 160 T 800 162" fill="none" opacity="0.5" stroke="#c0c7d1" strokeDasharray="4,4" strokeWidth="1"></path>
              <path d="M0 180 L 100 185 L 200 190 L 300 140 L 400 80 L 500 40 L 600 35 L 700 32 L 800 30" fill="none" stroke="#0066a1" strokeWidth="3"></path>
              <circle cx="300" cy="140" fill="#EF4444" r="4"></circle>
              <circle cx="500" cy="40" fill="#10B981" r="4"></circle>
            </svg>
          </div>
        </div>

        {/* Resolution Checklist */}
        <div className="col-span-12 lg:col-span-5 space-y-4">
          <div className="bg-surface-container-low p-4 ghost-border">
            <h4 className="text-[10px] font-black uppercase tracking-widest mb-4">Resolution Checklist</h4>
            <div className="space-y-3">
              {[
                { title: 'Traffic Reroute: Zone A-4', desc: 'Automated failover completed successfully via Cloudflare Tunnel.', done: true },
                { title: 'Database Re-indexing', desc: 'Post-crash consistency check completed. 0 corrupted blocks found.', done: true },
                { title: 'Cache Purge', desc: 'Global CDN purge initiated and confirmed at 14:10:00.', done: true, dimmed: true },
              ].map((item, i) => (
                <div key={i} className={`flex items-start gap-3 bg-white p-3 ghost-border ${item.dimmed ? 'opacity-60' : ''}`}>
                  <span className="material-symbols-outlined text-[#10B981]" style={{ fontVariationSettings: "'FILL' 1" }}>check_box</span>
                  <div>
                    <p className="text-xs font-bold text-primary">{item.title}</p>
                    <p className="text-[10px] text-on-surface-variant">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Terminal */}
        <div className="col-span-12 lg:col-span-7 bg-[#191c1e] p-5 rounded-lg shadow-2xl relative">
          <div className="flex items-center gap-2 mb-4 border-b border-white/10 pb-3">
            <div className="flex gap-1.5">
              <div className="w-2 h-2 rounded-full bg-error"></div>
              <div className="w-2 h-2 rounded-full bg-warning"></div>
              <div className="w-2 h-2 rounded-full bg-[#10B981]"></div>
            </div>
            <p className="text-[10px] font-mono text-white/40 ml-4">Terminal Output: post-resolution-dump.log</p>
          </div>
          <div className="font-mono text-xs space-y-1 overflow-y-auto max-h-48">
            {[
              { level: 'OK', msg: '14:11:05 - System integrity check initiated', color: 'text-[#10B981]' },
              { level: 'OK', msg: '14:11:12 - Handshake established with secondary nodes', color: 'text-[#10B981]' },
              { level: 'OK', msg: '14:11:45 - Cluster consensus reached @ 99.8% health', color: 'text-[#10B981]' },
              { level: 'OK', msg: '14:12:00 - Releasing incident lock from Redis', color: 'text-[#10B981]' },
              { level: 'INFO', msg: '14:12:05 - DASHBOARD_UPDATE: INC-2941-X status -> RESOLVED', color: 'text-primary-container' },
            ].map((log, i) => (
              <p key={i} className="text-white/60">
                <span className={log.color}>[{log.level}]</span> {log.msg}
              </p>
            ))}
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        {[
          { label: 'Confidence Score', value: '99.4%', color: 'text-[#10B981]' },
          { label: 'Affected Users', value: '1,429' },
          { label: 'SLA Credit Impact', value: '$0.00', color: 'text-error' },
          { label: 'Recovery Method', value: 'Auto-Heal + Manual Ack', isText: true },
        ].map((stat) => (
          <div key={stat.label} className="bg-surface-container p-4 ghost-border">
            <p className="text-[8px] font-black uppercase text-on-secondary-container mb-2">{stat.label}</p>
            {stat.isText ? (
              <span className="text-xs font-bold text-primary uppercase">{stat.value}</span>
            ) : (
              <span className={`text-xl font-bold font-mono ${stat.color || 'text-on-surface'}`}>{stat.value}</span>
            )}
          </div>
        ))}
      </div>

      {/* Navigation */}
      <div className="flex justify-between items-center p-4 bg-tertiary/10 rounded-lg ghost-border">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-tertiary">celebration</span>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-tertiary">Incident Complete</p>
            <p className="text-xs text-on-surface-variant">All remediation steps completed successfully.</p>
          </div>
        </div>
        <Link
          to="/"
          className="px-5 py-2 bg-primary text-white text-[10px] font-bold uppercase tracking-widest rounded shadow-md hover:bg-primary-container transition-colors flex items-center gap-2"
        >
          <span className="material-symbols-outlined text-sm">home</span>
          Back to Dashboard
        </Link>
      </div>

      {/* Navigation FAB */}
      <Link
        to="/"
        className="fixed bottom-8 right-8 w-14 h-14 bg-gradient-to-br from-tertiary to-green-600 text-white rounded-full shadow-lg hover:shadow-xl active:scale-95 transition-all flex items-center justify-center"
      >
        <span className="material-symbols-outlined !text-3xl">home</span>
      </Link>
    </div>
  );
}
