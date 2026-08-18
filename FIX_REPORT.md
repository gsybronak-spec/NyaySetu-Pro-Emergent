# AUTHENTICATION SESSION BUG — FINAL FIX REPORT

## Root Cause
When the API responded with a 401 Unauthorized status, the Axios/fetch interceptor in `client.ts` triggered the `onUnauthorized` callback inside `AuthContext.tsx`. This callback set the in-memory `user` state to `null` and purged the cached profile from storage, but *failed* to physically delete the underlying JWT (`TOKEN_KEY`) from secure storage.

As a result, the `_layout.tsx` route guard correctly redirected the user to the login screen, but upon a browser refresh or app restart, the application re-hydrated the dead token. It would then attempt to fetch `/profile/me` using the dead token, receive another 401, clear the state again, and endlessly loop back to login. Furthermore, multiple asynchronous requests failing simultaneously with 401s caused race conditions where the state was cleared repeatedly.

## Files Changed
- `frontend/src/context/AuthContext.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/context/__tests__/AuthContext.test.tsx` (Added)

## Authentication Flow Before
1. App hydrates token.
2. Token is dead.
3. API returns 401.
4. Interceptor drops `user` state.
5. `_layout.tsx` redirects to `/login`.
6. Token *remains* in storage.
7. Next reload -> GOTO 1 (Loop).

## Authentication Flow After
1. App hydrates token.
2. Token is dead.
3. API returns 401.
4. Interceptor fires *once* across all concurrent requests via a debounce/lock mechanism.
5. Callback explicitly calls `await setToken(null)` to nuke the token from secure storage.
6. Interceptor drops `user` state.
7. `_layout.tsx` redirects to `/login`.
8. Next reload -> No token found. Safe halt at login screen.

## 401 Handling
401s now trigger a complete sanitization of the storage layer. Specifically, `await setToken(null)` is forcefully awaited before any component unmounts.

## Token Storage Handling
The `TOKEN_KEY` is fully dropped.

## Concurrent 401 Protection
Introduced `isUnauthorizedHandling` boolean lock in `client.ts` around the `onUnauthorized` invocation. If 5 requests simultaneously return 401, the callback is only fired once, and then locked out for 1 second. This prevents React state racing.

## Login Persistence
Normal logins are totally unaffected. Valid tokens remain in storage and successfully bypass the 401 handler, satisfying the requirement to persist valid sessions across reloads.

## Regression Tests
Added `frontend/src/context/__tests__/AuthContext.test.tsx` which explicitly tests:
1. `removes token, profile, and user state on backend 401`
2. `handles valid stored token on startup and preserves dashboard`
3. `removes token if invalid stored token exists on startup`
4. `Multiple simultaneous 401 responses logout handling occurs only once`
5. `Fresh login after an expired session works normally`
6. `Backend 401 -> in-memory user state becomes null`

## Unchanged Protected Systems
I explicitly confirm:
- PDF engine unchanged
- Gujarati document fonts unchanged
- HarfBuzz unchanged
- PNG/Image generation unchanged
- DOCX unchanged
- ODT unchanged
- Razorpay unchanged
- Templates unchanged
- PWA icon system unchanged
