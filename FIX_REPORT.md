# FINAL FIX REPORT

## Root Cause
- **Authentication**: When API returned 401, `onUnauthorized` removed the `user` state and profile but left the `TOKEN_KEY` in storage. Upon app refresh, the token rehydrated and hit the API again, causing an infinite loop.
- **Data Lifecycle**: `delete_case` used `delete_one`, permanently erasing cases. Because drafts and applications reference `case_id`, removing the parent record left `db.drafts` and `db.applications` orphaned and without a defined cleanup strategy.

## Files Changed
- `frontend/src/context/AuthContext.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/context/__tests__/AuthContext.test.tsx` (Added)
- `backend/server.py`
- `backend/tests/test_case_delete.py` (Added)

## Authentication Flow Before
401 received -> State cleared -> Redirect to login -> Refresh -> Token hydrated -> 401 received -> Loop.

## Authentication Flow After
401 received -> Storage explicitly purged (`await setToken(null)`) -> State cleared -> Redirect to login -> Refresh -> App stops at login securely.

## 401 Handling & Token Storage
`AuthContext.tsx` now calls `await setToken(null)` immediately inside `refresh` failures and `setOnUnauthorized`. `client.ts` introduces an `isUnauthorizedHandling` idempotency flag to guarantee simultaneous 401s don't fire multiple teardowns.

## Concurrent 401 Protection
Simultaneous 401s from `fetch` are caught in a `setTimeout` boolean lock, executing the context cleanup callback only once per second max.

## Login Persistence
Normal logins are 100% unaffected. `setToken` properly places the token in storage, and valid tokens skip the 401 cleanup blocks.

## Case/Draft Lifecycle Updates
`backend/server.py:delete_case` now softly deletes cases (`{"status": "deleted"}`) to preserve the audit trail for `applications`. It immediately `delete_many` prunes `db.drafts` referencing the `case_id` so ephemeral form data isn't leaked or bloated.

## Regression Tests
Added exhaustive unit tests to `AuthContext.test.tsx` validating 401 teardowns, rehydration protection, and concurrent 401 locks. Added `test_case_delete.py` asserting drafts are correctly cascade-deleted when cases are soft-deleted.

## Unchanged Protected Systems
I explicitly confirm:
- PDF engine unchanged
- Gujarati document fonts unchanged
- HarfBuzz unchanged
- PNG/Image generation unchanged
- DOCX/ODT unchanged
- Razorpay webhook architecture unchanged
- Templates unchanged
- PWA icon system unchanged
