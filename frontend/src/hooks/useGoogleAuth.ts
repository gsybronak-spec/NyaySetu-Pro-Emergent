import { useCallback, useEffect, useRef, useState } from "react";
import { Platform } from "react-native";
import * as WebBrowser from "expo-web-browser";
import * as Linking from "expo-linking";
import { router } from "expo-router";

import { useAuth } from "@/src/context/AuthContext";
import { storage } from "@/src/utils/storage";

WebBrowser.maybeCompleteAuthSession();

// Native Google OAuth (Authorization Code flow). The client ID is public by
// design; the client SECRET lives only on the backend, which exchanges the code.
// Without EXPO_PUBLIC_GOOGLE_CLIENT_ID the flow is disabled (clear message),
// never faked. The Emergent auth page is fully removed from this flow.
const GOOGLE_CLIENT_ID = process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID || "";
const GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth";
const GOOGLE_SCOPES = "openid email profile";
const PENDING_REF_KEY = "nyaysetu_pending_referral";

function extractCode(url?: string | null): string | null {
  if (!url) return null;
  const m = url.match(/[?#&]code=([^&#]+)/);
  return m ? decodeURIComponent(m[1]) : null;
}

function extractError(url?: string | null): string | null {
  if (!url) return null;
  const m = url.match(/[?#&]error=([^&#]+)/);
  return m ? decodeURIComponent(m[1]).replace(/_/g, " ") : null;
}

function buildAuthUrl(redirectUri: string, state: string): string {
  const params = [
    `client_id=${encodeURIComponent(GOOGLE_CLIENT_ID)}`,
    `redirect_uri=${encodeURIComponent(redirectUri)}`,
    "response_type=code",
    `scope=${encodeURIComponent(GOOGLE_SCOPES)}`,
    "prompt=select_account",
    "access_type=online",
    `state=${encodeURIComponent(state)}`,
  ];
  return `${GOOGLE_AUTH_URL}?${params.join("&")}`;
}

export function useGoogleAuth() {
  const { completeGoogleCode } = useAuth();
  const [busy, setBusy] = useState(false);
  const [googleError, setGoogleError] = useState("");
  const processed = useRef<Set<string>>(new Set());

  const exchange = useCallback(
    async (code: string, redirectUri: string) => {
      if (!code || processed.current.has(code)) return;
      processed.current.add(code);
      setBusy(true);
      try {
        const referral = (await storage.getItem(PENDING_REF_KEY, "")) || undefined;
        const { is_new } = await completeGoogleCode(code, redirectUri, referral);
        await storage.removeItem(PENDING_REF_KEY);
        if (Platform.OS === "web") {
          // Clean the code from the URL after success
          try {
            const clean = window.location.origin + window.location.pathname;
            window.history.replaceState(window.history.state, "", clean);
          } catch {}
        }
        router.replace(is_new ? "/(auth)/onboarding" : "/(tabs)/home");
      } catch (e: any) {
        setGoogleError(e?.message || "Google login failed. Please try again.");
      } finally {
        setBusy(false);
      }
    },
    [completeGoogleCode]
  );

  // Handle cold-start (mobile) and mount detection (web) with an auth code
  useEffect(() => {
    let sub: any;
    (async () => {
      if (Platform.OS === "web") {
        const code =
          extractCode(window.location.hash) || extractCode(window.location.search);
        const err = extractError(window.location.hash) || extractError(window.location.search);
        if (err) setGoogleError(err);
        if (code) {
          const redirectUri = window.location.origin + "/";
          await exchange(code, redirectUri);
        }
      } else {
        sub = Linking.addEventListener("url", ({ url }) => {
          const code = extractCode(url);
          const err = extractError(url);
          if (err) setGoogleError(err);
          if (code) exchange(code, Linking.createURL(""));
        });
        const initial = await Linking.getInitialURL();
        const code = extractCode(initial);
        if (code) await exchange(code, Linking.createURL(""));
      }
    })();
    return () => sub?.remove?.();
  }, [exchange]);

  const startGoogleLogin = useCallback(
    async (referralCode?: string) => {
      if (!GOOGLE_CLIENT_ID) {
        setGoogleError(
          "Google login is not configured yet. Please use OTP or contact support."
        );
        return false;
      }
      setGoogleError("");
      setBusy(true);
      try {
        if (referralCode) await storage.setItem(PENDING_REF_KEY, referralCode);
        else await storage.removeItem(PENDING_REF_KEY);

        const redirectUri =
          Platform.OS === "web" ? window.location.origin + "/" : Linking.createURL("");
        const state = `${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
        const authUrl = buildAuthUrl(redirectUri, state);

        if (Platform.OS === "web") {
          window.location.href = authUrl;
          return true;
        }
        const result = await WebBrowser.openAuthSessionAsync(authUrl, redirectUri);
        let code: string | null = null;
        let err: string | null = null;
        if (result.type === "success" && (result as any).url) {
          code = extractCode((result as any).url);
          err = extractError((result as any).url);
        }
        if (err) {
          setGoogleError(err);
          return false;
        }
        if (!code) {
          const initial = await Linking.getInitialURL();
          code = extractCode(initial);
        }
        if (code) {
          await exchange(code, redirectUri);
          return true;
        }
        setGoogleError("Google login did not return an authorization code.");
        return false;
      } catch (e: any) {
        setGoogleError(e?.message || "Google login failed. Please try again.");
        return false;
      } finally {
        if (Platform.OS !== "web") setBusy(false);
      }
    },
    [exchange]
  );

  return { startGoogleLogin, googleBusy: busy, googleError, setGoogleError };
}
