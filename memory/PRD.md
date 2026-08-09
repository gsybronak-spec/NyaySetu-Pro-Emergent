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

## Backlog (P1/P2)
- P1: Real Razorpay integration (needs keys), Google Sign-In, transaction history screen, template usage analytics screen
- P1: Rich-text preview editing (currently form-edit re-generates preview)
- P2: Admin panel (template/pricing/margin management), referral tracking backend, support ticketing, WhatsApp/email direct share targets
- P2: More templates (20-25), transliteration search improvements

## Next Tasks
- Gather Razorpay keys for live payments
- Expand template catalog per Admin config
