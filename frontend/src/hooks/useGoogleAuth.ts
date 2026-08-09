import { useCallback, useEffect, useRef, useState } from "react";
import { Platform } from "react-native";
import * as WebBrowser from "expo-web-browser";
import * as Linking from "expo-linking";
import { router } from "expo-router";

import { useAuth } from "@/src/context/AuthContext";
import { storage } from "@/src/utils/storage";

WebBrowser.maybeCompleteAuthSession();

const AUTH_BASE = "https://auth.emergentagent.com/";
const PENDING_REF_KEY = "nyaysetu_pending_referral";

function extractSessionId(url?: string | null): string | null {
  if (!url) return null;
  const m = url.match(/[?#&]session_id=([^&#]+)/);
  return m ? decodeURIComponent(m[1]) : null;
}

export function useGoogleAuth() {
  const { completeGoogleSession } = useAuth();
  const [busy, setBusy] = useState(false);
  const processed = useRef<Set<string>>(new Set());

  const exchange = useCallback(
    async (sessionId: string) => {
      if (!sessionId || processed.current.has(sessionId)) return;
      processed.current.add(sessionId);
      setBusy(true);
      try {
        const referral = (await storage.getItem(PENDING_REF_KEY, "")) || undefined;
        const { is_new } = await completeGoogleSession(sessionId, referral);
        await storage.removeItem(PENDING_REF_KEY);
        if (Platform.OS === "web") {
          // Clean the session_id from the URL after success
          try {
            const clean = window.location.origin + window.location.pathname;
            window.history.replaceState(window.history.state, "", clean);
          } catch {}
        }
        router.replace(is_new ? "/(auth)/onboarding" : "/(tabs)/home");
      } catch (e) {
        // silent; caller can retry
      } finally {
        setBusy(false);
      }
    },
    [completeGoogleSession]
  );

  // Handle cold-start (mobile) and mount detection (web)
  useEffect(() => {
    let sub: any;
    (async () => {
      if (Platform.OS === "web") {
        const sid = extractSessionId(window.location.hash) || extractSessionId(window.location.search);
        if (sid) await exchange(sid);
      } else {
        sub = Linking.addEventListener("url", ({ url }) => {
          const sid = extractSessionId(url);
          if (sid) exchange(sid);
        });
        const initial = await Linking.getInitialURL();
        const sid = extractSessionId(initial);
        if (sid) await exchange(sid);
      }
    })();
    return () => sub?.remove?.();
  }, [exchange]);

  const startGoogleLogin = useCallback(
    async (referralCode?: string) => {
      setBusy(true);
      try {
        if (referralCode) await storage.setItem(PENDING_REF_KEY, referralCode);
        else await storage.removeItem(PENDING_REF_KEY);

        const redirectUrl =
          Platform.OS === "web" ? window.location.origin + "/" : Linking.createURL("");
        const authUrl = `${AUTH_BASE}?redirect=${encodeURIComponent(redirectUrl)}`;

        if (Platform.OS === "web") {
          window.location.href = authUrl;
          return;
        }
        const result = await WebBrowser.openAuthSessionAsync(authUrl, redirectUrl);
        let sid: string | null = null;
        if (result.type === "success" && (result as any).url) {
          sid = extractSessionId((result as any).url);
        }
        if (!sid) {
          const initial = await Linking.getInitialURL();
          sid = extractSessionId(initial);
        }
        if (sid) await exchange(sid);
      } finally {
        if (Platform.OS !== "web") setBusy(false);
      }
    },
    [exchange]
  );

  return { startGoogleLogin, googleBusy: busy };
}
