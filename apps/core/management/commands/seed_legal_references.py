"""Seed Vietnamese legal references for compliance tracking."""

from datetime import date

from django.core.management.base import BaseCommand

from apps.core.models import LegalReference

LEGAL_REFS = [
    {"code": "BLLD2019", "name": "Bộ luật Lao động 2019", "full_name": "Bộ luật Lao động số 45/2019/QH14", "issuing_body": "Quốc hội", "issue_date": "2019-11-20", "effective_date": "2021-01-01", "applicable_to": ["hr"], "summary": "Bộ luật Lao động — quy định quan hệ lao động, hợp đồng, tiền lương, BHXH."},
    {"code": "TT133", "name": "TT133/2016", "full_name": "Thông tư 133/2016/TT-BTC - Chế độ kế toán DN nhỏ và vừa", "issuing_body": "Bộ Tài chính", "issue_date": "2016-08-01", "effective_date": "2017-01-01", "applicable_to": ["accounting"], "summary": "Chế độ kế toán doanh nghiệp nhỏ và vừa."},
    {"code": "TT99", "name": "TT99/2025", "full_name": "Thông tư 99/2025/TT-BTC - Chế độ kế toán DN (thay TT200)", "issuing_body": "Bộ Tài chính", "issue_date": "2025-09-15", "effective_date": "2026-01-01", "applicable_to": ["accounting"], "summary": "Chế độ kế toán doanh nghiệp mới thay thế TT200/2014."},
    {"code": "TT32", "name": "TT32/2025", "full_name": "Thông tư 32/2025/TT-BTC - Hóa đơn điện tử (thay TT78)", "issuing_body": "Bộ Tài chính", "issue_date": "2025-05-15", "effective_date": "2025-06-01", "applicable_to": ["e-invoice"], "summary": "Hóa đơn điện tử khởi tạo từ máy tính tiền, thay thế TT78/2021."},
    {"code": "TT80", "name": "TT80/2021", "full_name": "Thông tư 80/2021/TT-BTC - Tờ khai thuế GTGT", "issuing_body": "Bộ Tài chính", "issue_date": "2021-09-29", "effective_date": "2022-01-01", "applicable_to": ["tax"], "summary": "Ban hành mẫu tờ khai thuế GTGT (01/GTGT)."},
    {"code": "LuatBHXH2024", "name": "Luật BHXH 41/2024", "full_name": "Luật Bảo hiểm xã hội số 41/2024/QH15", "issuing_body": "Quốc hội", "issue_date": "2024-06-29", "effective_date": "2025-07-01", "applicable_to": ["hr"], "summary": "Luật Bảo hiểm xã hội thay thế Luật 14/2006."},
    {"code": "LuatBHYT2024", "name": "Luật BHYT 51/2024", "full_name": "Luật sửa đổi BHYT số 51/2024/QH15", "issuing_body": "Quốc hội", "issue_date": "2024-11-29", "effective_date": "2025-07-01", "applicable_to": ["hr"], "summary": "Sửa đổi, bổ sung Luật Bảo hiểm y tế 25/2008."},
    {"code": "LuatViecLam2025", "name": "Luật Việc làm 74/2025", "full_name": "Luật Việc làm số 74/2025/QH15", "issuing_body": "Quốc hội", "issue_date": "2025-06-16", "effective_date": "2025-07-01", "applicable_to": ["hr"], "summary": "Luật Việc làm thay thế Luật 38/2013."},
    {"code": "ND74", "name": "ND 74/2024", "full_name": "Nghị định 74/2024/NĐ-CP - Lương tối thiểu vùng", "issuing_body": "Chính phủ", "issue_date": "2024-12-31", "effective_date": "2025-07-01", "applicable_to": ["hr"], "summary": "Quy định mức lương tối thiểu vùng áp dụng từ 01/07/2025."},
    {"code": "ND73", "name": "ND 73/2024", "full_name": "Nghị định 73/2024/NĐ-CP - Lương cơ sở 2.340.000đ", "issuing_body": "Chính phủ", "issue_date": "2024-06-26", "effective_date": "2024-07-01", "applicable_to": ["hr"], "summary": "Mức lương cơ sở dùng để tính BHXH/BHYT/BHTN: 2.340.000đ/tháng."},
    {"code": "TT111", "name": "TT 111/2013", "full_name": "Thông tư 111/2013/TT-BTC - Thuế TNCN", "issuing_body": "Bộ Tài chính", "issue_date": "2013-08-15", "effective_date": "2013-10-01", "applicable_to": ["tax"], "summary": "Hướng dẫn LUẬT Thuế TNCN, giảm trừ gia cảnh."},
    {"code": "ND145", "name": "ND 145/2018", "full_name": "Nghị định 145/2018/NĐ-CP - Kinh phí công đoàn", "issuing_body": "Chính phủ", "issue_date": "2018-10-22", "effective_date": "2019-01-01", "applicable_to": ["hr"], "summary": "Quy định chi tiết Luật CĐVN về kinh phí công đoàn 2%."},
    {"code": "ND123", "name": "ND 123/2020", "full_name": "Nghị định 123/2020/NĐ-CP - Hóa đơn, chứng từ", "issuing_body": "Chính phủ", "issue_date": "2020-09-23", "effective_date": "2022-07-01", "applicable_to": ["e-invoice"], "summary": "Hóa đơn, chứng từ điện tử — thay thế NĐ 51/2010."},
    {"code": "LuatKT", "name": "Luật Kế toán 88/2015", "full_name": "Luật Kế toán số 88/2015/QH13", "issuing_body": "Quốc hội", "issue_date": "2015-11-20", "effective_date": "2017-01-01", "applicable_to": ["accounting"], "summary": "Luật Kế toán thay thế Luật 03/2003."},
    {"code": "LuatThueTNDN", "name": "Luật Thuế TNDN", "full_name": "Luật Thuế thu nhập doanh nghiệp số 14/2008/QH12 (sửa đổi 2022)", "issuing_body": "Quốc hội", "issue_date": "2008-06-03", "effective_date": "2009-01-01", "applicable_to": ["tax"], "summary": "Thuế TNDN, thuế suất 20%."},
]


class Command(BaseCommand):
    help = "Seed Vietnamese legal references (TT133, TT99, TT32, BLLĐ, BHXH, ...) into DB."

    def handle(self, *args, **options):
        created_count = 0
        for ref in LEGAL_REFS:
            issue_date = date.fromisoformat(ref["issue_date"])
            effective_date = date.fromisoformat(ref["effective_date"])
            _, created = LegalReference.objects.update_or_create(
                code=ref["code"],
                defaults={
                    "name": ref["name"],
                    "full_name": ref["full_name"],
                    "issuing_body": ref["issuing_body"],
                    "issue_date": issue_date,
                    "effective_date": effective_date,
                    "applicable_to": ref["applicable_to"],
                    "summary": ref.get("summary", ""),
                    "status": "active",
                },
            )
            if created:
                created_count += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(LEGAL_REFS)} legal references ({created_count} new)."
            )
        )
