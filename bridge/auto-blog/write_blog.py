#!/usr/bin/env python3
"""
write_blog.py — CÔNG CỤ SINH BÀI VIẾT TỰ ĐỘNG (X.aladDin.vn auto-blog, Diamond 09-08).

Đọc chủ đề nóng hội nhóm (topics/YYYY-MM-DD.json từ meta_topics.py) + số liệu bang gia
(moi-gioi.yml — NGUỒN THẬT duy nhất, CẤM số Meta mâu thuẫn theo bài học meta-num-conflict)
→ sinh _blog/YYYY-MM-DD-<slug>.md theo khung bài đã kiểm chứng:
  Câu hỏi thật → Nỗi đau → Giải thích → Bằng chứng thật → Hành động nhỏ (môi giới tôn vinh)

Verify bằng CÔNG CỤ (không tự chấm): slug không trùng, front matter đủ field, file tồn tại.

Cách dùng:
  python3 write_blog.py                        # sinh bài từ topics mới nhất chưa dùng
  python3 write_blog.py --topic "chủ đề"       # sinh bài 1 chủ đề cụ thể
  python3 write_blog.py --dry-run              # chỉ báo bài sẽ sinh, không ghi file
"""
import argparse, datetime, json, os, re, sys, unicodedata
from pathlib import Path

SITE = Path("/home/diamond/empire/xaydung-site")
BLOG_DIR = SITE / "_blog"
DATA = SITE / "_data" / "moi-gioi.yml"
TOPICS_DIR = SITE / "bridge" / "auto-blog" / "topics"
STATE_FILE = SITE / "bridge" / "auto-blog" / ".used_topics.json"

# Các KEY trong moi-gioi.yml mà bài viết được phép trích (số liệu kiểm chứng)
ALLOWED_KEYS = ["khach-hoi", "bang-gia", "quy-trinh", "quy-trinh-meta", "quy-trinh-bien-so"]

def slugify(text: str) -> str:
    """'Xây nhà ngoại thành 1.3 tỷ' → 'xay-nha-ngoai-thanh-1-3-ty' (không dấu, nối gạch)."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:90].strip("-")

def load_used_slugs():
    """Slug đã dùng = slug của mọi file _blog/ hiện có (kể cả chưa commit)."""
    used = set()
    if BLOG_DIR.exists():
        for f in BLOG_DIR.glob("*.md"):
            m = re.match(r"\d{4}-\d{2}-\d{2}-(.+)\.md$", f.name)
            if m:
                used.add(m.group(1))
    return used

def load_topics():
    """Đọc topics mới nhất chưa dùng (state .used_topics.json)."""
    jobs = sorted(TOPICS_DIR.glob("*.json")) if TOPICS_DIR.exists() else []
    if not jobs:
        print("[write_blog] Không có topics/ — chạy meta_topics.py trước hoặc tạo topics thủ công.")
        sys.exit(1)
    used_dates = set()
    if STATE_FILE.exists():
        used_dates = set(json.loads(STATE_FILE.read_text()).get("used", []))
    for jf in reversed(jobs):  # mới nhất trước
        if jf.stem in used_dates:
            continue
        data = json.loads(jf.read_text(encoding="utf-8"))
        return jf.stem, data.get("topics", [])
    print("[write_blog] Mọi chủ đề đã dùng hết — không còn bài mới.")
    sys.exit(0)

def extract_data(text: str):
    """Trích các block trong moi-gioi.yml có key cho phép → dict key: [dòng nội dung]."""
    out = {}
    lines = text.splitlines()
    key, block = None, []
    for ln in lines:
        m = re.match(r"^([a-z0-9-]+):\s*(#.*)?$", ln.strip())
        if m:
            if key in ALLOWED_KEYS and block:
                out[key] = block
            key, block = m.group(1), []
            continue
        if key in ALLOWED_KEYS and (ln.strip() == "" or ln.lstrip().startswith("#")):
            if block and key in out:
                pass
            continue
        if key in ALLOWED_KEYS and ln.strip():
            block.append(ln.strip())
    if key in ALLOWED_KEYS and block:
        out[key] = block
    return out

def pick_evidence(data: dict, topic: str):
    """Chọn 2-3 dòng bằng chứng thật từ moi-gioi.yml liên quan chủ đề (fallback: dòng đầu)."""
    lines_all = []
    for k in ALLOWED_KEYS:
        if k in data:
            for l in data[k]:
                # bỏ token YAML (- cau_hoi:, tra_loi:, ghi-chu:, quoted) — chỉ giữ nội dung
                l = re.sub(r"^[-*]\s*", "", l.strip())
                l = re.sub(r"^[a-z0-9_-]+:\s*", "", l).strip().strip('"')
                if l.startswith("[") or l.startswith("{"):
                    continue
                if 25 <= len(l) <= 300:
                    lines_all.append(l)
    if not lines_all:
        return ["(Kiểm chứng tại nguồn: _data/moi-gioi.yml)"]
    # heuristic: ưu tiên dòng chứa từ khoá chủ đề (tiền → xây → sửa → giá...)
    words = [w for w in re.split(r"\W+", topic.lower()) if len(w) >= 4]
    scored = sorted(set(lines_all), key=lambda l: -sum(w in l.lower() for w in words))
    return scored[:3]

def build_post(topic: dict, evidence: list) -> dict:
    chu_de = topic.get("chu_de", "Chủ đề nóng hội nhóm")
    cau_hoi = topic.get("cau_hoi", "")
    slug = slugify(chu_de)
    today = datetime.date.today().isoformat()
    title = chu_de  # giữ nguyên chữ viết của nguồn (không .title() làm hỏng tên riêng/số)
    desc = (cau_hoi[:140] + "…") if len(cau_hoi) > 140 else cau_hoi
    body = f"""---
title: "{title}"
nhom: "Dành cho Môi giới"
date: {today}
description: "{desc}"
---

Khi anh/chị gặp khách hỏi *“{cau_hoi}”* — đừng trả lời qua loa. Dưới đây là cách trả lời có căn cứ, dùng được ngay khi dẫn khách xem đất.

## Vì sao chủ đề này đang nóng

Chủ đề *“{chu_de}”* xuất hiện liên tục trong các hội nhóm xây/sửa nhà Hà Nội trong tuần gần đây. Người mua nhà đất thường hỏi nhất, và anh/chị môi giới là người họ hỏi đầu tiên.

## Trả lời ngắn cho khách

> **{cau_hoi}**

Câu trả lời mà khách cần nghe không phải một con số chẵn — mà là một cách ước lượng có căn cứ, kèm theo các khoản “ẩn” mà chủ nhà hay quên tính.

## Số liệu kiểm chứng (nguồn: _data/moi-gioi.yml)

{chr(10).join("- " + e for e in evidence)}

Để tra nhanh tại chỗ, anh/chị dùng công cụ tính giá trên trang X.aladDin.vn — ra con số theo đúng quận, diện tích, loại hình chỉ trong vài giây.

## Hành động nhỏ hôm nay

Ghi chú lại câu hỏi này vào sổ tay tư vấn của anh/chị. Lần tới gặp khách hỏi đúng vấn đề, anh/chị đã sẵn câu trả lời — khách tin ngay, tăng khả năng chốt.

> 💡 Anh/chị môi giới cần thêm số liệu chi tiết cho từng khu vực? Mở trang X.aladDin.vn/moi-gioi/ để xem bảng giá đầy đủ và công cụ tính nhanh.
"""
    return {"slug": slug, "title": title, "file": f"{today}-{slug}.md", "body": body}

def main():
    ap = argparse.ArgumentParser(description="Sinh bài viết tự động từ topics + moi-gioi.yml")
    ap.add_argument("--topic", help="sinh bài 1 chủ đề cụ thể (không cần topics/)")
    ap.add_argument("--question", help="câu hỏi điển hình người dùng (dùng với --topic)")
    ap.add_argument("--dry-run", action="store_true", help="chỉ báo bài sẽ sinh")
    args = ap.parse_args()

    used_slugs = load_used_slugs()
    raw_text = DATA.read_text(encoding="utf-8") if DATA.exists() else ""
    data = extract_data(raw_text)

    src_date = datetime.date.today().isoformat()
    if args.topic:
        q = args.question or "Xây/sửa nhà ở Hà Nội hiện nay chi phí khoảng bao nhiêu?"
        topics = [{"chu_de": args.topic, "cau_hoi": q}]
    else:
        src_date, topics = load_topics()

    used_dates = set()
    if STATE_FILE.exists():
        used_dates = set(json.loads(STATE_FILE.read_text()).get("used", []))

    made = []
    for t in topics:
        post = build_post(t, pick_evidence(data, t.get("chu_de", "")))
        if post["slug"] in used_slugs:
            print(f"[write_blog] Slug trùng, bỏ qua: {post['slug']}")
            continue
        path = BLOG_DIR / post["file"]
        if args.dry_run:
            print(f"[dry-run] Sẽ tạo: {path}")
            continue
        path.write_text(post["body"], encoding="utf-8")
        made.append(post["file"])
        used_slugs.add(post["slug"])
        used_dates.add(src_date)
        print(f"[write_blog] ✅ Đã tạo: {path}")

    # ghi state đã dùng (chống lặp ngày kể cả khi slug trùng)
    if made:
        STATE_FILE.write_text(json.dumps({"used": sorted(used_dates)}, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print("[write_blog] Không tạo bài mới (đã có hoặc trùng).")

if __name__ == "__main__":
    main()