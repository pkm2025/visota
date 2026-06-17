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
    # --- New 2025/2026 tax & SME regulations ---
    # Tax rates
    {"code": "LuatTNDN2025", "name": "Luật Thuế TNDN 2025", "full_name": "Luật Thuế thu nhập doanh nghiệp số 67/2025/QH15", "issuing_body": "Quốc hội", "issue_date": "2025-06-13", "effective_date": "2026-01-01", "url": "https://luatvietnam.vn/thue/luat-thue-thu-nhap-doanh-nghiep-2025-so-67-2025-qh15-404386-d1.html", "summary": "Thuế suất TNDN mới: 15% (DN ≤3 tỷ DT), 17% (DN 3-50 tỷ), 20% (chuẩn). Áp dụng ưu đãi miễn/giảm cho DN nhỏ vừa mới thành lập.", "applicable_to": ["tax"]},
    {"code": "ND174", "name": "ND 174/2025", "full_name": "Nghị định 174/2025/NĐ-CP - Giảm thuế GTGT 8% (giảm 2%)", "issuing_body": "Chính phủ", "issue_date": "2025-06-30", "effective_date": "2025-07-01", "expiry_date": "2026-12-31", "url": "https://thuvienphapluat.vn/ma-so-thue/phap-luat-thue/toan-van-nghi-dinh-1742025ndcp-ve-giam-thue-gtgt-2-den-het-2026-theo-nghi-quyet-2042025qh15-206993.html", "summary": "Giảm thuế GTGT từ 10% xuống 8% cho hầu hết HHDV từ 01/07/2025 đến 31/12/2026. Không áp dụng cho viễn thông, tài chính, ngân hàng, kim loại, hóa chất, HHDV chịu TTĐB.", "applicable_to": ["tax"]},
    {"code": "ND82", "name": "ND 82/2025", "full_name": "Nghị định 82/2025/NĐ-CP - Gia hạn nộp thuế GTGT, TNDN, tiền thuê đất 2025", "issuing_body": "Chính phủ", "issue_date": "2025-04-02", "effective_date": "2025-04-02", "expiry_date": "2025-12-31", "url": "https://luatvietnam.vn/dat-dai/nghi-dinh-82-2025-nd-cp-gia-han-thoi-han-nop-thue-va-tien-thue-dat-trong-nam-2025-396148-d1.html", "summary": "Gia hạn thuế GTGT 5-6 tháng, TNDN tạm nộp 5 tháng, tiền thuê đất 6 tháng cho DN.", "applicable_to": ["tax"]},
    {"code": "NQ204", "name": "NQ 204/2025", "full_name": "Nghị quyết 204/2025/QH15 - Giảm thuế GTGT", "issuing_body": "Quốc hội", "issue_date": "2025-06-26", "effective_date": "2025-07-01", "url": "", "summary": "Cơ sở pháp lý cho ND 174/2025 giảm thuế GTGT 8%.", "applicable_to": ["tax"]},
    # SME classification
    {"code": "ND80", "name": "ND 80/2021", "full_name": "Nghị định 80/2021/NĐ-CP - Tiêu chí xác định doanh nghiệp nhỏ và vừa", "issuing_body": "Chính phủ", "issue_date": "2021-08-26", "effective_date": "2021-10-10", "url": "https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Nghi-dinh-80-2021-ND-CP-huong-dan-Luat-Ho-tro-doanh-nghiep-nho-va-vua-486147.aspx", "summary": "3 loại: siêu nhỏ (DT<3 tỷ hoặc vốn<3 tỷ), nhỏ (DT 3-50 tỷ hoặc vốn 3-20 tỷ), vừa (DT 50-200 tỷ hoặc vốn 20-100 tỷ). Tiêu chí theo ngành nghề: Nông-Lâm-Thủy sản/Công nghiệp-Xây dựng vs Thương mại-Dịch vụ.", "applicable_to": ["sme"]},
    {"code": "LuatHTDN", "name": "Luật Hỗ trợ DN nhỏ vừa", "full_name": "Luật Hỗ trợ doanh nghiệp nhỏ và vừa số 04/2017/QH14", "issuing_body": "Quốc hội", "issue_date": "2017-06-12", "effective_date": "2018-01-01", "url": "https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Luat-Ho-tro-doanh-nghiep-nho-va-vua-04-2017-QH14-325109.aspx", "summary": "Khung pháp lý hỗ trợ SME: tín dụng, thuế, đất đai, công nghệ, thị trường.", "applicable_to": ["sme"]},
    # PIT changes
    {"code": "LuatTNCN2025", "name": "Luật Thuế TNCN 2025", "full_name": "Luật Thuế thu nhập cá nhân (sửa đổi) — dự thảo đang trình Quốc hội", "issuing_body": "Quốc hội", "issue_date": "2025-01-01", "effective_date": "2026-01-01", "url": "", "summary": "Đề xuất tăng giảm trừ gia cảnh, điều chỉnh biểu thuế lũy tiến. Theo dõi cập nhật.", "applicable_to": ["tax", "hr"]},
    # Other relevant
    {"code": "ND20", "name": "ND 20/2026", "full_name": "Nghị định 20/2026/NĐ-CP - Ưu đãi thuế TNDN (triển khai NQ 198/2025/QH15)", "issuing_body": "Chính phủ", "issue_date": "2026-01-15", "effective_date": "2026-02-01", "url": "", "summary": "Miễn thuế TNDN 3 năm cho DN nhỏ/vừa mới thành lập. Giảm 50% trong 4 năm tiếp theo cho startup đổi mới sáng tạo.", "applicable_to": ["tax", "sme"]},
    # --- Comprehensive VN tax type additions (v1.4.0) ---
    # Thuế Tiêu thụ Đặc biệt (TTĐB)
    {"code": "LuatTTDB2025", "name": "Luật TTĐB 2025", "full_name": "Luật Thuế tiêu thụ đặc biệt số 66/2025/QH15 (sửa đổi)", "issuing_body": "Quốc hội", "issue_date": "2025-06-14", "effective_date": "2026-01-01", "url": "https://luatvietnam.vn/thue-phi-le-phi/diem-moi-cua-luat-thue-tieu-thu-dac-biet-565-98391-article.html", "summary": "TTĐB mới: rượu ≥20° 65%→90% (2031), bia 65%→90%, thuốc lá 75% + thuế tuyệt đối 5.000đ/bao, xe hybrid ưu đãi 70%. Phương pháp hỗn hợp (tỷ lệ + tuyệt đối).", "applicable_to": ["tax"]},
    # Thuế Môn bài
    {"code": "ND22", "name": "ND 22/2020", "full_name": "Nghị định 22/2020/NĐ-CP - Lệ phí môn bài", "issuing_body": "Chính phủ", "issue_date": "2020-02-24", "effective_date": "2020-04-10", "url": "https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Nghi-dinh-22-2020-ND-CP-thue-mon-bai-374936.aspx", "summary": "DN vốn >10 tỷ: 3 triệu/năm. DN vốn ≤10 tỷ: 2 triệu/năm. Chi nhánh: 1 triệu. Hạn nộp: 30/01 hàng năm.", "applicable_to": ["tax"]},
    # Lệ phí trước bạ
    {"code": "LuatTruocBa", "name": "Luật Phí trước bạ", "full_name": "Nghị định 10/2022/NĐ-CP - Lệ phí trước bạ", "issuing_body": "Chính phủ", "issue_date": "2022-01-16", "effective_date": "2022-03-01", "url": "", "summary": "Nhà/đất/ô tô <9 chỗ: 0.5%. Tài sản khác: 1%. ND 50/2026 điều chỉnh tiền sử dụng đất.", "applicable_to": ["tax"]},
    # Thuế tài nguyên
    {"code": "LuatTaiNguyen", "name": "Luật Thuế tài nguyên", "full_name": "Luật Thuế tài nguyên số 38/2009/QH12", "issuing_body": "Quốc hội", "issue_date": "2009-06-17", "effective_date": "2010-01-01", "url": "", "summary": "Thuế gián thu đánh trên sản lượng tài nguyên khai thác × giá tính thuế × thuế suất theo từng loại khoáng sản.", "applicable_to": ["tax"]},
    # Thuế bảo vệ môi trường
    {"code": "LuatBVMT", "name": "Luật Thuế BVMT", "full_name": "Luật Thuế bảo vệ môi trường số 57/2010/QH12", "issuing_body": "Quốc hội", "issue_date": "2010-11-15", "effective_date": "2011-01-01", "url": "", "summary": "Áp cho xăng dầu, than, HCFC, túi nilon, thuốc trừ sâu. Thuế = SL × giá tính thuế.", "applicable_to": ["tax"]},
    # Thuế sử dụng đất nông nghiệp
    {"code": "LuatSDNN", "name": "Luật Thuế SD đất NN", "full_name": "Luật Thuế sử dụng đất nông nghiệp số 50/2010/QH12", "issuing_body": "Quốc hội", "issue_date": "2010-11-23", "effective_date": "2011-01-01", "url": "", "summary": "Nghị quyết 216/2025: miễn đến 31/12/2030. Chuyển NN sang ở: quy định mới từ 1/1/2026.", "applicable_to": ["tax"]},
    # Thuế nhà thầu
    {"code": "TT20", "name": "TT 20/2026", "full_name": "Thông tư 20/2026/TT-BTC - Thuế nhà thầu (thay TT 103/2014)", "issuing_body": "Bộ Tài chính", "issue_date": "2026-02-12", "effective_date": "2026-03-12", "url": "", "summary": "Thuế nhà thầu: TNDN thường 5%, kết hợp VAT có thể 15% tổng. DT tính = toàn bộ DT nhà thầu trước khi trừ thuế.", "applicable_to": ["tax"]},
    # Thuế chuyển nhượng vốn
    {"code": "ND320", "name": "ND 320/2025", "full_name": "Nghị định 320/2025/NĐ-CP - Chuyển nhượng vốn", "issuing_body": "Chính phủ", "issue_date": "2025-12-15", "effective_date": "2026-01-01", "url": "", "summary": "Chuyển nhượng vốn TNHH: 20%. Tái cơ cấu nội bộ: miễn nếu không đổi công ty mẹ. TT 20/2026 hướng dẫn chi tiết.", "applicable_to": ["tax"]},
    # Luật GTGT mới
    {"code": "LuatGTGT2026", "name": "Luật GTGT 2026", "full_name": "Luật Thuế giá trị gia tăng (sửa đổi) theo Luật số 09/2026/QH16", "issuing_body": "Quốc hội", "issue_date": "2026-04-24", "effective_date": "2026-01-01", "url": "https://thuvienphapluat.vn/phap-luat/ho-tro-phap-luat/luat-thue-gia-tri-gia-tang-moi-nhat-2026-va-cac-nghi-dinh-thong-tu-huong-dan-moi-nhat-hien-nay-398530-248988.html", "summary": "Bãi bỏ ngưỡng 500 triệu. Xe 10-16 chỗ: 2%→7% (2031). Hoàn thuế nếu đầu vào ≥300 triệu (cho HH 5%). Miễn thuế DN DT <1 tỷ.", "applicable_to": ["tax"]},
    # --- PIT deduction history (Luật TNCN qua các thời kỳ) ---
    {"code": "LuatTNCN2007", "name": "Luật TNCN 04/2007", "full_name": "Luật Thuế TNCN số 04/2007/QH12 (đã bãi bỏ)", "issuing_body": "Quốc hội", "issue_date": "2007-11-21", "effective_date": "2009-01-01", "expiry_date": "2013-06-30", "url": "", "status": "superseded", "summary": "GTGC 4 triệu/tháng, NPT 1.6 triệu. 7 bậc 5-35%.", "applicable_to": ["tax", "hr"]},
    {"code": "LuatTNCN2012", "name": "Luật TNCN 26/2012", "full_name": "Luật sửa đổi Luật TNCN số 26/2012/QH13", "issuing_body": "Quốc hội", "issue_date": "2012-11-22", "effective_date": "2013-07-01", "expiry_date": "2020-06-30", "url": "", "status": "superseded", "summary": "GTGC tăng lên 9 triệu/tháng, NPT 3.6 triệu. 7 bậc.", "applicable_to": ["tax", "hr"]},
    {"code": "NQ954", "name": "NQ 954/2020", "full_name": "Nghị quyết 954/2020/NQ-UBTVQH14 — điều chỉnh GTGC", "issuing_body": "Ủy ban Thường vụ Quốc hội", "issue_date": "2020-06-02", "effective_date": "2020-07-01", "url": "", "summary": "GTGC tăng từ 9 lên 11 triệu/tháng, NPT từ 3.6 lên 4.4 triệu. Hiệu lực đến 30/06/2026.", "applicable_to": ["tax", "hr"]},
    {"code": "NQ110", "name": "NQ 110/2025", "full_name": "Nghị quyết 110/2025/NQ-UBTVQH15 — GTGC 15.5 triệu", "issuing_body": "Ủy ban Thường vụ Quốc hội", "issue_date": "2025-11-14", "effective_date": "2026-07-01", "url": "", "summary": "GTGC tăng lên 15.5 triệu/tháng (186 triệu/năm), NPT 6.2 triệu. Biểu thuế rút gọn còn 5 bậc.", "applicable_to": ["tax", "hr"]},
    # --- Bidding Law (Luật Đấu thầu) ---
    {"code": "LuatDauThau2023", "name": "Luật Đấu thầu 2023", "full_name": "Luật Đấu thầu số 22/2023/QH15", "issuing_body": "Quốc hội", "issue_date": "2023-06-23", "effective_date": "2024-01-01", "url": "https://thuvienphapluat.vn/van-ban/Dau-tu/Luat-Dau-thau-2023-22-2023-QH15-518805.aspx", "summary": "10 chương 96 điều. 8 loại HĐ (trọn gói, đơn giá cố định, đơn giá điều chỉnh, thời gian, khung, quản lý dự án, tư vấn, khác). Bảo lãnh 10-30%. Tạm ứng ≤30%. Thanh toán theo nghiệm thu.", "applicable_to": ["contracts"]},
    {"code": "ND24", "name": "ND 24/2024", "full_name": "Nghị định 24/2024/NĐ-CP - Hướng dẫn Luật Đấu thầu", "issuing_body": "Chính phủ", "issue_date": "2024-02-27", "effective_date": "2024-04-01", "url": "https://luatvietnam.vn/linh-vuc-khac/tong-hop-nghi-dinh-huong-dan-luat-dau-thau-cap-nhat-moi-nhat-883-105096-article.html", "summary": "Hướng dẫn chi tiết lựa chọn nhà thầu theo Luật 22/2023. Bao gồm quy định về hợp đồng, bảo lãnh, tạm ứng.", "applicable_to": ["contracts"]},
    {"code": "TT02BXD", "name": "TT 02/2023/TT-BXD", "full_name": "Thông tư 02/2023/TT-BXD - Mẫu hợp đồng xây dựng", "issuing_body": "Bộ Xây dựng", "issue_date": "2023-06-30", "effective_date": "2023-08-01", "url": "", "summary": "Ban hành mẫu HĐ thi công xây dựng, HĐ tư vấn, HĐ cung cấp hàng hóa theo Luật Đấu thầu 2023.", "applicable_to": ["contracts"]},
]


class Command(BaseCommand):
    help = "Seed Vietnamese legal references (TT133, TT99, TT32, BLLĐ, BHXH, ...) into DB."

    def handle(self, *args, **options):
        created_count = 0
        for ref in LEGAL_REFS:
            issue_date = date.fromisoformat(ref["issue_date"])
            effective_date = date.fromisoformat(ref["effective_date"])
            expiry_date = (
                date.fromisoformat(ref["expiry_date"])
                if ref.get("expiry_date")
                else None
            )
            _, created = LegalReference.objects.update_or_create(
                code=ref["code"],
                defaults={
                    "name": ref["name"],
                    "full_name": ref["full_name"],
                    "issuing_body": ref["issuing_body"],
                    "issue_date": issue_date,
                    "effective_date": effective_date,
                    "expiry_date": expiry_date,
                    "applicable_to": ref["applicable_to"],
                    "summary": ref.get("summary", ""),
                    "url": ref.get("url", ""),
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
