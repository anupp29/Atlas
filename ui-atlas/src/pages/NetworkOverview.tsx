export function NetworkOverview() {
  return (
    <div className="max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-black text-on-surface tracking-tighter uppercase">Network Overview</h1>
          <p className="text-sm text-on-surface-variant font-medium">Real-time infrastructure performance matrix</p>
        </div>
        <div className="flex gap-2">
          <div className="px-3 py-1.5 bg-tertiary/10 text-tertiary text-[10px] font-bold rounded flex items-center gap-2 border border-tertiary/20">
            <span className="w-1.5 h-1.5 rounded-full bg-tertiary"></span> LIVE STREAMING
          </div>
          <div className="px-3 py-1.5 bg-surface-container-high text-on-surface-variant text-[10px] font-bold rounded border border-outline-variant/20">
            REFRESH: 2S
          </div>
        </div>
      </div>

      {/* Bento Grid */}
      <div className="grid grid-cols-12 gap-6">
        {/* Left Column */}
        <div className="col-span-12 lg:col-span-4 space-y-6">
          <div className="bg-surface-container-lowest p-5 rounded ghost-border shadow-sm">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xs font-black uppercase tracking-widest text-[#004d7c]">Client Roster</h2>
              <span className="material-symbols-outlined text-outline">more_vert</span>
            </div>
            <div className="space-y-1">
              {[
                { name: 'Alpha Project', ip: '192.168.1.104', status: 'HEALTHY' },
                { name: 'Beta Tech', ip: '10.0.4.22', status: 'HEALTHY' },
                { name: 'Gamma X-Ray', ip: '172.16.254.1', status: 'HEALTHY' },
              ].map((client) => (
                <div key={client.name} className="flex items-center justify-between p-2 hover:bg-surface-container-low transition-colors rounded">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded bg-primary/5 flex items-center justify-center text-primary font-black text-[10px]">
                      {client.name.split(' ').map(w => w[0]).join('')}
                    </div>
                    <div>
                      <p className="text-[11px] font-bold text-on-surface">{client.name}</p>
                      <p className="text-[9px] text-on-surface-variant font-mono">{client.ip}</p>
                    </div>
                  </div>
                  <span className="text-[10px] font-bold text-[#10B981] bg-[#10B981]/10 px-1.5 py-0.5 rounded">{client.status}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-surface-container-low p-4 rounded ghost-border">
              <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-tighter">Throughput</p>
              <div className="flex items-baseline gap-1 mt-1">
                <span className="text-xl font-black font-mono text-primary">842</span>
                <span className="text-[10px] font-bold text-on-surface-variant">Mb/s</span>
              </div>
            </div>
            <div className="bg-surface-container-low p-4 rounded ghost-border">
              <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-tighter">Active Nodes</p>
              <div className="flex items-baseline gap-1 mt-1">
                <span className="text-xl font-black font-mono text-primary">1,204</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column - System Logs */}
        <div className="col-span-12 lg:col-span-8">
          <div className="bg-surface-container-lowest rounded ghost-border shadow-sm flex flex-col h-[520px]">
            <div className="p-4 border-b border-[#eceef0] flex justify-between items-center bg-[#fcfdfe]">
              <div className="flex items-center gap-4">
                <h2 className="text-xs font-black uppercase tracking-widest text-[#004d7c]">System Logs</h2>
                <div className="flex gap-2">
                  <span className="w-2 h-2 rounded-full bg-tertiary animate-pulse"></span>
                  <span className="text-[10px] font-bold text-on-surface-variant">LIVE STREAMING</span>
                </div>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto bg-[#0a0c0e] text-[#a9b1d6] font-mono text-[11px] leading-relaxed">
              <table className="w-full border-collapse">
                <thead className="sticky top-0 bg-[#1a1b26] text-[10px] text-[#565f89] uppercase font-bold tracking-widest border-b border-[#24283b]">
                  <tr>
                    <th className="py-2 px-4 text-left">Timestamp</th>
                    <th className="py-2 px-4 text-left">Source</th>
                    <th className="py-2 px-4 text-left">Event</th>
                    <th className="py-2 px-4 text-left">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { time: '14:22:01.442', source: 'srv-alpha-04', event: 'GET /api/v1/telemetry/push', status: '200 OK', statusColor: 'text-[#10B981]' },
                    { time: '14:22:02.109', source: 'cluster-ingress-01', event: 'Routing traffic to node-p44', status: 'INFO', statusColor: 'text-[#7aa2f7]' },
                    { time: '14:22:02.910', source: 'db-replica-main', event: 'Handshake initiated with node-09', status: 'PENDING', statusColor: 'text-[#e0af68]' },
                    { time: '14:22:03.551', source: 'srv-alpha-04', event: 'POST /api/v1/auth/verify', status: '200 OK', statusColor: 'text-[#10B981]' },
                    { time: '14:22:04.112', source: 'auth-gate-02', event: 'Session token validated for user 992', status: 'SUCCESS', statusColor: 'text-[#10B981]' },
                  ].map((row, i) => (
                    <tr key={i} className="border-b border-[#1f2335] hover:bg-[#1a1b26] transition-colors">
                      <td className="py-2 px-4 text-[#737aa2]">{row.time}</td>
                      <td className="py-2 px-4 text-[#4fd6be]">{row.source}</td>
                      <td className="py-2 px-4 text-[#c0caf5]">{row.event}</td>
                      <td className="py-2 px-4"><span className={`font-bold ${row.statusColor}`}>{row.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Bottom Metrics */}
        <div className="col-span-12 grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { icon: 'memory', label: 'CPU Utilization', value: '32.4', unit: '%', color: 'text-primary' },
            { icon: 'speed', label: 'Network Latency', value: '12', unit: 'ms', color: 'text-[#10B981]' },
            { icon: 'dns', label: 'Instance Count', value: '182', unit: '', color: 'text-primary-container' },
          ].map((metric) => (
            <div key={metric.label} className="bg-surface-container-low p-5 rounded ghost-border flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-white shadow-sm flex items-center justify-center">
                <span className={`material-symbols-outlined !text-3xl ${metric.color}`}>{metric.icon}</span>
              </div>
              <div>
                <p className="text-[10px] font-black text-on-surface-variant uppercase tracking-widest">{metric.label}</p>
                <p className="text-xl font-black font-mono text-on-surface">{metric.value}<span className="text-sm font-normal">{metric.unit}</span></p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
