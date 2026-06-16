# 00. Tổng quan 13 module chức năng

## 1. Sơ đồ module tổng thể

```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│                    SIS ACCOUNTING ONLINE                              │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
                                   │
       ┌───────────┬───────────────┼───────────────┬─────────────┐
       ▼           ▼               ▼               ▼             ▼
┌─────────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐
│ Module nền │ │ Module │ │ Module  │ │ Module  │ │ Module    │
│ kế toán    │ │ nghiệp │ │ chuyên │ │ báo cáo │ │ hệ thống  │
│ tổng hợp   │ │ vụ    │ │ ngành  │ │         │ │           │
└─────────────┘ └─────────┘ └──────────┘ └──────────┘ └────────────┘
   │              │             │            │             │
   │              │             │            │             │
1.Tổng hợp     3.Bán hàng   5.Tồn kho    11.BCTC       13.Hệ thống
2.Vốn bằng tiền 4.Mua hàng  6.TSCĐ       12.Báo cáo   
                              7.CCDC      thuế         
                              8.Chi phí  
                              9.NS        
                              10.Lương    
```

## 2. Bảng tổng hợp 13 module

| # | Module | Nhóm | Mục đích | Entry points chính |
|---|--------|------|---------|-------------------|
| 1 | **Kế toán tổng hợp** | Nền | Phiếu kế toán, kết chuyển, số dư | Phiếu kế toán, Kết chuyển cuối kỳ |
| 2 | **Vốn bằng tiền** | Nghiệp vụ | Tiền mặt/tg ngân hàng, tạm ứng | Thu/chi tiền mặt, Thu/chi ngân hàng |
| 3 | **Bán hàng** | Nghiệp vụ | Hóa đơn, công nợ khách | Hóa đơn bán hàng, Hóa đơn dịch vụ |
| 4 | **Mua hàng** | Nghiệp vụ | Phiếu nhập mua, công nợ NCC | Phiếu nhập mua, Nhập khẩu |
| 5 | **Tồn kho** | Chuyên ngành | Nhập/xuất/điều chuyển, tính giá | Phiếu nhập kho, Phiếu xuất kho |
| 6 | **Tài sản cố định** | Chuyên ngành | Tăng/giảm TSCĐ, khấu hao | Cập nhật tài sản, Tính khấu hao |
| 7 | **Công cụ dụng cụ** | Chuyên ngành | CCDC, phân bổ chi phí | CCDC, Tính phân bổ |
| 8 | **Chi phí, giá thành** | Chuyên ngành | Giá thành giản đơn | Tính giá thành, Phân xưởng |
| 9 | **Quản lý nhân sự** | Chuyên ngành | Hồ sơ NV, hợp đồng | Hồ sơ nhân viên |
| 10 | **Tiền lương** | Chuyên ngành | Chấm công, ca làm | Chấm công, Lịch nghỉ |
| 11 | **Báo cáo tài chính** | Báo cáo | BCTC theo TT133/TT200 | B01-DN, B02-DN, B03-DN |
| 12 | **Báo cáo thuế** | Báo cáo | Tờ khai GTGT, bảng kê | Tờ khai 01/GTGT TT80 |
| 13 | **Hệ thống** | Hệ thống | User, phân quyền, config | Người sử dụng, Tham số |

## 3. Module 1: Kế toán tổng hợp (General Ledger)

Trục chính của hệ thống. Tất cả nghiệp vụ kế toán đều quy về việc tạo **phiếu kế toán** (voucher) với **bút toán ghi nợ/có** trên các tài khoản.

**Chức năng chính**:
- Phiếu kế toán (Accounting voucher) — lấy danh sách, thêm, sửa, xóa
- Kết chuyển cuối kỳ (Period closing entries) — kết chuyển doanh thu, chi phí
- Phân bổ cuối kỳ (Period allocations) — phân bổ chi phí chờ
- Khai báo kết chuyển cuối kỳ (Closing templates) — template cho auto-closing
- Khóa số liệu (Lock data) — khóa kỳ, không cho sửa
- Đánh lại số chứng từ (Re-sequence voucher numbers)
- Số dư đầu của các tài khoản (Account opening balances)
- Vào số dư ban đầu của các khách hàng (Customer opening balances)
- Vào số dư ban đầu của các hoá đơn (Invoice opening balances)
- Chuyển số dư tài khoản sang năm sau (Year-end carry-forward)

**Hình thức ghi sổ hỗ trợ**:
- Nhật ký chung (General Journal form) — mẫu S03a-DN/DNN
- Chứng từ ghi sổ (Voucher Register form) — mẫu S02a-DN/DNN

**Master data liên quan**:
- Danh mục tài khoản (Chart of Accounts)
- Danh mục loại tài khoản (Account Types)
- Bộ phận hạch toán (Cost centers / Departments)

## 4. Module 2: Vốn bằng tiền (Treasury)

**Chức năng chính**:
- Thu qua ngân hàng (Bank receipt)
- Thu tiền mặt (Cash receipt)
- Chi qua ngân hàng (Bank payment)
- Chi tiền mặt (Cash payment)
- Thanh toán tạm ứng (Advance payment settlement)
- Phân bổ tiền thu cho các HĐ (Allocate received money to contracts)
- Phân bổ tiền trả cho HĐ (Allocate paid money to contracts)

**Master data**:
- Danh mục ngoại tệ (Foreign currencies)
- Danh mục khế ước vay (Loan agreements)
- Tài khoản ngân hàng (Bank accounts)
- Danh mục tỷ giá (Exchange rates)

**Báo cáo**:
- Sổ quỹ tiền mặt (S07-DN, S04a-DNN)
- Sổ kế toán chi tiết quỹ tiền mặt (S07a-DN, S04b-DNN)
- Sổ tiền gửi ngân hàng (S08-DN, S05-DNN)

## 5. Module 3: Bán hàng (Sales)

**Chứng từ**:
- Hóa đơn bán hàng (Sales invoice)
- Hóa đơn bán dịch vụ (Service invoice)
- Hóa đơn xuất khẩu (Export invoice)
- Tính số dư tức thời của khách hàng (Real-time customer balance)

**Hóa đơn điện tử**:
- Khai báo hóa đơn điện tử BKAV (BKAV e-invoice config)
- Cập nhật số hóa đơn (Update invoice numbers)

**Báo cáo**:
- Sổ chi tiết công nợ của một khách hàng
- Bảng cân đối phát sinh công nợ của một tài khoản
- Sổ chi tiết bán hàng (S35-DN, S17-DNN)
- Bảng số dư công nợ (đầu kỳ/cuối kỳ)
- Báo cáo tổng hợp bán hàng
- Sổ chi tiết t/t của khách hàng (S31-DN, S12-DNN)

**Master data**:
- Khách hàng (Customers)
- Nhóm khách hàng (Customer groups)
- Giá bán (Sales prices)
- Nhân viên bán hàng (Sales staff)
- Thuế suất GTGT bán ra (Output VAT rates)
- Nhóm thuế suất GTGT đầu ra (Output VAT rate groups)

## 6. Module 4: Mua hàng (Purchasing)

**Chứng từ**:
- Phiếu nhập mua hàng (Purchase receipt)
- Phiếu nhập dịch vụ (Service receipt)
- Phiếu nhập khẩu (Import receipt)
- Nhập mua xuất thẳng (Direct purchase issue)
- Chi phí mua hàng (Purchase expenses)
- Hóa đơn đầu vào từ TCT (Input invoice from tax authority portal)

**Báo cáo**:
- Tổng hợp hàng nhập mua
- Bảng cân đối phát sinh công nợ của một tài khoản
- Sổ chi tiết công nợ của một nhà cung cấp
- Bảng số dư công nợ (đầu kỳ/cuối kỳ)

**Master data**:
- Nhà cung cấp (Suppliers)
- Nhóm nhà cung cấp (Supplier groups)
- Thuế suất GTGT đầu vào (Input VAT rates)

## 7. Module 5: Tồn kho (Inventory)

**Chứng từ**:
- Phiếu nhập kho (Stock receipt)
- Phiếu xuất kho (Stock issue)
- Phiếu xuất điều chuyển (Stock transfer)

**Tính giá (Costing methods)**:
- Tính giá trung bình tháng (Monthly average)
- Tính giá trung bình di động theo ngày (Moving average daily)
- Tính giá nhập trước xuất trước (FIFO)

**Báo cáo**:
- Tổng hợp nhập xuất tồn (Inventory summary)
- Thẻ kho (S10, 12-DN, S6, S8-DNN)

**Tồn kho đầu kỳ**:
- Vào số tồn kho ban đầu
- Vào chi tiết tồn kho NTXT
- Kết chuyển số tồn kho sang năm sau
- Tính lại số tồn kho tức thời

**Master data**:
- Hàng hóa, vật tư (Goods, materials)
- Nhóm hàng hóa, vật tư (Goods groups)
- Danh mục quy đổi đvt (Unit conversion)
- Danh mục kho (Warehouses)
- Danh mục lô (Lots/batches)

## 8. Module 6: Tài sản cố định (Fixed Assets)

**Chứng từ**:
- Cập nhật tài sản (Asset update)
- Khai báo thay đổi TSCĐ (Asset change declaration)
- Điều chuyển (Transfer)
- Sản lượng (Production volume — cho khấu hao theo sản lượng)
- Tính khấu hao (Calculate depreciation)
- Điều chỉnh khấu hao (Adjust depreciation)
- Khai báo hệ số phân bổ khấu hao (Allocation coefficient)
- Tính khấu hao chi tiết (Detailed depreciation)
- Tạo bút toán chi phí khấu hao (Create depreciation journal entry)

**Báo cáo** (10 mẫu):
- Bảng tính khấu hao TSCĐ (06-TSCĐ)
- Bảng tính khấu hao TSCĐ - chi tiết
- Bảng tính khấu hao TSCĐ theo bpsd
- Bảng tổng hợp khấu hao TSCĐ
- Bảng tổng hợp khấu hao TSCĐ - theo 2 chỉ tiêu
- Bảng kê phân bổ khấu hao TSCĐ
- Bảng kê TSCĐ tăng trong kỳ
- Bảng kê TSCĐ giảm trong kỳ
- Báo cáo tổng hợp tăng giảm TSCĐ
- Bảng cân đối phát sinh TSCĐ

**Master data**:
- Bộ phận sử dụng TSCĐ
- Lý do tăng giảm
- Nguồn vốn
- Loại tài sản, Nhóm tài sản, Phân nhóm tài sản

## 9. Module 7: Công cụ dụng cụ (Tools & Supplies)

Tương tự TSCĐ nhưng cho CCDC (tài khoản 142, 242) — phân bổ thay vì khấu hao.

**Chứng từ**:
- CCDC, Thay đổi CCDC
- Tính phân bổ, Điều chỉnh phân bổ
- Tính khấu hao chi tiết
- Tạo bút toán chi phí khấu hao
- Khai báo hệ số phân bổ khấu hao

**Báo cáo**:
- Bảng tính chi phí CCDC (nhiều variant)
- Bảng kê phân bổ chi phí CCDC
- Bảng kê thông tin chung CCDC
- Bảng kê giá trị CCDC
- Thẻ công cụ, dụng cụ
- Sổ công cụ, dụng cụ
- Sổ theo dõi CCDC tại nơi sử dụng (S22-DN, S10-DNN)
- Bảng kê CCDC tăng/giảm trong kỳ
- Bảng kê CCDC chuyển bộ phận sử dụng
- Bảng cân đối phát sinh CCDC

**Master data**:
- Bộ phận sử dụng
- Nhóm CCDC, Loại CCDC, Phân nhóm CCDC
- Lý do tăng giảm, Nguồn vốn

## 10. Module 8: Chi phí, giá thành (Costing)

Sub-module **Giá thành giản đơn** (simple/process costing) — không thấy có "Giá thành phân bước" hay "Theo đơn đặt hàng" trong demo.

**Chức năng**:
- Tính giá thành (Cost calculation)
- Hệ số sản phẩm (Product coefficient)
- Số dư ban đầu các phân xưởng (Workshop opening balances)
- Dở dang cuối kỳ các phân xưởng (WIP end of period)
- Kết chuyển số dư phân xưởng sang năm sau

**Báo cáo**:
- Bảng giá thành sản phẩm
- Bảng cân đối phát sinh phân xưởng

**Master data**:
- Phân xưởng (Workshops)
- Danh mục tk theo dõi số dư phân xưởng

## 11. Module 9: Quản lý nhân sự (HR)

Module lớn với 19 nghiệp vụ cập nhật số liệu + 4 nhóm báo cáo.

**Chức năng cập nhật số liệu**:
- Hồ sơ nhân viên (Employee profiles) — entity trung tâm
- Quan hệ gia đình, Bằng cấp/chứng chỉ
- Hợp đồng thử việc, Hợp đồng lao động, Phụ lục HĐLĐ
- Quá trình công tác, Quá trình tham gia bảo hiểm
- Giao nhận HS, Điều chuyển NS
- Xếp loại nhân viên, Khen thưởng/kỷ luật
- Nhân viên vi phạm, nghỉ việc
- Nhân viên nuôi con dưới 12 tháng, nghỉ thai sản
- Nhân viên công tác, Danh sách NV gửi lương
- Đề xuất chi phí

**Cấp phát CCDC**:
- Cấp phát công cụ dụng cụ
- Thu hồi, điều chuyển CCDC
- Báo cáo tổng hợp CCDC

**Tuyển dụng, đào tạo**:
- Thông tin tuyển dụng

**Báo cáo**:
- Danh sách CB-NV công ty
- Tổng hợp lao động tăng giảm trong tháng
- Sinh nhật NV, hết hạn HĐLĐ/HĐHV/tròn năm
- Biểu đồ biến động nhân viên theo tháng

**Master data** (rất nhiều dictionary): Bộ phận NS, Chức vụ, Chức danh, Xếp loại LĐ, Bằng cấp, Dân tộc, Tôn giáo, Quốc gia, Tỉnh thành, Phường/xã, Ngoại ngữ, Nơi KCB, v.v.

## 12. Module 10: Tiền lương, chấm công (Payroll)

Lưu ý: chỉ thấy module chấm công, không thấy module tính lương chi tiết trong demo.

**Chấm công**:
- Lịch nghỉ trong năm
- Đăng ký ca làm việc NV
- Ngày nghỉ phép đầu năm
- Định mức nghỉ năm
- Kết chuyển nghỉ phép sang năm sau
- Chấm công (Time keeping)
- Ngày nghỉ, lý do nghỉ
- Đăng ký tăng ca/làm thêm

**Báo cáo**:
- Vào ra chi tiết (Detailed in/out)
- Bảng chấm tổng hợp
- Bảng chấm công chi tiết 1 NV
- Tình hình nghỉ phép
- NV đi muộn về sớm
- Tổng hợp NV làm thêm
- NV đi làm trong ngày
- Tổng hợp công cơm theo tháng

**Master data**:
- Danh mục ca làm việc
- Khai báo ngày công chuẩn
- Danh mục máy chấm công

## 13. Module 11: Báo cáo tài chính (Financial Statements)

**Báo cáo chính (theo TT133)**:
- Bảng cân đối tài khoản (S06-DN, F01-DNN) — Trial Balance
- Báo cáo tình hình tài chính (B01-DN, DNN) — Balance Sheet
- Báo cáo kết quả SXKD (B02-DN, DNN) — P&L
- BC dòng tiền theo PP trực tiếp (B03-DN, DNN) — Cash Flow Direct
- BC dòng tiền theo PP gián tiếp (B03-DN, DNN) — Cash Flow Indirect

## 14. Module 12: Báo cáo thuế (Tax Reports)

**Tờ khai thuế GTGT**:
- Tờ khai thuế 01/GTGT TT80 (theo Thông tư 80/2021)
- Bảng kê đầu ra (Output VAT listing — mẫu 01-1/GTGT)
- Bảng kê đầu vào (Input VAT listing — mẫu 01-2/GTGT)
- Hóa đơn GTGT đầu ra (Output VAT invoices)
- Hóa đơn GTGT đầu vào (Input VAT invoices)

## 15. Module 13: Hệ thống (System Admin)

**Người dùng**:
- Người sử dụng (Users)
- Tham số tùy chọn (System parameters)
- Màn hình chứng từ (Voucher screens config)
- Danh mục quyển chứng từ (Voucher books / number series)
- Trạng thái chứng từ (Voucher statuses)
- Thống kê truy cập của NSD (User access logs)
- Khai báo năm tài chính (Fiscal year setup)

**Danh mục**:
- Danh mục đơn vị (Companies / Tenants)

## 16. Ma trận liên kết module

| Module | Phụ thuộc vào | Được dùng bởi |
|--------|-------------|--------------|
| 1. Kế toán tổng hợp | 13. Hệ thống | Tất cả module khác |
| 2. Vốn bằng tiền | 1, 3, 4 | 11, 12 |
| 3. Bán hàng | 1, 5 | 2, 11, 12 |
| 4. Mua hàng | 1, 5 | 2, 11, 12 |
| 5. Tồn kho | 1 | 3, 4, 8 |
| 6. TSCĐ | 1 | 1 (chi phí khấu hao) |
| 7. CCDC | 1 | 1 (chi phí phân bổ) |
| 8. Chi phí/giá thành | 1, 5, 6, 7, 9 | 11 |
| 9. Quản lý nhân sự | 13 | 10 |
| 10. Tiền lương | 9 | 1, 8 |
| 11. Báo cáo tài chính | 1-10 | - |
| 12. Báo cáo thuế | 1, 3, 4 | - |
| 13. Hệ thống | - | 1-12 |

## 17. Thứ tự triển khai đề xuất

Theo nguyên tắc **foundation-first**:

1. **Phase 1 (nền tảng)**: Module 13 + Module 1 (chart of accounts, vouchers, posting) — ~30% effort
2. **Phase 2 (nghiệp vụ cốt lõi)**: Module 2, 3, 4, 5 — ~30% effort
3. **Phase 3 (chuyên ngành)**: Module 6, 7, 8 — ~15% effort
4. **Phase 4 (nhân sự)**: Module 9, 10 — ~15% effort
5. **Phase 5 (báo cáo & hoàn thiện)**: Module 11, 12 — ~10% effort

Chi tiết xem [09-ke-hoach-trien-khai/01-roadmap.md](../09-ke-hoach-trien-khai/01-roadmap.md).
