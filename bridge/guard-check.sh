#!/usr/bin/env bash
# ============================================================
# guard-check.sh — KIỂM TRA TÍNH NĂNG GỐC BẤT KHẢ XÂM PHẠM
#
# Chạy TRƯỚC khi commit / trước khi agent thay đổi web, bridge, data.
# Báo ĐỎ/mạnh nếu phát hiện thiếu hoặc có dấu hiệu thay đổi tính năng gốc.
#
# Cách chạy:   bash guard-check.sh
# Exit code:   0 = bảo toàn OK · 1 = PHÁT HIỆN RỦI RO (phải xử lý/cảnh báo Diamond)
# ============================================================
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INDEX="$ROOT/index.html"
SERVER="$ROOT/bridge/server.py"
SYNC="$ROOT/bridge/sync_backup.sh"
GITIGNORE="$ROOT/.gitignore"
DATA="$ROOT/bridge/data"

FAIL=0
warn(){ echo "  🚨 $1"; FAIL=1; }
ok(){ echo "  ✅ $1"; }

# Giúp đếm linh hoạt (không hardcode số tuyệt đối dễ vỡ; kiểm tra SỰ TỒN TẠI)
have(){ grep -q "$1" "$2" 2>/dev/null; }

echo "=== 🛡️ GUARD CHECK — tính năng gốc (web + opencode2 + data) ==="
echo ""
echo "--- VÙNG 1: WEB (index.html) ---"
have "resolveBridge" "$INDEX" && ok "W1 Bridge JS → OpenCode (resolveBridge)" || warn "W1 THIẾU resolveBridge → web mất kết nối bộ não!"
have "doAsk" "$INDEX" && ok "W1 doAsk (luồng hỏi)" || warn "W1 THIẾU doAsk → không hỏi được!"
have "Khách của anh/chị đang cân nhắc căn nhà nào?" "$INDEX" && ok "W2 Câu hỏi hero định vị" || warn "W2 MẤT câu hỏi hero → mất định vị môi giới đầu khách mua"
have "goCalc" "$INDEX" && have "goChecklist" "$INDEX" && ok "W3 3 hành động chính (calc/checklist/expert)" || warn "W3 THIẾU 1 trong 3 hành động chính"
have "calcNow" "$INDEX" && ok "W4 Form tính tức thì (calcNow)" || warn "W4 THIẾU calcNow → mất tính nhanh"
have "checklistNow" "$INDEX" && ok "W6 Checklist trước cọc (checklistNow)" || warn "W6 THIẾU checklist trước cọc"
have "goGuiBaoCao" "$INDEX" && ok "W7 Báo cáo mang tên môi giới (gửi Zalo)" || warn "W7 THIẾU nút báo cáo mang tên môi giới → mất cộng sinh"
have "beacon" "$INDEX" && ok "W8 Beacon dữ liệu người dùng" || warn "W8 THIẾU beacon → ngừng thu dữ liệu quý"

echo "--- VÙNG 2: OPENCODE2 / BRIDGE (server.py) ---"
have "_call_chorus" "$SERVER" && ok "O1 Luồng hỏi → Chorus/OpenCode" || warn "O1 THIẾU _call_chorus → bộ não ngừng!"
have "_call_proxy" "$SERVER" && ok "O4 Fallback proxy (resilience)" || warn "O4 THIẾU _call_proxy → mất fallback"
have "_user_key" "$SERVER" && ok "O2 Hội thoại riêng theo user" || warn "O2 THIẾU _user_key → mất bộ nhớ theo user"
have "_build_system_prompt" "$SERVER" && ok "O3 Knowledge pack (persona Hải + dữ liệu)" || warn "O3 THIẾU knowledge pack"

echo "--- VÙNG 3: DỮ LIỆU (quý giá) ---"
have "_touch_profile" "$SERVER" && have "USERS_FILE" "$SERVER" && ok "D1 Hồ sơ người dùng (users.json)" || warn "D1 THIẾU data layer profile"
have "_log_event" "$SERVER" && have "EVENTS_FILE" "$SERVER" && ok "D2 Dấu chân tương tác (events.jsonl)" || warn "D2 THIẾU event log"
[ -f "$SYNC" ] && ok "D3 Đồng bộ (sync_backup.sh tồn tại)" || warn "D3 THIẾU sync_backup.sh → mất backup dữ liệu quý"
grep -q "bridge/data/" "$GITIGNORE" 2>/dev/null && ok "D4 bridge/data/ đã chặn khỏi GitHub công khai" || warn "D4 bridge/data/ KHÔNG bị ignore → NGUY CƠ LỘ ZALO/DỮ LIỆU CÔNG KHAI!"

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "✅ GUARD OK — toàn bộ tính năng gốc được BẢO TOÀN."
  exit 0
else
  echo "🔴 GUARD FAIL — PHÁT HIỆN VỀ TÍNH NĂNG GỐC BỊ ĐỤNG/THIẾU."
  echo "   → KHÔNG tiếp tục xóa/sửa vùng này. PHẢI cảnh báo Diamond MẠNH MẼ trước."
  exit 1
fi
