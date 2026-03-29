import { useAuth } from '@/contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { LogOut, User, Bell, Clock, Shield, Users } from 'lucide-react';
import type { UserRole } from '@/types/atlas';
import { useAtlasData } from '@/contexts/AtlasDataContext';
import { cn } from '@/lib/utils';

// SDM can impersonate any role for oversight — no other role can self-switch
const sdmRoleOptions: { value: UserRole; label: string; desc: string }[] = [
  { value: 'L1', label: 'L1 Engineer', desc: 'First-line triage and approval' },
  { value: 'L2', label: 'L2 Engineer', desc: 'Investigation and root cause analysis' },
  { value: 'L3', label: 'L3 / SRE', desc: 'Engineering debugging and manual override' },
  { value: 'SDM', label: 'Service Delivery Manager', desc: 'Portfolio oversight and SLA governance' },
  { value: 'CLIENT', label: 'Client Portal', desc: 'Read-only service transparency' },
];

const roleDescriptions: Record<UserRole, string> = {
  L1: 'First-line triage — approve or escalate AI recommendations within SLA windows.',
  L2: 'Operational investigation — root cause analysis, confidence scoring, parameter modification.',
  L3: 'Engineering debugging — code-level diagnosis, configuration diffs, manual override authority.',
  SDM: 'Service delivery oversight — portfolio health, SLA governance, client trust management.',
  CLIENT: 'Read-only transparency portal — incident status, SLA compliance, resolution history.',
};

export default function SettingsPage() {
  const { user, logout, switchRole } = useAuth();
  const navigate = useNavigate();
  const { backendConnected, incidents } = useAtlasData();
  const activeCount = incidents.filter(i => i.status !== 'Resolved').length;
  const isRoleController = user?.role === 'SDM' || user?.homeRole === 'SDM';

  const roleBadgeClass = (() => {
    if (user?.role === 'L1') return 'bg-status-healthy/10 text-status-healthy';
    if (user?.role === 'L2') return 'bg-accent/10 text-accent';
    if (user?.role === 'L3') return 'bg-status-critical/10 text-status-critical';
    if (user?.role === 'SDM') return 'bg-primary/10 text-primary';
    return 'bg-muted text-muted-foreground';
  })();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="max-w-2xl space-y-4">
      <div>
        <h1 className="text-[16px] font-semibold text-foreground">Settings</h1>
        <p className="text-[12px] text-muted-foreground mt-0.5">Account and system configuration</p>
      </div>

      {/* Account */}
      <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
        <div className="flex items-center gap-2 mb-3">
          <User className="h-3.5 w-3.5 text-muted-foreground" />
          <h2 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Account</h2>
        </div>
        <div className="space-y-2.5 text-[12px]">
          <div className="flex items-center gap-3">
            <span className="text-muted-foreground w-24 shrink-0">Name</span>
            <span className="text-foreground font-medium">{user?.name}</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-muted-foreground w-24 shrink-0">Email</span>
            <span className="text-foreground font-mono text-[11px]">{user?.email}</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-muted-foreground w-24 shrink-0">Role</span>
            <div className="flex items-center gap-2">
              <span className={cn('text-[10px] font-semibold px-2 py-0.5 rounded uppercase', roleBadgeClass)}>{user?.role}</span>
              <span className="text-muted-foreground text-[11px]">{user?.role ? roleDescriptions[user.role] : ''}</span>
            </div>
          </div>
        </div>
      </div>

      {/* SDM-only: workspace view switcher for oversight */}
      {isRoleController && (
        <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
          <div className="flex items-center gap-2 mb-1">
            <Users className="h-3.5 w-3.5 text-muted-foreground" />
            <h2 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Workspace View</h2>
            <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-primary/10 text-primary uppercase">SDM Only</span>
          </div>
          <p className="text-[11px] text-muted-foreground mb-3 leading-relaxed">
            As Service Delivery Manager (SDM/SRM controller role), you can preview any role's workspace to validate the experience your engineers see. Engineer accounts cannot self-switch roles.
          </p>
          <div className="flex items-center gap-3">
            <Select value={user?.role} onValueChange={(v) => switchRole(v as UserRole)}>
              <SelectTrigger className="h-9 text-[12px] w-[240px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {sdmRoleOptions.map(r => (
                  <SelectItem key={r.value} value={r.value}>
                    <div className="py-0.5">
                      <p className="text-[12px] font-medium">{r.label}</p>
                      <p className="text-[10px] text-muted-foreground">{r.desc}</p>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {user?.role !== 'SDM' && (
              <button
                onClick={() => switchRole('SDM')}
                className="text-[11px] text-accent hover:underline"
              >
                Return to SDM view
              </button>
            )}
          </div>
        </div>
      )}

      {/* System status */}
      <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
        <div className="flex items-center gap-2 mb-3">
          <Shield className="h-3.5 w-3.5 text-muted-foreground" />
          <h2 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">System Status</h2>
        </div>
        <div className="space-y-2 text-[12px]">
          <div className="flex items-center justify-between py-1 border-b border-border/50">
            <span className="text-muted-foreground">Backend connection</span>
            <div className="flex items-center gap-1.5">
              <span className={cn('h-1.5 w-1.5 rounded-full', backendConnected ? 'bg-status-healthy live-dot' : 'bg-muted-foreground')} />
              <span className={cn('font-medium', backendConnected ? 'text-status-healthy' : 'text-muted-foreground')}>
                {backendConnected ? 'Live — real-time data' : 'Offline — demo mode'}
              </span>
            </div>
          </div>
          <div className="flex items-center justify-between py-1 border-b border-border/50">
            <span className="text-muted-foreground">Active incidents</span>
            <span className={cn('font-mono font-semibold', activeCount > 0 ? 'text-status-warning' : 'text-status-healthy')}>{activeCount}</span>
          </div>
          <div className="flex items-center justify-between py-1 border-b border-border/50">
            <span className="text-muted-foreground">API endpoint</span>
            <span className="font-mono text-[10px] text-muted-foreground">{import.meta.env.VITE_ATLAS_API_BASE_URL || 'http://localhost:8000'}</span>
          </div>
          <div className="flex items-center justify-between py-1">
            <span className="text-muted-foreground">WebSocket</span>
            <span className="font-mono text-[10px] text-muted-foreground">{import.meta.env.VITE_ATLAS_WS_BASE_URL || 'ws://localhost:8000'}</span>
          </div>
        </div>
      </div>

      {/* Notifications */}
      <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
        <div className="flex items-center gap-2 mb-2">
          <Bell className="h-3.5 w-3.5 text-muted-foreground" />
          <h2 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Notifications</h2>
        </div>
        <p className="text-[11px] text-muted-foreground leading-relaxed">
          Notification routing, escalation thresholds, and Slack webhook configuration are managed by the Service Delivery Manager via the ATLAS admin console. Contact your SDM to adjust channels or routing rules.
        </p>
      </div>

      {/* Session */}
      <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
        <div className="flex items-center gap-2 mb-2">
          <Clock className="h-3.5 w-3.5 text-muted-foreground" />
          <h2 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Session</h2>
        </div>
        <p className="text-[11px] text-muted-foreground mb-3 leading-relaxed">
          Your session is stored in <span className="font-mono text-[10px]">sessionStorage</span> and persists until you sign out or close this browser tab. It is never written to disk or shared across tabs.
        </p>
        <Button variant="outline" size="sm" className="gap-1.5 text-[11px] h-8 border-status-critical/30 text-status-critical hover:bg-status-critical/5 hover:border-status-critical/50" onClick={handleLogout}>
          <LogOut className="h-3 w-3" />
          Sign out
        </Button>
      </div>
    </div>
  );
}
