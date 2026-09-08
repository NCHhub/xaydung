#!/usr/bin/env bash
# run.sh — AUTO-BLOG X.aladDin.vn (Diamond 09-08)
# Dây chuyền: meta_topics (Meta AI chủ đề nóng hội nhóm) → write_blog (sinh _blog/*.md từ
# moi-gioi.yml — NGUỒN THẬT duy nhất) → git commit/push → verify. 0 token AI ở phần script.
#
# Cron đề xuất: 0 9 * * *  (sáng, sau khi Meta AI đã có thông tin mới)
set -euo pipefail

SITE="/home/diamond/empire/xaydung-site"
cd "$SITE"

echo "== [1/4] Thu chủ đề nóng hội nhóm từ Meta AI =="
python3 bridge/auto-blog/meta_topics.py || { echo "⚠️ meta_topics không có chủ đề mới — dùng topics thủ công nếu có."; }

echo "== [2/4] Sinh bài viết từ topics + moi-gioi.yml =="
python3 bridge/auto-blog/write_blog.py || { echo "⚠️ write_blog không tạo bài mới."; }

# Nếu có bài mới chưa commit → commit + push
NEW_FILES=$(git status --porcelain -- _blog/ | wc -l)
if [ "$NEW_FILES" -gt 0 ]; then
  echo "== [3/4] Commit + push $NEW_FILES thay đổi ở _blog/ =="
  git add _blog/ bridge/auto-blog/ 2>/dev/null || true
  git commit -m "[auto-blog] thêm bài viết từ chủ đề nóng hội nhóm $(date +%Y-%m-%d)" || echo "không có gì để commit"
  git push origin HEAD 2>/dev/null || git push origin main 2>/dev/null || echo "⚠️ push lỗi — kiểm tra branch"
else
  echo "== [3/4] Không có bài mới — bỏ qua commit/push =="
fi

echo "== [4/4] Xong. GH Pages build ~40s. Verify sau: curl -sI https://x.aladdin.vn/ =="