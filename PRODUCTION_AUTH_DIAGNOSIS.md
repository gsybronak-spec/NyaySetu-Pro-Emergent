# Production Authentication Forensic Diagnosis Report — NyaySetu Pro

**Date**: September 7, 2026  
**Environment**: LIVE PRODUCTION  
**Production URLs**:
- Frontend: `https://nyaysetupro.in`
- Backend API: `https://backend-gold-iota-nyngopebeg.vercel.app`
- Database: Google Cloud Firestore `nyaysetu-pro` (`asia-south1`, Mumbai)

---

## Executive Summary

A forensic code-level and live-log investigation was performed to diagnose the real-device authentication behavior reported by the project owner.

### Verified Status of Real-Device Flows:
- **Google Sign-In**: **PARTIAL PASS (Core Auth Succeeded)**
  - Google OAuth token exchange: **PASS**
  - User document creation in Firestore: **PASS** (Created user `44e94708-90d6-4851-bcc4-4e1bf9c75c1d`)
  - Wallet creation with 5 signup credits: **PASS** (Created wallet `44b218b3-7da9-4c60-afa4-134d64d0c769`)
  - Redirection to `/profile-completion` ("Complete Your Profile"): **PASS**
- **Profile Completion Save API**: **BLOCKED (Backend Index Exception)**
  - `PUT /api/profile/update` crashed with `FailedPrecondition (400)` due to a composite inequality query on Firestore users collection without an index.
- **Login via OTP**: **BLOCKED**
  - Backend returned HTTP 503 `"OTP service is not configured. Please contact support."` because `SMS_PROVIDER` is unconfigured (`console`) in `ENVIRONMENT=production`.
- **Signup via OTP**: **BLOCKED**
  - Frontend showed `"SMS OTP is temporarily unavailable for this region"` because Phone Provider is not enabled in Firebase Console for `nyaysetu-pro` (`auth/operation-not-allowed`).
- **Password Login**: **BLOCKED / EXPECTED FOR NEW ACCOUNTS**
  - Returned HTTP 401 `"Invalid mobile/email or password."` because no user with that credential had been registered yet in the clean Firestore database.

---

## Step 1: Trace of the Google Profile Completion Failure

### Concrete Evidence from Live Vercel Production Logs:
```text
TIME         HOST                                     LEVEL                   
13:29:18.80  backend-gold-iota-nyngopebeg.vercel.app  info   λ OPTIONS /api/auth/google          
13:29:19.07  backend-gold-iota-nyngopebeg.vercel.app  info   λ POST /api/auth/google             
HTTP Request: POST https://oauth2.googleapis.com/token "HTTP/1.1 200 OK"
HTTP Request: GET https://www.googleapis.com/oauth2/v3/userinfo "HTTP/1.1 200 OK"
13:29:21.52  backend-gold-iota-nyngopebeg.vercel.app  info   λ GET /api/catalog/districts        
13:29:59.48  backend-gold-iota-nyngopebeg.vercel.app  info   λ OPTIONS /api/profile/update       
13:29:59.88  backend-gold-iota-nyngopebeg.vercel.app  info   λ PUT /api/profile/update           

Exception in ASGI application:
Traceback (most recent call last):
  File "/var/task/server.py", line 1492, in update_profile
    async for d in db.collection('users').where(filter=firestore.FieldFilter('mobile', '==', clean_mobile)).where(filter=firestore.FieldFilter('id', '!=', user['id'])).limit(1).stream():
...
google.api_core.exceptions.FailedPrecondition: 400 The query requires an index. You can create it here:
https://console.firebase.google.com/v1/r/project/nyaysetu-pro/firestore/indexes?create_composite=Ckpwcm9qZWN0cy9ueWF5c2V0dS1wcm8vZGF0YWJhc2VzLyhkZWZhdWx0KS9jb2xsZWN0aW9uR3JvdXBzL3VzZXJzL2luZGV4ZXMvXxABGgoKBm1vYmlsZRABGgYKAmlkEAEaDAoIX19uYW1lX18QAQ
```

### Forensic Analysis:
1. **Endpoint Called**: `PUT /api/profile/update`
2. **Authentication**: Valid Bearer token was passed and accepted. The user `44e94708-90d6-4851-bcc4-4e1bf9c75c1d` was resolved from Firestore.
3. **The Crash**:
   In `backend/server.py` line 1492:
   ```python
   async for d in db.collection('users').where(filter=firestore.FieldFilter('mobile', '==', clean_mobile)).where(filter=firestore.FieldFilter('id', '!=', user['id'])).limit(1).stream():
       existing = d.to_dict()
       break
   ```
   Firestore prohibits combining equality filters (`mobile == clean_mobile`) with inequality filters (`id != user['id']`) across different fields unless an explicit composite index exists.
4. **Client Impact**: Because an unhandled `FailedPrecondition` exception occurred, the server responded with an error, which the browser client caught and displayed via `describeNetworkError()`:
   `"Network error — could not reach the server. Please check your connection and try again."`

---

## Step 2: Trace of OTP Configuration

### 1. Login Screen -> "Use OTP" Tab:
- **Client Action**: Calls `signInOtp(mobile)` -> `POST /api/auth/send-otp`.
- **Backend Code**: `backend/server.py` lines 721-726:
  ```python
  if SMS_PROVIDER in ("", "console"):
      if not _DEV_OTP_ALLOWED:
          raise HTTPException(
              503,
              "OTP service is not configured. Please contact support.",
          )
  ```
- **Finding**: In production (`ENVIRONMENT=production`), `_DEV_OTP_ALLOWED` is strictly `False`. Because no third-party SMS provider (e.g. Twilio) is configured in Vercel environment variables, `SMS_PROVIDER` defaults to `"console"`. The backend intentionally fails closed with HTTP 503 `"OTP service is not configured. Please contact support."`

### 2. Create Account Screen (Signup):
- **Client Action**: Calls `firebaseSendPhoneOtp(mobile)` via Firebase Web SDK `signInWithPhoneNumber`.
- **Finding**: Firebase returned SDK error `auth/operation-not-allowed`.
  In `frontend/app/(auth)/signup.tsx` lines 83-84:
  ```typescript
  if (code === "auth/operation-not-allowed" || code === "auth/unauthorized-continue-uri") {
    setErr("SMS OTP is temporarily unavailable for this region. Please try again later or use password login.");
  }
  ```
- **Cause**: In the Firebase Console for project `nyaysetu-pro`, **Phone** authentication is currently disabled under *Authentication -> Sign-in method*.

---

## Step 3: Password Authentication Verification

- **Endpoint**: `POST /api/auth/login`
- **Backend Code**: `backend/server.py` lines 902-914:
  ```python
  if not user or not user.get("password_hash") or not verify_password(req.password, user["password_hash"]):
      raise HTTPException(401, "Invalid mobile/email or password.")
  ```
- **Finding**: The production Firestore database `nyaysetu-pro` is a fresh database. Per project safety rules, no MongoDB user accounts or passwords were migrated.
- When an un-registered mobile/email is entered, `user` is `None`, and the API correctly rejects the request with HTTP 401 `"Invalid mobile/email or password."`

---

## Step 4: Firebase Auth & Google Config Verification

| Item | Configuration | Status |
| :--- | :--- | :--- |
| **Firebase Project ID** | `nyaysetu-pro` | **VERIFIED MATCH** |
| **Auth Domain** | `nyaysetu-pro.firebaseapp.com` | **VERIFIED MATCH** |
| **Google Provider** | Enabled in Firebase & Google Cloud Console | **VERIFIED WORKING** |
| **Authorized Domains** | Includes `nyaysetupro.in` | **VERIFIED WORKING** |
| **User & Wallet Creation** | Stored in real Firestore collections | **VERIFIED WORKING** |
| **Phone Provider** | Firebase Console -> Sign-in method | **DISABLED** (`auth/operation-not-allowed`) |

---

## Step 5: Root Cause Classification

| Component | Issue | Classification | Concrete Evidence |
| :--- | :--- | :--- | :--- |
| **Profile Completion** | "Network error" on Save | **H. Backend bug (Firestore query)** | `google.api_core.exceptions.FailedPrecondition: 400 The query requires an index` at `server.py:1492` |
| **Backend OTP (Login)** | "OTP service is not configured" | **A. Production env missing SMS provider** | `server.py:725`: `SMS_PROVIDER` defaults to `console`, dev OTP disabled in prod |
| **Firebase OTP (Signup)** | "SMS OTP temporarily unavailable" | **F. Firebase Console config missing Phone provider** | Firebase SDK error `auth/operation-not-allowed` caught in `signup.tsx:83` |
| **Password Login** | "Invalid mobile/email or password" | **Expected Behavior** | Clean production DB with zero pre-existing password accounts |

---

## Step 6: Safe Fix Plan (Minimum Required Changes)

### Fix 1: Resolve Profile Completion Crash (Backend Code)
- **File**: `backend/server.py` line 1492
- **Change**: Replace composite inequality query with a single-field query and in-memory ID exclusion:
  ```python
  # Before:
  async for d in db.collection('users').where(filter=firestore.FieldFilter('mobile', '==', clean_mobile)).where(filter=firestore.FieldFilter('id', '!=', user['id'])).limit(1).stream():
      existing = d.to_dict()
      break

  # After:
  async for d in db.collection('users').where(filter=firestore.FieldFilter('mobile', '==', clean_mobile)).limit(2).stream():
      doc = d.to_dict()
      if doc and doc.get("id") != user.get("id"):
          existing = doc
          break
  ```
- **Why Required**: Resolves the 400 `FailedPrecondition` crash. Profile completion will succeed immediately.
- **Environment Variables Changed**: None.
- **Firebase Console Changed**: None.
- **Deployment Required**: Backend Vercel production redeployment.
- **Firestore Data / MongoDB**: 100% UNTOUCHED.

### Fix 2: Enable OTP in Production (Operational Option)
Choose one of the two standard production options:
- **Option A (Firebase Phone Auth - Recommended)**:
  - In Firebase Console (`nyaysetu-pro`): Go to *Authentication -> Sign-in method -> Phone* and click Enable.
  - Add test phone numbers (e.g. `+91 9999999999` with code `123456`) under "Phone numbers for testing".
  - Requires: Zero code changes, zero environment variable changes.
- **Option B (Twilio Backend SMS)**:
  - Configure `SMS_PROVIDER=twilio`, `SMS_ACCOUNT_SID`, `SMS_AUTH_TOKEN`, and `SMS_FROM` in Vercel Production environment variables.
