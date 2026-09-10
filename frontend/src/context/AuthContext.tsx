import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { onAuthStateChanged } from "firebase/auth";
import { api, getRefreshToken, getToken, setOnUnauthorized, setTokens } from "@/src/api/client";
import { firebaseSignOutClient } from "@/src/hooks/useFirebaseAuth";
import { getFirebaseAuth } from "@/src/firebase/config";
import { storage } from "@/src/utils/storage";

interface User {
  id: string;
  mobile?: string | null;
  name?: string | null;
  first_name?: string | null;
  middle_name?: string | null;
  last_name?: string | null;
  gender?: string | null;
  dob?: string | null;
  email?: string | null;
  picture?: string | null;
  bar_council_no?: string | null;
  advocate_name_en?: string | null;
  advocate_name_gu?: string | null;
  state?: string | null;
  district?: string | null;
  user_type?: string | null;
  provider?: string | null;
  has_password?: boolean;
  is_profile_complete?: boolean;
  profile_completed?: boolean;
  wallet_balance?: number;
  total_credits_used?: number;
  unlimited_access?: boolean;
  is_owner?: boolean;
  is_partner?: boolean;
}

interface AuthResult {
  is_new: boolean;
  is_profile_complete?: boolean;
  profile_completed?: boolean;
}

interface AuthCtx {
  user: User | null;
  ready: boolean;
  loading: boolean;
  signInOtp: (mobile: string) => Promise<void>;
  verifyOtp: (mobile: string, otp: string, referralCode?: string) => Promise<AuthResult>;
  signInPassword: (identifier: string, password: string, referralCode?: string) => Promise<AuthResult>;
  registerAccount: (data: { mobile: string; otp: string; password: string; name?: string; email?: string; referralCode?: string }) => Promise<AuthResult>;
  completeGoogleCode: (code: string, redirectUri: string, referralCode?: string) => Promise<AuthResult>;
  firebaseExchange: (idToken: string, referralCode?: string) => Promise<AuthResult>;
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
    // Load cached profile immediately for instant UI render
    let cachedUser: any = null;
    try {
      cachedUser = await storage.get("nyaysetu_user_profile", null as any);
      if (cachedUser && typeof cachedUser === "object" && cachedUser.id) {
        setUser(cachedUser);
      }
    } catch {
      // Ignore cache read error
    }

    const [token, refreshToken] = await Promise.all([getToken(), getRefreshToken()]);

    if (!token && !refreshToken) {
      // If local tokens are absent, check if Firebase has an active authenticated user
      const fbAuth = await getFirebaseAuth();
      if (fbAuth?.currentUser) {
        try {
          console.info("[AuthContext] Active Firebase session detected, establishing backend session...");
          const idToken = await fbAuth.currentUser.getIdToken(true);
          const res = await api.firebaseAuth(idToken);
          await setTokens(res.token, res.refresh_token);
          setUser(res.user);
          if (res.user) await storage.set("nyaysetu_user_profile", res.user);
          return;
        } catch (fbErr) {
          console.warn("[AuthContext] Firebase startup session restoration failed", fbErr);
        }
      }
      setUser(null);
      await storage.remove("nyaysetu_user_profile");
      return;
    }

    try {
      const u = await api.me();
      if (u && typeof u === "object") {
        setUser(u);
        await storage.set("nyaysetu_user_profile", u);
      }
    } catch (err: any) {
      console.warn("[AuthContext] Background user validation failed, preserving session", err);
      // On network errors, 5xx, timeouts, or cold starts: KEEP existing session and token!
      if (cachedUser && typeof cachedUser === "object" && cachedUser.id) {
        setUser(cachedUser);
      }
    }
  }, []);

  useEffect(() => {
    refresh().finally(() => setReady(true));
  }, [refresh]);

  // Listen to Firebase Auth state transitions (handles asynchronous Web IndexedDB restore)
  useEffect(() => {
    const fbAuth = getFirebaseAuth();
    if (!fbAuth) return;
    const unsubscribe = onAuthStateChanged(fbAuth, async (fbUser) => {
      if (fbUser) {
        const [token, refreshToken] = await Promise.all([getToken(), getRefreshToken()]);
        if (!token && !refreshToken) {
          try {
            console.info("[AuthContext] onAuthStateChanged restored user, syncing backend session...");
            const idToken = await fbUser.getIdToken();
            const res = await api.firebaseAuth(idToken);
            await setTokens(res.token, res.refresh_token);
            setUser(res.user);
            if (res.user) await storage.set("nyaysetu_user_profile", res.user);
          } catch (e) {
            console.warn("[AuthContext] onAuthStateChanged silent exchange failed", e);
          }
        }
      }
    });
    return () => unsubscribe();
  }, []);

  // Live profile & wallet sync: periodically sync latest credits/profile from backend (throttled)
  useEffect(() => {
    if (!user?.id) return;
    let inFlight = false;
    let lastSyncAt = Date.now();

    const syncWallet = async (force = false) => {
      const now = Date.now();
      if (!force && (now - lastSyncAt < 30000 || inFlight)) return;
      if (typeof document !== "undefined" && document.hidden) return;
      inFlight = true;
      try {
        const u = await api.me();
        if (u && typeof u === "object") {
          lastSyncAt = Date.now();
          setUser((prev) => (prev ? { ...prev, ...u } : u));
          storage.set("nyaysetu_user_profile", u);
        }
      } catch {
        // Silently ignore background sync failures
      } finally {
        inFlight = false;
      }
    };

    const interval = setInterval(() => syncWallet(true), 60000);
    const onFocus = () => { syncWallet(false); };
    if (typeof window !== "undefined") {
      window.addEventListener("focus", onFocus);
      document.addEventListener("visibilitychange", onFocus);
    }
    return () => {
      clearInterval(interval);
      if (typeof window !== "undefined") {
        window.removeEventListener("focus", onFocus);
        document.removeEventListener("visibilitychange", onFocus);
      }
    };
  }, [user?.id]);

  // C4: definitive unauthorized callback with Firebase recovery attempt before logout
  useEffect(() => {
    setOnUnauthorized(async () => {
      const fbAuth = getFirebaseAuth();
      if (fbAuth?.currentUser) {
        try {
          console.info("[AuthContext] Backend session rejected, attempting silent Firebase recovery...");
          const idToken = await fbAuth.currentUser.getIdToken(true);
          const res = await api.firebaseAuth(idToken);
          await setTokens(res.token, res.refresh_token);
          setUser(res.user);
          if (res.user) await storage.set("nyaysetu_user_profile", res.user);
          return;
        } catch (fbErr) {
          console.warn("[AuthContext] Firebase re-authentication recovery failed", fbErr);
        }
      }
      setUser(null);
      await storage.remove("nyaysetu_user_profile");
    });
    return () => setOnUnauthorized(null);
  }, []);

  // Multi-tab synchronization (web): listen for storage events to sync login/logout
  useEffect(() => {
    if (typeof window === "undefined" || !window.addEventListener) return;
    const handleStorage = (e: StorageEvent) => {
      if (e.key === "nyaysetu_token" || e.key === "nyaysetu_refresh_token") {
        if (!e.newValue) {
          setUser(null);
          storage.remove("nyaysetu_user_profile").catch(() => {});
        } else {
          refresh();
        }
      }
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, [refresh]);

  const signInOtp = async (mobile: string) => {
    setLoading(true);
    try {
      await api.sendOtp(mobile);
    } finally {
      setLoading(false);
    }
  };

  const verifyOtp = async (mobile: string, otp: string, referralCode?: string): Promise<AuthResult> => {
    setLoading(true);
    try {
      const res = await api.verifyOtp(mobile, otp, referralCode);
      await setTokens(res.token, res.refresh_token);
      setUser(res.user);
      if (res.user) await storage.set("nyaysetu_user_profile", res.user);
      return {
        is_new: res.is_new,
        is_profile_complete: res.user?.is_profile_complete ?? res.user?.profile_completed,
        profile_completed: res.user?.profile_completed ?? res.user?.is_profile_complete,
      };
    } finally {
      setLoading(false);
    }
  };

  const signInPassword = async (identifier: string, password: string, referralCode?: string): Promise<AuthResult> => {
    setLoading(true);
    try {
      const res = await api.login(identifier, password, referralCode);
      await setTokens(res.token, res.refresh_token);
      setUser(res.user);
      if (res.user) await storage.set("nyaysetu_user_profile", res.user);
      return {
        is_new: res.is_new,
        is_profile_complete: res.user?.is_profile_complete ?? res.user?.profile_completed,
        profile_completed: res.user?.profile_completed ?? res.user?.is_profile_complete,
      };
    } finally {
      setLoading(false);
    }
  };

  const registerAccount = async (data: { mobile: string; otp: string; password: string; name?: string; email?: string; referralCode?: string }): Promise<AuthResult> => {
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
      await setTokens(res.token, res.refresh_token);
      setUser(res.user);
      if (res.user) await storage.set("nyaysetu_user_profile", res.user);
      return {
        is_new: res.is_new,
        is_profile_complete: res.user?.is_profile_complete ?? res.user?.profile_completed,
        profile_completed: res.user?.profile_completed ?? res.user?.is_profile_complete,
      };
    } finally {
      setLoading(false);
    }
  };

  const completeGoogleCode = async (code: string, redirectUri: string, referralCode?: string): Promise<AuthResult> => {
    setLoading(true);
    try {
      const res = await api.googleExchange(code, redirectUri, referralCode);
      await setTokens(res.token, res.refresh_token);
      setUser(res.user);
      if (res.user) await storage.set("nyaysetu_user_profile", res.user);
      return {
        is_new: res.is_new,
        is_profile_complete: res.user?.is_profile_complete ?? res.user?.profile_completed,
        profile_completed: res.user?.profile_completed ?? res.user?.is_profile_complete,
      };
    } finally {
      setLoading(false);
    }
  };

  const firebaseExchange = async (idToken: string, referralCode?: string): Promise<AuthResult> => {
    setLoading(true);
    try {
      const res = await api.firebaseAuth(idToken, referralCode);
      await setTokens(res.token, res.refresh_token);
      setUser(res.user);
      if (res.user) await storage.set("nyaysetu_user_profile", res.user);
      return {
        is_new: res.is_new,
        is_profile_complete: res.user?.is_profile_complete ?? res.user?.profile_completed,
        profile_completed: res.user?.profile_completed ?? res.user?.is_profile_complete,
      };
    } finally {
      setLoading(false);
    }
  };

  const signOut = async () => {
    try {
      const refreshToken = await getRefreshToken();
      await api.logout(refreshToken || undefined);
    } catch (e) {
      console.warn("[AuthContext] Logout API call error (proceeding with local cleanup)", e);
    }
    await setTokens(null, null);
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
