#!/usr/bin/env python3
"""web_status.py — BẢNG QUẢN LÝ WEB X.aladDin.vn (GitHub Pages + Jekyll).

Chuẩn thế giới: status board giám sát uptime — quét mọi URL quan trọng,
in bảng trực quan + ghi JSON cho dashboard. 0 token AI (curl thuần).

Chạy:
  python3 web_status.py            # in bảng + ghi status.json
  python3 web_status.py --json     # chỉ JSON (cho script/UI khác)
  python3 web_status.py --heal     # bonus: nếu lỗi → đề xuất lệnh heal

URL quét: index, /bai-viet/, /cong-trinh/, 5 bài mới nhất, 1 công trình.
"""
import argparse, json, subprocess, sys, time
from pathlib import Path

BASE = "https://X.aladDin.vn"
ROOT = Path.home() / "empire/xaydung-site"
STATUS_FILE = Path.home() / "empire/shared/logs/web_status.json"


def slug_from_title(title: str) -> str:
    """Jekyll slugify chuẩn (giống write_blog.py): đ→d trước NFKD."""
    import re, unicodedata
    s = title.replace('đ', 'd').replace('Đ', 'd')
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:90].strip("-")


def recent_slugs():
    """5 bài mới nhất (theo date trong filename) — slug từ frontmatter title."""
    slugs = []
    if ROOT.joinpath("_blog").exists():
        entries = []
        for f in ROOT.glob("_blog/*.md"):
            try:
                raw = f.read_text(encoding="utf-8")[:1200]
                title = ""
                for line in raw.splitlines():
                    line = line.strip()
                    if line.startswith("title:"):
                        title = line[6:].strip().strip('"').strip("'")
                        break
                date = f.name[:10]
                entries.append((date, slug_from_title(title) if title else f.stem))
            except Exception:
                continue
        entries.sort(reverse=True)
        slugs = ["/bai-viet/" + s + "/" for _, s in entries[:5]]
    return slugs


def check(url):
    t0 = time.time()
    try:
        p = subprocess.run(["curl", "-s", "-o", "/dev/null", "-m", "20",
                            "-w", "%{http_code} %{time_total}", url],
                           capture_output=True, text=True, timeout=25)
        out = p.stdout.strip()
        code, tt = (out.split() + ["0"])[:2]
        ms = int(float(tt or 0) * 1000)
        return code, ms
    except Exception:
        return "ERR", 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    urls = ["/", "/bai-viet/", "/cong-trinh/"] + recent_slugs()
    rows, all_ok = [], True
    for u in urls:
        code, ms = check(BASE + u.split("/")[0] + ("" if u == "/" else
                         ("/bai-viet/" if "bai-viet" in u else
                          "/cong-trinh/" if "cong-trinh" in u else "")) + "/".join(u.split("/")[1:]) + "/" if not u.endswith("/") else u)
        # đơn giản hóa: dùng URL gốc
        code, ms = check(BASE + u)
        ok = code == "200"
        all_ok = all_ok and ok
        rows.append({"url": u, "code": code, "ms": ms, "ok": ok})

    summary = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(rows), "ok": sum(1 for r in rows if r["ok"]),
        "status": "OK" if all_ok else "PROBLEM",
        "rows": rows,
    }
    STATUS_FILE.write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                           encoding="utf-8")

    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
        return 0 if all_ok else 1

    print(f"📊 WEB STATUS X.aladDin.vn — {summary['status']} "
          f"({summary['ok']}/{summary['total']} OK) @ {summary['ts']}")
    for r in rows:
        mark = "🟢" if r["ok"] else "🔴"
        print(f" {mark} {r['code']:>4} {r['ms']:>5}ms  {r['url']}")
    if not all_ok:
        print(f"\n⚠ Có {summary['total'] - summary['ok']} URL lỗi — xem "
              f"log: tail ~/empire/shared/logs/web_heal.log")
        print("Nếu lỗi toàn trang → chờ GitHub Pages build 2-5 phút, "
              "KHÔNG thêm .nojekyll (lesson nojekyll-kill).")
    print(f"\n💾 {STATUS_FILE}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())