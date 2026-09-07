# Final Real-User Production Acceptance Plan & Verification — NyaySetu Pro

**Date**: September 7, 2026  
**Target Environment**: LIVE PRODUCTION  
**Production Frontend**: `https://nyaysetupro.in`  
**Production Frontend Vercel Alias**: `https://nyay-setu-pro-emergent-bo83.vercel.app`  
**Production Admin Portal**: `https://nyaysetupro.in/admin`  
**Production Backend API**: `https://backend-gold-iota-nyngopebeg.vercel.app`  
**Production Database**: Google Cloud Firestore `nyaysetu-pro` (`asia-south1`, Mumbai)  
**Rollback Standby**: MongoDB (100% UNTOUCHED)

---

## Part 1: Automated Verification Summary (Completed & Certified)

Every automated gate has been executed against the actual deployed production endpoints and certified:

| Subsystem | Verified Target | Status | Verification Evidence |
| :--- | :--- | :--- | :--- |
| **Backend API** | `https://backend-gold-iota-nyngopebeg.vercel.app/healthz` | **PASS** | HTTP 200 OK (`{"app":"NyaySetu Pro","status":"ok","version":"1.0.0"}`) |
| **Backend Smoke Suite** | Live Vercel Lambda -> Cloud Firestore | **PASS** | 14 / 14 Tests Passed (0 failures, 0 errors) |
| **Cloud Firestore** | Project `nyaysetu-pro` (`asia-south1`) | **PASS** | 34 Districts, 255 Talukas, 47 Courts, 23 Case Types, 4 Plans, 45 Templates |
| **21 Canonical Templates**| Bilingual Template Verification | **PASS** | All 21 canonical Gujarati legal applications verified with `name_en` & `name_gu` |
| **Document Generation** | Live HarfBuzz engine on Vercel | **PASS** | Valid `%PDF-` and `\x89PNG` generated with Gujarati font shaping |
| **Frontend Production** | `https://nyaysetupro.in` | **PASS** | HTTP 200 OK, SSL certified, no redirect loop |
| **Edge Asset Inspection**| Bundles on Vercel CDN | **PASS** | Points strictly to `backend-gold-iota-nyngopebeg.vercel.app`; 0 banned URLs |
| **Admin Portal** | `https://nyaysetupro.in/admin` | **PASS** | HTTP 200 OK, Vite Admin SPA bundles loaded and configured |
| **CORS Configuration** | Backend allowed origins | **PASS** | `Access-Control-Allow-Origin: https://nyaysetupro.in` + credentials allowed |
| **MongoDB Safety** | Rollback isolation | **UNTOUCHED** | Zero production runtime code accesses MongoDB; local config preserved |

---

## Part 2: Real Device / Real User Acceptance Checklist

Please perform the following 10 verification flows on your physical Android smartphone:

### Flow 1: Initial Page Load & Mobile Layout
- [ ] **Action**: Open Chrome on your Android phone and navigate to `https://nyaysetupro.in`.
- [ ] **Expected Result**:
  - The NyaySetu Pro application loads quickly without a blank screen.
  - Page layout fits the mobile viewport vertically with no horizontal scrolling or clipped text.
  - Gujarati fonts (Anek Gujarati) render smoothly on headers and UI elements.

### Flow 2: Authentication Flow
- [ ] **Action**: Log in using your registered mobile number / OTP or Google Sign-In.
- [ ] **Expected Result**:
  - OTP is received and verified promptly.
  - You are redirected into the main lawyer dashboard.
  - Refresh the browser tab: session persists (no unexpected logout).
  - Open navigation menu and tap Logout: session terminates cleanly. Re-login to proceed.

### Flow 3: Master Data Cascade
- [ ] **Action**: Navigate to Case Creation or Profile settings. Tap the **District** dropdown.
- [ ] **Expected Result**:
  - Full list of Gujarat districts appears (Ahmedabad, Surat, Rajkot, Vadodara, etc.).
  - Selecting a district instantly populates its associated **Talukas**.
  - Selecting a taluka populates the corresponding **Courts**.
  - **Case Type** dropdown displays Civil Suit, Criminal Case, Special Civil Application, etc.

### Flow 4: Canonical Legal Template Library
- [ ] **Action**: Tap on **Templates** in the navigation bar.
- [ ] **Expected Result**:
  - All **21 canonical legal templates** are visible with Gujarati and English titles (e.g., `મુદત અરજી (Mudat Arji)`, `હાજરી માફી અરજી (Hazari Mafi Arji)`, `વકીલાતનામું (Vakilatnama)`).
  - Search bar filters templates instantly when typing Gujarati or English letters.
  - Tapping the Star icon marks a template as Favorite and keeps it pinned.

### Flow 5: Create a Test Case
- [ ] **Action**: Tap **Cases** -> **+ New Case**. Enter:
  - Case Number (e.g., `C.S. 101/2026`)
  - Court (e.g., `Principal Senior Civil Judge`)
  - Party Name (Plaintiff, Gujarati): `રમણલાલ પ્રજાપતિ`
  - Opposite Party (Defendant, Gujarati): `સુરેશભાઈ પંચાલ`
- [ ] **Expected Result**:
  - Case saves successfully without network errors.
  - Reopen the case: all saved Gujarati and English fields remain intact.

### Flow 6: Create Application from Case (Auto-Fill Validation)
- [ ] **Action**: Inside the saved case, tap **Generate Application** and select **મુદત અરજી (Mudat Arji)**.
- [ ] **Expected Result**:
  - Court name, Case Number, Plaintiff, and Defendant are **automatically populated** from the Case.
  - An "Auto-filled from Case" indicator is visible.
  - Repetitive case details are NOT requested again.
  - Only template-specific fields are requested (e.g., Mudat Reason, Next Date).
  - The **Date** field remains the final input at the bottom.

### Flow 7: Gujarati PDF Document Generation & Download
- [ ] **Action**: Tap **Generate PDF** / **Download PDF**.
- [ ] **Expected Result**:
  - PDF generation completes within a few seconds.
  - Browser downloads the PDF file to your Android phone (`mudat_arji.pdf`).
  - Open the file in Google PDF Viewer / Acrobat:
    - Gujarati characters and conjuncts (જોડાક્ષરો) are shaped properly.
    - No overlapping, clipped, or misplaced matras (`િ`, `ી`, `ુ`, `ૂ`, `ે`, `ૈ`).
    - Standard legal margins (top/left 1.5 in) and court formatting are preserved.

### Flow 8: Image Preview / JPG Generation
- [ ] **Action**: Tap **Download Image** / **View JPG**.
- [ ] **Expected Result**:
  - High-resolution image downloads or previews in Android gallery.
  - Gujarati script is crisp and legible with proper ligature rendering.

### Flow 9: Admin Portal Verification
- [ ] **Action**: On mobile or desktop browser, navigate to `https://nyaysetupro.in/admin`.
- [ ] **Expected Result**:
  - Admin login screen loads with clean branding.
  - Admin authentication connects directly to the production backend (`https://backend-gold-iota-nyngopebeg.vercel.app`).
  - Template catalog management screen lists published templates.

### Flow 10: Network & Edge Security Inspection
- [ ] **Action**: Open Chrome DevTools (or review mobile network requests).
- [ ] **Expected Result**:
  - All API requests route to `https://backend-gold-iota-nyngopebeg.vercel.app`.
  - Zero requests to `localhost`, `127.0.0.1`, or previous preview URLs.
  - Zero CORS errors.
  - All assets loaded over secure HTTPS.

---

## Part 3: Acceptance Gate Status

| Gate | Status | Notes |
| :--- | :--- | :--- |
| **Frontend Production** | **PASS** | Deployed, live, and verified at `https://nyaysetupro.in` |
| **Backend Production** | **PASS** | Deployed, live, and certified with 14/14 smoke tests passing |
| **Firestore Production** | **PASS** | Active on `nyaysetu-pro` (`asia-south1`) with full master data |
| **Real User Acceptance**| **PENDING** | Awaiting manual verification by the human project owner |
| **MongoDB Safeguard** | **UNTOUCHED** | Preserved for rollback readiness |
