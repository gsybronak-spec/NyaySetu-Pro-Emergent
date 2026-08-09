import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "@/src/api/client";

interface User {
  id: string;
  mobile: string;
  name?: string | null;
  email?: string | null;
  bar_council_no?: string | null;
  state?: string | null;
  district?: string | null;
  court?: string | null;
}

interface AuthCtx {
  user: User | null;
  ready: boolean;
  loading: boolean;
  signInOtp: (mobile: string) => Promise<void>;
  verifyOtp: (mobile: string, otp: string) => Promise<{ is_new: boolean }>;
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
  setUser: (u: User | null) => void;
}

const Ctx = createContext<AuthCtx>(null as any);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    const t = await getToken();
    if (!t) {
      setUser(null);
      return;
    }
    try {
      const u = await api.me();
      setUser(u);
    } catch {
      await setToken(null);
      setUser(null);
    }
  }, []);

  useEffect(() => {
    refresh().finally(() => setReady(true));
  }, [refresh]);

  const signInOtp = async (mobile: string) => {
    setLoading(true);
    try {
      await api.sendOtp(mobile);
    } finally {
      setLoading(false);
    }
  };

  const verifyOtp = async (mobile: string, otp: string) => {
    setLoading(true);
    try {
      const res = await api.verifyOtp(mobile, otp);
      await setToken(res.token);
      setUser(res.user);
      return { is_new: res.is_new };
    } finally {
      setLoading(false);
    }
  };

  const signOut = async () => {
    await setToken(null);
    setUser(null);
  };

  return (
    <Ctx.Provider value={{ user, ready, loading, signInOtp, verifyOtp, refresh, signOut, setUser }}>
      {children}
    </Ctx.Provider>
  );
}

export const useAuth = () => useContext(Ctx);
