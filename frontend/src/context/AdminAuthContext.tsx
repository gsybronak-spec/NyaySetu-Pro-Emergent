import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { adminApi, getAdminToken, setAdminToken, setOnAdminUnauthorized } from "@/src/api/adminClient";
import type { AdminUser } from "@/src/types/admin";
import { storage } from "@/src/utils/storage";

interface AdminAuthCtx {
  adminUser: AdminUser | null;
  token: string | null;
  ready: boolean;
  loading: boolean;
  isAuthenticated: boolean;
  isSuperAdmin: boolean;
  signIn: (email: string, password: string) => Promise<AdminUser>;
  signOut: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AdminCtx = createContext<AdminAuthCtx>(null as any);

const ADMIN_PROFILE_CACHE_KEY = "nyaysetu_admin_profile";

export function AdminAuthProvider({ children }: { children: React.ReactNode }) {
  const [adminUser, setAdminUser] = useState<AdminUser | null>(null);
  const [token, setTokenState] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    const t = await getAdminToken();
    setTokenState(t);
    if (!t) {
      setAdminUser(null);
      await storage.remove(ADMIN_PROFILE_CACHE_KEY);
      return;
    }

    try {
      const cached = await storage.get(ADMIN_PROFILE_CACHE_KEY, null as any);
      if (cached && typeof cached === "object" && cached.id) {
        setAdminUser(cached);
      }
    } catch {
      // Ignore cache error
    }

    try {
      const profile = await adminApi.me();
      if (profile && profile.id) {
        setAdminUser(profile);
        await storage.set(ADMIN_PROFILE_CACHE_KEY, profile);
      }
    } catch (err) {
      console.warn("[AdminAuthContext] profile fetch failed", err);
    }
  }, []);

  useEffect(() => {
    refresh().finally(() => setReady(true));
  }, [refresh]);

  useEffect(() => {
    setOnAdminUnauthorized(async () => {
      setAdminUser(null);
      setTokenState(null);
      await storage.remove(ADMIN_PROFILE_CACHE_KEY);
    });
    return () => setOnAdminUnauthorized(null);
  }, []);

  const signIn = async (email: string, password: string): Promise<AdminUser> => {
    setLoading(true);
    try {
      const res = await adminApi.login(email.trim(), password);
      await setAdminToken(res.token);
      setTokenState(res.token);
      setAdminUser(res.admin);
      await storage.set(ADMIN_PROFILE_CACHE_KEY, res.admin);
      return res.admin;
    } finally {
      setLoading(false);
    }
  };

  const signOut = async () => {
    setLoading(true);
    try {
      try {
        await adminApi.logout();
      } catch {
        // Ignore logout network error
      }
      await setAdminToken(null);
      setTokenState(null);
      setAdminUser(null);
      await storage.remove(ADMIN_PROFILE_CACHE_KEY);
    } finally {
      setLoading(false);
    }
  };

  const isAuthenticated = !!adminUser && !!token;
  const isSuperAdmin = adminUser?.role === "super_admin";

  return (
    <AdminCtx.Provider
      value={{
        adminUser,
        token,
        ready,
        loading,
        isAuthenticated,
        isSuperAdmin,
        signIn,
        signOut,
        refresh,
      }}
    >
      {children}
    </AdminCtx.Provider>
  );
}

export function useAdminAuth() {
  const ctx = useContext(AdminCtx);
  if (!ctx) {
    throw new Error("useAdminAuth must be used within an AdminAuthProvider");
  }
  return ctx;
}
