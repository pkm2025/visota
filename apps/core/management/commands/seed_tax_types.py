"""Seed comprehensive Vietnamese tax types.

Adds 14 tax types covering direct/indirect taxes and fees:
VAT, CIT, PIT, TTĐB, XNK (imp/exp), môn bài, trước bạ, tài nguyên,
BVMT, SD đất NN, nhà thầu, chuyển nhượng vốn, lợi tức vốn.
"""

from datetime import date

from django.core.management.base import BaseCommand

from apps.core.models import TaxType

# (code, name, category, current_rate_text, legal_basis)
TAX_TYPES = [
    (
        "VAT",
        "Thuế Giá trị gia tăng (GTGT)",
        "indirect",
        "10% (đang giảm 8% đến 31/12/2026)",
        "Luật GTGT 2026 + ND 174/2025",
    ),
    (
        "CIT",
        "Thuế Thu nhập doanh nghiệp (TNDN)",
        "direct",
        "15% (DT≤3 tỷ), 17% (3-50 tỷ), 20% (chuẩn)",
        "Luật TNDN 2025",
    ),
    (
        "PIT",
        "Thuế Thu nhập cá nhân (TNCN)",
        "direct",
        "Lũy tiến 5-35% (7 bậc), GTGC 11M + 4.4M/NPT",
        "TT 111/2013 + Luật 09/2026",
    ),
    (
        "SCT",
        "Thuế Tiêu thụ đặc biệt (TTĐB)",
        "indirect",
        "Rượu≥20° 65→90%, bia 65→90%, thuốc lá 75%+5Kđ/bao",
        "Luật TTĐB 66/2025",
    ),
    (
        "IMP",
        "Thuế Xuất khẩu",
        "indirect",
        "Theo biểu thuế xuất khẩu",
        "Luật Thuế XNK",
    ),
    (
        "EXP",
        "Thuế Nhập khẩu",
        "indirect",
        "Theo biểu thuế nhập khẩu + MFN + FTA",
        "Luật Thuế XNK",
    ),
    (
        "MB",
        "Lệ phí Môn bài",
        "fee",
        "DN>10 tỷ: 3 triệu/năm, ≤10 tỷ: 2 triệu",
        "ND 22/2020",
    ),
    (
        "RB",
        "Lệ phí Trước bạ",
        "fee",
        "Nhà/đất/ô tô: 0.5%, khác: 1%",
        "ND 10/2022",
    ),
    (
        "NR",
        "Thuế Tài nguyên",
        "indirect",
        "Theo từng loại khoáng sản × sản lượng",
        "Luật 38/2009",
    ),
    (
        "EPT",
        "Thuế Bảo vệ môi trường",
        "indirect",
        "Xăng dầu, than, HCFC, nilon × giá tính thuế",
        "Luật 57/2010",
    ),
    (
        "AL",
        "Thuế Sử dụng đất nông nghiệp",
        "direct",
        "Miễn đến 31/12/2030 (NQ 216/2025)",
        "Luật 50/2010",
    ),
    (
        "FCT",
        "Thuế Nhà thầu",
        "indirect",
        "TNDN 5% + VAT (tổng có thể 15%)",
        "TT 20/2026",
    ),
    (
        "CAP",
        "Thuế Chuyển nhượng vốn",
        "direct",
        "TNHH 20%, tái cơ cấu nội bộ: miễn",
        "ND 320/2025",
    ),
    (
        "LB",
        "Thuế Lợi tức vốn đầu tư nước ngoài",
        "direct",
        "Theo quy định FCT",
        "TT 20/2026",
    ),
]

# English names + descriptions (aligned by code above)
TAX_TYPE_DETAILS = {
    "VAT": (
        "Value Added Tax",
        "Đánh trên giá trị tăng thêm của HHDV trong quá trình lưu thông.",
    ),
    "CIT": (
        "Corporate Income Tax",
        "Đánh trên lợi nhuận ròng của doanh nghiệp (DT - chi phí hợp lý).",
    ),
    "PIT": (
        "Personal Income Tax",
        "Thuế lũy tiến từng phần với thu nhập cá nhân thường trú và không thường trú.",
    ),
    "SCT": (
        "Special Consumption Tax",
        "Đánh tiêu dùng chọn lọc: rượu, bia, thuốc lá, ô tô, bài lá.",
    ),
    "IMP": ("Export Tax", "Đánh trên hàng hóa xuất khẩu theo biểu thuế xuất khẩu."),
    "EXP": (
        "Import Tax",
        "Đánh trên hàng hóa nhập khẩu theo biểu thuế + MFN/FTA ưu đãi.",
    ),
    "MB": ("Business License Fee", "Lệ phí hàng năm dựa trên vốn điều lệ — nộp trước 30/01."),
    "RB": ("Registration Fee", "Lệ phí khi đăng ký tài sản (nhà, đất, ô tô) lần đầu."),
    "NR": ("Natural Resources Tax", "Gián thu đánh trên tài nguyên khai thác."),
    "EPT": ("Environmental Protection Tax", "Đánh trên HHDV gây tác động xấu đến môi trường."),
    "AL": ("Agricultural Land Use Tax", "Đánh trên đất sản xuất NN — đang được miễn đến 2030."),
    "FCT": ("Foreign Contractor Tax", "Thuế áp cho nhà thầu nước ngoài có DT phát sinh tại VN."),
    "CAP": ("Capital Transfer Tax", "Đánh trên chuyển nhượng vốn góp TNHH."),
    "LB": ("Foreign Capital Gains Tax", "Lợi tức vốn đầu tư nước ngoài — quy theo FCT."),
}

# Effective date default
DEFAULT_EFFECTIVE = date(2026, 1, 1)


class Command(BaseCommand):
    help = "Seed 14 Vietnamese tax types (VAT, CIT, PIT, TTĐB, XNK, môn bài, ...) into DB."

    def handle(self, *args, **options):
        created_count = 0
        for code, name, category, rate_text, legal_basis in TAX_TYPES:
            name_en, description = TAX_TYPE_DETAILS.get(code, ("", ""))
            _, created = TaxType.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "name_en": name_en,
                    "category": category,
                    "description": description,
                    "current_rate_text": rate_text,
                    "legal_basis": legal_basis,
                    "effective_date": DEFAULT_EFFECTIVE,
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(TAX_TYPES)} tax types ({created_count} new)."
            )
        )
