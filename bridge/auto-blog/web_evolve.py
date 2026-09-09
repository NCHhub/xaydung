#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
web_evolve.py — WEB TỰ HỌC THÀNH CÔNG → TỰ TIẾN HÓA LIÊN TỤC (0 token)
Diamond 09-09: "Web tự học thành công tiến hóa tiếp, thu hút đúng đối tượng. Liên tục tiến hóa."

VÒNG LẶP SINH HỌC (chạy hằng ngày sau fb_pipeline, cron 06:40 sáng hôm sau nếu cần):
  1. SENSE  — đọc nhu cầu thật: bridge/data/library/posts.jsonl (loai=hoi-that, engagement)
  2. LEARN  — tính độ nóng mỗi chu_de (tổng engagement posts thật) vs số bài đã có (_blog)
  3. EVOLVE — sinh topics mới cho chu_de HOT CHƯA CÓ BÀI (≥2) + chỉ ra chu_de THỪA/THIẾU
             + cân bằng ĐỐI TƯỢNG (mục tiêu web = thu hút KHÁCH xây/sửa nhà = Chủ nhà,
             môi giới là nguồn cộng sinh — đo tỷ lệ bài, gợi ý dịch chuyển)
  4. GHI    — báo cáo evolve-YYYY-MM-DD.md + append log evolve.log
LUẬT: KHÔNG bịa — mọi chủ đề sinh ra đều có câu hỏi thật verbatim từ hội nhóm.
      Exit 0 = thường, 1 = có topics mới sinh (pipeline biết cần đăng bài).
"""
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

SITE = Path("/home/diamond/empire/xaydung-site")
LIBRARY = SITE / "bridge" / "data" / "library" / "posts.jsonl"
BLOG = SITE / "_blog"
TOPICS_DIR = SITE / "bridge" / "auto-blog" / "topics"
LOG = Path.home() / "empire" / "shared" / "logs" / "evolve.log"
REPORT_DIR = SITE / "bridge" / "data" / "evolve"

# Đối tượng mục tiêu web (mục tiêu Diamond): thu hút khách tìm thông tin xây sửa = Chủ nhà.
# Môi giới = đối tác cộng sinh (nguồn khách + lan tỏa). Tỷ lệ cân bằng mong muốn.
TARGET_SPLIT = {"Dành cho Chủ nhà": 0.55, "Dành cho Môi giới": 0.40, "Khác": 0.05}
MIN_HOT = 25            # tổng engagement tối thiểu coi là chủ đề NÓNG
MIN_TOPICS = 2          # cần ≥2 chủ đề mới mới xuất (chống spam, đúng luật pipeline)

# Map chu_de người hỏi (library, chi tiết) → chu_de bài viết (blog, taxonomy rộng).
# Chủ đề ĐÃ CÓ bài trong blog theo taxonomy này = đã trả lời → KHÔNG sinh trùng.
CHUDE_TO_TAXONOMY = {
    "thu-hoi-dat": "thu-hoi-den-bu",
    "den-bu": "thu-hoi-den-bu",
    "gpmb": "thu-hoi-den-bu",
    "tai-dinh-cu": "tai-dinh-cu-tam-tru",
    "thue-nha-tam": "tai-dinh-cu-tam-tru",
    "ho-tro-nha-o": "tai-dinh-cu-tam-tru",
    "mua-ban": "mua-ban",          # chưa có bài + CHỜ key moi-gioi.yml
    "cho-thue": "cho-thue",        # chưa có bài ✓
    "dich-vu": "dich-vu",          # chưa có bài ✓
    "khac": "",
}

# Chủ đề CHƯA có key tương ứng trong moi-gioi.yml → viết bài sẽ LỆCH (bài học mua-ban .trash).
# Evolve chỉ SINH topics cho chủ đề có key; chủ đề chờ key chỉ BÁO CÁO.
CHUDE_PROGRESS = {
    "mua-ban": "cần bổ sung key mua-ban vào _data/moi-gioi.yml trước khi sinh bài",
}

# Map chu_de trong library → HƯỚNG đối tượng bài viết nên phục vụ
CHUDE_TO_NHOM = {
    "thu-hoi-dat": "Dành cho Chủ nhà",
    "den-bu": "Dành cho Chủ nhà",
    "tai-dinh-cu": "Dành cho Chủ nhà",
    "gpmb": "Dành cho Chủ nhà",
    "thue-nha-tam": "Dành cho Chủ nhà",
    "ho-tro-nha-o": "Dành cho Chủ nhà",
    "mua-ban": "Dành cho Môi giới",
    "cho-thue": "Dành cho Môi giới",
    "dich-vu": "Dành cho Môi giới",
    "khac": "",
}


def load_posts():
    if not LIBRARY.exists():
        return []
    posts = []
    for line in LIBRARY.read_text(encoding="utf-8").splitlines():
        try:
            posts.append(json.loads(line))
        except Exception:
            continue
    return posts


def load_blog_topics():
    """Map chu_de → số bài blog đã có + nhom của từng bài."""
    used = defaultdict(int)
    nhom_count = defaultdict(int)
    if BLOG.exists():
        for p in BLOG.glob("*.md"):
            text = p.read_text(encoding="utf-8")
            m = re.search(r"^chu_de:\s*(.+)$", text, re.M)
            cd = m.group(1).strip().strip('"').strip("'") if m else "khac"
            used[cd] += 1
            m2 = re.search(r'^nhom:\s*"([^"]+)"', text, re.M)
            nhom_count[m2.group(1) if m2 else "?"] += 1
    return used, nhom_count


def main() -> int:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    posts = load_posts()
    used, nhom_count = load_blog_topics()
    today = date.today().isoformat()

    # ── SENSE + LEARN: độ nóng từng chu_de theo posts THẬT ───────────────
    hot = defaultdict(lambda: {"eng": 0, "count": 0, "questions": [], "max_date": ""})
    for p in posts:
        if p.get("loai") != "hoi-that":
            continue
        cd = p.get("chu_de", "khac")
        hot[cd]["eng"] += int(p.get("engagement", 0))
        hot[cd]["count"] += 1
        if len(hot[cd]["questions"]) < 3:
            hot[cd]["questions"].append(p.get("text", "")[:220])
        if p.get("date", "") > hot[cd]["max_date"]:
            hot[cd]["max_date"] = p.get("date", "")

    # ── EVOLVE 1: chủ đề NÓNG chưa có bài (theo taxonomy blog) + có key → topics ──
    new_topics = []
    waiting = []  # chủ đề nóng nhưng CHỜ key moi-gioi.yml (chưa sinh — chống bài lệch)
    for cd, d in sorted(hot.items(), key=lambda kv: -kv[1]["eng"]):
        if d["eng"] < MIN_HOT:
            continue
        tax = CHUDE_TO_TAXONOMY.get(cd, cd)
        have = used.get(tax, 0)
        if have > 0:
            continue  # đã có bài trả lời — không sinh trùng
        if cd in CHUDE_PROGRESS:
            waiting.append((cd, d, CHUDE_PROGRESS[cd]))
            continue
        if d["questions"]:
            new_topics.append({
                "chu_de": _compact(cd, d),
                "cau_hoi": d["questions"][0],
                "nguon": f"{d['count']} câu hỏi thật, {d['eng']} engagement",
            })

    # ── EVOLVE 2: phân bố đối tượng (đúng đối tượng mục tiêu) ────────────
    total = sum(nhom_count.values()) or 1
    balance_lines = []
    for nhom, target in TARGET_SPLIT.items():
        now = nhom_count.get(nhom, 0)
        pct = now / total
        status = "✓ đủ" if abs(pct - target) <= 0.12 else ("🔼 thiếu" if pct < target else "🔽 thừa")
        balance_lines.append(f"  - {nhom}: {now}/{total} ({pct:.0%}) — mục tiêu {target:.0%} [{status}]")
    chunha_share = nhom_count.get("Dành cho Chủ nhà", 0) / total
    shift_hint = ""
    if chunha_share < 0.45:
        shift_hint = ("→ Gợi ý tiến hóa: ưu tiên trả lời câu hỏi mới hướng 'Dành cho Chủ nhà' "
                      "(khách tìm xây/sửa nhà = đối tượng mục tiêu web); môi giới giữ 40%.")

    # ── GHI topics nếu đủ ≥2 (đúng luật chống spam) ──────────────────────
    if len(new_topics) >= MIN_TOPICS:
        payload = {
            "date": today,
            "source": "web-evolve-auto",
            "topics": [{k: v for k, v in t.items() if k != "nguon"} for t in new_topics],
            "note": f"Tự học từ {sum(hot[c]['count'] for c in hot)} câu hỏi thật — {len(new_topics)} chủ đề nóng chưa có bài. Nguồn library/posts.jsonl.",
        }
        out = TOPICS_DIR / f"evolve-{today}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        out = None

    # ── BÁO CÁO ──────────────────────────────────────────────────────────
    lines = [
        f"\n=== WEB EVOLVE {today} ===",
        f"📡 SENSE: {len(posts)} posts thật trong kho, {sum(hot[c]['count'] for c in hot)} câu hỏi thật.",
        f"🧠 LEARN — chủ đề nóng (engagement ≥ {MIN_HOT}, theo taxonomy blog):",
    ]
    for cd, d in sorted(hot.items(), key=lambda kv: -kv[1]["eng"])[:8]:
        tax = CHUDE_TO_TAXONOMY.get(cd, cd)
        lines.append(f"   {cd} (→ bài {tax}): eng={d['eng']} ({d['count']} hỏi) · bài đã có={used.get(tax,0)}")
    lines.append("🔄 EVOLVE — topics mới sinh:")
    if out:
        lines.extend(f"   + [{t['chu_de']}]" for t in new_topics)
        lines.append(f"   → file: {out.relative_to(SITE)} ({len(new_topics)} chủ đề, hợp lệ ≥2)")
    else:
        lines.append("   (không có chủ đề nóng chưa-trả-lời mới — web đã cover, chờ data nhu cầu mới)")
    if waiting:
        lines.append("⏳ CHỜ KEY moi-gioi.yml (nóng nhưng chưa viết được — tránh bài lệch):")
        for cd, d, why in waiting:
            lines.append(f"   - {cd} (eng={d['eng']}): {why}")
    lines.append("🎯 ĐỐI TƯỢNG (mục tiêu: khách xây/sửa nhà = Chủ nhà):")
    lines.extend(balance_lines)
    if shift_hint:
        lines.append(shift_hint)
    report = "\n".join(lines)
    print(report)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(report + "\n")
    (REPORT_DIR / f"evolve-{today}.md").write_text(report + "\n", encoding="utf-8")
    return 1 if out else 0


def _compact(cd: str, d: dict) -> str:
    """Chu_de ngắn gọn có nghĩa — từ câu hỏi thật nóng nhất, không bịa."""
    q = d["questions"][0]
    # lấy phần quan trọng của câu hỏi (bỏ từ hỏi lót), tối đa ~55 ký tự
    q = re.sub(r"^(mọi người|mấy bác|các bác|em|anh chị)[ ,：:]*", "", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q[:55] or cd


if __name__ == "__main__":
    sys.exit(main())