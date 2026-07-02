# CHANGELOG

## v3.1.0 (2026-07-02) — Test Suite Recovery + P1/P2 Features

### Bug Fixes

- **staticfiles manifest**: Override `STORAGES` in test settings to use
  `StaticFilesStorage` instead of `CompressedManifestStaticFilesStorage`
  which requires a collectstatic manifest that doesn't exist during testing
  (fixed 51 test failures).
- **axes segfault**: Set `AXES_HANDLER = AxesDummyHandler` in test settings
  to avoid `AxesDatabaseHandler.user_logged_in` -> `reset_user_attempts`
  which segfaults in MySQLdb C code during `force_login()`.
- **time-sensitive tests**: `general_ledger` test now passes `period` param;
  `bc01` test sets `issue_date` explicitly to match report period.
- **e2e locator**: Sales invoice table locator uses `.first` (VietQR added
  2nd table to page).
- **mobile CSS**: `topbar-left`/`topbar-right` responsive rules for <768px
  to prevent horizontal overflow on mobile.
- **timezone-aware datetime**: `generate_bc01` now uses `timezone.make_aware()`
  instead of naive `datetime()` for issue_date range filter.

### New Features (P1)

- **Auto Tax Reminders** (`send_tax_reminders` command): Sends in-app
  notifications 7 days and 1 day before VAT, PIT, BHXH deadlines. Dedup
  via hash key prevents duplicate alerts. Supports `--dry-run` mode.

### New Features (P2)

- **Mobile Home Screen**: Compact metrics row (Tien, Doanh thu, Cong no)
  + 4 quick action buttons (Phieu, Duyet, Bao cao, Thong bao) with badge
  counts. Hidden on desktop (`d-md-none`).
- **Simplified CRM**: Sidebar hides Ticket/Campaign for micro/small
  companies (`sme_size` field). Lead + Opportunity always visible.
- **Contract Wizard** (`/modern/contracts/wizard/`): Guided template
  selection by category (labor, commercial, construction, minutes,
  decision, other). ContractCreateView accepts `?template=CODE` param.
- **Knowledge Base** (`/modern/help/`): In-app help center with searchable
  article index. Seed command creates 5 initial articles (HDDT, TT133,
  VAT filing, hiring, month-end close).

### Code Quality

- Auto-fixed 65 lint errors in `apps/` (unused imports, import sorting).
- Formatted 41 files with `ruff format`.
- Added 20 new tests (7 tax reminder, 2 dashboard mobile, 2 CRM simplify,
  3 contract wizard, 6 help center).

### Test Results

| Suite | Before | After |
|-------|--------|-------|
| Unit tests | 446 pass, 55 fail | **521 pass, 0 fail** |
| E2E tests | 164 collected (segfault) | **164 pass, 0 fail** |
| Total | — | **685 pass, 0 fail** |

---

## v3.0.0 (2026-06-26) — Initial Production Release

- 28 Django apps covering full accounting workflow
- TT133/2016 and TT200/2014 compliance
- Multi-tenant with 8 system roles and 25 module permissions
- 153 URL endpoints, 120 templates, 53 migrations
- PWA with offline support, mobile bottom nav
- VietQR dynamic, e-invoice PDF with stamp, voice input, F-keys shortcuts
