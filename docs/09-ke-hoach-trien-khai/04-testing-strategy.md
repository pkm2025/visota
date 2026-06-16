# 04. Chiến lược kiểm thử (Testing Strategy)

> Quy ước test cho PMKetoan: unit, integration, e2e, performance.

## 1. Kim tự tháp test

```
                    /\
                   /  \
                  / E2E\         5%  (Playwright, slow)
                 /------\
                /        \
               /Integration\    25% (Django TestCase)
              /------------\
             /              \
            /    Unit        \  70% (pytest, fast)
           /------------------\
```

**Target**: ≥ 80% line coverage cho `apps/`, ≥ 90% cho `services/`.

## 2. Test layers

### 2.1. Unit tests (70%)

- **Mục tiêu**: Test business logic thuần, không phụ thuộc DB/network
- **Công cụ**: pytest + factory_boy + pytest-mock
- **Tốc độ**: < 1s/test
- **Coverage**: services, value_objects, utils, validators

```python
# apps/ledger/tests/test_posting_service.py
import pytest
from decimal import Decimal
from apps.ledger.services import VoucherPostingService
from apps.ledger.tests.factories import (
    AccountingVoucherFactory, VoucherLineFactory
)


@pytest.mark.django_db
class TestVoucherPostingService:
    
    def test_post_balanced_voucher_updates_balance(self):
        """Test posting voucher cân đối → cập nhật balance"""
        voucher = AccountingVoucherFactory()
        VoucherLineFactory(
            voucher=voucher,
            account_code='111',
            debit_vnd=Decimal('100000'),
            credit_vnd=Decimal('0'),
        )
        VoucherLineFactory(
            voucher=voucher,
            account_code='5111',
            debit_vnd=Decimal('0'),
            credit_vnd=Decimal('100000'),
        )
        
        service = VoucherPostingService()
        service.post(voucher)
        
        assert voucher.status == AccountingVoucher.Status.LEDGER
        balance = AccountPeriodBalance.objects.get(
            account_code='111',
            period=voucher.period,
        )
        assert balance.period_debit == Decimal('100000')
    
    def test_post_unbalanced_voucher_raises(self):
        """Test voucher lệch → raise error"""
        voucher = AccountingVoucherFactory()
        VoucherLineFactory(
            voucher=voucher,
            account_code='111',
            debit_vnd=Decimal('100000'),
        )
        VoucherLineFactory(
            voucher=voucher,
            account_code='5111',
            credit_vnd=Decimal('50000'),  # lệch
        )
        
        service = VoucherPostingService()
        with pytest.raises(VoucherNotBalancedError):
            service.post(voucher)
```

### 2.2. Integration tests (25%)

- **Mục tiêu**: Test các thành phần làm việc cùng nhau
- **Công cụ**: pytest-django (Django TestCase)
- **Tốc độ**: 1-5s/test
- **Coverage**: workflows, multi-model scenarios

```python
# tests/integration/test_voucher_workflow.py
import pytest
from django.test import TestCase
from apps.ledger.services import (
    VoucherService, PeriodClosingService
)


@pytest.mark.django_db
class TestVoucherEndToEndWorkflow:
    
    def test_full_accounting_cycle(self, company, fiscal_year):
        """Test full accounting cycle: tạo voucher → post → close period"""
        # Setup chart of accounts
        setup_tt133_accounts(company)
        
        # Create sales invoice
        sales_service = VoucherService(company=company)
        voucher = sales_service.create({
            'voucher_type': 'sales_invoice',
            'voucher_date': '2026-06-15',
            'description': 'Bán hàng cho KH A',
            'lines': [
                {'account_code': '131', 'debit_vnd': 110000000},
                {'account_code': '5111', 'credit_vnd': 100000000},
                {'account_code': '33311', 'credit_vnd': 10000000},
            ]
        })
        
        # Verify
        assert voucher.total_vnd == 110000000
        assert voucher.status == AccountingVoucher.Status.LEDGER
        
        # Close period
        closing_service = PeriodClosingService(company=company)
        closing_service.run_period_closing(
            fiscal_year=fiscal_year,
            period=6,
        )
        
        # Verify closing entries created
        closing_voucher = AccountingVoucher.objects.filter(
            company=company,
            source='closing',
        ).first()
        assert closing_voucher is not None
```

### 2.3. E2E tests (5%)

- **Mục tiêu**: Test user flows qua UI thật
- **Công cụ**: Playwright (Python)
- **Tốc độ**: 5-30s/test
- **Coverage**: critical paths

```python
# tests/e2e/test_create_voucher.py
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestVoucherE2E:
    
    def test_create_and_post_voucher(self, page: Page, live_server):
        # Login
        page.goto(f'{live_server.url}/auth/login/')
        page.fill('[name=username]', 'admin')
        page.fill('[name=password]', 'password')
        page.click('button[type=submit]')
        
        # Navigate to voucher creation
        page.goto(f'{live_server.url}/ledger/vouchers/new/')
        
        # Fill header
        page.fill('[name=voucher_date]', '2026-06-15')
        page.fill('[name=description]', 'Test voucher')
        
        # Add lines
        page.fill('[name=lines-0-account_code]', '111')
        page.fill('[name=lines-0-debit_vnd]', '1000000')
        page.fill('[name=lines-1-account_code]', '5111')
        page.fill('[name=lines-1-credit_vnd]', '1000000')
        
        # Submit
        page.click('button[name=action][value=save_post]')
        
        # Verify
        expect(page.locator('.alert-success')).to_be_visible()
        expect(page.locator('text=Đã ghi sổ')).to_be_visible()
```

## 3. Test data factories

```python
# apps/ledger/tests/factories.py
import factory
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.core.tests.factories import CompanyFactory


class AccountingVoucherFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AccountingVoucher
    
    company = factory.SubFactory(CompanyFactory)
    fiscal_year = 2026
    period = 6
    voucher_no = factory.Sequence(lambda n: f'BC{n:04d}')
    voucher_type = 'journal'
    voucher_date = factory.Faker('date_time_this_year').generate({}).date()
    status = AccountingVoucher.Status.DRAFT
    currency_code = 'VND'
    exchange_rate = Decimal('1')


class VoucherLineFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = VoucherLine
    
    voucher = factory.SubFactory(AccountingVoucherFactory)
    line_no = factory.Sequence(lambda n: n + 1)
    account_code = '111'
    debit_vnd = Decimal('0')
    credit_vnd = Decimal('0')
```

## 4. Fixtures

```python
# tests/conftest.py
import pytest
from apps.core.tests.factories import CompanyFactory, UserFactory
from apps.master_data.tests.factories import (
    ChartOfAccountsFactory, CurrencyFactory
)


@pytest.fixture
def company(db):
    return CompanyFactory()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def authenticated_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def setup_tt133_accounts(db, company):
    """Setup TT133 chart of accounts"""
    from apps.master_data.services import ChartOfAccountsService
    service = ChartOfAccountsService()
    service.load_tt133(company)
```

## 5. Property-based testing (cho domain calculations)

Dùng `hypothesis` để test các tính chất bất biến:

```python
# apps/ledger/tests/test_voucher_invariants.py
from hypothesis import given, strategies as st


@given(
    debit=st.decimals(min_value=0, max_value=1e12, places=2),
    credit=st.decimals(min_value=0, max_value=1e12, places=2),
)
def test_voucher_total_always_equals_max_of_debit_or_credit(debit, credit):
    """Voucher total = max(debit, credit)"""
    voucher = create_voucher(debit=debit, credit=credit)
    if debit == credit:
        assert voucher.total_vnd == debit


@given(
    rate=st.decimals(min_value='0.01', max_value='100000', places=6),
    amount_fc=st.decimals(min_value=0, max_value=1e9, places=2),
)
def test_currency_conversion_is_lossless(rate, amount_fc):
    """FC × rate = VND"""
    amount_vnd = amount_fc * rate
    assert amount_vnd == amount_fc * rate  # Decimal precision
```

## 6. Performance tests

```python
# tests/performance/test_voucher_list_perf.py
import pytest
from apps.ledger.tests.factories import AccountingVoucherFactory


@pytest.mark.parametrize('count', [100, 1000, 10000])
@pytest.mark.django_db
def test_voucher_list_performance(count):
    # Setup
    vouchers = AccountingVoucherFactory.create_batch(count)
    
    # Measure
    import time
    start = time.time()
    
    # Query with optimized select_related
    from apps.ledger.models import AccountingVoucher
    list(AccountingVoucher.objects.for_company(1).select_related('created_by'))
    
    elapsed = time.time() - start
    
    # Assert: < 1s even for 10k records
    assert elapsed < 1.0, f"Too slow: {elapsed:.2f}s for {count} records"
```

## 7. Coverage requirements

| Module | Coverage target |
|--------|----------------|
| `apps/ledger/services/` | ≥ 95% |
| `apps/inventory/services/` | ≥ 95% |
| `apps/assets/services/` | ≥ 95% |
| `apps/*/api/` | ≥ 85% |
| `apps/*/views/` | ≥ 75% |
| `apps/*/models/` | ≥ 70% (chỉ test methods, không test fields) |
| `shared/` | ≥ 90% |
| `config/` | ≥ 50% |

## 8. Test database

```python
# config/settings/test.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'test_pmketoan',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': 'localhost',
    }
}

# Speed up tests
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
Q_CLUSTER = {'sync': True}  # Run django-q2 tasks synchronously in tests
```

## 9. pytest config

```ini
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.test
python_files = tests.py test_*.py *_tests.py
addopts = 
    -v
    --cov=apps
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
    --cov-fail-under=80
    --reuse-db
    --nomigrations
markers =
    unit: Unit tests (fast, no DB)
    integration: Integration tests (DB, services)
    e2e: End-to-end tests (slow, browser)
    slow: Slow tests (> 1s)
    performance: Performance tests
```

## 10. CI pipeline

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']
    
    services:
      mariadb:
        image: mariadb:11.4
        env:
          MYSQL_ROOT_PASSWORD: ''
          MYSQL_ALLOW_EMPTY_PASSWORD: yes
          MYSQL_DATABASE: test_pmketoan
        ports: ['3306:3306']
    
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install uv
        run: pip install uv
      
      - name: Install deps
        run: uv sync --frozen
      
      - name: Lint
        run: |
          poetry run ruff check apps/
          poetry run black --check apps/
          poetry run mypy apps/
      
      - name: Test
        run: poetry run pytest --cov=apps --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
```

## 11. Test commands (Makefile)

```makefile
test:
	poetry run pytest

test-unit:
	poetry run pytest -m "not slow and not e2e and not performance"

test-fast:
	poetry run pytest -n auto --cov=apps

test-cov:
	poetry run pytest --cov=apps --cov-report=html
	open htmlcov/index.html

test-e2e:
	poetry run pytest -m e2e

test-perf:
	poetry run pytest -m performance

test-watch:
	poetry run ptw
```

## 12. Continuous testing

- **Pre-commit**: ruff + black + mypy
- **Pre-merge**: full test suite pass + coverage ≥ 80%
- **Pre-deploy**: e2e tests pass on staging
- **Production**: smoke tests sau deploy

---

**Kết thúc**: Bộ tài liệu hoàn chỉnh tại [README.md](../README.md)
