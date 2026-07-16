"""Static Vietnamese regulation text used by ``seed_pkm_regulations``.

The content here mirrors the mission ``library/`` reference files so the
seeded ``PKMDocument`` records are self-contained (no filesystem dependency
on the mission directory at runtime). Each entry is a tuple of
``(slug, title, markdown_body)``.

Keeping the bodies as plain markdown keeps them parseable by the existing
``doc_parser.extract_text`` path (the ``.md`` extension is supported) and
keeps chunks semantically meaningful for downstream RAG retrieval.
"""

from __future__ import annotations

TT58_REFERENCE_BODY = """\
# Thông tư 58/2026/TT-BTC — Chế độ kế toán Doanh nghiệp siêu nhỏ (DNSN)

Thông tư 58/2026/TT-BTC thay thế Thông tư 132/2018/TT-BTC.
Hiệu lực: 01/07/2026.
Áp dụng cho: Doanh nghiệp siêu nhỏ (DNSN), hộ kinh doanh, cá nhân kinh doanh (tự nguyện).

## Tiêu chí Doanh nghiệp siêu nhỏ
- Không quá 10 lao động tham gia BHXH bình quân năm.
- VÀ đáp ứng 1 trong 2: tổng nguồn vốn <= 3 tỷ HOẶC doanh thu <= 3 tỷ
  (sản xuất/xây dựng) / <= 10 tỷ (thương mại/dịch vụ).

## 4 Nhóm phương pháp nộp thuế
- Nhóm 1: GTGT tỷ lệ % trên doanh thu, TNDN tỷ lệ % trên doanh thu, sổ S1-DNSN.
- Nhóm 2: GTGT tỷ lệ % trên doanh thu, TNDN tính thuế, sổ S2a/S2b/S2c/S2d-DNSN.
- Nhóm 3: GTGT khấu trừ, TNDN tỷ lệ % trên doanh thu, sổ S3a/S3b-DNSN.
- Nhóm 4: GTGT khấu trừ, TNDN tính thuế, sổ S2b/S2c/S2d/S3b-DNSN.

## Sổ kế toán chính
- S1-DNSN: Sổ doanh thu bán hàng hóa, dịch vụ (Nhóm 1).
- S2a-DNSN: Sổ doanh thu bán hàng hóa, dịch vụ (Nhóm 2).
- S2b-DNSN: Sổ chi tiết doanh thu, chi phí (Nhóm 2, 4).
- S2c-DNSN: Sổ chi tiết vật liệu, dụng cụ, sản phẩm, hàng hóa (Nhóm 2, 4).
- S2d-DNSN: Sổ chi tiết tiền (Nhóm 2, 4).
- S3a-DNSN: Sổ doanh thu bán hàng hóa, dịch vụ (Nhóm 3).
- S3b-DNSN: Sổ theo dõi nghĩa vụ thuế GTGT (Nhóm 3, 4).

## Báo cáo tài chính DNSN
- B01-DNSN: Báo cáo tình hình tài chính (bắt buộc cho Nhóm 2, 4).
- B02-DNSN: Báo cáo kết quả hoạt động kinh doanh (bắt buộc cho Nhóm 2, 4).
- Nhóm 1, 3 (TNDN tỷ lệ %): Không bắt buộc lập BCTC nộp cơ quan thuế.

## Điểm mới so với TT132
- Bổ sung hộ kinh doanh, cá nhân kinh doanh (tự nguyện áp dụng).
- Không bắt buộc bố trí kế toán trưởng — người phụ trách kế toán được ký thay.
- Cho phép người thân làm kế toán (cha mẹ, vợ chồng, con cái, anh chị em ruột).
- Bỏ hệ thống tài khoản Nợ/Có — ghi sổ trực tiếp.
- Sổ kế toán thiết kế theo phương pháp nộp thuế — 4 nhóm.
- Đồng bộ hóa đơn điện tử — cơ quan thuế hỗ trợ xác định số thuế phải nộp.
"""

REGULATORY_RATES_BODY = """\
# Biểu thuế và mức trích đóng hiện hành (tháng 7/2026)

## Thuế TNCN (PIT) — Hiệu lực 01/07/2026
- Giảm trừ gia cảnh bản thân: 15.500.000 VND/tháng (NQ 110/2025 + ND 253/2026).
- Giảm trừ người phụ thuộc: 6.200.000 VND/NPT/tháng.
- Biểu thuế lũy tiến 5 bậc (Luật 09/2026/QH16):
  + Bậc 1: 5% cho thu nhập chịu thuế đến 5 triệu.
  + Bậc 2: 10% cho thu nhập 5-10 triệu.
  + Bậc 3: 20% cho thu nhập 10-18 triệu.
  + Bậc 4: 30% cho thu nhập 18-32 triệu.
  + Bậc 5: 35% trên 32 triệu.
- Các khoản không chịu thuế (ND 253/2026 + TT 87/2026):
  + Tiền ăn ca: 1.200.000 VND/tháng.
  + Bảo hiểm tự nguyện/BH sự mạng: 3.000.000 VND/tháng.
  + Y tế: 23.000.000 VND/năm.
  + Giáo dục: 24.000.000 VND/năm.
  + Ngưỡng thu nhập NPT: 3.000.000 VND/tháng.
  + Ngưỡng khấu trừ tại nguồn: 5.000.000 VND/lần thanh toán.

## BHXH — Hiệu lực 01/07/2026 (ND 161/2026)
- Lương cơ sở: 2.530.000 VND/tháng.
- Trần đóng BHXH (20x lương cơ sở): 50.600.000 VND/tháng.
- Người sử dụng lao động đóng: 21,5% (BHXH 17% + BHYT 3% + BHTN 1% + BHTNLĐ-BNN 0,5%).
- Người lao động đóng: 10,5% (BHXH 8% + BHYT 1,5% + BHTN 1%).

## Thuế TNDN (CIT) — Hiệu lực 01/01/2026
- Doanh thu <= 1 tỷ VND/năm: 0% (miễn, ND 141/2026).
- Doanh thu <= 3 tỷ (siêu nhỏ): 15% (Luật 67/2025 + ND 320/2025).
- Doanh thu 3-50 tỷ (nhỏ): 17%.
- Doanh thu > 50 tỷ: 20%.

## Thuế GTGT (VAT) — Luật GTGT 09/2026
- Thuế suất tiêu chuẩn: 10%.
- Thuế suất giảm (tạm thời): 8% đến 31/12/2026 (ND 174/2025).
- Ngưỡng miễn thuế: doanh thu <= 1 tỷ VND/năm (bao gồm cả mốc 1 tỷ).
- Ngưỡng hoàn thuế: thuế GTGT đầu vào >= 300 triệu VND.

## Lương tối thiểu vùng — Hiệu lực 01/01/2026 (ND 293/2025)
- Vùng I: 5.310.000 VND/tháng (25.600 VND/giờ).
- Vùng II: 4.720.000 VND/tháng (22.700 VND/giờ).
- Vùng III: 4.120.000 VND/tháng (19.900 VND/giờ).
- Vùng IV: 3.700.000 VND/tháng (17.800 VND/giờ).
"""

TT133_CHART_OVERVIEW_BODY = """\
# Thông tư 133/2016/TT-BTC — Chế độ kế toán doanh nghiệp nhỏ và vừa

Tổng quan hệ thống tài khoản và sổ sách kế toán áp dụng cho doanh nghiệp
nhỏ và vừa (TT133/2016, hiệu lực từ 01/01/2017).

## Hệ thống tài khoản chính (trích)
- Loại 1: Tài sản ngắn hạn (Tiền, Đầu tư TC ngắn hạn, Phải thu, Hàng tồn kho).
- Loại 2: Tài sản dài hạn (TSCĐ, BĐS đầu tư, Đầu tư TC dài hạn).
- Loại 3: Nợ phải trả (Phải trả người bán, Thuế, Vay nợ, Quỹ).
- Loại 4: Vốn chủ sở hữu (Vốn góp, LNST chưa PP, Quỹ принадлежит CSH).
- Loại 5: Doanh thu (Doanh thu bán hàng & CC DV).
- Loại 6: Chi phí (Giá vốn, Chi phí bán hàng, Chi phí QLDN).
- Loại 7: Thu nhập khác.
- Loại 8: Chi phí khác.
- Loại 9: Xác định kết quả kinh doanh (TK 911).

## Sổ kế toán áp dụng
- Nhật ký chung (phương pháp chủ yếu).
- Kèm theo sổ cái, sổ quỹ, sổ ngân hàng, sổ chi tiết các TK.
- Báo cáo tài chính: B01-DN (Bảng CĐKT), B02-DN (KQHĐKD), B03-DN (LCTT),
  Thuyết minh BCTC.

## Khác biệt chính với TT200
- Ít tài khoản hơn (tập hợp các TK chi tiết thành TK tổng hợp).
- Không bắt buộc lập sổ chi tiết cho mọi TK.
- Phù hợp DN nhỏ và vừa, hoạt động đơn giản.
"""

ND254_EINVOICE_BODY = """\
# Nghị định 254/2026/NĐ-CP — Hóa đơn, chứng từ điện tử

Khung pháp lý mới về hóa đơn điện tử thay thế ND 123/2020 và ND 78.
Hiệu lực: 01/07/2026. Hướng dẫn bởi Thông tư 91/2026/TT-BTC.

## Phân loại hóa đơn điện tử
- Hóa đơn có mã của cơ quan thuế (CQT): Hóa đơn do CQT cấp mã trước khi
  người bán gửi cho người mua.
- Hóa đơn không có mã: Người bán lập và gửi cho người mua, không qua CQT.
- Hóa đơn khởi tạo từ máy tính tiền: Phát sinh từ hệ thống POS, có thể
  có mã hoặc không có mã.

## Đối tượng bắt buộc sử dụng
- Doanh nghiệp, tổ chức kinh tế.
- Hộ kinh doanh có doanh thu > 1 tỷ VND/năm bắt buộc dùng HĐĐT có mã CQT
  và kê khai thuế theo phương pháp kê khai (theo TT 50/2026/TT-BTC).
- Hộ kinh doanh có doanh thu <= 1 tỷ VND/năm được miễn HĐĐT (ND 141/2026).

## Quy trình cơ bản
1. Người bán lập hóa đơn điện tử.
2. Truyền hóa đơn cho người mua và CQT (theo quy định của từng loại).
3. CQT xử lý, cấp mã (với loại có mã) và lưu trữ dữ liệu.
4. Người mua nhận hóa đơn và sử dụng để kê khai, khấu trừ thuế.

## Xử lý hóa đơn sai
- Hóa đơn đã lập sai khi chưa gửi cho người mua: Lập lại hóa đơn mới.
- Hóa đơn đã gửi cho người mua: Lập hóa đơn điều chỉnh (tăng/giảm) hoặc
  hóa đơn thay thế theo quy định tại TT 91/2026/TT-BTC.

## Luật liên quan
- Luật Quản lý thuế 108/2025/QH15 (hiệu lực 01/07/2026).
- Luật Thuế GTGT 09/2026/QH16.
"""

#: Registry of regulation documents to seed.
#: Each entry: (slug, title, body_markdown).
REGULATION_DOCUMENTS: list[tuple[str, str, str]] = [
    ("tt58-2026", "TT58/2026/TT-BTC — Chế độ kế toán DNSN", TT58_REFERENCE_BODY),
    ("regulatory-rates-2026", "Biểu thuế PIT/BHXH/CIT/VAT — tháng 7/2026", REGULATORY_RATES_BODY),
    (
        "tt133-chart-overview",
        "TT133/2016 — Tổng quan hệ thống tài khoản DN nhỏ và vừa",
        TT133_CHART_OVERVIEW_BODY,
    ),
    ("nd254-einvoice", "NĐ 254/2026 — Hóa đơn điện tử (cơ bản)", ND254_EINVOICE_BODY),
]

__all__ = ["REGULATION_DOCUMENTS"]
