#!/usr/bin/env bash
# fb_pipeline.sh — Pipeline liên tục cho FB groups scraping + auto-blog
# Diamond 09-08: khai thác miễn phí (Apify free tier), tái sử dụng data, cộng hưởng.
# Cron 09-09: HẰNG NGÀY 09:30 với cửa sổ NHỎ (2 ngày, 20 bài/group, ≥5 tương tác)
#   → ít credit/run, merge cộng dồn, topics + viết bài + gate đều 0 token.
#   Weekly giữ bản to (60d/50/10) khi cần quét sâu: FB_DAYS=60 FB_POSTS=50 FB_MIN_REACT=10.
# Toàn pipeline = 0 token LLM (chỉ tốn Apify credit free); Meta AI chỉ dùng khi chạy run.sh thủ công.

set -euo pipefail
SITE="/home/diamond/empire/xaydung-site"
cd "$SITE"

# ---- 1) Kiểm tra token Apify ----
TOKEN_FILE="$HOME/.apify/token"
[ -f "$TOKEN_FILE" ] && TOKEN=$(cat "$TOKEN_FILE") || { echo "❌ Thiếu $TOKEN_FILE"; exit 1; }

# ---- 2) Chạy Apify actor — cửa sổ theo cron (daily nhỏ / weekly lớn) ----
FB_DAYS="${FB_DAYS:-2}"
FB_POSTS="${FB_POSTS:-20}"
FB_MIN_REACT="${FB_MIN_REACT:-5}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTFILE="bridge/data/fb-groups-60d-$TIMESTAMP.json"
INPUT_JSON=$(python3 -c "
import json, sys
d = {
    'groupUrls': [
        'https://www.facebook.com/groups/2702319990143345',
        'https://www.facebook.com/groups/953678636273766',
    ],
    'postsNewerThan': '$FB_DAYS days',
    'sortBy': 'highest_engagement',
    'minReactions': int('$FB_MIN_REACT'),
    'postsPerGroup': int('$FB_POSTS'),
}
sys.stdout.write(json.dumps(d, ensure_ascii=False))
")
echo "🔭 Cửa sổ scrape: ${FB_DAYS} ngày, ${FB_POSTS} bài/group, ≥${FB_MIN_REACT} react"

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
import json, re, sys, unicodedata
from pathlib import Path

SITE = Path("$SITE")
LIB = SITE / "bridge" / "data" / "library"
TOPICS_DIR = SITE / "bridge" / "auto-blog" / "topics"
BLOG_DIR = SITE / "_blog"

def slugify(s: str) -> str:
    """Đúng chuẩn write_blog.py: đ→d trước (NFKD không tách đ), bỏ dấu kết hợp, nối gạch."""
    s = s.replace("đ", "d").replace("Đ", "d")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:90]

# Map mã chu_de (thủ thư đặt) → TỰA ĐỀ đầy đủ, viết hoa, đúng giọng tư vấn.
# Luật: KHÔNG dùng mã ngắn làm title — bài rác bị quality_gate chặn.
LABELS = {
    "thu-hoi-dat": "Thu hồi đất tại Hà Nội — những điều chủ nhà cần biết",
    "den-bu": "Đền bù sau kiểm đếm — cách đối chiếu phương án chính xác",
    "gpmb": "Giải phóng mặt bằng theo tuyến đường Hà Nội — tiến độ và thủ tục",
    "tai-dinh-cu": "Tái định cư — quỹ đất, thủ tục và điều gia đình cần chuẩn bị",
    "cho-thue": "Đi thuê nhà ở tạm khi chờ bàn giao mặt bằng",
    "khac": "Kinh nghiệm tư vấn nhà đất thực tế từ hội nhóm Hà Nội",
}

# Đọc posts.jsonl — ưu tiên bài engagement cao
posts = []
try:
    with open(LIB / "posts.jsonl", encoding="utf-8") as f:
        for line in f:
            p = json.loads(line.strip())
            if p.get("loai") == "hoi-that" and p.get("engagement", 0) >= 5:
                posts.append(p)
    posts.sort(key=lambda p: p.get("engagement", 0), reverse=True)
except Exception as e:
    print(f"⚠️ Không đọc được posts.jsonl: {e}")
    posts = []

if not posts:
    print("📝 Không có bài hỏi thật mới để tạo topics — sẽ chạy lại lần sau.")
    sys.exit(0)

TOPICS_DIR.mkdir(parents=True, exist_ok=True)

# Slug đã dùng: toàn bộ bài _blog + chủ đề topics cũ
used_slugs = set()
for t_file in TOPICS_DIR.glob("*.json"):
    try:
        for t in json.loads(t_file.read_text(encoding="utf-8")).get("topics", []):
            cd = t.get("chu_de", "")
            if cd:
                used_slugs.add(slugify(cd))
    except Exception:
        pass
for f in BLOG_DIR.glob("*.md"):
    m = re.match(r"\d{4}-\d{2}-\d{2}-(.+)\.md$", f.name)
    if m:
        used_slugs.add(m.group(1))

# Chọn tối đa 8 chủ đề: mỗi mã chu_de → 1 topic (bài engagement cao nhất)
topics = []
for p in posts:
    cd = p.get("chu_de", "")
    if not cd:
        continue
    chu_de = LABELS.get(cd, cd)
    sg = slugify(chu_de)
    if sg in used_slugs:
        continue
    topics.append({"chu_de": chu_de, "cau_hoi": (p.get("text", "") or "")[:400]})
    used_slugs.add(sg)
    if len(topics) >= 8:
        break

if len(topics) < 2:
    print(f"⚠️ Chỉ có {len(topics)} chủ đề mới (cần >= 2) — chờ data mới.")
    sys.exit(0)

today = json.loads((LIB / "index.json").read_text(encoding="utf-8")).get("updated", __import__("datetime").date.today().isoformat())
topics_data = {"date": today, "source": "fb-pipeline-auto", "topics": topics}
topics_file = TOPICS_DIR / f"{today}-fb-pipeline-{len(topics)}topics.json"
topics_file.write_text(json.dumps(topics_data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"✅ Đã tạo topics: {topics_file.name} ({len(topics)} chủ đề)")
PYEOF

# ---- 5b) PHÂN TÍCH KHÁCH HÀNG + tạo topics GAP (0 token, Diamond 09-09) ----
# Hiểu khách hơn cả chính họ: nỗi đau thật + lời thật + tuyến nóng + lifecycle
# → nấc kế tiếp họ chưa nói ra. Chỉ sinh topics nếu hôm nay chưa có (không trùng).
echo "🧠 Đang phân tích insight khách hàng từ data thật..."
python3 bridge/auto-blog/audience_insights.py 2>&1 || echo "⚠️ audience_insights gặp lỗi (xem log)"

# ---- 6) Chạy write_blog.py sinh bài mới ----
echo "✍️ Đang sinh bài blog..."
python3 bridge/auto-blog/write_blog.py 2>&1 | grep -E "^\\[write_blog\\]|^\[ ✅\\]|^\[ ❌\\]" || echo "⚠️ write_blog kết quả không rõ"

# ---- 7) TƯ PHÁP: quality_gate kiểm tra bài mới → CHỈ push bài PASS ----
echo "⚖️ Tư pháp kiểm tra chất lượng bài mới (quality_gate)..."
GATE_JSON=$(python3 bridge/auto-blog/quality_gate.py --json 2>/dev/null || true)
PASS_LIST=$(echo "$GATE_JSON" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print('\n'.join(r['file'] for r in data.get('results', []) if r.get('verdict') == 'PASS'))
except Exception:
    pass
" 2>/dev/null || true)
FAIL_LIST=$(echo "$GATE_JSON" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print('\n'.join(r['file'] for r in data.get('results', []) if r.get('verdict') == 'FAIL'))
except Exception:
    pass
" 2>/dev/null || true)

if [ -n "$FAIL_LIST" ]; then
    echo "❌ Bài FAIL quality_gate (KHÔNG đăng — lưu local, chờ sửa):"
    echo "$FAIL_LIST" | sed 's/^/   - /'
fi

if [ -n "$PASS_LIST" ]; then
    echo "✅ Bài PASS quality_gate → commit + push:"
    echo "$PASS_LIST" | sed 's/^/   + /'
    echo "$PASS_LIST" | while read -r f; do git add "$f"; done
    git add bridge/auto-blog/quality_gate.py bridge/auto-blog/write_blog.py bridge/auto-blog/.used_topics.json bridge/auto-blog/topics/ 2>/dev/null || true
    if git diff --cached --quiet 2>/dev/null; then
        echo "✅ Không có file PASS mới."
    else
        git commit -q -m "xaydung: auto-blog pipeline ${TIMESTAMP} — bài PASS quality_gate (Tam quyền: lập pháp=chuẩn bài Hải, hành pháp=pipeline, tư pháp=gate độc lập 0 token)"
        git push origin main 2>&1 | tail -2
        echo "✅ Đã push live ($(echo "$PASS_LIST" | wc -l) bài)."
    fi
else
    echo "✅ Không có bài PASS mới trong session này."
fi

echo "=== fb_pipeline.sh xong ==="