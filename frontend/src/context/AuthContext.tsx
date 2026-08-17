import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, getToken, setOnUnauthorized, setToken } from "@/src/api/client";
import { firebaseSignOutClient } from "@/src/hooks/useFirebaseAuth";

interface User {
  id: string;
  mobile: string;
  name?: string | null;
  email?: string | null;
  bar_council_no?: string | null;
  state?: string | null;
  district?: string | null;
  court?: string | null;
  has_password?: boolean;
}

interface AuthCtx {
  user: User | null;
  ready: boolean;
  loading: boolean;
  signInOtp: (mobile: string) => Promise<void>;
  verifyOtp: (mobile: string, otp: string, referralCode?: string) => Promise<{ is_new: boolean }>;
  signInPassword: (identifier: string, password: string, referralCode?: string) => Promise<{ is_new: boolean }>;
  registerAccount: (data: { mobile: string; otp: string; password: string; name?: string; email?: string; referralCode?: string }) => Promise<{ is_new: boolean }>;
  completeGoogleCode: (code: string, redirectUri: string, referralCode?: string) => Promise<{ is_new: boolean }>;
  firebaseExchange: (idToken: string, referralCode?: string) => Promise<{ is_new: boolean }>;
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
      await storage.remove("nyaysetu_user_profile");
      return;
    }
    // Load cached profile immediately for instant UI render
    try {
      const cached = await storage.get("nyaysetu_user_profile", null as any);
      if (cached && typeof cached === "object" && cached.id) {
        setUser(cached);
      }
    } catch {
      // Ignore cache read error
    }

    try {
      const u = await api.me();
      if (u && typeof u === "object") {
        setUser(u);
        await storage.set("nyaysetu_user_profile", u);
      }
    } catch (err: any) {
      console.warn("[AuthContext] Background refresh failed, preserving session", err);
      // Only 401 triggers logout (handled by client.ts onUnauthorized callback).
      // On network errors, 5xx, timeouts, or cold starts: KEEP existing session and token!
    }
  }, []);

  useEffect(() => {
    refresh().finally(() => setReady(true));
  }, [refresh]);

  // C4: any 401 from the API clears the in-memory session so the tabs route
  // guard redirects to login instead of leaving the user on a broken screen.
  useEffect(() => {
    setOnUnauthorized(async () => {
      setUser(null);
      await storage.remove("nyaysetu_user_profile");
    });
    return () => setOnUnauthorized(null);
  }, []);

  const signInOtp = async (mobile: string) => {
    setLoading(true);
    try {
      await api.sendOtp(mobile);
    } finally {
      setLoading(false);
    }
  };

  const verifyOtp = async (mobile: string, otp: string, referralCode?: string) => {
    setLoading(true);
    try {
      const res = await api.verifyOtp(mobile, otp, referralCode);
      await setToken(res.token);
      setUser(res.user);
      if (res.user) await storage.set("nyaysetu_user_profile", res.user);
      return { is_new: res.is_new };
    } finally {
      setLoading(false);
    }
  };

  const signInPassword = async (identifier: string, password: string, referralCode?: string) => {
    setLoading(true);
    try {
      const res = await api.login(identifier, password, referralCode);
      await setToken(res.token);
      setUser(res.user);
      if (res.user) await storage.set("nyaysetu_user_profile", res.user);
      return { is_new: res.is_new };
    } finally {
      setLoading(false);
    }
  };

  const registerAccount = async (data: { mobile: string; otp: string; password: string; name?: string; email?: string; referralCode?: string }) => {
    setLoading(true);
    try {
      const res = await api.register({
        mobile: data.mobile,
        otp: data.otp,
        password: data.password,
        name: data.name,
        email: data.email,
        referral_code: data.referralCode,
      });
      await setToken(res.token);
      setUser(res.user);
      if (res.user) await storage.set("nyaysetu_user_profile", res.user);
      return { is_new: res.is_new };
    } finally {
      setLoading(false);
    }
  };

  const completeGoogleCode = async (code: string, redirectUri: string, referralCode?: string) => {
    setLoading(true);
    try {
      const res = await api.googleExchange(code, redirectUri, referralCode);
      await setToken(res.token);
      setUser(res.user);
      if (res.user) await storage.set("nyaysetu_user_profile", res.user);
      return { is_new: res.is_new };
    } finally {
      setLoading(false);
    }
  };

  const firebaseExchange = async (idToken: string, referralCode?: string) => {
    setLoading(true);
    try {
      const res = await api.firebaseAuth(idToken, referralCode);
      await setToken(res.token);
      setUser(res.user);
      if (res.user) await storage.set("nyaysetu_user_profile", res.user);
      return { is_new: res.is_new };
    } finally {
      setLoading(false);
    }
  };

  const signOut = async () => {
    await setToken(null);
    setUser(null);
    await storage.remove("nyaysetu_user_profile");
    // Clear the Firebase client session too (no-op when Firebase is not
    // configured). The NyaySetu JWT removal is authoritative either way.
    await firebaseSignOutClient();
  };

  return (
    <Ctx.Provider value={{ user, ready, loading, signInOtp, verifyOtp, signInPassword, registerAccount, completeGoogleCode, firebaseExchange, refresh, signOut, setUser }}>
      {children}
    </Ctx.Provider>
  );
}

export const useAuth = () => useContext(Ctx);
