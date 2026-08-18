# NYAYSETU PRO — SECOND-STAGE FORENSIC VERIFICATION

## 1. VERIFIED CRITICAL BUGS

### BUG-001
ID: BUG-001
TITLE: Concurrent Razorpay Webhook Causes Double Crediting
STATUS: FALSE POSITIVE / ALREADY PROTECTED
SEVERITY: CRITICAL
CONFIDENCE: HIGH
EXACT FILE: `backend/server.py`
EXACT FUNCTION: `razorpay_webhook`
EXACT CODE PATH: `await db.wallets.update_one({"user_id": user["id"]}, {"$inc": {"balance": plan["credits"]}...})` followed by `db.transactions.insert_one({"razorpay_payment_id": payment_id})`
EVIDENCE: The `create_indexes` function runs on `@app.on_event("startup")` and enforces: `await _ensure_index(db.transactions, "razorpay_payment_id", unique=True, sparse=True)`. In the `razorpay_webhook` function, the `insert_one` is wrapped in a `try...except`. If `insert_one` fails due to the unique index violation (duplicate `razorpay_payment_id`), the `except` block explicitly rolls back the wallet increment (`{"$inc": {"balance": -plan["credits"]}}`). This guarantees idempotency natively in MongoDB without requiring a multi-document transaction lock.
USER IMPACT: None (Safely handled).
BUSINESS IMPACT: None (No double credits issued).
RECOMMENDED FIX: None required.
REGRESSION TEST: Ensure `test_razorpay_payments.py` includes a concurrent webhook invocation test to prove the unique index catches the race condition natively.

### BUG-003
ID: BUG-003
TITLE: Unexpected Automatic Logouts Due to Incomplete Token Refresh Architecture
STATUS: REAL BUG
SEVERITY: HIGH
CONFIDENCE: HIGH
EXACT FILE: `frontend/src/context/AuthContext.tsx`
EXACT FUNCTION: `AuthContext.refresh` & `_layout.tsx`
EXACT CODE PATH: `client.ts` sets `onUnauthorized` which clears `user` but DOES NOT clear `TOKEN_KEY` from `secureStore`. If a user session expires mid-use (401), `user` is set to `null`, which causes `_layout.tsx` (`if (ready && !user) return <Redirect />`) to dump the user to the login screen. However, because `storage.secureRemove(TOKEN_KEY)` isn't called inside `onUnauthorized`, the app remains structurally confused upon refresh—re-hydrating the dead token, fetching `/profile/me`, receiving another 401, and looping out.
EVIDENCE: The `setOnUnauthorized` callback only calls `setUser(null)` and `await storage.remove("nyaysetu_user_profile")`. It does not forcefully remove the core JWT (`await setToken(null)`).
USER IMPACT: High. Active users are unexpectedly bumped to the login screen without graceful session persistence, and app reloads can fail repeatedly.
BUSINESS IMPACT: High churn and perceived instability of the core drafting tool.
RECOMMENDED FIX: Inside `setOnUnauthorized`, ensure `await setToken(null)` is called. Additionally, implement silent token refresh headers if a valid `token_version` mutation happens, or show a graceful "Session Expired" modal instead of a harsh hard redirect.
REGRESSION TEST: Write a test where an active logged-in user receives a mock 401 response, verifying they are cleanly logged out at the storage level, not just the state level.

## 2. VERIFIED HIGH BUGS

### BUG-002
ID: BUG-002
TITLE: Missing Cascading Delete Leaves Orphaned Application Documents
STATUS: DESIGN RISK
SEVERITY: MEDIUM
CONFIDENCE: HIGH
EXACT FILE: `backend/server.py`
EXACT FUNCTION: `delete_case`
EXACT CODE PATH: `await db.cases.delete_one({"id": case_id, "user_id": user["id"]})`
EVIDENCE: Deleting a case correctly purges the `cases` collection. However, generated applications remain in `db.applications` (tied to `case_id`) and drafts remain in `db.drafts`.
USER IMPACT: The user expects their data to be deleted when they delete a case. But the document metadata and drafts persist in the background.
BUSINESS IMPACT: Compliance (Data Privacy) risk and uncontrolled database bloat.
RECOMMENDED FIX: Do NOT aggressively cascade-delete `applications`. Legal systems often require audit trails. Introduce a soft-delete mechanism for cases (`{"status": "deleted"}`) instead of hard `delete_one`, or offer an explicit "Purge Case History" endpoint. Drafts should be purged (cascade delete) on case deletion, but applications should merely lose their case reference or be archived.
REGRESSION TEST: A unit test verifying `db.drafts` count decreases when a parent case is deleted.

## 3. VERIFIED MEDIUM/LOW BUGS

### BUG-004
ID: BUG-004
TITLE: Stale PWA Cache Manifests
STATUS: FALSE POSITIVE
SEVERITY: LOW
CONFIDENCE: HIGH
EXACT FILE: `frontend/vercel.json`
EXACT FUNCTION: Deployment Headers
EXACT CODE PATH: `Cache-Control: public, max-age=0, must-revalidate` is strictly enforced on `manifest.json`.
EVIDENCE: There is no overly-aggressive `service-worker.js` caching static assets locally. The Vercel deployment correctly invalidates the frontend routing.
USER IMPACT: Minimal.
BUSINESS IMPACT: Minimal.
RECOMMENDED FIX: None.
REGRESSION TEST: N/A.

## 4. FALSE POSITIVES

*   **PWA Stale Cache**: No custom service worker locks assets. Vercel headers handle `index.html` well.
*   **Double Payments (Race Condition)**: The webhook uses a unique `razorpay_payment_id` sparse index and gracefully rolls back the wallet increment if the insert throws an exception.
*   **Duplicate Template Fields**: Parsed the `TEMPLATES_V2` arrays. No template contains duplicate `key` definitions.

## 5. ALREADY PROTECTED AREAS

*   **Document Engine**: The Noto font stack, ReportLab integration, and HarfBuzz OpenType logic are heavily tested and strictly isolated in `backend/doc_generator.py`. They operate safely.
*   **Security (IDOR)**: `get_case`, `update_case`, `delete_case`, and `application_history` endpoints all tightly couple operations to `user_id: user["id"]`. It is impossible for User A to modify User B's case. Admin boundaries strictly enforce `token_type == "admin"`.
*   **Gujarati/English Language Switch**: Tests prove that mixed strings, ligatures, and conditionally rendered placeholders correctly render natively.
*   **Single Application Workflow**: Template selection allows rendering without a `case_id`, smoothly ignoring the `client_ctx` enrichment logic.

## 6. MISSING TEST COVERAGE

1.  **Concurrent Razorpay Webhooks**: Explicitly sending two `payment.captured` webhooks simultaneously in `test_razorpay_payments.py` to assert the unique constraint triggers the rollback.
2.  **Session Logout Flow**: Asserting that a `401` from the backend correctly flushes the `TOKEN_KEY` from secure storage in the React Native layer.
3.  **Draft Pruning**: Validating that deleting a case safely purges `db.drafts` where `case_id` matches.

## 7. RECOMMENDED FIX ORDER

1.  **Auth (High)**: Fix the `setOnUnauthorized` clear logic in the frontend `client.ts` to fully remove the token, solving the automatic logout loop.
2.  **Data Lifecycle (Medium)**: Soft-delete cases instead of hard-deleting them to preserve legal document audit history, while purging irrelevant drafts.
3.  **Testing (Polish)**: Add the explicit concurrent webhook test to permanently close the perceived financial race condition risk in future audits.
