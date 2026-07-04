---
name: add-accounting-report
description: Create a new Vietnamese accounting report (sổ sách/báo cáo) following TT133/200 conventions. Generates view, template, URL, sidebar link, and test.
---

# Skill: Add Accounting Report

Create a new Vietnamese accounting report following existing patterns.

## Steps

1. **Create the view** in `apps/ui_modern/views/report_views.py`:
   - Extend `LoginRequiredMixin, TemplateView`
   - Use `_parse_period_kwargs()` and `_common_period_choices()` helpers
   - Filter `VoucherLine` or `AccountPeriodBalance` by `fiscal_year`, `period`
   - Return rows + totals in context

2. **Create the template** in `templates/modern/reporting/<report_name>.html`:
   - Extend `modern/base/layout.html`
   - Include period filter form (fiscal_year + period dropdowns)
   - Use `|vnd` filter for currency formatting
   - Add breadcrumb with report name

3. **Add URL** in `apps/ui_modern/urls.py`:
   ```python
   path("reports/<report-name>/", login_required(NewReportView.as_view()), name="report_new_report"),
   ```

4. **Add sidebar link** in `templates/modern/base/layout.html` under "Sổ sách" section.

5. **Export the view** in `apps/ui_modern/views/__init__.py`.

6. **Write tests** in `tests/test_<report_name>.py`:
   - Test 200 status for logged-in user
   - Test data appears in context
   - Test login required

## Conventions
- Vietnamese for all UI labels
- Use form codes: S01-DN, S02-DN, S03a-DN, B01-DN, B02-DN, etc.
- Follow TT133/2016 or TT200/2014 account mapping
