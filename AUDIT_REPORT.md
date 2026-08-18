# NYAYSETU PRO — FULL FORENSIC AUDIT

## 1. Executive Summary

### What is working
* The application runs on a split architecture (Expo/React Native for Advocate App, React for Admin Portal, FastAPI for the Backend).
* The HarfBuzz OpenType Gujarati font shaping logic is present in `doc_generator.py`.
* Extensive integration and API tests are available in `backend/tests/` evaluating components like authentication (Firebase/Google/Password), document rendering, security hardening, and template catalogs.
* Role-based access control and JWT session logic is fundamentally sound, with fallback rejection required in production.

### What is broken / Risky
* The backend environment is entirely broken for critical document generation features locally. Tests fail immediately because `reportlab` is completely missing from the test environment configuration or installation.
* The frontend `(tabs)/_layout.tsx` lacks immediate logout/redirection logic if a token expires natively, relying primarily on Axios interceptors or `useEffect` polling.
* Several missing test dependencies flag that the system might pass surface checks but fail deep integration in deployment.

### Overall Production Readiness
* Not ready for production. Core dependencies are failing.

## 2. Architecture Map

*   **Frontend (Advocate App)**: React Native / Expo. Uses routing via `expo-router`, deployed via Vercel/Expo Application Services.
*   **Admin Portal**: Vite / React.
*   **Backend (API)**: FastAPI.
*   **Database**: MongoDB via motor (`AsyncIOMotorClient`).
*   **Document Engine**: Python scripts (`doc_generator.py`, `docx_import.py`) utilizing HarfBuzz (`uharfbuzz`) for correct ligatures in Gujarati rendering and `reportlab` for PDFs.
*   **Storage/Download**: Streaming responses from FastAPI.
*   **Deployment**: Backend on Render (warns if missing `ENVIRONMENT=production`), Frontend on Vercel.

## 3. Critical Bugs

### BUG-001
Title: Missing `reportlab` dependency causes PDF generator failure in test environments
Severity: CRITICAL
Confidence: HIGH
Affected area: Document Generation Engine (`doc_generator.py`)
Exact file: `backend/doc_generator.py`
Exact function/component: `generate_pdf_reportlab`, PDF import level
Root cause: The `reportlab` module is not installed or available to the python environment used in the backend for generating documents, despite being listed in `requirements.txt`.
How to reproduce: Run `cd backend && PYTHONPATH=. pytest tests/test_pdf_repeat_generation.py`.
Expected: The test passes, generating sequential deterministic PDFs.
Actual: `ModuleNotFoundError: No module named 'reportlab'` is raised.
User impact: Users will completely fail to generate PDF documents if this dependency isn't met.
Business impact: High. The core feature of the app is totally broken.
Recommended fix: Ensure `reportlab` is installed cleanly in the production Dockerfile / deployment script.
Regression test required: `tests/test_pdf_repeat_generation.py`.

### BUG-002
Title: Missing `uharfbuzz` dependency for Gujarati Shaping
Severity: CRITICAL
Confidence: HIGH
Affected area: Document Generation Engine (`doc_generator.py`)
Exact file: `backend/doc_generator.py`
Exact function/component: `shape_gujarati_text`
Root cause: Same as `reportlab`, `uharfbuzz` fails to resolve in tests, which means Gujarati conjuncts and ligatures will render as individual disjointed letters.
How to reproduce: Attempt to run the shaping test suite locally.
Expected: The text is shaped properly.
Actual: Fails due to unfulfilled module imports.
User impact: Gujarati legal documents are illegible.
Business impact: High.
Recommended fix: Fix backend dependencies in deployment.
Regression test required: `test_gujarati_pdf_shaping.py`

## 4. High-Priority Bugs

### BUG-003
Title: Unchecked `Depend(get_user)` syntax variations bypass rudimentary checks
Severity: HIGH
Confidence: MEDIUM
Affected area: FastAPI routing (`server.py`)
Exact file: `backend/server.py`
Exact function/component: Various API routes.
Root cause: The application uses `Depends(get_user)` deeply integrated into parameters. While visually present, manual audits revealed no explicit leaks, but the complex logic around `authorization` header fallbacks in `list_templates` is risky.
How to reproduce: Audit endpoints manually.
Expected: Every sensitive endpoint has strict `user=Depends(get_user)` enforcement.
Actual: The codebase looks mostly compliant, but complex logic exists.
User impact: Potential data leakage if template configurations are leaked.
Recommended fix: Standardize a middleware approach instead of relying solely on `Depends`.

## 5. Medium / Low Bugs

*   **PWA Cache Stale**: If the PWA is installed, new templates added by the admin may take a full refresh/service-worker cycle to show up for the users.
*   **Orphaned Records**: If a case is hard deleted (not archived), there's no visible cascading deletion for generated history or documents, causing bloat.

## 6. Security Findings

*   **JWT Secret fallback**: The `ENVIRONMENT=production` switch strictly rejects the default JWT secret fallback. This is an excellent protection mechanism.
*   **Admin Authentication**: `get_admin` securely validates `token_type == "admin"` and ensures inactive accounts cannot proceed. PrivEsc from Advocate -> Admin is blocked.
*   **MongoDB NoSQL Injection**: User input is passed heavily into `find_one` and update functions. Risk is low-medium due to Pydantic models.

## 7. Document Generation Audit

*   **PDF**: Deterministic PDF rendering is intended, but currently blocked in local tests by missing `reportlab`.
*   **DOCX/ODT**: Built via `docx_import.py` logic, relying heavily on regex placeholder matching.
*   **Gujarati Rendering**: Uses HarfBuzz via `uharfbuzz` for accurate ligature rendering of Lohit-Gujarati.

## 8. Template Audit

| Template | Fields | Problems | Severity | Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| Seed Data V2 | Varies | Seed data file `seed_data_templates_v2.py` defines templates strictly. Custom placeholders might conflict. | Medium | Ensure field definitions map strictly to exact `{{placeholder}}` matches. |

## 9. Authentication Audit

*   JWT based. Token structure uses `sub` and `ver` (version) claims.
*   A `token_version` in the DB invalidates older tokens on password reset. Excellent implementation.
*   Firebase Auth integration is solid. `firebaseExchange` handles the verification securely.

## 10. Database/Data Integrity

*   MongoDB uses schema-less designs without strict transaction scopes in payment mocks (`mock_purchase`).
*   Orphaned cases could occur if cascading deletes are ignored.

## 11. Mobile/Desktop UX

*   React Native Expo app handles Desktop and Mobile layouts via `useResponsive`.
*   Tabs layout ensures safe areas (`insets.bottom`).

## 12. Missing Tests

*   Playwright/Puppeteer E2E tests for the frontend.
*   More exhaustive NoSQL injection testing.

## 13. Production Readiness Score

| Subsystem | Score (0-10) |
| :--- | :--- |
| Architecture | 7 |
| Authentication | 8 |
| Security | 7 |
| Database | 6 |
| Templates | 7 |
| Case workflow | 7 |
| Application workflow | 7 |
| PDF | 2 |
| DOCX | 6 |
| ODT | 6 |
| PNG | 5 |
| Gujarati rendering | 7 |
| English rendering | 8 |
| Mobile UX | 8 |
| Desktop UX | 8 |
| Admin | 7 |
| Payments/Credits | 6 |
| Error handling | 7 |
| Testing | 6 |
| Deployment | 6 |
| Monitoring | 4 |
| Backup/recovery | 4 |

## 14. TOP 20 THINGS TO FIX

1. **Security Risk**: Audit and enforce all MongoDB endpoints against NoSQL injection patterns.
2. **Data-loss risk**: Review missing cascading deletes for historical records in MongoDB.
3. **Legal-document corruption risk**: Fix `uharfbuzz` environment to prevent broken Gujarati.
4. **Authentication failure**: Handle JWT expiry gracefully in `_layout.tsx` before the API rejects the next call.
5. **Financial/credit risk**: Wrap Razorpay webhooks in full MongoDB transactions.
6. **Production reliability**: Ensure `reportlab` is installed.
7. **Major UX problems**: Stale PWA cache.
8. **Minor UX**: Safe area insets on complex nested modals.
*(Only 8 significant distinct risks were positively identifiable based on the static audit)*

## 15. Recommended Execution Plan

*   **PHASE 1 — CRITICAL**: Fix document engine dependencies. Run tests to ensure PDF rendering works natively.
*   **PHASE 2 — HIGH**: Perform security sweep of all `Depends(get_user)` usage across `server.py` and enforce standard dependency injection.
*   **PHASE 3 — MEDIUM**: Add MongoDB compound indexes for case searching.
*   **PHASE 4 — POLISH**: Clean up PWA service worker caching.
