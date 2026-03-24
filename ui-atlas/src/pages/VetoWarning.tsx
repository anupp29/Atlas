import { Link } from 'react-router-dom';

export function VetoWarning() {
  return (
    <div className="max-w-7xl mx-auto pb-20">
      <header className="mb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono font-bold text-primary px-2 py-0.5 bg-primary/10 tracking-tighter">INCIDENT-4402</span>
            <span className="text-xs font-bold text-error bg-error/10 px-2 py-0.5 uppercase">Critical Block</span>
          </div>
          <Link
            to="/incidents/l1-command"
            className="px-4 py-2 bg-surface-container text-xs font-bold uppercase tracking-widest rounded hover:bg-surface-container-high transition-colors"
          >
            Back to L1 Command
          </Link>
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-on-surface mt-4">Veto Briefing: Payment Cluster</h1>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Veto Panel */}
        <div className="lg:col-span-8">
          <section className="bg-error-container/20 ghost-border rounded-lg overflow-hidden flex flex-col relative">
            <div className="p-6 border-b border-error/10 bg-error/5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-error flex items-center justify-center text-white shadow-lg">
                    <span className="material-symbols-outlined text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>gavel</span>
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-error tracking-tight">PCI-DSS COMPLIANCE VETO</h2>
                    <p className="text-sm text-on-surface-variant font-medium">Automatic Execution Prevented</p>
                  </div>
                </div>
                <div className="flex flex-col items-end">
                  <span className="font-mono text-sm font-bold text-error">VETO-STATUS: ACTIVE</span>
                  <span className="text-[0.65rem] text-on-surface-variant uppercase font-bold tracking-widest">Policy Engine 2.4.1</span>
                </div>
              </div>
            </div>
            <div className="p-6 bg-surface-container-lowest">
              <p className="text-on-surface font-medium leading-relaxed mb-6">
                Automated remediation for <span className="font-mono bg-surface-container-highest px-1">US-EAST-PAYROLL-DB</span> was intercepted by the compliance shield. 
                Applying the proposed patch would violate <span className="underline decoration-error/30">PCI-DSS Requirement 6.4.3</span> regarding unauthorized code execution in sensitive payment environments.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-surface-container-low rounded-lg border-l-4 border-error">
                  <div className="text-[0.65rem] uppercase font-bold text-on-surface-variant mb-1">Threat Vector</div>
                  <div className="font-bold text-on-surface">Unauthorized Data Exfiltration Risk</div>
                </div>
                <div className="p-4 bg-surface-container-low rounded-lg border-l-4 border-primary">
                  <div className="text-[0.65rem] uppercase font-bold text-on-surface-variant mb-1">Proposed Resolution</div>
                  <div className="font-bold text-on-surface">Manual Override &amp; Verified Patching</div>
                </div>
              </div>
            </div>
            <div className="p-4 bg-surface-container-high/50 flex justify-end gap-3">
              <button className="px-4 py-2 text-xs font-bold uppercase text-on-surface-variant hover:bg-surface-container-highest transition-colors rounded-sm">View Full Logs</button>
              <Link to="/incidents/l1-command" className="px-6 py-2 bg-primary text-white text-xs font-bold uppercase rounded-sm shadow-md hover:opacity-90 transition-opacity">
                Request Manual Override
              </Link>
            </div>
          </section>
        </div>

        {/* Early Warning Sidecar */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          <section className="bg-surface-container-lowest ghost-border rounded-lg p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold uppercase tracking-wider text-on-surface-variant flex items-center gap-2">
                <span className="material-symbols-outlined text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>warning</span>
                Early Warning System
              </h3>
              <span className="text-[0.65rem] font-mono font-bold text-primary bg-primary/10 px-1.5 py-0.5 rounded">LIVE</span>
            </div>
            <div className="p-4 bg-surface-container-low rounded-lg relative overflow-hidden">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <div className="text-sm font-bold text-on-surface">AuthService</div>
                  <div className="text-[0.65rem] font-mono text-on-surface-variant">POD_LATENCY_ANOMALY</div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-mono font-bold text-error">+1.8σ</div>
                  <div className="text-[0.6rem] font-bold text-error/60 uppercase">Trending Upward</div>
                </div>
              </div>
              <div className="h-12 w-full flex items-end gap-0.5 mb-2">
                {[20, 25, 22, 30, 45, 40, 65, 85, 100].map((h, i) => (
                  <div key={i} className={`w-full ${h > 60 ? 'bg-error' : h > 40 ? 'bg-primary/40' : 'bg-primary/20'}`} style={{ height: `${h}%` }}></div>
                ))}
              </div>
              <div className="text-[0.65rem] text-on-surface-variant italic">
                Prediction: Service saturation expected in <span className="font-bold text-on-surface">14 minutes</span> if current trend persists.
              </div>
            </div>
          </section>

          <section className="grid grid-cols-2 gap-3">
            <div className="bg-primary p-4 rounded-lg text-white shadow-md">
              <div className="text-[0.6rem] font-bold uppercase opacity-70 mb-1">MTTR Target</div>
              <div className="text-xl font-mono font-bold">45m</div>
            </div>
            <div className="bg-surface-container-highest p-4 rounded-lg">
              <div className="text-[0.6rem] font-bold uppercase text-on-surface-variant mb-1">Scope</div>
              <div className="text-xl font-mono font-bold text-primary">08 Nodes</div>
            </div>
          </section>
        </div>
      </div>

      {/* Terminal */}
      <section className="mt-8 bg-inverse-surface text-surface rounded-lg overflow-hidden ghost-border">
        <div className="flex items-center justify-between px-4 py-2 bg-[#191c1e]">
          <div className="flex items-center gap-4">
            <span className="text-[0.65rem] font-bold uppercase tracking-widest text-primary-fixed-dim">Compliance Terminal</span>
            <div className="flex gap-1.5">
              <div className="w-2 h-2 rounded-full bg-error/40"></div>
              <div className="w-2 h-2 rounded-full bg-primary/40"></div>
              <div className="w-2 h-2 rounded-full bg-tertiary/40"></div>
            </div>
          </div>
          <span className="material-symbols-outlined text-sm text-surface-dim opacity-50">open_in_full</span>
        </div>
        <div className="p-4 font-mono text-[0.7rem] leading-relaxed max-h-48 overflow-y-auto">
          {[
            { time: '12:44:55', level: 'INFO', msg: 'Initializing Veto Check Sequence for Cluster Alpha-9', color: 'text-primary-fixed-dim' },
            { time: '12:44:56', level: 'INFO', msg: 'Scanning manifest for sensitive compliance tags...', color: 'text-primary-fixed-dim' },
            { time: '12:44:57', level: 'WARN', msg: 'Tag \'PCI-DSS-L1\' detected on resource: payroll_db_main', color: 'text-secondary-fixed-dim' },
            { time: '12:44:57', level: 'ERROR', msg: 'VETO_EXCEPTION: Rule 6.4.3 violated. Automated remediation halted.', color: 'text-error' },
            { time: '12:44:58', level: 'INFO', msg: 'Alerting on-call compliance officer...', color: 'text-primary-fixed-dim' },
            { time: '12:45:00', level: 'STATUS', msg: 'Briefing generated for operator review.', color: 'text-primary-fixed-dim' },
          ].map((log, i) => (
            <div key={i} className="mb-1">
              <span className={log.color}>[{log.time}]</span> <span className="text-tertiary-fixed">{log.level}:</span> {log.msg}
            </div>
          ))}
          <div className="animate-pulse bg-surface/20 w-2 h-4 inline-block align-middle ml-1"></div>
        </div>
      </section>

      {/* Navigation FAB */}
      <Link
        to="/incidents/l1-command"
        className="fixed bottom-8 right-8 w-14 h-14 bg-gradient-to-br from-error to-red-700 text-white rounded-full shadow-lg hover:shadow-xl active:scale-95 transition-all flex items-center justify-center"
      >
        <span className="material-symbols-outlined !text-3xl">arrow_back</span>
      </Link>
    </div>
  );
}
