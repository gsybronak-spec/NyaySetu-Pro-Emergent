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

const getCachedAdmin = (): AdminUser | null => {
  try {
    const raw = localStorage.getItem('admin_user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [admin, setAdmin] = React.useState<AdminUser | null>(getCachedAdmin);
  const [loading, setLoading] = React.useState(false);
  const [ready, setReady] = React.useState(false);

  React.useEffect(() => {
    const handleUnauthorized = () => {
      localStorage.removeItem('admin_token');
      localStorage.removeItem('admin_refresh_token');
      localStorage.removeItem('admin_user');
      setAdmin(null);
    };

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'admin_token' && !e.newValue) {
        // Explicit logout in another tab
        setAdmin(null);
      } else if (e.key === 'admin_user' && e.newValue) {
        // Login or profile sync from another tab
        try {
          setAdmin(JSON.parse(e.newValue));
        } catch {}
      }
    };

    window.addEventListener('admin:unauthorized', handleUnauthorized);
    window.addEventListener('storage', handleStorageChange);

    const token = localStorage.getItem('admin_token');
    const refreshToken = localStorage.getItem('admin_refresh_token');

    if (!token && !refreshToken) {
      setAdmin(null);
      setReady(true);
      return () => {
        window.removeEventListener('admin:unauthorized', handleUnauthorized);
        window.removeEventListener('storage', handleStorageChange);
      };
    }

    // Verify or refresh session on startup
    adminApi.me()
      .then((data) => {
        setAdmin(data);
        localStorage.setItem('admin_user', JSON.stringify(data));
      })
      .catch((_err) => {
        // Transient network failure or server cold start:
        // Do NOT log out. Retain cached admin state.
        // If it was a definitive 401 from /auth/refresh, handleUnauthorized already fired.
      })
      .finally(() => {
        setReady(true);
      });

    return () => {
      window.removeEventListener('admin:unauthorized', handleUnauthorized);
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  const login = async (email: string, password: string) => {
    setLoading(true);
    try {
      const res = await adminApi.login(email, password);
      localStorage.setItem('admin_token', res.token);
      if (res.refresh_token) {
        localStorage.setItem('admin_refresh_token', res.refresh_token);
      }
      localStorage.setItem('admin_user', JSON.stringify(res.admin));
      setAdmin(res.admin);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    adminApi.logout().catch(() => {});
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_refresh_token');
    localStorage.removeItem('admin_user');
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
