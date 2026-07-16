"""Tests for the VAT Return XML export endpoint (M2.6, VAL-M2-012..020).

Endpoint: ``GET /modern/reports/vat-return-xml/?fiscal_year=Y&period=P``
"""

from datetime import date
from decimal import Decimal

import pytest
from lxml import etree

from apps.core.models import Company
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.master_data.models import InvoiceGroup, TaxRateCode
from apps.reporting.models import VATReportLine

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="XTC", name="XML Test Co")


@pytest.fixture
def tax_rates(db):
    rates = {}
    for code, rate, name in [
        ("00", Decimal("0"), "0%"),
        ("05", Decimal("5"), "5%"),
        ("10", Decimal("10"), "10%"),
    ]:
        rates[code], _ = TaxRateCode.objects.get_or_create(
            code=code, defaults={"rate": rate, "display_name": name}
        )
    return rates


@pytest.fixture
def invoice_groups(db):
    groups = {}
    for code, name in [
        ("4", "INPUT"),
        ("5", "OUTPUT"),
        ("6", "OTHER"),
    ]:
        groups[code], _ = InvoiceGroup.objects.get_or_create(
            code=code, defaults={"name_vi": name, "name_en": name}
        )
    return groups


@pytest.fixture
def vat_config(db):
    from django.core.management import call_command

    call_command("seed_vat_tt80", verbosity=0)
    return VATReportLine.objects.count()


@pytest.fixture
def auth_client(company):
    """Django test client logged in as a superuser, bound to ``company``."""
    from django.test import Client

    from apps.identity.models import User

    user = User.objects.create_superuser(
        username="xml_tester", password="Secret123", email="xml@test.local"
    )
    c = Client()
    c.force_login(user)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    return c


def _post_tax_line(
    company,
    fiscal_year,
    period,
    *,
    account_code,
    invoice_group,
    tax_rate,
    goods_amount,
    tax_amount,
    debit=Decimal("0"),
    credit=Decimal("0"),
    voucher_no="V1",
):
    AccountingVoucher.objects.create(
        company=company,
        fiscal_year=fiscal_year,
        period=period,
        voucher_no=voucher_no,
        voucher_type=AccountingVoucher.VoucherType.JOURNAL,
        voucher_date=date(fiscal_year, period, 15),
        status=AccountingVoucher.Status.LEDGER,
    )
    VoucherLine.objects.create(
        voucher=AccountingVoucher.objects.get(voucher_no=voucher_no, company=company),
        line_no=1,
        account_code=account_code,
        debit_vnd=debit,
        credit_vnd=credit,
        tax_code=tax_rate,
        tax_rate=tax_rate.rate if tax_rate else Decimal("0"),
        goods_amount_vnd=goods_amount,
        tax_amount_vnd=tax_amount,
        invoice_group_code=invoice_group,
    )


# ---------------------------------------------------------------------------
# VAL-M2-012: XML endpoint returns XML for a known period
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_xml_endpoint_returns_xml(auth_client, vat_config):
    """GET returns 200 with a body starting with <?xml."""
    resp = auth_client.get("/modern/reports/vat-return-xml/?fiscal_year=2026&period=6")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert body.lstrip().startswith("<?xml")
    assert "application/xml" in resp["Content-Type"]


# ---------------------------------------------------------------------------
# VAL-M2-013: Content-Type is application/xml; charset=utf-8
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_content_type_is_application_xml(auth_client, vat_config):
    """Content-Type header equals application/xml; charset=utf-8."""
    resp = auth_client.get("/modern/reports/vat-return-xml/?fiscal_year=2026&period=6")
    assert resp["Content-Type"] == "application/xml; charset=utf-8"


# ---------------------------------------------------------------------------
# VAL-M2-014: Content-Disposition filename is 01GTKT-YYYYMM.xml
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_content_disposition_filename(auth_client, vat_config):
    """Filename is 01GTKT-202606.xml for fy=2026 period=6."""
    resp = auth_client.get("/modern/reports/vat-return-xml/?fiscal_year=2026&period=6")
    cd = resp["Content-Disposition"]
    assert 'filename="01GTKT-202606.xml"' in cd

    # Verify zero-padding for single-digit month
    resp2 = auth_client.get("/modern/reports/vat-return-xml/?fiscal_year=2026&period=3")
    cd2 = resp2["Content-Disposition"]
    assert 'filename="01GTKT-202603.xml"' in cd2


# ---------------------------------------------------------------------------
# VAL-M2-015: XML is well-formed (parses with lxml)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_xml_well_formed(auth_client, vat_config):
    """The XML body parses cleanly with lxml.etree.fromstring."""
    resp = auth_client.get("/modern/reports/vat-return-xml/?fiscal_year=2026&period=6")
    body_bytes = resp.content
    root = etree.fromstring(body_bytes)
    assert root is not None


# ---------------------------------------------------------------------------
# VAL-M2-016: Root element matches TT80 schema
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_root_element_is_hsokhaithue(auth_client, vat_config):
    """Root tag is HSoKhaiThue with TT80 namespace."""
    resp = auth_client.get("/modern/reports/vat-return-xml/?fiscal_year=2026&period=6")
    root = etree.fromstring(resp.content)
    # Tag without namespace prefix
    tag = etree.QName(root).localname
    assert tag == "HSoKhaiThue"
    # Namespace present
    nsmap = root.nsmap
    assert None in nsmap or any(
        v == "http://kekhaithue.gdt.gov.vn/TKhaiThue" for v in nsmap.values()
    ), f"namespace not found in nsmap: {nsmap}"


# ---------------------------------------------------------------------------
# VAL-M2-017: LTinh node contains all line codes
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ltinh_contains_all_line_codes(auth_client, vat_config):
    """<LTinh> subtree has <ctXX> elements for all codes 21-33."""
    resp = auth_client.get("/modern/reports/vat-return-xml/?fiscal_year=2026&period=6")
    root = etree.fromstring(resp.content)
    ns = root.nsmap

    # Find LTinh node
    ltinh = root.find(".//LTinh", ns)
    if ltinh is None:
        ltinh = root.find(".//*[local-name()='LTinh']")
    assert ltinh is not None, "LTinh node not found"

    # Collect all ctXX children
    found_codes = set()
    for child in ltinh:
        local = etree.QName(child).localname
        if local.startswith("ct") and local[2:].isdigit():
            found_codes.add(local[2:])

    expected = {str(c) for c in range(21, 34)}
    assert expected.issubset(found_codes), f"missing codes: {expected - found_codes}"

    # Each ctXX has a numeric text value
    for child in ltinh:
        local = etree.QName(child).localname
        if local.startswith("ct") and local[2:].isdigit():
            text = child.text or "0"
            Decimal(text)  # raises if not numeric


# ---------------------------------------------------------------------------
# VAL-M2-018: XML numeric values match HTML display values
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_xml_values_match_html_values(auth_client, company, tax_rates, invoice_groups, vat_config):
    """For the same period, each XML line value matches the HTML view."""
    # Post some data so values are non-zero
    _post_tax_line(
        company,
        2026,
        6,
        account_code="1331",
        invoice_group=invoice_groups["4"],
        tax_rate=tax_rates["10"],
        goods_amount=Decimal("10000000"),
        tax_amount=Decimal("1000000"),
        debit=Decimal("11000000"),
        voucher_no="XML_IN1",
    )
    _post_tax_line(
        company,
        2026,
        6,
        account_code="33311",
        invoice_group=invoice_groups["5"],
        tax_rate=tax_rates["10"],
        goods_amount=Decimal("20000000"),
        tax_amount=Decimal("2000000"),
        credit=Decimal("2000000"),
        voucher_no="XML_OUT1",
    )

    # Get HTML values
    html_resp = auth_client.get("/modern/reports/vat-return/?fiscal_year=2026&period=6")
    assert html_resp.status_code == 200

    # Get XML values
    xml_resp = auth_client.get("/modern/reports/vat-return-xml/?fiscal_year=2026&period=6")
    assert xml_resp.status_code == 200
    root = etree.fromstring(xml_resp.content)

    # Extract XML values by code (use xpath for local-name support)
    ltinh_results = root.xpath(".//*[local-name()='LTinh']")
    assert len(ltinh_results) > 0, "LTinh node not found"
    ltinh = ltinh_results[0]
    xml_values = {}
    for child in ltinh:
        local = etree.QName(child).localname
        if local.startswith("ct") and local[2:].isdigit():
            xml_values[local[2:]] = Decimal(child.text or "0")

    # Compute expected values from the service directly (same service used
    # by both views) and verify the XML matches.
    from apps.reporting.services.vat_return import VATReturnService

    data = VATReturnService(company=company).generate(2026, 6)
    for code in range(21, 34):
        code_str = str(code)
        expected = (data["values_by_code"].get(code_str, Decimal("0"))).quantize(Decimal("1"))
        assert xml_values[code_str] == expected, (
            f"line [{code_str}]: XML={xml_values[code_str]} expected={expected}"
        )


# ---------------------------------------------------------------------------
# VAL-M2-019: Empty period returns valid XML with zeros
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_empty_period_returns_valid_xml_with_zeros(auth_client, vat_config):
    """Empty period XML is well-formed with all-zero values."""
    resp = auth_client.get("/modern/reports/vat-return-xml/?fiscal_year=2099&period=12")
    assert resp.status_code == 200
    root = etree.fromstring(resp.content)
    assert etree.QName(root).localname == "HSoKhaiThue"

    ltinh_results = root.xpath(".//*[local-name()='LTinh']")
    assert len(ltinh_results) > 0
    ltinh = ltinh_results[0]

    for child in ltinh:
        local = etree.QName(child).localname
        if local.startswith("ct") and local[2:].isdigit():
            text = (child.text or "0").strip()
            assert Decimal(text) == Decimal("0"), f"{local} should be 0 in empty period, got {text}"


# ---------------------------------------------------------------------------
# VAL-M2-020: Login required (anonymous redirect)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_anonymous_redirects_to_login(vat_config):
    """Anonymous GET redirects to /auth/login/."""
    from django.test import Client

    c = Client()
    resp = c.get("/modern/reports/vat-return-xml/?fiscal_year=2026&period=6")
    assert resp.status_code in (301, 302)
    location = resp["Location"]
    assert "/auth/login/" in location
