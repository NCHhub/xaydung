# Web phụ X.aladDin.vn — Hải & Cộng sự

Trang giới thiệu dịch vụ **xây dựng & sửa chữa nhà ở** dành cho **ACE môi giới** và **chủ nhà**.
Nền tảng: **GitHub Pages + Jekyll** — tự động hoàn toàn bằng lệnh, không cần bấm web.

## 0983.601.366 — Hải & Cộng sự

---

## Cách thêm bài viết mới (tự động bằng lệnh)

### 1. Bài viết (cho môi giới / chủ nhà)

Tạo 1 file Markdown trong thư mục **`_blog/`**:

```markdown
---
title: "Tiêu đề bài viết"
nhom: "Dành cho Môi giới"        # hoặc "Dành cho Chủ nhà"
date: 2026-09-01
description: "Mô tả ngắn hiện trên danh sách."
image: "/assets/img/bai-viet/ten-anh.jpg"   # (tùy chọn) ảnh bìa
---

Nội dung bài viết viết bằng Markdown. Ảnh trong bài:
![Mô tả ảnh](/assets/img/bai-viet/ten-anh.jpg)
```

### 2. Công trình (portfolio)

Tạo file Markdown trong thư mục **`_portfolio/`** với `loai` và `dia_diem`:

```markdown
---
title: "Tên công trình"
loai: "Nhà phố"
dia_diem: "Khu vực"
date: 2026-09-01
description: "Mô tả ngắn."
image: "/assets/img/cong-trinh/ten-anh.jpg"
---

Nội dung mô tả công trình.
```

### 3. Đưa ảnh vào

Đặt ảnh vào thư mục **`assets/img/`** (chia thư mục con: `bai-viet/`, `cong-trinh/`).

### 4. Đăng lên web

```bash
git add -A
git commit -m "Thêm bài: <tên bài>"
git push
```

GitHub tự build và đăng trong 1-2 phút. Không cần cài gì.

---

## Cấu trúc thư mục

```
xaydung/
├── _config.yml          ← cấu hình trung tâm (url, collections)
├── index.html           ← trang chủ
├── _layouts/            ← khung giao diện
├── _includes/           ← đầu trang, chân trang, thẻ head
├── _blog/               ← các bài viết (Môi giới / Chủ nhà)
├── _portfolio/          ← các công trình thi công
├── bai-viet/            ← trang danh sách bài viết
├── cong-trinh/          ← trang danh sách công trình
├── assets/
│   ├── css/style.css    ← toàn bộ giao diện
│   └── img/             ← ảnh bài viết & công trình
└── CNAME                ← tên miền X.aladDin.vn
```

---

## Bản ghi DNS (đã thêm từ pavietnam)

- Loại: **CNAME**
- Tên: **xaydung**
- Giá trị: **NCHhub.github.io**
- TTL: 3600

## Liên hệ

- Điện thoại: **0983.601.366**
- Email: nch@aladdin.vn