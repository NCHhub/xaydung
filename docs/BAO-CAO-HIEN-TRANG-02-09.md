# BÁO CÁO HIỆN TRẠNG — xaydung.aladdin.vn
_Ngày: 02/09/2026 — Khảo sát theo LỆNH TỔNG Mục 5 & 20_

---

## 1. Tổng quan stack hiện tại

| Thành phần | Hiện trạng |
|---|---|
| **Framework** | Jekyll 4 (static site) trên GitHub Pages |
| **Hosting** | GitHub Pages — tự build trên push to `main`, ~40s/build |
| **Domain** | `xaydung.aladdin.vn` (custom domain, HTTPS cert đang pending) |
| **Frontend** | HTML/CSS/JS thuần + Bootstrap 5.3.8 + AdminLTE v4 (CDN) |
| **Backend / Database** | **Không có** |
| **Auth** | **Không có** |
| **API** | **Không có** |
| **CI/CD** | GitHub Pages auto-build (không có `.github/workflows` riêng) |
| **Analytics** | Chưa có |
| **Data** | `_data/moi-gioi.yml` (static: 6 câu hỏi/trả lời + 5 bài content suggestions) |
| **Forms** | Google Forms ngoài (góp ý + giới thiệu khách) — không tích hợp |
| **Tương thích mobile** | OK — AdminLTE responsive, CSSApple mobile-first |

## 2. Các route đang hoạt động

| Route | Trang | Trạng thái |
|---|---|---|
| `/` | Landing page — giới thiệu ACE + lợi ích | ✅ Live |
| `/moi-gioi/` | Dashboard "Hôm nay" — 3 hành động lớn + góp ý + cam kết | ✅ Live |
| `/moi-gioi/khach-hoi/` | 6 câu hỏi khách hay hỏi + copy để trả lời | ✅ Live |
| `/moi-gioi/hom-nay-dang-gi/` | 5 chủ đề content + caption copy | ✅ Live |
| `/bai-viet/...` | Blog SEO (8 bài) | ✅ Live |
| `/cong-trinh/...` | Portfolio (3 công trình) | ✅ Live |
| Sidebar | YouTube/Facebook/Group/Zalo + Góp ý nhanh | ✅ Live |

## 3. Phân tích theo LỆNH TỔNG V2

### 3.1. Kiến trúc yêu cầu (Mục 0.0)

```
Web (giao diện) → Relay API (cloud) → Bridge (PC) → OpenCode Advisor (localhost)
```

Bốn thành phần MVP:

| Thành phần | Yêu cầu | Hiện trạng | Cần xây |
|---|---|---|---|
| **Web mobile-first** | Ô hỏi, 3-4 nút lớn, render kết quả JSON | Dashboard hiện có (static, chưa có ô hỏi, chưa render JSON) | CẦN |
| **Relay API** | Nhận task, xác thực, xếp hàng, lưu trạng thái | **KHÔNG CÓ** | **CẦN MỚI** |
| **Aladdin Bridge (PC)** | Kéo task, gọi OpenCode, gửi kết quả | opencode serve đang chạy trên PC (4097) | CẦN (Bridge mới) |
| **OpenCode Advisor** | Agent bị khóa quyền, đọc knowledge, trả JSON | Chưa có (opencode hiện dùng chung) | CẦN MỚI |

### 3.2. Lỗ hổng lớn nhất: KHÔNG CÓ BACKEND

Toàn bộ trang hiện tại là **static site** — KHÔNG có API, KHÔNG có database, KHÔNG có auth.

Phase 1 yêu cầu (Mục 15):
- ✅ Dashboard "Hôm nay" → đã có (static)
- ❌ Giới thiệu khách <60s + ghi người giới thiệu → cần backend lưu lead
- ❌ Khách của tôi + timeline trạng thái → cần DB + phân quyền
- ❌ Phản hồi + đề xuất tính năng → cần lưu + track trạng thái
- ❌ Admin cập nhật lead + phản hồi → cần auth + admin panel

**Kết luận:** Phase 1 theo đúng nghĩa chỉ làm được ~30% trên stack hiện tại. Phần còn lại CẦN quyết định kiến trúc backend.

## 4. Bản đồ route đề xuất (theo Mục 9)

```
/                          → Landing (✅ có)
/app                       → Dashboard Hôm nay (cải thiện từ /moi-gioi/)
/app/hoi-aladdin           → Nhập câu hỏi + kết quả (MỚI — cần Relay API)
/app/noi-dung              → Nội dung có bằng chứng (cải thiện /moi-gioi/hom-nay-dang-gi/)
/app/uoc-tinh              → Ước tính sơ bộ + checklist (MỚI — cần Relay API)
/app/gioi-thieu-khach      → Form gửi khách <60s (cải thiện từ Google Forms)
/app/khach-cua-toi         → Danh sách lead + timeline (MỚI — cần DB)
/app/gop-y                 → Góp ý + đề xuất + bình chọn (cải thiện từ Google Forms)
/app/tai-khoan             → Hồ sơ môi giới (MỚI — cần auth)
/admin                     → Quản trị vận hành (MỚI — cần auth + DB)
/bai-viet/...               → Blog SEO (✅ giữ nguyên)
/cong-trinh/...             → Portfolio (✅ giữ nguyên)
```

## 5. Schema dữ liệu đề xuất (Mục 10)

Để Phase 1 chạy cần ít nhất 6 bảng:

```
users              (id, role, status, name, phone, created_at)
agent_profiles     (user_id, khu_vuc, ma_gioi_thieu, cai_dat_rieng_tu)
leads              (id, referrer_id, info_khach加密, nhu_cau, consent, status)
lead_events        (lead_id, actor_id, trang_thai_cu_moi, ghi_chu, created_at)
feedback           (user_id, target_type_id, vote, category, text, status)
feature_votes      (feedback_id, user_id, created_at)
```

## 6. Điểm cần quyết định của chủ dự án

| # | Vấn đề | Tại sao quan trọng | Lựa chọn |
|---|---|---|---|
| **D1** | **Backend chạy ở đâu?** | Relay API cần server có URL public — GitHub Pages chỉ tĩnh | **(A)** Cloudflare Workers + D1 (free, serverless) · **(B)** Vercel + Supabase (free) · **(C)** Chạy trên PC (Python/FastAPI + SQLite, Bridge expose qua Cloudflare Tunnel) |
| **D2** | **Auth bằng gì?** | Phase 1 cần phân quyền môi giới/admin, "Khách của tôi" cần đăng nhập | **(A)** Google Sign-In (OAuth2, cần Google Cloud project) · **(B)** Magic link / email · **(C)** Chưa auth, dùng link riêng theo mã môi giới (đơn giản nhất) |
| **D3** | **Phase 1 nên làm gì trước?** | Không thể làm hết cùng lúc | **(A)** Ưu tiên "Ô hỏi" + Relay + Bridge (chứng minh kết nối OpenCode) · **(B)** Ưu tiên "Giới thiệu khách" + lead tracking (giá trị rõ nhất cho môi giới) · **(C)** Ưu tiên "Khách của tôi" + timeline (giữ mối quan hệ môi giới-Aladdin) |
| **D4** | **Knowledge pack có sẵn chưa?** | OpenCode Advisor cần kiến thức để trả lời — có thể dùng `_data/moi-gioi.yml` + blog hiện có, hoặc cần chuyên gia soạn thêm | Nếu chưa → Advisor trả lời từ knowledge pack hiện có + cảnh báo "AI sơ bộ" |
| **D5** | **Triển khai production?** | Tài liệu nói "không triển khai production nếu chưa có lệnh" | Bao gồm: Google Cloud project, domain DNS, Bridge auto-start, HTTPS enforced |

---

## 7. Lời khuyên từ khảo sát

### ✅ Điểm mạnh đã có
- Giao diện mobile-first tốt, nói tiếng môi giới rõ ràng
- Content SEO + portfolio thật, có bằng chứng
- GitHub Pages miễn phí, build tự động, không maintenance
- Channel Zalo/YT/FB/Group đã tích hợp

### ❌ Điểm yếu cần giải quyết
- Không có backend → không thể lưu lead, phân quyền, track trạng thái
- Google Forms bên ngoài → không tích hợp, không track được ai submit, không có timeline
- Không có ô hỏi trung tâm (theo Mục 0.2 — yêu cầu bắt buộc)
- Không có知识 (knowledge pack) cho Advisor
- Bridge chưa có — chưa chứng minh được kết nối Web ↔ OpenCode trên PC

### 🎯 Gợi ý lát dọc an toàn (không cần quyết định D1/D2 ngay)

**Có thể triển khai NGAY trên stack hiện tại (static Jekyll):**
1. **Ô "Khách đang hỏi gì?"** → Thêm input box trên dashboard, link đến `/moi-gioi/khach-hoi/` (hiện đã có câu hỏi tĩnh — chưa cần AI)
2. **Bố cục trang chủ** theo Mục 0.2: 3 nút lớn (Tính chi phí, Soi báo giá, Tính vật tư) — hiện đã có dạng tương tự
3. **Guest flow**: giữ nguyên không bắt đăng nhập
4. **Nội dung có bằng chứng**: cải thiện `/moi-gioi/hom-nay-dang-gi/` để hiển thị nguồn + ngày rõ ràng hơn

**Cần quyết định D1/D2/D3 mới làm được:**
- Relay API + Bridge → chứng minh câu hỏi → Advisor trả lời JSON → Web render
- Giới thiệu khách có tracking → lead database → timeline trạng thái
- Auth + "Khách của tôi" + admin panel
