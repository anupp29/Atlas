import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import type { User, UserRole } from '@/types/atlas';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => boolean;
  logout: () => void;
  switchRole: (role: UserRole) => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

const roleUsers: Record<UserRole, User> = {
  L1: { id: 'u1', name: 'A. Petrov', email: 'a.petrov@atos.net', role: 'L1' },
  L2: { id: 'u2', name: 'S. Weber', email: 's.weber@atos.net', role: 'L2' },
  L3: { id: 'u3', name: 'J. Nakamura', email: 'j.nakamura@atos.net', role: 'L3' },
  SDM: { id: 'u4', name: 'C. Laurent', email: 'c.laurent@atos.net', role: 'SDM' },
  CLIENT: { id: 'u5', name: 'Dr. R. Hartley', email: 'r.hartley@nht.nhs.uk', role: 'CLIENT' },
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [roleChangeCount, setRoleChangeCount] = useState(0);

  const login = useCallback((email: string, _password: string) => {
    const found = Object.values(roleUsers).find(u => u.email === email);
    if (found) {
      setUser(found);
      return true;
    }
    setUser(roleUsers.L2);
    return true;
  }, []);

  const logout = useCallback(() => setUser(null), []);

  const switchRole = useCallback((role: UserRole) => {
    setUser(roleUsers[role]);
    setRoleChangeCount(c => c + 1);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, logout, switchRole }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
