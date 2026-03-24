import { Link } from 'react-router-dom';

export function PlaybookExecution() {
  return (
    <div className="max-w-7xl mx-auto pb-20">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-10 gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="bg-primary/10 text-primary text-[10px] font-bold px-2 py-0.5 rounded tracking-tighter uppercase">Active Session</span>
            <span className="text-on-surface-variant text-xs font-mono">PID: 8829-X</span>
          </div>
          <h1 className="text-3xl font-black text-on-surface tracking-tight leading-none mb-2">ATLAS Playbook Executing</h1>
          <p className="text-on-surface-variant text-sm font-medium flex items-center gap-2">
            <span className="material-symbols-outlined text-base text-primary">analytics</span>
            Remediation progress view: <span className="text-on-surface font-bold italic">High Latency Mitigation</span>
          </p>
        </div>
        <div className="flex gap-3 items-center">
          <div className="text-right">
            <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-1">Time Remaining</p>
            <p className="font-mono text-2xl font-bold text-primary">~120<span className="text-sm ml-1">s</span></p>
          </div>
          <Link
            to="/incidents/resolved"
            className="bg-tertiary text-white px-4 py-2 text-xs font-bold uppercase tracking-widest rounded shadow-md hover:brightness-110 transition-colors flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-sm">check_circle</span>
            Simulate Complete
          </Link>
        </div>
      </div>

      {/* Execution Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 mb-6">
        <div className="md:col-span-8 bg-surface-container-lowest p-6 ghost-border rounded-lg relative overflow-hidden">
          <div className="absolute top-0 left-0 w-1 h-full bg-primary"></div>
          <div className="flex justify-between items-center mb-6">
            <div className="flex items-center gap-4">
              <div className="flex flex-col">
                <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Current Task</span>
                <span className="text-lg font-bold text-on-surface">Step 2 of 5</span>
              </div>
              <span className="material-symbols-outlined text-primary text-2xl">arrow_forward</span>
              <span className="text-lg font-bold text-primary">Updating HikariCP config</span>
            </div>
            <div className="text-right">
              <span className="text-2xl font-black font-mono text-primary">40%</span>
            </div>
          </div>

          <div className="w-full bg-surface-container-highest h-3 rounded-full overflow-hidden mb-8">
            <div className="bg-gradient-to-r from-primary to-primary-container h-full w-[40%]"></div>
          </div>

          {/* Pipeline Visualizer */}
          <div className="flex justify-between relative mt-4">
            <div className="absolute top-1/2 left-0 w-full h-px bg-surface-container-high -translate-y-1/2 -z-10"></div>
            {[
              { label: 'Identify', icon: 'check', color: 'bg-tertiary', textColor: 'text-tertiary', done: true },
              { label: 'Optimize', icon: 'settings_input_component', color: 'bg-primary', textColor: 'text-primary', active: true },
              { label: 'Restart', icon: 'refresh', color: 'bg-surface-container-highest', textColor: 'text-on-surface-variant' },
              { label: 'Validate', icon: 'rule', color: 'bg-surface-container-highest', textColor: 'text-on-surface-variant' },
              { label: 'Deploy', icon: 'cloud_done', color: 'bg-surface-container-highest', textColor: 'text-on-surface-variant' },
            ].map((step, i) => (
              <div key={step.label} className="flex flex-col items-center gap-2 bg-surface-container-lowest px-2" style={{ opacity: i > 2 ? 0.4 : 1 }}>
                <div className={`w-8 h-8 rounded-full ${step.color} flex items-center justify-center text-white ${step.active ? 'outline outline-4 outline-primary/10' : ''}`}>
                  <span className="material-symbols-outlined text-sm" style={step.done ? { fontVariationSettings: "'FILL' 1" } : {}}>{step.icon}</span>
                </div>
                <span className={`text-[9px] font-bold uppercase ${step.textColor}`}>{step.label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="md:col-span-4 bg-surface-container-low p-6 rounded-lg ghost-border flex flex-col justify-between">
          <div>
            <h3 className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-4">Target Environment</h3>
            <div className="space-y-4">
              {[
                { label: 'Cluster ID', value: 'NA-EAST-01' },
                { label: 'Node Group', value: 'DB-PROD-REPLICA' },
                { label: 'Auth Method', value: 'mTLS / Vault' },
              ].map((item) => (
                <div key={item.label} className="flex justify-between items-center">
                  <span className="text-xs font-medium text-on-surface-variant">{item.label}</span>
                  <span className="font-mono text-xs font-bold text-on-surface">{item.value}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="pt-4 border-t border-[#c0c7d1]/20 mt-4">
            <div className="flex items-center gap-2 text-tertiary">
              <span className="w-2 h-2 rounded-full bg-tertiary"></span>
              <span className="text-[10px] font-bold uppercase tracking-widest">System Healthy</span>
            </div>
          </div>
        </div>
      </div>

      {/* Terminal */}
      <div className="bg-[#191c1e] rounded-lg overflow-hidden shadow-2xl flex flex-col h-[400px]">
        <div className="bg-[#2d3133] px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-sm text-slate-400">terminal</span>
            <span className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">Real-time Execution Log</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse"></span>
              <span className="text-[9px] text-slate-400 font-bold uppercase">Streaming</span>
            </span>
            <span className="material-symbols-outlined text-sm text-slate-400 cursor-pointer hover:text-white">content_copy</span>
          </div>
        </div>
        <div className="p-4 font-mono text-xs leading-relaxed overflow-y-auto space-y-1">
          {[
            { time: '12:44:01', level: 'INFO', msg: 'Playbook session initialized. Target nodes identified: 4', color: 'text-tertiary' },
            { time: '12:44:05', level: 'INFO', msg: 'Step 1: Check connectivity and permissions... SUCCESS', color: 'text-tertiary' },
            { time: '12:44:12', level: 'INFO', msg: 'Step 2: Commencing HikariCP optimization on nodes [1-4]', color: 'text-tertiary' },
            { time: '12:44:15', level: 'CMD', msg: 'sed -i \'s/maximumPoolSize=20/maximumPoolSize=50/g\' /app/config/datasource.properties', color: 'text-primary-fixed-dim', isCmd: true },
            { time: '12:44:20', level: 'INFO', msg: 'Applying changes to node 1... DONE', color: 'text-tertiary' },
            { time: '12:44:25', level: 'INFO', msg: 'Applying changes to node 2... DONE', color: 'text-tertiary' },
            { time: '12:45:08', level: 'INFO', msg: 'Pushing configuration updates to node 3...', color: 'text-white', highlight: true },
          ].map((log, i) => (
            <div key={i} className={`flex gap-4 ${log.highlight ? 'bg-primary/20 -mx-4 px-4 py-0.5 border-l-2 border-primary' : ''}`}>
              <span className="text-slate-600 shrink-0">{log.time}</span>
              <span className={log.color}>[{log.level}]</span>
              <span className={log.isCmd ? 'text-slate-400' : 'text-slate-300'}>{log.msg}</span>
              {log.highlight && <span className="text-slate-300 ml-2 animate-pulse">_</span>}
            </div>
          ))}
        </div>
      </div>

      {/* Safety Control */}
      <div className="mt-8 flex justify-between items-center p-4 bg-surface-container-low rounded-lg ghost-border">
        <div className="flex items-center gap-4">
          <span className="material-symbols-outlined text-error">warning</span>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">Safety Control</p>
            <p className="text-xs font-medium text-on-surface">Force abort will rollback all completed steps.</p>
          </div>
        </div>
        <div className="flex gap-3">
          <button className="px-4 py-2 bg-transparent text-secondary text-[10px] font-bold uppercase tracking-widest hover:text-on-surface transition-colors">
            View Audit Log
          </button>
          <Link
            to="/incidents/resolved"
            className="px-4 py-2 bg-tertiary text-white text-[10px] font-bold uppercase tracking-widest rounded shadow-sm hover:brightness-110 active:scale-95 transition-all"
          >
            Complete & View Report
          </Link>
        </div>
      </div>

      {/* Navigation FAB */}
      <Link
        to="/incidents/resolved"
        className="fixed bottom-8 right-8 w-14 h-14 bg-gradient-to-br from-tertiary to-green-600 text-white rounded-full shadow-lg hover:shadow-xl active:scale-95 transition-all flex items-center justify-center"
      >
        <span className="material-symbols-outlined !text-3xl">check</span>
      </Link>
    </div>
  );
}
