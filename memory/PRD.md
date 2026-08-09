# NyaySetu Pro — PRD

## Original Problem Statement
Professional mobile app "NyaySetu Pro" (tagline: *The New Era of Advocacy*) for Indian Advocates to draft routine court applications fast and affordably. Advocate creates a case once, selects a template, auto-fills case data, enters only missing fields, previews, generates PDF/Word, and consumes 1 template credit. Deep Court Blue + Royal Gold premium legal-tech aesthetic, Gujarati + English support, dark mode.

## Architecture
- **Frontend**: Expo Router (React Native), theme context (light/dark), auth context (JWT in SecureStore), custom components (Button, Field, Dropdown).
- **Backend**: FastAPI + MongoDB (motor), JWT auth, mock OTP.
- **Docs**: Server-side generation — ReportLab (PDF, Noto Sans Gujarati bundled font for GU / Times-Roman for EN), python-docx (Word).
- **Data**: Seeded catalogs (case types, laws+sections, districts bilingual, 12 templates bilingual, plans, quotes).

## User Persona
Indian Advocates (Gujarat focus) needing routine court documents (adjournment, certified copy, exemption, bail, affidavit, etc.) without a typist.

## Core Requirements (static)
- Mobile OTP auth, advocate onboarding (skippable), 5 free credits.
- Case management with dependent dropdowns (case type → complaint type → law → section).
- Template library (bilingual, multilingual search: mudat/adjournment/મુદત).
- Application wizard: auto-fill → missing fields → date picker → preview → edit → PDF/Word → rename → share.
- Credit wallet, mock Razorpay pricing (₹9 single, ₹299/51, ₹499/251, ₹999/1111).
- Dark mode, profile, legal pages, referral (info).

## Implemented (2026-06)
- [x] Splash + branding, mobile OTP login, onboarding, congrats screen
- [x] Bottom tabs: Home, My Cases, Templates, Subscription, Profile
- [x] Dashboard: welcome card + quote + wallet chip, action cards, continue drafting, categories, most-used templates grid
- [x] Case creation with language toggle + dependent dropdowns; case detail with Create Application
- [x] Template library with category chips + multilingual search
- [x] Application generation wizard (3 steps) with auto-fill, date picker, preview, PDF/Word download + share, rename, autosave draft
- [x] Server-side PDF (Gujarati font) + DOCX generation
- [x] Credit wallet + atomic consumption, mock purchase
- [x] Dark mode toggle, profile with legal pages
- [x] **Google Sign-In (Emergent-managed OAuth)** — /api/auth/google-session, upsert user by email, issues app JWT (login screen "Continue with Google")
- [x] **Referral Rewards** — unique referral_code per user, +10 credits to referrer on new signup (OTP or Google), anti-abuse (no self-referral, one reward per referred user), /api/referral/me stats, dedicated /referral screen with copy + share
- [x] **Case Management module (enhanced)** — searchable dropdowns (case type/law/district/section); refined bilingual case-type catalog (23 types) + laws (incl. family/property) with dependent sections; server-enriched case labels (category/type/law/section/district/complaint) with GU/EN display; My Cases with filter chips (All/Civil/Criminal/Other) + search + archived toggle; shared CaseForm for create/edit; case detail with Edit/Archive/Restore/Delete (delete confirmed, archive reversible); case→application reference model with application_count
- [x] **Template Library (23 templates)** — expanded to 23 bilingual court applications with multilingual aliases; direct-use from Templates tab
- [x] **Structured Court & Police Station pickers** — /api/catalog/courts?district_id= (district-specific + generic) and /api/catalog/police-stations?district_id=; case stores court_id/police_station_id (+custom "Other"); labels resolved GU/EN and used in generated docs
- [x] **Case sorting** — /api/cases?sort=updated|name|type; My Cases Sort modal (Recently Updated / Name A-Z / Case Type)
- [x] **Court Favourites** — per-user pinned courts (/api/favourites/courts add/remove); favourited courts show a gold star and are grouped to the top of the Court picker

## Backlog (P1/P2)
- P1: Live Razorpay (backend order+verify + web checkout) — awaiting user's Razorpay Key ID + Secret; mock active until then
- P1: Transaction history screen, template usage analytics screen
- P2: Admin panel (template/pricing/margin management), support ticketing
- P2: More templates (20-25), transliteration search improvements

## Next Tasks
- Gather Razorpay keys for live payments
- Expand template catalog per Admin config
