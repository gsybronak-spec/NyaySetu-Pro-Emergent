# OTP LOGIN FIX VERIFICATION — NYAYSETU PRO

**Date**: 2026-09-07  
**Status**: VERIFIED & DEPLOYED TO PRODUCTION  
**Production Frontend**: `https://nyaysetupro.in`  
**Frontend Deployment ID**: `dpl_yQAzTmVf2sSeRgNQuab1zjbRxFuK`  
**Production Backend**: `https://backend-gold-iota-nyngopebeg.vercel.app`  
**Backend Deployment ID**: `dpl_7iB2KSM6Tt9tWy1WnYxGHZUFAsaH`  
**Firebase Project**: `nyaysetu-pro`  
**Cloud Firestore Location**: `asia-south1 (Mumbai)`  

---

## 1. Summary of Changes

### Root Cause Resolved
In `frontend/app/(auth)/login.tsx`:
- The previous `submitOtp` implementation contained a silent `try / catch` that caught any Firebase exception (or missing DOM anchor) and fell through to `await signInOtp(m)` $\rightarrow$ `POST /api/auth/send-otp`.
- On the backend, `POST /api/auth/send-otp` failed closed (`HTTP 503 "OTP service is not configured. Please contact support."`) because `SMS_PROVIDER=console` in production.
- In addition, the invisible reCAPTCHA anchor was conditionally mounted inside `mode === "otp"`, risking unmounted ref timing issues when toggling from Password to OTP.

### Code Fix Applied (`frontend/app/(auth)/login.tsx`)
1. **Removed Silent Fall-through**:
   - The production web application now routes OTP requests exclusively to Firebase Phone Auth (`firebaseSendPhoneOtp`).
   - If Firebase Phone Auth throws an error (quota, invalid phone number, rate limit, region block), it is caught and surfaced directly to the user using the same user-friendly mapping as `signup.tsx`.
   - It **never** falls through to `signInOtp()` or `POST /api/auth/send-otp` in production.
2. **Permanent reCAPTCHA Anchor Mounting**:
   - Moved `<View ref={recaptchaAnchorRef as any} style={styles.recaptchaAnchor} collapsable={false} />` outside the mode toggle to the root of `KeyboardAvoidingView`.
   - Guarantees `recaptchaAnchorRef.current` is permanently mounted in the DOM across mode switching.
3. **Reused Existing Pipeline**:
   - Reuses `firebaseSendPhoneOtp()`, `otp.tsx`, and `POST /api/auth/firebase` token exchange.
   - Zero backend changes; zero Firestore schema changes; MongoDB untouched.

---

## 2. Build & Production Deployment

1. **TypeScript Type Check**: `npx tsc --noEmit` $\rightarrow$ **PASS** (0 errors)
2. **Local Production Build**: `npm run build` $\rightarrow$ **PASS**
   - Injected PWA metadata & Anek Gujarati fonts
   - Admin portal bundle synchronized
   - Verified production bundle contains:
     - `backend-gold-iota-nyngopebeg.vercel.app`
     - `nyaysetu-pro`
     - 0 occurrences of `127.0.0.1` or `demobackend`
3. **Vercel Production Deployment**:
   - Project: `nyay-setu-pro-emergent-bo83`
   - Deployment ID: `dpl_yQAzTmVf2sSeRgNQuab1zjbRxFuK`
   - Production Domain: `https://nyaysetupro.in`
   - Status: **READY / ALIASED**

---

## 3. End-to-End Live Verification Results

Live test execution against `https://nyaysetupro.in` and `https://backend-gold-iota-nyngopebeg.vercel.app`:

| Test Step | Verification Action | Live Result | Status |
|:---|:---|:---|:---:|
| **1. Send OTP** | `accounts:sendVerificationCode` (`+919999999999`) | HTTP 200 OK (`sessionInfo` received) | **PASS** |
| **2. Verify OTP** | `accounts:signInWithPhoneNumber` (code `123456`) | HTTP 200 OK (Firebase ID token + UID) | **PASS** |
| **3. Token Exchange** | `POST /api/auth/firebase` | HTTP 200 OK (`is_new=True`, NyaySetu JWT) | **PASS** |
| **4. User & Wallet** | Firestore validation | User doc verified; wallet created with 5 credits | **PASS** |
| **5. Re-Login Flow** | Repeated sign-in with same number | HTTP 200 OK (`is_new=False`, same user ID) | **PASS** |
| **6. Duplicate Guard** | Firestore duplicate count | Exactly 1 user document in collection | **PASS** |
| **7. Session** | `GET /api/profile/me` with JWT | HTTP 200 OK (Authenticated profile loaded) | **PASS** |
| **8. Cleanup** | Firestore cleanup | Temporary test user & wallet safely deleted | **PASS** |

---

## 4. Instructions for Real Physical Android Device Acceptance

To perform final physical verification on your Android phone:

1. Open **Chrome** (or your mobile browser) and navigate to:
   ```text
   https://nyaysetupro.in/login
   ```
2. Tap **Use OTP** tab.
3. Enter the configured dedicated Firebase test number:
   ```text
   9999999999
   ```
4. Tap **Send OTP**.
   - *Expected*: The screen advances to `/otp` ("Verify OTP" with "+91 9999999999"). The message *"OTP service is not configured"* will **NOT** appear.
5. In the 6-digit OTP input, enter:
   ```text
   123456
   ```
6. Tap **Verify & Continue**.
   - *Expected*: Authentication succeeds, Firebase exchanges token for NyaySetu session, and you are redirected directly to the **Home dashboard** (or Profile Completion if testing a new user).
7. Refresh the page:
   - *Expected*: Session persists; you remain logged in.
8. Tap **Sign Out**:
   - *Expected*: Session clears cleanly and returns to `/login`.
