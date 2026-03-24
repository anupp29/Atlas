import { Link, useLocation } from 'react-router-dom';

interface SideNavProps {
  title?: string;
  subtitle?: string;
}

const workflowSteps = [
  { name: 'Dashboard', icon: 'dashboard', path: '/', exact: true },
  { name: 'Detection Phase', icon: 'radar', path: '/detection' },
  { name: 'Incident Intel', icon: 'monitoring', path: '/incidents' },
  { name: 'Incident Briefing', icon: 'summarize', path: '/incidents/briefing' },
  { name: 'L1 Command', icon: 'terminal', path: '/incidents/l1-command' },
  { name: 'Approval Workflow', icon: 'verified_user', path: '/incidents/approval' },
  { name: 'Playbook Execution', icon: 'play_circle', path: '/incidents/playbook' },
  { name: 'Post Resolution', icon: 'check_circle', path: '/incidents/resolved' },
];

const regions = [
  { name: 'Global Fleet', icon: 'public', path: '/', active: true },
  { name: 'North America', icon: 'lan', path: '/region/north-america' },
  { name: 'EMEA', icon: 'domain', path: '/region/emea' },
  { name: 'APAC', icon: 'hub', path: '/region/apac' },
  { name: 'LATAM', icon: 'map', path: '/region/latam' },
];

export function SideNavBar({ title = 'ATLAS Platform', subtitle = 'Incident Workflow' }: SideNavProps) {
  const location = useLocation();
  
  const isActive = (step: typeof workflowSteps[0]) => {
    if (step.exact) return location.pathname === step.path;
    return location.pathname.startsWith(step.path);
  };
  
  return (
    <aside className="bg-[#f2f4f6] flex flex-col h-screen fixed left-0 top-14 w-64 z-40 border-r border-[#c0c7d1]/15">
      <div className="p-4">
        <div className="mb-4">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-8 h-8 bg-primary rounded flex items-center justify-center text-white font-bold text-xs">A</div>
            <div>
              <h3 className="font-['Inter'] text-xs font-bold uppercase tracking-wider text-[#004d7c]">{title}</h3>
              <p className="text-[10px] text-slate-500 uppercase tracking-tighter">{subtitle}</p>
            </div>
          </div>
        </div>
        
        {/* Workflow Navigation */}
        <div className="mb-4">
          <p className="text-[9px] font-black uppercase tracking-widest text-slate-400 mb-2 px-3">Incident Workflow</p>
          <nav className="flex flex-col gap-0.5">
            {workflowSteps.map((step) => (
              <Link
                key={step.path}
                to={step.path}
                className={`flex items-center gap-3 px-3 py-2 rounded-sm transition-all duration-200 relative ${
                  isActive(step)
                    ? 'bg-white text-[#004d7c] shadow-sm'
                    : 'text-slate-600 hover:bg-[#eceef0]'
                }`}
              >
                {isActive(step) && (
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary rounded-r"></div>
                )}
                <span className="material-symbols-outlined text-lg">{step.icon}</span>
                <span className="font-['Inter'] text-xs font-medium">{step.name}</span>
                {isActive(step) && (
                  <span className="ml-auto">
                    <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
                  </span>
                )}
              </Link>
            ))}
          </nav>
        </div>
        
        {/* Regions */}
        <div className="mb-4">
          <p className="text-[9px] font-black uppercase tracking-widest text-slate-400 mb-2 px-3">Regions</p>
          <nav className="flex flex-col gap-0.5">
            {regions.map((region) => (
              <Link
                key={region.name}
                to={region.path}
                className={`flex items-center gap-3 px-3 py-2 rounded-sm transition-all duration-200 ${
                  location.pathname === region.path
                    ? 'bg-white text-[#004d7c] shadow-sm'
                    : 'text-slate-600 hover:bg-[#eceef0]'
                }`}
              >
                <span className="material-symbols-outlined text-lg">{region.icon}</span>
                <span className="font-['Inter'] text-xs font-medium uppercase tracking-wider">{region.name}</span>
              </Link>
            ))}
          </nav>
        </div>
      </div>
      
      <div className="mt-auto flex flex-col gap-1 p-3 border-t border-outline-variant/20">
        <Link to="/network" className="flex items-center gap-3 px-3 py-2 text-slate-600 hover:bg-[#eceef0] transition-all duration-200">
          <span className="material-symbols-outlined text-lg">hub</span>
          <span className="font-['Inter'] text-xs font-bold uppercase tracking-wider">Network Overview</span>
        </Link>
        <Link to="/finance" className="flex items-center gap-3 px-3 py-2 text-slate-600 hover:bg-[#eceef0] transition-all duration-200">
          <span className="material-symbols-outlined text-lg">account_balance</span>
          <span className="font-['Inter'] text-xs font-bold uppercase tracking-wider">Finance Core</span>
        </Link>
        <Link to="/incidents/veto" className="flex items-center gap-3 px-3 py-2 text-error hover:bg-error/10 transition-all duration-200">
          <span className="material-symbols-outlined text-lg">gavel</span>
          <span className="font-['Inter'] text-xs font-bold uppercase tracking-wider">Veto Warning</span>
        </Link>
      </div>
    </aside>
  );
}
