import { Platform } from "react-native";

export const RAZORPAY_SCRIPT_URL = "https://checkout.razorpay.com/v1/checkout.js";

/**
 * NyaySetu Pro Brand Colors for Razorpay Standard Checkout
 * Primary Brand Blue: #0B1B3D
 */
export const RAZORPAY_THEME_COLOR = "#0B1B3D";
export const RAZORPAY_BACKDROP_COLOR = "rgba(11, 27, 61, 0.65)";
export const RAZORPAY_LOGO_URL = "https://nyaysetupro.in/icons/pwa-192x192.v2.png";

let scriptPromise: Promise<void> | null = null;

/**
 * Check whether Razorpay Checkout is already loaded in the window.
 */
export function isRazorpayLoaded(): boolean {
  if (Platform.OS !== "web" || typeof window === "undefined") return false;
  return Boolean((window as any).Razorpay);
}

/**
 * Preload or load Razorpay script on demand with singleton promise to prevent duplicate injection.
 */
export function loadRazorpayScript(src = RAZORPAY_SCRIPT_URL): Promise<void> {
  if (Platform.OS !== "web" || typeof document === "undefined") {
    return Promise.resolve();
  }

  if ((window as any).Razorpay) {
    return Promise.resolve();
  }

  if (scriptPromise) {
    return scriptPromise;
  }

  const existing = document.querySelector<HTMLScriptElement>(`script[src="${src}"]`);
  if (existing) {
    scriptPromise = new Promise((resolve, reject) => {
      if ((window as any).Razorpay) {
        resolve();
      } else {
        existing.addEventListener("load", () => resolve(), { once: true });
        existing.addEventListener("error", () => reject(new Error("Could not load payment gateway")), { once: true });
      }
    });
    return scriptPromise;
  }

  scriptPromise = new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src;
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => {
      scriptPromise = null; // allow retry on error
      reject(new Error("Could not load payment gateway"));
    };
    document.head.appendChild(s);
  });

  return scriptPromise;
}

/**
 * Proactively prefetch the Razorpay Checkout script so it is ready before the user taps Pay.
 */
export function preloadRazorpayScript(): void {
  if (Platform.OS === "web" && typeof window !== "undefined") {
    loadRazorpayScript().catch(() => {
      // Silent catch on prefetch failure
    });
  }
}

/**
 * Prepare viewport before opening Razorpay modal:
 * Blurs active element to remove virtual keyboard and prevent viewport displacement downwards.
 */
export function prepareRazorpayModal(): void {
  if (Platform.OS === "web" && typeof document !== "undefined") {
    try {
      (document.activeElement as HTMLElement)?.blur?.();
    } catch {
      // Ignore
    }
  }
}
