# PRODUCTION AUTH FIX VERIFICATION — NYAYSETU PRO

**Date**: 2026-09-07  
**Status**: VERIFIED & DEPLOYED TO PRODUCTION  
**Vercel Backend Deployment ID**: `dpl_7iB2KSM6Tt9tWy1WnYxGHZUFAsaH`  
**Production Backend URL**: `https://backend-gold-iota-nyngopebeg.vercel.app`  
**Production Frontend URL**: `https://nyaysetupro.in`  
**Database**: Google Cloud Firestore (`nyaysetu-pro`, `asia-south1`)  

---

## 1. Executive Summary

During live real-device testing of Google Sign-In on Android, users were able to sign in with Google and arrived at the "Complete Your Profile" screen, but submitting the profile resulted in:
```text
"Network error — could not reach the server. Please check your connection and try again."
```
The root cause was identified as a Firestore query in `backend/server.py` combining equality (`mobile == clean_mobile`) with inequality (`id != user.get('id')`), which requires a composite index that was not provisioned.

The query was refactored to perform a single-field equality check on `mobile` with in-memory filtering of the current user ID. The fix was verified locally against real Cloud Firestore, deployed to Vercel Production, and confirmed live with end-to-end testing.

---

## 2. Code Fix Applied

### File: `backend/server.py` (lines 1491–1498)

#### Before:
```python
existing = None
async for d in db.collection('users').where(filter=firestore.FieldFilter('mobile', '==', clean_mobile)).where(filter=firestore.FieldFilter('id', '!=', user.get("id"))).limit(1).stream():
    existing = d.to_dict()
    break
if existing:
    raise HTTPException(400, "This mobile number is already registered with another account.")
```

#### After:
```python
existing = None
async for d in db.collection('users').where(filter=firestore.FieldFilter('mobile', '==', clean_mobile)).limit(2).stream():
    doc = d.to_dict()
    if doc and doc.get("id") != user.get("id"):
        existing = doc
        break
if existing:
    raise HTTPException(400, "This mobile number is already registered with another account.")
```

### Key Architectural Invariants Maintained:
- **No Composite Index Required**: Only queries `mobile == clean_mobile` (single-field index, supported by default).
- **Duplicate Prevention**: If any other user document has `clean_mobile`, HTTP 400 is returned.
- **Self-Update Allowed**: If the current user already owns that mobile number, the update proceeds without error.
- **Zero Schema or DB Mutation**: Existing data, wallets, cases, and MongoDB rollback configurations remain untouched.

---

## 3. Verification & Test Results

### Phase 1: Local Regression Tests Against Real Cloud Firestore (`nyaysetu-pro`)
Script: `scratch/test_profile_regression_live.py`
```text
Test 1: Updating profile with new unused mobile... [PASS] (HTTP 200, no index error)
Test 2: Updating profile keeping own existing mobile... [PASS] (HTTP 200, self-mobile allowed)
Test 3: Attempting to use another user's mobile... [PASS] (HTTP 400 duplicate rejected)
Cleanup: Temporary test users deleted.
Result: ALL 3 REGRESSION TESTS PASSED
```

### Phase 2: Production Vercel Deployment
- Command: `npx vercel deploy --prod --yes`
- Deployment ID: `dpl_7iB2KSM6Tt9tWy1WnYxGHZUFAsaH`
- Alias Assigned: `https://backend-gold-iota-nyngopebeg.vercel.app`
- Status: `READY`

### Phase 3: Live Production API Verification
Script: `scratch/test_prod_profile_update.py`
Target: `https://backend-gold-iota-nyngopebeg.vercel.app`
```text
1. GET /healthz: HTTP 200 - {'app': 'NyaySetu Pro', 'status': 'ok', 'version': '1.0.0'}
2. PUT /api/profile/update with mobile=9826216753... HTTP 200
   [PASS] Profile update completed successfully with no Firestore index error!
3. GET /api/profile/me: HTTP 200 [PASS]
4. Cleanup: Deleted test user live_test_user_7fa494ed
Result: ALL PASSED
```

### Phase 4: Production Smoke Suite (14/14 Tests)
Script: `scratch/run_production_smoke_tests.py`
```text
  [PASS] TEST 1: Health (/healthz -> HTTP 200) (1.21s)
  [PASS] TEST 2: Firebase Connectivity (Real Firestore SDK) (0.95s)
  [PASS] TEST 3: Catalog Complete (34 Districts, 255 Talukas, 47 Courts, 23 Case Types) (2.57s)
  [PASS] TEST 4: Canonical 21 Templates Verification (2.12s)
  [PASS] TEST 5: Authentication Protection (HTTP 401 on Unauthorized) (1.36s)
  [PASS] TEST 6: Authorization Verification (HTTP 403 on Admin Routes for Lawyers) (2.82s)
  [PASS] TEST 7: Application Flow (Case Creation & mudat_arji Preview) (3.52s)
  [PASS] TEST 8: Document Generation (Gujarati PDF & PNG via HarfBuzz) (10.72s)
  [PASS] TEST 9: Wallet / Business Logic (Zero-Balance Guard) (2.18s)
  [PASS] TEST 10: CORS Configuration (Allowed for https://nyaysetupro.in) (0.84s)
  [PASS] TEST 11: Error Handling & Credential Sanitization (No Leaks) (0.75s)
  [PASS] TEST 12: MongoDB Isolation (Untouched / 0 Runtime Connections) (0.00s)
  [PASS] TEST 13: Production Environment Isolation (Dev OTP Bypass Disabled) (0.78s)
  [PASS] TEST 14: Repeated Invocation & Cold-Start Stability (5 Sequential Calls) (2.41s)

Result: 14/14 PASSED
```

---

## 4. Current Authentication Status Summary

| Authentication Flow | Live Production Status | Notes |
|:---|:---:|:---|
| **Google Sign-In** | **PASS** | Google OAuth token verification succeeds in Firestore |
| **Profile Completion** | **PASS** | `PUT /api/profile/update` succeeds with HTTP 200 (Index error eliminated) |
| **Session Persistence** | **PASS** | Production JWT verification operational (`PROD_JWT_SECRET`) |
| **Mobile OTP Login** | **BLOCKED (Design)** | Production environment operates with `SMS_PROVIDER=console` |
| **Mobile OTP Signup** | **BLOCKED (Firebase)** | Firebase Phone Provider is disabled in Firebase Console |
| **Password Login** | **PASS (Auth)** | Returns 401 for non-existent users as expected; active users authenticate normally |
| **MongoDB** | **UNTOUCHED** | Zero production connections; local configuration preserved |
