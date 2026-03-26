import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { LogOut, User, Bell, Clock, Shield, Monitor, Database, Globe } from 'lucide-react';

export default function SettingsPage() {
  const { user, logout } = useAuth();

  return (
    <div className="max-w-2xl space-y-4">
      <div>
        <h1 className="text-[16px] font-semibold text-foreground">Settings</h1>
        <p className="text-[12px] text-muted-foreground mt-0.5">Account, security, and system configuration</p>
      </div>

      {/* Account */}
      <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
        <div className="flex items-center gap-2 mb-3">
          <User className="h-3.5 w-3.5 text-muted-foreground" />
          <h2 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Account</h2>
        </div>
        <div className="space-y-2 text-[12px]">
          <div className="flex gap-3"><span className="text-muted-foreground w-24 shrink-0">Name</span><span className="text-foreground font-medium">{user?.name}</span></div>
          <div className="flex gap-3"><span className="text-muted-foreground w-24 shrink-0">Email</span><span className="text-foreground font-mono text-[11px]">{user?.email}</span></div>
          <div className="flex gap-3"><span className="text-muted-foreground w-24 shrink-0">Role</span><span className="text-foreground">{user?.role}</span></div>
          <div className="flex gap-3"><span className="text-muted-foreground w-24 shrink-0">Department</span><span className="text-foreground">Managed Services — AIOps</span></div>
          <div className="flex gap-3"><span className="text-muted-foreground w-24 shrink-0">Region</span><span className="text-foreground">EMEA</span></div>
        </div>
      </div>

      {/* Notifications */}
      <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
        <div className="flex items-center gap-2 mb-3">
          <Bell className="h-3.5 w-3.5 text-muted-foreground" />
          <h2 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Notifications</h2>
        </div>
        <div className="space-y-2">
          {[
            { label: 'P1 incidents', desc: 'Immediate notification via Slack and email', enabled: true },
            { label: 'P2 incidents', desc: 'Notification via Slack channel', enabled: true },
            { label: 'SLA breach warnings', desc: '10 and 5 minute warnings', enabled: true },
            { label: 'Resolution confirmations', desc: 'Post-resolution summary', enabled: false },
          ].map((item) => (
            <div key={item.label} className="flex items-center justify-between py-1.5">
              <div>
                <p className="text-[12px] font-medium text-foreground">{item.label}</p>
                <p className="text-[10px] text-muted-foreground">{item.desc}</p>
              </div>
              <div className={`h-5 w-9 rounded-full ${item.enabled ? 'bg-accent' : 'bg-muted'} relative cursor-pointer transition-colors`}>
                <div className={`h-4 w-4 rounded-full bg-card border border-border absolute top-0.5 transition-all ${item.enabled ? 'left-[18px]' : 'left-0.5'}`} />
              </div>
            </div>
          ))}
        </div>
        <p className="text-[10px] text-muted-foreground mt-3 pt-3 border-t border-border">
          Routing rules are managed centrally by the Service Delivery Manager. Contact your SDM to adjust escalation thresholds.
        </p>
      </div>

      {/* Security */}
      <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
        <div className="flex items-center gap-2 mb-3">
          <Shield className="h-3.5 w-3.5 text-muted-foreground" />
          <h2 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">Security</h2>
        </div>
        <div className="space-y-2 text-[11px]">
          <div className="flex justify-between py-1"><span className="text-muted-foreground">Authentication</span><span className="text-foreground font-medium">SSO via SAML 2.0 (Atos Enterprise IdP)</span></div>
          <div className="flex justify-between py-1"><span className="text-muted-foreground">MFA</span><span className="text-status-healthy font-medium">Enforced</span></div>
          <div className="flex justify-between py-1"><span className="text-muted-foreground">Password policy</span><span className="text-foreground">Managed via enterprise identity provider</span></div>
          <div className="flex justify-between py-1"><span className="text-muted-foreground">Last login</span><span className="text-foreground font-mono text-[10px]">{new Date().toLocaleString('en-GB')}</span></div>
        </div>
      </div>

      {/* System info */}
      <div className="bg-card border border-border rounded-lg p-4 shadow-atlas">
        <div className="flex items-center gap-2 mb-3">
          <Monitor className="h-3.5 w-3.5 text-muted-foreground" />
          <h2 className="text-[12px] font-semibold text-foreground uppercase tracking-wider">System</h2>
        </div>
        <div className="space-y-2 text-[11px]">
          <div className="flex justify-between py-1"><span className="text-muted-foreground">Platform version</span><span className="font-mono text-foreground">ATLAS v2.4.1-prod</span></div>
          <div className="flex justify-between py-1"><span className="text-muted-foreground">Intelligence engine</span><span className="font-mono text-foreground">LangGraph v0.8.2 + ChromaDB</span></div>
          <div className="flex justify-between py-1"><span className="text-muted-foreground">Knowledge base</span><span className="text-foreground">2,847 incident records</span></div>
          <div className="flex justify-between py-1"><span className="text-muted-foreground">Playbooks loaded</span><span className="text-foreground">7 active</span></div>
          <div className="flex justify-between py-1"><span className="text-muted-foreground">Agent uptime</span><span className="text-status-healthy font-medium">99.97% (30d)</span></div>
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
          <LogOut className="h-3 w-3" /> Sign out
        </Button>
      </div>
    </div>
  );
}
