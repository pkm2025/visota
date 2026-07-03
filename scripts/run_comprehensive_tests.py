"""Comprehensive test script with screenshots for every test case.

Outputs evidence screenshots to test-evidence/ directory.
Generates a full HTML report.
"""

import os
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8903"
EVIDENCE = Path(__file__).parent.parent / "test-evidence"
EVIDENCE.mkdir(exist_ok=True)

# Clean old screenshots
for f in EVIDENCE.glob("*.png"):
    f.unlink()

# Results collector
results = []
current_group = ""


def screenshot(page, name):
    """Take screenshot and return path."""
    path = EVIDENCE / f"{name}.png"
    page.screenshot(path=str(path), full_page=False)
    return f"test-evidence/{name}.png"


def test_case(page, tc_id, description, test_func):
    """Run a test case, capture result + screenshot."""
    global current_group
    status = "PASS"
    error_msg = ""
    screenshot_path = ""
    try:
        screenshot_path = test_func(page)
    except Exception as e:
        status = "FAIL"
        error_msg = str(e)[:200]
        try:
            screenshot_path = screenshot(page, f"{tc_id}_FAIL")
        except Exception:
            screenshot_path = ""
    results.append(
        {
            "tc_id": tc_id,
            "group": current_group,
            "description": description,
            "status": status,
            "error": error_msg,
            "screenshot": screenshot_path,
        }
    )
    print(f"  [{status}] {tc_id}: {description}")
    return status


def login(page, username="e2e_admin", password="E2EPass123!"):
    """Login helper - delegates to _do_login."""
    _do_login(page, username, password)


def check_page(title, url_path, ss_name):
    """Test factory: visit a page and check for content."""

    def _test(page):
        page.goto(f"{BASE}{url_path}", wait_until="networkidle", timeout=15000)
        content = page.content()
        # Check for error indicators
        if "Traceback" in content or "Server Error" in content:
            raise Exception(f"Server error on {url_path}")
        return screenshot(page, ss_name)

    return _test


# ============================================================
# TEST CASES DEFINITION
# ============================================================

ALL_TESTS = []


def define_group(name):
    global current_group
    current_group = name


def add(tc_id, desc, func):
    ALL_TESTS.append((tc_id, desc, func))


# --- Group 1: Authentication ---
define_group("1. Xác thực (Authentication)")
add("AUTH-01", "Trang dang nhap hien thi", lambda p: check_page("Login", "/auth/login/", "auth_01_login_page")(p))
add("AUTH-02", "Dang nhap admin thanh cong", lambda p: _auth_02(p))
add("AUTH-03", "Dang nhap sai mat khau", lambda p: _auth_03(p))
add("AUTH-04", "Dang xuat", lambda p: _auth_04(p))


def _do_login(page, username, password):
    page.context.clear_cookies()
    page.goto(f"{BASE}/auth/login/", wait_until="networkidle", timeout=10000)
    page.wait_for_selector('input[name="username"]', timeout=5000)
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.press('input[name="password"]', 'Enter')
    page.wait_for_load_state("networkidle", timeout=10000)
    page.wait_for_timeout(1500)


def _auth_02(page):
    _do_login(page, "e2e_admin", "E2EPass123!")
    url = page.url
    if "login" in url:
        raise Exception(f"Login failed - still on login page: {url}")
    return screenshot(page, "auth_02_login_success")


def _auth_03(page):
    _do_login(page, "e2e_admin", "wrongpassword")
    return screenshot(page, "auth_03_wrong_password")


def _auth_04(page):
    _do_login(page, "e2e_admin", "E2EPass123!")
    page.evaluate("const f=document.createElement('form');f.method='POST';f.action='/auth/logout/';const c=document.querySelector('[name=csrfmiddlewaretoken]');if(c){const i=document.createElement('input');i.name='csrfmiddlewaretoken';i.value=c.value;f.appendChild(i);}document.body.appendChild(f);f.submit();")
    page.wait_for_load_state("networkidle", timeout=10000)
    page.wait_for_timeout(1000)
    return screenshot(page, "auth_04_logout")


# --- Group 2: Dashboard ---
define_group("2. Dashboard")
add("DASH-01", "Dashboard hiển thị", lambda p: check_page("Dashboard", "/modern/", "dash_01_dashboard")(p))
add("DASH-02", "Mobile dashboard", lambda p: _dash_02(p))


def _dash_02(page):
    # Ensure logged in
    page.goto(f"{BASE}/modern/", wait_until="networkidle", timeout=10000)
    if "login" in page.url:
        login(page)
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{BASE}/modern/", wait_until="networkidle")
    page.wait_for_timeout(500)
    return screenshot(page, "dash_02_mobile")


# --- Group 3: Kế toán tổng hợp ---
define_group("3. Kế toán tổng hợp (Ledger)")
add("LED-01", "Danh sách chứng từ", lambda p: check_page("Vouchers", "/modern/vouchers/", "led_01_voucher_list")(p))
add("LED-02", "Tạo chứng từ", lambda p: check_page("Voucher create", "/modern/vouchers/new/", "led_02_voucher_create")(p))
add("LED-03", "Nhật ký chung (S03a-DN)", lambda p: check_page("GJ", "/modern/reports/general-journal/", "led_03_general_journal")(p))
add("LED-04", "Sổ cái TK (S03b-DN)", lambda p: check_page("GL", "/modern/reports/general-ledger/", "led_04_general_ledger")(p))
add("LED-05", "Bảng cân đối TK (S06)", lambda p: check_page("TB", "/modern/reports/trial-balance/", "led_05_trial_balance")(p))
add("LED-06", "Sổ chi tiết TK", lambda p: check_page("SubLedger", "/modern/reports/sub-ledger/", "led_06_sub_ledger")(p))
add("LED-07", "Sổ ĐK CTGS (S02a-DN)", lambda p: check_page("BER", "/modern/reports/book-entry-register/", "led_07_book_entry")(p))


# --- Group 4: Nhật ký chuyên biệt ---
define_group("4. Nhật ký chuyên biệt (Specialized Journals)")
add("SJ-01", "NK thu tiền (S03a1-DN)", lambda p: check_page("CRJ", "/modern/reports/journal/cash-receipt/", "sj_01_cash_receipt")(p))
add("SJ-02", "NK chi tiền (S03a2-DN)", lambda p: check_page("CPJ", "/modern/reports/journal/cash-payment/", "sj_02_cash_payment")(p))
add("SJ-03", "NK bán hàng (S03a4-DN)", lambda p: check_page("SJ", "/modern/reports/journal/sales/", "sj_03_sales")(p))
add("SJ-04", "NK mua hàng (S03a3-DN)", lambda p: check_page("PJ", "/modern/reports/journal/purchase/", "sj_04_purchase")(p))
add("SJ-05", "Sổ tổng hợp chữ T", lambda p: check_page("T-Account", "/modern/reports/t-account/", "sj_05_t_account")(p))


# --- Group 5: Sổ kế toán chi tiết ---
define_group("5. Sổ kế toán chi tiết (Sub-ledger Books)")
add("SL-01", "Sổ quỹ tiền mặt (S07-DN)", lambda p: check_page("CashBook", "/modern/reports/cash-book/", "sl_01_cash_book")(p))
add("SL-02", "Sổ tiền gửi ngân hàng (S08-DN)", lambda p: check_page("BankBook", "/modern/reports/bank-book/", "sl_02_bank_book")(p))
add("SL-03", "Sổ chi tiết bán hàng (S35-DN)", lambda p: check_page("SalesDetail", "/modern/reports/sales-detail/", "sl_03_sales_detail")(p))


# --- Group 6: Báo cáo tài chính ---
define_group("6. Báo cáo tài chính")
add("FIN-01", "BC tình hình tài chính (B01-DN)", lambda p: check_page("BS", "/modern/reports/balance-sheet/", "fin_01_balance_sheet")(p))
add("FIN-02", "BC kết quả SXKD (B02-DN)", lambda p: check_page("PnL", "/modern/reports/pnl/", "fin_02_pnl")(p))
add("FIN-03", "BC dòng tiền trực tiếp (B03-DN)", lambda p: check_page("CF-D", "/modern/reports/cash-flow/direct/", "fin_03_cashflow_direct")(p))
add("FIN-04", "BC dòng tiền gián tiếp (B03-DN)", lambda p: check_page("CF-I", "/modern/reports/cash-flow/indirect/", "fin_04_cashflow_indirect")(p))
add("FIN-05", "Tờ khai thuế GTGT (01-GTGT)", lambda p: check_page("VAT", "/modern/reports/vat-return/", "fin_05_vat")(p))
add("FIN-06", "Bảng tính giá thành", lambda p: check_page("Cost", "/modern/reports/cost/", "fin_06_cost")(p))


# --- Group 7: CTGS Workflow ---
define_group("7. Chứng từ ghi sổ (CTGS Workflow)")
add("CTGS-01", "Khai báo CTGS", lambda p: check_page("CTGS-Create", "/modern/ctgs/create/", "ctgs_01_create")(p))
add("CTGS-02", "Đăng ký CTGS", lambda p: check_page("CTGS-Register", "/modern/ctgs/register/", "ctgs_02_register")(p))
add("CTGS-03", "Kiểm tra CTGS", lambda p: check_page("CTGS-Check", "/modern/ctgs/check/", "ctgs_03_check")(p))
add("CTGS-04", "Bảng kê S04-H", lambda p: check_page("CTGS-Schedule", "/modern/ctgs/schedule/", "ctgs_04_schedule")(p))


# --- Group 8: Cập nhật số liệu ---
define_group("8. Cập nhật số liệu (Period Tools)")
add("TOOL-01", "Phân bổ cuối kỳ", lambda p: check_page("Allocation", "/modern/tools/period-allocation/", "tool_01_allocation")(p))
add("TOOL-02", "KK kết chuyển cuối kỳ", lambda p: check_page("Closing", "/modern/tools/closing-entry-declaration/", "tool_02_closing")(p))
add("TOOL-03", "Đánh lại số chứng từ", lambda p: check_page("Renumber", "/modern/tools/voucher-renumber/", "tool_03_renumber")(p))
add("TOOL-04", "Chuyển số dư năm sau", lambda p: check_page("CarryForward", "/modern/tools/year-end-carry-forward/", "tool_04_carry_forward")(p))
add("TOOL-05", "Dư ban đầu KH", lambda p: check_page("CustOB", "/modern/tools/opening-balances/customers/", "tool_05_cust_ob")(p))
add("TOOL-06", "Dư ban đầu HĐ", lambda p: check_page("InvOB", "/modern/tools/opening-balances/invoices/", "tool_06_inv_ob")(p))


# --- Group 9: Master Data ---
define_group("9. Danh mục từ điển (Master Data)")
add("MD-01", "Hệ thống tài khoản", lambda p: check_page("CoA", "/modern/chart-of-accounts/", "md_01_coa")(p))
add("MD-02", "Bộ phận hạch toán", lambda p: check_page("Dept", "/modern/departments/", "md_02_department")(p))
add("MD-03", "Khách hàng", lambda p: check_page("Customers", "/modern/customers/", "md_03_customers")(p))
add("MD-04", "Nhà cung cấp", lambda p: check_page("Vendors", "/modern/vendors/", "md_04_vendors")(p))
add("MD-05", "Hàng hóa", lambda p: check_page("Products", "/modern/products/", "md_05_products")(p))


# --- Group 10: Bán hàng & Mua hàng ---
define_group("10. Bán hàng & Mua hàng")
add("SALE-01", "Danh sách hóa đơn bán", lambda p: check_page("SI", "/modern/sales-invoices/", "sale_01_list")(p))
add("SALE-02", "Tạo hóa đơn bán", lambda p: check_page("SI-New", "/modern/sales-invoices/new/", "sale_02_create")(p))
add("PUR-01", "Danh sách phiếu nhập mua", lambda p: check_page("PI", "/modern/purchase-invoices/", "pur_01_list")(p))
add("PUR-02", "Tạo phiếu nhập mua", lambda p: check_page("PI-New", "/modern/purchase-invoices/new/", "pur_02_create")(p))


# --- Group 11: Kho & Tài sản ---
define_group("11. Kho & Tài sản")
add("INV-01", "Phiếu nhập xuất", lambda p: check_page("Stock", "/modern/stock-vouchers/", "inv_01_stock")(p))
add("INV-02", "Tổng quan kho", lambda p: check_page("StockDash", "/modern/inventory/dashboard/", "inv_02_dashboard")(p))
add("INV-03", "Thẻ kho", lambda p: check_page("StockCard", "/modern/inventory/stock-card/", "inv_03_stock_card")(p))
add("ASSET-01", "Tài sản cố định", lambda p: check_page("Assets", "/modern/assets/", "asset_01_list")(p))
add("ASSET-02", "Tính khấu hao", lambda p: check_page("Depreciation", "/modern/assets/depreciation/", "asset_02_depreciation")(p))


# --- Group 12: Nhân sự & Lương ---
define_group("12. Nhân sự & Lương")
add("HR-01", "Nhân viên", lambda p: check_page("Employees", "/modern/employees/", "hr_01_employees")(p))
add("HR-02", "Hợp đồng lao động", lambda p: check_page("LC", "/modern/labor-contracts/", "hr_02_contracts")(p))
add("HR-03", "Tính lương", lambda p: check_page("Payroll", "/modern/payroll/run/", "hr_03_payroll")(p))
add("HR-04", "BHXH", lambda p: check_page("Insurance", "/modern/insurance/", "hr_04_insurance")(p))
add("HR-05", "BC D62", lambda p: check_page("D62", "/modern/reports/d62/", "hr_05_d62")(p))
add("HR-06", "BC thuế TNCN", lambda p: check_page("PIT", "/modern/reports/pit-monthly/", "hr_06_pit")(p))


# --- Group 13: CRM & Dự án ---
define_group("13. CRM & Dự án")
add("CRM-01", "Khách tiềm năng", lambda p: check_page("Leads", "/modern/crm/leads/", "crm_01_leads")(p))
add("CRM-02", "Cơ hội bán hàng", lambda p: check_page("Opps", "/modern/crm/opportunities/", "crm_02_opportunities")(p))
add("PRJ-01", "Quản lý dự án", lambda p: check_page("Projects", "/modern/projects/", "prj_01_projects")(p))


# --- Group 14: Ngân hàng & HĐĐT ---
define_group("14. Ngân hàng & Hóa đơn điện tử")
add("BANK-01", "Tài khoản ngân hàng", lambda p: check_page("BA", "/modern/banking/accounts/", "bank_01_accounts")(p))
add("BANK-02", "Đối soát ngân hàng", lambda p: check_page("BR", "/modern/banking/reconcile/", "bank_02_reconcile")(p))
add("EINV-01", "Hóa đơn điện tử", lambda p: check_page("EI", "/modern/einvoices/", "einv_01_list")(p))


# --- Group 15: Hợp đồng ---
define_group("15. Hợp đồng")
add("CON-01", "Danh sách hợp đồng", lambda p: check_page("Contracts", "/modern/contracts/", "con_01_list")(p))
add("CON-02", "Mẫu hợp đồng", lambda p: check_page("CT", "/modern/contract-templates/", "con_02_templates")(p))
add("CON-03", "Wizard tạo hợp đồng", lambda p: check_page("Wizard", "/modern/contracts/wizard/", "con_03_wizard")(p))


# --- Group 16: RBAC ---
define_group("16. Phan quyen (RBAC)")
add("RBAC-01", "Sales truy cap vouchers", lambda p: _rbac_01(p))
add("RBAC-02", "Sales truy cap sales duoc phep", lambda p: _rbac_02(p))


def _rbac_01(page):
    _do_login(page, "e2e_sales", "E2EPass123!")
    page.goto(f"{BASE}/modern/vouchers/", wait_until="networkidle", timeout=10000)
    page.wait_for_timeout(1000)
    return screenshot(page, "rbac_01_sales_vouchers")


def _rbac_02(page):
    page.goto(f"{BASE}/modern/sales-invoices/", wait_until="networkidle", timeout=10000)
    return screenshot(page, "rbac_02_sales_allowed")


# --- Group 17: Help & Settings ---
define_group("17. Trợ giúp & Hệ thống")
add("HELP-01", "Trang trợ giúp", lambda p: check_page("Help", "/modern/help/", "help_01_kb")(p))
add("SYS-01", "Hồ sơ công ty", lambda p: check_page("Profile", "/modern/admin/company-profile/", "sys_01_company")(p))
add("SYS-02", "Vai trò & phân quyền", lambda p: check_page("Roles", "/modern/admin/roles/", "sys_02_roles")(p))


# ============================================================
# RUN ALL TESTS
# ============================================================

def main():
    print("=" * 70)
    print("COMPREHENSIVE TEST SUITE WITH SCREENSHOTS")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE}")
    print(f"Evidence dir: {EVIDENCE}")
    print("=" * 70)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        # Login once for all tests
        login(page)
        print(f"\n[Setup] Logged in as e2e_admin\n")

        for tc_id, desc, func in ALL_TESTS:
            # Auth tests handle their own login/logout
            if not tc_id.startswith("AUTH") and not tc_id.startswith("RBAC"):
                # Ensure we're logged in - try to access dashboard
                page.goto(f"{BASE}/modern/", wait_until="networkidle", timeout=10000)
                if "login" in page.url:
                    _do_login(page, "e2e_admin", "E2EPass123!")

            test_case(page, tc_id, desc, func)

            # After AUTH-04 (logout), session is cleared - need re-login
            if tc_id == "AUTH-04":
                _do_login(page, "e2e_admin", "E2EPass123!")
            # Re-login as admin after RBAC-02
            if tc_id == "RBAC-02":
                _do_login(page, "e2e_admin", "E2EPass123!")

        browser.close()

    # Summary
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = total - passed
    print(f"\n{'=' * 70}")
    print(f"RESULTS: {passed}/{total} passed, {failed} failed")
    print(f"{'=' * 70}")

    # Generate HTML report
    generate_html_report()
    print(f"\nReport saved to: test-evidence/report.html")


def generate_html_report():
    """Generate comprehensive HTML report with embedded screenshots."""
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = total - passed

    # Group results
    from collections import OrderedDict

    groups = OrderedDict()
    for r in results:
        if r["group"] not in groups:
            groups[r["group"]] = []
        groups[r["group"]].append(r)

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Báo cáo kiểm thử toàn diện — PMKetoan</title>
<style>
body {{ font-family: -apple-system, sans-serif; margin: 20px; background: #f8f9fa; }}
h1 {{ color: #2563eb; border-bottom: 3px solid #2563eb; padding-bottom: 10px; }}
h2 {{ color: #495057; margin-top: 30px; border-left: 4px solid #2563eb; padding-left: 10px; }}
.summary {{ display: flex; gap: 20px; margin: 20px 0; }}
.summary-card {{ background: white; padding: 20px 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
.summary-card .num {{ font-size: 36px; font-weight: bold; }}
.summary-card .label {{ color: #6c757d; font-size: 14px; }}
.pass .num {{ color: #16a34a; }}
.fail .num {{ color: #dc2626; }}
.total .num {{ color: #2563eb; }}
.test-case {{ background: white; margin: 10px 0; padding: 15px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
.test-case-header {{ display: flex; justify-content: space-between; align-items: center; }}
.test-case-id {{ font-weight: bold; color: #495057; }}
.badge {{ padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
.badge-pass {{ background: #d4edda; color: #155724; }}
.badge-fail {{ background: #f8d7da; color: #721c24; }}
.screenshot {{ margin-top: 10px; max-width: 100%; border: 1px solid #dee2e6; border-radius: 4px; }}
.error-msg {{ color: #dc2626; font-size: 13px; margin-top: 5px; }}
.meta {{ color: #6c757d; font-size: 13px; margin-bottom: 20px; }}
table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #dee2e6; }}
th {{ background: #e9ecef; font-weight: 600; }}
</style>
</head>
<body>
<h1>Báo cáo kiểm thử toàn diện — PMKetoan (Visota)</h1>
<div class="meta">
  <p><strong>Ngày test:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
  <p><strong>Server:</strong> {BASE}</p>
  <p><strong>Tài khoản:</strong> e2e_admin (superuser), e2e_sales (RBAC)</p>
  <p><strong>Tổng số test case:</strong> {total}</p>
</div>

<div class="summary">
  <div class="summary-card total"><div class="num">{total}</div><div class="label">Tổng</div></div>
  <div class="summary-card pass"><div class="num">{passed}</div><div class="label">Pass</div></div>
  <div class="summary-card fail"><div class="num">{failed}</div><div class="label">Fail</div></div>
  <div class="summary-card"><div class="num">{passed*100//total}%</div><div class="label">Pass Rate</div></div>
</div>
"""

    for group_name, cases in groups.items():
        g_total = len(cases)
        g_pass = sum(1 for c in cases if c["status"] == "PASS")
        html += f"<h2>{group_name} ({g_pass}/{g_total})</h2>\n"

        for r in cases:
            badge = "badge-pass" if r["status"] == "PASS" else "badge-fail"
            html += f"""
<div class="test-case">
  <div class="test-case-header">
    <span class="test-case-id">{r['tc_id']}: {r['description']}</span>
    <span class="badge {badge}">{r['status']}</span>
  </div>
"""
            if r["error"]:
                html += f'  <div class="error-msg">Error: {r["error"]}</div>\n'
            if r["screenshot"]:
                html += f'  <img class="screenshot" src="{r["screenshot"]}" alt="{r["tc_id"]}" loading="lazy">\n'
            html += "</div>\n"

    html += """
</body>
</html>"""

    report_path = EVIDENCE / "report.html"
    report_path.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
