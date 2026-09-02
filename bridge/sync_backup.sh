#!/usr/bin/env bash
# ============================================================
# sync_backup.sh — Đồng bộ dữ liệu người dùng (X.aladDin.vn)
#   conversations/ (dấu vết hội thoại môi giới) → 2 nơi an toàn:
#     1. PC/WSL backup  : ~/empire/backups/xaydung/
#     2. Google Drive   : G:\My Drive\2026\xaydung\  (= /mnt/g/My Drive/2026/xaydung/)
#
# Chạy thủ công:  bash bridge/sync_backup.sh
# Chạy tự động:   thêm cron hằng giờ (xem cuối file)
# ============================================================
set -uo pipefail

BRIDGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONV_DIR="$BRIDGE_DIR/conversations"

# 1) PC backup
PC_BACKUP="$HOME/empire/backups/xaydung/conversations"
mkdir -p "$PC_BACKUP"
if [ -d "$CONV_DIR" ] && ls "$CONV_DIR"/*.json >/dev/null 2>&1; then
  cp -f "$CONV_DIR"/*.json "$PC_BACKUP/" 2>/dev/null
  echo "[sync] ✅ PC backup: $(ls "$PC_BACKUP"/*.json 2>/dev/null | wc -l) file -> $PC_BACKUP"
else
  echo "[sync] ⚠️ Không có conversations/*.json (chưa có dữ liệu)"
fi

# 2) Google Drive — ổ G ảo: G:\My Drive\2026\ → /mnt/g/My Drive/2026/
GDRIVE_DIR="/mnt/g/My Drive/2026/xaydung"
mkdir -p "$GDRIVE_DIR" 2>/dev/null || true
if [ -d "$CONV_DIR" ] && ls "$CONV_DIR"/*.json >/dev/null 2>&1; then
  if cp -f "$CONV_DIR"/*.json "$GDRIVE_DIR/" 2>/dev/null; then
    echo "[sync] ✅ Google Drive (ổ G): conversations -> G:\\My Drive\\2026\\xaydung\\"
  else
    echo "[sync] ⚠️ Không copy được lên ổ G (chưa mount?). Chạy: sudo mount -t drvfs 'G:' /mnt/g"
  fi
fi

echo "[sync] Đồng bộ xong: $(date '+%Y-%m-%d %H:%M:%S')"
# ============================================================
# CRON tự động (chạy mỗi giờ):
#   crontab -e  → thêm dòng:
#   0 * * * * /bin/bash /tmp/opencode/xaydung/bridge/sync_backup.sh >> /tmp/opencode/sync_backup.log 2>&1
# ============================================================
