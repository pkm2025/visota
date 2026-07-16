"""Tests for Company.industry field (VAL-COMP-005).

Verifies:
- Company model has industry field (CharField, max_length=200, blank=True)
- seed_dogfood sets industry per dogfood company:
    DF-SG: Thương mại - Công nghệ
    DF-HN: Thương mại - Điện tử
    DF-AB: Dịch vụ - bán lẻ
- Industry field defaults to empty string
"""

from io import StringIO

from django.core.management import call_command

from apps.core.models import Company


def test_company_has_industry_field(db):
    """Company model has an 'industry' CharField with max_length=200 and blank=True."""
    field = Company._meta.get_field("industry")
    assert field is not None
    assert field.max_length == 200
    assert field.blank is True


def test_company_industry_defaults_to_empty_string(db):
    """New Company instances get industry='' by default."""
    company = Company.objects.create(
        code="TEST-IND",
        name="Test Industry Co",
    )
    assert company.industry == ""


def test_company_industry_can_be_set(db):
    """Industry field can be set and retrieved."""
    company = Company.objects.create(
        code="TEST-IND2",
        name="Test Industry Co 2",
        industry="Thương mại",
    )
    company.refresh_from_db()
    assert company.industry == "Thương mại"


def test_seed_dogfood_sets_industry_per_company(db):
    """seed_dogfood command sets the correct industry for each dogfood company.

    DF-SG: Thương mại - Công nghệ
    DF-HN: Thương mại - Điện tử
    DF-AB: Dịch vụ - bán lẻ
    """
    out = StringIO()
    call_command("seed_dogfood", stdout=out)

    sg = Company.objects.get(code="DF-SG")
    hn = Company.objects.get(code="DF-HN")
    ab = Company.objects.get(code="DF-AB")

    assert sg.industry == "Thương mại - Công nghệ"
    assert hn.industry == "Thương mại - Điện tử"
    assert ab.industry == "Dịch vụ - bán lẻ"


def test_seed_dogfood_industry_idempotent(db):
    """Running seed_dogfood twice preserves the industry values."""
    out = StringIO()
    call_command("seed_dogfood", stdout=out)
    call_command("seed_dogfood", stdout=out)

    sg = Company.objects.get(code="DF-SG")
    hn = Company.objects.get(code="DF-HN")
    ab = Company.objects.get(code="DF-AB")

    assert sg.industry == "Thương mại - Công nghệ"
    assert hn.industry == "Thương mại - Điện tử"
    assert ab.industry == "Dịch vụ - bán lẻ"
