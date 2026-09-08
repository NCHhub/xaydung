#!/usr/bin/env bash
# fb_pipeline.sh — Pipeline liên tục cho FB groups scraping + auto-blog
# Diamond 09-08: khai thác miễn phí (Apify free tier), tái sử dụng data, cộng hưởng.
# Cron: 2×/tuần (Thứ 2 + Thứ 5, 09:30) — tốn ít credit free tier, tránh repeat.

set -euo pipefail
SITE="/home/diamond/empire/xaydung-site"
cd "$SITE"

# ---- 1) Kiểm tra token Apify ----
TOKEN_FILE="$HOME/.apify/token"
[ -f "$TOKEN_FILE" ] && TOKEN=$(cat "$TOKEN_FILE") || { echo "❌ Thiếu $TOKEN_FILE"; exit 1; }

# ---- 2) Chạy Apify actor (postsNewerThan 60 days, highest_engagement) ----
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTFILE="bridge/data/fb-groups-60d-$TIMESTAMP.json"
INPUT_JSON='{"groupUrls":["https://www.facebook.com/groups/2702319990143345","https://www.facebook.com/groups/953678636273766"],"postsNewerThan":"60 days","sortBy":"highest_engagement","minReactions":10,"postsPerGroup":50}'

echo "🚀 Bắt đầu scrape Apify actor (free tier)..."
APIFY_RUN=$(apify actors call api-empire/facebook-groups-scraper "$INPUT_JSON" --token "$TOKEN" 2>&1 || true)
echo "$APIFY_RUN"

# ---- 3) Nếu có dataset mới → merge + dedupe vào bridge/data ----
if [ -f "$OUTFILE" ]; then
    echo "📦 Đang merge dataset mới..."
    # Đọc dataset cũ nhất (nếu có)
    OLDEST=$(ls -t bridge/data/fb-groups-60d-*.json 2>/dev/null | head -1)
    if [ -n "$OLDEST" ]; then
        python3 - << 'PYEOF'
import json, sys
from pathlib import Path

new_path = Path("$OUTFILE")
old_path = Path("$OLDEST")
out_dir = Path("bridge/data")

# Load mới
try:
    new_data = json.loads(new_path.read_text(encoding="utf-8"))
except Exception:
    new_data = []

# Load cũ
try:
    old_data = json.loads(old_path.read_text(encoding="utf-8"))
except Exception:
    old_data = []

# Dedupe theo legacyId
seen = set()
all_posts = []
for p in old_data:
    if isinstance(p, dict) and p.get("type") == "post":
        lid = p.get("legacyId") or p.get("id")
        if lid and lid not in seen:
            seen.add(lid)
            all_posts.append(p)

for p in new_data:
    if isinstance(p, dict) and p.get("type") == "post":
        lid = p.get("legacyId") or p.get("id")
        if lid and lid not in seen:
            seen.add(lid)
            all_posts.append(p)

out = out_dir / "fb-groups-all.json"
out.write_text(json.dumps(all_posts, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"✅ Merge xong: {len(all_posts)} bài (đã loại {len(old_data) - sum(1 for p in old_data if isinstance(p, dict) and p.get('type') == 'post' and (p.get('legacyId') or p.get('id')) in [q.get('legacyId') or q.get('id') for q in new_data if isinstance(q, dict) and q.get('type') == 'post'])})")
PYEOF
    else
        cp "$OUTFILE" bridge/data/fb-groups-all.json
        echo "✅ Sao chép dataset đơn lẻ"
    fi
else
    echo "⚠️ Dataset Apify không tạo ra file — có thể vẫn trong quá trình crawl. Đang dùng dữ liệu cũ..."
fi

# ---- 4) Chạy fb_librarian.py để cập nhật library + thống kê ----
echo "📚 Đang cập nhật thủ thư data..."
python3 bridge/auto-blog/fb_librarian.py 2>&1 || echo "⚠️ fb_librarian gặp lỗi (có thể thiếu data)"

# ---- 5) Tạo topics mới từ các bài hỏi thật trong kho ----
echo "🧠 Đang quét chủ đề hỏi thật để sinh blog..."
python3 - << 'PYEOF'
import json, re, sys
from pathlib import Path

SITE = Path("$SITE")
LIB = SITE / "bridge" / "data" / "library"
TOPICS_DIR = SITE / "bridge" / "auto-blog" / "topics"
BLOG_DIR = SITE / "_blog"

# Đọc posts.jsonl
posts = []
try:
    with open(LIB / "posts.jsonl", encoding="utf-8") as f:
        for line in f:
            p = json.loads(line.strip())
            if p.get("loai") == "hoi-that" and p.get("engagement", 0) >= 5:
                posts.append(p)
except Exception as e:
    print(f"⚠️ Không đọc được posts.jsonl: {e}")
    posts = []

if not posts:
    print("📝 Không có bài hỏi thật mới để tạo topics — sẽ chạy lại lần sau.")
    sys.exit(0)

# Đảm bảo topics directory
TOPICS_DIR.mkdir(parents=True, exist_ok=True)

# Lấy các chủ đề chưa có slug trong topics/
existing_slugs = set()
for t_file in TOPICS_DIR.glob("*.json"):
    try:
        data = json.loads(t_file.read_text(encoding="utf-8"))
        # Lấy các chu_de đã có
        for t in data.get("topics", []):
            cd = t.get("chu_de", "")
            if cd:
                sg = re.sub(r"[^a-z0-9]+", "-", cd.lower()).strip("-")[:90].replace("đ", "d").replace("Đ", "d")
                existing_slugs.add(sg)
    except Exception:
        pass

# Gom các chu_de unique + câu hỏi ngắn (tối đa 8 topics)
seen_chu_de = []
for p in posts:
    cd = p.get("chu_de", "")
    if not cd:
        continue
    sg = re.sub(r"[^a-z0-9]+", "-", cd.lower()).strip("-")[:90].replace("đ", "d").replace("Đ", "d")
    if sg in existing_slugs or sg in seen_chu_de:
        continue
    seen_chu_de.append(sg)
    if len(seen_chu_de) >= 8:
        break

if len(seen_chu_de) < 2:
    print(f"⚠️ Chỉ có {len(seen_chu_de)} topic duy nhất (cần >= 2). Để chạy lại lần sau khi có data mới.")
    sys.exit(0)

# Viết topics JSON mới (date-based, không ghi vào used_topics conflict)
today = json.loads((LIB / "index.json").read_text(encoding="utf-8")).get("updated", __import__("datetime").date.today().isoformat())
topics_data = {
    "date": today,
    "source": "fb-pipeline-auto",
    "topics": []
}
for i, cd in enumerate(seen_chu_de, 1):
    # Lấy câu hỏi đầu tiên tương ứng
    q_text = next((p.get("text", "") for p in posts if re.sub(r"[^a-z0-9]+", "-", p.get("chu_de", "").lower())[:90].replace("đ", "d").replace("Đ", "d") == cd), "")
    # Rút gọn desc 140 char
    desc = (q_text[:137] + "…") if len(q_text) > 137 else q_text
    topics_data["topics"].append({
        "chu_de": cd,
        "cau_hoi": q_text
    })

topics_file = TOPICS_DIR / f"2026-09-08-fb-pipeline-{len(seen_chu_de)}topics.json"
topics_file.write_text(json.dumps(topics_data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"✅ Đã tạo topics: {topics_file.name} ({len(seen_chu_de)} chủ đề)")
PYEOF

# ---- 6) Chạy write_blog.py sinh bài mới ----
echo "✍️ Đang sinh bài blog..."
python3 bridge/auto-blog/write_blog.py 2>&1 | grep -E "^\\[write_blog\\]|^\[ ✅\\]|^\[ ❌\\]" || echo "⚠️ write_blog kết quả không rõ"

# ---- 7) Commit + push nếu có bài mới ----
echo "📦 Đang kiểm tra bài mới..."
NEW_BLOG=$(ls -t _blog/202*-*.md 2>/dev/null | head -1 | xargs basename 2>/dev/null || true)
if [ -n "$NEW_BLOG" ]; then
    git add _blog/"$NEW_BLOG" bridge/auto-blog/write_blog.py bridge/auto-blog/.used_topics.json bridge/auto-blog/topics/ 2>/dev/null || true
    if git diff --cached --quiet 2>/dev/null; then
        echo "✅ Không có file thay đổi mới."
    else
        git commit -q -m "xaydung: auto-blog pipeline ${TIMESTAMP} — thêm $(echo "$NEW_BLOG" | sed 's/2026-09-08-//' | sed 's/-/ /g' | awk '{print $1,$2}')"
        git push origin main 2>&1 | tail -2
        echo "✅ Đã push live."
    fi
else
    echo "✅ Không có bài blog mới trong session hiện tại."
fi

echo "=== fb_pipeline.sh xong ==="