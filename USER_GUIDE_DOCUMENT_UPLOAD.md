# 📚 HƯỚNG DẪN UPLOAD TÀI LIỆU - Document Upload Guide

**Phiên bản**: 1.0  
**Ngày**: May 6, 2026  
**Dành cho**: Tất cả người dùng  

---

## 🎯 Phạm Vi Truy Cập (Access Scope) là gì?

**Phạm vi truy cập** xác định những **ai có thể xem** tài liệu của bạn:

### 🏢 **Toàn Công Ty (Company-wide)**
- **Ai có thể xem?** Mọi người trong công ty
- **Khi nào dùng?** 
  - Chính sách công ty
  - Thông báo chung
  - Tài liệu công khai
- **Ví dụ**: "Chính sách làm việc từ nhà", "Lịch công ty 2024"

### 👥 **Phòng Ban (Department)**
- **Ai có thể xem?** Chỉ những người trong phòng ban của bạn
- **Khi nào dùng?** 
  - Báo cáo phòng ban
  - Kế hoạch nội bộ
  - Tài liệu nhóm
- **Ví dụ**: "Báo cáo Q1 của phòng Sales", "Kế hoạch dự án"

### 🔒 **Cá Nhân (Personal)**
- **Ai có thể xem?** Chỉ bạn
- **Khi nào dùng?** 
  - Bản nháp cá nhân
  - Ghi chú riêng tư
  - Tài liệu chưa hoàn tất
- **Ví dụ**: "Bản nháp báo cáo", "Ý tưởng cá nhân"

---

## 📤 Các Bước Upload Tài Liệu

### Bước 1: Mở Modal Upload

![Button](Nhấn nút **⬆️ Upload** ở góc phải màn hình)

### Bước 2: Chọn File

```
┌─────────────────────────────────┐
│ Chọn File *                     │
│ ┌─────────────────────────────┐ │
│ │ 🤖 Kéo thả file vào đây     │ │
│ │    hoặc nhấn để chọn        │ │
│ │                             │ │
│ │ Hỗ trợ: PDF, DOCX, TXT,    │ │
│ │ MD, XLSX - tối đa 100MB     │ │
│ └─────────────────────────────┘ │
└─────────────────────────────────┘
```

**Hỗ trợ các định dạng**:
- 📄 PDF (Portable Document Format)
- 📝 DOCX / DOC (Microsoft Word)
- 📋 XLSX / XLS (Microsoft Excel)
- 📑 TXT (Text)
- 📖 MD (Markdown)

**Giới hạn**: Max 100 MB

### Bước 3: Chọn Phạm Vi Truy Cập

```
Phạm vi truy cập
┌────────────────────────────────┐
│ ▼ Toàn công ty                 │
├────────────────────────────────┤
│ • Toàn công ty                 │
│ • Phòng ban                    │
│ • Cá nhân                      │
└────────────────────────────────┘

🏢 Mọi người trong công ty có thể xem tài liệu này
```

**Tùy chọn dựa trên vai trò của bạn**:
- 👨‍💼 **Admin**: Có thể chọn tất cả 3 phạm vi
- 👔 **Trưởng phòng**: Có thể chọn "Toàn công ty", "Phòng ban", "Cá nhân"
- 👤 **Nhân viên**: Chỉ có thể chọn "Cá nhân"

### Bước 4: (Nếu chọn "Phòng Ban") Chọn Phòng Ban

⚠️ **Bắt buộc** khi access_scope = "Phòng ban":

```
┌──────────────────────────────────────────────┐
│ Phòng ban * (Bắt buộc)                       │
│ ┌──────────────────────────────────────────┐ │
│ │ ▼ -- Chọn phòng ban --                   │ │
│ ├──────────────────────────────────────────┤ │
│ │ Finance (Tài chính)                      │ │
│ │ Sales (Bán hàng)                         │ │
│ │ HR (Nhân sự)                             │ │
│ └──────────────────────────────────────────┘ │
│ 👥 Tài liệu sẽ chỉ có thể truy cập bởi      │
│    những người trong phòng ban này           │
└──────────────────────────────────────────────┘
```

### Bước 5: (Tùy chọn) Chọn Thư Mục

Tài liệu sẽ được lưu vào thư mục được chọn:

```
Thư mục (Tùy chọn)
┌──────────────────────────────────────┐
│ ▼ -- Không chọn (Gốc) --             │
├──────────────────────────────────────┤
│ Finance                              │
│   ↳ 2024                             │
│   ↳ 2023                             │
│ Sales                                │
│   ↳ Q1 Reports                       │
│   ↳ Campaigns                        │
└──────────────────────────────────────┘

ℹ️ Phạm vi truy cập sẽ kế thừa từ thư mục
   (👥 phòng ban)
```

**Quy tắc**: 
- ✅ Nếu chọn thư mục personal → phạm vi sẽ là "Cá nhân"
- ✅ Nếu chọn thư mục phòng ban → phạm vi sẽ là "Phòng ban"
- ✅ Nếu chọn thư mục công ty → phạm vi sẽ là "Toàn công ty"

### Bước 6: (Tùy chọn) Thêm Mô Tả

```
Mô tả
┌────────────────────────────────────────┐
│ Nhập mô tả tài liệu...                 │
│                                        │
│ Báo cáo tài chính quý I 2024           │
│                                        │
└────────────────────────────────────────┘
```

**Ví dụ**:
- "Báo cáo tài chính Q1 2024 - Kinh doanh bất động sản"
- "Hợp đồng nhân sự - Mẫu 2024"
- "Slide thuyết trình lãnh đạo"

### Bước 7: (Tùy chọn) Thêm Tags

```
Tags (phân cách bằng dấu phẩy)
┌────────────────────────────────────────┐
│ vd: quy trình, kỹ thuật, 2024          │
│                                        │
│ báo cáo, tài chính, Q1, 2024           │
│                                        │
└────────────────────────────────────────┘
```

**Ví dụ**: 
- `báo cáo, tài chính, quý 1`
- `hợp đồng, nhân sự, 2024`
- `nội quy, chính sách, công ty`

**Lợi ích**: Giúp tìm kiếm nhanh hơn sau này

### Bước 8: Upload

```
┌──────────────────────────┐
│ Đang upload: 45%         │
│ ████████░░░░░░░░░░░░    │
└──────────────────────────┘
```

Chờ cho đến khi upload hoàn tất ✅

---

## ⚠️ Thông Báo Lỗi Phổ Biến

### ❌ "Tài liệu trong personal folder phải có access_scope='personal'"

**Nguyên nhân**: Bạn đang cố upload tài liệu vào **personal folder** nhưng chọn phạm vi **"Toàn công ty"** hoặc **"Phòng ban"**

**Giải pháp**:
1. Chọn thư mục công ty hoặc phòng ban thay vì personal folder
2. Hoặc chọn phạm vi "Cá nhân"

### ❌ "Tài liệu trong department folder không thể là company-wide"

**Nguyên nhân**: Bạn chọn **department folder** nhưng lại chọn phạm vi **"Toàn công ty"**

**Giải pháp**:
1. Chọn phạm vi "Phòng ban"
2. Hoặc chọn company folder thay vì department folder

### ❌ "Vui lòng chọn phòng ban cho tài liệu department-scoped"

**Nguyên nhân**: Bạn chọn phạm vi **"Phòng ban"** nhưng **không chọn phòng ban**

**Giải pháp**: 
1. Chọn phòng ban từ dropdown

### ❌ "File quá lớn. Tối đa 100MB"

**Nguyên nhân**: File của bạn lớn hơn 100MB

**Giải pháp**:
1. Nén file (tối ưu hóa kích thước)
2. Hoặc chia nhỏ file thành nhiều phần

---

## 💡 Mẹo & Thủ Thuật

### 💾 Lưu File Draft

```
1. Chọn access_scope = "Cá nhân"
2. Thêm tags: "draft", "nháp"
3. Upload
   → Chỉ bạn thấy được
   → Có thể sửa sau
```

### 🏢 Share Với Cả Công Ty

```
1. Chọn access_scope = "Toàn công ty"
2. Viết mô tả rõ ràng
3. Thêm tags để dễ tìm
4. Upload
   → Mọi người có thể tìm thấy
```

### 👥 Share Với Phòng Ban

```
1. Chọn access_scope = "Phòng ban"
2. Chọn phòng ban của bạn
3. (Optional) Chọn folder của phòng ban
4. Upload
   → Chỉ phòng ban thấy được
```

### 🔍 Dễ Tìm Kiếm Sau

```
Tags tốt:
✅ "báo cáo, tài chính, 2024, Q1"
✅ "hợp đồng, khách hàng, VN"
✅ "nội quy, chính sách, mới"

Không tốt:
❌ "file1"
❌ "tài liệu"
❌ "báo cáo"
```

---

## 📱 Quy Trình So Sánh: OneDrive vs Hệ Thống Này

| Bước | OneDrive | Hệ Thống Hiện Tại | Khác Biệt |
|------|----------|-----------------|----------|
| 1. Chọn file | Upload file | Upload file | ✅ Giống |
| 2. Chọn folder | Click folder | Chọn dropdown | Cách thức khác |
| 3. Sharing | Set after upload | Trước upload | ✅ Sớm hơn |
| 4. Phạm vi | "Anyone" / "Org" | Company / Dept / Personal | ✅ Chi tiết hơn |
| 5. Department | Không có | Có tuỳ chọn | 🆕 Tính năng mới |

---

## ❓ FAQ

### Q: Sau upload xong có thể thay đổi phạm vi không?

A: Hiện tại hãy liên hệ admin để thay đổi. Trong tương lai sẽ có tính năng chỉnh sửa.

### Q: Phòng ban không xuất hiện trong dropdown?

A: Bạn chưa được gán vào phòng ban đó. Liên hệ admin.

### Q: Có thể share riêng lẻ với từng người không?

A: Hiện tại hỗ trợ: Công ty / Phòng ban / Cá nhân. Chi tiết sẽ bổ sung sau.

### Q: Upload bị lỗi, cách khắc phục?

A: 
1. Kiểm tra kích thước file (< 100MB)
2. Kiểm tra định dạng file (PDF, DOCX, ...)
3. Kiểm tra phạm vi + folder tương thích
4. Thử upload lại

### Q: File đã upload mất đi?

A: Files ở trạng thái `pending` (xử lý) có thể mất tạm thời. Chờ vài phút hoặc reload page.

---

## 🎓 Workflow Examples

### Ví Dụ 1: Upload Báo Cáo Tài Chính (Trưởng Phòng Finance)

```
1. File: "BaoCAO_TaiChinh_Q1_2024.xlsx"
2. Phạm vi: "Phòng ban"
3. Phòng ban: "Finance"
4. Thư mục: "Finance > 2024 > Q1"
5. Mô tả: "Báo cáo tài chính quý I năm 2024"
6. Tags: "báo cáo, tài chính, Q1, 2024"
7. Upload ✅

Kết quả: Chỉ phòng Finance thấy được
```

### Ví Dụ 2: Upload Chính Sách Công Ty (Admin)

```
1. File: "ChinhSach_LamViec_2024.pdf"
2. Phạm vi: "Toàn công ty"
3. Phòng ban: (Không cần)
4. Thư mục: "Chính sách"
5. Mô tả: "Chính sách làm việc từ nhà 2024"
6. Tags: "nội quy, chính sách, 2024"
7. Upload ✅

Kết quả: Mọi người trong công ty thấy được
```

### Ví Dụ 3: Upload Bản Nháp Cá Nhân (Nhân Viên Bất Kỳ)

```
1. File: "BanNhap_Bai_Viet.docx"
2. Phạm vi: "Cá nhân"
3. Phòng ban: (Không cần)
4. Thư mục: (Không cần)
5. Mô tả: "Bản nháp bài viết quản lý dự án"
6. Tags: "draft, nháp, cá nhân"
7. Upload ✅

Kết quả: Chỉ bạn thấy được (bảo mật)
```

---

## 📞 Support

Nếu gặp vấn đề:
1. Xem lại **Thông Báo Lỗi** phía trên
2. Xem **FAQ**
3. Liên hệ Admin / IT Support

---

**Chúc bạn upload tài liệu thành công! 🎉**

