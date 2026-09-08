#!/usr/bin/env python3
"""
meta_topics.py — CÔNG CỤ THU CHỦ ĐỀ NÓNG HỘI NHÓM (X.aladDin.vn auto-blog, Diamond 09-08).

Lấy chủ đề nóng từ Meta AI (hiểu người dùng chia sẻ gì trong hội nhóm xây/sửa nhà HN)
→ lưu topics/YYYY-MM-DD.json để write_blog.py tiêu thụ.

0 token AI ở chỗ này (chỉ gọi orchestrate Meta AI qua ai_ask.py --ai meta).

Cách dùng:
  python3 meta_topics.py                  # thu chủ đề hôm nay, lưu topics/ (chống trùng ngày)
  python3 meta_topics.py --force-link     # chỉ in link trực tiếp (không vào topics/)

Brief gửi Meta AI được định nghĩa BÊN DƯỚI — sửa tại đây khi muốn đổi hướng câu hỏi.
Lưu ý (bài học meta-num-conflict): Meta chỉ lấy KHUNG CHỦ ĐỀ + câu hỏi thật, KHÔNG lấy số liệu
giá thay thế. Mọi số liệu giá trong bài viết lấy từ moi-gioi.yml (write_blog.py đọc riêng).
"""
import argparse, datetime, json, os, subprocess, sys
from pathlib import Path

SITE = Path("/home/diamond/empire/xaydung-site")
TOPICS_DIR = SITE / "bridge" / "auto-blog" / "topics"
AI_ASK = Path("/home/diamond/empire/fail-states/meta/ai_ask.py")

# Brief Meta AI — câu hỏi điều hướng hội nhóm (sửa tại đây, Diamond có thể đổi hướng)
BRIEF = """Bạn đọc giúp các hội nhóm Facebook về xây sửa nhà ở Hà Nội (nội thất, xây nhà, sửa nhà, tìm thầu).
Hãy cho tôi 3 chủ đề ĐANG NÓNG nhất tuần này mà chủ nhà thực sự hỏi/chia sẻ/than vãn,
kèm 1-2 câu hỏi điển hình nguyên văn người dùng hay hỏi cho mỗi chủ đề.
Ưu tiên chủ đề mà MÔI GIỚI BĐS cần biết để tư vấn khách xây/sửa nhà.
Trả lời bằng tiếng Việt, ngắn gọn, format:
CHỦ ĐỀ 1: <tên>
CÂU HỎI: <câu hỏi điển hình>
CHỦ ĐỀ 2: <tên>
CÂU HỎI: <câu hỏi điển hình>
CHỦ ĐỀ 3: <tên>
CÂU HỎI: <câu hỏi điển hình>"""


def call_meta_ai(timeout=240):
    """Gọi Meta AI (ai_ask.py --ai meta -f brief) — đã login thu.nguyenxuan."""
    brief_file = "/tmp/meta_topics_brief.txt"
    Path(brief_file).write_text(BRIEF, encoding="utf-8")
    cmd = [sys.executable, str(AI_ASK), "--ai", "meta", "-f", brief_file, "--timeout", str(timeout)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 30)
        out = (r.stdout or "") + (("\n" + r.stderr) if r.stderr else "")
        print("[meta_topics] exit:", r.returncode)
        return out
    except Exception as e:
        print("[meta_topics] LỖI gọi Meta AI:", e)
        return ""


def parse_topics(raw):
    """Tách raw text Meta → list {chu_de, cau_hoi}. Trả [] nếu không parse được."""
    topics, cur = [], {}
    for line in raw.splitlines():
        line = line.strip().lstrip("-•*").strip()
        low = line.lower()
        if low.startswith("chủ đề") or low.startswith("chu de"):
            if cur.get("chu_de"):
                topics.append(cur)
            cur = {"chu_de": line.split(":", 1)[1].strip() if ":" in line else line}
        elif low.startswith("câu hỏi") or low.startswith("cau hoi"):
            cur["cau_hoi"] = line.split(":", 1)[1].strip() if ":" in line else line
        elif low.startswith("chủ đề 1") or low.startswith("chủ đề 2") or low.startswith("chủ đề 3"):
            if cur.get("chu_de"):
                topics.append(cur)
            cur = {"chu_de": line.split(":", 1)[1].strip() if ":" in line else line}
    if cur.get("chu_de"):
        topics.append(cur)
    return [t for t in topics if t.get("chu_de")]


def main():
    ap = argparse.ArgumentParser(description="Thu chủ đề nóng hội nhóm từ Meta AI")
    ap.add_argument("--force-link", action="store_true", help="chỉ in link trực tiếp")
    args = ap.parse_args()

    today = datetime.date.today().isoformat()
    out_file = TOPICS_DIR / f"{today}.json"

    if not args.force_link and out_file.exists():
        print(f"[meta_topics] Đã có topics hôm nay: {out_file} (bỏ qua, dùng --force-link để chạy lại)")
        return

    raw = call_meta_ai()
    topics = parse_topics(raw)
    if not topics:
        print("[meta_topics] Không parse được chủ đề. Output thô:\n", raw[:500])
        sys.exit(1)

    # Lưu cả raw + parsed (raw = bằng chứng nguồn Meta, parsed = cho write_blog)
    TOPICS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"date": today, "source": "meta-ai-live", "raw": raw, "topics": topics}
    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[meta_topics] ✅ Đã lưu {len(topics)} chủ đề → {out_file}")
    for i, t in enumerate(topics, 1):
        print(f"  {i}. {t['chu_de']} — {t.get('cau_hoi','')[:80]}")


if __name__ == "__main__":
    main()