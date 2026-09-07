# Phase 3: Pre-Production Technical Audit Report
**NyaySetu Pro — Native Firebase & Vercel Migration**

*Generated: 2026-09-06 | Stage: Pre-Production Gate Verification*

---

## Executive Summary

Pursuant to the Phase 3 Gate directives, this Pre-Production Audit establishes the complete environment, security, database, and infrastructure requirements for connecting NyaySetu Pro to a real Firebase Firestore instance and deploying to Vercel Staging/Preview.

MongoDB databases, clusters, connection strings, and rollback configurations remain **100% untouched and active** during this verification phase.

---

## 1. Required Firebase Environment Variables

The backend uses `firebase-admin` and `google-cloud-firestore` natively. When deploying outside the local emulator (e.g. Vercel Staging, Production, or direct test runner), the following environment variables are required:

| Variable Name | Purpose | Sensitivity | Format / Example Pattern |
|---|---|---|---|
| `FIREBASE_PROJECT_ID` | GCP / Firebase Project identifier | Public / Config | String (e.g. `nyaysetu-prod`) |
| `FIREBASE_CLIENT_EMAIL` | Service Account Client Email | Identifier | Email (e.g. `firebase-adminsdk-xxx@<project>.iam.gserviceaccount.com`) |
| `FIREBASE_PRIVATE_KEY` | RSA Private Key for Admin SDK auth | Secret | PKCS#8 PEM string (escaped `\n` or multiline) |
| `FIREBASE_PRIVATE_KEY_ID` | (Optional) Key identifier from JSON | Metadata | 40-character hex string |
| `FIREBASE_CLIENT_ID` | (Optional) Service account client ID | Metadata | Numeric string |
| `FIRESTORE_EMULATOR_HOST` | Local development emulator host | Local dev only | Host:port (e.g. `127.0.0.1:8080`). **Must be UNSET in staging/production**. |

---

## 2. Required Vercel Environment Variables

To operate the FastAPI serverless backend (`backend/api/index.py`) on Vercel:

| Variable Name | Required? | Default / Purpose |
|---|---|---|
| `FIREBASE_PROJECT_ID` | **Required** | Target Firebase project ID |
| `FIREBASE_CLIENT_EMAIL` | **Required** | Firebase Service Account email |
| `FIREBASE_PRIVATE_KEY` | **Required** | Service Account RSA private key |
| `JWT_SECRET` | **Required** | HMAC-SHA256 secret for lawyer and admin access tokens |
| `ENVIRONMENT` | Recommended | Set to `staging` or `production` |
| `CORS_ORIGINS` | Recommended | Allowed origins for web & admin (e.g. `https://staging.nyaysetu.com,http://localhost:8081`) |
| `TEMPLATE_AUTO_SEED` | Recommended | Set to `false` in production (prevents auto-reseed on every cold start) |
| `ADMIN_SEED_EMAIL` | Optional | Initial super admin email for `seed_firestore.py` |
| `ADMIN_SEED_PASSWORD` | Optional | Initial super admin password for `seed_firestore.py` |
| `MONGO_URL` | **Preserved** | Kept intact for rollback safety (do not remove) |
| `DB_NAME` | **Preserved** | Kept intact for rollback safety (do not remove) |

---

## 3. Firebase Authentication Requirements

1. **Authentication Architecture**:
   - NyaySetu Pro employs a backend-mediated authentication flow. The client talks exclusively to FastAPI endpoints (`/api/auth/phone-login`, `/api/auth/verify-otp`, `/api/auth/admin-login`).
   - Session tokens are custom signed JWTs (`HS256`) signed with `JWT_SECRET`, containing `sub` (lawyer UID), `phone`, and expiry claims.
   - For optional Google OAuth logins, Google ID tokens are verified backend-side, and a corresponding lawyer document is fetched or created in Firestore.
2. **User Identity Records**:
   - Stored in the Firestore `lawyers` collection.
   - Keyed by deterministic unique document ID (`id`), containing phone number, name, bar enrollment number, practice areas, and creation timestamp.

---

## 4. Firestore Requirements

1. **Database Mode**: Cloud Firestore in **Native Mode** (default database: `(default)`).
2. **GCP APIs Required**:
   - Cloud Firestore API (`firestore.googleapis.com`) enabled.
   - Identity and Access Management (IAM) API enabled.
3. **IAM Roles for Service Account**:
   - `roles/datastore.user` (Cloud Datastore User) or Firebase Admin SDK Administrator Service Agent.
4. **Primary Collections**:
   - `lawyers`: Advocate user profiles and metadata.
   - `cases`: Legal cases owned by advocates.
   - `applications`: Completed application forms linked to cases.
   - `templates`: Canonical application templates (v1 and v2 catalog).
   - `template_revisions`: Version-controlled immutable template snapshots.
   - `districts`, `talukas`, `courts`, `case_types`: Master Gujarat court geographic and jurisdictional catalog.
   - `plans`: Credit purchase and subscription tiers.
   - `wallets`: Advocate credit balances.
   - `transactions`: Credit addition and usage ledgers.
   - `referrals`: Advocate referral tracking.
   - `admin_users`: Super admin and staff credential records.
   - `system_settings`: Feature flags and seed status flags (`seed_complete`).

---

## 5. Storage Requirements

- **Audit Finding**: **ZERO EXTERNAL OBJECT STORAGE REQUIRED**.
- Document generation in `backend/doc_generator.py` compiles ReportLab / HarfBuzz PDFs, python-docx DOCX files, ODF ODT files, and pypdfium2/Pillow raster images in-memory (`io.BytesIO`).
- Endpoints (`/api/applications/{id}/download`, `/api/applications/preview`, etc.) stream the generated binary payloads directly across HTTP as binary responses with strict streaming headers (`Content-Disposition`, `Content-Type: application/pdf`).
- No Firebase Storage bucket or Google Cloud Storage bucket needs to be provisioned or configured for core document generation.

---

## 6. Required Composite Indexes

Firestore requires composite indexes for queries with multiple inequality filters, or equality filters combined with sort order. The complete composite index configuration has been audited and committed to `backend/firestore.indexes.json`:

1. **`applications`**: `lawyer_id` (ASC) + `created_at` (DESC)
2. **`cases`**: `lawyer_id` (ASC) + `created_at` (DESC)
3. **`drafts`**: `lawyer_id` (ASC) + `updated_at` (DESC)
4. **`transactions`**: `lawyer_id` (ASC) + `created_at` (DESC)
5. **`referrals`**: `referrer_id` (ASC) + `created_at` (DESC)
6. **`templates`**: `status` (ASC) + `category` (ASC)
7. **`template_revisions`**: `template_id` (ASC) + `version` (DESC)

*Deployment command*: `firebase deploy --only firestore:indexes`

---

## 7. Required Seed Data

Authoritative application catalog and master data definitions:

| Catalog Component | Item Count | Source Definition |
|---|---|---|
| **Canonical Legal Templates (v2)** | **21** | `backend/test_seed_data_templates_v2.py` (transcribed verbatim from lawyer drafts) |
| **Standard Templates (v1)** | **24** | `backend/test_seed_data.py` |
| **Total Templates** | **45** | Fully reconciled with zero collisions |
| **Districts (Gujarat)** | **34** | `backend/seed_data.py` (`DISTRICTS`) |
| **Talukas (Gujarat)** | **255** | `backend/seed_data.py` (`TALUKAS`) |
| **Courts** | **47** | `backend/seed_data.py` (`COURTS`) |
| **Case Types** | **23** | `backend/seed_data.py` (`CASE_TYPES`) |
| **Credit Plans** | **4** | `backend/seed_data.py` (`PLANS`) |

Seeding is performed idempotently via `backend/seed_firestore.py` without copying or migrating any legacy MongoDB operational data.

---

## 8. Required Admin Accounts

- Initial root admin user is provisioned via `backend/seed_firestore.py` (`seed_super_admin()`).
- Credentials sourced from `ADMIN_SEED_EMAIL` and `ADMIN_SEED_PASSWORD`.
- Passwords are salted and hashed with `bcrypt` (12 rounds) prior to insertion into the `admin_users` collection.
- Super admin role permissions grant full template management, catalog updates, and analytics oversight.

---

## 9. Required Security Configuration

1. **Firestore Client Rules (`backend/firestore.rules`)**:
   ```javascript
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /{document=**} {
         allow read, write: if false;
       }
     }
   }
   ```
   **All client-side privileged Firestore access is explicitly prohibited.**
2. **Backend Tenancy Isolation**:
   - All client traffic routes through FastAPI.
   - The `get_current_user` dependency verifies JWT signatures and extracts the authenticated advocate UID.
   - All document and case queries strictly enforce `FieldFilter("lawyer_id", "==", current_user["id"])`. IDOR attempts return 404 / 403.
3. **Admin Privilege Enforcement**:
   - Admin routes strictly enforce `admin_required` dependency checking `role == "super_admin"` or explicit permission flags.

---

## 10. Required Secrets

All secrets must be securely managed via Vercel Environment Variables and CI/CD secret stores. **No secrets are stored in version control.**

1. `FIREBASE_PRIVATE_KEY`: Service account cryptographic signing key.
2. `JWT_SECRET`: High-entropy symmetric key for authentication tokens.
3. `ADMIN_SEED_PASSWORD`: Initial bootstrap administrator password.
4. `RAZORPAY_KEY_SECRET`: (Optional) Payment gateway webhook verification secret.
5. `SMS_AUTH_TOKEN`: (Optional) SMS OTP delivery provider token.
6. `GOOGLE_OAUTH_CLIENT_SECRET`: (Optional) Google Sign-in OAuth secret.

---

*Pre-Production Audit complete. Ready for Step 3 connection to real Firebase staging project upon credential availability.*
