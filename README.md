# PMKetoan

Vietnamese accounting software. Built with Django 5.2 + django-ninja + HTMX + Alpine.js + MariaDB.

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
# Open http://localhost:8000/auth/login/ → admin / admin123
```

## Testing

```bash
make test
make test-fast  # parallel
```

## Documentation

See `docs/` for full design documentation:
- `docs/README.md` — Master index
- `docs/01-tong-quan/` — System overview
- `docs/09-ke-hoach-trien-khai/` — Roadmap

## Deployment

See `docs/05-kien-truc-ky-thuat/06-deployment.md`.
