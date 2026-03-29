import { useState, useEffect, useRef } from 'react';
import { Bell, AlertTriangle, Clock, Search, Wifi, WifiOff, Activity } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useAtlasData } from '@/contexts/AtlasDataContext';
import { CountdownTimer } from './CountdownTimer';
import { PriorityBadge } from './PriorityBadge';
import { ActivityDrawer } from './ActivityDrawer';

const roleLabels = {
  L1: 'L1 Engineer',
  L2: 'L2 Engineer',
  L3: 'L3 / SRE',
  SDM: 'Service Delivery Manager',
  CLIENT: 'Client Portal',
} as const;

const roleContexts = {
  L1: 'First-line triage and approval',
  L2: 'Operational investigation and modification',
  L3: 'Engineering debugging and manual override',
  SDM: 'Portfolio oversight and SLA governance',
  CLIENT: 'Read-only service transparency',
} as const;

export function TopBar() {
  const { user } = useAuth();
  const { incidents, activityFeed, backendConnected, isLoading } = useAtlasData();
  const p1Incidents = incidents.filter(i => i.priority === 'P1' && i.status !== 'Resolved');
  const activeCount = incidents.filter(i => i.status !== 'Resolved').length;
  const role = (user?.role || 'L2') as keyof typeof roleLabels;

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  // Use a ref to track the feed length at the time the drawer was last closed/opened
  // This avoids the race condition where newCount could go negative
  const lastSeenLengthRef = useRef(0);

  useEffect(() => {
    if (drawerOpen) {
      // Drawer opened — mark everything as seen
      lastSeenLengthRef.current = activityFeed.length;
      setUnreadCount(0);
    } else {
      // Drawer closed — count genuinely new entries since last seen
      const newEntries = activityFeed.length - lastSeenLengthRef.current;
      if (newEntries > 0) {
        setUnreadCount(newEntries);
      }
    }
  }, [activityFeed.length, drawerOpen]);

  const handleOpenDrawer = () => {
    setDrawerOpen(true);
    setUnreadCount(0);
    lastSeenLengthRef.current = activityFeed.length;
  };

  return (
    <>
      <header className="h-14 border-b border-border bg-card flex items-center justify-between px-5 shrink-0 z-30 relative">
        <div className="flex items-center gap-4 min-w-0">
          <div className="hidden xl:flex flex-col min-w-[220px]">
            <span className="text-[11px] font-semibold text-foreground uppercase tracking-wider">{roleLabels[role]}</span>
            <span className="text-[10px] text-muted-foreground leading-tight">{roleContexts[role]}</span>
          </div>

          {p1Incidents.map(inc => (
            <div key={inc.id} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-destructive/[0.06] border border-destructive/15">
              <AlertTriangle className="h-3.5 w-3.5 text-status-critical" />
              <span className="text-[12px] font-medium text-foreground">{inc.clientName}</span>
              <PriorityBadge priority="P1" />
              <div className="flex items-center gap-1 ml-1">
                <Clock className="h-3 w-3 text-status-critical" />
                <CountdownTimer deadline={inc.slaDeadline} className="text-[11px]" />
              </div>
            </div>
          ))}

          {p1Incidents.length === 0 && activeCount > 0 && (
            <span className="text-[12px] text-muted-foreground">{activeCount} active incident{activeCount !== 1 ? 's' : ''}</span>
          )}
          {activeCount === 0 && (
            <span className="text-[12px] text-muted-foreground">All clear — no active incidents</span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-muted/50 border border-border text-muted-foreground">
            <Search className="h-3.5 w-3.5" />
            <span className="text-[11px]">Search...</span>
            <kbd className="text-[9px] bg-background border border-border rounded px-1 py-0.5 ml-4 font-mono">⌘K</kbd>
          </div>

          {/* Backend status */}
          <div className="hidden sm:flex items-center gap-1.5 px-2 py-1 rounded-lg">
            {isLoading ? (
              <span className="text-[10px] text-muted-foreground">connecting…</span>
            ) : backendConnected ? (
              <>
                <Wifi className="h-3 w-3 text-status-healthy" />
                <span className="text-[10px] text-status-healthy font-medium">Live</span>
              </>
            ) : (
              <>
                <WifiOff className="h-3 w-3 text-muted-foreground" />
                <span className="text-[10px] text-muted-foreground">Demo</span>
              </>
            )}
          </div>

          {/* Activity feed button */}
          <button
            onClick={handleOpenDrawer}
            className="relative p-2 rounded-lg hover:bg-muted transition-colors duration-150 flex items-center gap-1.5"
            title="Activity Feed"
          >
            <Activity className="h-4 w-4 text-muted-foreground" />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 h-4 min-w-[16px] px-0.5 rounded-full bg-accent text-accent-foreground text-[9px] font-bold flex items-center justify-center tabular-nums">
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </button>

          {/* Notifications bell */}
          <button className="relative p-2 rounded-lg hover:bg-muted transition-colors duration-150">
            <Bell className="h-4 w-4 text-muted-foreground" />
            {p1Incidents.length > 0 && (
              <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-status-critical live-dot" />
            )}
          </button>

          <div className="h-6 w-px bg-border" />

          {/* User avatar */}
          <div className="flex items-center gap-2.5">
            <div className="h-7 w-7 rounded-full bg-primary flex items-center justify-center">
              <span className="text-[10px] font-semibold text-primary-foreground">
                {user?.name?.split(' ').map(n => n[0]).join('').slice(0, 2)}
              </span>
            </div>
            <div className="hidden sm:flex flex-col">
              <span className="text-[12px] font-medium text-foreground leading-tight">{user?.name}</span>
              <span className="text-[10px] text-muted-foreground leading-tight">{roleLabels[role]}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Activity Drawer */}
      <ActivityDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        entries={activityFeed}
      />
    </>
  );
}
