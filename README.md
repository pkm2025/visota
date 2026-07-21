# Visota ERP

ERP cho doanh nghiệp siêu nhỏ và nhỏ (DNSN). Built with Django 5.2 + django-ninja + HTMX + Alpine.js + MariaDB.

Tuân thủ TT58/2026/TT-BTC (DNSN), TT133/2016, TT200/2014, TT78/2021 (HĐĐT), Luật Kế toán 2015, Luật Đấu thầu 23/2023.

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

# Seed TT58 demo data (DNSN companies for all 4 tax method groups)
python manage.py seed_tt58_demo

# Start dev server
make dev
# Open http://localhost:8903/auth/login/ -> admin / admin123
```

## Testing

```bash
make test          # unit tests (1900+ passing)
make test-fast     # parallel

# E2E tests (requires running server on port 8903)
DJANGO_SETTINGS_MODULE=config.settings.e2e uvicorn config.asgi:application --host 0.0.0.0 --port 8903 &
pytest -c pytest_e2e.ini
```

## Key Features

| Module | Status |
|--------|--------|
| Kế toán tổng hợp (TT133/TT200) | Production |
| **Kế toán DNSN (TT58/2026)** | **Production** |
| Bán hàng + Công nợ phải thu | Production |
| Mua hàng + Công nợ phải trả | Production |
| Tồn kho + Tính giá | Production |
| Tài sản cố định + Khấu hao | Production |
| Nhân sự + Tiền lương + PIT | Production |
| Hóa đơn điện tử (TT78 + 02BANHANG) | Stub (provider API) |
| Hợp đồng + 22 mẫu văn bản | Production |
| CRM (Lead/Opp/Ticket/Campaign) | Production |
| Ngân hàng + Đối soát | Production |
| Bảo lãnh + Vay vốn | Production |
| Đấu thầu (Luật 23/2023) | Production |
| Ngân sách + Dòng tiền | Production |
| Định giá ngoại tệ | Production |
| Phê duyệt (Workflow) | Production |

### TT58/2026/TT-BTC (Doanh nghiệp siêu nhỏ)

- **4 nhóm phương pháp nộp thuế** (GTGT + TNDN combinations)
- **Sổ kế toán DNSN** (S1-S3 theo nhóm thuế, không dùng hệ thống tài khoản)
- **Chứng từ đơn giản** (phiếu thu/chi/nhập/xuất, không hạch toán Nợ/Có)
- **Báo cáo tài chính DNSN** (B01-DNSN, B02-DNSN)
- **Chuyển đổi số dư** từ TT132/TT133 sang TT58
- **Hóa đơn 02BANHANG** cho DN nộp thuế GTGT theo tỷ lệ %
- **Hỗ trợ hộ kinh doanh** (entity type riêng, không bắt buộc kế toán trưởng)

### Startup-focused features (P0-P2)

- **Onboarding Wizard** -- multi-step signup with auto-seed
- **Dashboard DNSN** -- simplified widgets (doanh thu, chi phí, lợi nhuận, thuế, công nợ, tồn kho)
- **Mobile Home Screen** -- compact metrics + quick actions
- **Quick Expense** -- 1-line entry, auto-generates voucher
- **Guided Voucher Mode** -- pick action, auto-generates journal entry
- **Modular Sidebar** -- core modules by default, advanced modules on-demand
- **Contract Wizard** -- guided template selection
- **Auto Tax Reminders** -- notifications 7d + 1d before deadlines
- **Knowledge Base** -- in-app help center with seed articles
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


### PKM Module (Personal Knowledge Management)

Module quản trị tri thức cá nhân cho mọi user theo vai trò công việc.

- **Notes** -- ghi chú cá nhân với markdown, tags, ghim, tìm kiếm, role-based context
- **Documents + RAG** -- upload PDF/DOCX/TXT/MD/XLSX, tự động chunk + embed + vector search
- **Q&A AI** -- hỏi đáp dựa trên (RAG), trích nguồn, lưu lịch sử
- **Multi-provider LLM** -- OpenAI, Anthropic, Gemini, Groq, OpenRouter, Ollama (local)
- **Vector storage** -- MariaDB 12.3 native VECTOR + HNSW index


Truy cập:
- Browser UI: `/modern/knowledge/` (cần quyền `pkm.access`)
- API: `/api/v1/pkm/`
