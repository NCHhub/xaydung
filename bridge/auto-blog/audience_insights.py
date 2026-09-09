#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audience_insights.py — PHÂN TÍCH KHÁCH HÀNG MỤC TIÊU TỪ DATA THẬT (0 token)
Diamond 09-09: "từ dữ liệu, tự động phân tích để hiểu khách hàng mục tiêu hơn cả chính họ.
Từ đó tiếp tục tạo nội dung mới từ kiến thức, thành công đã có."

NGUỒN THẬT (chỉ đọc, không bịa):
  - bridge/data/library/posts.jsonl        ← thủ thư data đã phân loại (fb_librarian)
  - bridge/data/fb-groups-all.json         ← merge raw từ Apify (nếu có)
  - _blog/*.md                             ← bài đã live (để gap analysis)

ĐẦU RA:
  1. bridge/data/audience/insights-YYYY-MM-DD.md   ← báo cáo insight đọc được
  2. topics/YYYY-MM-DD-fb-audience-Ntopics.json    ← chủ đề GAP chưa có bài
     (chỉ sinh nếu hôm nay chưa có topics → write_blog.py tiêu thụ, không trùng)

CÁCH HIỂU KHÁCH "HƠN CẢ CHÍNH HỌ":
  - Nấc 1: họ NÓI gì (câu hỏi thật verbatim, engagement thật)
  - Nấc 2: họ ĐANG Ở đâu (chu_de + tuyến + độ nóng)
  - Nấc 3: họ SẮP cần gì (lifecycle: kiểm đếm → đền bù → bàn giao/thuê tạm →
           tái định cư → xây/sửa nhà mới → mua-bán) — nấc kế tiếp CHƯA nói ra.
"""
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

SITE = Path("/home/diamond/empire/xaydung-site")
LIB = SITE / "bridge" / "data" / "library"
DATA_DIR = SITE / "bridge" / "data"
AUD_DIR = DATA_DIR / "audience"
TOPICS_DIR = SITE / "bridge" / "auto-blog" / "topics"
BLOG_DIR = SITE / "_blog"

# Nhãn chủ đề đầy đủ (giống fb_pipeline.sh — KHÔNG dùng mã ngắn làm title)
LABELS = {
    "thu-hoi-dat": "Thu hồi đất tại Hà Nội — những điều chủ nhà cần biết",
    "den-bu": "Đền bù sau kiểm đếm — cách đối chiếu phương án chính xác",
    "gpmb": "Giải phóng mặt bằng theo tuyến đường Hà Nội — tiến độ và thủ tục",
    "tai-dinh-cu": "Tái định cư — quỹ đất, thủ tục và điều gia đình cần chuẩn bị",
    "cho-thue": "Đi thuê nhà ở tạm khi chờ bàn giao mặt bằng",
    "thue-nha-tam": "Thuê nhà ở tạm — kinh nghiệm chọn chỗ và những việc cần chuẩn bị",
    "ho-tro-nha-o": "Hỗ trợ nhà ở khi bị thu hồi đất — quyền lợi và thủ tục",
    "mua-ban": "Kinh nghiệm mua bán nhà đất Hà Nội — kiểm tra pháp lý trước khi đặt cọc",
    "dich-vu": "Dịch vụ tư vấn nhà đất Hà Nội — khi nào nên nhờ chuyên gia",
    "khac": "Kinh nghiệm tư vấn nhà đất thực tế từ hội nhóm Hà Nội",
}

# Lifecycle khách hàng bị thu hồi đất → nấc kế tiếp (dự đoán nhu cầu chưa nói ra)
LIFECYCLE = [
    ("thong-bao-thu-hoi", ["thu-hoi-dat"], "Thông báo thu hồi — còn im ắng nên lo hay không"),
    ("kiem-dem-danh-gia", ["thu-hoi-dat", "gpmb"], "Kiểm đếm, định giá tài sản"),
    ("den-bu", ["den-bu"], "Chốt phương án đền bù"),
    ("ban-giao-thu-nha", ["gpmb", "thue-nha-tam", "cho-thue"], "Bàn giao mặt bằng, thuê nhà tạm"),
    ("tai-dinh-cu", ["tai-dinh-cu", "ho-tro-nha-o"], "Tái định cư, quỹ đất, hỗ trợ nhà ở"),
    ("xay-sua-nha-moi", ["khac", "mua-ban"], "Xây/sửa nhà mới hoặc mua nhà thay thế"),
]


def slugify(s: str) -> str:
    """Giống hệt write_blog.py — đ→d trước (NFKD KHÔNG tách đ), rồi bỏ dấu kết hợp."""
    s = s.replace("đ", "d").replace("Đ", "d")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:90]


def load_posts() -> list:
    posts = []
    f = LIB / "posts.jsonl"
    if not f.exists():
        print("❌ Không có library/posts.jsonl — chạy fb_librarian.py hoặc fb_pipeline.sh trước.")
        return []
    for line in f.read_text(encoding="utf-8").splitlines():
        try:
            posts.append(json.loads(line))
        except Exception:
            pass
    return posts


def load_blog_slugs() -> set:
    used = set()
    if BLOG_DIR.exists():
        for f in BLOG_DIR.glob("*.md"):
            m = re.match(r"\d{4}-\d{2}-\d{2}-(.+)\.md$", f.name)
            if m:
                used.add(m.group(1))
    return used


def today_topics_exist() -> bool:
    for f in TOPICS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("date", "").startswith(date.today().isoformat()) and data.get("topics"):
                return True
        except Exception:
            pass
    return False


def main() -> int:
    posts = load_posts()
    if not posts:
        return 1
    blog_slugs = load_blog_slugs()
    AUD_DIR.mkdir(parents=True, exist_ok=True)

    hoi = [p for p in posts if p.get("loai") == "hoi-that"]
    print(f"👥 Kho data: {len(posts)} bài ({len(hoi)} câu hỏi thật)")

    # ---------- 1) Nỗi đau: rank chu_de theo (số hỏi, tổng engagement) ----------
    by_cd = defaultdict(list)
    for p in hoi:
        by_cd[p.get("chu_de", "khac")].append(p)
    cd_rank = sorted(
        by_cd.items(),
        key=lambda kv: (-len(kv[1]), -sum(x.get("engagement", 0) for x in kv[1])),
    )

    # ---------- 2) Ngôn ngữ thật: câu hỏi verbatim engagement cao ----------
    verbatim = []
    for cd, items in cd_rank:
        top = sorted(items, key=lambda x: -x.get("engagement", 0))[0]
        verbatim.append((cd, top.get("text", "")[:300], top.get("engagement", 0)))
    verbatim = verbatim[:10]

    # ---------- 3) Theo tuyến đường ----------
    tuyen = Counter()
    tuyen_eng = Counter()
    for p in hoi:
        t = (p.get("tuyen") or "").strip() or "(chưa rõ tuyến)"
        tuyen[t] += 1
        tuyen_eng[t] += p.get("engagement", 0)

    # ---------- 4) Gap analysis: chủ đề hỏi thật nhưng CHƯA có bài ----------
    gaps = []
    for cd, items in cd_rank:
        label = LABELS.get(cd, cd)
        sg = slugify(label)
        # bài đã cover chủ đề nếu slug bài trong _blog trùng prefix slug nhãn
        covered = any(b.startswith(sg[:30]) or sg.startswith(b[:30]) for b in blog_slugs)
        if not covered:
            top_q = sorted(items, key=lambda x: -x.get("engagement", 0))[0]
            gaps.append({
                "chu_de": label,
                "cau_hoi": (top_q.get("text", "") or "")[:400],
            })
    gaps = gaps[:5]  # tối đa 5 chủ đề mới/run

    # ---------- 5) Lifecycle: họ đang ở đâu → sắp cần gì ----------
    stage_count = {}
    stage_eng = {}
    for name, keys, _desc in LIFECYCLE:
        items = [p for p in hoi if p.get("chu_de") in keys]
        stage_count[name] = len(items)
        stage_eng[name] = sum(p.get("engagement", 0) for p in items)
    # Nấc tiếp theo = nấc kế nấc nhiệt nhất (có bài coverage dựa theo chu_de đã có)
    busiest = max(stage_count, key=lambda k: (stage_count[k], stage_eng[k]))
    idx = [s[0] for s in LIFECYCLE].index(busiest)
    next_stage = LIFECYCLE[idx + 1] if idx + 1 < len(LIFECYCLE) else None

    # ---------- 6) Ghi báo cáo insight ----------
    today = date.today().isoformat()
    lines = []
    lines.append(f"# Insight khách hàng mục tiêu — {today}")
    lines.append("")
    lines.append("> Tự động từ data thật (library/posts.jsonl + fb-groups), 0 token. "
                 "Nguồn câu hỏi = verbatim, không bịa.")
    lines.append("")
    lines.append("## 1. Họ đang đau nhất điều gì (xếp theo số hỏi × engagement)")
    for cd, items in cd_rank[:6]:
        name = LABELS.get(cd, cd)
        n = len(items)
        eng = sum(x.get("engagement", 0) for x in items)
        lines.append(f"- `{cd}` {name} — {n} hỏi, tổng {eng} tương tác")
    lines.append("")
    lines.append("## 2. Họ nói bằng lời thật (top câu hỏi)")
    for cd, text, eng in verbatim:
        lines.append(f"- ({eng} tương tác): {text}")
    lines.append("")
    lines.append("## 3. Tuyến đường nóng nhất")
    for t, n in tuyen.most_common(5):
        lines.append(f"- {t}: {n} hỏi ({tuyen_eng[t]} tương tác)")
    lines.append("")
    lines.append(f"## 4. Họ đang ở nấc nào — và nấc kế tiếp họ CHƯA NÓI RA")
    for name, keys, desc in LIFECYCLE:
        mark = " ◀ ĐANG NÓNG NHẤT" if name == busiest else ""
        lines.append(f"- {desc}: {stage_count[name]} hỏi, {stage_eng[name]} tương tác{mark}")
    if next_stage:
        lines.append("")
        lines.append(f"→ **Nấc kế tiếp dự đoán: {next_stage[2]}** — họ chưa hỏi tới vì vẫn"
                     f" đang ở nấc trước. Đây là nội dung mới cần chuẩn bị trước.")
    lines.append("")
    lines.append("## 5. Cơ hội nội dung (chủ đề hỏi thật nhưng chưa có bài)")
    if gaps:
        for g in gaps:
            lines.append(f"- [ ] **{g['chu_de']}** — câu hỏi: {g['cau_hoi'][:120]}")
    else:
        lines.append("- Không có chủ đề hỏi thật nào chưa có bài — kho đã cover tốt. "
                     "Theo dõi data mới hằng ngày.")
    lines.append("")
    lines.append(f"## 6. Hành động tự động")
    lines.append("- [ ] Pipeline viết bài: chạy write_blog.py để sinh bài từ topics mới"
                 " (nội dung lấy từ _data/moi-gioi.yml — NGUỒN THẬT duy nhất)")
    lines.append("- [ ] Quality gate kiểm tra trước khi push (chỉ đăng bài PASS)")

    report = AUD_DIR / f"insights-{today}.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"📊 Đã ghi báo cáo insight: {report.name}")

    # ---------- 7) Sinh topics GAP (chỉ nếu hôm nay chưa có topics) ----------
    if today_topics_exist():
        print("📝 Đã có topics hôm nay — chỉ cập nhật report, không sinh topics trùng.")
        return 0
    if len(gaps) < 2:
        print(f"⚠️ Chỉ có {len(gaps)} chủ đề gap (cần ≥2) — chờ data mới.")
        return 0

    TOPICS_DIR.mkdir(parents=True, exist_ok=True)
    topics_data = {"date": today, "source": "fb-audience-auto", "topics": gaps}
    tf = TOPICS_DIR / f"{today}-fb-audience-{len(gaps)}topics.json"
    tf.write_text(json.dumps(topics_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Đã tạo topics GAP: {tf.name} ({len(gaps)} chủ đề) — sẵn sàng cho write_blog.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())