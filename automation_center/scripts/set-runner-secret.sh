#!/bin/zsh
# Sinh RUNNER_SHARED_SECRET ngẫu nhiên mạnh, đẩy lên Cloudflare Worker và
# ghi cùng giá trị vào runner/.env.
#
# Giá trị KHÔNG bao giờ được in ra màn hình, log hay biến shell history.
# Yêu cầu: đã chạy `npx wrangler login` một lần trước đó.

set -eu

REPO_ROOT="/Users/admin/Documents/ChatGPT/erptrello/flow-v2"
CENTER_DIR="$REPO_ROOT/automation_center"
ENV_FILE="$CENTER_DIR/runner/.env"

if [ ! -f "$ENV_FILE" ]; then
  print -u2 "Chưa có $ENV_FILE. Copy từ content-image-runner.env.example trước."
  exit 1
fi

umask 077
TMP_SECRET=$(mktemp)
TMP_ENV=$(mktemp)
trap 'rm -f "$TMP_SECRET" "$TMP_ENV"' EXIT

# 32 byte ngẫu nhiên, base64url, không ký tự cần escape.
openssl rand -base64 48 | tr -d '\n=' | tr '+/' '-_' | cut -c1-48 > "$TMP_SECRET"

# 1) Đẩy lên Worker qua stdin (wrangler không ghi giá trị ra log).
( cd "$CENTER_DIR" && npx --yes wrangler secret put RUNNER_SHARED_SECRET < "$TMP_SECRET" )

# 2) Ghi cùng giá trị vào runner/.env, thay dòng cũ nếu có.
SECRET_VALUE=$(cat "$TMP_SECRET")
awk -v val="$SECRET_VALUE" '
  /^AUTOMATION_RUNNER_SECRET=/ { print "AUTOMATION_RUNNER_SECRET=" val; found=1; next }
  { print }
  END { if (!found) print "AUTOMATION_RUNNER_SECRET=" val }
' "$ENV_FILE" > "$TMP_ENV"
cat "$TMP_ENV" > "$ENV_FILE"
chmod 600 "$ENV_FILE"

print "Đã đặt RUNNER_SHARED_SECRET trên Worker và đồng bộ vào runner/.env."
print "Khởi động lại runner: launchctl kickstart -k gui/\$(id -u)/com.havigroup.content-image-runner"
