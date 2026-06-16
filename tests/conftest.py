import pytest
from apps.core.models import Company


@pytest.fixture
def company(db):
    return Company.objects.create(
        code='TEST',
        name='Test Company',
        tax_code='0101234567',
        accounting_regime='tt133',
    )
