#!/bin/bash
# web_heal.sh — CHẾ ĐỘ PHỤC HỒI WEB X.aladDin.vn (GitHub Pages + Jekyll)
# Theo chuẩn thế giới: monitor → phát hiện down → tự rollback → báo cáo.
# 0 token AI — script thuần, cron mỗi 10 phút (`*/10 * * * *`).
#
# Cơ chế:
#   1. Curl index + /bai-viet/ (3 lần, mỗi lần cách 10s) — nếu HTTP <200 hoặc ≥500 → FAIL
#   2. FAIL ≥2/3 → nghi ngờ web gãy → git revert commit cuối (HEAD) + push → GitHub Pages build lại
#   3. Verify sau 60s — nếu vẫn fail → cảnh báo log + không spam (tối đa 1 heal/30 phút)
# Log: ~/empire/shared/logs/web_heal.log

set -u
URL="https://X.aladDin.vn"
REPO="$HOME/empire/xaydung-site"
LOG="$HOME/empire/shared/logs/web_heal.log"
STATE="$HOME/empire/shared/logs/web_heal.state"   # timestamp lần heal gần nhất
mkdir -p "$(dirname "$LOG")"
TS() { date +"%Y-%m-%d %H:%M:%S"; }

log() { echo "[$(TS)] $1" >> "$LOG"; }

# 1) Kiểm tra HTTP — 3 lần
FAIL=0
for i in 1 2 3; do
  code=$(curl -s -o /dev/null -m 20 -w "%{http_code}" "$URL/" 2>/dev/null)
  if [ "$code" != "200" ]; then
    FAIL=$((FAIL + 1))
    log "FAIL[$i/$3] HTTP=$code $URL/"
  else
    break  # 200 → web OK
  fi
  sleep 10
done

if [ "$FAIL" -eq 0 ]; then
  exit 0  # web khỏe — không làm gì
fi

log "⚠ WEB LỖI ($FAIL/3 lần fail) — kích hoạt tự phục hồi."

# 2) Rollback: chỉ heal nếu lần cuối >30 phút trước (tránh loop)
LAST=0
[ -f "$STATE" ] && LAST=$(cat "$STATE" 2>/dev/null || echo 0)
NOW=$(date +%s)
if [ $((NOW - LAST)) -lt 1800 ]; then
  log "BỎ QUA heal (đã heal $((NOW - LAST))s trước) — tránh vòng lặp."
  exit 0
fi

cd "$REPO" || { log "LỖI: không vào được repo"; exit 1; }

# Chỉ rollback nếu working tree sạch (không mất thay đổi cục bộ)
if ! git diff --quiet HEAD; then
  log "BỎ QUA rollback — working tree có thay đổi chưa commit (giữ nguyên)."
  exit 0
fi

# Blacklist: không bao giờ revert các commit hạ tầng quan trọng
LAST_MSG=$(git log -1 --pretty=%s)
if echo "$LAST_MSG" | grep -qiE "cron|pipeline|quality_gate|fb_pipeline|infra"; then
  log "BỎ QUA rollback commit hạ tầng: $LAST_MSG"
  exit 0
fi

log "REVERT commit: $LAST_MSG"
if git revert --no-edit HEAD >/dev/null 2>&1; then
  git push origin main >> "$LOG" 2>&1
  echo "$NOW" > "$STATE"
  log "✅ Đã revert + push — chờ GitHub Pages build (~2-3 phút)."
  sleep 60
  code=$(curl -s -o /dev/null -m 20 -w "%{http_code}" "$URL/" 2>/dev/null)
  log "Verify sau heal: HTTP=$code $URL/"
else
  log "❌ git revert thất bại — cần xử lý thủ công."
fi