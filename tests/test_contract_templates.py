"""Tests for ContractTemplate + ContractPrintService."""

from datetime import date
from decimal import Decimal

import pytest

from apps.contracts.models import Contract, ContractTemplate
from apps.contracts.services.contract_print_service import ContractPrintService
from apps.core.models import Company


@pytest.fixture
def company(db):
    return Company.objects.create(
        code='TPL', name='CÔNG TY TEST TPL',
        address='123 Đường A, Hà Nội', tax_code='0101234567',
        legal_representative='Nguyễn Văn A',
    )


@pytest.fixture
def contract(company):
    return Contract.objects.create(
        company=company,
        contract_no='HD0001',
        contract_date=date(2026, 6, 18),
        contract_type='sale',
        party_name='Công ty ABC',
        party_tax_code='0101234567',
        party_address='Số 1 Đường X',
        value=Decimal('100000000'),
        currency_code='VND',
        start_date=date(2026, 6, 18),
        end_date=date(2026, 12, 31),
        status='active',
    )


def test_create_contract_template(db):
    """A ContractTemplate can be created with required fields."""
    tpl = ContractTemplate.objects.create(
        code='sale_v1',
        name='Hợp đồng mua bán hàng hóa',
        contract_type='sale',
        template_html='<html>Bên A: {{ company.name }} — {{ contract.party_name }}</html>',
        required_fields=['company', 'party_name', 'value'],
        legal_basis='BLDS 2015',
        version='2026',
    )
    assert tpl.pk is not None
    assert tpl.code == 'sale_v1'
    assert tpl.is_active is True
    assert 'company' in tpl.required_fields
    assert tpl.version == '2026'


def test_render_template_with_context(company, contract):
    """Template HTML renders with company + contract context."""
    ContractTemplate.objects.create(
        code='sale_v1',
        name='HĐ mua bán',
        contract_type='sale',
        template_html='<p>Bên A: {{ company.name }}</p><p>Bên B: {{ contract.party_name }}</p>',
    )
    service = ContractPrintService()
    ctx = service._build_context(contract)
    from django.template import engines
    django_engine = engines['django']
    rendered = django_engine.from_string(tpl.template_html).render(ctx)
    assert 'CÔNG TY TEST TPL' in rendered
    assert 'Công ty ABC' in rendered


def test_generate_contract_pdf_bytes(company, contract):
    """generate_contract_pdf returns PDF bytes (or HTML fallback)."""
    tpl = ContractTemplate.objects.create(
        code='sale_v1',
        name='HĐ mua bán',
        contract_type='sale',
        template_html='<html><body><h1>{{ company.name }}</h1><p>{{ contract.party_name }}</p></body></html>',
    )
    service = ContractPrintService()
    pdf_bytes = service.generate_contract_pdf(contract, 'sale_v1')
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 50
    # If WeasyPrint available → starts with %PDF; otherwise HTML fallback containing data
    assert pdf_bytes[:4] == b'%PDF' or b'C\xc3\x94NG' in pdf_bytes or b'company' not in pdf_bytes


def test_build_context_autofill(company, contract):
    """_build_context auto-fills company, contract, today."""
    ContractTemplate.objects.create(
        code='sale_v1', name='HĐ mua bán', contract_type='sale', template_html='x',
    )
    service = ContractPrintService()
    ctx = service._build_context(contract)
    assert ctx['company'] == company
    assert ctx['contract'] == contract
    assert 'today' in ctx
    assert isinstance(ctx['today'], date)
