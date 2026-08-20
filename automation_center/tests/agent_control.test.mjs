// Ranh giới quyền của Agent trung tâm điều khiển agent.
//
// Chạy: node --test 'automation_center/tests/*.test.mjs'
//
// Ba lớp của PRD mục 6 được kiểm ở đây, từng lớp một và độc lập nhau:
//   lớp 1 — capability của vai trò;
//   lớp 2 — phạm vi (runner nào, action nào, trần/ngày, khung giờ);
//   lớp 3 — PROTECTED_RUNNER_KEYS, thứ mà không phạm vi nào vượt được.
// Lời nhắc gửi cho mô hình ngôn ngữ không phải một lớp và không có mặt ở đây.

import assert from "node:assert/strict";
import { test } from "node:test";

import * as worker from "../src/worker.js";
import {
  CONTROL_ACTIONS, PROTECTED_RUNNER_KEYS, OWNER_DEFAULT_CONTROL_SCOPE, CONTROL_LIMITS,
  capability, isProtectedRunnerKey, parseRunnerKeyList, parseActionList,
  normaliseControlScopeRow, normaliseFrozenScope, validateControlCommand,
  parseAllowedHours, isWithinAllowedHours, vietnamHour, vietnamDayStartIso,
} from "../src/worker.js";

const DASHBOARD = "listing2-erp-agent";

// Giờ VN 10:00 ngày 15/08/2026 — trong mọi khung giờ hành chính của test.
const AT_10H_VN = Date.UTC(2026, 7, 15, 3, 0, 0);
const AT_19H_VN = Date.UTC(2026, 7, 15, 12, 0, 0);

const bot = (overrides = {}) => ({
  id: "listing2-erp-agent-runner",
  dashboard_id: DASHBOARD,
  runner_key: "listing2-erp-runner",
  ...overrides,
});

const scopeOf = (overrides = {}) => normaliseControlScopeRow({
  subject_type: "role",
  subject: "operator",
  allow_runner_keys: "listing2-erp-runner",
  allow_actions: "start,stop,status",
  max_commands_per_day: 20,
  allowed_hours: "",
  ...overrides,
});

const check = (command, scope, context = {}) => validateControlCommand(
  command, scope, { dashboardId: DASHBOARD, at: AT_10H_VN, commandsToday: 0, canRecover: false, ...context },
);

// ─── Lớp 1: vai trò ──────────────────────────────────────────────────────────

test("chỉ những vai trò được chọn mới điều khiển và khôi phục được agent", () => {
  assert.equal(capability("owner", "agent_control"), true);
  assert.equal(capability("admin", "agent_control"), true);
  assert.equal(capability("operator", "agent_control"), true);
  assert.equal(capability("reviewer", "agent_control"), false);
  assert.equal(capability("viewer", "agent_control"), false);

  // Operator điều khiển được nhưng không tự khôi phục được — recover ép một
  // run đang chạy thành failed, đó là quyền dọn dẹp chứ không phải vận hành.
  assert.equal(capability("operator", "agent_recover"), false);
  assert.equal(capability("admin", "agent_recover"), true);
  assert.equal(capability("owner", "agent_recover"), true);
  assert.equal(capability("reviewer", "agent_recover"), false);

  // Vai trò lạ không mượn được quyền điều khiển.
  assert.equal(capability("constructor", "agent_control"), false);
  assert.equal(capability("", "agent_control"), false);
});

// ─── Lớp 3: runner được bảo vệ ───────────────────────────────────────────────

test("runner được bảo vệ chặn được cả Owner với phạm vi rộng nhất", () => {
  for (const runnerKey of PROTECTED_RUNNER_KEYS) {
    const verdict = check(
      { action: "stop", bot: bot({ runner_key: runnerKey }) },
      { ...OWNER_DEFAULT_CONTROL_SCOPE },
      { canRecover: true },
    );
    assert.equal(verdict.ok, false, `${runnerKey} phải bị chặn`);
    assert.equal(verdict.code, "protected_runner");
  }
});

test("liệt kê đúng tên runner được bảo vệ trong phạm vi cũng không mở được nó", () => {
  // Đây là cái bẫy thật: người cấp quyền gõ thẳng "agent-control-runner" vào
  // phạm vi.  Lớp 3 phải thắng lớp 2, và lý do từ chối phải nói đúng luật nào
  // đã chặn — audit đọc "ngoài phạm vi" sẽ dẫn người ta đi sửa nhầm chỗ.
  const scope = scopeOf({ allow_runner_keys: "agent-control-runner\norchestrator-runner" });
  const verdict = check({ action: "stop", bot: bot({ runner_key: "orchestrator-runner" }) }, scope);
  assert.equal(verdict.ok, false);
  assert.equal(verdict.code, "protected_runner");
});

test("danh sách runner được bảo vệ có đủ hai khoá và so khớp bằng nhau", () => {
  assert.deepEqual(PROTECTED_RUNNER_KEYS, ["agent-control-runner", "orchestrator-runner"]);
  assert.equal(isProtectedRunnerKey("agent-control-runner"), true);
  // Không phải tiền tố, không phải glob: một key khác tên là một runner khác.
  assert.equal(isProtectedRunnerKey("agent-control-runner-2"), false);
  assert.equal(isProtectedRunnerKey("listing2-erp-runner"), false);
  assert.equal(isProtectedRunnerKey(""), false);
});

// ─── Lớp 2: phạm vi ──────────────────────────────────────────────────────────

test("không có dòng phạm vi thì không gửi được lệnh nào", () => {
  const verdict = check({ action: "status", bot: bot() }, null);
  assert.equal(verdict.ok, false);
  assert.equal(verdict.code, "no_scope");
});

test("phạm vi rỗng không âm thầm trở thành phạm vi mở", () => {
  // Dòng có thật trong bảng nhưng không cho runner nào (hoặc không action
  // nào) phải đọc là "chưa được cấp", không phải "được cấp tất cả".
  assert.equal(normaliseControlScopeRow({ allow_runner_keys: "", allow_actions: "start" }), null);
  assert.equal(normaliseControlScopeRow({ allow_runner_keys: "listing2-erp-runner", allow_actions: "" }), null);
  assert.equal(normaliseControlScopeRow(null), null);
  assert.deepEqual(parseRunnerKeyList(""), []);
  assert.deepEqual(parseActionList(""), []);
});

test("so khớp runner key là so bằng, không phải tiền tố", () => {
  const scope = scopeOf({ allow_runner_keys: "listing2-erp-runner" });
  assert.equal(check({ action: "start", bot: bot({ runner_key: "listing2-erp-runner" }) }, scope).ok, true);
  const near = check({ action: "start", bot: bot({ runner_key: "listing2-erp-runner-2" }) }, scope);
  assert.equal(near.ok, false);
  assert.equal(near.code, "target_out_of_scope");
});

test("action ngoài phạm vi bị chặn dù runner nằm trong phạm vi", () => {
  const scope = scopeOf({ allow_actions: "status" });
  assert.equal(check({ action: "status", bot: bot() }, scope).ok, true);
  const verdict = check({ action: "start", bot: bot() }, scope);
  assert.equal(verdict.ok, false);
  assert.equal(verdict.code, "action_out_of_scope");
});

test("action lạ không đi qua được, kể cả với phạm vi của Owner", () => {
  for (const action of ["delete", "restart", "run", "", "constructor"]) {
    const verdict = check({ action, bot: bot() }, { ...OWNER_DEFAULT_CONTROL_SCOPE });
    assert.equal(verdict.ok, false, `${action} phải bị chặn`);
    assert.equal(verdict.code, "unknown_action");
  }
  assert.deepEqual(CONTROL_ACTIONS, ["start", "stop", "status", "recover"]);
});

test("phạm vi ở dashboard này không với sang bot của dashboard khác", () => {
  const verdict = check(
    { action: "stop", bot: bot({ dashboard_id: "content-image-agent" }) },
    { ...OWNER_DEFAULT_CONTROL_SCOPE },
  );
  assert.equal(verdict.ok, false);
  assert.equal(verdict.code, "wrong_dashboard");
});

test("bot không tìm thấy hoặc chưa gán runner bị từ chối, không đoán hộ", () => {
  const scope = { ...OWNER_DEFAULT_CONTROL_SCOPE };
  assert.equal(check({ action: "status", bot: null }, scope).code, "unknown_target");
  assert.equal(check({ action: "status", bot: bot({ runner_key: "" }) }, scope).code, "no_runner");
});

test("recover cần capability riêng, không đi kèm quyền điều khiển", () => {
  const scope = scopeOf({ allow_actions: "start,stop,status,recover" });
  const denied = check({ action: "recover", bot: bot() }, scope, { canRecover: false });
  assert.equal(denied.ok, false);
  assert.equal(denied.code, "no_recover_capability");
  assert.equal(check({ action: "recover", bot: bot() }, scope, { canRecover: true }).ok, true);
});

test("phạm vi mặc định của Owner là mọi bot trong dashboard, không phải mọi bot", () => {
  // any_runner_key là một cờ riêng, không phải allow_runner_keys = ["*"]:
  // thêm glob vào danh sách runner sẽ khớp cả những key tương lai chưa ai duyệt.
  assert.equal(OWNER_DEFAULT_CONTROL_SCOPE.any_runner_key, true);
  assert.deepEqual(OWNER_DEFAULT_CONTROL_SCOPE.allow_runner_keys, []);
  assert.deepEqual(OWNER_DEFAULT_CONTROL_SCOPE.allow_actions, CONTROL_ACTIONS);
  // Dòng lấy từ bảng thì không bao giờ có cờ đó.
  assert.equal(scopeOf().any_runner_key, false);
});

test("trần lệnh mỗi ngày bị kẹp trong khoảng có nghĩa", () => {
  assert.equal(normaliseControlScopeRow({ allow_runner_keys: "a", allow_actions: "stop", max_commands_per_day: 0 }).max_commands_per_day, 1);
  assert.equal(normaliseControlScopeRow({ allow_runner_keys: "a", allow_actions: "stop", max_commands_per_day: 9999 }).max_commands_per_day, 200);
  assert.equal(normaliseControlScopeRow({ allow_runner_keys: "a", allow_actions: "stop", max_commands_per_day: "abc" }).max_commands_per_day, 1);
});

test("vượt trần lệnh trong ngày thì lệnh bị từ chối", () => {
  const scope = scopeOf({ max_commands_per_day: 2 });
  assert.equal(check({ action: "start", bot: bot() }, scope, { commandsToday: 1 }).ok, true);
  const verdict = check({ action: "start", bot: bot() }, scope, { commandsToday: 2 });
  assert.equal(verdict.ok, false);
  assert.equal(verdict.code, "daily_limit");
});

test("danh sách runner và action bỏ rác, bỏ trùng, không tự thêm gì", () => {
  assert.deepEqual(
    parseRunnerKeyList("listing2-erp-runner\ncontent-image-runner,listing2-erp-runner\n\n"),
    ["listing2-erp-runner", "content-image-runner"],
  );
  assert.deepEqual(parseActionList("start, stop , stop\nrestart\nSTATUS"), ["start", "stop", "status"]);
  assert.deepEqual(parseActionList("delete drop"), []);
});

// ─── Khung giờ ───────────────────────────────────────────────────────────────

test("khung giờ đọc theo giờ VN, không theo giờ UTC của Worker", () => {
  // 03:00 UTC = 10:00 VN.  Nếu ai đó đọc nhầm sang giờ UTC thì khung 08-18 sẽ
  // chặn đúng thời điểm đáng lẽ phải cho.
  assert.equal(vietnamHour(AT_10H_VN), 10);
  assert.equal(vietnamHour(AT_19H_VN), 19);
  assert.equal(isWithinAllowedHours("08-18", AT_10H_VN), true);
  assert.equal(isWithinAllowedHours("08-18", AT_19H_VN), false);
  // Đúng 08:00 là trong khung; đúng 18:00 là ngoài (khung đóng ở đầu trên).
  assert.equal(isWithinAllowedHours("08-18", Date.UTC(2026, 7, 15, 1, 0, 0)), true);
  assert.equal(isWithinAllowedHours("08-18", Date.UTC(2026, 7, 15, 11, 0, 0)), false);
});

test("khung giờ qua đêm nằm ở hai đầu ngày", () => {
  const at23hVn = Date.UTC(2026, 7, 15, 16, 0, 0);
  const at2hVn = Date.UTC(2026, 7, 15, 19, 0, 0);
  const at12hVn = Date.UTC(2026, 7, 15, 5, 0, 0);
  assert.equal(isWithinAllowedHours("22-06", at23hVn), true);
  assert.equal(isWithinAllowedHours("22-06", at2hVn), true);
  assert.equal(isWithinAllowedHours("22-06", at12hVn), false);
});

test("khung giờ gõ sai thì đóng lại, không mở ra", () => {
  assert.deepEqual(parseAllowedHours(""), { kind: "any" });
  assert.deepEqual(parseAllowedHours("   "), { kind: "any" });
  for (const raw of ["8h-18h", "08:00-18:00", "25-30", "08-08", "abc", "08", "-", "08-18-20"]) {
    assert.equal(parseAllowedHours(raw).kind, "invalid", `${raw} phải là khung giờ không hợp lệ`);
    assert.equal(isWithinAllowedHours(raw, AT_10H_VN), false, `${raw} phải đóng`);
  }
  // Rỗng = mọi giờ, đó là mặc định khi người cấp không khai khung nào.
  assert.equal(isWithinAllowedHours("", AT_19H_VN), true);
});

test("dừng khẩn không chờ giờ hành chính", () => {
  const scope = scopeOf({ allowed_hours: "08-18" });
  const started = check({ action: "start", bot: bot() }, scope, { at: AT_19H_VN });
  assert.equal(started.ok, false);
  assert.equal(started.code, "outside_hours");
  // stop được miễn: khung giờ giới hạn việc khởi động thêm việc, không được
  // biến thành lý do để một bot chạy sai tiếp tục chạy tới sáng.
  assert.equal(check({ action: "stop", bot: bot() }, scope, { at: AT_19H_VN }).ok, true);
  // status thì không được miễn — nó vẫn tiêu một lệnh của agent trung tâm.
  assert.equal(check({ action: "status", bot: bot() }, scope, { at: AT_19H_VN }).code, "outside_hours");
});

test("ngày để đếm trần lệnh là ngày theo giờ VN", () => {
  // 02:00 UTC ngày 15 là 09:00 VN ngày 15 → mốc đầu ngày là 17:00 UTC ngày 14.
  assert.equal(vietnamDayStartIso(Date.UTC(2026, 7, 15, 2, 0, 0)), "2026-08-14T17:00:00.000Z");
  // 20:00 UTC ngày 15 đã là 03:00 VN ngày 16 → mốc đầu ngày là 17:00 UTC ngày 15.
  assert.equal(vietnamDayStartIso(Date.UTC(2026, 7, 15, 20, 0, 0)), "2026-08-15T17:00:00.000Z");
  // Ngay tại mốc: 17:00 UTC = 00:00 VN hôm sau, mốc là chính nó.
  assert.equal(vietnamDayStartIso(Date.UTC(2026, 7, 15, 17, 0, 0)), "2026-08-15T17:00:00.000Z");
});

// ─── Đường đi qua ────────────────────────────────────────────────────────────

test("module xuất ra vẫn nạp được vào workerd", () => {
  // workerd coi mọi named export của entrypoint là một service entrypoint và
  // chỉ nhận function hoặc object.  Xuất thẳng một hằng số kiểu chuỗi/số làm
  // `wrangler dev` chết ngay lúc khởi động ("Incorrect type for map entry"),
  // và lỗi đó chỉ lộ ra khi chạy Worker chứ không phải khi chạy node --test.
  for (const [name, value] of Object.entries(worker)) {
    if (name === "default") continue;
    assert.equal(
      typeof value === "function" || (typeof value === "object" && value !== null),
      true,
      `export "${name}" là ${typeof value}; hãy gom vào một object như CONTROL_LIMITS`,
    );
  }
  // Các hằng số vẫn phải với tới được từ test, chỉ là qua một cái hộp.
  assert.equal(CONTROL_LIMITS.AGENT_CONTROL_RUNNER_KEY, "agent-control-runner");
  assert.equal(CONTROL_LIMITS.RUNNER_ONLINE_WITHIN_MS, 45000);
  assert.equal(CONTROL_LIMITS.ORPHAN_AFTER_MS, 5 * 60 * 1000);
  assert.equal(CONTROL_LIMITS.VN_OFFSET_MS, 7 * 60 * 60 * 1000);
});

test("lệnh hợp lệ trả về đúng bot và runner đã kiểm, không trả lại chuỗi thô", () => {
  const verdict = check({ action: "start", bot: bot() }, scopeOf());
  assert.deepEqual(verdict, {
    ok: true,
    action: "start",
    botId: "listing2-erp-agent-runner",
    runnerKey: "listing2-erp-runner",
  });
});

// ─── Phạm vi đọc lại từ scope_json (đường A) ─────────────────────────────────
//
// Yêu cầu chat đóng băng phạm vi lúc xếp hàng rồi mới chạy, có khi sau nhiều
// phút.  Lúc chạy lại, dòng scope_json đó phải được đọc theo kiểu đóng: thiếu
// khoá, sai kiểu hay rỗng đều là "chưa được cấp", không bao giờ là "cho tất cả".

test("phạm vi đóng băng đọc lại đúng như lúc ghi", () => {
  const frozen = normaliseFrozenScope({
    allow_runner_keys: ["listing2-erp-runner"],
    any_runner_key: false,
    allow_actions: ["start", "status"],
    max_commands_per_day: 20,
    allowed_hours: "07-22",
    note: "ghi lúc xếp hàng",
    source: "role:operator",
  });
  assert.deepEqual(frozen, {
    allow_runner_keys: ["listing2-erp-runner"],
    any_runner_key: false,
    allow_actions: ["start", "status"],
    max_commands_per_day: 20,
    allowed_hours: "07-22",
    note: "ghi lúc xếp hàng",
    source: "role:operator",
  });
});

test("scope_json hỏng hoặc rỗng là chưa được cấp, không phải cho tất cả", () => {
  for (const broken of [null, undefined, "", "{}", 0, [], {}, { allow_actions: ["start"] }]) {
    assert.equal(normaliseFrozenScope(broken), null, `${JSON.stringify(broken)} lẽ ra phải là null`);
  }
  // Có runner nhưng không action nào hợp lệ → vẫn là chưa được cấp.
  assert.equal(normaliseFrozenScope({
    allow_runner_keys: ["listing2-erp-runner"], allow_actions: ["delete", "deploy"],
  }), null);
  // Có action nhưng không runner nào → cũng vậy.
  assert.equal(normaliseFrozenScope({ allow_runner_keys: [], allow_actions: ["status"] }), null);
});

test("any_runner_key chỉ đúng khi nó đúng là true", () => {
  // Một giá trị "gần đúng" (chuỗi, số 1) không được biến thành mọi runner.
  for (const almost of ["true", 1, "yes", {}]) {
    const frozen = normaliseFrozenScope({
      any_runner_key: almost, allow_runner_keys: ["listing2-erp-runner"], allow_actions: ["status"],
    });
    assert.equal(frozen.any_runner_key, false, `any_runner_key: ${JSON.stringify(almost)}`);
  }
  assert.equal(normaliseFrozenScope({ any_runner_key: true, allow_actions: ["status"] }).any_runner_key, true);
});

test("trần lệnh đọc lại luôn nằm trong khoảng dùng được", () => {
  const capOf = (value) => normaliseFrozenScope({
    any_runner_key: true, allow_actions: ["status"], max_commands_per_day: value,
  }).max_commands_per_day;
  assert.equal(capOf(20), 20);
  assert.equal(capOf(0), 1);           // 0 lệnh/ngày là phạm vi không dùng được
  assert.equal(capOf(-5), 1);
  assert.equal(capOf(9999), 200);      // không vượt trần cứng
  assert.equal(capOf("hai mươi"), 1);  // rác → chặt nhất
});

test("action đọc lại vẫn nằm trong tập đóng và không phân biệt hoa thường", () => {
  const frozen = normaliseFrozenScope({
    any_runner_key: true,
    allow_actions: ["START", "Status", "deploy", "", "recover"],
  });
  assert.deepEqual(frozen.allow_actions, ["start", "status", "recover"]);
});

test("phạm vi đóng băng không tự cấp quyền chạm runner được bảo vệ", () => {
  // any_runner_key nghe như "mọi runner", nhưng lớp 3 nằm ở validateControlCommand
  // chứ không ở đây, nên nó vẫn phải chặn.
  const frozen = normaliseFrozenScope({ any_runner_key: true, allow_actions: CONTROL_ACTIONS });
  const verdict = check({ action: "stop", bot: bot({ runner_key: "agent-control-runner" }) }, frozen);
  assert.equal(verdict.ok, false);
  assert.equal(verdict.code, "protected_runner");
});
