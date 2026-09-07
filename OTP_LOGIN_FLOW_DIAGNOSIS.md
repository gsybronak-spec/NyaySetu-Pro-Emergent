# OTP LOGIN FLOW FORENSIC DIAGNOSIS — NYAYSETU PRO

**Date**: 2026-09-07  
**Issue**: Live desktop testing on `https://nyaysetupro.in/login` $\rightarrow$ "Login with OTP" $\rightarrow$ "Send OTP" produced:  
`"OTP service is not configured. Please contact support."`  
**Target Backend**: `https://backend-gold-iota-nyngopebeg.vercel.app`  
**Target Frontend**: `https://nyaysetupro.in`  

---

## 1. Executive Summary

End-to-end verification previously confirmed that Firebase Phone Authentication is fully enabled and working at the infrastructure and API level:
- Firebase `sendVerificationCode` $\rightarrow$ HTTP 200 (Success)
- Firebase `signInWithPhoneNumber` $\rightarrow$ HTTP 200 (Success, issued Firebase ID token)
- Backend `POST /api/auth/firebase` $\rightarrow$ HTTP 200 (Success, issued NyaySetu JWT)
- Firestore user and wallet creation $\rightarrow$ Verified

However, on the live production frontend (`nyaysetupro.in/login`), selecting **Login $\rightarrow$ Use OTP** and clicking **Send OTP** displayed:
```text
"OTP service is not configured. Please contact support."
```

### Root Cause:
In `frontend/app/(auth)/login.tsx`, the `submitOtp` handler contains a **silent try/catch fall-through**:
```typescript
if (fbConfigured && Platform.OS === "web" && recaptchaAnchorRef.current) {
  try {
    await firebaseSendPhoneOtp(m, recaptchaAnchorRef.current as any);
    router.push({ pathname: "/(auth)/otp", params: { mobile: m, referral: referral.trim(), firebase: "1" } });
    return;
  } catch {
    // fall through to the existing OTP flow below
  }
}
try {
  await signInOtp(m);
  router.push({ pathname: "/(auth)/otp", params: { mobile: m, referral: referral.trim() } });
} catch (e: any) {
  setErr(e.message);
}
```

1. If `firebaseSendPhoneOtp` encounters **any exception** (or if `recaptchaAnchorRef.current` is not ready), the `catch` block on line 108 **silently discards the Firebase error**.
2. It then immediately executes `await signInOtp(m)`.
3. `signInOtp(m)` in `AuthContext.tsx` calls `api.sendOtp(m)` $\rightarrow$ `POST /api/auth/send-otp` on the backend.
4. On the production backend (`backend/server.py:721-726`), when `SMS_PROVIDER=console` (production default), the endpoint intentionally fails closed:
   ```python
   if SMS_PROVIDER in ("", "console"):
       if not _DEV_OTP_ALLOWED:
           raise HTTPException(503, "OTP service is not configured. Please contact support.")
   ```
5. `login.tsx` catches this 503 error and sets `setErr(e.message)`, rendering the confusing message: `"OTP service is not configured. Please contact support."`

In contrast, `frontend/app/(auth)/signup.tsx` **does not have this silent fall-through**. When Firebase fails in `signup.tsx`, it catches and displays the actual Firebase error to the user without calling `api.sendOtp`.

---

## 2. Comparison: Signup UI vs Login UI

| Aspect | `signup.tsx` | `login.tsx` |
|:---|:---|:---|
| **Primary Route** | Firebase Phone Auth (`firebaseSendPhoneOtp`) | Firebase Phone Auth (`firebaseSendPhoneOtp`) |
| **Error Handling** | Transparent: maps Firebase error codes (`auth/too-many-requests`, `auth/invalid-phone-number`, `auth/operation-not-allowed`) to clear messages. | Opaque: catches all errors silently and falls through to `signInOtp`. |
| **Fallback Route** | Only calls `api.sendOtp` if `firebaseConfigured` is `false` (local dev). | Calls `signInOtp` on **any** Firebase error, masking the real error. |
| **DOM Anchor** | `<View ref={recaptchaAnchorRef} />` is permanently mounted in the component. | `<View ref={recaptchaAnchorRef} />` is conditionally mounted only when `mode === "otp"`. |

---

## 3. Architecture Confirmation

- **Production OTP Login Architecture**:
  Must use Firebase native Phone Authentication exclusively:
  $$\text{Client Phone Input} \longrightarrow \text{Firebase Invisible reCAPTCHA} \longrightarrow \text{Firebase SMS Delivery} \longrightarrow \text{OTP Entry} \longrightarrow \text{Firebase ID Token} \longrightarrow \text{POST /api/auth/firebase} \longrightarrow \text{NyaySetu JWT / Session}$$
- **Role of `POST /api/auth/send-otp`**:
  - A backend-orchestrated SMS gateway fallback designed for direct SMS providers (e.g. MSG91 DLT approved).
  - Intentionally disabled (`503`) in production because `SMS_PROVIDER=console`.
  - Must **not** be called as an automatic fallback when Firebase Phone Auth encounters an error.

---

## 4. Proposed Minimum Code Fix

### File to Modify: `frontend/app/(auth)/login.tsx`

#### Change 1: Remove Silent Fall-through in `submitOtp`
Replace lines 92–118 with:
```typescript
  const submitOtp = async () => {
    setErr(undefined);
    const m = mobile.trim();
    if (!/^\d{10}$/.test(m)) {
      setErr("Enter a valid 10-digit mobile number");
      return;
    }
    try {
      if (fbConfigured && Platform.OS === "web" && recaptchaAnchorRef.current) {
        await firebaseSendPhoneOtp(m, recaptchaAnchorRef.current as any);
        router.push({ pathname: "/(auth)/otp", params: { mobile: m, referral: referral.trim(), firebase: "1" } });
        return;
      }
      // Development/testing fallback when Firebase is not configured
      await signInOtp(m);
      router.push({ pathname: "/(auth)/otp", params: { mobile: m, referral: referral.trim() } });
    } catch (e: any) {
      const code = e?.code as string | undefined;
      if (code === "auth/operation-not-allowed" || code === "auth/unauthorized-continue-uri") {
        setErr("SMS OTP is temporarily unavailable for this region. Please try again later or use password login.");
      } else if (code === "auth/too-many-requests") {
        setErr("Too many OTP requests. Please wait a minute and try again.");
      } else if (code === "auth/invalid-phone-number") {
        setErr("Enter a valid 10-digit mobile number.");
      } else if (code === "auth/quota-exceeded") {
        setErr("SMS quota exceeded for today. Please use password login or contact support.");
      } else {
        setErr(e?.message || "Could not send OTP. Please try again.");
      }
    }
  };
```

#### Change 2: Ensure reCAPTCHA Anchor is Permanently Mounted
Move:
```tsx
{fbConfigured && Platform.OS === "web" && (
  <View ref={recaptchaAnchorRef as any} style={styles.recaptchaAnchor} collapsable={false} />
)}
```
outside the `{mode === "password" ? (...) : (...)}` conditional block so it is always present in the DOM tree when switching tabs.

---

## 5. Test Plan (10 Comprehensive Scenarios)

1. **Login $\rightarrow$ Use OTP $\rightarrow$ Send OTP**: Enter test number `+919999999999`, verify invisible reCAPTCHA triggers and navigates to `/(auth)/otp` with `firebase="1"`.
2. **OTP Verification**: Enter code `123456`, verify `firebaseConfirmPhoneOtp` succeeds.
3. **Existing Firebase User Login**: Confirms user document is matched by `firebase_uid`/`mobile`, `is_new=False`, existing wallet and cases are linked.
4. **New Firebase User Signup**: In `signup.tsx`, test number creates account, `is_new=True`, initial wallet of 5 credits created.
5. **Wrong OTP**: Enter `000000`, verify Firebase rejects with `auth/invalid-verification-code` and surfaces user-friendly error without crashing.
6. **Expired OTP**: Stale sessionInfo produces clear error message prompting resend.
7. **Duplicate Prevention**: Re-login with same mobile produces no duplicate Firestore document (`where('mobile', '==', ...)` count remains exactly 1).
8. **Session Persistence**: Refreshing page keeps session intact; `/api/profile/me` succeeds with stored JWT.
9. **Logout**: Signing out clears NyaySetu JWT and Firebase client session; returns to `/login`.
10. **Google Login Invariant**: "Continue with Google" remains 100% functional, untouched.

---

## 6. Audit & Safety Invariants

- **Backend Code**: Untouched
- **Firestore Schema & Data**: Untouched
- **MongoDB**: Untouched
- **Google Auth**: Untouched
- **SMS Gateway**: None added (uses Firebase Phone Auth directly)
- **Secrets Exposed**: None
