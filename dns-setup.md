# DNS SETUP — Aladdin.vn (tạm thời trỏ X — ĐÃ DỰNG XONG 12/09)

## ĐÃ XONG (không cần làm lại)
- Repo GitHub Pages: `NCHhub/aladdin-landing` (branch main, CNAME = aladdin.vn)
- Nội dung: `index.html` = landing CLI + meta refresh 0s → https://x.aladdin.vn/
- GitHub Pages: built, https://aladdin.vn/ (sau khi DNS đổi)

## BƯỚC DUY NHẤT CÒN LẠI — ĐỔI DNS (ở nhà cung cấp tên miền của bạn)

> Nameserver hiện tại: ns1.pavietnam.vn / ns2.pavietnam.vn / nsbak.pavietnam.net → đăng nhập **quản trị DNS PAVIETNAM** (không phải registry).

### 1. XÓA (bản ghi cũ → facebook)
| Name | Type | Value cũ |
|---|---|---|
| @ (aladdin.vn) | A | 112.213.89.38 ❌ |
| www | A | 112.213.89.38 ❌ |

### 2. THÊM (bản ghi mới → GitHub Pages)
| Name | Type | Value | TTL |
|---|---|---|---|
| @ (aladdin.vn) | A | 185.199.108.153 | 300 |
| @ (aladdin.vn) | A | 185.199.109.153 | 300 |
| @ (aladdin.vn) | A | 185.199.110.153 | 300 |
| @ (aladdin.vn) | A | 185.199.111.153 | 300 |
| www | CNAME | aladdin.vn | 300 |

### 3. GIỮ NGUYÊN (đang chạy tốt)
| Name | Type | Value |
|---|---|---|
| x.aladdin.vn | A x4 | 185.199.108~111.153 (GH Pages — web xaydung-site) |
| q.aladdin.vn | A | 185.199.108.153 (mới thêm, chờ nội dung Q) |

## CÁCH LÀM TRÊN PAVIETNAM (từng bước)
1. Đăng nhập **https://pavietnam.vn** (hoặc trang quản trị bạn nhận khi đăng ký domain) với tài khoản chủ tên miền.
2. Vào **Quản lý tên miền → chọn `aladdin.vn` → DNS / Bản ghi DNS / Zone Editor** (có nơi nằm trong **cPanel → Zone Editor** hoặc **DirectAdmin → DNS Management**).
3. **SỬA dòng A:** tên `@` hoặc `aladdin.vn` → bỏ IP `112.213.89.38` → ghi `185.199.108.153`. (Muốn chắc, thêm đủ 4: `.108/.109/.110/.111`)
4. **SỬA dòng www:** nếu có `www` A `112.213.89.38` → đổi thành `www` CNAME `aladdin.vn` (hoặc A `185.199.108.153`).
5. **GIỮ NGUYÊN:** `x.aladdin.vn` (4 A GitHub Pages đang chạy) · `q.aladdin.vn` (thêm nếu chưa: A `185.199.108.153`).
6. Bấm **Save / Apply / Cập nhật** → chờ 5–30 phút.
7. Kiểm tra: `nslookup aladdin.vn` thấy `185.199.108.153` là xong.

## SAU KHI ĐỔI (chờ 5–30 phút lan DNS)
- `aladdin.vn` → hiển thị landing → tự nhảy sang `x.aladdin.vn` (HẾT facebook).
- HTTPS: GitHub tự cấp SSL trong vài giờ → bỏ lỗi 443.

## GỠ "tạm thời" sau này
- Sửa index.html: bỏ dòng `<meta http-equiv="refresh" ...>` → push lên repo aladdin-landing → aladdin.vn thành landing đầy đủ.