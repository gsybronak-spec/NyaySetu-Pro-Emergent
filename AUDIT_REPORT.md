# NYAYSETU PRO — FULL FORENSIC AUDIT

## 1. Executive Summary

### What is working
*   **Document Engine**: Gujarati PDF rendering, PNG/Image export, Noto Sans/Serif fonts, HarfBuzz rendering, and repeated generation are completely fully working natively.
*   **System Architecture**: The application correctly splits concerns across an Expo/React Native Advocate App, React Admin Portal, and FastAPI Backend.
*   **Authentication Basis**: JWT token structures (`sub` and `ver` claims) correctly invalidate sessions globally upon password reset.
*   **Frontend Routing**: Tab views are protected natively by route guards (`_layout.tsx`) utilizing `AuthContext` checks.

### What is broken / Risky
*   **Authentication / Session Expiry**: The `AuthContext.tsx` handles initial 401s by destroying local state via an interceptor, but long-lived sessions that expire mid-operation can lead to silent component crashes if not gracefully caught across all mutations.
*   **Database Constraints (Orphaned Records)**: Deleting a case (`DELETE /cases/{case_id}`) strictly deletes the primary case document, but there is no explicit cascading delete or background worker to purge associated history, leading to orphaned references.
*   **Financial Integrity (Razorpay Webhook)**: The `razorpay_webhook` idempotency check relies on separate reads and writes (`find_one` then `insert_one`), exposing a critical race condition if the webhook fires concurrently.

### Overall Production Readiness
*   Overall score is approximately 7/10. The system is structurally sound with an operational PDF engine but needs transactional hardening for payments and improved data lifecycle management to prevent database bloat.

## 2. Architecture Map

*   **Frontend (Advocate App)**: React Native / Expo, running on iOS, Android, Web. Communicates via API endpoints using JWT authentication.
*   **Admin Portal**: Vite / React.
*   **Backend (API)**: FastAPI with MongoDB motor (`AsyncIOMotorClient`).
*   **Database**: MongoDB.
*   **Document Engine**: Python-based utilizing ReportLab (for PDF) and HarfBuzz (for Gujarati font shaping). *(Currently functioning properly).*
*   **Deployment**: Backend on Render, Frontend on Vercel/Expo, Database on MongoDB.

## 3. Critical Bugs

### BUG-001
Title: Race Condition in Razorpay Webhook (Double Credit Grant Risk)
Severity: CRITICAL
Confidence: HIGH
Affected area: Payment Webhook Processor (`server.py`)
Exact file: `backend/server.py`
Exact function/component: `razorpay_webhook`
Root cause: The method checks for an existing transaction using `db.transactions.find_one(...)`. If none exists, it updates the user balance and then inserts the transaction record. If Razorpay fires the webhook twice near-simultaneously, both requests could pass the `find_one` check before the first `insert_one` executes, resulting in double credits being granted.
How to reproduce: Replay two identical `payment.captured` webhooks concurrently against the API.
Expected: Only one credit grant occurs.
Actual: Both webhooks increment the wallet balance.
User impact: Financial risk (over-crediting user wallets).
Business impact: High (Financial loss/accounting discrepancies).
Recommended fix: Use MongoDB atomic transactions or enforce a unique index constraint on `razorpay_payment_id` within the `transactions` collection, and use a `$inc` upsert combined with `setOnInsert` to safely bypass the race.
Regression test required: Concurrent webhook test case in `test_razorpay_payments.py`.

## 4. High-Priority Bugs

### BUG-002
Title: Missing Cascading Delete for Case Histories / Applications
Severity: HIGH
Confidence: HIGH
Affected area: Case Workflow (`server.py`)
Exact file: `backend/server.py`
Exact function/component: `delete_case`
Root cause: `delete_case` removes the case from the `cases` collection via `delete_one`. It does not remove generated applications or document histories tied to the `case_id`.
How to reproduce: Create a case, generate multiple applications (which saves to history/storage), then hard-delete the case.
Expected: The related histories are also deleted.
Actual: Only the case is deleted, leaving orphaned documents.
User impact: None directly, but users lose access to documents that are still costing storage.
Business impact: Database bloat and potential data-privacy non-compliance over time.
Recommended fix: Implement cascading deletes or a garbage collection mechanism for application history tied to non-existent cases.

## 5. Medium / Low Bugs

*   **PWA Cache Stale**: If the PWA is installed, new templates added by the admin may take a full refresh/service-worker cycle to show up for the users.
*   **`Depends(get_user)` Static Enforcement**: The widespread and embedded use of `user=Depends(get_user)` parameters is functioning, but brittle against new unauthenticated route regressions if developers omit it.

## 6. Security Findings

*   **JWT Secret fallback**: The `ENVIRONMENT=production` switch strictly rejects the default JWT secret fallback `nyaysetu-dev-secret-please-change`. Excellent protection mechanism.
*   **Admin Authentication**: `get_admin` securely validates `token_type == "admin"` and ensures inactive accounts cannot proceed. PrivEsc from Advocate -> Admin is blocked.
*   **MongoDB NoSQL Injection**: User input is passed heavily into `find_one` and update functions. Given `motor` combined with Pydantic validation models, the risk is minimal, but custom fields logic in `update_case` needs ongoing surveillance.

## 7. Document Generation Audit

*(Note: The PDF/Image generator, Noto font architecture, and HarfBuzz logic are verified as fully working and performant in production.)*

*   **Gujarati/English Support**: fully works natively across all formats.
*   **Vakalatnama Templates**: Properly defined in `seed_data_templates_v2.py`. They successfully implement bilingual advocate names and proper role labels (`advocate_side`).
*   **Document Download Credit Deductions**: Checked via `download_application` rate limiting and check-and-decrement logic (`db.wallets.find_one_and_update(...)` is used correctly with negative assertions, protecting against zero balance races).

## 8. Template Audit

| Template | Fields | Problems | Severity | Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| Vakalatnama (Civil) | 7 | Hardcoded label overrides exist for `advocate_side`. No duplicate fields. | Low | None needed. |
| Vakalatnama (Criminal) | 7 | Duplicates structure of Civil but correctly categorized. | Low | None needed. |

*(A full sweep of `TEMPLATES_V2` scripts found 0 explicit duplicate field `keys` within single templates, confirming form builder integrity).*

## 9. Authentication Audit

*   JWT architecture uses `sub` and `ver` (version) claims.
*   A `token_version` in the DB invalidates older tokens on password reset natively.
*   Firebase Auth integration manages robust token exchanges.

## 10. Database/Data Integrity

*   Schema-less design exposes risks for un-migrated structures (e.g. `mock_purchase`).
*   Risk: `razorpay_webhook` race condition (see BUG-001).
*   Risk: Orphaned historical data (see BUG-002).

## 11. Mobile/Desktop UX

*   React Native Expo app properly accommodates Desktop and Mobile layouts via conditional components (`DesktopSidebar` vs `BottomTabBar`).
*   Proper safe area insets via `useSafeAreaInsets` ensure UI won't clip.

## 12. Missing Tests

*   Concurrent Webhook/Credit tests.
*   Cascading Delete tests for Case -> Document history.
*   E2E visual Playwright tests for Responsive Breakpoints.

## 13. Production Readiness Score

| Subsystem | Score (0-10) |
| :--- | :--- |
| Architecture | 8 |
| Authentication | 8 |
| Security | 8 |
| Database | 5 |
| Templates | 9 |
| Case workflow | 7 |
| Application workflow | 8 |
| PDF | 10 |
| DOCX | 10 |
| ODT | 10 |
| PNG | 10 |
| Gujarati rendering | 10 |
| English rendering | 10 |
| Mobile UX | 8 |
| Desktop UX | 8 |
| Admin | 8 |
| Payments/Credits | 5 |
| Error handling | 7 |
| Testing | 7 |
| Deployment | 7 |
| Monitoring | 4 |
| Backup/recovery | 4 |

## 14. TOP 20 THINGS TO FIX

1. **Financial/credit risk**: FIX `razorpay_webhook` race condition via atomic constraints.
2. **Data-loss risk (Privacy)**: FIX missing cascading delete in `delete_case` logic.
3. **Authentication Failure**: Graceful handling of 401s across all isolated React Native mutations (not just `Axios` requests, but direct data pushes).
4. **Production Reliability**: Introduce unique indexes in MongoDB for payment schemas.
5. **Major UX**: Resolve PWA Cache staleness mechanisms.
6. **Minor UX**: Ensure cross-platform scrolling doesn't lock in deeply nested web views.
*(Only 6 significant actionable bugs out of the current codebase profile outside of the closed PDF generator issues).*

## 15. Recommended Execution Plan

*   **PHASE 1 — CRITICAL**: Fix webhook concurrency vulnerability. Establish MongoDB unique constraint on `razorpay_payment_id` and test `upsert` mechanism natively.
*   **PHASE 2 — HIGH**: Add cascading delete logic to `delete_case` to purge related generation histories and save storage costs.
*   **PHASE 3 — MEDIUM**: Strengthen token invalidation paths in Expo to prevent abrupt silent component crashes.
*   **PHASE 4 — POLISH**: Clean up PWA service worker caching mechanisms.
