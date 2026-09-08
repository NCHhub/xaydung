#!/usr/bin/env python3
"""
fb_librarian.py — THỦ THƯ DATA FB (Diamond 09-08).

Nhiệm vụ: liên tục phân tích, thấu hiểu, phân loại, học hỏi từ data FB group
đã thu (Apify actor, 0 code scrape) — để CỘNG HƯỞNG: mỗi bài được gắn nhãn,
đưa vào kho có cấu trúc, dùng lại nhiều lần (topics auto-blog, tra cứu nhanh,
thống kê xu hướng). Không lãng phí data.

Lane: L0 rule deterministic (0 token) — đúng cho việc lặp, khuôn mẫu.
Lớp AI ("thấu hiểu sâu") bật sau khi có endpoint model thủ thư (RX 580 Vulkan/
ollama) qua OLLAMA_HOST + THU_THU_MODEL — script vẫn chạy được khi không có.

Đọc : bridge/data/fb-groups-*.json  (tích lũy, 1 file mỗi lần scrape)
Ghi : bridge/data/library/
        posts.jsonl   — mỗi bài 1 dòng: {legacyId, group, date, text, loai,
                          chu_de, tuyen, do_nong, engagement, likes, comments}
        index.json    — thống kê: tổng, theo loai, chu_de, tuyen, mốc cập nhật
        summary.md    — báo cáo ngắn đọc được cho người

Chạy: python3 fb_librarian.py
"""
import json, re, sys
from pathlib import Path

SITE = Path("/home/diamond/empire/xaydung-site")
DATA_DIR = SITE / "bridge" / "data"
LIB = DATA_DIR / "library"

# ---- Rule phân loại -------------------------------------------------------
RAO_KW = ["sổ đỏ", "sổ đ.ỏ", "hotline", "zalo", "liên hệ", "lh:", "cần bán",
          "bán nhanh", "chính chủ", "cho thuê", "cho thue", "xây mới",
          "thu mua", "thanh lý", "phế liệu", "xác nhà", "mặt đường chính",
          "nhà phố", "xưởng", "căn hộ", "sở hữu", "ngân hàng cho vay",
          "em an", "lh an", "liên hệ an", "giá cao", "chiết khấu", "1pn", "2 ngủ"]
ICONS = ["💥", "🔥", "🎀", "👑", "🌸", "🌺", "🏗️", "♻️", "🏡", "💎", "👉", "📞", "☎️"]
HOI_KW = ["các bác", "bác nào", "cho e hỏi", "cho em hỏi", "mọi người ơi",
          "có thông tin", "phải không", "bao nhiêu", "ở đâu", "khi nào",
          "thế nào", "ko biết", "không biết", "giúp", "nhờ các bác", "ac ơi",
          "có biết", "tháng mấy", "bác nhỉ", "mấy bác", "hỏi"]
CHU_DE_RULES = [  # (keyword, nhãn) — thứ tự ưu tiên
    ("thu hồi", "thu-hoi-dat"), ("kiểm đếm", "thu-hoi-dat"),
    ("đền bù", "den-bu"), ("bồi thường", "den-bu"),
    ("tái định cư", "tai-dinh-cu"), ("tdc", "tai-dinh-cu"), ("hộ phụ", "tai-dinh-cu"),
    ("giải phóng", "gpmb"), ("bàn giao", "gpmb"), ("mặt bằng", "gpmb"),
    ("thuê nhà", "thue-nha-tam"), ("ở tạm", "thue-nha-tam"), ("thuê chỗ", "thue-nha-tam"),
    ("hỗ trợ nhà ở", "ho-tro-nha-o"), ("hỗ trợ", "ho-tro-nha-o"),
    ("thu mua", "dich-vu"), ("thanh lý", "dich-vu"), ("phế liệu", "dich-vu"),
    ("xác nhà", "dich-vu"), ("xưởng", "dich-vu"),
    ("bán", "mua-ban"), ("sổ đỏ", "mua-ban"), ("sổ đ.ỏ", "mua-ban"),
    ("cho thuê", "cho-thue"), ("cho thue", "cho-thue"),
]
TUYEN = ["260 giải phóng", "giải phóng", "bạch mai", "hoàng mai", "ngọc hồi",
         "thường tín", "cầu giấy", "hà đông", "đống đa", "nam từ liêm",
         "bắc từ liêm", "long biên", "cổ linh", "đại mỗ", "văn điển",
         "trương định", "vân trì", "vân nội", "pháp vân", "quốc lộ 1a",
         "gia lâm", "thanh trì", "hà nội"]

def classify_loai(text: str, engagement: int) -> str:
    t = text.lower()
    if engagement >= 5 and any(k in t for k in HOI_KW):
        return "hoi-that"
    hits = sum(t.count(ic) for ic in ICONS)
    if hits >= 2 or any(k in t for k in RAO_KW):
        return "rao-ban"
    if engagement >= 5:
        return "hoi-that"
    return "khac"

def classify_chude(text: str) -> str:
    t = text.lower()
    for kw, label in CHU_DE_RULES:
        if kw in t:
            return label
    return "khac"

def find_tuyen(text: str):
    t = text.lower()
    for name in TUYEN:
        if name in t:
            return name
    return ""

def do_nong(engagement: int) -> str:
    if engagement >= 30:
        return "cao"
    if engagement >= 10:
        return "trung"
    if engagement >= 5:
        return "thap"
    return "rac"

def load_posts():
    posts, seen = [], set()
    for f in sorted(DATA_DIR.glob("fb-groups-*.json")):
        try:
            items = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for p in items if isinstance(items, list) else items.get("data", []):
            if not isinstance(p, dict) or p.get("type") != "post":
                continue
            lid = p.get("legacyId") or p.get("id")
            if not lid or lid in seen:
                continue
            seen.add(lid)
            posts.append(p)
    return posts

def main():
    posts = load_posts()
    if not posts:
        print("[fb_librarian] Không có data — chạy scrape (Apify) trước.")
        sys.exit(1)
    rows = []
    for p in posts:
        text = (p.get("text") or "").strip()
        eng = p.get("engagementTotal") or 0
        row = {
            "legacyId": p.get("legacyId") or p.get("id"),
            "group": p.get("facebookId"),
            "date": (p.get("date") or "")[:10],
            "text": text[:300],
            "loai": classify_loai(text, eng),
            "chu_de": classify_chude(text),
            "tuyen": find_tuyen(text),
            "do_nong": do_nong(eng),
            "engagement": eng,
            "likes": p.get("likesCount") or 0,
            "comments": p.get("commentsCount") or 0,
        }
        rows.append(row)
    rows.sort(key=lambda r: -r["engagement"])

    LIB.mkdir(parents=True, exist_ok=True)
    with open(LIB / "posts.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    from collections import Counter
    loai = Counter(r["loai"] for r in rows)
    chude = Counter(r["chu_de"] for r in rows)
    tuyen = Counter(r["tuyen"] for r in rows if r["tuyen"])
    dn = Counter(r["do_nong"] for r in rows)
    index = {
        "updated": datetime_now(),
        "total": len(rows),
        "theo_loai": dict(loai),
        "theo_chu_de": dict(chude),
        "theo_tuyen": dict(tuyen.most_common(10)),
        "theo_do_nong": dict(dn),
        "hoi_that_top": [r["text"] for r in rows if r["loai"] == "hoi-that"][:10],
    }
    (LIB / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 📚 Thủ thư data FB — Báo cáo tự động",
        "",
        f"- Mốc cập nhật: {datetime_now()}",
        f"- Tổng số bài trong kho: **{len(rows)}**",
        "",
        "## Phân loại",
        f"- 🗣️ Câu hỏi thật (hội thoại): **{loai.get('hoi-that', 0)}** bài",
        f"- 🛒 Rao bán/quảng cáo: **{loai.get('rao-ban', 0)}** bài",
        f"- ⚪ Khác: **{loai.get('khac', 0)}** bài",
        "",
        "## Chủ đề nóng",
    ]
    for label, n in chude.most_common(8):
        lines.append(f"- {label}: {n}")
    if tuyen:
        lines += ["", "## Tuyến đường/địa danh", ""]
        for name, n in tuyen.most_common(8):
            lines.append(f"- {name}: {n}")
    lines += ["", "## Độ nóng", ""]
    for k in ("cao", "trung", "thap", "rac"):
        lines.append(f"- {k}: {dn.get(k, 0)}")
    (LIB / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[fb_librarian] ✅ {len(rows)} bài → library/ (posts.jsonl · index.json · summary.md)")
    for label, n in loai.most_common():
        print(f"  {label}: {n}")
    print("  chủ đề:", ", ".join(f"{k}={v}" for k, v in chude.most_common(6)))
    if tuyen:
        print("  tuyến:", ", ".join(f"{k}={v}" for k, v in tuyen.most_common(5)))

def datetime_now():
    import datetime
    return datetime.date.today().isoformat()

if __name__ == "__main__":
    main()