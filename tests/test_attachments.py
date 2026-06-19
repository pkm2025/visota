"""Tests for the universal attachment system."""

from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.models import Company
from apps.documents.models.attachment import Attachment
from apps.documents.services.attachment_service import AttachmentService
from apps.master_data.models import Product
from apps.projects.models import Project


@pytest.fixture
def company(db):
    return Company.objects.create(code="TCO", name="Test")


def _make_product(company, code="SP001", name="Test Product", ptype="service"):
    return Product.objects.create(
        company=company,
        code=code,
        name=name,
        product_type=ptype,
        unit_id="Goi" if ptype == "service" else "CAI",
        gl_account_inv="" if ptype == "service" else "156",
        gl_account_cogs="642" if ptype == "service" else "632",
        gl_account_revenue="5112" if ptype == "service" else "5111",
    )


def test_attach_to_product(company):
    product = _make_product(company)
    fake = SimpleUploadedFile("spec.pdf", b"%PDF spec", content_type="application/pdf")
    att = AttachmentService.attach(product, "Spec Sheet", fake, "specification")
    assert att.pk is not None
    assert att.content_type.model == "product"
    assert att.object_id == product.pk
    assert att.file_size > 0
    assert att.file_type == "pdf"
    # Company auto-detected from product
    assert att.company_id == company.pk


def test_attach_to_project(company):
    project = Project.objects.create(
        company=company,
        code="PRJ001",
        name="Test Project",
        start_date=date(2026, 1, 1),
    )
    fake = SimpleUploadedFile(
        "report.docx", b"PK report", content_type="application/vnd.openxmlformats"
    )
    att = AttachmentService.attach(project, "Final Report", fake, "report")
    assert att.content_type.model == "project"
    assert att.object_id == project.pk
    assert att.company_id == company.pk


def test_get_attachments_for_object(company):
    product = _make_product(company, ptype="goods")
    for i in range(3):
        fake = SimpleUploadedFile(f"file{i}.pdf", b"%PDF", content_type="application/pdf")
        AttachmentService.attach(product, f"File {i}", fake, "other")
    atts = AttachmentService.get_for_object(product)
    assert atts.count() == 3


def test_attachment_types(db):
    """Multiple attachment types on the same object."""
    company = Company.objects.create(code="TCO2", name="T")
    product = _make_product(company, code="SP002", name="Service")
    AttachmentService.attach(
        product,
        "Spec",
        SimpleUploadedFile("s.pdf", b"%PDF", content_type="application/pdf"),
        "specification",
    )
    AttachmentService.attach(
        product,
        "Cert",
        SimpleUploadedFile("c.jpg", b"JFIF", content_type="image/jpeg"),
        "certificate",
    )
    AttachmentService.attach(
        product,
        "SLA",
        SimpleUploadedFile("sla.pdf", b"%PDF", content_type="application/pdf"),
        "sla",
    )

    all_atts = AttachmentService.get_for_object(product)
    assert all_atts.count() == 3

    certs = AttachmentService.get_by_type(product, "certificate")
    assert certs.count() == 1
    assert certs.first().title == "Cert"


def test_attachment_auto_detects_file_type(company):
    product = _make_product(company, code="SP003", name="T", ptype="goods")
    fake = SimpleUploadedFile("photo.png", b"\x89PNG", content_type="image/png")
    att = AttachmentService.attach(product, "Photo", fake, "photo")
    assert att.file_type == "png"
    assert att.file_size > 0


def test_attachment_isolates_by_object(company):
    """Attachments for one object don't leak into another."""
    p1 = _make_product(company, code="A001", name="A")
    p2 = _make_product(company, code="B001", name="B")
    fake = SimpleUploadedFile("x.pdf", b"%PDF", content_type="application/pdf")
    AttachmentService.attach(p1, "P1 doc", fake, "report")
    assert AttachmentService.get_for_object(p1).count() == 1
    assert AttachmentService.get_for_object(p2).count() == 0


def test_attachment_choices_present():
    """All expected attachment types are present."""
    types = {c[0] for c in Attachment.AttachmentType.choices}
    expected = {
        "specification",
        "contract_scan",
        "proposal",
        "report",
        "certificate",
        "photo",
        "deliverable",
        "sla",
        "invoice_scan",
        "receipt",
        "other",
    }
    assert expected.issubset(types)
