# NYAYSETU PRO — PRODUCTION CUTOVER PLAN
**Document:** PRODUCTION_CUTOVER_PLAN.md  
**Platform:** NyaySetu Pro (ન્યાયસેતુ પ્રો)  
**Date:** September 7, 2026  
**Current Phase:** Pre-Promotion Cutover Staging (DO NOT DEPLOY YET)  

---

## A. Current Preview URLs
- **Vercel Preview Backend URL:**
  `https://backend-mktqrcse5-gsybronak-6847s-projects.vercel.app`
  *(Status: Verified 100% healthy, tested with 15/15 integration tests & physical Android device)*
- **Local Android Test Harness:**
  `http://192.168.137.66:8080` (Serving generated artifacts)
- **Preview Frontend Deployment:**
  `https://nyay-setu-pro-emergent-bo83-b3vhdvac1-gsybronak-6847s-projects.vercel.app`

---

## B. Intended Production URLs
- **Production Backend API URL:**
  `https://backend-gold-iota-nyngopebeg.vercel.app`
  *(Default production alias for Vercel project: `backend`)*
- **Production Frontend Custom Domain:**
  `https://nyaysetupro.in`
- **Production Frontend Vercel Domain:**
  `https://nyay-setu-pro-emergent-bo83.vercel.app`
- **Production Admin Web Portal:**
  `https://nyaysetupro.in/admin` (or `https://nyay-setu-pro-emergent-bo83.vercel.app/admin`)

---

## C. Required Vercel Production Environment Variables

### 1. Backend Project (`backend`)
Currently, the following variables are configured **ONLY for `Preview`** in Vercel. They **MUST be added to `Production`** prior to running `vercel deploy --prod`:

| Variable Name | Required Target | Current Vercel Setting | Purpose |
| :--- | :---: | :---: | :--- |
| `FIREBASE_PROJECT_ID` | Production | Preview only | Cloud Firestore project ID (`nyaysetu-pro`) |
| `FIREBASE_CLIENT_EMAIL` | Production | Preview only | Firebase Admin SDK service account email |
| `FIREBASE_PRIVATE_KEY` | Production | Preview only | RSA private key (with escaped \n) |
| `ENVIRONMENT` | Production | Preview only | Set to `production` |
| `TEMPLATE_AUTO_SEED` | Production | Preview only | Set to `false` (DB already seeded) |
| `TEMPORARILY_DISABLE_ALL_TEMPLATES` | Production | Preview only | Set to `false` (Templates active) |
| `JWT_SECRET` | Production | Preview only | HS256 JWT signing secret |
| `ADMIN_SEED_EMAIL` | Production | Preview only | Super admin email |
| `ADMIN_SEED_PASSWORD` | Production | Preview only | Super admin password hash |
| `MONGO_URL` | Production | Preview only | **MongoDB Rollback Safeguard** (Preserved 100%) |
| `DB_NAME` | Production | Preview only | **MongoDB Rollback Safeguard** (Preserved 100%) |
| `GOOGLE_OAUTH_CLIENT_ID` | Production | Production, Preview | Google Sign-In Client ID (Already set) |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Production | Production, Preview | Google Sign-In Secret (Already set) |

### 2. Frontend Project (`nyay-setu-pro-emergent-bo83`)
| Variable Name | Required Target | Current Vercel Setting | Value to Set |
| :--- | :---: | :---: | :--- |
| `EXPO_PUBLIC_BACKEND_URL` | Production | Production, Preview | `https://backend-gold-iota-nyngopebeg.vercel.app` |
| `EXPO_PUBLIC_FIREBASE_PROJECT_ID` | Production | Production, Preview | `nyaysetu-pro` |
| `EXPO_PUBLIC_FIREBASE_API_KEY` | Production | Production, Preview | Configured |
| `EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN`| Production | Production, Preview | `nyaysetu-pro.firebaseapp.com` |
| `EXPO_PUBLIC_GOOGLE_CLIENT_ID` | Production | Production, Preview | Configured |

---

## D. Firebase Configuration Status
- **Project ID:** `nyaysetu-pro`
- **Mode:** Native Cloud Firestore (Strictly Non-Datastore)
- **Location:** `asia-south1` (Mumbai, India)
- **Active Collections & Counts Verified Live:**
  - `districts`: 34
  - `talukas`: 255
  - `courts`: 47
  - `case_types`: 23
  - `plans`: 4 (Silver, Gold, Platinum, Pay-per-doc)
  - `templates`: 45 published templates
  - `template_revisions`: 45 versioned snapshots
  - `admin_users`: 1 active super-admin record
- **Security Rules:** `firestore.rules` deployed with `allow read, write: if false;` (Zero-trust; all client access mediated by backend).
- **Reseeding Status:** COMPLETED. No re-seeding or data duplication will be executed.

---

## E. Frontend API URL That Must Be Used in Production
`https://backend-gold-iota-nyngopebeg.vercel.app`
- Configured in `frontend/.env` as:
  `EXPO_PUBLIC_BACKEND_URL=https://backend-gold-iota-nyngopebeg.vercel.app`
- Fallback in `frontend/src/api/client.ts` already defaults to this exact production domain.

---

## F. Admin API URL That Must Be Used in Production
`https://backend-gold-iota-nyngopebeg.vercel.app`
- Configured in `admin/.env` as:
  `VITE_API_BASE=https://backend-gold-iota-nyngopebeg.vercel.app`
- Fallback in `admin/src/lib/api.ts` already defaults to this exact production domain.

---

## G. Exact Deployment Commands (For Execution Upon User Approval)

### Step 1: Promote Backend Environment Variables to Production
*(Using automated script `scratch/configure_backend_production_env.py` or Vercel CLI)*
```bash
# Push the 11 verified environment variables from backend/.env & service account to Vercel Production
npx.cmd vercel env add FIREBASE_PROJECT_ID production --project backend --yes --force
npx.cmd vercel env add FIREBASE_CLIENT_EMAIL production --project backend --yes --force
npx.cmd vercel env add FIREBASE_PRIVATE_KEY production --project backend --yes --force
npx.cmd vercel env add ENVIRONMENT production --project backend --yes --force
npx.cmd vercel env add TEMPLATE_AUTO_SEED production --project backend --yes --force
npx.cmd vercel env add TEMPORARILY_DISABLE_ALL_TEMPLATES production --project backend --yes --force
npx.cmd vercel env add JWT_SECRET production --project backend --yes --force
npx.cmd vercel env add ADMIN_SEED_EMAIL production --project backend --yes --force
npx.cmd vercel env add ADMIN_SEED_PASSWORD production --project backend --yes --force
npx.cmd vercel env add MONGO_URL production --project backend --yes --force
npx.cmd vercel env add DB_NAME production --project backend --yes --force
```

### Step 2: Deploy Backend to Production
```bash
cd C:\Users\HP\Downloads\NyaySetu-Pro-Emergent\backend
npx.cmd vercel deploy --prod --yes
```

### Step 3: Deploy Frontend to Production
```bash
cd C:\Users\HP\Downloads\NyaySetu-Pro-Emergent\frontend
npx.cmd vercel deploy --prod --yes
```

---

## H. Post-Deployment Verification Commands

1. **Verify Backend Production Healthz:**
   ```bash
   curl.exe -i -s https://backend-gold-iota-nyngopebeg.vercel.app/healthz
   # Expected: HTTP 200 OK {"app":"NyaySetu Pro","status":"ok","version":"1.0.0"}
   ```

2. **Verify Production Catalog API:**
   ```bash
   curl.exe -s https://backend-gold-iota-nyngopebeg.vercel.app/api/catalog/districts
   # Expected: JSON array of 34 districts
   ```

3. **Verify Production Template Library:**
   ```bash
   curl.exe -s https://backend-gold-iota-nyngopebeg.vercel.app/api/templates
   # Expected: JSON array of 45 published templates
   ```

4. **Verify Production Frontend:**
   ```bash
   curl.exe -i -s https://nyaysetupro.in
   # Expected: HTTP 200 OK
   ```

5. **Verify Live PDF Generation on Production:**
   Run `python scratch/verify_prod_doc_generation.py` to generate and inspect a live PDF directly from `https://backend-gold-iota-nyngopebeg.vercel.app`.

---

## I. Rollback Procedure
If any unexpected issue arises post-cutover:

1. **Backend Rollback:**
   ```bash
   # Redeploy the previously working production deployment
   npx.cmd vercel rollback --project backend --yes
   ```
   Or instantly point traffic back to the verified preview deployment URL.

2. **Frontend Rollback:**
   ```bash
   npx.cmd vercel rollback --project nyay-setu-pro-emergent-bo83 --yes
   ```

---

## J. MongoDB Rollback Safeguard
- **Active State:** MongoDB remains 100% untouched and populated.
- **Environment Variables:** `MONGO_URL` and `DB_NAME` are preserved in `backend/.env` and will remain in Vercel environment variables.
- **Codebase Reversibility:** If catastrophic failure occurs in Cloud Firestore, the Motor/MongoDB driver code branch can be restored instantaneously via git with zero data loss.
- **Destructive Deletion Block:** No script or command is permitted to drop, truncate, or wipe MongoDB collections until 30 days of stable production operation.
