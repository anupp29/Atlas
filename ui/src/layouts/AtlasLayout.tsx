import { useAuth } from '@/contexts/AuthContext';
import { AppSidebar } from '@/components/atlas/AppSidebar';
import { TopBar } from '@/components/atlas/TopBar';
import { ActivityFeed } from '@/components/atlas/ActivityFeed';
import { mockActivityFeed } from '@/data/mock';

export function AtlasLayout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();

  if (user?.role === 'CLIENT') {
    return (
      <div className="flex min-h-screen w-full bg-background">
        <div className="flex-1 flex flex-col">
          <TopBar />
          <main className="flex-1 p-6">{children}</main>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen w-full bg-background">
      <AppSidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <div className="flex-1 flex min-h-0">
          <main className="flex-1 p-6 overflow-auto">{children}</main>
          <aside className="hidden 2xl:flex w-[280px] border-l border-border bg-card flex-col shrink-0">
            <div className="px-4 py-3 border-b border-border flex items-center justify-between">
              <h2 className="text-[11px] font-semibold text-foreground uppercase tracking-wider">Activity Feed</h2>
              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-status-healthy live-dot" />
                <span className="text-[9px] text-muted-foreground">Live</span>
              </div>
            </div>
            <div className="flex-1 overflow-auto">
              <ActivityFeed entries={mockActivityFeed} />
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
