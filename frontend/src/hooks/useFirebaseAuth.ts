import {
  ConfirmationResult,
  RecaptchaVerifier,
  User,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signInWithPhoneNumber,
  signOut as fbSignOut,
} from "firebase/auth";

import { firebaseConfigured, getFirebaseAuth } from "@/src/firebase/config";

export { firebaseConfigured };

// Holds the phone-auth ConfirmationResult between the login screen and the OTP
// screen (the object cannot travel through router params). A page reload clears
// it — the user simply requests a fresh OTP.
let pendingConfirmation: ConfirmationResult | null = null;

// The invisible reCAPTCHA widget. Exactly ONE may exist at a time — a new
// instance is created per Send-OTP click and destroyed on error / unmount so
// no stale widget or iframe is ever left on the page.
let activeVerifier: RecaptchaVerifier | null = null;

function clearActiveVerifier() {
  if (activeVerifier) {
    try {
      activeVerifier.clear();
    } catch {
      // widget already cleared or detached — nothing to do
    }
    activeVerifier = null;
  }
}

export function getPendingPhoneConfirmation(): ConfirmationResult | null {
  return pendingConfirmation;
}

export function clearPendingPhoneConfirmation() {
  pendingConfirmation = null;
}

export function isFirebaseConfigured(): boolean {
  return firebaseConfigured;
}

/**
 * Firebase email/password sign-in. Returns the Firebase ID token when the
 * account exists in Firebase, null when Firebase is unconfigured, and throws
 * the original Firebase error otherwise (caller decides fallback).
 */
export async function firebaseEmailPasswordLogin(
  email: string,
  password: string
): Promise<{ idToken: string; firebaseUser: User } | null> {
  const auth = getFirebaseAuth();
  if (!auth) return null;
  const cred = await signInWithEmailAndPassword(auth, email.trim(), password);
  return { idToken: await cred.user.getIdToken(), firebaseUser: cred.user };
}

/**
 * Starts Firebase phone OTP with an INVISIBLE reCAPTCHA (size: "invisible").
 * Returns the ConfirmationResult (SMS already sent) or null when Firebase is
 * unconfigured. `verifierElement` is the DOM node to attach the invisible
 * widget to — the Send OTP button itself (RN Web View/Pressable ref) — so no
 * reCAPTCHA container is ever rendered on the login page. A previous verifier
 * (if any) is destroyed first; on error it is reset so a retry works.
 */
export async function firebaseSendPhoneOtp(
  mobile10: string,
  verifierElement: HTMLElement | string
): Promise<ConfirmationResult | null> {
  const auth = getFirebaseAuth();
  if (!auth) return null;
  // Never stack multiple verifier instances (invisible widget + iframe).
  clearActiveVerifier();
  const verifier = new RecaptchaVerifier(auth, verifierElement, {
    size: "invisible",
  });
  activeVerifier = verifier;
  try {
    const result = await signInWithPhoneNumber(auth, `+91${mobile10}`, verifier);
    pendingConfirmation = result;
    return result;
  } catch (e) {
    // Reset the widget so the next attempt initializes a fresh, working one.
    clearActiveVerifier();
    throw e;
  }
}

/**
 * Destroys the invisible reCAPTCHA widget. Call when leaving the login screen
 * (component unmount) or restarting the OTP flow so no widget is left behind.
 * The pending ConfirmationResult is intentionally NOT cleared here — the OTP
 * screen still needs it to verify the code.
 */
export function destroyFirebaseRecaptcha() {
  clearActiveVerifier();
}

/** Verifies the OTP on a pending Firebase phone-auth confirmation. Returns the
 * Firebase ID token; throws with the Firebase error on a wrong/expired OTP. */
export async function firebaseConfirmPhoneOtp(
  confirmation: ConfirmationResult,
  otp: string
): Promise<string> {
  const cred = await confirmation.confirm(otp);
  const idToken = await cred.user.getIdToken();
  pendingConfirmation = null;
  return idToken;
}

/** Firebase password reset email (no user enumeration — same message either way). */
export async function firebaseSendPasswordReset(email: string): Promise<boolean> {
  const auth = getFirebaseAuth();
  if (!auth) return false;
  await sendPasswordResetEmail(auth, email.trim());
  return true;
}

/** Signs the Firebase client out (no-op when unconfigured or signed out). */
export async function firebaseSignOutClient(): Promise<void> {
  const auth = getFirebaseAuth();
  if (!auth) return;
  try {
    await fbSignOut(auth);
  } catch {
    // best-effort — the NyaySetu JWT is the authoritative session
  }
  pendingConfirmation = null;
}
