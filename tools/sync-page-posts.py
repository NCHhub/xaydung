#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync-page-posts.py — Đồng bộ BÀI ĐÃ ĐĂNG trên các fanpage xây nhà Hà Nội lên web x.aladdin.vn

NGUỒN THẬT (không bịa — LUẬT #11):
  ~/empire/shared/knowledge/page-posts/page-posts-*.json
  (thư viện bài đăng P1 Nguyễn Cao Hải / P2 KTS Nguyễn Cao Hải và Cộng sự / P3 25 năm Xây nhà trọn gói)

QUY TẮC:
  - CHỈ lấy bài status = POSTED (đã thật sự lên page) + có link bài (post_url/url).
  - Ảnh: copy ảnh gốc trong ~/empire/shared/knowledge/page-posts/img/ → assets/img/page-posts/.
  - Ghi page-posts.json (web đọc) + copy ảnh, CHỈ commit/push khi có thay đổi.
  - 0 token LLM, 0 đồng.

Chạy:  python3 ~/empire/xaydung-site/tools/sync-page-posts.py
Cron:  27 */6 * * *  ~/empire/xaydung-site/tools/sync-page-posts.py > /dev/null 2>&1
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # ~/empire/xaydung-site
SRC_DIR = Path.home() / "empire/shared/knowledge/page-posts"
IMG_SRC = SRC_DIR / "img"
IMG_DST = ROOT / "assets/img/page-posts"
OUT_FILE = ROOT / "page-posts.json"

PAGE_NAMES = {
    "P1": "Nguyễn Cao Hải",
    "P2": "KTS Nguyễn Cao Hải và Cộng sự",
    "P3": "25 năm Xây nhà trọn gói Hà Nội",
}


def norm_title(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def load_posts():
    """Gom MỌI file page-posts-*.json (bỏ .bak), dedupe theo tiêu đề."""
    seen, items = set(), []
    files = sorted(SRC_DIR.glob("page-posts-*.json"))
    for f in files:
        if ".bak" in f.name:
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"⚠️ Bỏ qua {f.name}: {e}", file=sys.stderr)
            continue
        if not isinstance(data, list):
            continue
        for p in data:
            if not isinstance(p, dict):
                continue
            status = (p.get("status") or "").strip().upper()
            url = (p.get("post_url") or p.get("url") or "").strip()
            if status != "POSTED" or not url:
                continue          # chỉ bài ĐÃ đăng + có link thật
            title = (p.get("title") or "").strip()
            if not title:
                continue
            key = norm_title(title)
            if key in seen:
                continue
            seen.add(key)
            items.append(p)
    return items


def copy_image(rel_path: str) -> str:
    """Copy ảnh nguồn → assets/img/page-posts/; trả URL web (hoặc '' nếu không có)."""
    rel_path = (rel_path or "").strip()
    if not rel_path:
        return ""
    name = os.path.basename(rel_path)
    src = IMG_SRC / name
    if not src.exists():
        # thử resolve theo path tương đối từ ~/empire
        cand = Path.home() / "empire" / rel_path
        src = cand if cand.exists() else None
    if not src or not src.exists():
        return ""
    IMG_DST.mkdir(parents=True, exist_ok=True)
    dst = IMG_DST / name
    if (not dst.exists()) or src.stat().st_mtime > dst.stat().st_mtime:
        shutil.copy2(src, dst)
    return f"/assets/img/page-posts/{name}"


def main():
    posts = load_posts()
    if not posts:
        print("Không có bài POSTED nào trong thư viện — giữ nguyên page-posts.json", file=sys.stderr)
        return 0

    # sắp xếp mới nhất trước (ts dạng YYYY-MM-DD; thiếu thì xuống cuối)
    posts.sort(key=lambda p: (p.get("ts") or "0000-00-00"), reverse=True)

    items = []
    for p in posts:
        pk = (p.get("page_key") or "").strip().upper()
        items.append({
            "page": pk,
            "page_name": PAGE_NAMES.get(pk, pk or "Fanpage"),
            "title": (p.get("title") or "").strip(),
            "hook": (p.get("hook") or "").strip(),
            "body": (p.get("body") or "").strip(),
            "steps": [s for s in (p.get("img_steps") or []) if str(s).strip()],
            "image": copy_image(p.get("image") or ""),
            "post_url": (p.get("post_url") or p.get("url") or "").strip(),
            "ts": (p.get("ts") or "").strip(),
        })

    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    data = {
        "updated": now,
        "source": "Fanpage Hải & Cộng sự (P1/P2/P3) — bài đã đăng thật",
        "count": len(items),
        "items": items,
    }

    new_text = json.dumps(data, ensure_ascii=False, indent=2)
    old_text = OUT_FILE.read_text(encoding="utf-8") if OUT_FILE.exists() else ""
    # so sánh BỎ phần "updated" để không commit khi chỉ đổi giờ
    def strip_updated(t):
        try:
            d = json.loads(t)
            d.pop("updated", None)
            return json.dumps(d, ensure_ascii=False, sort_keys=True)
        except Exception:
            return t
    if strip_updated(old_text) == strip_updated(new_text):
        print("Không có bài mới — bỏ qua (tránh spam build).")
        return 0

    OUT_FILE.write_text(new_text, encoding="utf-8")

    subprocess.run(["git", "add", "page-posts.json", "assets/img/page-posts"], cwd=ROOT, check=False)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        print("Không có gì để commit.")
        return 0
    subprocess.run(["git", "commit", "-m", f"page-posts: đồng bộ {len(items)} bài fanpage lên web {now}"],
                   cwd=ROOT, check=True)
    # remote có thể đi trước (news-updater/analytics) → rebase rồi push
    subprocess.run(["git", "pull", "--rebase", "--autostash", "origin", "main"], cwd=ROOT, check=False)
    subprocess.run(["git", "push", "origin", "main"], cwd=ROOT, check=True)
    print(f"✅ Đã đồng bộ {len(items)} bài fanpage lên web ({now}) + push OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
