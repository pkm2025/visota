"""Tests for the WikiPage model (Karpathy LLM Wiki pattern, Layer 2).

Covers model creation, field defaults, page_type choices, M2M relationships
(source_refs to PKMDocument, linked_pages self-M2M, tags to Tag), the
``is_ai_generated`` / ``is_system`` boolean flags, ``last_ingest_at``
timestamp, unique constraint on (user, company, title), and multi-tenant
(user/company) isolation.

Fulfills VAL-WIKI-001: WikiPage model exists with correct fields, inherits
CompanyOwnedModel.
"""

import pytest
from django.db import IntegrityError

from apps.core.managers import CompanyOwnedModel
from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import KnowledgeNote, PKMDocument, Tag, WikiPage

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="WIKI_TEST", name="Wiki Test Co")


@pytest.fixture
def user(db, company):
    return User.objects.create_user(
        username="wiki_user", password="Test1234", email="wiki@t.co"
    )


@pytest.fixture
def other_user(db, company):
    return User.objects.create_user(
        username="wiki_other", password="Test1234", email="wother@t.co"
    )


@pytest.fixture
def other_company(db):
    return Company.objects.create(code="WIKI_OTHER", name="Wiki Other Co")


@pytest.fixture
def wiki_page(db, user, company):
    """A minimal WikiPage for relationship tests."""
    return WikiPage.objects.create(
        user=user,
        company=company,
        title="VAT Overview",
        content="# VAT Overview\n\nVietnam VAT basics.",
        page_type=WikiPage.PageType.CONCEPT,
    )


# ---------------------------------------------------------------------------
# Model inheritance / structural checks (VAL-WIKI-001)
# ---------------------------------------------------------------------------


def test_wiki_page_extends_company_owned_model():
    """WikiPage must extend CompanyOwnedModel for multi-tenant isolation."""
    assert issubclass(WikiPage, CompanyOwnedModel)


def test_wiki_page_has_required_fields():
    """WikiPage must declare all required fields (VAL-WIKI-001)."""
    field_names = {f.name for f in WikiPage._meta.get_fields()}
    required = {
        "title",
        "content",
        "page_type",
        "source_refs",
        "linked_pages",
        "tags",
        "is_ai_generated",
        "is_system",
        "last_ingest_at",
        "user",
        "company",
    }
    missing = required - field_names
    assert not missing, f"WikiPage missing fields: {missing}"


# ---------------------------------------------------------------------------
# Creation and defaults
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wiki_page_creation(user, company):
    """WikiPage can be created with all required fields."""
    page = WikiPage.objects.create(
        user=user,
        company=company,
        title="PIT Summary",
        content="## Personal Income Tax\n\nProgressive rates apply.",
        page_type=WikiPage.PageType.SUMMARY,
    )
    assert page.pk is not None
    assert page.user == user
    assert page.company == company
    assert page.title == "PIT Summary"
    assert "Personal Income Tax" in page.content
    assert page.page_type == WikiPage.PageType.SUMMARY
    assert page.created_at is not None
    assert page.updated_at is not None


@pytest.mark.django_db
def test_wiki_page_content_default_blank(user, company):
    """content defaults to empty string when not provided."""
    page = WikiPage.objects.create(
        user=user, company=company, title="Empty", page_type=WikiPage.PageType.CONCEPT
    )
    assert page.content == ""


@pytest.mark.django_db
def test_wiki_page_is_ai_generated_default_false(user, company):
    """is_ai_generated defaults to False (human-authored unless flagged)."""
    page = WikiPage.objects.create(
        user=user,
        company=company,
        title="Manual",
        content="handwritten",
        page_type=WikiPage.PageType.CONCEPT,
    )
    assert page.is_ai_generated is False


@pytest.mark.django_db
def test_wiki_page_is_ai_generated_true(user, company):
    """is_ai_generated can be set to True for AI-authored pages."""
    page = WikiPage.objects.create(
        user=user,
        company=company,
        title="AI Notes",
        content="synthesised",
        page_type=WikiPage.PageType.SYNTHESIS,
        is_ai_generated=True,
    )
    assert page.is_ai_generated is True


@pytest.mark.django_db
def test_wiki_page_is_system_default_false(user, company):
    """is_system defaults to False."""
    page = WikiPage.objects.create(
        user=user, company=company, title="User Page", page_type=WikiPage.PageType.CONCEPT
    )
    assert page.is_system is False


@pytest.mark.django_db
def test_wiki_page_is_system_true(user, company):
    """is_system can be set True for shared cross-tenant pages."""
    page = WikiPage.objects.create(
        user=user,
        company=company,
        title="System Reg",
        content="regulation",
        page_type=WikiPage.PageType.OVERVIEW,
        is_system=True,
    )
    assert page.is_system is True


@pytest.mark.django_db
def test_wiki_page_last_ingest_at_nullable(user, company):
    """last_ingest_at is nullable and defaults to None until first ingest."""
    page = WikiPage.objects.create(
        user=user, company=company, title="No Ingest", page_type=WikiPage.PageType.CONCEPT
    )
    assert page.last_ingest_at is None


@pytest.mark.django_db
def test_wiki_page_last_ingest_at_set(user, company):
    """last_ingest_at can be recorded when an ingest runs."""
    from django.utils import timezone

    now = timezone.now()
    page = WikiPage.objects.create(
        user=user,
        company=company,
        title="Ingested",
        content="after ingest",
        page_type=WikiPage.PageType.SUMMARY,
        last_ingest_at=now,
    )
    assert page.last_ingest_at == now


# ---------------------------------------------------------------------------
# page_type choices
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wiki_page_page_type_all_choices(user, company):
    """All five page_type choices can be stored."""
    choices = [
        WikiPage.PageType.SUMMARY,
        WikiPage.PageType.CONCEPT,
        WikiPage.PageType.ENTITY,
        WikiPage.PageType.OVERVIEW,
        WikiPage.PageType.SYNTHESIS,
    ]
    for idx, ptype in enumerate(choices):
        page = WikiPage.objects.create(
            user=user,
            company=company,
            title=f"Page {idx}",
            page_type=ptype,
        )
        assert page.page_type == ptype


@pytest.mark.django_db
def test_wiki_page_page_type_default_summary(user, company):
    """page_type defaults to SUMMARY when not provided."""
    page = WikiPage.objects.create(user=user, company=company, title="Default Type")
    assert page.page_type == WikiPage.PageType.SUMMARY


# ---------------------------------------------------------------------------
# M2M: source_refs (PKMDocument)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wiki_page_source_refs_m2m(user, company, wiki_page):
    """WikiPage can reference multiple PKMDocuments via source_refs."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    doc1 = PKMDocument.objects.create(
        user=user,
        company=company,
        title="Doc 1",
        file=SimpleUploadedFile("a.pdf", b"data"),
        file_type="pdf",
    )
    doc2 = PKMDocument.objects.create(
        user=user,
        company=company,
        title="Doc 2",
        file=SimpleUploadedFile("b.pdf", b"data"),
        file_type="pdf",
    )
    wiki_page.source_refs.add(doc1, doc2)
    assert wiki_page.source_refs.count() == 2
    assert doc1 in wiki_page.source_refs.all()
    assert doc2 in wiki_page.source_refs.all()


@pytest.mark.django_db
def test_wiki_page_source_refs_optional(user, company, wiki_page):
    """source_refs can be empty (a concept page may have no direct source)."""
    assert wiki_page.source_refs.count() == 0


# ---------------------------------------------------------------------------
# M2M: linked_pages (self-referential)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wiki_page_linked_pages_self_m2m(user, company, wiki_page):
    """WikiPage can cross-reference other WikiPages via linked_pages."""
    other = WikiPage.objects.create(
        user=user,
        company=company,
        title="Related Concept",
        content="linked",
        page_type=WikiPage.PageType.CONCEPT,
    )
    wiki_page.linked_pages.add(other)
    assert other in wiki_page.linked_pages.all()
    # symmetrical by default -> bidirectional link
    assert wiki_page in other.linked_pages.all()


@pytest.mark.django_db
def test_wiki_page_linked_pages_can_be_empty(user, company, wiki_page):
    """A page with no cross-references works."""
    assert wiki_page.linked_pages.count() == 0


# ---------------------------------------------------------------------------
# M2M: tags (Tag)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wiki_page_tags_m2m(user, company, wiki_page):
    """WikiPage can be tagged via M2M to Tag."""
    t1 = Tag.objects.create(user=user, company=company, name="vat")
    t2 = Tag.objects.create(user=user, company=company, name="tax")
    wiki_page.tags.add(t1, t2)
    assert wiki_page.tags.count() == 2
    assert t1 in wiki_page.tags.all()


@pytest.mark.django_db
def test_wiki_page_tags_can_be_empty(user, company, wiki_page):
    """A page with no tags works."""
    assert wiki_page.tags.count() == 0


# ---------------------------------------------------------------------------
# Unique constraint on (user, company, title)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wiki_page_unique_user_company_title(user, company):
    """Unique constraint on (user, company, title) prevents duplicates."""
    WikiPage.objects.create(
        user=user, company=company, title="Unique Title", page_type=WikiPage.PageType.CONCEPT
    )
    with pytest.raises(IntegrityError):
        WikiPage.objects.create(
            user=user,
            company=company,
            title="Unique Title",
            page_type=WikiPage.PageType.SUMMARY,
        )


@pytest.mark.django_db
def test_wiki_page_same_title_different_user(company, user, other_user):
    """Different users can have pages with the same title."""
    p1 = WikiPage.objects.create(
        user=user, company=company, title="Shared", page_type=WikiPage.PageType.CONCEPT
    )
    p2 = WikiPage.objects.create(
        user=other_user, company=company, title="Shared", page_type=WikiPage.PageType.CONCEPT
    )
    assert p1.pk != p2.pk


@pytest.mark.django_db
def test_wiki_page_same_title_different_company(user, company, other_company):
    """Same user in different companies can have pages with the same title."""
    p1 = WikiPage.objects.create(
        user=user, company=company, title="Cross Co", page_type=WikiPage.PageType.CONCEPT
    )
    p2 = WikiPage.objects.create(
        user=user,
        company=other_company,
        title="Cross Co",
        page_type=WikiPage.PageType.CONCEPT,
    )
    assert p1.pk != p2.pk


# ---------------------------------------------------------------------------
# Multi-tenant scoping (user + company isolation)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wiki_page_user_isolation(company, user, other_user):
    """Wiki pages are private per user."""
    WikiPage.objects.create(
        user=user, company=company, title="User A Page", page_type=WikiPage.PageType.CONCEPT
    )
    assert WikiPage.objects.filter(user=other_user, company=company).count() == 0


@pytest.mark.django_db
def test_wiki_page_company_isolation(user, company, other_company):
    """Wiki pages are isolated by company."""
    WikiPage.objects.create(
        user=user, company=company, title="Co A Page", page_type=WikiPage.PageType.CONCEPT
    )
    assert WikiPage.objects.filter(user=user, company=other_company).count() == 0


@pytest.mark.django_db
def test_wiki_page_for_company_queryset(company, other_company, user):
    """Wiki pages can be scoped to a single tenant via company filter."""
    WikiPage.objects.create(
        user=user, company=company, title="A", page_type=WikiPage.PageType.CONCEPT
    )
    WikiPage.objects.create(
        user=user, company=other_company, title="B", page_type=WikiPage.PageType.CONCEPT
    )
    assert WikiPage.objects.filter(company=company).count() == 1
    assert WikiPage.objects.filter(company=other_company).count() == 1


# ---------------------------------------------------------------------------
# Cascade deletes
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wiki_page_cascade_delete_user(user, company):
    """Deleting a user cascades to their wiki pages."""
    user_id = user.id
    WikiPage.objects.create(
        user=user, company=company, title="Goes With User", page_type=WikiPage.PageType.CONCEPT
    )
    assert WikiPage.objects.filter(user_id=user_id).count() == 1
    user.delete()
    assert WikiPage.objects.filter(user_id=user_id).count() == 0


@pytest.mark.django_db
def test_wiki_page_cascade_delete_company(user, company):
    """Deleting a company cascades to its wiki pages."""
    company_id = company.id
    WikiPage.objects.create(
        user=user, company=company, title="Goes With Co", page_type=WikiPage.PageType.CONCEPT
    )
    assert WikiPage.objects.filter(company_id=company_id).count() == 1
    company.delete()
    assert WikiPage.objects.filter(company_id=company_id).count() == 0


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wiki_page_str_representation(user, company):
    """WikiPage __str__ returns a meaningful representation."""
    page = WikiPage.objects.create(
        user=user, company=company, title="My Wiki Title", page_type=WikiPage.PageType.CONCEPT
    )
    assert "My Wiki Title" in str(page)


@pytest.mark.django_db
def test_wiki_page_db_table():
    """WikiPage uses the expected db_table."""
    assert WikiPage._meta.db_table == "pkm_wiki_page"


@pytest.mark.django_db
def test_wiki_page_updated_at_changes(user, company, wiki_page):
    """updated_at is refreshed on save."""
    original = wiki_page.updated_at
    wiki_page.title = "Renamed"
    wiki_page.save()
    wiki_page.refresh_from_db()
    assert wiki_page.updated_at >= original


# Keep KnowledgeNote import used to avoid flake8 unused warnings in CI lint
_ = KnowledgeNote
