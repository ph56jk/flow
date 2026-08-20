#!/bin/zsh
# Wrapper khởi động Content Image Runner cho launchd.
#
# Bí mật chỉ nằm trong runner/.env (chmod 600, đã gitignore).  Script này
# nạp file đó vào môi trường tiến trình và không in bất kỳ giá trị nào ra
# stdout/stderr, nên log launchd không chứa secret.

set -eu

REPO_ROOT="/Users/admin/Documents/ChatGPT/erptrello/flow-v2"
ENV_FILE="${AUTOMATION_RUNNER_ENV_FILE:-$REPO_ROOT/automation_center/runner/.env}"
PYTHON="$REPO_ROOT/.venv/bin/python"
RUNNER="$REPO_ROOT/automation_center/runner/content_image_runner.py"

if [ ! -f "$ENV_FILE" ]; then
  print -u2 "Thiếu file cấu hình runner: $ENV_FILE"
  exit 78
fi

# Từ chối chạy nếu file cấu hình để lộ quyền đọc cho người khác.
PERMS=$(stat -f "%OLp" "$ENV_FILE")
if [ "$PERMS" != "600" ]; then
  print -u2 "Quyền của $ENV_FILE là $PERMS, cần 600. Chạy: chmod 600 \"$ENV_FILE\""
  exit 78
fi

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

if [ -z "${AUTOMATION_RUNNER_SECRET:-}" ]; then
  print -u2 "AUTOMATION_RUNNER_SECRET chưa được đặt trong $ENV_FILE"
  exit 78
fi

exec "$PYTHON" "$RUNNER"
