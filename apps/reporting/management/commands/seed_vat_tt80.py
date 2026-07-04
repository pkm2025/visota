"""Seed ``VATReportLine`` rows for the TT80/2021 VAT return (01/GTGT).

The TT80/2021 form 01/GTGT layout:

    Section A — Thông tin chung
        Pure header; no data lines on the engine side.

    Section B-I — Hàng hóa, dịch vụ mua vào (input VAT)
        [21] Số thuế GTGT của HHDV mua vào phát sinh trong kỳ (TK 1331 Nợ)
        [22] Tổng thuế GTGT đầu vào phát sinh trong kỳ             = [21]
        [23] Thuế GTGT HHDV mua vào không được khấu trừ             (group 6)
        [24] Thuế GTGT đầu vào được khấu trừ kỳ này                 = [22] - [23]
        [25] Thuế GTGT đầu vào được khấu trừ (hỗ trợ)               = [24]
        [26] Thuế GTGT đầu vào của HHDV dùng chung cho đối tượng
             chịu thuế và không chịu thuế (phân bổ)
        [27] Thuế GTGT đầu vào đã kê khai, nộp thừa kỳ trước chuyển sang

    Section B-II — Hàng hóa, dịch vụ bán ra (output VAT)
        [28] Tổng thuế GTGT của HHDV bán ra/chịu thuế (TK 33311 Có)
        [29] Doanh số HHDV bán ra không chịu thuế / thuế suất 0%   (rate 00)
        [30] Doanh số HHDV bán ra chịu thuế suất 5%               (rate 05)
        [31] Thuế GTGT của HHDV bán ra chịu thuế suất 5%           = [30] * 5%
        [32] Doanh số HHDV bán ra chịu thuế suất 10%              (rate 10)
        [33] Thuế GTGT của HHDV bán ra chịu thuế suất 10%          = [32] * 10%

    Section C — Thuế GTGT còn phải nộp / còn được khấu trừ
        [40] THUẾ GTGT CÒN PHẢI NỘP = [28] - ([25] + [26] - [27])  when output > input
        [42] THUẾ GTGT CÒN ĐƯỢC KHẤU TRỪ KỲ SAU (input - output)   when input > output

The engine computes [40]/[42] as a formula of [28] and the input-net;
the view layers the conditional rendering (payable vs. credit).

Idempotent: rows are matched on ``line_code`` via ``update_or_create``.
"""

from django.core.management.base import BaseCommand

from apps.reporting.models import VATReportLine

# (line_code, section, stt, chi_tieu, tk_filter, invoice_group_filter,
#  tax_code_filter, amount_field, cong_thuc, is_header)
_TT80_LINES = [
    # --- Section A: header only -----------------------------------------
    ("A", "A", "A", "THÔNG TIN CHUNG", "", "", "", "tax_amount_vnd", "", True),
    # --- Section B-I: input VAT (TK 1331, group #4 INPUT) --------------
    ("B-I", "B-I", "I", "HÀNG HÓA, DỊCH VỤ MUA VÀO", "", "", "", "tax_amount_vnd", "", True),
    (
        "21",
        "B-I",
        "1",
        "Số thuế GTGT của HHDV mua vào phát sinh trong kỳ (TK 1331 Nợ)",
        "1331*",
        "4",
        "",
        "tax_amount_vnd",
        "",
        False,
    ),
    (
        "22",
        "B-I",
        "2",
        "Tổng thuế GTGT đầu vào phát sinh trong kỳ",
        "1331*",
        "4",
        "",
        "tax_amount_vnd",
        "",
        False,
    ),
    (
        "23",
        "B-I",
        "2a",
        "Thuế GTGT HHDV mua vào không được khấu trừ (group #6 / KT)",
        "1331*",
        "6",
        "KT",
        "tax_amount_vnd",
        "",
        False,
    ),
    (
        "24",
        "B-I",
        "3",
        "Thuế GTGT đầu vào được khấu trừ kỳ này",
        "",
        "",
        "",
        "tax_amount_vnd",
        "[22]-[23]",
        False,
    ),
    (
        "25",
        "B-I",
        "4",
        "Thuế GTGT đầu vào được khấu trừ (kỳ này)",
        "",
        "",
        "",
        "tax_amount_vnd",
        "[24]",
        False,
    ),
    (
        "26",
        "B-I",
        "5",
        "Thuế GTGT đầu vào của HHDV dùng chung (phân bổ)",
        "",
        "",
        "",
        "tax_amount_vnd",
        "",
        False,
    ),
    (
        "27",
        "B-I",
        "6",
        "Thuế GTGT đầu vào đã kê khai, nộp thừa kỳ trước chuyển sang",
        "",
        "",
        "",
        "tax_amount_vnd",
        "",
        False,
    ),
    # --- Section B-II: output VAT (TK 33311, group #5 OUTPUT) ----------
    ("B-II", "B-II", "II", "HÀNG HÓA, DỊCH VỤ BÁN RA", "", "", "", "tax_amount_vnd", "", True),
    (
        "28",
        "B-II",
        "7",
        "Tổng thuế GTGT của HHDV bán ra phát sinh trong kỳ (TK 33311 Có)",
        "33311*",
        "5",
        "",
        "tax_amount_vnd",
        "",
        False,
    ),
    (
        "29",
        "B-II",
        "8",
        "Doanh số HHDV bán ra không chịu thuế / thuế suất 0%",
        "511*",
        "5",
        "00",
        "goods_amount_vnd",
        "",
        False,
    ),
    (
        "30",
        "B-II",
        "9",
        "Doanh số HHDV bán ra chịu thuế suất 5%",
        "511*",
        "5",
        "05",
        "goods_amount_vnd",
        "",
        False,
    ),
    (
        "31",
        "B-II",
        "10",
        "Thuế GTGT của HHDV bán ra chịu thuế suất 5%",
        "33311*",
        "5",
        "05",
        "tax_amount_vnd",
        "",
        False,
    ),
    (
        "32",
        "B-II",
        "11",
        "Doanh số HHDV bán ra chịu thuế suất 10%",
        "511*",
        "5",
        "10",
        "goods_amount_vnd",
        "",
        False,
    ),
    (
        "33",
        "B-II",
        "12",
        "Thuế GTGT của HHDV bán ra chịu thuế suất 10%",
        "33311*",
        "5",
        "10",
        "tax_amount_vnd",
        "",
        False,
    ),
    # --- Section C: payable / credit ------------------------------------
    ("C", "C", "C", "THUẾ GTGT CÒN PHẢI NỘP / KHẤU TRỪ", "", "", "", "tax_amount_vnd", "", True),
    (
        "40",
        "C",
        "13",
        "THUẾ GTGT CÒN PHẢI NỘP TRONG KỲ (= [28] - ([25]+[26]-[27]))",
        "",
        "",
        "",
        "tax_amount_vnd",
        "[28]-[25]-[26]+[27]",
        False,
    ),
    (
        "42",
        "C",
        "14",
        "THUẾ GTGT CÒN ĐƯỢC KHẤU TRỪ KỲ SAU (= [25]+[26]-[27]-[28])",
        "",
        "",
        "",
        "tax_amount_vnd",
        "[25]+[26]-[27]-[28]",
        False,
    ),
]


class Command(BaseCommand):
    help = "Seed VATReportLine rows for the TT80/2021 VAT return (01/GTGT)."

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for order, row in enumerate(_TT80_LINES, start=1):
            (
                line_code,
                section,
                stt,
                chi_tieu,
                tk_filter,
                group_filter,
                tax_filter,
                amount_field,
                cong_thuc,
                is_header,
            ) = row
            _, was_created = VATReportLine.objects.update_or_create(
                line_code=line_code,
                defaults={
                    "section": section,
                    "stt": stt,
                    "chi_tieu": chi_tieu,
                    "tk_filter": tk_filter,
                    "invoice_group_filter": group_filter,
                    "tax_code_filter": tax_filter,
                    "amount_field": amount_field,
                    "cong_thuc": cong_thuc,
                    "is_header": is_header,
                    "display_order": order,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        total = VATReportLine.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f"seed_vat_tt80: created={created} updated={updated} total={total}")
        )
