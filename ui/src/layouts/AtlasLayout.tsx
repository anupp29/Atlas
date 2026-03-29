import { useAuth } from '@/contexts/AuthContext';
import { AppSidebar } from '@/components/atlas/AppSidebar';
import { TopBar } from '@/components/atlas/TopBar';

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
        <main className="flex-1 p-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
