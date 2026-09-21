#!/usr/bin/env bash
# auto-sync.sh — ĐỒNG BỘ WEB x.aladdin.vn (0 đồng, Diamond 21-09)
#   1) Tin RSS hữu ích cho môi giới  → news.json
#   2) Bài đã đăng trên fanpage P1/P2/P3 → page-posts.json
# Chạy TUẦN TỰ để tránh tranh chấp git push (mỗi script tự pull --rebase trước push).
#
# Cron: 0 8 * * *   và   30 19 * * *
#   cd /home/diamond/empire/xaydung-site && /bin/bash tools/auto-sync.sh >> /home/diamond/empire/shared/logs/xaydung-auto-sync.log 2>&1
set -uo pipefail
SITE="/home/diamond/empire/xaydung-site"
cd "$SITE"

echo "=== auto-sync $(date '+%Y-%m-%d %H:%M:%S') ==="
/usr/bin/python3 tools/news-updater.py   || echo "⚠️ news-updater lỗi (xem log trên)"
/usr/bin/python3 tools/sync-page-posts.py || echo "⚠️ sync-page-posts lỗi (xem log trên)"
echo "=== auto-sync xong $(date '+%H:%M:%S') ==="
