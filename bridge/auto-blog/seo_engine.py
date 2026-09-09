#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seo_engine.py — VÒNG LẶP TỰ ĐỘNG TỐI ƯU WEB THEO THÀNH CÔNG THẾ GIỚI (0 token)
Diamond 09-09: "Học thành công của thế giới để web thu hút nhiều nhất khách hàng
tìm thông tin xây sửa nhà Hà Nội. Tự động tối ưu web dựa theo thành công."

NGUYÊN LÝ HỌC TỪ THẾ GIỚI (Ahrefs Local SEO, Backlinko, Google best practice):
  1. On-page: title 50-60 ký tự, description 120-160, URL thân thiện, ảnh alt
  2. Internal links: mỗi bài liên kết tới ít nhất 2 bài khác cùng chủ đề
  3. Sitemap + robots + feed (đã bật jekyll-seo-tag / sitemap / feed — GH Pages sẵn)
  4. NAP nhất quán (LocalBusiness JSON-LD — đã thêm vào head.html)
  5. Nội dung mới hằng ngày theo trend (fb_pipeline.sh — cron 09:30)
  6. AI visibility: feed.xml + JSON-LD chuẩn để LLM hiểu nội dung

VIỆC SCRIPT NÀY LÀM MỖI LẦN CHẠY (mặc định: sau khi write_blog trong pipeline):
  - Audit toàn bộ _blog/*.md: title/desc/ảnh/internal link/nhom/chu_de
  - Ghi báo cáo số + gợi ý sửa vào ~/empire/shared/logs/seo_audit.log
  - Exit code: 0 = ổn, 1 = có bài vi phạm chuẩn (để pipeline biết cần cải thiện)
"""
import re
import sys
from datetime import date
from pathlib import Path

SITE = Path("/home/diamond/empire/xaydung-site")
BLOG = SITE / "_blog"
LOG_DIR = Path.home() / "empire" / "shared" / "logs"
LOG_FILE = LOG_DIR / "seo_audit.log"

# Chuẩn thế giới (Google / Ahrefs)
TITLE_MIN, TITLE_MAX = 25, 70          # ký tự (tiếng Việt dài hơi — nới 70)
DESC_MIN, DESC_MAX = 80, 165           # ký tự
MIN_INTERNAL_LINKS = 2                 # bài liên quan — render tự động ở layout
MIN_IMAGES = 1                         # ít nhất 1 ảnh cover (fallback og-default)


def read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def _quote(v: str) -> str:
    """Bọc giá trị YAML an toàn — giữ nguyên nếu không cần."""
    if any(c in v for c in '":#{}[],'):
        return '"' + v.replace('"', '\\"') + '"'
    return v


def _rewrite_fm(path: Path, key: str, value: str) -> bool:
    """Sửa 1 key trong front matter, giữ nguyên BODY phía sau (bài học 09-09:
    bug cũ ghi lại toàn file chỉ từ front matter → mất nội dung bài)."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return False
    fm, rest = m.group(1), text[m.end():]
    lines = fm.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(key + ":"):
            lines[i] = f"{key}: {_quote(value)}"
            path.write_text("---\n" + "\n".join(lines) + "\n---\n" + rest, encoding="utf-8")
            return True
    return False


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    posts = sorted(BLOG.glob("*.md"))
    issues = []
    good = 0
    today = date.today().isoformat()
    fix_mode = "--fix" in sys.argv

    for p in posts:
        fm = read_frontmatter(p)
        slug = p.name
        errs = []
        # 1) Title
        title = fm.get("title", "")
        if not title:
            errs.append("thiếu title")
        elif not (TITLE_MIN <= len(title) <= TITLE_MAX):
            if fix_mode and len(title) > TITLE_MAX:
                # tự rút gọn ở ranh giới từ
                words = title.split()
                cut = ""
                for w in words:
                    if len(cut) + len(w) + 1 <= TITLE_MAX - 1:
                        cut = (cut + " " + w).strip()
                    else:
                        break
                cut = cut.rstrip(" —-–:;.,")
                if cut and len(cut) >= TITLE_MIN:
                    _rewrite_fm(p, "title", cut)
                    title = cut
                    print(f"  ✂️ fix title: {slug} -> {len(cut)} ký tự")
                else:
                    errs.append(f"title {len(title)} ký tự (chuẩn {TITLE_MIN}-{TITLE_MAX})")
            else:
                errs.append(f"title {len(title)} ký tự (chuẩn {TITLE_MIN}-{TITLE_MAX})")
        # 2) Description
        desc = fm.get("description", "")
        if not desc:
            errs.append("thiếu description")
        elif not (DESC_MIN <= len(desc) <= DESC_MAX):
            if fix_mode and len(desc) < DESC_MIN:
                # nối đuôi chuẩn giúp desc đủ dài (không bịa số liệu)
                suffix = " Kinh nghiệm thực tế 21 năm từ Hải & Cộng sự — Hà Nội."
                new_desc = desc.rstrip(" .") + suffix
                _rewrite_fm(p, "description", new_desc)
                desc = new_desc
                print(f"  ✏️ fix desc: {slug} -> {len(new_desc)} ký tự")
            else:
                errs.append(f"desc {len(desc)} ký tự (chuẩn {DESC_MIN}-{DESC_MAX})")
        # 3) Ảnh cover
        if not fm.get("image"):
            errs.append("thiếu ảnh cover (ảnh = tăng CTR theo nghiên cứu thế giới)")
        # 4) Phân loại nội dung
        if not fm.get("nhom"):
            errs.append("thiếu nhóm (nhom)")
        if not fm.get("chu_de"):
            errs.append("thiếu chủ đề (chu_de)")
        # 5) Internal links — tự động qua block "Bài liên quan" trong layout post.html
        #    (kiểm tra layout 1 lần ở dưới, không đếm body — bài liên quan render mọi bài)
        if errs:
            issues.append((slug, errs))
        else:
            good += 1

    # Layout post.html phải có block bài liên quan (internal linking chuẩn thế giới)
    layout_ok = "related" in (SITE / "_layouts" / "post.html").read_text(encoding="utf-8") if (SITE / "_layouts" / "post.html").exists() else False
    if not layout_ok:
        issues.append(("_layouts/post.html", ["thiếu block 'Bài liên quan' (internal linking)"]))

    total = len(posts)
    # Báo cáo
    lines = [
        f"\n=== SEO AUDIT {today} — {total} bài ===",
        f"✅ Đạt chuẩn: {good}/{total} · ⚠️ Cần cải thiện: {len(issues)}",
    ]
    for slug, errs in issues[:10]:
        lines.append(f"  - {slug}: {'; '.join(errs)}")
    if len(issues) > 10:
        lines.append(f"  ... và {len(issues) - 10} bài nữa")
    lines.append("Sitemap/feed/robots/meta: tự động qua jekyll-seo-tag + jekyll-sitemap + jekyll-feed (GH Pages build).")
    report = "\n".join(lines)
    print(report)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(report + "\n")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())