import { LayoutDashboard, AlertCircle, BookOpen, FileText, Settings, Shield, LogOut } from 'lucide-react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { cn } from '@/lib/utils';
import { StatusIndicator } from './StatusIndicator';
import type { UserRole } from '@/types/atlas';

const navItems = [
  { label: 'Portfolio', path: '/portfolio', icon: LayoutDashboard, roles: ['L1', 'L2', 'L3', 'SDM'] as UserRole[] },
  { label: 'Incidents', path: '/incidents', icon: AlertCircle, roles: ['L1', 'L2', 'L3', 'SDM'] as UserRole[] },
  { label: 'Playbooks', path: '/playbooks', icon: BookOpen, roles: ['L2', 'L3', 'SDM'] as UserRole[] },
  { label: 'Onboarding', path: '/onboarding', icon: Shield, roles: ['SDM'] as UserRole[] },
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
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const role = user?.role || 'L2';
  const visibleItems = navItems.filter(item => item.roles.includes(role as UserRole));

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className="w-[220px] bg-primary flex flex-col shrink-0 h-screen sticky top-0">
      {/* Wordmark */}
      <div className="px-5 pt-5 pb-5">
        <div className="flex items-center gap-2.5">
          <div className="h-9 w-9 rounded-lg bg-accent flex items-center justify-center">
            <Shield className="h-4.5 w-4.5 text-accent-foreground" />
          </div>
          <div>
            <h1 className="text-[15px] font-bold tracking-[0.15em] leading-none text-primary-foreground">ATLAS</h1>
            <p className="text-[9px] text-primary-foreground/40 mt-0.5 tracking-[0.08em] uppercase">AIOps Platform</p>
          </div>
        </div>
      </div>

      {/* Section label */}
      <div className="px-5 mb-1.5">
        <span className="text-[9px] text-primary-foreground/30 uppercase tracking-[0.12em] font-medium">Navigation</span>
      </div>

      {/* Navigation */}
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

      {/* User info + logout */}
      <div className="px-3 mb-2">
        <div className="px-3 py-2.5 rounded-lg bg-sidebar-accent/30">
          <div className="flex items-center gap-2.5 mb-2">
            <div className="h-7 w-7 rounded-full bg-accent flex items-center justify-center shrink-0">
              <span className="text-[10px] font-semibold text-accent-foreground">{user?.name?.split(' ').map(n => n[0]).join('')}</span>
            </div>
            <div className="min-w-0">
              <p className="text-[11px] font-medium text-primary-foreground truncate">{user?.name}</p>
              <p className="text-[9px] text-primary-foreground/40">{roleLabels[role as UserRole]}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] text-primary-foreground/40 hover:text-primary-foreground/70 hover:bg-sidebar-accent/40 transition-colors"
          >
            <LogOut className="h-3 w-3" />
            Sign out
          </button>
        </div>
      </div>

      {/* System health */}
      <div className="px-5 py-3 border-t border-sidebar-border">
        <div className="flex items-center gap-2">
          <StatusIndicator status="healthy" />
          <span className="text-[10px] text-primary-foreground/40">All systems operational</span>
        </div>
      </div>
    </aside>
  );
}
