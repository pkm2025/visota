"""Seed ``FinancialReportLine`` rows for the four statutory reports.

Idempotent: running multiple times produces the same row count because
rows are matched on ``(report_type, display_order)`` via ``update_or_create``.

Convention:
  - Asset / expense accounts (debit-natured) use ``tk_no_pattern``.
  - Liability / equity / revenue accounts (credit-natured) use ``tk_co_pattern``.
  - Parent lines use ``cong_thuc`` to sum child ``ma_so`` codes.

Report types and approximate line counts:
    B01-DN           ~50 lines  (Balance Sheet)
    B02-DN           ~30 lines  (Profit & Loss)
    B03-DN-direct    ~20 lines  (Cash Flow - direct method)
    B03-DN-indirect  ~20 lines  (Cash Flow - indirect method)
"""

from django.core.management.base import BaseCommand

from apps.reporting.models import FinancialReportLine

# Each tuple: (stt, ma_so, chi_tieu, thuyet_minh, tk_no, tk_co, cong_thuc,
#              tinh_giam_tru, is_header, parent_ma_so)

B01_DN = [
    # ================== TÀI SẢN (Assets - debit-natured: tk_no_pattern) ==================
    ("A", "", "TÀI SẢN NGẮN HẠN", "", "", "", "", "", True, "A"),
    ("I", "100", "Tổng tài sản ngắn hạn", "", "", "", "=110+120+130+140+150", "", False, "A"),
    ("1", "110", "Tiền và các khoản tương đương tiền", "", "111*,112*", "", "", "", False, "A"),
    ("", "110a", "Tiền mặt", "", "1111*", "", "", "", False, "A"),
    ("", "110b", "Tiền gửi ngân hàng", "", "1121*", "", "", "", False, "A"),
    ("", "110c", "Tiền đang chuyển", "", "113*", "", "", "", False, "A"),
    ("2", "120", "Đầu tư tài chính ngắn hạn", "", "121*,128*", "", "", "", False, "A"),
    ("", "120a", "Chứng khoán kinh doanh", "", "121*", "", "", "", False, "A"),
    ("", "120b", "Đầu tư nắm giữ đến ngày đáo hạn", "", "1281*", "", "", "", False, "A"),
    ("3", "130", "Các khoản phải thu ngắn hạn", "", "131*,136*,138*", "", "", "", False, "A"),
    ("", "130a", "Phải thu ngắn hạn khách hàng", "", "131*", "", "", "", False, "A"),
    ("", "130b", "Trả trước cho người bán ngắn hạn", "", "3311*", "", "", "", False, "A"),
    ("", "130c", "Phải thu nội bộ", "", "136*", "", "", "", False, "A"),
    ("", "130d", "Phải thu khác ngắn hạn", "", "138*", "", "", "", False, "A"),
    ("4", "140", "Hàng tồn kho", "", "151*,152*,153*,155*,156*,157*", "", "", "", False, "A"),
    ("", "140a", "Nguyên liệu, vật liệu, công cụ", "", "152*", "", "", "", False, "A"),
    ("", "140b", "Chi phí SXKD dở dang", "", "154*", "", "", "", False, "A"),
    ("", "140c", "Thành phẩm", "", "155*", "", "", "", False, "A"),
    ("", "140d", "Hàng hóa", "", "156*", "", "", "", False, "A"),
    ("5", "150", "Tài sản ngắn hạn khác", "", "241*,242*", "", "", "", False, "A"),
    ("", "150a", "Chi phí trả trước ngắn hạn", "", "242*", "", "", "", False, "A"),
    ("", "150b", "Thuế GTGT được khấu trừ", "", "1331*", "", "", "", False, "A"),
    # --- B. TÀI SẢN DÀI HẠN ---
    ("B", "", "TÀI SẢN DÀI HẠN", "", "", "", "", "", True, "A"),
    ("II", "200", "Tổng tài sản dài hạn", "", "", "", "=210+220+230+240+250", "", False, "A"),
    ("1", "210", "Tài sản cố định", "", "211*,212*,213*", "", "", "", False, "A"),
    ("", "210a", "TSCĐ hữu hình", "", "211*,212*", "", "", "", False, "A"),
    ("", "210b", "TSCĐ vô hình", "", "213*", "", "", "", False, "A"),
    ("2", "220", "Bất động sản đầu tư", "", "2271*", "", "", "", False, "A"),
    ("3", "230", "Tài sản dở dang dài hạn", "", "2422*", "", "", "", False, "A"),
    ("4", "240", "Đầu tư tài chính dài hạn", "", "2282*", "", "", "", False, "A"),
    ("5", "250", "Tài sản dài hạn khác", "", "261*,262*", "", "", "", False, "A"),
    # --- TỔNG CỘNG TÀI SẢN ---
    ("", "270", "TỔNG CỘNG TÀI SẢN", "", "", "", "=100+200", "", True, "A"),
    # ================== NGUỒN VỐN ==================
    # --- C. NỢ PHẢI TRẢ (Liabilities - credit-natured: tk_co_pattern) ---
    ("C", "", "NỢ PHẢI TRẢ", "", "", "", "", "", True, "L"),
    ("I", "300", "Nợ ngắn hạn", "", "", "", "=310+320+330+340+350+360+370+380+390", "", False, "L"),
    ("1", "310", "Vay và nợ thuê TC ngắn hạn", "", "", "311*", "", "", False, "L"),
    ("2", "320", "Phải trả người bán ngắn hạn", "", "", "3311*", "", "", False, "L"),
    ("3", "330", "Người mua trả tiền trước", "", "", "131*", "", "", False, "L"),
    ("4", "340", "Thuế và các khoản phải nộp NN", "", "", "333*,334*", "", "", False, "L"),
    ("", "340a", "Thuế GTGT đầu ra", "", "", "33311*", "", "", False, "L"),
    ("", "340b", "Thuế TNDN", "", "", "3334*", "", "", False, "L"),
    (
        "",
        "340c",
        "Thuế, lệ phí khác",
        "",
        "",
        "3332*,3333*,3336*,3337*,3338*,3339*",
        "",
        "",
        False,
        "L",
    ),
    ("5", "350", "Phải trả nội bộ", "", "", "3361*", "", "", False, "L"),
    ("6", "360", "Chi phí phải trả", "", "", "3351*", "", "", False, "L"),
    ("7", "370", "Tạm ứng", "", "", "314*", "", "", False, "L"),
    ("8", "380", "Doanh thu chưa thực hiện", "", "", "3387*", "", "", False, "L"),
    (
        "9",
        "390",
        "Nợ ngắn hạn khác",
        "",
        "",
        "3381*,3382*,3383*,3384*,3385*,3388*,3389*,351*,352*",
        "",
        "",
        False,
        "L",
    ),
    ("II", "400", "Nợ dài hạn", "", "", "", "=410+420+430+440+450+460+490", "", False, "L"),
    ("1", "410", "Vay và nợ thuê TC dài hạn", "", "", "3411*,3412*", "", "", False, "L"),
    ("2", "420", "Phải trả trên thuê TC dài hạn", "", "", "34111*", "", "", False, "L"),
    ("3", "430", "Thuế GNNS được hoãn", "", "", "3471*", "", "", False, "L"),
    ("4", "440", "Phải trả nội bộ dài hạn", "", "", "3362*", "", "", False, "L"),
    ("5", "450", "Chi phí phải trả dài hạn", "", "", "3352*", "", "", False, "L"),
    ("6", "460", "Doanh thu chưa thực hiện dài hạn", "", "", "3387*", "", "", False, "L"),
    ("7", "490", "Nợ dài hạn khác", "", "", "342*,344*", "", "", False, "L"),
    # --- D. VỐN CHỦ SỞ HỮU (Equity - credit-natured: tk_co_pattern) ---
    ("D", "", "VỐN CHỦ SỞ HỮU", "", "", "", "", "", True, "E"),
    (
        "III",
        "500",
        "Vốn chủ sở hữu",
        "",
        "",
        "",
        "=510+520+530+540+550+560+570+580",
        "",
        False,
        "E",
    ),
    ("1", "510", "Vốn góp của chủ sở hữu", "", "", "411*", "", "", False, "E"),
    ("2", "520", "Cổ phiếu quỹ", "", "419*", "", "", "", False, "E"),
    ("3", "530", "Chênh lệch đánh giá lại TS", "", "", "412*", "", "", False, "E"),
    ("4", "540", "Chênh lệch tỷ giá hối đoái", "", "", "413*", "", "", False, "E"),
    ("5", "550", "Quỹ thuộc VCSH", "", "", "414*,418*", "", "", False, "E"),
    ("6", "560", "Lợi nhuận sau thuế chưa phân phối", "", "", "421*", "", "", False, "E"),
    ("7", "570", "Nguồn vốn tài trợ", "", "", "441*", "", "", False, "E"),
    ("8", "580", "Quỹ khen thưởng, phúc lợi", "", "", "3531*,3532*", "", "", False, "E"),
    ("IV", "600", "Nguồn kinh phí và quỹ khác", "", "", "46*", "", "", False, "E"),
    # --- TỔNG NGUỒN VỐN ---
    ("", "700", "TỔNG CỘNG NGUỒN VỐN", "", "", "", "=300+400+500+600", "", True, "L"),
]

B02_DN = [
    # P&L: ma_so 01-14 used by PnLService._generate_from_config
    # Revenue/income accounts use tk_co_pattern (credit-natured).
    # Expense accounts use tk_no_pattern (debit-natured).
    ("1", "01", "Doanh thu bán hàng và cung cấp dịch vụ", "", "", "511*,512*", "", "", False, ""),
    (
        "2",
        "02",
        "Các khoản giảm trừ doanh thu",
        "",
        "5211*,5212*,5213*,5218*",
        "",
        "",
        "",
        False,
        "",
    ),
    ("3", "01a", "Doanh thu thuần bán hàng và CCDV", "", "", "", "=01-02", "", False, ""),
    ("4", "03", "Giá vốn hàng bán", "", "6321*,6322*,6323*,6324*,6328*", "", "", "", False, ""),
    ("5", "03a", "Lợi nhuận gộp về bán hàng và CCDV", "", "", "", "=01-02-03", "", True, ""),
    (
        "6",
        "04",
        "Doanh thu hoạt động tài chính",
        "",
        "",
        "5151*,5152*,5153*,5154*,5158*",
        "",
        "",
        False,
        "",
    ),
    ("", "04a", "Cổ tức, lợi nhuận được chia", "", "", "5151*", "", "", False, ""),
    ("", "04b", "Lãi tiền gửi, cho vay", "", "", "5152*", "", "", False, ""),
    ("", "04c", "Lãi chênh lệch tỷ giá", "", "", "5153*", "", "", False, ""),
    ("", "04d", "Lãi bán CK, thanh lý", "", "", "5154*", "", "", False, ""),
    ("7", "05", "Chi phí tài chính", "", "6351*,6352*,6353*,6354*,6358*", "", "", "", False, ""),
    ("", "05a", "Chi phí lãi vay", "", "6351*", "", "", "", False, ""),
    ("", "05b", "Lỗ chênh lệch tỷ giá", "", "6353*", "", "", "", False, ""),
    ("", "05c", "Chi phí bán CK, thanh lý", "", "6354*", "", "", "", False, ""),
    ("8", "06", "Chi phí bán hàng", "", "6411*,6412*,6413*,6414*,6418*", "", "", "", False, ""),
    ("", "06a", "Chi phí NV bán hàng", "", "6411*", "", "", "", False, ""),
    ("", "06b", "Chi phí vật liệu, bao bì", "", "6412*", "", "", "", False, ""),
    ("", "06c", "Chi phí ĐTLS CCDC bán", "", "6413*", "", "", "", False, ""),
    ("", "06d", "Chi phí KH TSCĐ", "", "6414*", "", "", "", False, ""),
    ("9", "07", "Chi phí quản lý DN", "", "6421*,6422*,6423*,6424*,6428*", "", "", "", False, ""),
    ("", "07a", "Chi phí NV quản lý", "", "6421*", "", "", "", False, ""),
    ("", "07b", "Chi phí vật liệu quản lý", "", "6422*", "", "", "", False, ""),
    ("", "07c", "Chi phí ĐTLS CCDC", "", "6423*", "", "", "", False, ""),
    ("", "07d", "Chi phí KH TSCĐ", "", "6424*", "", "", "", False, ""),
    ("10", "08", "Lợi nhuận thuần từ HĐKD", "", "", "", "=01-02-03+04-05-06-07", "", True, ""),
    (
        "11",
        "09",
        "Thu nhập khác",
        "",
        "",
        "7111*,7112*,7113*,7114*,7115*,7117*,7118*",
        "",
        "",
        False,
        "",
    ),
    ("12", "10", "Chi phí khác", "", "8111*,8112*,8113*,8118*", "", "", "", False, ""),
    ("13", "11", "Lợi nhuận khác", "", "", "", "=09-10", "", False, ""),
    ("14", "12", "Tổng lợi nhuận kế toán trước thuế", "", "", "", "=08+11", "", True, ""),
    ("15", "13", "Chi phí thuế TNDN", "", "8211*,8212*", "", "", "", False, ""),
    ("16", "14", "Lợi nhuận sau thuế TNDN", "", "", "", "=12-13", "", True, ""),
    ("17", "15", "Lãi cơ bản trên cổ phiếu (VND)", "", "", "", "", "", False, ""),
]

B03_DIRECT = [
    # Direct method cash flow: ma_so 01-10
    # Each data line aggregates the cash leg (TK 111*/112*) but only for
    # vouchers whose counterpart (offset) line hits the account pattern in
    # ``tk_doi_ung``.  This produces a DIFFERENT value per line instead of
    # the identical meaningless value the old shared ``111*,112*`` pattern
    # produced.
    #
    # Direction convention:
    #   - Inflow lines  (01, 04, 07): use tk_no_pattern (sum cash DEBIT)
    #   - Outflow lines (02, 02a, 02b, 05, 05a, 08, 08a):
    #                    use tk_co_pattern (sum cash CREDIT)
    #
    # Tuple format: (stt, ma_so, chi_tieu, thuyet_minh, tk_no, tk_co,
    #                 cong_thuc, tinh_giam_tru, is_header, parent,
    #                 tk_doi_ung)
    ("I", "", "Dòng tiền từ HĐKD", "", "", "", "", "", True, "", ""),
    # 01 inflow: cash received from customers
    (
        "1",
        "01",
        "Tiền thu từ khách hàng, người mua",
        "",
        "111*,112*",
        "",
        "",
        "",
        False,
        "",
        "511*,131*",
    ),
    # 02 outflow: cash paid to suppliers
    (
        "2",
        "02",
        "Tiền trả cho người cung cấp",
        "",
        "",
        "111*,112*",
        "",
        "",
        False,
        "",
        "531*,331*,152*,156*",
    ),
    # 02a outflow: cash paid to employees
    (
        "3",
        "02a",
        "Tiền trả cho cán bộ công nhân viên",
        "",
        "",
        "111*,112*",
        "",
        "",
        False,
        "",
        "334*",
    ),
    # 02b outflow: tax and other payments
    (
        "4",
        "02b",
        "Tiền nộp thuế và các khoản khác",
        "",
        "",
        "111*,112*",
        "",
        "",
        False,
        "",
        "3334*,3331*,821*",
    ),
    ("5", "03", "Tiền thuần từ HĐKD", "", "", "", "=01-02-02a-02b", "", True, "", ""),
    ("II", "", "Dòng tiền từ HĐ đầu tư", "", "", "", "", "", True, "", ""),
    # 04 inflow: cash from asset disposal
    (
        "6",
        "04",
        "Tiền thu từ thanh lý, nhượng bán TS",
        "",
        "111*,112*",
        "",
        "",
        "",
        False,
        "",
        "211*,212*,213*,711*",
    ),
    # 05 outflow: cash paid to buy fixed assets
    (
        "7",
        "05",
        "Tiền chi mua sắm, xây dựng TS dài hạn",
        "",
        "",
        "111*,112*",
        "",
        "",
        False,
        "",
        "211*,212*,213*,241*",
    ),
    # 05a outflow: cash lent / invested in securities
    (
        "8",
        "05a",
        "Tiền cho vay, đầu tư chứng khoán",
        "",
        "",
        "111*,112*",
        "",
        "",
        False,
        "",
        "121*,228*",
    ),
    ("9", "06", "Tiền thuần từ HĐ đầu tư", "", "", "", "=04-05-05a", "", True, "", ""),
    ("III", "", "Dòng tiền từ HĐ tài chính", "", "", "", "", "", True, "", ""),
    # 07 inflow: cash from borrowing / issuing shares
    (
        "10",
        "07",
        "Tiền thu từ đi vay, phát hành TP",
        "",
        "111*,112*",
        "",
        "",
        "",
        False,
        "",
        "341*,411*",
    ),
    # 08 outflow: cash paid to repay loans / return capital
    (
        "11",
        "08",
        "Tiền trả nợ vay, trả vốn góp",
        "",
        "",
        "111*,112*",
        "",
        "",
        False,
        "",
        "341*,411*",
    ),
    # 08a outflow: cash paid for dividends / profit distribution
    (
        "12",
        "08a",
        "Tiền trả cổ tức, lợi nhuận",
        "",
        "",
        "111*,112*",
        "",
        "",
        False,
        "",
        "421*,3531*",
    ),
    ("13", "09", "Tiền thuần từ HĐ tài chính", "", "", "", "=07-08-08a", "", True, "", ""),
    ("", "10", "Tăng/giảm tiền thuần trong kỳ", "", "", "", "=03+06+09", "", True, "", ""),
    ("", "10a", "Tiền đầu kỳ", "", "", "", "", "", False, "", ""),
    ("", "10b", "Tiền cuối kỳ", "", "", "", "=10+10a", "", True, "", ""),
]

B03_INDIRECT = [
    # Indirect method cash flow: ma_so 01-10
    ("I", "", "Dòng tiền từ HĐKD", "", "", "", "", "", True, ""),
    ("1", "01", "Lợi nhuận trước thuế", "", "", "", "", "", False, ""),
    ("2", "02", "Điều chỉnh do KH TSCĐ, BĐSĐT", "", "214*", "", "", "", False, ""),
    ("", "02a", "Điều chỉnh dự phòng giảm giá", "", "229*,159*", "", "", "", False, ""),
    ("3", "03", "Tăng giảm khoản phải thu", "", "131*", "", "", "", False, ""),
    ("4", "04", "Tăng giảm hàng tồn kho", "", "152*", "", "", "", False, ""),
    ("5", "05", "Tăng giảm chi phí trả trước", "", "242*", "", "", "", False, ""),
    ("6", "06", "Tăng giảm khoản phải trả", "", "", "331*", "", "", False, ""),
    ("", "06a", "Tăng giảm chi phí phải trả", "", "", "3351*", "", "", False, ""),
    ("7", "07", "Tiền thuần từ HĐKD", "", "", "", "=01+02+02a-03-04-05+06+06a", "", True, ""),
    ("II", "", "Dòng tiền từ HĐ đầu tư", "", "", "", "", "", True, ""),
    ("8", "08", "Chi mua TS dài hạn", "", "211*", "", "", "", False, ""),
    ("", "08a", "Thu thanh lý TS dài hạn", "", "211*", "", "", "", False, ""),
    ("", "08b", "Cho vay, thu hồi nợ", "", "1288*", "", "", "", False, ""),
    ("III", "", "Dòng tiền từ HĐ tài chính", "", "", "", "", "", True, ""),
    ("9", "09", "Dòng tiền từ HĐ tài chính", "", "", "341*,411*", "", "", False, ""),
    ("", "09a", "Tiền đi vay", "", "", "3411*", "", "", False, ""),
    ("", "09b", "Tiền trả nợ vay", "", "3411*", "", "", "", False, ""),
    ("", "10", "Tăng/giảm tiền thuần trong kỳ", "", "", "", "=07+08+08a+09", "", True, ""),
    ("", "10a", "Tiền đầu kỳ", "", "", "", "", "", False, ""),
    ("", "10b", "Tiền cuối kỳ", "", "", "", "=10+10a", "", True, ""),
]


def _build_rows(report_type: str, data: list) -> list[dict]:
    """Convert raw tuple data into FinancialReportLine field dicts.

    Tuple format (10 or 11 elements):
        (stt, ma_so, chi_tieu, thuyet_minh, tk_no, tk_co,
         cong_thuc, tinh_giam_tru, is_header, parent [, tk_doi_ung])

    The optional 11th element ``tk_doi_ung`` sets the
    ``tk_doi_ung_pattern`` field (counterpart account pattern for the
    cash-flow direct method).  Older tuples without it default to ``""``.
    """
    rows = []
    for idx, item in enumerate(data):
        (
            stt,
            ma_so,
            chi_tieu,
            thuyet_minh,
            tk_no,
            tk_co,
            cong_thuc,
            giam_tru,
            is_header,
            parent,
        ) = item[:10]
        tk_doi_ung = item[10] if len(item) > 10 else ""
        rows.append(
            {
                "report_type": report_type,
                "stt": stt,
                "ma_so": ma_so,
                "chi_tieu": chi_tieu,
                "thuyet_minh": thuyet_minh,
                "tk_no_pattern": tk_no,
                "tk_co_pattern": tk_co,
                "cong_thuc": cong_thuc,
                "tinh_giam_tru": giam_tru,
                "is_header": is_header,
                "parent_ma_so": parent,
                "tk_doi_ung_pattern": tk_doi_ung,
                "display_order": idx,
            }
        )
    return rows


class Command(BaseCommand):
    help = "Seed FinancialReportLine config rows for B01-DN, B02-DN, B03-DN direct/indirect."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing rows before seeding.",
        )

    def handle(self, *args, **options):
        if options.get("reset"):
            FinancialReportLine.objects.all().delete()
            self.stdout.write("Cleared existing FinancialReportLine rows.")

        all_rows: list[dict] = []
        all_rows.extend(_build_rows("B01-DN", B01_DN))
        all_rows.extend(_build_rows("B02-DN", B02_DN))
        all_rows.extend(_build_rows("B03-DN-direct", B03_DIRECT))
        all_rows.extend(_build_rows("B03-DN-indirect", B03_INDIRECT))

        created = 0
        updated = 0
        for row in all_rows:
            _, was_created = FinancialReportLine.objects.update_or_create(
                report_type=row["report_type"],
                display_order=row["display_order"],
                defaults=row,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        counts = {}
        for rt, _ in FinancialReportLine.REPORT_TYPES:
            counts[rt] = FinancialReportLine.objects.filter(report_type=rt).count()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(all_rows)} financial report lines "
                f"({created} new, {updated} updated).\n"
                f"  B01-DN: {counts.get('B01-DN', 0)}\n"
                f"  B02-DN: {counts.get('B02-DN', 0)}\n"
                f"  B03-DN-direct: {counts.get('B03-DN-direct', 0)}\n"
                f"  B03-DN-indirect: {counts.get('B03-DN-indirect', 0)}"
            )
        )
