#!/usr/bin/env python3
"""xdhub_topics.py — Tận dụng XD-HUB (730 câu hỏi thật Zalo) → topics cho write_blog.
0 token, theo contract topics/*.json {date, source, topics:[{chu_de, cau_hoi}]}.
Đọc câu hỏi thật → lọc chất lượng → chọn top theo segment nóng → ghi topics.
"""
import json, re, sqlite3, unicodedata
from pathlib import Path

DB = Path.home() / "empire/shared/bds-xd-hub/xd-hub.db"
SITE = Path.home() / "empire/xaydung-site"
TOPICS_DIR = SITE / "bridge/auto-blog/topics"
BLOG_DIR = SITE / "_blog"

# Segment nóng theo XD-HUB report (ưu tiên nỗi đau số 1 = pháp lý) — tên key thật trong DB
SEGMENT_PRIORITY = ["giay-to-phap-ly", "thau-gia", "tai-chinh",
                    "noi-that-hoan-thien", "sua-chua", "xay-moi"]

# Từ khóa ngành theo segment (report XD-HUB §2) — lọc câu hỏi THẬT của khách, bỏ chuyện nội bộ
SEGMENT_KEYWORDS = {
    "giay-to-phap-ly": ["quy hoach", "sổ đỏ", "sổ hồng", "giấy phép", "gpxd", "thu hồi", "đền bù",
                        "tách thửa", "một cửa", "kiểm đếm", "pháp lý", "bồi thường", "tái định cư",
                        "cắm mốc", "đất bị", "dự án", "hồ sơ", "thủ tục", "đăng ký", "công chứng"],
    "thau-gia": ["nhà thầu", "đội thợ", "thầu", "báo giá", "hợp đồng", "vật tư", "bảo hành",
                 "nghiệm thu", "tiến độ", "phát sinh", "công thợ", "m2", "m²"],
    "tai-chinh": ["vay", "tiền", "chi phí", "kinh phí", "ngân sách", "tài chính", "trả góp",
                  "giá xây", "bao nhiêu tiền", "tổng chi"],
    "noi-that-hoan-thien": ["nội thất", "hoàn thiện", "thiết kế", "điện nước", "sơn", "gạch",
                            "trần", "cửa", "tủ", "bếp"],
    "sua-chua": ["sửa nhà", "sửa chữa", "cải tạo", "nâng tầng", "chống thấm", "thấm", "nứt",
                 "mối", "hỏng", "sàn"],
    "xay-moi": ["xây nhà", "xây mới", "xây thô", "làm móng", "thi công", "xây dựng", "mấy tầng",
                "bao nhiêu tầng", "diện tích", "mặt tiền"],
}

def slugify(text: str) -> str:
    text = text.replace('đ', 'd').replace('Đ', 'd')
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:90].strip("-")

def clean_question(q: str) -> str:
    """Chuẩn hóa câu hỏi thật: bỏ tên người/ký tự thừa, giữ verbatim phần hỏi."""
    q = re.sub(r"^\[[^\]]*\]\s*", "", q)          # [Tên|Tên] → bỏ
    q = re.sub(r"\s+", " ", q).strip().strip('"').strip()
    return q

def main():
    db = sqlite3.connect(DB)
    # Câu hỏi thật + segment của thread chứa nó
    rows = db.execute("""
        SELECT q.text, t.segments
        FROM zalo_cau_hoi q
        JOIN zalo_thread t ON substr(q.thread_id, 1, instr(q.thread_id, '|')-1)
                            = substr(t.thread_id, 1, instr(t.thread_id, '_')-1)
        WHERE length(q.text) >= 15
    """).fetchall()

    used_slugs = set()
    for f in BLOG_DIR.glob("*.md"):
        m = re.match(r"\d{4}-\d{2}-\d{2}-(.+)\.md$", f.name)
        if m:
            used_slugs.add(m.group(1))

    # Gom theo segment ưu tiên, mỗi segment chọn câu hỏi tốt nhất
    per_seg = {s: [] for s in SEGMENT_PRIORITY}
    for text, segs in rows:
        q = clean_question(text)
        if not q:
            continue
        q_low = q.lower()
        if "?" not in q and "?" not in q:  # câu hỏi thật phải có dấu hỏi
            continue
        if len(q) < 20 or len(q) > 250:
            continue
        for s in (segs or "").split(","):
            s = s.strip()
            if s in per_seg:
                # phải chứa ≥1 từ khóa ngành của segment (bỏ chuyện nội bộ)
                kws = SEGMENT_KEYWORDS.get(s, [])
                if kws and not any(k in q_low for k in kws):
                    continue
                per_seg[s].append((q, sum(1 for k in kws if k in q_low)))  # (câu, số từ khóa)

    topics = []
    QUESTION_STARTS = ["có", "bao nhiêu", "chi phí", "giá", "thủ tục", "làm sao", "như thế nào",
                       "được", "xây", "sửa", "quy hoạch", "thu hồi", "đền bù", "đất", "nhà",
                       "giấy", "hợp đồng", "vay", "vật tư", "thiết kế", "nội thất", "hoàn thiện"]
    for seg in SEGMENT_PRIORITY:
        cands = sorted(per_seg[seg], key=lambda x: (-x[1], -len(x[0])))
        for q, score in cands[:8]:
            q_low = q.lower()
            # bỏ câu trò chuyện nội bộ rõ ràng
            if any(x in q_low for x in ["anh ơi", "shop ơi", "duy ơi", "bạn ơi", "các bác ơi",
                                        "bên mình", "thảo ơi", "vũ ơi", "vinh ơi"]):
                continue
            # bỏ chào hàng B2B (xưởng/thi công tự quảng cáo) — không phải nhu cầu Chủ nhà
            if any(x in q_low for x in ["tên là", "xưởng sản xuất", "gửi em bản vẽ",
                                        "liên hệ dần", "liên hệ em", "bên em chuyên",
                                        "mình chuyên", "làm tại xưởng"]):
                continue
            # ưu tiên câu chuẩn: bắt đầu bằng từ nghi vấn/ngành, không "e","em","tôi" đứng đầu
            first = q_low.strip().split(" ")[0].strip(".,")
            if first not in QUESTION_STARTS and not any(k in q_low for k in SEGMENT_KEYWORDS[seg][:4]):
                continue
            # làm mượt chu_de: bỏ tiền tố "e/em/anh/tôi" + mấy từ chêm
            cd = re.sub(r"^(e|em|anh|tôi|mình|chú|bác) ", "", q.strip(), flags=re.I)
            cd = re.sub(r"\s+", " ", cd).strip()
            cd = cd[:80].rstrip(" ,.?")
            slug = slugify(cd)
            if slug in used_slugs:
                continue
            used_slugs.add(slug)
            topics.append({"chu_de": cd, "cau_hoi": q,
                           "segment": seg})
            break  # 1 topic/segment/lần chạy (tránh spam 1 chủ đề)

    if len(topics) < 2:
        print(f"Chỉ {len(topics)} topics mới — chưa đủ ≥2, không ghi (chống spam).")
        return

    today = __import__("datetime").date.today().isoformat()
    payload = {
        "date": today,
        "source": "xd-hub-zalo-730",
        "topics": [{"chu_de": t["chu_de"], "cau_hoi": t["cau_hoi"]} for t in topics],
        "note": f"Tự học từ XD-HUB: 730 câu hỏi thật Zalo (segment nóng: pháp lý/đền bù → thầu/báo giá → tài chính...). {len(topics)} chủ đề mới.",
    }
    out = TOPICS_DIR / f"xd-hub-{today}.json"
    # KHÔNG ghi đè bản đã chốt (MCP chốt = chuẩn, heuristic chỉ đề xuất khi chưa có)
    if out.exists():
        try:
            existing = json.loads(out.read_text(encoding="utf-8"))
            if existing.get("topics"):
                print(f"⏭️ {out.name} đã có {len(existing['topics'])} topics (bản MCP chốt) — heuristic không ghi đè.")
                return
        except Exception:
            pass
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ topics: {out.relative_to(SITE)} ({len(topics)} chủ đề)")
    for t in payload["topics"]:
        print(f"   - {t['chu_de'][:70]}")

if __name__ == "__main__":
    main()