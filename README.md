# PMKetoan

Vietnamese accounting software (Visota). Built with Django 5.2 + django-ninja + HTMX + Alpine.js + MariaDB.

Tuân thủ TT133/2016, TT200/2014, TT78/2021 (HĐĐT), Luật Kế toán 2015, Luật Đấu thầu 23/2023.

## Quick Start

```bash
# Install dependencies
make install

# Setup database (requires MariaDB running)
mysql -u root -e "CREATE DATABASE pmketoan CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE USER 'pmketoan'@'localhost' IDENTIFIED BY 'devpass'; GRANT ALL ON pmketoan.* TO 'pmketoan'@'localhost';"

# Configure environment
cp .env.example .env

# Run migrations + seed demo data
make migrate
make seed

# Start dev server
make dev
# Open http://localhost:8000/auth/login/ -> admin / admin123
```

## Testing

```bash
make test          # unit tests (521 passing)
make test-fast     # parallel

# E2E tests (requires running server on port 8903)
DJANGO_SETTINGS_MODULE=config.settings.e2e python manage.py runserver 8903 --noreload &
pytest -c pytest_e2e.ini   # 164 Playwright tests
```

## Key Features

| Module | Status |
|--------|--------|
| Kế toán tổng hợp (TT133) | Production |
| Bán hàng + Công nợ phải thu | Production |
| Mua hàng + Công nợ phải trả | Production |
| Tồn kho + Tính giá | Production |
| Tài sản cố định + Khấu hao | Production |
| Nhân sự + Tiền lương + PIT | Production |
| Hóa đơn điện tử (TT78) | Stub (provider API) |
| Hợp đồng + 22 mẫu văn bản | Production |
| CRM (Lead/Opp/Ticket/Campaign) | Production |
| Ngân hàng + Đối soát | Production |
| Bảo lãnh + Vay vốn | Production |
| Đấu thầu (Luật 23/2023) | Production |
| Ngân sách + Dòng tiền | Production |
| Định giá ngoại tệ | Production |
| Phê duyệt (Workflow) | Production |

### Startup-focused features (P0-P2)

- **Onboarding Wizard** -- multi-step signup with auto-seed TT133
- **Dashboard CEO** -- cash position, P&L card, AR aging, tax calendar
- **Mobile Home Screen** -- compact metrics + quick actions
- **Quick Expense** -- 1-line entry, auto-generates voucher
- **Guided Voucher Mode** -- pick action, auto-generates journal entry
- **Contract Wizard** -- guided template selection
- **Auto Tax Reminders** -- notifications 7d + 1d before deadlines
- **Knowledge Base** -- in-app help center with seed articles
- **Simplified CRM** -- hides Ticket/Campaign for micro/small companies
- **VietQR Dynamic** -- QR thanh toan on invoices
- **E-invoice PDF** -- signed PDF with stamp overlay
- **Voice Input** -- Web Speech API (vi-VN)
- **F-keys Shortcuts** -- F2/F3/F8/F9/ESC context-aware

## Documentation

See `docs/` for full documentation:
- `docs/INDEX.md` -- Operations documentation index
- `docs/README.md` -- Design specification master index
- `docs/runbook/` -- Monthly/yearly close, tax filing, deploy
- `docs/strategy/` -- Feature gap analysis, go-to-market

## Deployment

See `docs/runbook/deploy-vps.md` for VPS deployment guide.

```bash
# Production deploy (on VPS)
git pull origin main
python manage.py migrate --noinput
python manage.py seed_permissions
python manage.py collectstatic --noinput --clear
sudo systemctl reload visota
```
