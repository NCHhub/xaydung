#!/usr/bin/env python3
"""quality_gate.py — TƯ PHÁP: cổng kiểm soát chất lượng bài blog TRƯỚC khi đăng.

Tách khỏi executor (write_blog.py / pipeline). Mô phỏng "bài thành công" của
Diamond (công thức trong _data/moi-gioi.yml: CÂU HỎI THẬT → NỖI ĐAU → GIẢI THÍCH
→ BẰNG CHỨNG THẬT → HÀNH ĐỘNG NHỎ) + yếu tố cá nhân Hải (SĐT, công trình thật,
hợp tác minh bạch). Rule-based, 0 token, model-agnostic.

Cách dùng:
  python3 quality_gate.py                     # tự dò bài mới chưa commit (git status _blog)
  python3 quality_gate.py file1.md file2.md   # kiểm tra file chỉ định
  python3 quality_gate.py --all               # kiểm tra MỌI bài trong _blog
  python3 quality_gate.py --json              # output JSON (bash dễ xử lý)

Exit code: 0 = PASS hết · 1 = có bài FAIL · 2 = lỗi chạy.
Pipeline CHỈ git add/push các file PASS (đọc từ stdout --json nếu cần).
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent.parent  # .../xaydung-site
BLOG_DIR = SITE / "_blog"

# ---- Yếu tố cá nhân Hải (chuẩn bài thành công) ----
PERSONAL = ["0983.601.366", "X.aladDin.vn", "công trình thật", "hợp tác lâu dài"]
THUHOI_SLUG = ["thu-hoi", "den-bu", "tai-dinh-cu", "giai-phong", "kiem-dem", "mat-bang", "ban-giao"]
BANG_GIA_BAN = [r"\d[\d.,]*\s*(tr|triệu|trieu)\s*/\s*m", r"\d[\d.,]*\s*(triệu|trieu|tr)\s*m2", r"13,5", r"19,5"]
PLACEHOLDERS = ["TODO", "lorem", "PASTE", "XXX", "placeholder"]
MIN_CHARS = 600
MIN_HEADINGS = 2


def git_untracked_blogs():
    """Bài _blog/ có thay đổi chưa commit (untracked ?? hoặc modified M)."""
    try:
        out = subprocess.run(["git", "-C", str(SITE), "status", "--porcelain"],
                             capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return []
    files = []
    for line in out.splitlines():
        if not line or len(line) < 4:
            continue
        p = line[3:].strip().strip('"')
        if p.startswith("_blog/") and p.endswith(".md"):
            files.append(SITE / p)
    return files


def check_file(path: Path):
    """Trả (verdict, list[(tên_check, pass, ghi_chú)])."""
    checks = []
    text = path.read_text(encoding="utf-8")
    name = path.name
    is_thuhoi = any(k in name for k in THUHOI_SLUG)

    # C1 — Front-matter
    fm = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not fm:
        checks.append(("front-matter", False, "Thiếu khối ---front-matter---"))
    else:
        body_meta = fm.group(1)
        ok = all(k in body_meta for k in ("title:", "date:", "description:"))
        checks.append(("front-matter", ok, "title/date/description" if ok else "Thiếu title/date/description"))

    body = text.split("---", 2)[2] if "---" in text else text

    # C2 — Độ dài
    checks.append(("nội_dung_đủ_dài", len(body) >= MIN_CHARS,
                   f"{len(body)} ký tự (cần ≥{MIN_CHARS})"))

    # C3 — Có câu hỏi thật (blockquote hoặc chứa "hỏi"/"?")
    has_q = ("*“" in body and "”*" in body) or ("?" in body) or ("hỏi" in body)
    checks.append(("câu_hỏi_thật", has_q, "có câu hỏi/anh dẫn" if has_q else "thiếu câu hỏi thật"))

    # C4 — Có hướng dẫn hành động (mô phỏng "HÀNH ĐỘNG NHỎ")
    has_action = ("Hành động" in body) or ("hành động" in body) or ("làm" in body and "nên" in body)
    checks.append(("hành_động_nhỏ", has_action, "có bước hành động" if has_action else "thiếu phần hành động"))

    # C5 — Yếu tố cá nhân Hải (ít nhất 1 trong 4; bắt buộc SĐT hoặc tên miền)
    personal_hits = [p for p in PERSONAL if p in body]
    checks.append(("yếu_tố_cá_nhân_Hải", len(personal_hits) >= 2,
                   ", ".join(personal_hits) if personal_hits else "thiếu SĐT/X.aladDin.vn/công trình thật"))

    # C6 — Nếu chủ đề thu hồi: KHÔNG được lẫn bảng giá xây nhà
    if is_thuhoi:
        bad = [b for b in BANG_GIA_BAN if re.search(b, body, re.I)]
        checks.append(("không_lẫn_bảng_giá_xây", not bad,
                       "OK — không có đơn giá xây" if not bad else f"CÓ đơn giá xây (tránh hiểu lầm): {bad}"))
    else:
        checks.append(("không_lẫn_bảng_giá_xây", True, "không thuộc chủ đề thu hồi"))

    # C7 — Không placeholder rác
    ph = [x for x in PLACEHOLDERS if x.lower() in body.lower()]
    checks.append(("không_placeholder", not ph, "sạch" if not ph else f"có {ph}"))

    # C8 — Đủ heading (cấu trúc rõ ràng)
    n_head = len(re.findall(r"^#{1,3} ", body, re.M))
    checks.append(("cấu_trúc_heading", n_head >= MIN_HEADINGS, f"{n_head} heading (cần ≥{MIN_HEADINGS})"))

    passed = all(p for _, p, _ in checks)
    return ("PASS" if passed else "FAIL"), checks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", help="file .md cần kiểm tra (mặc định: bài mới chưa commit)")
    ap.add_argument("--all", action="store_true", help="kiểm tra mọi bài trong _blog")
    ap.add_argument("--json", action="store_true", help="output JSON")
    args = ap.parse_args()

    if args.all:
        files = sorted(BLOG_DIR.glob("*.md"))
    elif args.files:
        files = [Path(f) for f in args.files]
    else:
        files = git_untracked_blogs()
        if not files:
            print("[quality_gate] Không có bài mới chưa commit — không có gì để kiểm tra.")
            return 0

    results = []
    for f in files:
        if not f.exists():
            results.append({"file": str(f), "verdict": "SKIP", "checks": [], "note": "file không tồn tại"})
            continue
        verdict, checks = check_file(f)
        results.append({"file": str(f), "verdict": verdict,
                        "checks": [{"check": c, "pass": p, "note": n} for c, p, n in checks]})

    if args.json:
        print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"\n=== {r['verdict']} {r['file']} ===")
            for c in r.get("checks", []):
                mark = "✓" if c["pass"] else "✗"
                print(f"  {mark} {c['check']}: {c['note']}")
            if r.get("note"):
                print(f"  ⚠ {r['note']}")

    n_fail = sum(1 for r in results if r["verdict"] == "FAIL")
    if args.json:
        return 1 if n_fail else 0
    if n_fail:
        print(f"\n[quality_gate] ❌ {n_fail}/{len(results)} bài FAIL — KHÔNG push các bài này.")
        return 1
    print(f"\n[quality_gate] ✅ {len(results)}/{len(results)} bài PASS — sẵn sàng đăng.")
    return 0


if __name__ == "__main__":
    sys.exit(main())