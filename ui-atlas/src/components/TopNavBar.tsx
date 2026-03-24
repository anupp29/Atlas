import { Link, useLocation } from 'react-router-dom';

const navItems = [
  { label: 'Observability', path: '/' },
  { label: 'Incidents', path: '/incidents' },
  { label: 'Logs', path: '/logs' },
  { label: 'Topology', path: '/topology' },
];

export function TopNavBar() {
  const location = useLocation();
  
  return (
    <header className="bg-[#f7f9fb] flex justify-between items-center w-full px-6 h-14 border-b border-[#c0c7d1]/15 fixed top-0 z-50">
      <div className="flex items-center gap-8">
        <Link to="/" className="text-xl font-black text-[#004d7c] tracking-widest font-['Inter']">ATLAS</Link>
        <nav className="hidden md:flex gap-6 items-center h-full">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`font-['Inter'] font-semibold tracking-tight pb-1 transition-colors ${
                location.pathname === item.path
                  ? 'text-[#004d7c] border-b-2 border-[#004d7c]'
                  : 'text-slate-500 hover:text-[#004d7c]'
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
      <div className="flex items-center gap-4">
        <span className="font-['JetBrains_Mono'] text-xs font-bold text-[#004d7c]">
          {new Date().toLocaleTimeString('en-US', { hour12: false, timeZone: 'UTC' })} UTC
        </span>
        <div className="flex gap-2">
          <button className="p-2 text-slate-500 hover:text-[#004d7c] transition-transform scale-95 active:scale-90">
            <span className="material-symbols-outlined">sensors</span>
          </button>
          <button className="p-2 text-slate-500 hover:text-[#004d7c] transition-transform scale-95 active:scale-90 relative">
            <span className="material-symbols-outlined">notifications</span>
            <span className="absolute top-1 right-1 w-2 h-2 bg-error rounded-full"></span>
          </button>
          <button className="p-2 text-slate-500 hover:text-[#004d7c] transition-transform scale-95 active:scale-90">
            <span className="material-symbols-outlined">account_circle</span>
          </button>
        </div>
      </div>
    </header>
  );
}
