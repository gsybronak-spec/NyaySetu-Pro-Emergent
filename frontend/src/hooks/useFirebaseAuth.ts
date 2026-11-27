import { Platform } from 'react-native';
import {
  ConfirmationResult,
  RecaptchaVerifier,
  User,
  confirmPasswordReset,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signInWithPhoneNumber,
  signOut as fbSignOut,
  verifyPasswordResetCode,
} from 'firebase/auth';

import { firebaseConfigured, getFirebaseAuth } from '@/src/firebase/config';

let nativeAuthMod: any = null;
if (Platform.OS !== 'web') {
  try {
    nativeAuthMod = require('@react-native-firebase/auth');
  } catch (e) {
    console.warn('React Native Firebase Auth not available', e);
  }
}

function getNativeAuth(): any | null {
  if (Platform.OS === 'web' || !nativeAuthMod) return null;
  try {
    if (typeof nativeAuthMod.getAuth === 'function') {
      return nativeAuthMod.getAuth();
    }
    if (typeof nativeAuthMod.default === 'function') {
      return nativeAuthMod.default();
    }
  } catch (e) {
    console.warn('Native Firebase Auth not initialized', e);
  }
  return null;
}

function callNativeAuth(fnName: string, authInstance: any, ...args: any[]) {
  if (typeof nativeAuthMod?.[fnName] === 'function') {
    return nativeAuthMod[fnName](authInstance, ...args);
  }
  if (typeof authInstance?.[fnName] === 'function') {
    return authInstance[fnName](...args);
  }
  throw new Error(`Native Firebase Auth method ${fnName} is unavailable`);
}

export { firebaseConfigured };

let pendingConfirmation: any | null = null;
let activeVerifier: RecaptchaVerifier | null = null;

function isVerifierValid(verifier: RecaptchaVerifier | null): boolean {
  if (!verifier) return false;
  if ((verifier as any).destroyed) return false;
  const container = (verifier as any).container;
  if (typeof document !== 'undefined' && container) {
    if (typeof container === 'string') {
      const el = document.getElementById(container);
      if (!el || !document.body.contains(el)) return false;
    } else if (container instanceof HTMLElement) {
      if (!document.body.contains(container)) return false;
    }
  }
  return true;
}

function resolveVerifierElement(
  verifierElement: HTMLElement | string | null
): HTMLElement | string | null {
  if (typeof document === 'undefined') return verifierElement;
  if (verifierElement && typeof verifierElement !== 'string' && (verifierElement as any).nodeType) {
    if (document.body.contains(verifierElement as HTMLElement)) {
      return verifierElement;
    }
  }
  if (typeof verifierElement === 'string') {
    const el = document.getElementById(verifierElement);
    if (el && document.body.contains(el)) return el;
  }
  const defaultEl = document.getElementById('recaptcha-container');
  if (defaultEl && document.body.contains(defaultEl)) {
    return defaultEl;
  }
  return verifierElement || 'recaptcha-container';
}

function clearActiveVerifier() {
  if (Platform.OS === 'web' && activeVerifier) {
    try {
      if (!(activeVerifier as any).destroyed) {
        activeVerifier.clear();
      }
    } catch {
    }
    activeVerifier = null;
  }
}

export function getPendingPhoneConfirmation(): any | null {
  return pendingConfirmation;
}

export function clearPendingPhoneConfirmation() {
  pendingConfirmation = null;
}

export function isFirebaseConfigured(): boolean {
  if (Platform.OS !== 'web') {
    return Boolean(getNativeAuth());
  }
  return firebaseConfigured;
}

export async function firebaseEmailPasswordLogin(
  email: string,
  password: string
): Promise<{ idToken: string; firebaseUser: any } | null> {
  if (Platform.OS === 'web') {
    const auth = getFirebaseAuth();
    if (!auth) return null;
    const cred = await signInWithEmailAndPassword(auth, email.trim(), password);
    return { idToken: await cred.user.getIdToken(), firebaseUser: cred.user };
  } else {
    const auth = getNativeAuth();
    if (!auth) return null;
    const cred = await callNativeAuth('signInWithEmailAndPassword', auth, email.trim(), password);
    const idToken =
      typeof cred.user?.getIdToken === 'function'
        ? await cred.user.getIdToken()
        : await nativeAuthMod.getIdToken(cred.user);
    return { idToken, firebaseUser: cred.user };
  }
}

export function getOrCreateRecaptchaVerifier(
  verifierElement: HTMLElement | string | null = 'recaptcha-container'
): RecaptchaVerifier | null {
  if (Platform.OS !== 'web') return null;
  const auth = getFirebaseAuth();
  if (!auth) return null;

  const target = resolveVerifierElement(verifierElement);

  if (activeVerifier && isVerifierValid(activeVerifier)) {
    return activeVerifier;
  }

  clearActiveVerifier();

  let mountTarget: HTMLElement | string = (target as any) || 'recaptcha-container';
  if (typeof document !== 'undefined') {
    let parentEl: HTMLElement | null = null;
    if (typeof target === 'string') {
      parentEl = document.getElementById(target);
    } else if (target && typeof target === 'object' && 'appendChild' in target) {
      parentEl = target as HTMLElement;
    }
    if (parentEl) {
      try {
        parentEl.innerHTML = '';
        const freshChild = document.createElement('div');
        freshChild.id = `recaptcha-mount-${Date.now()}`;
        parentEl.appendChild(freshChild);
        mountTarget = freshChild;
      } catch {}
    }
  }

  try {
    const verifier = new RecaptchaVerifier(auth, mountTarget as any, {
      size: 'invisible',
    });
    activeVerifier = verifier;
    return verifier;
  } catch (e) {
    console.warn('[useFirebaseAuth] could not initialize RecaptchaVerifier', e);
    return null;
  }
}

export async function firebaseSendPhoneOtp(
  mobile10: string,
  verifierElement: HTMLElement | string | null
): Promise<any | null> {
  if (Platform.OS === 'web') {
    const auth = getFirebaseAuth();
    if (!auth) return null;

    let verifier = getOrCreateRecaptchaVerifier(verifierElement);
    if (!verifier) {
      throw new Error('Could not initialize reCAPTCHA verifier. Please try again.');
    }

    try {
      const result = await signInWithPhoneNumber(auth, `+91${mobile10}`, verifier);
      pendingConfirmation = result;
      return result;
    } catch (e: any) {
      const msg = (e?.message || '').toLowerCase();
      // If error is reCAPTCHA related (e.g. client element removed, expired, destroyed), retry once with fresh verifier
      if (
        msg.includes('recaptcha') ||
        msg.includes('client element has been removed') ||
        msg.includes('destroyed') ||
        msg.includes('already rendered')
      ) {
        clearActiveVerifier();
        const retryVerifier = getOrCreateRecaptchaVerifier(verifierElement);
        if (retryVerifier) {
          try {
            const result = await signInWithPhoneNumber(auth, `+91${mobile10}`, retryVerifier);
            pendingConfirmation = result;
            return result;
          } catch (retryErr) {
            clearActiveVerifier();
            throw retryErr;
          }
        }
      }
      clearActiveVerifier();
      throw e;
    }
  } else {
    const auth = getNativeAuth();
    if (!auth) return null;
    const result = await callNativeAuth('signInWithPhoneNumber', auth, `+91${mobile10}`);
    pendingConfirmation = result;
    return result;
  }
}

export function destroyFirebaseRecaptcha() {
  clearActiveVerifier();
}

export async function firebaseConfirmPhoneOtp(
  confirmation: any,
  otp: string
): Promise<string> {
  const cred = await confirmation.confirm(otp);
  const idToken =
    typeof cred.user?.getIdToken === 'function'
      ? await cred.user.getIdToken()
      : await nativeAuthMod.getIdToken(cred.user);
  pendingConfirmation = null;
  return idToken;
}

export async function firebaseSendPasswordReset(email: string): Promise<boolean> {
  if (Platform.OS === 'web') {
    const auth = getFirebaseAuth();
    if (!auth) return false;
    await sendPasswordResetEmail(auth, email.trim());
    return true;
  } else {
    const auth = getNativeAuth();
    if (!auth) return false;
    await callNativeAuth('sendPasswordResetEmail', auth, email.trim());
    return true;
  }
}

export async function firebaseVerifyPasswordResetCode(code: string): Promise<string | null> {
  if (Platform.OS === 'web') {
    const auth = getFirebaseAuth();
    if (!auth) return null;
    return await verifyPasswordResetCode(auth, code);
  } else {
    const auth = getNativeAuth();
    if (!auth) return null;
    return await callNativeAuth('verifyPasswordResetCode', auth, code);
  }
}

export async function firebaseConfirmPasswordReset(code: string, newPassword: string): Promise<void> {
  if (Platform.OS === 'web') {
    const auth = getFirebaseAuth();
    if (!auth) throw new Error('Firebase Auth not available');
    await confirmPasswordReset(auth, code, newPassword);
  } else {
    const auth = getNativeAuth();
    if (!auth) throw new Error('Firebase Auth not available');
    await callNativeAuth('confirmPasswordReset', auth, code, newPassword);
  }
}

export async function firebaseSignOutClient(): Promise<void> {
  if (Platform.OS === 'web') {
    const auth = getFirebaseAuth();
    if (!auth) return;
    try {
      await fbSignOut(auth);
    } catch {}
  } else {
    const auth = getNativeAuth();
    if (!auth) return;
    try {
      await callNativeAuth('signOut', auth);
    } catch {}
  }
  pendingConfirmation = null;
}
