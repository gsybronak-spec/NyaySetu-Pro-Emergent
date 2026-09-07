# Production Environment Variable Audit — NyaySetu Pro Backend

**Target Project**: `nyaysetu-pro` (Firebase Firestore)  
**Backend Vercel Project**: `backend` (`prj_fb5PuzUA1JPQ9khsyxSGEbYn6POQ`)  
**Production API Domain**: `https://backend-gold-iota-nyngopebeg.vercel.app`  
**Audit Date**: September 7, 2026  
**Status**: Pre-Promotion Security & Runtime Dependency Audit Complete (NO changes made)

---

## Executive Summary

Before promoting any environment variables from Vercel **Preview** to Vercel **Production**, a static code-level dependency analysis was conducted across all 16 production backend Python modules in `backend/`.

The analysis evaluated 13 target environment variables to determine their exact runtime necessity, code consumers, default behaviors, and security implications.

### Key Takeaways:
1. **6 Variables MUST be configured in Vercel Production**:
   - `FIREBASE_PROJECT_ID` (`nyaysetu-pro`)
   - `FIREBASE_CLIENT_EMAIL` (service account email)
   - `FIREBASE_PRIVATE_KEY` (service account private key)
   - `JWT_SECRET` (session token signing key >= 32 characters)
   - `ENVIRONMENT` (`production`)
   - `TEMPORARILY_DISABLE_ALL_TEMPLATES` (`false` — **CRITICAL**: backend defaults to `"true"` if omitted, which hides all templates)
2. **2 Variables are ALREADY configured in Vercel Production**:
   - `GOOGLE_OAUTH_CLIENT_ID`
   - `GOOGLE_OAUTH_CLIENT_SECRET`
3. **5 Variables should NOT be in Vercel Production**:
   - `ADMIN_SEED_EMAIL` & `ADMIN_SEED_PASSWORD`: **SEED-ONLY**. The admin user `admin@nyaysetupro.in` is already seeded in Firestore. Storing plaintext admin passwords in Vercel serverless environment variables violates the principle of least privilege.
   - `TEMPLATE_AUTO_SEED`: **OPTIONAL / SEED-ONLY**. Firestore already has 21 canonical templates seeded. Auto-seeding on serverless cold starts is unnecessary and disabled by default (`false`).
   - `MONGO_URL` & `DB_NAME`: **ROLLBACK-ONLY / LEGACY**. Zero lines of active runtime code in `backend/*.py` consume MongoDB. These remain in local `backend/.env` for rollback readiness but should not be exposed to Vercel.
   - `FIRESTORE_EMULATOR_HOST`: **SHOULD NOT BE IN PRODUCTION**. Local emulator hook only.

---

## Detailed Variable Audit Matrix

| Variable | Classification | Code Location(s) | Default in Code | Recommended Action for Vercel Production | Risk if Missing / Misconfigured |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`FIREBASE_PROJECT_ID`** | **REQUIRED AT RUNTIME** | `firebase_init.py:47,103`<br>`server.py:113,204,1311,1325,1376` | None / `"demo-nyaysetu"` (dev only) | **Add to Production** (`nyaysetu-pro`) | **FATAL (500/503)**: Firebase Admin SDK fails initialization; Firestore queries fail; Firebase token verification fails. |
| **`FIREBASE_CLIENT_EMAIL`** | **REQUIRED AT RUNTIME** | `firebase_init.py:48,110` | None | **Add to Production** (Service account email) | **FATAL (500)**: Backend cannot authenticate to Google Cloud; crashes with `RuntimeError: Firebase credentials are not configured`. |
| **`FIREBASE_PRIVATE_KEY`** | **REQUIRED AT RUNTIME** | `firebase_init.py:49,111` | None | **Add to Production** (Service account private key) | **FATAL (500)**: Cannot sign Google OAuth service account JWTs; serverless invocation fails immediately. |
| **`JWT_SECRET`** | **REQUIRED AT RUNTIME** | `server.py:67,69-73,433,464,2406,3668,3702,3907` | None | **Add to Production** (from `backend/.env`, >=32 chars) | **FATAL (Startup Crash)**: Line 69 enforces `len(JWT_SECRET) >= 32` when `ENVIRONMENT=production`. Refuses startup with `RuntimeError` if missing or short. |
| **`ENVIRONMENT`** | **REQUIRED AT RUNTIME** | `server.py:59,62,73,166,720,2980` | `""` | **Add to Production** (`production`) | **CRITICAL SECURITY RISK**: If missing or set to `development`, dev OTP bypass can be triggered, and production safeguards are disabled. |
| **`TEMPORARILY_DISABLE_ALL_TEMPLATES`** | **REQUIRED AT RUNTIME** | `server.py:95,2311,2320,5348` | **`"true"`** (Hardcoded default!) | **Add to Production** (`false`) | **MAJOR USER OUTAGE**: Because default in code is `"true"`, omitting this variable causes `/api/templates` to return `[]` (empty list). Users see 0 templates. |
| **`GOOGLE_OAUTH_CLIENT_ID`** | **REQUIRED AT RUNTIME** | `server.py:181,1163,1201` | None | **Keep Existing** (Already in Production) | Google Sign-In endpoint fails with 503 if missing. |
| **`GOOGLE_OAUTH_CLIENT_SECRET`** | **REQUIRED AT RUNTIME** | `server.py:182,1164,1201` | None | **Keep Existing** (Already in Production) | Google Sign-In token verification fails if missing. |
| **`TEMPLATE_AUTO_SEED`** | **OPTIONAL / SEED-ONLY** | `server.py:91` | `"false"` | **DO NOT ADD** (Leave unset or `"false"`) | If set to `"true"`, re-runs template seeding on every cold start. Safely omitted. |
| **`ADMIN_SEED_EMAIL`** | **SEED-ONLY** | `server.py:85,6310-6313` | None | **DO NOT ADD** | None. Admin user `admin@nyaysetupro.in` is already present in Firestore. Omitting avoids plaintext credentials in Vercel config. |
| **`ADMIN_SEED_PASSWORD`** | **SEED-ONLY** | `server.py:86,6310,6318` | None | **DO NOT ADD** | None. Same as above. Line 6311 safely logs `skipping admin seed` and continues normally. |
| **`MONGO_URL`** | **ROLLBACK-ONLY** | None in production code | None | **DO NOT ADD** | Zero runtime impact on Firestore backend. Retain in local `backend/.env` for MongoDB rollback safeguard. |
| **`DB_NAME`** | **ROLLBACK-ONLY** | None in production code | None | **DO NOT ADD** | Zero runtime impact on Firestore backend. Retain in local `backend/.env` for MongoDB rollback safeguard. |
| **`FIRESTORE_EMULATOR_HOST`** | **SHOULD NOT BE IN PRODUCTION** | `firebase_init.py:45,106`<br>`server.py:112` | None | **DO NOT ADD** | **FATAL**: Directs Firestore traffic to a non-existent localhost emulator on Vercel lambda, causing connection timeouts. |

---

## Detailed Analysis of Critical Variables

### 1. `TEMPORARILY_DISABLE_ALL_TEMPLATES` (Critical Finding)
In `backend/server.py`:
```python
def _is_templates_disabled() -> bool:
    is_test = "PYTEST_CURRENT_TEST" in os.environ
    is_disabled = os.environ.get("TEMPORARILY_DISABLE_ALL_TEMPLATES", "true").lower() == "true"
    return is_disabled and not is_test
```
**Notice**: The fallback value in `os.environ.get(..., "true")` is string `"true"`.
If the variable is **not set** in Vercel Production, `is_disabled` evaluates to `True`. Consequently, the `/api/templates` endpoint will hide all legal templates from lawyers in production.
- **Remedy**: Must be explicitly set to `false` in Vercel Production.

### 2. `ADMIN_SEED_EMAIL` and `ADMIN_SEED_PASSWORD` (Security Finding)
In `backend/server.py`:
```python
async def seed_admin_user():
    if not ADMIN_SEED_EMAIL or not ADMIN_SEED_PASSWORD:
        logger.info("ADMIN_SEED_EMAIL / ADMIN_SEED_PASSWORD not set — skipping admin seed.")
        return
```
- During Phase 3 Step 4, the admin user (`admin@nyaysetupro.in`) was already seeded into Firestore collection `admin_users` with a securely hashed bcrypt password.
- Verification tests in Step 5 proved admin authentication works via Firestore lookup.
- Adding `ADMIN_SEED_EMAIL` and `ADMIN_SEED_PASSWORD` to Vercel environment variables is completely redundant and poses an unnecessary credential exposure risk.
- **Recommendation**: Omit both variables from Vercel Production.

### 3. `MONGO_URL` and `DB_NAME` (Clean Separation Finding)
- Static analysis scanned all 6,413 lines of `backend/server.py` and all utility modules.
- Result: **0 occurrences** of `MONGO_URL` and `DB_NAME` in production code.
- Firestore operates 100% independently via `firebase-admin` and `google-cloud-firestore`.
- Leaving MongoDB credentials out of Vercel Production ensures production lambdas do not carry unused database connections or secrets. Both variables remain intact in local `backend/.env` ensuring rollback capability.

---

## Exact Production Variable Delta

### Variables Currently in Backend Production:
1. `GOOGLE_OAUTH_CLIENT_ID` (Configured)
2. `GOOGLE_OAUTH_CLIENT_SECRET` (Configured)

### Variables to Add to Backend Production (Exact 6):
| # | Key | Target Environment | Value Reference |
| :--- | :--- | :--- | :--- |
| 1 | `FIREBASE_PROJECT_ID` | Production | `nyaysetu-pro` |
| 2 | `FIREBASE_CLIENT_EMAIL` | Production | Service Account Email (from `backend/.env`) |
| 3 | `FIREBASE_PRIVATE_KEY` | Production | Service Account Private Key (from `backend/.env`) |
| 4 | `JWT_SECRET` | Production | Application JWT Secret (from `backend/.env`, >=32 chars) |
| 5 | `ENVIRONMENT` | Production | `production` |
| 6 | `TEMPORARILY_DISABLE_ALL_TEMPLATES` | Production | `false` |

---

## Safety Confirmation
- **No changes have been made to Vercel environment variables.**
- **No production deployment (`vercel deploy --prod`) has been triggered.**
- **MongoDB data and local environment variables have not been modified or deleted.**
- **No secret values have been printed or logged.**
