import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';
import type { User, UserRole } from '@/types/atlas';

const SESSION_KEY = 'atlas_session';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => boolean;
  logout: () => void;
  switchRole: (role: UserRole) => void;
}

type SessionUser = User & {
  homeRole?: UserRole;
};

const AuthContext = createContext<AuthContextType | null>(null);

function loadSession(): SessionUser | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as SessionUser) : null;
  } catch {
    return null;
  }
}

function saveSession(user: SessionUser): void {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(user));
}

function clearSession(): void {
  sessionStorage.removeItem(SESSION_KEY);
}

export function AuthProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  const [user, setUser] = useState<SessionUser | null>(loadSession);

  const inferRoleFromEmail = useCallback((email: string): UserRole => {
    const normalized = email.trim().toLowerCase();
    if (
      normalized.includes('sdm')
      || normalized.includes('srm')
      || normalized.includes('manager')
      || normalized.includes('service.delivery')
      || normalized.includes('service.reliability')
    ) {
      return 'SDM';
    }
    if (normalized.includes('client') || normalized.endsWith('@client.atos.net')) {
      return 'CLIENT';
    }
    if (normalized.includes('l1') || normalized.includes('tier1') || normalized.includes('ops1')) {
      return 'L1';
    }
    if (normalized.includes('l3') || normalized.includes('sre') || normalized.includes('platform')) {
      return 'L3';
    }
    if (normalized.includes('l2') || normalized.includes('tier2')) {
      return 'L2';
    }
    return 'L2';
  }, []);

  const login = useCallback((email: string, _password: string) => {
    const role = inferRoleFromEmail(email);
    const name = email.split('@')[0].split('.').map(p => p.charAt(0).toUpperCase() + p.slice(1)).join(' ');
    const newUser: SessionUser = {
      id: `user-${role}-${Date.now()}`,
      name,
      email,
      role,
      homeRole: role,
    };
    saveSession(newUser);
    setUser(newUser);
    return true;
  }, [inferRoleFromEmail]);

  const logout = useCallback(() => {
    clearSession();
    setUser(null);
  }, []);

  const switchRole = useCallback((role: UserRole) => {
    setUser(prev => {
      if (!prev) return null;
      const controllerRole = prev.homeRole || prev.role;
      if (controllerRole !== 'SDM') {
        return prev;
      }
      const updated = { ...prev, role };
      saveSession(updated);
      return updated;
    });
  }, []);

  const contextValue = useMemo(() => ({
    user,
    isAuthenticated: !!user,
    login,
    logout,
    switchRole,
  }), [user, login, logout, switchRole]);

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
