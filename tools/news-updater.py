#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
news-updater.py — Cập nhật TIN THẬT cho x.aladdin.vn (section #news-live)
Nguồn: RSS VnExpress BĐS (+ fallback VnEconomy BĐS, Cafef BĐS)
Quy tắc (LUẬT #11): KHÔNG bịa số/nhân vật — lấy title+link gốc + trích summary từ RSS.
Hành động môi giới = template có căn cứ theo từ khóa (không hứa lợi nhuận).
Chỉ commit khi có tin mới (tránh spam build GitHub Pages).
Cron gợi ý: */30 * * * *  ~/empire/xaydung-site/tools/news-updater.py > /dev/null 2>&1
"""
import json, os, re, subprocess, sys, datetime
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # ~/empire/xaydung-site
NEWS_FILE = os.path.join(ROOT, "news.json")
MAX_ITEMS = 3
MAX_HISTORY = 6

FEEDS = [
    ("VnExpress BĐS", "https://vnexpress.net/rss/bat-dong-san.rss"),
    ("VnEconomy BĐS", "https://vneconomy.vn/bat-dong-san.rss"),
    ("Cafef BĐS", "https://cafef.vn/bat-dong-san.rss"),
]

ACTION_MAP = [
    (["lãi suất", "vay", "lãi", "lạm phát"],
     "➡️ Môi giới: khách phân vân vay vốn — trình bảng chi phí xây/sửa (nguồn gốc) để khách thấy tổng dòng tiền trước khi vay. Không hứa lợi nhuận."),
    (["quy hoạch", "quy hoạch đô thị", "thu hồi", "thuế đất"],
     "➡️ Môi giới: nhắc khách kiểm tra quy hoạch TRƯỚC khi mua/xây — kiểm tra đúng thửa đất + ghi nhận hiện trạng nhà liền kề."),
    (["chung cư", "căn hộ"],
     "➡️ Môi giới: tư vấn có căn cứ trước khi khách bán/thuê — liệt kê đủ chi phí giữ nhà bằng checklist xây sửa, không khuyến khích quyết định vội."),
    (["giá", "thị trường", "tăng", "giảm"],
     "➡️ Môi giới: dùng số liệu gốc khi tư vấn — đừng bịa giá; đối chiếu bảng giá thực tế từng khu trước khi nói với khách."),
    (["khởi công", "dự án", "mở bán", "Vinhomes"],
     "➡️ Môi giới: theo dõi mở bán để kịp tư vấn khách; hỏi nhu cầu xây/sửa nhà để tăng giá trị thương vụ."),
    (["nhà ở xã hội", "NƠXH"],
     "➡️ Môi giới: nguồn nhà ở xã hội mới ảnh hưởng vùng lân cận — cập nhật hồ sơ để tư vấn khách đúng nhu cầu."),
]
FALLBACK_ACTION = "➡️ Môi giới: dùng tin này làm tư liệu tư vấn khách — luôn kiểm chứng số liệu gốc trước khi nói (LUẬT #11)."

def pick_action(text):
    t = text.lower()
    for keys, action in ACTION_MAP:
        if any(k in t for k in keys):
            return action
    return FALLBACK_ACTION

def clean(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()

# Ưu tiên tin liên quan MÔI GIỚI THỔ CƯ HÀ NỘI; loại tin vùng xa không liên quan
PREFER_KEYS = ["hà nội", "thủ đô", "thổ cư", "nhà ở", "quy hoạch", "chung cư", "lãi suất",
               "vay mua nhà", "xây", "sửa nhà", "đất nền", "giá nhà", "biệt thự", "khởi công", "Vinhomes"]
SKIP_KEYS = ["miền trung", "miền nam", "tây nguyên", "đà nẵng", "bình dương", "cần thơ",
             "phú quốc", "nghệ an", "thanh hóa", "khánh hòa", "bà rịa", "đồng nai", "bình thuận"]

def prefer_score(text):
    t = text.lower()
    score = sum(1 for k in PREFER_KEYS if k in t)
    if any(k in t for k in SKIP_KEYS):
        score -= 3
    return score

def fetch_feed(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
    root = ET.fromstring(data)
    out = []
    for it in root.iter("item"):
        title = clean(it.findtext("title"))
        link = (it.findtext("link") or "").strip()
        if not title or not link:
            continue
        summary = clean(it.findtext("description"))[:180]
        pub = (it.findtext("pubDate") or "")
        m = re.search(r"(\d{1,2}) (\w{3}) (\d{4})", pub)
        months = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,"Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
        if m:
            day, mon, year = int(m.group(1)), months.get(m.group(2), 1), int(m.group(3))
            d = datetime.date(year, mon, day)
            time_str = d.strftime("%d/%m/%Y")
        else:
            time_str = datetime.date.today().strftime("%d/%m/%Y")
        out.append({"title": title, "link": link, "summary": summary, "time": time_str})
    return out

def main():
    seen, items = set(), []
    for name, url in FEEDS:
        try:
            for it in fetch_feed(url):
                key = it["title"][:80]
                if key in seen:
                    continue
                seen.add(key)
                items.append(it)
        except Exception as e:
            print(f"RSS {name} lỗi: {e}", file=sys.stderr)
    if not items:
        print("Không lấy được tin nào — giữ nguyên news.json", file=sys.stderr)
        return 0
    # Ưu tiên tin liên quan Hà Nội/thổ cư (score), sau đó mới theo ngày
    items.sort(key=lambda x: (prefer_score(x["title"] + " " + x["summary"]), x["time"]), reverse=True)
    top = items[:MAX_ITEMS]

    old = {}
    if os.path.exists(NEWS_FILE):
        try:
            old = json.load(open(NEWS_FILE, encoding="utf-8"))
        except Exception:
            old = {}

    old_titles = {it.get("title") for it in old.get("items", [])}
    new_titles = {it["title"] for it in top}
    if old_titles == new_titles:
        print("Không có tin mới — bỏ qua (tránh spam build).")
        return 0

    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    history = list(old.get("history", []))
    for it in old.get("items", []):
        history.append({"time": it.get("time", ""), "title": it.get("title", ""), "action": it.get("action", "")})
    history = history[-MAX_HISTORY:]

    data = {
        "updated": now,
        "source": "RSS VnExpress/VnEconomy/Cafef BĐS + phân tích môi giới",
        "items": [{"icon": "📰", **it, "action": pick_action(it["title"] + " " + it["summary"])} for it in top],
        "history": history,
    }
    with open(NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    subprocess.run(["git", "add", "news.json"], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-m", f"news-updater: cập nhật tin thật {now}"], cwd=ROOT, check=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=ROOT, check=True)
    print(f"Đã cập nhật {len(top)} tin ({now}) + push OK.")
    return 0

if __name__ == "__main__":
    sys.exit(main())