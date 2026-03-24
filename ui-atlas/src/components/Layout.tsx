import { Outlet } from 'react-router-dom';
import { TopNavBar } from './TopNavBar';
import { SideNavBar } from './SideNavBar';

export function Layout() {
  return (
    <div className="flex flex-col min-h-screen">
      <TopNavBar />
      <div className="flex pt-14">
        <SideNavBar />
        <main className="ml-64 flex-1 overflow-y-auto bg-surface p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
