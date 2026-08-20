#!/bin/zsh
# Kiểm tra sức khoẻ host runner.  Chỉ in trạng thái có/không, không in giá trị secret.

set -u

REPO_ROOT="/Users/admin/Documents/ChatGPT/erptrello/flow-v2"
ENV_FILE="$REPO_ROOT/automation_center/runner/.env"
CENTER_URL="https://automation.havigroup.llc"
FLOW_URL="http://127.0.0.1:8000"
UID_NUM=$(id -u)

ok()   { print "  [OK]   $1" }
bad()  { print "  [THIẾU] $1" }

print "== Flow v2 local =="
if curl -fsS --max-time 6 "$FLOW_URL/api/health" > /dev/null 2>&1; then
  ok "Flow trả lời tại $FLOW_URL"
else
  bad "Flow không trả lời tại $FLOW_URL"
fi
if launchctl print "gui/$UID_NUM/com.havigroup.flow-v2" > /dev/null 2>&1; then
  ok "launchd com.havigroup.flow-v2 đã nạp"
else
  bad "launchd com.havigroup.flow-v2 chưa nạp"
fi
PROJECT_SET=$(curl -fsS --max-time 8 "$FLOW_URL/api/state" 2>/dev/null \
  | "$REPO_ROOT/.venv/bin/python" -c 'import json,sys;print("yes" if (json.load(sys.stdin).get("config") or {}).get("project_id") else "no")' 2>/dev/null)
if [ "$PROJECT_SET" = "yes" ]; then ok "Flow đã chọn Project ID"; else bad "Flow chưa chọn Project ID (mở $FLOW_URL để chọn)"; fi

print "== Cấu hình runner =="
if [ -f "$ENV_FILE" ]; then
  ok "Có $ENV_FILE"
  [ "$(stat -f '%OLp' "$ENV_FILE")" = "600" ] && ok "Quyền file là 600" || bad "Quyền file phải là 600"
  for KEY in AUTOMATION_RUNNER_SECRET CF_ACCESS_CLIENT_ID CF_ACCESS_CLIENT_SECRET; do
    if grep -qE "^$KEY=.+" "$ENV_FILE"; then ok "$KEY đã có giá trị"; else bad "$KEY còn trống"; fi
  done
else
  bad "Chưa có $ENV_FILE"
fi

print "== Automation Center =="
CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$CENTER_URL/api/runner/heartbeat" -X POST -H 'content-type: application/json' -d '{}' 2>/dev/null)
case "$CODE" in
  401) ok "Access cho qua, Worker từ chối vì sai secret (đúng như mong đợi khi test rỗng)" ;;
  302|403) bad "Cloudflare Access chặn ($CODE) — Service Token chưa đúng hoặc chưa gắn policy" ;;
  *)   print "  [?]    Heartbeat trả về HTTP $CODE" ;;
esac

print "== Runner service =="
if launchctl print "gui/$UID_NUM/com.havigroup.content-image-runner" > /dev/null 2>&1; then
  ok "launchd com.havigroup.content-image-runner đã nạp"
else
  bad "Runner chưa nạp (bootstrap sau khi điền .env)"
fi
