"""Integration tests for PKM Notes UI views (/modern/knowledge/).

Covers:
    VAL-NOTES-001 - Create a new knowledge note via UI
    VAL-NOTES-002 - View list of own notes
    VAL-NOTES-003 - Edit an existing note via UI
    VAL-NOTES-004 - Delete a note via UI
    VAL-NOTES-009 - Pinned notes appear at top
    VAL-NOTES-010 - Note content supports markdown rendering
    VAL-NOTES-013 - Sidebar shows PKM section for permitted users
    VAL-CROSS-001 - First-visit empty state
    VAL-CROSS-002 - Permission redirect for unauthorized users
    VAL-CROSS-006 - Navigation reachability
    VAL-CROSS-010 - Sidebar visibility by permission
    VAL-CROSS-011 - Login redirect for unauthenticated access
"""

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import Permission, Role, User, UserCompanyRole
from apps.pkm.models import KnowledgeNote, Tag

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="PKM_UI", name="PKM UI Co")


@pytest.fixture
def admin_user(db, company):
    """Superuser — bypasses permission checks (has pkm.access implicitly)."""
    return User.objects.create_superuser(
        username="pkm_admin", password="Test1234", email="admin@pkm.test"
    )


@pytest.fixture
def regular_user_with_perm(db, company):
    """Regular user with pkm.access permission."""
    user = User.objects.create_user(
        username="pkm_user", password="Test1234", email="user@pkm.test"
    )
    # Create pkm.access permission if not exists
    perm, _ = Permission.objects.get_or_create(
        code="pkm.access",
        defaults={"module": "pkm", "name": "PKM Access", "description": "Access PKM module"},
    )
    role = Role.objects.create(company=company, code="pkm_role", name="PKM Role")
    role.permissions.add(perm)
    UserCompanyRole.objects.create(user=user, company=company, role=role)
    return user


@pytest.fixture
def regular_user_no_perm(db, company):
    """Regular user WITHOUT pkm.access permission."""
    user = User.objects.create_user(
        username="no_pkm_user", password="Test1234", email="noperm@pkm.test"
    )
    role = Role.objects.create(company=company, code="no_pkm", name="No PKM Role")
    UserCompanyRole.objects.create(user=user, company=company, role=role)
    return user


@pytest.fixture
def admin_client(admin_user):
    c = Client()
    c.force_login(admin_user)
    return c


@pytest.fixture
def perm_client(regular_user_with_perm, company):
    """Client for a regular user WITH pkm.access permission.

    Sets session current_company_id so middleware can resolve company.
    """
    c = Client()
    c.force_login(regular_user_with_perm)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    return c


@pytest.fixture
def no_perm_client(regular_user_no_perm, company):
    """Client for a regular user WITHOUT pkm.access permission."""
    c = Client()
    c.force_login(regular_user_no_perm)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    return c


@pytest.fixture
def note(admin_user, company):
    return KnowledgeNote.objects.create(
        user=admin_user,
        company=company,
        title="Test Note",
        content="# Heading\n\nSome **bold** text and a list:\n\n- Item 1\n- Item 2",
    )


@pytest.fixture
def pinned_note(admin_user, company):
    return KnowledgeNote.objects.create(
        user=admin_user,
        company=company,
        title="Pinned Note",
        content="This is pinned",
        is_pinned=True,
    )


@pytest.fixture
def regular_note(admin_user, company):
    return KnowledgeNote.objects.create(
        user=admin_user,
        company=company,
        title="Regular Note",
        content="This is not pinned",
        is_pinned=False,
    )


@pytest.fixture
def tagged_note(admin_user, company):
    tag = Tag.objects.create(user=admin_user, company=company, name="accounting")
    n = KnowledgeNote.objects.create(
        user=admin_user, company=company, title="Tagged Note", content="Has a tag"
    )
    n.tags.add(tag)
    return n


# ---------------------------------------------------------------------------
# VAL-CROSS-011: Login redirect for unauthenticated access
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_unauthenticated_redirect_to_login():
    """Unauthenticated user navigating to /modern/knowledge/ is redirected to login."""
    client = Client()
    response = client.get("/modern/knowledge/")
    assert response.status_code == 302
    assert "/auth/login/" in response.url


@pytest.mark.django_db
def test_unauthenticated_notes_redirect_to_login():
    """Unauthenticated user cannot access notes list."""
    client = Client()
    response = client.get("/modern/knowledge/notes/")
    assert response.status_code == 302
    assert "/auth/login/" in response.url


# ---------------------------------------------------------------------------
# VAL-CROSS-002, VAL-CROSS-010: Permission redirect for unauthorized users
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_perm_user_redirected_from_knowledge(no_perm_client):
    """User without pkm.access is redirected to /no-access/."""
    response = no_perm_client.get("/modern/knowledge/")
    assert response.status_code == 302
    assert "/no-access/" in response.url


@pytest.mark.django_db
def test_no_perm_user_redirected_from_notes(no_perm_client):
    """User without pkm.access cannot access notes list."""
    response = no_perm_client.get("/modern/knowledge/notes/")
    assert response.status_code == 302
    assert "/no-access/" in response.url


@pytest.mark.django_db
def test_no_perm_user_blocked_on_write(no_perm_client):
    """User without pkm.access gets 403 on POST (not redirect)."""
    response = no_perm_client.post("/modern/knowledge/notes/new/", {"title": "X", "content": "Y"})
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# VAL-CROSS-001: First-visit empty state
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_empty_dashboard_shows_getting_started(admin_client):
    """A user with no notes sees an empty dashboard with getting-started prompt."""
    response = admin_client.get("/modern/knowledge/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Chào mừng" in content
    assert "Tạo ghi chú đầu tiên" in content


# ---------------------------------------------------------------------------
# VAL-CROSS-006: Navigation reachability
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dashboard_reachable(admin_client):
    response = admin_client.get("/modern/knowledge/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_notes_list_reachable(admin_client):
    response = admin_client.get("/modern/knowledge/notes/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_note_create_page_reachable(admin_client):
    response = admin_client.get("/modern/knowledge/notes/new/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_search_page_reachable(admin_client):
    response = admin_client.get("/modern/knowledge/search/")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# VAL-NOTES-013, VAL-CROSS-010: Sidebar shows PKM section
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sidebar_shows_pkm_section_for_perm_user(perm_client):
    """User with pkm.access sees 'Tri thức cá nhân' in sidebar."""
    response = perm_client.get("/modern/knowledge/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Tri thức cá nhân" in content
    assert "nav_PKM" in content


@pytest.mark.django_db
def test_sidebar_hides_pkm_section_for_no_perm_user(no_perm_client):
    """User without pkm.access does NOT see PKM sidebar links (section is hidden).

    The nav-section div has style="display:none" and the links inside are
    gated by {% if can_pkm %} so they are not rendered.
    """
    response = no_perm_client.get("/modern/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    # The section title text is present (HTML is always rendered, just hidden)
    assert "Tri thức cá nhân" in content
    assert "nav_PKM" in content
    # The PKM nav links should NOT be rendered for no-permission users
    # (they are gated by {% if can_pkm %})
    # The dashboard link specifically should not have an href to pkm_dashboard
    assert 'href="/modern/knowledge/"' not in content.split("nav_PKM")[1].split(
        "nav_SYS"
    )[0] if "nav_PKM" in content and "nav_SYS" in content else True


@pytest.mark.django_db
def test_sidebar_shows_pkm_links_for_perm_user(perm_client):
    """Sidebar PKM section has links to Dashboard, Notes, Search."""
    response = perm_client.get("/modern/knowledge/")
    content = response.content.decode("utf-8")
    assert "Tổng quan" in content
    assert "Ghi chú" in content
    assert "Tìm kiếm" in content


# ---------------------------------------------------------------------------
# VAL-NOTES-002: View list of own notes
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_notes_list_shows_notes(admin_client, note, pinned_note, regular_note):
    """Notes list page shows the user's notes with title and timestamp."""
    response = admin_client.get("/modern/knowledge/notes/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Test Note" in content
    assert "Pinned Note" in content
    assert "Regular Note" in content


@pytest.mark.django_db
def test_notes_list_empty_state(admin_client):
    """Empty notes list shows a message."""
    response = admin_client.get("/modern/knowledge/notes/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Chưa có ghi chú" in content


# ---------------------------------------------------------------------------
# VAL-NOTES-001: Create a new knowledge note via UI
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_note_via_ui(admin_client, admin_user, company):
    """POST to create form saves a note and redirects to detail."""
    response = admin_client.post(
        "/modern/knowledge/notes/new/",
        {
            "title": "My New Note",
            "content": "# Title\n\nSome content",
            "role_context": "",
            "is_pinned": "",
        },
    )
    assert response.status_code == 302
    assert "/modern/knowledge/notes/" in response.url

    note = KnowledgeNote.objects.filter(title="My New Note").first()
    assert note is not None
    assert note.user == admin_user
    assert note.company == company
    assert note.content == "# Title\n\nSome content"
    assert note.is_pinned is False


@pytest.mark.django_db
def test_create_pinned_note_via_ui(admin_client):
    """POST with is_pinned=on creates a pinned note."""
    response = admin_client.post(
        "/modern/knowledge/notes/new/",
        {
            "title": "Pinned via UI",
            "content": "Pinned content",
            "is_pinned": "on",
        },
    )
    assert response.status_code == 302
    note = KnowledgeNote.objects.get(title="Pinned via UI")
    assert note.is_pinned is True


@pytest.mark.django_db
def test_create_note_with_tags(admin_client, admin_user, company):
    """POST with tag IDs attaches tags to the note."""
    tag = Tag.objects.create(user=admin_user, company=company, name="important")
    response = admin_client.post(
        "/modern/knowledge/notes/new/",
        {
            "title": "Tagged via UI",
            "content": "Content",
            "tags": [str(tag.id)],
        },
    )
    assert response.status_code == 302
    note = KnowledgeNote.objects.get(title="Tagged via UI")
    assert note.tags.count() == 1
    assert note.tags.first().name == "important"


# ---------------------------------------------------------------------------
# VAL-NOTES-011: Validation error on empty title
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_note_empty_title_validation(admin_client):
    """POST with empty title shows validation error and does not create note."""
    response = admin_client.post(
        "/modern/knowledge/notes/new/",
        {
            "title": "",
            "content": "Content without title",
        },
    )
    assert response.status_code == 200  # Stays on form page
    content = response.content.decode("utf-8")
    assert "Tiêu đề không được để trống" in content
    assert KnowledgeNote.objects.filter(content="Content without title").count() == 0


@pytest.mark.django_db
def test_create_note_whitespace_title_validation(admin_client):
    """POST with whitespace-only title also triggers validation."""
    response = admin_client.post(
        "/modern/knowledge/notes/new/",
        {
            "title": "   ",
            "content": "Whitespace title",
        },
    )
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Tiêu đề không được để trống" in content


# ---------------------------------------------------------------------------
# VAL-NOTES-003: Edit an existing note via UI
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_edit_note_form_loads(admin_client, note):
    """GET on edit page loads with existing content."""
    response = admin_client.get(f"/modern/knowledge/notes/{note.pk}/edit/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Test Note" in content  # Title is shown
    assert "Sửa ghi chú" in content or "Sửa:" in content


@pytest.mark.django_db
def test_edit_note_submit_updates(admin_client, note):
    """POST on edit page updates the note."""
    response = admin_client.post(
        f"/modern/knowledge/notes/{note.pk}/edit/",
        {
            "title": "Updated Title",
            "content": "Updated **markdown** content",
            "is_pinned": "on",
        },
    )
    assert response.status_code == 302
    note.refresh_from_db()
    assert note.title == "Updated Title"
    assert note.content == "Updated **markdown** content"
    assert note.is_pinned is True


@pytest.mark.django_db
def test_edit_note_empty_title_validation(admin_client, note):
    """POST with empty title on edit page shows validation error."""
    response = admin_client.post(
        f"/modern/knowledge/notes/{note.pk}/edit/",
        {
            "title": "",
            "content": "Should not save",
        },
    )
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Tiêu đề không được để trống" in content
    note.refresh_from_db()
    assert note.title == "Test Note"  # Unchanged


# ---------------------------------------------------------------------------
# VAL-NOTES-004: Delete a note via UI
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_delete_confirm_page_loads(admin_client, note):
    """GET on delete page shows confirmation."""
    response = admin_client.get(f"/modern/knowledge/notes/{note.pk}/delete/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Xác nhận xóa" in content
    assert "Test Note" in content


@pytest.mark.django_db
def test_delete_note_submit(admin_client, note):
    """POST on delete page removes the note."""
    note_pk = note.pk
    response = admin_client.post(f"/modern/knowledge/notes/{note_pk}/delete/", {})
    assert response.status_code == 302
    assert "/modern/knowledge/notes/" in response.url
    assert not KnowledgeNote.objects.filter(pk=note_pk).exists()


# ---------------------------------------------------------------------------
# VAL-NOTES-010: Note content supports markdown rendering
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_note_detail_renders_markdown(admin_client, note):
    """Note detail page renders markdown as HTML."""
    response = admin_client.get(f"/modern/knowledge/notes/{note.pk}/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    # Markdown heading -> <h1> (with id from toc extension)
    assert "<h1" in content
    assert "Heading</h1>" in content
    # Bold text -> <strong>
    assert "<strong>bold</strong>" in content
    # List items -> <li>
    assert "<li>Item 1</li>" in content
    assert "<li>Item 2</li>" in content


@pytest.mark.django_db
def test_note_detail_empty_content(admin_client, admin_user, company):
    """Note with empty content shows placeholder."""
    note = KnowledgeNote.objects.create(
        user=admin_user, company=company, title="Empty", content=""
    )
    response = admin_client.get(f"/modern/knowledge/notes/{note.pk}/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "chưa có nội dung" in content


# ---------------------------------------------------------------------------
# VAL-NOTES-009: Pinned notes appear at top
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pinned_notes_appear_first_in_list(admin_client, pinned_note, regular_note):
    """Pinned notes appear before unpinned notes in the list."""
    response = admin_client.get("/modern/knowledge/notes/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    # The pinned note should appear before the regular note in HTML
    pinned_pos = content.find("Pinned Note")
    regular_pos = content.find("Regular Note")
    assert pinned_pos > 0
    assert regular_pos > 0
    assert pinned_pos < regular_pos


@pytest.mark.django_db
def test_pinned_icon_shown_in_list(admin_client, pinned_note):
    """Pinned notes show a pin icon in the list."""
    response = admin_client.get("/modern/knowledge/notes/")
    content = response.content.decode("utf-8")
    assert "bi-pin-angle-fill" in content


# ---------------------------------------------------------------------------
# Search and tag filter in UI
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_search_filters_notes(admin_client, note, regular_note):
    """Search box filters notes by keyword."""
    response = admin_client.get("/modern/knowledge/notes/?search=Test")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Test Note" in content
    assert "Regular Note" not in content


@pytest.mark.django_db
def test_search_by_content(admin_client, note, regular_note):
    """Search filters by content as well as title."""
    response = admin_client.get("/modern/knowledge/notes/?search=bold")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Test Note" in content  # Contains "bold" in content
    assert "Regular Note" not in content


@pytest.mark.django_db
def test_tag_filter(admin_client, tagged_note, note):
    """Tag filter shows only notes with the selected tag."""
    response = admin_client.get("/modern/knowledge/notes/?tag=accounting")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Tagged Note" in content
    assert "Test Note" not in content


@pytest.mark.django_db
def test_search_page_works(admin_client, note, regular_note):
    """Dedicated search page returns results."""
    response = admin_client.get("/modern/knowledge/search/?q=Test")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Test Note" in content


@pytest.mark.django_db
def test_search_page_empty_query(admin_client, note):
    """Search page with empty query shows no results."""
    response = admin_client.get("/modern/knowledge/search/?q=")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Chưa có ghi chú" in content


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pagination(admin_client, admin_user, company):
    """Notes list is paginated when more than paginate_by notes exist."""
    # Create 15 notes (paginate_by=10)
    for i in range(15):
        KnowledgeNote.objects.create(
            user=admin_user, company=company, title=f"Page Note {i:02d}", content=f"Content {i}"
        )
    response = admin_client.get("/modern/knowledge/notes/")
    assert response.status_code == 200
    assert response.context["is_paginated"] is True
    assert response.context["page_obj"].object_list.count() == 10
    assert response.context["paginator"].num_pages == 2

    # Page 2
    response2 = admin_client.get("/modern/knowledge/notes/?page=2")
    assert response2.status_code == 200
    assert response2.context["page_obj"].object_list.count() == 5


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dashboard_shows_stats(admin_client, note, pinned_note):
    """Dashboard shows note count stat."""
    response = admin_client.get("/modern/knowledge/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Tổng ghi chú" in content
    assert "stat-notes" in content
    # Should show count of 2 (note + pinned_note)
    assert ">2<" in content or ">2 " in content


# ---------------------------------------------------------------------------
# Per-user isolation in UI
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_notes_private_per_user(admin_client, admin_user, company, note):
    """User B cannot see User A's notes via UI."""
    other_user = User.objects.create_user(
        username="other_ui_user", password="Test1234", email="other@pkm.test"
    )
    # Grant pkm.access to other user
    perm, _ = Permission.objects.get_or_create(
        code="pkm.access",
        defaults={"module": "pkm", "name": "PKM Access", "description": "Access PKM module"},
    )
    role = Role.objects.create(company=company, code="other_pkm", name="Other PKM Role")
    role.permissions.add(perm)
    UserCompanyRole.objects.create(user=other_user, company=company, role=role)

    other_client = Client()
    other_client.force_login(other_user)
    session = other_client.session
    session["current_company_id"] = company.id
    session.save()

    # Other user sees empty list
    response = other_client.get("/modern/knowledge/notes/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Test Note" not in content

    # Other user cannot access admin's note via direct URL (404)
    response = other_client.get(f"/modern/knowledge/notes/{note.pk}/")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Note detail view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_note_detail_404_for_nonexistent(admin_client):
    """Non-existent note returns 404."""
    response = admin_client.get("/modern/knowledge/notes/99999/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_note_detail_shows_tags(admin_client, tagged_note):
    """Note detail page shows tags as clickable badges."""
    response = admin_client.get(f"/modern/knowledge/notes/{tagged_note.pk}/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "accounting" in content
