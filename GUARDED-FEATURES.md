# 🛡️ GUARDED FEATURES — TÍNH NĂNG GỐC BẤT KHẢ XÂM PHẠM

> **LUẬT CỨNG CỦA DIAMOND (chốt 02-09):** Những tính năng gốc, ngầm, quan trọng của
> **opencode2** và của **web** được **BẢO TOÀN TRONG MỌI TRƯỜNG HỢP**.
> Khi có bất kỳ **xóa bỏ / thay đổi / đổi tên / di chuyển / vô hiệu hóa** nào đụng tới
> chúng → **PHẢI CẢNH BÁO DIAMOND MẠNH MẼ TRƯỚC KHI THỰC HIỆN.**
> Không tự xóa, không tự sửa im lặng, không "thu gọn" nếu chưa được phép.

---

## VÙNG 1 — WEB (index.html, X.aladDin.vn) — "KHUÔN MẶT"

| # | Tính năng gốc | File / vị trí | Vai trò | CẤM |
|---|---|---|---|---|
| W1 | **Bridge JS → OpenCode bộ não** | index.html `DEFAULT_BRIDGE`, `resolveBridge()`, `doAsk()`, `render()` | Kết nối web tới OpenCode trên PC để trả lời AI theo user | Xóa / đổi địa chỉ / tắt không thay thế |
| W2 | **Câu hỏi lớn hero** "Anh/chị đang có căn nhà hay khách hàng nào cần tư vấn?" | index.html tool-section | Định vị môi giới thi công — thấy câu hỏi = biết ngay công cụ cho mình | Đổi câu định vị sang generic |
| W3 | **3 hành động chính** (Tính tiền / Kiểm tra cọc / Nhờ kỹ sư) | index.html `.tool-btn` | Lõi nghiệp vụ môi giới đầu khách mua | Xóa / hạ cấp xuống menu phụ |
| W4 | **Form tính tức thì (client-side <1s)** | index.html `calcNow()`, PRICING | Giá trị nhanh không cần AI, offline vẫn chạy | Xóa logic tính |
| W5 | **Sửa chữa theo hạng mục checkbox** | index.html `c-sua-wrap`, `hm-*` | Chi tiết hóa việc sửa | Xóa |
| W6 | **Checklist trước khi đặt cọc** | index.html `checklist-box`, `checklistNow()` | Phân loại bình thường/hỏi thêm/khảo sát | Xóa |
| W7 | **Báo cáo mang tên môi giới (gửi Zalo)** | index.html `goGuiBaoCao()`, nút "Gửi báo cáo mang tên tôi" | Cộng sinh với môi giới (điểm then chốt) | Xóa / bỏ tên môi giới |
| W8 | **Beacon dữ liệu người dùng (dấu vết ngầm)** | index.html `beacon()`, `/profile` | Dữ liệu quý giá — thu thập hành vi | Xóa / tắt ghi dấu |
| W9 | **Zone đăng nhập Google (tùy chọn)** | index.html `login-zone`, `handleLogin()` | Nhận diện người dùng → cá nhân hóa | Xóa / bắt buộc đăng nhập |
| W10 | **Zone chào hỏi cá nhân hóa** | index.html `greeting-zone`, `showGreeting()` | Hiện khi đã nhận diện, tạo cảm giác thân quen | Xóa |
| W11 | **Flow渐渐 gợi ý tiếp theo** | index.html `flow-hint`, `showFlowHint()` | Hiển thị dần theo tình huống — KHÔNG mở menu 20 tool | Xóa / thay bằng menu cố định |

## VÙNG 2 — OPENCODE2 (bộ não, qua bridge) — "TRÍ TUỆ"

| # | Tính năng gốc | Vị trí | Vai trò | CẤM |
|---|---|---|---|---|
| O1 | **Luồng hỏi → OpenCode → trả kết quả** | bridge/server.py `call_advisor→call_chorus/call_proxy` | Bộ não trả lời thật | Phá luồng / bỏ fallback |
| O2 | **Hội thoại riêng theo user (có bộ nhớ)** | `_user_key()`, `CONV_FILE`, `_call_chorus` sid | Mỗi user 1 cuộc nói liền mạch | Xóa khóa user / phá bộ nhớ |
| O3 | **Knowledge pack (persona Hải + dữ liệu)** | `_build_system_prompt()`, `get_knowledge()` | Trí tuệ + dữ liệu riêng chèn vào mọi câu | Bỏ nguồn dữ liệu |
| O4 | **Resilience "nước chảy mây trôi"** | Chorus→proxy fallback, retry | Không sập khi 1 nguồn lỗi | Bỏ fallback |

## VÙNG 3 — DỮ LIỆU (tài sản quý giá) — "BỘ NHỚ"

| # | Tính năng gốc | Vị trí | Vai trò | CẤM |
|---|---|---|---|---|
| D1 | **Hồ sơ người dùng (users.json)** | bridge/data/users.json | Dữ liệu người dùng nhận dạng | Xóa / để lộ công khai |
| D2 | **Dấu chân tương tác (events.jsonl)** | bridge/data/events.jsonl | Sổ lịch sử hành vi append-only | Xóa / ghi đè mất |
| D3 | **Đồng bộ (PC + Google Drive)** | sync_backup.sh | Backup dữ liệu quý 2 nơi an toàn | Xóa / vô hiệu đồng bộ |
| D4 | **Bảo vệ dữ liệu khỏi GitHub công khai** | .gitignore `bridge/data/` | Không lộ Zalo/data quý ra công khai | Bỏ ignore / push data lên public |

---

## ⚠️ QUY TRÌNH CẢNH BÁO MẠNH KHI ĐỤNG VÀO TÍNH NĂNG GỐC

Bất kỳ ai (Diamond, agent, script) định làm 1 trong các việc dưới đây với tính năng gốc:
```
[xóa]  [thay đổi]  [đổi tên]  [di chuyển thư mục]  [vô hiệu hóa]  [che giấu]
```
→ **BẮT BUỘC báo Diamond MẠNH MẼ trước** bằng format:

```
🚨 CẢNH BÁO TÍNH NĂNG GỐC
────────────────────────────
Tính năng bị đụng:  W1 — Bridge JS → OpenCode (khuôn mặt ↔ bộ não)
Hành động dự kiến:  XÓA doanhAsk()
Lý do:              ...
RỦI RO:            Web mất kết nối OpenCode → KHÔNG trả lời AI được
Đề xuất:            [giữ nguyên / thay bằng X ...]
→ CHỜ DIAMOND DUYỆT TRƯỚC KHI LÀM. KHÔNG tự quyết.
```

**Quy tắc bổ sung:**
1. **Over-engineering trong tối giản KHÔNG được phép đụng guard zone.** "Thu gọn web" ≠ "xóa bridge".
2. Cần **cảnh báo kép**: vừa trong file này, vừa qua **Telegram/Zalo cho Diamond** nếu hành động là do cron/agent tự chạy.
3. Nếu Diamond không trả lời → **KHÔNG tự tiếp tục vùng guard** (an toàn hơn xin lỗi sau).

---

## 🔒 CHỈ THỊ BỔ SUNG (Diamond chốt 03-09 — LÀM RÕ + NHẤN MẠNH)

> **"Đừng thay đổi những tính năng đã có, NHẤT LÀ những tính năng NGẦM. Sau này CHỈ là điều chỉnh GIAO DIỆN, CÁCH TRÌNH BÀY. Nếu xóa tính năng quan trọng → PHẢI CẢNH BÁO Diamond."**

### 1. ƯU TIÊN BẢO TOÀN TÍNH NĂNG NGẦM (cao nhất)
Tính năng NGẦM (chạy âm thầm phía sau, người dùng không thấy) là **xương sống hệ thống** — BẢO TOÀN TUYỆT ĐỐI:
- **Bridge ↔ OpenCode** (khuôn mặt ↔ bộ não) — W1/O1.
- **Beacon dấu vết người dùng + thu thập dữ liệu ngầm** — W8/D2.
- **Hội thoại riêng theo user + bộ nhớ** — O2.
- **Knowledge pack (persona Hải + dữ liệu)** — O3.
- **Data layer ngầm (users.json / events.jsonl / backup)** — D1-D4.
- Mọi tính năng ngầm sinh ra từ kiến trúc "Quy trình ngầm" (đăng nhập→nhận diện, bộ nhớ trung tâm Aladdin, viên nang trí nhớ, gợi ý chủ động) sau khi triển khai — cũng nằm trong vùng bảo toàn.

### 2. "CHỈ điều chỉnh giao diện + cách trình bày"
- Chiều được phép thay đổi: **UI, layout, màu sắc, font, vị trí hiển thị, cách bố cục, văn bản trình bày**.
- ❌ Không được đổi cách tính, logic, luồng ngầm, nguồn dữ liệu, kết nối bridge, thu thập dấu vết, backup.
- Nếu một thay đổi giao diện VÔ TÌNH kéo theo đụng logic ngầm → dừng + hỏi Diamond trước.

### 3. Xóa tính năng quan trọng → CẢNH BÁO (luật sắt)
- Trước KHI xóa / vô hiệu / che giấu bất kỳ tính năng (ngầm hay hiện) → **BÁO DIAMOND MẠNH MẼ TRƯỚC**, không làm sau.
- Dùng format cảnh báo ở trên + gửi qua Telegram/Zalo nếu agent tự chạy.
- Không xóa im lặng. Không "thu gọn" mà không nói.

---

## KIỂM TRA NHANH (chạy trước mỗi commit/agent):

```bash
# Chạy guard-check: báo nếu thiếu tính năng gốc / có thay đổi vi phạm
bash /tmp/opencode/xaydung/bridge/guard-check.sh
# Guard FAIL (exit 1) = DỪNG + BÁO DIAMOND, KHÔNG tự xử lý thêm
```
