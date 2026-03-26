import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { LogOut, User, Bell, Clock, Shield } from 'lucide-react';

export default function SettingsPage() {
  const { user, logout } = useAuth();

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
        <div className="space-y-2 text-[12px]">
          <div className="flex gap-3">
            <span className="text-muted-foreground w-20 shrink-0">Name</span>
            <span className="text-foreground">{user?.name}</span>
          </div>
          <div className="flex gap-3">
            <span className="text-muted-foreground w-20 shrink-0">Email</span>
            <span className="text-foreground font-mono text-[11px]">{user?.email}</span>
          </div>
          <div className="flex gap-3">
            <span className="text-muted-foreground w-20 shrink-0">Role</span>
            <span className="text-foreground">{user?.role}</span>
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
          Notification routing rules are managed centrally by the Service Delivery Manager. Contact your SDM to adjust incident routing, escalation thresholds, or notification channels.
        </p>
      </div>

      {/* Security */}
      <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
        <div className="flex items-center gap-2 mb-2">
          <Shield className="h-3.5 w-3.5 text-muted-foreground" />
          <h2 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Security</h2>
        </div>
        <div className="space-y-1.5 text-[11px] text-muted-foreground">
          <p>Authentication: SSO via SAML 2.0 (Atos Enterprise IdP)</p>
          <p>MFA: Enforced for all roles</p>
          <p>Password policy: Managed via enterprise identity provider</p>
        </div>
      </div>

      {/* Session */}
      <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
        <div className="flex items-center gap-2 mb-2">
          <Clock className="h-3.5 w-3.5 text-muted-foreground" />
          <h2 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Session</h2>
        </div>
        <p className="text-[11px] text-muted-foreground mb-3">
          Sessions expire after 8 hours of inactivity. Expiry redirects to login with a session expired message.
        </p>
        <Button variant="outline" size="sm" className="gap-1.5 text-[11px] h-7" onClick={logout}>
          <LogOut className="h-3 w-3" />
          Sign out
        </Button>
      </div>
    </div>
  );
}
