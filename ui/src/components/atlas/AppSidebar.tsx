import { LayoutDashboard, AlertCircle, BookOpen, FileText, Settings, ChevronDown } from 'lucide-react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { cn } from '@/lib/utils';
import { StatusIndicator } from './StatusIndicator';
import { AtlasLogo } from './AtlasLogo';
import type { UserRole } from '@/types/atlas';
import { useState } from 'react';

const navItems = [
  { label: 'Portfolio', path: '/portfolio', icon: LayoutDashboard, roles: ['L1', 'L2', 'L3', 'SDM'] as UserRole[] },
  { label: 'Incidents', path: '/incidents', icon: AlertCircle, roles: ['L1', 'L2', 'L3', 'SDM'] as UserRole[] },
  { label: 'Playbooks', path: '/playbooks', icon: BookOpen, roles: ['L2', 'L3', 'SDM'] as UserRole[] },
  { label: 'Audit Log', path: '/audit', icon: FileText, roles: ['L1', 'L2', 'L3', 'SDM'] as UserRole[] },
  { label: 'Settings', path: '/settings', icon: Settings, roles: ['L1', 'L2', 'L3', 'SDM'] as UserRole[] },
];

const roleLabels: Record<UserRole, string> = {
  L1: 'L1 Engineer',
  L2: 'L2 Engineer',
  L3: 'L3 / SRE',
  SDM: 'Service Delivery Mgr',
  CLIENT: 'Client Portal',
};

export function AppSidebar() {
  const { user, switchRole } = useAuth();
  const navigate = useNavigate();
  const role = user?.role || 'L2';
  const visibleItems = navItems.filter(item => item.roles.includes(role as UserRole));
  const [showRoles, setShowRoles] = useState(false);

  const handleRoleSwitch = (r: UserRole) => {
    switchRole(r);
    setShowRoles(false);
    if (r === 'CLIENT') navigate('/portal');
    else if (r === 'SDM') navigate('/portfolio');
    else navigate('/incidents');
  };

  return (
    <aside className="w-[220px] bg-primary flex flex-col shrink-0 h-screen sticky top-0">
      <div className="px-5 pt-5 pb-5">
        <AtlasLogo size="md" variant="light" />
      </div>

      <div className="px-5 mb-1.5">
        <span className="text-[9px] text-primary-foreground/30 uppercase tracking-[0.12em] font-medium">Navigation</span>
      </div>

      <nav className="flex-1 px-3">
        <ul className="space-y-0.5">
          {visibleItems.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 px-3 py-[9px] rounded-lg text-[13px] transition-colors duration-150',
                    isActive
                      ? 'bg-sidebar-accent text-primary-foreground font-medium'
                      : 'text-primary-foreground/50 hover:text-primary-foreground/80 hover:bg-sidebar-accent/40',
                  )
                }
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <div className="px-3 mb-2">
        <div className="px-3 mb-2">
          <span className="text-[9px] text-primary-foreground/25 uppercase tracking-[0.12em] font-medium">Demo Controls</span>
        </div>
        <button
          onClick={() => setShowRoles(!showRoles)}
          className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-[11px] text-primary-foreground/50 hover:text-primary-foreground/70 hover:bg-sidebar-accent/30 transition-colors"
        >
          <span className="font-medium">{roleLabels[role as UserRole]}</span>
          <ChevronDown className={cn('h-3 w-3 transition-transform', showRoles && 'rotate-180')} />
        </button>
        {showRoles && (
          <div className="mt-1 space-y-0.5">
            {(['L1', 'L2', 'L3', 'SDM', 'CLIENT'] as UserRole[]).map((r) => (
              <button
                key={r}
                onClick={() => handleRoleSwitch(r)}
                className={cn(
                  'w-full text-left px-3 py-1.5 rounded-lg text-[12px] transition-colors duration-150',
                  role === r
                    ? 'bg-accent text-accent-foreground font-medium'
                    : 'text-primary-foreground/40 hover:text-primary-foreground/65 hover:bg-sidebar-accent/30',
                )}
              >
                {roleLabels[r]}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="px-5 py-3 border-t border-sidebar-border">
        <div className="flex items-center gap-2">
          <StatusIndicator status="healthy" />
          <span className="text-[10px] text-primary-foreground/40">All systems operational</span>
        </div>
      </div>
    </aside>
  );
}
