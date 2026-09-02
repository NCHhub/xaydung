#!/usr/bin/env bash
# ============================================================
# sync_backup.sh — ĐỒNG BỘ DỮ LIỆU NGƯỜI DÙNG (X.aladDin.vn)
#   "DỮ LIỆU LÀ CỰC KỲ QUÝ GIÁ" → đồng bộ + backup an toàn, không ghi đè mất.
#
# Đồng bộ 2 nguồn dữ liệu:
#   bridge/conversations/  → hội thoại Chorus/user (dấu vết liền mạch)
#   bridge/data/           → users.json (hồ sơ user) + events.jsonl (dấu chân tương tác)
# Về 2 nơi an toàn:
#   1. PC/WSL backup  : ~/empire/backups/xaydung/
#   2. Google Drive   : G:\My Drive\2026\xaydung\  (= /mnt/g/My Drive/2026/xaydung/)
#
# Chạy thủ công:  bash bridge/sync_backup.sh
# Chạy tự động:   cron hằng giờ (xem cuối file)
# ============================================================
set -uo pipefail

BRIDGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$BRIDGE_DIR/data"
CONV_DIR="$BRIDGE_DIR/conversations"

# Stamp thời gian cho bản backup (giữ lịch sử, không ghi đè — chống mất dữ liệu)
STAMP="$(date +%Y%m%d-%H%M)"
KEEP_HOURS="${SYNC_KEEP_HOURS:-72}"   # giữ 72h = ~3 ngày backup theo giờ

sync_to() {
  local dest="$1"
  mkdir -p "$dest" 2>/dev/null || { echo "[sync] ⚠️ Không tạo được $dest"; return 1; }

  # 1) conversations/*.json — bản mới nhất
  if [ -d "$CONV_DIR" ] && ls "$CONV_DIR"/*.json >/dev/null 2>&1; then
    for f in "$CONV_DIR"/*.json; do
      cp -f "$f" "$dest/" 2>/dev/null
    done
  fi

  # 2) data/ (users.json + events.jsonl) — bản versioned theo giờ
  if [ -d "$DATA_DIR" ] && ls "$DATA_DIR/"*.json "$DATA_DIR/"*.jsonl >/dev/null 2>&1; then
    for f in "$DATA_DIR"/users.json "$DATA_DIR"/events.jsonl; do
      [ -f "$f" ] || continue
      cp -f "$f" "$dest/" 2>/dev/null                       # bản mới nhất
      cp -f "$f" "$dest/$(basename "${f%.*}")-$STAMP.${f##*.}" 2>/dev/null  # bản versioned
    done
  fi

  # 3) Dọn backup cũ quá hạn giữ (theo metadata — giữ bản versioned gần nhất)
  if [ -n "$dest" ]; then
    find "$dest" -name "*-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-*.json*" \
      -mmin "+$((KEEP_HOURS*60))" -delete 2>/dev/null
  fi
}

echo "[sync] Đồng bộ $(date '+%Y-%m-%d %H:%M:%S')"

# 1) PC backup
PC_BACKUP="$HOME/empire/backups/xaydung"
sync_to "$PC_BACKUP"
echo "[sync] ✅ PC backup: $(ls "$PC_BACKUP" 2>/dev/null | wc -l) đối tượng -> $PC_BACKUP"

# 2) Google Drive — ổ G ảo: G:\My Drive\2026\ → /mnt/g/My Drive/2026/
GDRIVE_DIR="/mnt/g/My Drive/2026/xaydung"
if sync_to "$GDRIVE_DIR"; then
  echo "[sync] ✅ Google Drive (ổ G): -> G:\\My Drive\\2026\\xaydung\\"
else
  echo "[sync] ⚠️ Không copy được lên ổ G (chưa mount?). Chạy: sudo mount -t drvfs 'G:' /mnt/g"
fi

echo "[sync] Đồng bộ xong: $(date '+%Y-%m-%d %H:%M:%S')"
# ============================================================
# CRON tự động (chạy mỗi giờ — backup dữ liệu quý, 0 token):
#   crontab -e  → thêm dòng:
#   3 * * * * /bin/bash /tmp/opencode/xaydung/bridge/sync_backup.sh >> /tmp/opencode/sync_backup.log 2>&1
# ============================================================
