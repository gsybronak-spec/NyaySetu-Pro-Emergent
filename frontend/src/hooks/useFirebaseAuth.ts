import { Platform } from 'react-native';
import type {
  ConfirmationResult,
  RecaptchaVerifier,
  User,
} from 'firebase/auth';

import { firebaseConfigured, getFirebaseAuth } from '@/src/firebase/config';

let nativeAuth: any = null;
if (Platform.OS !== 'web') {
  try {
    nativeAuth = require('@react-native-firebase/auth').default;
  } catch (e) {
    console.warn('React Native Firebase Auth not available', e);
  }
}

export { firebaseConfigured };

let pendingConfirmation: any | null = null;
let activeVerifier: RecaptchaVerifier | null = null;

function clearActiveVerifier() {
  if (Platform.OS === 'web' && activeVerifier) {
    try {
      activeVerifier.clear();
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
    return !!nativeAuth;
  }
  return firebaseConfigured;
}

export async function firebaseEmailPasswordLogin(
  email: string,
  password: string
): Promise<{ idToken: string; firebaseUser: any } | null> {
  if (Platform.OS === 'web') {
    const auth = await getFirebaseAuth();
    if (!auth) return null;
    const { signInWithEmailAndPassword } = await import('firebase/auth');
    const cred = await signInWithEmailAndPassword(auth, email.trim(), password);
    return { idToken: await cred.user.getIdToken(), firebaseUser: cred.user };
  } else {
    if (!nativeAuth) return null;
    const cred = await nativeAuth().signInWithEmailAndPassword(email.trim(), password);
    return { idToken: await cred.user.getIdToken(), firebaseUser: cred.user };
  }
}

export async function getOrCreateRecaptchaVerifier(
  verifierElement: HTMLElement | string | null = 'recaptcha-container'
): Promise<RecaptchaVerifier | null> {
  if (Platform.OS !== 'web') return null;
  const auth = await getFirebaseAuth();
  if (!auth) return null;
  if (activeVerifier) return activeVerifier;
  try {
    const { RecaptchaVerifier } = await import('firebase/auth');
    const verifier = new RecaptchaVerifier(auth, verifierElement as any, {
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
    const auth = await getFirebaseAuth();
    if (!auth) return null;
    let verifier = activeVerifier;
    if (!verifier) {
      verifier = await getOrCreateRecaptchaVerifier(verifierElement);
      activeVerifier = verifier;
    }
    try {
      const { signInWithPhoneNumber } = await import('firebase/auth');
      const result = await signInWithPhoneNumber(auth, `+91${mobile10}`, verifier as any);
      pendingConfirmation = result;
      return result;
    } catch (e) {
      clearActiveVerifier();
      throw e;
    }
  } else {
    if (!nativeAuth) return null;
    const result = await nativeAuth().signInWithPhoneNumber(`+91${mobile10}`);
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
  const idToken = await cred.user.getIdToken();
  pendingConfirmation = null;
  return idToken;
}

export async function firebaseSendPasswordReset(email: string): Promise<boolean> {
  if (Platform.OS === 'web') {
    const auth = await getFirebaseAuth();
    if (!auth) return false;
    const { sendPasswordResetEmail } = await import('firebase/auth');
    await sendPasswordResetEmail(auth, email.trim());
    return true;
  } else {
    if (!nativeAuth) return false;
    await nativeAuth().sendPasswordResetEmail(email.trim());
    return true;
  }
}

export async function firebaseSignOutClient(): Promise<void> {
  if (Platform.OS === 'web') {
    const auth = await getFirebaseAuth();
    if (!auth) return;
    try {
      const { signOut } = await import('firebase/auth');
      await signOut(auth);
    } catch {}
  } else {
    if (!nativeAuth) return;
    try {
      await nativeAuth().signOut();
    } catch {}
  }
  pendingConfirmation = null;
}
