import { initializeApp, getApp, getApps, FirebaseApp } from "firebase/app";
import { getAuth, Auth } from "firebase/auth";

/**
 * Firebase client configuration — activated ONLY when every required value is
 * present in the environment (EXPO_PUBLIC_FIREBASE_*). Until the Firebase
 * Console web-app values are added to Vercel, `firebaseConfigured` is false and
 * the app keeps using the existing NyaySetu auth flows untouched (safe-fail).
 *
 * The API key here is the public web API key from Firebase Console → Project
 * settings → General → Your apps → SDK setup and configuration. It is NOT a
 * secret and must never be confused with a Firebase service-account private
 * key, which belongs only in the backend and never in the client.
 */
const cfg = {
  apiKey: process.env.EXPO_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.EXPO_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.EXPO_PUBLIC_FIREBASE_APP_ID,
};

export const firebaseConfigured = Boolean(
  cfg.apiKey && cfg.authDomain && cfg.projectId && cfg.appId
);

let _app: FirebaseApp | null = null;
let _auth: Auth | null = null;

export function getFirebaseApp(): FirebaseApp | null {
  if (!firebaseConfigured) return null;
  if (!_app) {
    _app = getApps().length > 0 ? getApp() : initializeApp(cfg as any);
  }
  return _app;
}

export function getFirebaseAuth(): Auth | null {
  if (!firebaseConfigured) return null;
  if (!_auth) {
    const app = getFirebaseApp();
    if (!app) return null;
    _auth = getAuth(app);
  }
  return _auth;
}
