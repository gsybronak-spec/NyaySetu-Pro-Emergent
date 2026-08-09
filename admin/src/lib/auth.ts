import React from 'react';
import { adminApi } from './api';

export interface AdminUser {
  id: string;
  email: string;
  name: string;
  role: string;
  active: boolean;
  last_login: string | null;
  created_at: string;
}

interface AuthContextType {
  admin: AdminUser | null;
  loading: boolean;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = React.createContext<AuthContextType>(null as any);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [admin, setAdmin] = React.useState<AdminUser | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [ready, setReady] = React.useState(false);

  React.useEffect(() => {
    const token = localStorage.getItem('admin_token');
    if (!token) {
      setReady(true);
      return;
    }
    adminApi.me()
      .then((data) => setAdmin(data))
      .catch(() => {
        localStorage.removeItem('admin_token');
        setAdmin(null);
      })
      .finally(() => setReady(true));
  }, []);

  const login = async (email: string, password: string) => {
    setLoading(true);
    try {
      const res = await adminApi.login(email, password);
      localStorage.setItem('admin_token', res.token);
      setAdmin(res.admin);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('admin_token');
    setAdmin(null);
  };

  return React.createElement(
    AuthContext.Provider,
    { value: { admin, loading, ready, login, logout } },
    children
  );
}

export function useAdminAuth() {
  return React.useContext(AuthContext);
}
