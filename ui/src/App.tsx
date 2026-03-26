import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { AtlasLayout } from "@/layouts/AtlasLayout";
import Login from "./pages/Login";
import Portfolio from "./pages/Portfolio";
import Incidents from "./pages/Incidents";
import AuditLog from "./pages/AuditLog";
import Playbooks from "./pages/Playbooks";
import ClientPortal from "./pages/ClientPortal";
import SettingsPage from "./pages/Settings";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

function DefaultRedirect() {
  const { user } = useAuth();
  // SDM → Portfolio, L1/L2/L3 → Incidents, CLIENT → Portal
  if (user?.role === 'SDM') return <Navigate to="/portfolio" replace />;
  if (user?.role === 'CLIENT') return <Navigate to="/portal" replace />;
  return <Navigate to="/incidents" replace />;
}

function ProtectedRoutes() {
  const { isAuthenticated, user } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (user?.role === 'CLIENT') {
    return (
      <AtlasLayout>
        <Routes>
          <Route path="/portal" element={<ClientPortal />} />
          <Route path="*" element={<Navigate to="/portal" replace />} />
        </Routes>
      </AtlasLayout>
    );
  }

  return (
    <AtlasLayout>
      <Routes>
        <Route path="/portfolio" element={<Portfolio />} />
        <Route path="/incidents" element={<Incidents />} />
        <Route path="/playbooks" element={<Playbooks />} />
        <Route path="/audit" element={<AuditLog />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/" element={<DefaultRedirect />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </AtlasLayout>
  );
}

function AppRoutes() {
  const { isAuthenticated, user } = useAuth();

  const defaultPath = user?.role === 'SDM' ? '/portfolio' :
                      user?.role === 'CLIENT' ? '/portal' : '/incidents';

  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to={defaultPath} replace /> : <Login />} />
      <Route path="/*" element={<ProtectedRoutes />} />
    </Routes>
  );
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
