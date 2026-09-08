# Apify FB Group Scraper — Setup Guide (Diamond 09-08)

> Hướng đã chốt: **KHÔNG tự code** — dùng actor có sẵn `api-empire/facebook-groups-scraper` (Apify).
> Nhu cầu: bài nhiều tương tác 60 ngày từ hội nhóm FB (xây/sửa nhà HN) → chủ đề cho auto-blog + đối chiếu web.

## Trạng thái
- [x] apify-cli 1.10.0 đã cài (npm global, node 22)
- [ ] Diamond: tạo tài khoản Apify free + lấy API token  (bước 1 dưới)
- [ ] Diamond: mở Brave login FB, export cookie nếu cần private group (bước 2 — chỉ khi group kín)

## Bước 1 — Diamond: Token Apify (1 lần, ~2 phút)
1. Mở https://console.apify.com → Sign up (free, 5$/tháng credit tặng — đủ chạy thử)
2. Settings → Integrations → API token → copy
3. Gửi token cho agent (hoặc lưu `~/.apify/token.txt`), agent chạy:
   ```bash
   apify login --token <TOKEN>
   ```

## Bước 2 — Diamond (chỉ khi group KÍN, không bắt buộc)
- Public group: **không cần** (actor dùng residential proxy, đọc logged-out)
- Private group: mở Brave → login FB → F12 → Application → Cookies → https://www.facebook.com
  → export toàn bộ cookie (tối thiểu `c_user` + `xs`, nên thêm `fr`,`datr`,`sb`,`wd`)

## Chạy (agent, khi có token — KHÔNG tự viết code, chỉ gọi actor)
```bash
# gọi actor qua API (MCP/HTTP có sẵn) — ví dụ input:
#   startUrls: [nhóm FB], postsNewerThan: "60 days",
#   feedSortStrategy: TOP_POSTS, sortBy: highest_engagement, minReactions: 30
```
Actor trả JSON: post text, 7 loại reaction, comments, shares, engagement rank/percentile
→ export JSON/CSV → feed pipeline auto-blog (write_blog.py đã sẵn, đọc topics/).

## Nguồn thật
- Actor: https://apify.com/api-empire/facebook-groups-scraper
- Fallback: https://apify.com/whoareyouanas/facebook-group-scraper (private group qua cookies)

## Ràng buộc
- CẤM tự viết scraper. Chỉ cài/chạy công cụ có sẵn.
- Số liệu giá vẫn lấy từ `moi-gioi.yml` (bài học meta-num-conflict), FB/actor chỉ = nguồn chủ đề + câu hỏi thật.