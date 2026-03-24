import { Link } from 'react-router-dom';

export function ApprovalWorkflow() {
  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-20">
      {/* Breadcrumbs */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2 text-xs font-mono text-outline uppercase tracking-tighter">
          <span>Operations</span>
          <span className="material-symbols-outlined text-[14px]">chevron_right</span>
          <span>Incidents</span>
          <span className="material-symbols-outlined text-[14px]">chevron_right</span>
          <span className="text-primary-container">Workflow #882-QX</span>
        </div>
        <div className="flex items-center justify-between">
          <h1 className="text-4xl font-black text-primary tracking-tight font-headline">Awaiting Approval</h1>
          <Link
            to="/incidents/playbook"
            className="bg-primary text-white px-5 py-2 text-xs font-bold uppercase tracking-widest rounded shadow-md hover:bg-primary-container transition-colors flex items-center gap-2"
          >
            <span>Approve & Execute</span>
            <span className="material-symbols-outlined text-sm">arrow_forward</span>
          </Link>
        </div>
      </div>

      {/* Approval Progress */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-surface-container-lowest p-8 rounded-lg ghost-border shadow-sm flex flex-col gap-8">
            <div className="flex justify-between items-start">
              <div className="space-y-1">
                <h2 className="text-lg font-bold text-on-surface">Dual-Signoff Workflow</h2>
                <p className="text-sm text-on-surface-variant max-w-md">Critical infrastructure changes require verification from two authorized engineering leads before deployment execution.</p>
              </div>
              <div className="bg-amber-100 text-amber-800 px-3 py-1 rounded-full flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                <span className="text-[10px] font-bold uppercase tracking-widest">Pending Verification</span>
              </div>
            </div>

            {/* Progress Line */}
            <div className="relative py-4">
              <div className="absolute top-1/2 left-0 w-full h-1 bg-surface-container-high -translate-y-1/2 rounded-full"></div>
              <div className="absolute top-1/2 left-0 w-1/2 h-1 bg-primary -translate-y-1/2 rounded-full"></div>
              <div className="relative flex justify-between">
                <div className="flex flex-col items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-primary text-white flex items-center justify-center border-4 border-surface-container-lowest z-10">
                    <span className="material-symbols-outlined">check</span>
                  </div>
                  <div className="text-center">
                    <p className="text-[10px] font-black text-primary uppercase tracking-widest">Primary Approval</p>
                    <p className="text-[12px] font-mono text-on-surface-variant">raj.kumar@atos.com</p>
                  </div>
                </div>
                <div className="flex flex-col items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-surface-container-lowest border-2 border-primary text-primary flex items-center justify-center z-10 shadow-lg">
                    <span className="material-symbols-outlined">pending</span>
                  </div>
                  <div className="text-center">
                    <p className="text-[10px] font-black text-on-surface uppercase tracking-widest">Secondary Approval</p>
                    <p className="text-[12px] font-mono text-primary font-bold">sarah.chen@atos.com</p>
                  </div>
                </div>
                <div className="flex flex-col items-center gap-3 opacity-30">
                  <div className="w-10 h-10 rounded-full bg-surface-container-high text-outline flex items-center justify-center z-10">
                    <span className="material-symbols-outlined">rocket_launch</span>
                  </div>
                  <div className="text-center">
                    <p className="text-[10px] font-black text-outline uppercase tracking-widest">Execution</p>
                    <p className="text-[12px] font-mono text-on-surface-variant">System Automated</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Detail Tokens */}
            <div className="bg-surface-container-low p-6 rounded-lg grid grid-cols-2 gap-8 border-l-4 border-primary">
              <div className="space-y-1">
                <p className="text-[10px] font-bold text-outline uppercase tracking-wider">Primary Record</p>
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-tertiary text-sm">verified</span>
                  <p className="text-xs font-mono font-bold text-on-surface">ID: APPROVAL_TOKEN_9921_ALPHA</p>
                </div>
              </div>
              <div className="space-y-1">
                <p className="text-[10px] font-bold text-outline uppercase tracking-wider">Request Source</p>
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-outline text-sm">terminal</span>
                  <p className="text-xs font-mono font-bold text-on-surface">CLI: ATLAS-DEPLOY-CORE</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Secondary Actions */}
        <div className="space-y-6">
          <div className="bg-surface-container-lowest p-6 rounded-lg ghost-border shadow-sm flex flex-col gap-6">
            <h3 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Request Metadata</h3>
            <div className="space-y-4">
              {[
                { label: 'Priority', value: 'CRITICAL (P1)', color: 'text-error' },
                { label: 'Risk Factor', value: 'HIGH', color: 'text-amber-600' },
                { label: 'Wait Time', value: '02:14:55', color: 'text-on-surface' },
              ].map((item) => (
                <div key={item.label} className="flex justify-between items-center border-b border-surface-container-low pb-2">
                  <span className="text-xs text-outline">{item.label}</span>
                  <span className={`text-xs font-mono font-bold ${item.color}`}>{item.value}</span>
                </div>
              ))}
            </div>
            <button className="w-full bg-surface-container-high hover:bg-surface-container-highest transition-colors text-on-surface py-3 rounded-sm flex items-center justify-center gap-2">
              <span className="material-symbols-outlined text-sm">mail</span>
              <span className="text-[10px] font-bold uppercase tracking-widest">Nudge Secondary Signer</span>
            </button>
          </div>

          {/* Security Protocol */}
          <div className="bg-primary p-6 rounded-lg text-white shadow-xl relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-primary-container to-primary opacity-50"></div>
            <div className="relative z-10 flex flex-col h-full justify-between gap-4">
              <div className="flex justify-between items-start">
                <span className="material-symbols-outlined text-3xl opacity-50">security_update_good</span>
                <div className="text-right">
                  <p className="text-[10px] font-bold uppercase tracking-[0.2em] opacity-80">Security Protocol</p>
                  <p className="text-sm font-black tracking-widest">ISO-27001</p>
                </div>
              </div>
              <p className="text-xs leading-relaxed opacity-90">Changes to core routing topology require non-repudiable signatures from the Regional Lead and Security Architect.</p>
            </div>
          </div>
        </div>
      </div>

      {/* FABs */}
      <div className="fixed bottom-8 right-8 flex gap-3">
        <Link
          to="/incidents/l1-command"
          className="bg-error text-white h-14 px-6 rounded-full shadow-2xl flex items-center gap-3 active:scale-95 transition-transform"
        >
          <span className="material-symbols-outlined">close</span>
          <span className="text-xs font-bold uppercase tracking-widest">Reject</span>
        </Link>
        <Link
          to="/incidents/playbook"
          className="bg-primary text-white h-14 px-8 rounded-full shadow-2xl flex items-center gap-3 active:scale-95 transition-transform border border-white/20"
        >
          <span className="material-symbols-outlined">check</span>
          <span className="text-xs font-bold uppercase tracking-widest">Approve & Execute</span>
        </Link>
      </div>
    </div>
  );
}
