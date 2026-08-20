const ROLE_CAPABILITIES = {
  owner: ["view", "run", "review", "configure", "manage_members", "create_dashboard", "code_request", "code_approve", "agent_control", "agent_recover"],
  admin: ["view", "run", "review", "configure", "manage_members", "code_request", "code_approve", "agent_control", "agent_recover"],
  // Operator bấm được lệnh điều khiển nhưng không tự gỡ lần chạy mồ côi: đó là
  // thao tác ghi đè trạng thái, để dành cho Admin trở lên.
  operator: ["view", "run", "code_request", "agent_control"],
  reviewer: ["view", "review"],
  viewer: ["view"],
};

// Runner trên máy trung tâm nhận mọi yêu cầu sửa code.  Một khoá cố định để
// hàng đợi không phụ thuộc vào việc ai đã tạo bot nào.
const ORCHESTRATOR_RUNNER_KEY = "orchestrator-runner";

// Tập action đóng của agent trung tâm.  Đóng là cố ý: thêm một action mới phải
// là một lần sửa file này, không phải một chuỗi lạ từ mô hình ngôn ngữ.
const CONTROL_ACTIONS = ["start", "stop", "status", "recover"];

// Runner của chính agent trung tâm.  Hàng đợi yêu cầu điều khiển đi qua khoá
// cố định này, không phụ thuộc ai đã tạo bot nào.
const AGENT_CONTROL_RUNNER_KEY = "agent-control-runner";

// Lớp 3: không lệnh nào chạm được những runner này, kể cả của Owner và kể cả
// khi phạm vi liệt kê đúng tên chúng.
//
// Vì sao tự bảo vệ mình: một lệnh "stop" nhắm vào agent-control-runner là cách
// rẻ nhất để vô hiệu lớp giám sát; một lệnh "start" nhắm vào orchestrator-runner
// là cách biến quyền vận hành thành quyền sửa code.  Owner muốn dừng runner
// trung tâm thì dừng tiến trình trên máy, như hiện nay.
const PROTECTED_RUNNER_KEYS = [
  "agent-control-runner",
  "orchestrator-runner",
];

// Owner không cần ai cấu hình phạm vi hộ.  "any_runner_key" nghĩa là mọi bot
// CÓ TRONG DASHBOARD này — ranh giới dashboard vẫn là lớp nền, và lớp 3 vẫn
// chặn phía trên.  Nó là một cờ riêng chứ không phải allow_runner_keys = ["*"]:
// so khớp runner key là so bằng tuyệt đối, thêm glob vào đó chỉ mở đường cho
// "*-runner" khớp cả những key tương lai chưa ai duyệt.
const OWNER_DEFAULT_CONTROL_SCOPE = {
  allow_runner_keys: [],
  any_runner_key: true,
  allow_actions: [...CONTROL_ACTIONS],
  max_commands_per_day: 40,
  allowed_hours: "",
  source: "owner_default",
  note: "Phạm vi mặc định của Owner.",
};

// Run ở running/cancel_requested mà runner của nó im lặng lâu hơn ngưỡng này
// mới được coi là mồ côi.  5 phút >> heartbeat 45 giây để giảm dương tính giả:
// ép "failed" một run còn sống nghĩa là vứt kết quả của nó.
const ORPHAN_AFTER_MS = 5 * 60 * 1000;

// Runner online = heartbeat trong vòng 45 giây.  Hằng số này vốn nằm rải rác
// trong các so sánh Date.now() - Date.parse(...) < 45000.
const RUNNER_ONLINE_WITHIN_MS = 45000;

// Những file mà không vai trò nào được sửa tự động.  Diff chạm vào đây vẫn
// gửi được, nhưng bắt buộc Owner duyệt tay: đó là bí mật, hạ tầng triển khai,
// và chính mô hình phân quyền này — nếu agent sửa được worker.js hay
// migrations thì mọi giới hạn phía dưới chỉ còn là gợi ý.
const PROTECTED_GLOBS = [
  ".env", ".env.*", "**/.env", "**/.env.*", "**/*.env",
  "**/*.pem", "**/*.key", "**/*credentials*", "**/*secret*",
  ".gitignore", ".github/**",
  "wrangler.jsonc", "wrangler.toml", "**/wrangler.jsonc", "**/wrangler.toml",
  "automation_center/src/worker.js",
  "automation_center/migrations/**",
  "automation_center/runner/**",
  "automation_center/scripts/**",
];

// Owner không cần ai cấu hình phạm vi hộ.  Vẫn để auto_apply = 0: quyền sửa
// mọi file và quyền áp thẳng không cần ai xem là hai chuyện khác nhau.
const OWNER_DEFAULT_SCOPE = {
  allow_globs: ["**"],
  max_files: 40,
  max_lines: 4000,
  auto_apply: 0,
  source: "owner_default",
  note: "Phạm vi mặc định của Owner.",
};

const SEEDED_DASHBOARDS = [
  {
    id: "content-image-agent",
    slug: "agent-tao-anh-content",
    name: "Agent tạo ảnh Content",
    description: "Tạo ảnh theo idea, chờ duyệt từng ảnh và gửi kết quả đã duyệt về đúng nguồn.",
    icon: "image",
    color: "teal",
    status: "active",
  },
  {
    id: "listing2-erp-agent",
    slug: "listing-2-erp",
    name: "Listing 2 · ERP / Etsy",
    description: "Lấy ảnh nguồn từ HaviGroup ERP, tạo ảnh Flow, chờ duyệt trên dashboard rồi ghi URL đã duyệt về Task nguồn và đưa Listing 2 sang Etsy Draft.",
    icon: "image",
    color: "violet",
    status: "active",
  },
];

const SEEDED_BOTS = [
  {
    id: "content-image-agent-runner",
    dashboard_id: "content-image-agent",
    name: "Agent tạo ảnh Content",
    purpose: "Tạo ảnh theo idea và prompt đã gán; chờ duyệt trước khi gửi kết quả về nguồn.",
    runner_key: "content-image-runner",
    status: "needs_runner",
    last_run_status: "runner_integration_pending",
  },
  {
    id: "listing2-erp-agent-runner",
    dashboard_id: "listing2-erp-agent",
    name: "Listing 2 ERP / Etsy",
    purpose: "Đọc Task ERP đã gán, chạy Flow và chỉ ghi URL ảnh đã duyệt về Task nguồn; Listing 2 tiếp tục queue Etsy Draft trên runner nội bộ.",
    runner_key: "listing2-erp-runner",
    status: "needs_runner",
    last_run_status: "runner_integration_pending",
  },
];

const json = (value, status = 200) => new Response(JSON.stringify(value), {
  status,
  headers: {
    "content-type": "application/json; charset=UTF-8",
    "cache-control": "no-store",
  },
});

const error = (message, status = 400) => json({ error: message }, status);
const now = () => new Date().toISOString();
const id = () => crypto.randomUUID();
const clean = (value, max = 240) => String(value ?? "").trim().replace(/\s+/g, " ").slice(0, max);
const cleanText = (value, max = 3000) => String(value ?? "").trim().replace(/\s+/g, " ").slice(0, max);
function safeExternalUrl(value) {
  const candidate = cleanText(value, 2000);
  if (!candidate) return "";
  try {
    const parsed = new URL(candidate);
    return parsed.protocol === "https:" ? parsed.toString() : "";
  } catch {
    return "";
  }
}
const slugify = (value) => clean(value, 80)
  .normalize("NFD")
  .replace(/[\u0300-\u036f]/g, "")
  .toLowerCase()
  .replace(/[^a-z0-9]+/g, "-")
  .replace(/^-+|-+$/g, "")
  .slice(0, 64);

// Văn bản nhiều dòng (diff, log test, kế hoạch).  cleanText gộp mọi khoảng
// trắng thành một dấu cách, thứ đó phá nát một unified diff.
const cleanBlock = (value, max = 60000) => String(value ?? "")
  .replace(/\r\n?/g, "\n")
  .replace(/[^\S\n]+$/gm, "")
  .slice(0, max);

// Đếm số dòng thêm/bớt trong một patch unified.  Dòng "+++"/"---" là tiêu đề
// file, không phải nội dung thay đổi, nên phải loại ra.
function countDiffLines(diff) {
  let count = 0;
  for (const line of String(diff ?? "").split("\n")) {
    if (line.startsWith("+++") || line.startsWith("---")) continue;
    if (line.startsWith("+") || line.startsWith("-")) count += 1;
  }
  return count;
}

// Đường dẫn phải là đường dẫn tương đối trong repo và chỉ thế thôi.  "..",
// đường dẫn tuyệt đối và dấu \ của Windows đều bị loại — chúng là cách quen
// thuộc nhất để bước ra khỏi một allowlist.
function normaliseRepoPath(value) {
  const raw = String(value ?? "").trim().replace(/\\/g, "/");
  if (!raw || raw.length > 400) return "";
  if (raw.startsWith("/") || /^[A-Za-z]:/.test(raw)) return "";
  const parts = raw.split("/");
  if (parts.some((part) => part === "" || part === "." || part === "..")) return "";
  if (/[\0\n\r]/.test(raw)) return "";
  return parts.join("/");
}

// "**" đi qua cả dấu /, "*" thì không.  "a/**/b" cũng phải khớp "a/b", nên
// "**/" nuốt luôn dấu gạch chéo đi kèm.
function globToRegExp(glob) {
  let pattern = "^";
  for (let index = 0; index < glob.length; index += 1) {
    const char = glob[index];
    if (char === "*") {
      if (glob[index + 1] === "*") {
        if (glob[index + 2] === "/") { pattern += "(?:.*/)?"; index += 2; } else { pattern += ".*"; index += 1; }
      } else {
        pattern += "[^/]*";
      }
    } else if (char === "?") {
      pattern += "[^/]";
    } else {
      pattern += char.replace(/[.+^${}()|[\]\\]/g, "\\$&");
    }
  }
  return new RegExp(`${pattern}$`);
}

const matchesAnyGlob = (path, globs) => globs.some((glob) => {
  try { return globToRegExp(glob).test(path); } catch { return false; }
});

// So khớp không phân biệt hoa thường, khác với phạm vi do người cấp.  Máy trung
// tâm chạy Windows: ở đó "Secrets.json" và "secrets.json" là cùng một file, nên
// một danh sách bảo vệ phân biệt hoa thường chỉ tạo cảm giác an toàn.  Mọi mẫu
// trong PROTECTED_GLOBS đều đã viết thường.
const isProtectedPath = (path) => matchesAnyGlob(String(path ?? "").toLowerCase(), PROTECTED_GLOBS);

const parseGlobList = (value) => String(value ?? "")
  .split(/[\n,]/)
  .map((line) => normaliseRepoPath(line.replace(/\/+$/, "")))
  .filter(Boolean)
  .slice(0, 40);

function securityHeaders(response) {
  const headers = new Headers(response.headers);
  headers.set("x-content-type-options", "nosniff");
  headers.set("x-frame-options", "DENY");
  headers.set("referrer-policy", "same-origin");
  headers.set("permissions-policy", "camera=(), microphone=(), geolocation=()");
  headers.set(
    "content-security-policy",
    "default-src 'self'; img-src 'self' data: https:; style-src 'self'; script-src 'self'; connect-src 'self'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
  );
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

async function readJson(request) {
  const contentType = request.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    throw new Error("Yêu cầu phải dùng JSON.");
  }
  try {
    return await request.json();
  } catch {
    throw new Error("JSON không hợp lệ.");
  }
}

function identityFromRequest(request, env) {
  const fromAccess = clean(request.headers.get("cf-access-authenticated-user-email"), 254).toLowerCase();
  const fromDev = env.ALLOW_DEV_IDENTITY === "true"
    ? clean(request.headers.get("x-automation-dev-email"), 254).toLowerCase()
    : "";
  const email = fromAccess || fromDev;
  const domain = clean(env.COMPANY_EMAIL_DOMAIN || "havigroup.llc", 120).toLowerCase();
  if (!email || !email.endsWith(`@${domain}`)) {
    return null;
  }
  return { email, displayName: email.split("@")[0].replace(/[._-]+/g, " ") };
}

async function dbFirst(env, statement, ...values) {
  return env.DB.prepare(statement).bind(...values).first();
}

async function dbAll(env, statement, ...values) {
  const result = await env.DB.prepare(statement).bind(...values).all();
  return result.results || [];
}

async function dbRun(env, statement, ...values) {
  return env.DB.prepare(statement).bind(...values).run();
}

async function addAudit(env, actorEmail, action, targetType, targetId, dashboardId = null, metadata = {}) {
  await dbRun(
    env,
    "INSERT INTO audit_logs (id, dashboard_id, actor_email, action, target_type, target_id, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    id(), dashboardId, actorEmail, action, targetType, targetId, JSON.stringify(metadata), now(),
  );
}

async function ensureUser(env, identity) {
  await dbRun(
    env,
    "INSERT INTO users (email, display_name, global_role, active, created_at, updated_at) VALUES (?, ?, 'viewer', 1, ?, ?) ON CONFLICT(email) DO UPDATE SET display_name = excluded.display_name, updated_at = excluded.updated_at",
    identity.email, identity.displayName, now(), now(),
  );
  const initialOwner = clean(env.INITIAL_OWNER_EMAIL, 254).toLowerCase();
  if (initialOwner && initialOwner === identity.email) {
    await dbRun(env, "UPDATE users SET global_role = 'owner', updated_at = ? WHERE email = ?", now(), identity.email);
  }
  return dbFirst(env, "SELECT email, display_name, global_role, active FROM users WHERE email = ?", identity.email);
}

// Tra thẳng ROLE_CAPABILITIES[role] sẽ trúng thuộc tính kế thừa của Object:
// role = "constructor" trả về một hàm, khiến "|| []" không cứu được và
// .includes ném lỗi.  Chỉ nhận khoá do chính bảng này khai báo.
function permissionsFor(role) {
  return Object.hasOwn(ROLE_CAPABILITIES, role) ? ROLE_CAPABILITIES[role] : [];
}

function capability(role, required) {
  return permissionsFor(role).includes(required);
}

async function seedDashboards(env, user) {
  if (user.global_role !== "owner") return;
  for (const dashboard of SEEDED_DASHBOARDS) {
    await dbRun(
      env,
      "INSERT OR IGNORE INTO dashboards (id, slug, name, description, icon, color, status, runner_required, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)",
      dashboard.id, dashboard.slug, dashboard.name, dashboard.description, dashboard.icon, dashboard.color,
      dashboard.status, user.email, now(), now(),
    );
  }
  for (const bot of SEEDED_BOTS) {
    await dbRun(
      env,
      "INSERT OR IGNORE INTO bots (id, dashboard_id, name, purpose, runner_key, status, last_run_status, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
      bot.id, bot.dashboard_id, bot.name, bot.purpose, bot.runner_key, bot.status, bot.last_run_status,
      user.email, now(), now(),
    );
  }
}

async function dashboardAccess(env, dashboard, user) {
  if (user.global_role === "owner") return "owner";
  const membership = await dbFirst(
    env,
    "SELECT role FROM dashboard_members WHERE dashboard_id = ? AND user_email = ?",
    dashboard.id, user.email,
  );
  return membership?.role || "";
}

async function requireDashboard(env, slug, user, required = "view") {
  const dashboard = await dbFirst(env, "SELECT * FROM dashboards WHERE slug = ?", slug);
  if (!dashboard) throw new Response("Không tìm thấy dashboard.", { status: 404 });
  const role = await dashboardAccess(env, dashboard, user);
  if (!role || !capability(role, required)) throw new Response("Bạn không có quyền cho thao tác này.", { status: 403 });
  return { dashboard, role };
}

async function dashboardSummary(env, dashboard, role) {
  const [botCount, runningCount, approvalCount, projectCount, lastAudit] = await Promise.all([
    dbFirst(env, "SELECT COUNT(*) AS value FROM bots WHERE dashboard_id = ?", dashboard.id),
    dbFirst(env, "SELECT COUNT(*) AS value FROM bots WHERE dashboard_id = ? AND status = 'running'", dashboard.id),
    dbFirst(env, "SELECT COUNT(*) AS value FROM approvals WHERE dashboard_id = ? AND status = 'pending'", dashboard.id),
    dbFirst(env, "SELECT COUNT(*) AS value FROM dashboard_projects WHERE dashboard_id = ?", dashboard.id),
    dbFirst(env, "SELECT created_at FROM audit_logs WHERE dashboard_id = ? ORDER BY created_at DESC LIMIT 1", dashboard.id),
  ]);
  return {
    id: dashboard.id,
    slug: dashboard.slug,
    name: dashboard.name,
    description: dashboard.description,
    icon: dashboard.icon,
    color: dashboard.color,
    status: dashboard.status,
    runner_required: Boolean(dashboard.runner_required),
    role,
    counts: {
      bots: Number(botCount?.value || 0),
      running: Number(runningCount?.value || 0),
      approvals: Number(approvalCount?.value || 0),
      projects: Number(projectCount?.value || 0),
    },
    last_activity_at: lastAudit?.created_at || dashboard.updated_at,
  };
}

async function bootstrap(env, user) {
  await seedDashboards(env, user);
  const dashboards = await dbAll(env, "SELECT * FROM dashboards ORDER BY created_at ASC");
  const visible = [];
  for (const dashboard of dashboards) {
    const role = await dashboardAccess(env, dashboard, user);
    if (role) visible.push(await dashboardSummary(env, dashboard, role));
  }
  return {
    session: {
      email: user.email,
      display_name: user.display_name,
      global_role: user.global_role,
      is_owner: user.global_role === "owner",
    },
    capabilities: permissionsFor(user.global_role),
    dashboards: visible,
    role_definitions: Object.entries(ROLE_CAPABILITIES).map(([role, permissions]) => ({ role, permissions })),
  };
}

async function dashboardDetail(env, dashboard, role, user) {
  const [summary, rawBots, projects, approvals, logs, runs] = await Promise.all([
    dashboardSummary(env, dashboard, role),
    dbAll(env, "SELECT b.id, b.name, b.purpose, b.runner_key, b.status, b.last_run_at, b.last_run_status, b.created_at, r.status AS runner_status, r.last_seen_at AS runner_last_seen_at, r.last_error AS runner_last_error FROM bots b LEFT JOIN runners r ON r.runner_key = b.runner_key WHERE b.dashboard_id = ? ORDER BY b.created_at ASC", dashboard.id),
    dbAll(env, "SELECT project_id, project_name FROM dashboard_projects WHERE dashboard_id = ? ORDER BY project_name ASC", dashboard.id),
    dbAll(env, "SELECT id, title, detail, artifact_url, status, requested_by, reviewed_by, reviewed_at, created_at FROM approvals WHERE dashboard_id = ? ORDER BY CASE status WHEN 'pending' THEN 0 ELSE 1 END, created_at DESC LIMIT 50", dashboard.id),
    dbAll(env, "SELECT id, actor_email, action, target_type, target_id, metadata_json, created_at FROM audit_logs WHERE dashboard_id = ? ORDER BY created_at DESC LIMIT 60", dashboard.id),
    dbAll(env, "SELECT id, bot_id, title, prompt, aspect, image_count, status, runner_job_id, result_json, error, created_at, started_at, finished_at, updated_at FROM bot_runs WHERE dashboard_id = ? ORDER BY created_at DESC LIMIT 30", dashboard.id),
  ]);
  const currentTime = Date.now();
  const activeByBot = new Map();
  for (const run of runs) {
    if (["queued", "running", "cancel_requested"].includes(run.status) && !activeByBot.has(run.bot_id)) activeByBot.set(run.bot_id, run);
  }
  const bots = rawBots.map((bot) => ({
    ...bot,
    runner_online: runnerIsOnline({ status: bot.runner_status, last_seen_at: bot.runner_last_seen_at }, currentTime),
    active_run: activeByBot.get(bot.id) || null,
  }));
  const detail = { dashboard: summary, bots, projects, approvals, logs, runs };
  if (capability(role, "manage_members")) {
    detail.members = await dbAll(
      env,
      "SELECT m.user_email AS email, u.display_name, m.role, m.granted_by, m.created_at FROM dashboard_members m JOIN users u ON u.email = m.user_email WHERE m.dashboard_id = ? ORDER BY m.role, m.user_email",
      dashboard.id,
    );
  }
  detail.permissions = permissionsFor(role);
  detail.current_user = user.email;
  return detail;
}

async function createDashboard(request, env, user) {
  if (user.global_role !== "owner") return error("Chỉ Owner có thể tạo dashboard mới.", 403);
  const body = await readJson(request);
  const name = clean(body.name, 120);
  const description = clean(body.description, 420);
  let slug = slugify(body.slug || name);
  if (!name || !slug) return error("Dashboard cần có tên hợp lệ.");
  const existing = await dbFirst(env, "SELECT id FROM dashboards WHERE slug = ?", slug);
  if (existing) return error("Slug dashboard đã được dùng.", 409);
  const dashboard = {
    id: id(), slug, name, description, icon: clean(body.icon || "grid", 32),
    color: clean(body.color || "teal", 32), status: "draft",
    runner_required: body.runner_required === false ? 0 : 1,
    updated_at: now(),
  };
  await dbRun(
    env,
    "INSERT INTO dashboards (id, slug, name, description, icon, color, status, runner_required, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'draft', ?, ?, ?, ?)",
    dashboard.id, dashboard.slug, dashboard.name, dashboard.description, dashboard.icon, dashboard.color,
    dashboard.runner_required, user.email, now(), dashboard.updated_at,
  );
  await addAudit(env, user.email, "dashboard.created", "dashboard", dashboard.id, dashboard.id, { name });
  return json({ dashboard: await dashboardSummary(env, dashboard, "owner") }, 201);
}

async function grantMember(request, env, user, slug) {
  const { dashboard, role } = await requireDashboard(env, slug, user, "manage_members");
  const body = await readJson(request);
  const email = clean(body.email, 254).toLowerCase();
  const nextRole = clean(body.role, 20).toLowerCase();
  const domain = clean(env.COMPANY_EMAIL_DOMAIN || "havigroup.llc", 120).toLowerCase();
  if (!email.endsWith(`@${domain}`) || !["admin", "operator", "reviewer", "viewer"].includes(nextRole)) {
    return error("Email công ty và vai trò dashboard hợp lệ là bắt buộc.");
  }
  await dbRun(
    env,
    "INSERT INTO users (email, display_name, global_role, active, created_at, updated_at) VALUES (?, ?, 'viewer', 1, ?, ?) ON CONFLICT(email) DO UPDATE SET active = 1, updated_at = excluded.updated_at",
    email, email.split("@")[0].replace(/[._-]+/g, " "), now(), now(),
  );
  await dbRun(
    env,
    "INSERT INTO dashboard_members (dashboard_id, user_email, role, granted_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(dashboard_id, user_email) DO UPDATE SET role = excluded.role, granted_by = excluded.granted_by, updated_at = excluded.updated_at",
    dashboard.id, email, nextRole, user.email, now(), now(),
  );
  await addAudit(env, user.email, "member.granted", "user", email, dashboard.id, { role: nextRole, actor_role: role });
  return json({ ok: true });
}

async function createBot(request, env, user, slug) {
  const { dashboard } = await requireDashboard(env, slug, user, "configure");
  const body = await readJson(request);
  const name = clean(body.name, 120);
  const purpose = clean(body.purpose, 500);
  const runnerKey = clean(body.runner_key, 120);
  if (!name) return error("Bot cần có tên.");
  const bot = { id: id(), name, purpose, runnerKey, status: runnerKey ? "paused" : "needs_runner" };
  await dbRun(
    env,
    "INSERT INTO bots (id, dashboard_id, name, purpose, runner_key, status, last_run_status, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'never', ?, ?, ?)",
    bot.id, dashboard.id, bot.name, bot.purpose, bot.runnerKey, bot.status, user.email, now(), now(),
  );
  await addAudit(env, user.email, "bot.created", "bot", bot.id, dashboard.id, { name, runner_key: runnerKey || null });
  return json({ bot }, 201);
}

// Lõi điều khiển bot, dùng chung cho hai lối vào: nút bấm trên web và Agent
// điều phối.  Viết lại lần hai cho agent nghĩa là hai bản kiểm tra sẽ trôi khỏi
// nhau, và lối vào của agent là lối ít người soi hơn.  Trả về { ok, message }
// thay vì Response để cả hai bên tự bọc theo kiểu của mình.
async function runBotCommand(env, dashboard, actorEmail, botId, action, body = {}) {
  const fail = (message, status = 400) => ({ ok: false, status, message });
  if (!["run", "pause", "resume"].includes(action)) return fail("Action bot không hợp lệ.");
  const bot = await dbFirst(env, "SELECT * FROM bots WHERE id = ? AND dashboard_id = ?", botId, dashboard.id);
  if (!bot) return fail("Không tìm thấy bot trong dashboard này.", 404);
  const activeRun = await dbFirst(
    env,
    "SELECT * FROM bot_runs WHERE bot_id = ? AND status IN ('queued', 'running', 'cancel_requested') ORDER BY created_at DESC LIMIT 1",
    bot.id,
  );

  if (action === "pause") {
    if (!activeRun) return fail("Bot hiện không có lần chạy nào để dừng.", 409);
    if (activeRun.status === "queued") {
      await dbRun(env, "UPDATE bot_runs SET status = 'cancelled', finished_at = ?, updated_at = ? WHERE id = ?", now(), now(), activeRun.id);
      await dbRun(env, "UPDATE bots SET status = 'paused', last_run_status = 'cancelled_before_start', updated_at = ? WHERE id = ?", now(), bot.id);
      await addAudit(env, actorEmail, "bot.run_cancelled", "bot_run", activeRun.id, dashboard.id, { bot_id: bot.id, before_start: true });
      return { ok: true, run: { id: activeRun.id, status: "cancelled" }, message: "Đã huỷ lệnh tạo ảnh trước khi runner nhận việc." };
    }
    if (activeRun.status === "cancel_requested") {
      return { ok: true, run: { id: activeRun.id, status: "cancel_requested" }, message: "Runner đang nhận lệnh dừng." };
    }
    await dbRun(env, "UPDATE bot_runs SET status = 'cancel_requested', updated_at = ? WHERE id = ?", now(), activeRun.id);
    await dbRun(env, "UPDATE bots SET status = 'running', last_run_status = 'cancel_requested', updated_at = ? WHERE id = ?", now(), bot.id);
    await addAudit(env, actorEmail, "bot.stop_requested", "bot_run", activeRun.id, dashboard.id, { bot_id: bot.id });
    return { ok: true, run: { id: activeRun.id, status: "cancel_requested" }, message: "Đã gửi lệnh dừng. Runner sẽ dừng lần tạo ảnh hiện tại." };
  }

  if (activeRun) return fail("Bot đang có một lệnh chưa kết thúc. Hãy dừng lệnh đó trước.", 409);
  if (!bot.runner_key) return fail("Bot chưa được gán runner nên chưa thể chạy.", 409);
  const runner = await dbFirst(env, "SELECT status, last_seen_at FROM runners WHERE runner_key = ?", bot.runner_key);
  if (!runnerIsOnline(runner)) return fail("Runner tạo ảnh chưa kết nối. Không tạo lệnh giả; hãy bật runner trước.", 409);

  const prompt = cleanText(body.prompt, 3000);
  const aspect = clean(body.aspect || "landscape", 24).toLowerCase();
  const count = Math.max(1, Math.min(4, Number.parseInt(body.count, 10) || 1));
  if (prompt.length < 5) return fail("Hãy nhập yêu cầu tạo ảnh rõ ràng (ít nhất 5 ký tự).");
  if (!["landscape", "portrait", "square"].includes(aspect)) return fail("Tỷ lệ ảnh không hợp lệ.");
  // Mã Task ERP nguồn là tuỳ chọn: để trống thì Flow tự lấy Task từ danh sách
  // nguồn của PROJ-0049.  Chỉ nhận đúng dạng TASK-xxxx, không nhận chuỗi tự do.
  const erpTaskId = clean(body.erp_task_id, 140).toUpperCase();
  if (erpTaskId && !/^TASK-[A-Z0-9-]{1,120}$/.test(erpTaskId)) {
    return fail("Mã Task ERP phải có dạng TASK-xxxx.");
  }
  const run = {
    id: id(), dashboardId: dashboard.id, botId: bot.id, runnerKey: bot.runner_key,
    title: clean(body.title || `Ảnh Content · ${prompt.slice(0, 72)}`, 120), prompt, aspect, count, erpTaskId,
  };
  await dbRun(
    env,
    "INSERT INTO bot_runs (id, dashboard_id, bot_id, runner_key, requested_by, title, prompt, aspect, image_count, erp_task_id, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?)",
    run.id, run.dashboardId, run.botId, run.runnerKey, actorEmail, run.title, run.prompt, run.aspect, run.count, run.erpTaskId, now(), now(),
  );
  await dbRun(env, "UPDATE bots SET status = 'running', last_run_at = ?, last_run_status = 'queued', updated_at = ? WHERE id = ?", now(), now(), bot.id);
  await addAudit(env, actorEmail, "bot.run_queued", "bot_run", run.id, dashboard.id, { bot_id: bot.id, count, aspect });
  return { ok: true, created: true, run: { id: run.id, status: "queued" }, message: "Đã xếp lệnh tạo ảnh. Bạn có thể bấm Dừng ngay nếu đổi ý." };
}

async function botAction(request, env, user, slug, botId) {
  const { dashboard } = await requireDashboard(env, slug, user, "run");
  const body = await readJson(request);
  const result = await runBotCommand(env, dashboard, user.email, botId, clean(body.action, 20).toLowerCase(), body);
  if (!result.ok) return error(result.message, result.status || 400);
  return json({ ok: true, run: result.run, message: result.message }, result.created ? 201 : 200);
}

function runnerRequestAuthorized(request, env) {
  const expected = String(env.RUNNER_SHARED_SECRET || "");
  const received = String(request.headers.get("x-automation-runner-secret") || "");
  return Boolean(expected && received && expected === received);
}

async function runnerHeartbeat(request, env) {
  const body = await readJson(request);
  const runnerKey = clean(body.runner_key, 120);
  const label = clean(body.label, 120);
  const version = clean(body.version, 80);
  if (!runnerKey) return error("Runner key là bắt buộc.");
  await dbRun(
    env,
    "INSERT INTO runners (runner_key, label, status, version, last_seen_at, created_at, updated_at) VALUES (?, ?, 'online', ?, ?, ?, ?) ON CONFLICT(runner_key) DO UPDATE SET label = excluded.label, status = 'online', version = excluded.version, last_seen_at = excluded.last_seen_at, last_error = '', updated_at = excluded.updated_at",
    runnerKey, label || runnerKey, version, now(), now(), now(),
  );
  await dbRun(env, "UPDATE bots SET status = 'paused', last_run_status = CASE WHEN last_run_status = 'runner_integration_pending' THEN 'ready' ELSE last_run_status END, updated_at = ? WHERE runner_key = ? AND status = 'needs_runner'", now(), runnerKey);
  return json({ ok: true, poll_after_ms: 2500 });
}

async function runnerClaim(request, env) {
  const body = await readJson(request);
  const runnerKey = clean(body.runner_key, 120);
  if (!runnerKey) return error("Runner key là bắt buộc.");
  const runner = await dbFirst(env, "SELECT runner_key, status FROM runners WHERE runner_key = ?", runnerKey);
  if (!runner || runner.status !== "online") return error("Runner chưa heartbeat hoặc đang offline.", 409);
  const queued = await dbFirst(env, "SELECT * FROM bot_runs WHERE runner_key = ? AND status = 'queued' ORDER BY created_at ASC LIMIT 1", runnerKey);
  if (!queued) return json({ run: null });
  const claimed = await dbRun(env, "UPDATE bot_runs SET status = 'running', started_at = ?, updated_at = ? WHERE id = ? AND status = 'queued'", now(), now(), queued.id);
  if (!claimed.meta?.changes) return json({ run: null });
  await dbRun(env, "UPDATE bots SET status = 'running', last_run_status = 'running', updated_at = ? WHERE id = ?", now(), queued.bot_id);
  return json({ run: { id: queued.id, title: queued.title, prompt: queued.prompt, aspect: queued.aspect, count: queued.image_count, erp_task_id: queued.erp_task_id || "" } });
}

async function runnerRunStatus(env, runId, runnerKey) {
  const run = await dbFirst(env, "SELECT id, runner_key, status, runner_job_id, title, prompt, aspect, image_count, erp_task_id FROM bot_runs WHERE id = ?", runId);
  if (!run || run.runner_key !== runnerKey) return error("Không tìm thấy lần chạy của runner này.", 404);
  return json({ run });
}

async function runnerUpdateRun(request, env, runId) {
  const body = await readJson(request);
  const runnerKey = clean(body.runner_key, 120);
  const status = clean(body.status, 32).toLowerCase();
  if (!runnerKey || !["running", "completed", "failed", "cancelled"].includes(status)) return error("Cập nhật runner không hợp lệ.");
  const run = await dbFirst(env, "SELECT * FROM bot_runs WHERE id = ? AND runner_key = ?", runId, runnerKey);
  if (!run) return error("Không tìm thấy lần chạy của runner này.", 404);
  if (["completed", "failed", "cancelled"].includes(run.status)) return json({ ok: true, idempotent: true });
  const runnerJobId = clean(body.runner_job_id, 160);
  // Người dùng có thể bấm Dừng trong lúc runner còn đang gọi Flow để tạo job.
  // Khi đó run đã ở cancel_requested; một cập nhật "running" đến sau sẽ xoá mất
  // yêu cầu dừng và runner không bao giờ thấy nó nữa.  Chỉ ghi nhận runner_job_id
  // và giữ nguyên cancel_requested.
  if (run.status === "cancel_requested" && status === "running") {
    if (runnerJobId) {
      await dbRun(env, "UPDATE bot_runs SET runner_job_id = ?, updated_at = ? WHERE id = ?", runnerJobId, now(), run.id);
    }
    return json({ ok: true, cancel_requested: true });
  }
  const safeError = cleanText(body.error, 1000);
  const result = body.result && typeof body.result === "object" ? body.result : {};
  const terminal = ["completed", "failed", "cancelled"].includes(status);
  await dbRun(
    env,
    "UPDATE bot_runs SET status = ?, runner_job_id = CASE WHEN ? <> '' THEN ? ELSE runner_job_id END, result_json = ?, error = ?, finished_at = CASE WHEN ? THEN ? ELSE finished_at END, updated_at = ? WHERE id = ?",
    status, runnerJobId, runnerJobId, JSON.stringify(result), safeError, terminal ? 1 : 0, terminal ? now() : null, now(), run.id,
  );
  if (terminal) {
    const botStatus = status === "failed" ? "error" : "paused";
    await dbRun(env, "UPDATE bots SET status = ?, last_run_at = ?, last_run_status = ?, updated_at = ? WHERE id = ?", botStatus, now(), status, now(), run.bot_id);
    if (status === "completed" && Array.isArray(result.artifacts)) {
      // Tên bot lấy từ DB thay vì hằng số: dòng này dùng chung cho mọi bot có
      // runner, không riêng bot tạo ảnh Content.
      const botRow = await dbFirst(env, "SELECT name FROM bots WHERE id = ?", run.bot_id);
      const botName = clean(botRow?.name || "Agent", 120);
      for (const [index, artifact] of result.artifacts.slice(0, 4).entries()) {
        const url = safeExternalUrl(artifact?.url);
        // run_id + artifact_index cho phép runner ánh xạ quyết định duyệt ngược
        // về đúng Flow job và đúng artefact để resume bước ghi ERP.
        await dbRun(
          env,
          "INSERT INTO approvals (id, dashboard_id, run_id, artifact_index, title, detail, artifact_url, status, requested_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
          id(), run.dashboard_id, run.id, index, `Duyệt ảnh ${index + 1} · ${run.title}`, `Ảnh do ${botName} tạo. Duyệt hoặc từ chối từng ảnh.`, url, botName, now(),
        );
      }
    }
  }
  await addAudit(env, `runner:${runnerKey}`, `bot_run.${status}`, "bot_run", run.id, run.dashboard_id, { bot_id: run.bot_id, runner_job_id: runnerJobId || null });
  return json({ ok: true });
}

// Quyết định duyệt đã có nhưng chưa đẩy về Flow.  Chỉ trả các approval thuộc
// lần chạy của chính runner đang hỏi, để một runner không đọc được việc của runner khác.
async function runnerPendingApprovals(env, runnerKey) {
  if (!runnerKey) return error("Runner key là bắt buộc.");
  const rows = await dbAll(
    env,
    `SELECT a.id, a.run_id, a.artifact_index, a.status, a.artifact_url,
            r.runner_job_id, r.erp_task_id
       FROM approvals a
       JOIN bot_runs r ON r.id = a.run_id
      WHERE r.runner_key = ?
        AND a.status IN ('approved', 'rejected')
        AND a.pushed_at IS NULL
        AND a.run_id <> ''
      ORDER BY a.reviewed_at ASC
      LIMIT 20`,
    runnerKey,
  );
  return json({ approvals: rows });
}

async function runnerMarkApprovalPushed(request, env, approvalId) {
  const body = await readJson(request);
  const runnerKey = clean(body.runner_key, 120);
  if (!runnerKey) return error("Runner key là bắt buộc.");
  const row = await dbFirst(
    env,
    "SELECT a.id FROM approvals a JOIN bot_runs r ON r.id = a.run_id WHERE a.id = ? AND r.runner_key = ?",
    approvalId, runnerKey,
  );
  if (!row) return error("Không tìm thấy quyết định duyệt của runner này.", 404);
  const pushError = cleanText(body.error, 600);
  if (pushError) {
    // Giữ pushed_at = NULL để vòng poll sau thử lại; chỉ ghi lại lý do hỏng.
    await dbRun(env, "UPDATE approvals SET push_error = ? WHERE id = ?", pushError, approvalId);
    return json({ ok: true, retried: true });
  }
  await dbRun(env, "UPDATE approvals SET pushed_at = ?, push_error = '' WHERE id = ?", now(), approvalId);
  return json({ ok: true });
}

async function handleRunnerApi(request, env) {
  if (!runnerRequestAuthorized(request, env)) return error("Runner không được xác thực.", 401);
  const { pathname } = new URL(request.url);
  const segments = pathname.split("/").filter(Boolean);
  try {
    if (request.method === "POST" && pathname === "/api/runner/heartbeat") return await runnerHeartbeat(request, env);
    if (request.method === "POST" && pathname === "/api/runner/claim") return await runnerClaim(request, env);
    if (request.method === "POST" && pathname === "/api/runner/control/claim") {
      return await runnerClaimControlRequest(request, env);
    }
    if (segments[2] === "control" && segments[3] && segments[3] !== "claim") {
      const requestId = decodeURIComponent(segments[3]);
      if (request.method === "GET") {
        return await runnerControlRequestStatus(env, requestId, clean(new URL(request.url).searchParams.get("runner_key"), 120));
      }
      if (request.method === "POST") return await runnerUpdateControlRequest(request, env, requestId);
    }
    if (request.method === "GET" && pathname === "/api/runner/approvals") {
      return await runnerPendingApprovals(env, clean(new URL(request.url).searchParams.get("runner_key"), 120));
    }
    if (request.method === "POST" && segments[2] === "approvals" && segments[3] && segments[4] === "pushed") {
      return await runnerMarkApprovalPushed(request, env, decodeURIComponent(segments[3]));
    }
    if (segments[2] === "code") {
      if (request.method === "POST" && segments[3] === "claim") return await runnerClaimCodeRequest(request, env);
      if (request.method === "GET" && segments[3] === "approved") {
        return await runnerApprovedCodeRequests(env, clean(new URL(request.url).searchParams.get("runner_key"), 120));
      }
      if (segments[3]) {
        const codeRequestId = decodeURIComponent(segments[3]);
        if (request.method === "GET") {
          return await runnerCodeRequestStatus(env, codeRequestId, clean(new URL(request.url).searchParams.get("runner_key"), 120));
        }
        if (request.method === "POST") return await runnerUpdateCodeRequest(request, env, codeRequestId);
      }
    }
    if (segments[2] === "runs" && segments[3]) {
      const runId = decodeURIComponent(segments[3]);
      if (request.method === "GET") {
        const runnerKey = clean(new URL(request.url).searchParams.get("runner_key"), 120);
        if (segments[4] === "approvals") return await runnerRunApprovals(env, runId, runnerKey);
        return await runnerRunStatus(env, runId, runnerKey);
      }
      if (request.method === "POST") return await runnerUpdateRun(request, env, runId);
    }
    return error("Không tìm thấy Runner API.", 404);
  } catch (caught) {
    if (caught instanceof Response) return error(await caught.text(), caught.status);
    if (caught instanceof Error) return error(caught.message, 400);
    return error("Không thể xử lý lệnh runner.", 500);
  }
}

// ── Watchdog sức khoẻ ────────────────────────────────────────────────────────
//
// Ngày 2026-08-15 cả hai runner ngừng heartbeat lúc 01:00Z và không ai biết cho
// tới hơn 25 tiếng sau.  `runner_online` trong dashboardDetail vốn tính đúng,
// nhưng nó chỉ đúng khi có người đang mở dashboard ra nhìn.  Phần dưới đây là
// đường tự nhìn: một cron gọi runHealthChecks, ghi sự cố vào D1 và đẩy ra
// ALERT_WEBHOOK_URL.

// Runner đập heartbeat mỗi 2.5s và dashboard coi là mất kết nối sau 45s.  Watchdog
// chờ lâu hơn hẳn để một lần restart Scheduled Task (RestartInterval 1 phút) hay
// một cú mạng chập không tự biến thành cảnh báo.
const RUNNER_STALE_MS = 5 * 60 * 1000;
// Một run kẹt ở running/cancel_requested lâu hơn thế này là dấu runner chết giữa
// chừng: không ai còn cập nhật nó nữa.  Một lượt 12 ảnh đo được ~150s, nên một
// giờ là rộng rãi.
const RUN_ORPHAN_MS = 60 * 60 * 1000;
// Service Token Cloudflare Access hết hạn 2027-08-13 và Cloudflare không báo gì.
// Khi hết hạn, runner im lặng quay về lỗi Access và dashboard chỉ nói "chưa kết nối".
const ACCESS_TOKEN_WARN_DAYS = 45;
const ACCESS_TOKEN_SUBJECT = "cloudflare-access-service-token";

// Không đọc được mốc thời gian thì coi là quá hạn: một runner có hàng trong bảng
// nghĩa là nó đã từng heartbeat, nên last_seen_at hỏng là chuyện bất thường và
// im lặng bỏ qua sẽ giấu mất đúng thứ watchdog sinh ra để thấy.
function staleRunners(rows, nowMs, staleMs = RUNNER_STALE_MS) {
  return (rows || []).filter((row) => {
    const seen = Date.parse(row?.last_seen_at || "");
    return !Number.isFinite(seen) || nowMs - seen > staleMs;
  });
}

// Ngược lại với staleRunners: ở đây một mốc thời gian không đọc được sẽ khiến
// watchdog *ghi* vào bot_runs.  Nghi ngờ thì không đụng vào — bỏ sót một run mồ
// côi chỉ tốn một lần dọn tay, còn đánh hỏng một run đang chạy thật thì mất cả
// lượt ảnh.
function orphanRuns(rows, nowMs, orphanMs = RUN_ORPHAN_MS) {
  return (rows || []).filter((row) => {
    const touched = Date.parse(row?.updated_at || row?.started_at || row?.created_at || "");
    return Number.isFinite(touched) && nowMs - touched > orphanMs;
  });
}

function accessTokenIncident(expiresAt, nowMs, warnDays = ACCESS_TOKEN_WARN_DAYS) {
  const expiry = Date.parse(expiresAt || "");
  if (!Number.isFinite(expiry)) return null;
  const days = Math.floor((expiry - nowMs) / 86400000);
  if (days > warnDays) return null;
  const detail = days < 0
    ? `Service Token đã hết hạn ${Math.abs(days)} ngày trước (${expiresAt}). Runner sẽ bị Cloudflare Access chặn.`
    : `Service Token hết hạn sau ${days} ngày (${expiresAt}). Tạo token mới và thêm vào cùng policy trước ngày đó.`;
  return { kind: "access_token_expiring", subject: ACCESS_TOKEN_SUBJECT, detail };
}

function describeStaleRunner(row, nowMs) {
  const seen = Date.parse(row?.last_seen_at || "");
  const label = clean(row?.label || row?.runner_key, 120);
  if (!Number.isFinite(seen)) return `${label}: chưa từng ghi nhận heartbeat hợp lệ.`;
  const minutes = Math.floor((nowMs - seen) / 60000);
  const stamp = new Date(seen).toISOString();
  return minutes >= 120
    ? `${label}: mất tín hiệu ${Math.floor(minutes / 60)} giờ (heartbeat cuối ${stamp}).`
    : `${label}: mất tín hiệu ${minutes} phút (heartbeat cuối ${stamp}).`;
}

// Workerd đọc MỌI named export của module chính như một thành phần của Worker và
// đòi nó phải là hàm hoặc ExportedHandler; export thẳng một hằng số kiểu số làm
// runtime chết ngay lúc khởi động với "Incorrect type for map entry".  Ngưỡng vì
// thế đi ra ngoài qua một hàm, để test đọc được cùng con số mà code đang dùng
// thay vì chép lại.
function healthThresholds() {
  return {
    runnerStaleMs: RUNNER_STALE_MS,
    runOrphanMs: RUN_ORPHAN_MS,
    accessTokenWarnDays: ACCESS_TOKEN_WARN_DAYS,
  };
}

function alertText(incidents) {
  const lines = (incidents || []).map((incident) => `• [${incident.kind}] ${incident.detail}`);
  return `Automation HaviGroup — ${lines.length} sự cố cần xử lý:\n${lines.join("\n")}`;
}

// Mở một sự cố, hoặc không làm gì nếu sự cố cùng (kind, subject) đang mở.  Chốt
// chống trùng nằm ở chỉ số UNIQUE phần của migration 0005, không nằm ở đây: cron
// chạy mỗi 5 phút nên nếu dựa vào một lần SELECT trước INSERT thì hai lần chạy
// chồng nhau vẫn đẻ ra hai hàng.
async function openIncident(env, kind, subject, detail, { resolved = false } = {}) {
  const stamp = now();
  const result = await dbRun(
    env,
    "INSERT OR IGNORE INTO health_incidents (id, kind, subject, detail, opened_at, resolved_at) VALUES (?, ?, ?, ?, ?, ?)",
    id(), kind, subject, cleanText(detail, 1000), stamp, resolved ? stamp : null,
  );
  return Boolean(result.meta?.changes);
}

async function resolveIncident(env, kind, subject) {
  const result = await dbRun(
    env,
    "UPDATE health_incidents SET resolved_at = ? WHERE kind = ? AND subject = ? AND resolved_at IS NULL",
    now(), kind, subject,
  );
  return Boolean(result.meta?.changes);
}

// Đẩy các sự cố chưa báo ra webhook.  Không có ALERT_WEBHOOK_URL thì đánh dấu là
// đã báo và đi tiếp: cảnh báo vẫn nằm trong D1 cho /api/health, và một hàng đợi
// cứ phình mãi vì chưa ai cấu hình nơi nhận thì tự nó cũng là một vấn đề.
async function notifyIncidents(env) {
  const pending = await dbAll(
    env,
    "SELECT id, kind, subject, detail FROM health_incidents WHERE notified_at IS NULL ORDER BY opened_at ASC LIMIT 20",
  );
  if (!pending.length) return { notified: 0, skipped: 0 };
  const webhook = safeExternalUrl(env.ALERT_WEBHOOK_URL);
  if (!webhook) {
    for (const incident of pending) {
      await dbRun(
        env,
        "UPDATE health_incidents SET notified_at = ?, notify_error = ? WHERE id = ?",
        now(), "Chưa cấu hình ALERT_WEBHOOK_URL.", incident.id,
      );
    }
    return { notified: 0, skipped: pending.length };
  }
  let failure = "";
  try {
    const response = await fetch(webhook, {
      method: "POST",
      headers: { "content-type": "application/json; charset=UTF-8" },
      body: JSON.stringify({ text: alertText(pending), incidents: pending }),
    });
    if (!response.ok) failure = `Webhook trả về HTTP ${response.status}.`;
  } catch (caught) {
    failure = clean(caught instanceof Error ? caught.message : "Không gọi được webhook.", 240);
  }
  for (const incident of pending) {
    // Gửi hỏng thì giữ nguyên notified_at = NULL để vòng cron sau thử lại, và
    // ghi lý do lại — giống cách approvals giữ pushed_at NULL khi đẩy lỗi.
    await dbRun(
      env,
      "UPDATE health_incidents SET notified_at = CASE WHEN ? = '' THEN ? ELSE notified_at END, notify_error = ? WHERE id = ?",
      failure, now(), failure, incident.id,
    );
  }
  return failure ? { notified: 0, skipped: pending.length, error: failure } : { notified: pending.length, skipped: 0 };
}

async function runHealthChecks(env, nowMs = Date.now()) {
  const opened = [];
  const runners = await dbAll(env, "SELECT runner_key, label, status, last_seen_at FROM runners");
  const stale = new Set(staleRunners(runners, nowMs).map((row) => row.runner_key));
  for (const row of runners) {
    if (stale.has(row.runner_key)) {
      // status trong bảng chỉ được đặt 'online' lúc heartbeat và chưa từng có ai
      // đặt lại; runnerClaim đọc đúng cột này nên một runner chết vẫn tự nhận là
      // online với chính mình.
      if (row.status === "online") {
        await dbRun(env, "UPDATE runners SET status = 'offline', updated_at = ? WHERE runner_key = ?", now(), row.runner_key);
      }
      const detail = describeStaleRunner(row, nowMs);
      if (await openIncident(env, "runner_offline", row.runner_key, detail)) {
        opened.push({ kind: "runner_offline", subject: row.runner_key, detail });
      }
    } else {
      await resolveIncident(env, "runner_offline", row.runner_key);
    }
  }

  const active = await dbAll(
    env,
    "SELECT id, bot_id, dashboard_id, runner_key, status, created_at, started_at, updated_at FROM bot_runs WHERE status IN ('running', 'cancel_requested')",
  );
  for (const run of orphanRuns(active, nowMs)) {
    const detail = `Run ${run.id} kẹt ở '${run.status}' quá ${Math.floor(RUN_ORPHAN_MS / 60000)} phút sau lần cập nhật cuối; runner ${run.runner_key} nhiều khả năng đã chết giữa chừng.`;
    await dbRun(
      env,
      "UPDATE bot_runs SET status = 'failed', error = ?, finished_at = ?, updated_at = ? WHERE id = ? AND status IN ('running', 'cancel_requested')",
      "Watchdog đóng lần chạy mồ côi: runner ngừng cập nhật.", now(), now(), run.id,
    );
    await dbRun(env, "UPDATE bots SET status = 'error', last_run_status = 'failed', updated_at = ? WHERE id = ?", now(), run.bot_id);
    await addAudit(env, "watchdog", "bot_run.orphaned", "bot_run", run.id, run.dashboard_id, { runner_key: run.runner_key });
    // Mở và đóng cùng lúc: việc đã được xử lý xong ngay tại đây, nhưng vẫn phải
    // báo ra ngoài — notifyIncidents đọc theo notified_at chứ không theo resolved_at.
    if (await openIncident(env, "run_orphaned", run.id, detail, { resolved: true })) {
      opened.push({ kind: "run_orphaned", subject: run.id, detail });
    }
  }

  const tokenIncident = accessTokenIncident(env.ACCESS_TOKEN_EXPIRES_AT, nowMs);
  if (tokenIncident) {
    if (await openIncident(env, tokenIncident.kind, tokenIncident.subject, tokenIncident.detail)) opened.push(tokenIncident);
  } else {
    await resolveIncident(env, "access_token_expiring", ACCESS_TOKEN_SUBJECT);
  }

  const delivery = await notifyIncidents(env);
  return { checked_runners: runners.length, opened: opened.length, incidents: opened, delivery };
}

// Ai đăng nhập được Automation Center thì xem được sức khoẻ host.  Không có gì
// bí mật ở đây, và người trực cần thấy nó mà không phải hỏi Owner.
async function healthOverview(env, nowMs = Date.now()) {
  const [runners, open, recent] = await Promise.all([
    dbAll(env, "SELECT runner_key, label, status, version, last_seen_at FROM runners ORDER BY runner_key ASC"),
    dbAll(env, "SELECT id, kind, subject, detail, opened_at FROM health_incidents WHERE resolved_at IS NULL ORDER BY opened_at ASC"),
    dbAll(env, "SELECT id, kind, subject, detail, opened_at, resolved_at FROM health_incidents ORDER BY opened_at DESC LIMIT 20"),
  ]);
  const stale = new Set(staleRunners(runners, nowMs).map((row) => row.runner_key));
  return {
    checked_at: new Date(nowMs).toISOString(),
    healthy: open.length === 0 && runners.every((row) => !stale.has(row.runner_key)),
    runners: runners.map((row) => ({ ...row, online: !stale.has(row.runner_key) })),
    open_incidents: open,
    recent_incidents: recent,
  };
}

async function reviewApproval(request, env, user, slug, approvalId) {
  const { dashboard } = await requireDashboard(env, slug, user, "review");
  const body = await readJson(request);
  const status = clean(body.status, 20).toLowerCase();
  if (!["approved", "rejected"].includes(status)) return error("Quyết định duyệt không hợp lệ.");
  const approval = await dbFirst(env, "SELECT * FROM approvals WHERE id = ? AND dashboard_id = ?", approvalId, dashboard.id);
  if (!approval) return error("Không tìm thấy yêu cầu duyệt.", 404);
  if (approval.status !== "pending") return error("Yêu cầu này đã có quyết định.", 409);
  await dbRun(
    env,
    "UPDATE approvals SET status = ?, reviewed_by = ?, reviewed_at = ? WHERE id = ?",
    status, user.email, now(), approval.id,
  );
  await addAudit(env, user.email, `approval.${status}`, "approval", approval.id, dashboard.id, { title: approval.title });
  return json({ ok: true, status });
}

// ─── Agent điều phối ────────────────────────────────────────────────────────

// Dòng theo email thắng dòng theo vai trò: ngoại lệ cho một người phải mở
// (hoặc siết) được mà không đụng tới cả vai trò.  Không có dòng nào và không
// phải Owner thì không có phạm vi — đóng mặc định.
async function resolveCodeScope(env, dashboard, user, role) {
  const rows = await dbAll(
    env,
    "SELECT subject_type, subject, allow_globs, max_files, max_lines, auto_apply, note FROM code_scopes WHERE dashboard_id = ? AND ((subject_type = 'user' AND subject = ?) OR (subject_type = 'role' AND subject = ?))",
    dashboard.id, user.email, role,
  );
  const row = rows.find((item) => item.subject_type === "user") || rows.find((item) => item.subject_type === "role");
  if (!row) return role === "owner" ? { ...OWNER_DEFAULT_SCOPE } : null;
  const globs = parseGlobList(row.allow_globs);
  if (!globs.length) return null;
  return {
    allow_globs: globs,
    max_files: Math.max(1, Number(row.max_files) || 1),
    max_lines: Math.max(1, Number(row.max_lines) || 1),
    auto_apply: row.auto_apply ? 1 : 0,
    note: String(row.note || ""),
    source: `${row.subject_type}:${row.subject}`,
  };
}

// Đối chiếu danh sách file thật trong patch với phạm vi đã đóng băng.
function auditChangedFiles(files, scope) {
  const paths = [];
  const outside = [];
  const protectedPaths = [];
  for (const entry of Array.isArray(files) ? files.slice(0, 200) : []) {
    const path = normaliseRepoPath(entry?.path);
    if (!path) {
      outside.push(clean(entry?.path || "(đường dẫn trống)", 200));
      continue;
    }
    paths.push(path);
    if (!matchesAnyGlob(path, scope.allow_globs)) outside.push(path);
    if (isProtectedPath(path)) protectedPaths.push(path);
  }
  return { paths, outside, protectedPaths };
}

// ─── Agent trung tâm: ranh giới quyền điều khiển ─────────────────────────────
//
// Toàn bộ khối này là hàm thuần, không I/O: đây là phần quyết định một lệnh có
// được chạy hay không, nên nó phải kiểm được ngoài môi trường Worker.

// Múi giờ quy ước cứng: Asia/Ho_Chi_Minh = UTC+7, không DST.  Worker chạy giờ
// UTC còn khung giờ do người cấp khai theo giờ VN; tính sai một lần là phạm vi
// hoặc quá chặt hoặc quá lỏng theo chu kỳ ngày.
const VN_OFFSET_MS = 7 * 60 * 60 * 1000;

const vietnamHour = (utcMillis) => new Date(Number(utcMillis) + VN_OFFSET_MS).getUTCHours();

// Mốc 00:00 giờ VN của ngày chứa utcMillis, trả về ISO UTC.  Dùng làm cận dưới
// cho câu đếm trần lệnh/ngày, để "hôm nay" là hôm nay theo giờ người dùng chứ
// không phải theo giờ UTC.
function vietnamDayStartIso(utcMillis) {
  const shifted = new Date(Number(utcMillis) + VN_OFFSET_MS);
  const startUtc = Date.UTC(shifted.getUTCFullYear(), shifted.getUTCMonth(), shifted.getUTCDate()) - VN_OFFSET_MS;
  return new Date(startUtc).toISOString();
}

// "08-18" = từ 08:00 đến trước 19:00 giờ VN.  Rỗng = mọi giờ.  Chuỗi rác KHÔNG
// được hiểu là "mọi giờ": một khung giờ gõ sai phải đóng lại, không mở ra.
function parseAllowedHours(value) {
  const raw = String(value ?? "").trim();
  if (!raw) return { kind: "any" };
  const matched = /^(\d{1,2})\s*-\s*(\d{1,2})$/.exec(raw);
  if (!matched) return { kind: "invalid" };
  const start = Number(matched[1]);
  const end = Number(matched[2]);
  if (!Number.isInteger(start) || !Number.isInteger(end)) return { kind: "invalid" };
  if (start < 0 || start > 23 || end < 0 || end > 23) return { kind: "invalid" };
  // "08-08" không có nghĩa: nó vừa đọc được là "không giờ nào" vừa đọc được là
  // "mọi giờ".  Mơ hồ thì đóng.
  if (start === end) return { kind: "invalid" };
  return { kind: "window", start, end };
}

function isWithinAllowedHours(value, utcMillis) {
  const window = parseAllowedHours(value);
  if (window.kind === "any") return true;
  if (window.kind === "invalid") return false;
  const hour = vietnamHour(utcMillis);
  // Khung qua đêm ("22-06") là start > end: giờ hợp lệ nằm ở hai đầu ngày.
  return window.start < window.end
    ? hour >= window.start && hour < window.end
    : hour >= window.start || hour < window.end;
}

// Runner key là định danh máy móc do Owner đặt.  So khớp bằng nhau tuyệt đối,
// mỗi dòng một key; không glob, không tiền tố.
const parseRunnerKeyList = (value) => String(value ?? "")
  .split(/[\n,]/)
  .map((line) => clean(line, 120))
  .filter(Boolean)
  .filter((key, index, list) => list.indexOf(key) === index)
  .slice(0, 40);

const parseActionList = (value) => String(value ?? "")
  .split(/[\n,\s]+/)
  .map((item) => clean(item, 20).toLowerCase())
  .filter((item) => CONTROL_ACTIONS.includes(item))
  .filter((item, index, list) => list.indexOf(item) === index);

const isProtectedRunnerKey = (runnerKey) => PROTECTED_RUNNER_KEYS.includes(clean(runnerKey, 120));

// Một runner được coi là sống khi nó vừa heartbeat trong RUNNER_ONLINE_WITHIN_MS.
// Cột status trong bảng không đủ: một runner bị kill không kịp ghi 'offline',
// nên chỉ tin vào last_seen_at.
const runnerIsOnline = (runner, atMillis = Date.now()) => Boolean(
  runner?.status === "online" && runner.last_seen_at
  && atMillis - Date.parse(runner.last_seen_at) < RUNNER_ONLINE_WITHIN_MS,
);

// Một dòng agent_control_scopes → phạm vi đã chuẩn hoá.  Dòng không cho phép
// runner nào hoặc action nào là dòng vô nghĩa: trả null để nơi gọi coi như
// "chưa được cấp", thay vì một phạm vi rỗng trông như đã cấp.
function normaliseControlScopeRow(row) {
  if (!row) return null;
  const runnerKeys = parseRunnerKeyList(row.allow_runner_keys);
  const actions = parseActionList(row.allow_actions);
  if (!runnerKeys.length || !actions.length) return null;
  const maxPerDay = Math.max(1, Math.min(200, Number(row.max_commands_per_day) || 1));
  return {
    allow_runner_keys: runnerKeys,
    any_runner_key: false,
    allow_actions: actions,
    max_commands_per_day: maxPerDay,
    allowed_hours: String(row.allowed_hours || ""),
    note: String(row.note || ""),
    source: `${row.subject_type}:${row.subject}`,
  };
}

// Phạm vi đọc lại từ scope_json → phạm vi dùng được.  Dòng trong D1 do Worker
// tự ghi, nhưng đây là dữ liệu đã nằm im một thời gian: một khoá thiếu hay sai
// kiểu không được phép biến thành "cho tất cả".  Mọi trường hợp mơ hồ trả null
// (= chưa được cấp) và any_runner_key chỉ đúng khi nó đúng là true.
function normaliseFrozenScope(frozen) {
  if (!frozen || typeof frozen !== "object") return null;
  const anyRunnerKey = frozen.any_runner_key === true;
  const runnerKeys = Array.isArray(frozen.allow_runner_keys)
    ? frozen.allow_runner_keys.map((key) => clean(key, 120)).filter(Boolean)
    : [];
  const actions = Array.isArray(frozen.allow_actions)
    ? frozen.allow_actions.map((action) => clean(action, 20).toLowerCase()).filter((action) => CONTROL_ACTIONS.includes(action))
    : [];
  if ((!anyRunnerKey && !runnerKeys.length) || !actions.length) return null;
  return {
    allow_runner_keys: runnerKeys,
    any_runner_key: anyRunnerKey,
    allow_actions: actions,
    max_commands_per_day: Math.max(1, Math.min(200, Number(frozen.max_commands_per_day) || 1)),
    allowed_hours: String(frozen.allowed_hours || ""),
    note: String(frozen.note || ""),
    source: String(frozen.source || "frozen"),
  };
}

// Kiểm một lệnh, độc lập với đề xuất của mô hình.  Nơi gọi tra bot trong D1 và
// đưa vào đây; hàm này không đọc gì, nên mọi nhánh từ chối đều kiểm được.
//
// Thứ tự kiểm là thứ tự của ba lớp: lớp 3 (runner được bảo vệ) chặn trước phạm
// vi, để lý do từ chối nói đúng cái luật đã chặn — người đọc audit cần biết
// "bị chặn vì runner được bảo vệ", không phải "ngoài phạm vi".
function validateControlCommand(command, scope, context = {}) {
  const deny = (code, reason) => ({ ok: false, code, reason });
  const action = clean(command?.action, 20).toLowerCase();
  const bot = command?.bot || null;
  const runnerKey = clean(bot?.runner_key, 120);

  if (!scope) {
    return deny("no_scope", "Bạn chưa được cấp phạm vi điều khiển agent trong dashboard này.");
  }
  if (!CONTROL_ACTIONS.includes(action)) {
    return deny("unknown_action", `Action điều khiển không hợp lệ: chỉ nhận ${CONTROL_ACTIONS.join(", ")}.`);
  }
  if (!bot) {
    return deny("unknown_target", "Không tìm thấy bot đích trong dashboard này.");
  }
  // Ranh giới dashboard là lớp nền: một phạm vi cấp ở dashboard A không với
  // sang bot của dashboard B.
  if (context.dashboardId && bot.dashboard_id !== context.dashboardId) {
    return deny("wrong_dashboard", "Bot đích không thuộc dashboard này.");
  }
  if (!runnerKey) {
    return deny("no_runner", "Bot đích chưa được gán runner nên không điều khiển được.");
  }
  if (isProtectedRunnerKey(runnerKey)) {
    return deny("protected_runner", `Runner "${runnerKey}" nằm trong danh sách được bảo vệ; không lệnh nào điều khiển được nó.`);
  }
  if (!scope.allow_actions.includes(action)) {
    return deny("action_out_of_scope", `Phạm vi của bạn không có action "${action}".`);
  }
  if (!scope.any_runner_key && !scope.allow_runner_keys.includes(runnerKey)) {
    return deny("target_out_of_scope", `Runner "${runnerKey}" không nằm trong phạm vi điều khiển của bạn.`);
  }
  // recover ép một run đang chạy thành failed — đó là quyền dọn dẹp, không phải
  // quyền vận hành hằng ngày, nên nó có capability riêng.
  if (action === "recover" && !context.canRecover) {
    return deny("no_recover_capability", "Chỉ Owner/Admin được khôi phục run mồ côi.");
  }
  // Trần lệnh là phanh chi phí, không phải ranh giới an ninh: hai yêu cầu đua
  // nhau có thể cùng thấy 19/20 và cùng qua.  Chấp nhận lệch ±1 — D1 không có
  // transaction đa câu tiện dụng trong Worker, và một khoá tự chế ở đây sẽ hỏng
  // theo cách khó thấy hơn nhiều so với một lệnh thừa.
  const used = Math.max(0, Number(context.commandsToday) || 0);
  if (used >= scope.max_commands_per_day) {
    return deny("daily_limit", `Đã dùng hết ${scope.max_commands_per_day} lệnh trong ngày hôm nay (giờ VN).`);
  }
  // Dừng khẩn không chờ giờ hành chính: khung giờ giới hạn việc KHỞI ĐỘNG thêm
  // việc, không được biến thành lý do để một bot chạy sai tiếp tục chạy.
  if (action !== "stop" && !isWithinAllowedHours(scope.allowed_hours, context.at)) {
    return deny("outside_hours", `Ngoài khung giờ được phép (${scope.allowed_hours || "không hợp lệ"}, giờ VN).`);
  }
  return { ok: true, action, botId: String(bot.id || ""), runnerKey };
}

// Cột JSON trong D1 do Worker tự ghi, nhưng một dòng cũ (hoặc một lần sửa tay
// bằng wrangler d1 execute) có thể không parse được.  Trả về mặc định thay vì
// làm hỏng cả trang lịch sử vì một dòng lỗi.
const safeJson = (value, fallback = null) => {
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
};

async function addAgentMessage(env, thread, kind, content, meta = {}) {
  await dbRun(
    env,
    "INSERT INTO agent_messages (id, thread_id, dashboard_id, kind, author_email, content, request_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    id(), thread.id, thread.dashboard_id, kind, clean(meta.author, 254),
    cleanBlock(content, 6000), clean(meta.requestId, 60), now(),
  );
  await dbRun(env, "UPDATE agent_threads SET updated_at = ? WHERE id = ?", now(), thread.id);
}

// Không có diff_text ở đây là cố ý: danh sách được poll lại vài giây một lần,
// còn một diff có thể tới 60 KB.  Chỉ gửi độ dài để giao diện biết có gì để
// xem, rồi tải nội dung khi người duyệt thật sự bấm.
const REQUEST_COLUMNS = "id, thread_id, requested_by, requested_role, instruction, status, plan_summary, files_json, files_changed, lines_changed, diff_truncated, bot_commands_json, touches_protected, tests_passed, test_output, branch, commit_sha, error, decided_by, decided_at, auto_applied, scope_json, created_at, updated_at, finished_at, LENGTH(diff_text) AS diff_length";

async function agentOverview(env, dashboard, role, user) {
  const scope = await resolveCodeScope(env, dashboard, user, role);
  const [threads, requests] = await Promise.all([
    dbAll(env, "SELECT id, title, created_by, status, created_at, updated_at FROM agent_threads WHERE dashboard_id = ? ORDER BY updated_at DESC LIMIT 30", dashboard.id),
    dbAll(env, `SELECT ${REQUEST_COLUMNS} FROM code_change_requests WHERE dashboard_id = ? ORDER BY created_at DESC LIMIT 30`, dashboard.id),
  ]);
  const runner = await dbFirst(env, "SELECT status, last_seen_at, last_error FROM runners WHERE runner_key = ?", ORCHESTRATOR_RUNNER_KEY);
  const payload = {
    threads,
    requests,
    scope,
    permissions: permissionsFor(role),
    protected_globs: PROTECTED_GLOBS,
    runner: {
      runner_key: ORCHESTRATOR_RUNNER_KEY,
      online: runnerIsOnline(runner),
      last_seen_at: runner?.last_seen_at || null,
      last_error: runner?.last_error || "",
    },
  };
  if (capability(role, "manage_members")) {
    payload.scopes = await dbAll(
      env,
      "SELECT id, subject_type, subject, allow_globs, max_files, max_lines, auto_apply, note, updated_by, updated_at FROM code_scopes WHERE dashboard_id = ? ORDER BY subject_type, subject",
      dashboard.id,
    );
  }
  return payload;
}

async function agentThreadDetail(env, dashboard, threadId) {
  const thread = await dbFirst(env, "SELECT * FROM agent_threads WHERE id = ? AND dashboard_id = ?", threadId, dashboard.id);
  if (!thread) throw new Response("Không tìm thấy luồng trao đổi.", { status: 404 });
  const [messages, requests] = await Promise.all([
    dbAll(env, "SELECT id, kind, author_email, content, request_id, created_at FROM agent_messages WHERE thread_id = ? ORDER BY created_at ASC LIMIT 200", thread.id),
    dbAll(env, `SELECT ${REQUEST_COLUMNS} FROM code_change_requests WHERE thread_id = ? ORDER BY created_at ASC LIMIT 50`, thread.id),
  ]);
  return { thread, messages, requests };
}

// Diff tải riêng, không đi kèm danh sách.  Vẫn phải khoá theo dashboard: id
// yêu cầu đoán được thì diff của dashboard khác cũng đọc được.
async function agentRequestDiff(env, dashboard, requestId) {
  const row = await dbFirst(
    env,
    "SELECT id, diff_text, diff_truncated, branch FROM code_change_requests WHERE id = ? AND dashboard_id = ?",
    requestId, dashboard.id,
  );
  if (!row) throw new Response("Không tìm thấy yêu cầu.", { status: 404 });
  return row;
}

// Một tin nhắn của người dùng luôn sinh ra một yêu cầu cho agent.  Agent tự
// quyết định đó là câu hỏi (trả lời, status "answered") hay là lệnh sửa.
// Cửa vào của một đường chat: đã được cấp phạm vi chưa, và runner sẽ xử lý có
// còn sống không.  Tách khỏi queue*Request để nơi tạo luồng gọi được TRƯỚC khi
// ghi hàng agent_threads — nếu để queue*Request ném lỗi thì luồng đã ghi rồi và
// nằm lại vĩnh viễn: mỗi lần bị từ chối là một luồng rỗng.  Hai tab Chat và
// Điều khiển bot dùng CHUNG bảng agent_threads và danh sách chỉ hiện 30 hàng
// mới nhất, nên luồng rỗng của bên này đẩy luồng thật của bên kia ra khỏi màn
// hình — hỏng ở đường A hiện thành mất dữ liệu ở đường B.
async function codeRequestGate(env, dashboard, user, role) {
  const scope = await resolveCodeScope(env, dashboard, user, role);
  if (!scope) {
    throw new Response("Bạn chưa được cấp phạm vi sửa code trong dashboard này. Hãy nhờ Owner hoặc Admin mở phạm vi.", { status: 403 });
  }
  const runner = await dbFirst(env, "SELECT status, last_seen_at FROM runners WHERE runner_key = ?", ORCHESTRATOR_RUNNER_KEY);
  if (!runnerIsOnline(runner)) {
    throw new Response("Máy trung tâm chưa kết nối. Yêu cầu sẽ không có ai xử lý, nên không xếp hàng.", { status: 409 });
  }
  return scope;
}

async function queueCodeRequest(env, dashboard, user, role, thread, instruction, gated = null) {
  const scope = gated || await codeRequestGate(env, dashboard, user, role);
  const requestId = id();
  await addAgentMessage(env, thread, "user", instruction, { author: user.email, requestId });
  await dbRun(
    env,
    "INSERT INTO code_change_requests (id, dashboard_id, thread_id, runner_key, repo, requested_by, requested_role, instruction, scope_json, status, created_at, updated_at) VALUES (?, ?, ?, ?, 'flow-v2', ?, ?, ?, ?, 'queued', ?, ?)",
    requestId, dashboard.id, thread.id, ORCHESTRATOR_RUNNER_KEY, user.email, role,
    cleanBlock(instruction, 6000), JSON.stringify(scope), now(), now(),
  );
  await addAudit(env, user.email, "code_request.queued", "code_request", requestId, dashboard.id, {
    thread_id: thread.id, role, scope_source: scope.source, auto_apply: scope.auto_apply,
  });
  return { requestId, scope };
}

async function createAgentThread(request, env, user, slug) {
  const { dashboard, role } = await requireDashboard(env, slug, user, "code_request");
  const body = await readJson(request);
  const instruction = cleanBlock(body.message, 6000).trim();
  if (instruction.length < 8) return error("Hãy mô tả yêu cầu rõ hơn (ít nhất 8 ký tự).");
  const title = clean(body.title || instruction, 120);
  const gated = await codeRequestGate(env, dashboard, user, role);
  const thread = { id: id(), dashboard_id: dashboard.id };
  await dbRun(
    env,
    "INSERT INTO agent_threads (id, dashboard_id, title, created_by, status, created_at, updated_at) VALUES (?, ?, ?, ?, 'open', ?, ?)",
    thread.id, dashboard.id, title, user.email, now(), now(),
  );
  const { requestId } = await queueCodeRequest(env, dashboard, user, role, thread, instruction, gated);
  return json({ thread_id: thread.id, request_id: requestId }, 201);
}

async function postAgentMessage(request, env, user, slug, threadId) {
  const { dashboard, role } = await requireDashboard(env, slug, user, "code_request");
  const thread = await dbFirst(env, "SELECT * FROM agent_threads WHERE id = ? AND dashboard_id = ?", threadId, dashboard.id);
  if (!thread) return error("Không tìm thấy luồng trao đổi.", 404);
  if (thread.status !== "open") return error("Luồng này đã đóng.", 409);
  const body = await readJson(request);
  const instruction = cleanBlock(body.message, 6000).trim();
  if (instruction.length < 8) return error("Hãy mô tả yêu cầu rõ hơn (ít nhất 8 ký tự).");
  const pending = await dbFirst(
    env,
    "SELECT id FROM code_change_requests WHERE thread_id = ? AND status IN ('queued', 'planning', 'applying') LIMIT 1",
    thread.id,
  );
  if (pending) return error("Agent đang xử lý yêu cầu trước trong luồng này. Hãy chờ nó trả lời.", 409);
  const { requestId } = await queueCodeRequest(env, dashboard, user, role, thread, instruction);
  return json({ request_id: requestId }, 201);
}

async function decideCodeRequest(request, env, user, slug, requestId) {
  const { dashboard, role } = await requireDashboard(env, slug, user, "view");
  const body = await readJson(request);
  const decision = clean(body.decision, 20).toLowerCase();
  if (!["approved", "rejected", "cancelled"].includes(decision)) return error("Quyết định không hợp lệ.");
  const row = await dbFirst(env, "SELECT * FROM code_change_requests WHERE id = ? AND dashboard_id = ?", requestId, dashboard.id);
  if (!row) return error("Không tìm thấy yêu cầu sửa code.", 404);

  if (decision === "cancelled") {
    // Người gửi luôn rút lại được yêu cầu của chính mình, kể cả khi runner
    // đang chạy — runner đọc trạng thái trước khi ghi kết quả.
    if (row.requested_by !== user.email && !capability(role, "code_approve")) {
      return error("Chỉ người gửi hoặc Admin mới rút lại được yêu cầu này.", 403);
    }
    if (!["queued", "planning", "awaiting_approval"].includes(row.status)) return error("Yêu cầu này đã kết thúc.", 409);
    await dbRun(env, "UPDATE code_change_requests SET status = 'cancelled', decided_by = ?, decided_at = ?, updated_at = ?, finished_at = ? WHERE id = ?", user.email, now(), now(), now(), row.id);
    await addAudit(env, user.email, "code_request.cancelled", "code_request", row.id, dashboard.id, {});
    return json({ ok: true, status: "cancelled" });
  }

  if (!capability(role, "code_approve")) return error("Bạn không có quyền duyệt thay đổi code.", 403);
  if (row.status !== "awaiting_approval") return error("Yêu cầu này không ở trạng thái chờ duyệt.", 409);
  // Người gửi tự duyệt thay đổi của chính mình thì lớp duyệt không còn nghĩa
  // gì; Owner được miễn vì trong công ty này Owner là cấp cuối.
  if (row.requested_by === user.email && user.global_role !== "owner") {
    return error("Bạn không thể tự duyệt thay đổi do chính mình yêu cầu.", 403);
  }
  if (decision === "approved" && row.touches_protected && user.global_role !== "owner") {
    return error("Thay đổi này chạm vào file được bảo vệ (bí mật, hạ tầng, hoặc chính phần phân quyền). Chỉ Owner mới duyệt được.", 403);
  }
  const nextStatus = decision === "approved" ? "approved" : "rejected";
  await dbRun(
    env,
    "UPDATE code_change_requests SET status = ?, decided_by = ?, decided_at = ?, updated_at = ?, finished_at = CASE WHEN ? = 'rejected' THEN ? ELSE finished_at END WHERE id = ?",
    nextStatus, user.email, now(), now(), nextStatus, now(), row.id,
  );
  const thread = await dbFirst(env, "SELECT * FROM agent_threads WHERE id = ?", row.thread_id);
  if (thread) {
    await addAgentMessage(env, thread, "system", decision === "approved"
      ? `${user.email} đã duyệt. Máy trung tâm sẽ áp thay đổi này.`
      : `${user.email} đã từ chối thay đổi này. Không có file nào bị đổi.`, { author: user.email, requestId: row.id });
  }
  await addAudit(env, user.email, `code_request.${nextStatus}`, "code_request", row.id, dashboard.id, {
    files_changed: row.files_changed, touches_protected: Boolean(row.touches_protected),
  });
  return json({ ok: true, status: nextStatus });
}

async function saveCodeScope(request, env, user, slug) {
  const { dashboard, role } = await requireDashboard(env, slug, user, "manage_members");
  const body = await readJson(request);
  const subjectType = clean(body.subject_type, 10).toLowerCase();
  if (!["role", "user"].includes(subjectType)) return error("Loại đối tượng phải là role hoặc user.");
  const domain = clean(env.COMPANY_EMAIL_DOMAIN || "havigroup.llc", 120).toLowerCase();
  const subject = subjectType === "role"
    ? clean(body.subject, 20).toLowerCase()
    : clean(body.subject, 254).toLowerCase();
  if (subjectType === "role" && !["admin", "operator", "reviewer", "viewer"].includes(subject)) {
    return error("Vai trò không hợp lệ.");
  }
  if (subjectType === "user" && !subject.endsWith(`@${domain}`)) return error("Email phải thuộc công ty.");

  const globs = parseGlobList(body.allow_globs);
  const maxFiles = Math.max(1, Math.min(60, Number.parseInt(body.max_files, 10) || 3));
  const maxLines = Math.max(1, Math.min(6000, Number.parseInt(body.max_lines, 10) || 200));
  const autoApply = body.auto_apply === true || body.auto_apply === "true" ? 1 : 0;
  // Phạm vi rỗng là cách gỡ quyền: xoá hẳn dòng thay vì để lại một allowlist
  // trống mà người đọc bảng dễ tưởng là "cho tất cả".
  if (!globs.length) {
    await dbRun(env, "DELETE FROM code_scopes WHERE dashboard_id = ? AND subject_type = ? AND subject = ?", dashboard.id, subjectType, subject);
    await addAudit(env, user.email, "code_scope.revoked", "code_scope", `${subjectType}:${subject}`, dashboard.id, {});
    return json({ ok: true, removed: true });
  }
  // Cho auto_apply là cho phép sửa code mà không ai xem lại. Đó là quyết định
  // của Owner, không phải của Admin.
  if (autoApply && user.global_role !== "owner") {
    return error("Chỉ Owner mới bật được chế độ áp thẳng không cần duyệt.", 403);
  }
  const blocked = globs.filter((glob) => PROTECTED_GLOBS.some((protectedGlob) => protectedGlob === glob));
  if (blocked.length) return error(`Không thể cấp phạm vi trùng khít file được bảo vệ: ${blocked.join(", ")}`);

  await dbRun(
    env,
    "INSERT INTO code_scopes (id, dashboard_id, subject_type, subject, allow_globs, max_files, max_lines, auto_apply, note, updated_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(dashboard_id, subject_type, subject) DO UPDATE SET allow_globs = excluded.allow_globs, max_files = excluded.max_files, max_lines = excluded.max_lines, auto_apply = excluded.auto_apply, note = excluded.note, updated_by = excluded.updated_by, updated_at = excluded.updated_at",
    id(), dashboard.id, subjectType, subject, globs.join("\n"), maxFiles, maxLines, autoApply,
    clean(body.note, 240), user.email, now(), now(),
  );
  await addAudit(env, user.email, "code_scope.saved", "code_scope", `${subjectType}:${subject}`, dashboard.id, {
    globs, max_files: maxFiles, max_lines: maxLines, auto_apply: Boolean(autoApply), actor_role: role,
  });
  return json({ ok: true });
}

// ─── Agent điều phối · phía runner ──────────────────────────────────────────

async function runnerClaimCodeRequest(request, env) {
  const body = await readJson(request);
  const runnerKey = clean(body.runner_key, 120);
  if (!runnerKey) return error("Runner key là bắt buộc.");
  const runner = await dbFirst(env, "SELECT runner_key, status FROM runners WHERE runner_key = ?", runnerKey);
  if (!runner || runner.status !== "online") return error("Runner chưa heartbeat hoặc đang offline.", 409);
  const queued = await dbFirst(
    env,
    "SELECT * FROM code_change_requests WHERE runner_key = ? AND status = 'queued' ORDER BY created_at ASC LIMIT 1",
    runnerKey,
  );
  if (!queued) return json({ request: null });
  const claimed = await dbRun(
    env,
    "UPDATE code_change_requests SET status = 'planning', started_at = ?, updated_at = ? WHERE id = ? AND status = 'queued'",
    now(), now(), queued.id,
  );
  if (!claimed.meta?.changes) return json({ request: null });
  const history = await dbAll(
    env,
    "SELECT kind, author_email, content, created_at FROM agent_messages WHERE thread_id = ? ORDER BY created_at ASC LIMIT 40",
    queued.thread_id,
  );
  let scope = {};
  try { scope = JSON.parse(queued.scope_json || "{}"); } catch { scope = {}; }
  // Agent chỉ điều khiển được bot khi CHÍNH người gửi yêu cầu điều khiển được
  // — ranh giới đúng bằng cái nút họ tự bấm được trên web.  Vai trò lấy bản đã
  // đóng băng lúc xếp việc, không đọc lại vai trò hiện tại.
  const mayControlBots = capability(queued.requested_role, "run");
  const bots = mayControlBots
    ? await dbAll(env, "SELECT id, name, purpose, status, runner_key FROM bots WHERE dashboard_id = ? ORDER BY name ASC", queued.dashboard_id)
    : [];
  return json({
    request: {
      id: queued.id,
      thread_id: queued.thread_id,
      repo: queued.repo,
      instruction: queued.instruction,
      requested_by: queued.requested_by,
      requested_role: queued.requested_role,
      scope,
      protected_globs: PROTECTED_GLOBS,
      may_control_bots: mayControlBots,
      bots,
      history,
    },
  });
}

async function runnerCodeRequestStatus(env, requestId, runnerKey) {
  const row = await dbFirst(env, "SELECT id, status, runner_key FROM code_change_requests WHERE id = ?", requestId);
  if (!row || row.runner_key !== runnerKey) return error("Không tìm thấy yêu cầu của runner này.", 404);
  return json({ request: { id: row.id, status: row.status } });
}

async function runnerApprovedCodeRequests(env, runnerKey) {
  if (!runnerKey) return error("Runner key là bắt buộc.");
  const rows = await dbAll(
    env,
    "SELECT id, thread_id, repo, branch, files_json, instruction, auto_applied FROM code_change_requests WHERE runner_key = ? AND status = 'approved' ORDER BY decided_at ASC LIMIT 5",
    runnerKey,
  );
  return json({ requests: rows });
}

// Runner báo kết quả.  Đây là chỗ danh sách file thật được đối chiếu lại với
// phạm vi đã đóng băng — runner cũng tự kiểm, nhưng Worker mới là bên giữ
// quyền, nên nó không tin lời runner về việc patch nằm trong giới hạn.
async function runnerUpdateCodeRequest(request, env, requestId) {
  const body = await readJson(request);
  const runnerKey = clean(body.runner_key, 120);
  const status = clean(body.status, 32).toLowerCase();
  if (!runnerKey || !["planning", "awaiting_approval", "answered", "applying", "applied", "failed", "bot_action"].includes(status)) {
    return error("Cập nhật yêu cầu sửa code không hợp lệ.");
  }
  const row = await dbFirst(env, "SELECT * FROM code_change_requests WHERE id = ? AND runner_key = ?", requestId, runnerKey);
  if (!row) return error("Không tìm thấy yêu cầu của runner này.", 404);
  if (["applied", "answered", "failed", "rejected", "cancelled", "bot_done"].includes(row.status)) {
    return json({ ok: true, idempotent: true, status: row.status });
  }
  const thread = await dbFirst(env, "SELECT * FROM agent_threads WHERE id = ?", row.thread_id);
  const summary = cleanBlock(body.plan_summary, 4000);
  const testOutput = cleanBlock(body.test_output, 8000);
  const testsPassed = body.tests_passed === true ? 1 : 0;

  if (status === "planning" || status === "applying") {
    await dbRun(env, "UPDATE code_change_requests SET status = ?, updated_at = ? WHERE id = ?", status, now(), row.id);
    return json({ ok: true });
  }

  if (status === "failed") {
    const detail = cleanBlock(body.error, 4000) || "Máy trung tâm không hoàn thành được yêu cầu.";
    await dbRun(
      env,
      "UPDATE code_change_requests SET status = 'failed', plan_summary = ?, test_output = ?, error = ?, updated_at = ?, finished_at = ? WHERE id = ?",
      summary, testOutput, detail, now(), now(), row.id,
    );
    if (thread) await addAgentMessage(env, thread, "agent", `Không thực hiện được: ${detail}`, { author: "agent", requestId: row.id });
    await addAudit(env, `runner:${runnerKey}`, "code_request.failed", "code_request", row.id, row.dashboard_id, {});
    return json({ ok: true });
  }

  if (status === "bot_action") {
    // Agent xin điều khiển bot khác.  Quyền lấy từ vai trò đã đóng băng lúc
    // xếp việc, và mỗi lệnh vẫn đi qua đúng lõi mà nút bấm trên web dùng —
    // runner không được cấp thêm quyền nào so với chính người gửi.
    if (!capability(row.requested_role, "run")) {
      const detail = "Người gửi yêu cầu không có quyền chạy hay dừng bot.";
      await dbRun(env, "UPDATE code_change_requests SET status = 'failed', plan_summary = ?, error = ?, updated_at = ?, finished_at = ? WHERE id = ?", summary, detail, now(), now(), row.id);
      if (thread) await addAgentMessage(env, thread, "system", detail, { author: "system", requestId: row.id });
      return json({ ok: true, blocked: true, error: detail });
    }
    const dashboard = await dbFirst(env, "SELECT * FROM dashboards WHERE id = ?", row.dashboard_id);
    const commands = Array.isArray(body.bot_commands) ? body.bot_commands.slice(0, 5) : [];
    const results = [];
    for (const entry of commands) {
      const botId = clean(entry?.bot_id, 120);
      const action = clean(entry?.command, 20).toLowerCase();
      const outcome = dashboard
        ? await runBotCommand(env, dashboard, `agent:${row.requested_by}`, botId, action, entry || {})
        : { ok: false, message: "Không tìm thấy dashboard." };
      results.push({ bot_id: botId, command: action, ok: Boolean(outcome.ok), message: outcome.message });
    }
    const lines = results.length
      ? results.map((item) => `${item.ok ? "✓" : "✗"} ${item.command} ${item.bot_id}: ${item.message}`).join("\n")
      : "Agent không đưa ra lệnh bot nào.";
    await dbRun(
      env,
      "UPDATE code_change_requests SET status = 'bot_done', plan_summary = ?, bot_commands_json = ?, updated_at = ?, finished_at = ? WHERE id = ?",
      summary, JSON.stringify(results), now(), now(), row.id,
    );
    if (thread) await addAgentMessage(env, thread, "agent", `${summary}\n\n${lines}`, { author: "agent", requestId: row.id });
    await addAudit(env, `agent:${row.requested_by}`, "code_request.bot_action", "code_request", row.id, row.dashboard_id, { commands: results });
    return json({ ok: true, results });
  }

  if (status === "answered") {
    await dbRun(
      env,
      "UPDATE code_change_requests SET status = 'answered', plan_summary = ?, updated_at = ?, finished_at = ? WHERE id = ?",
      summary, now(), now(), row.id,
    );
    if (thread) await addAgentMessage(env, thread, "agent", summary || "(agent không trả lời gì)", { author: "agent", requestId: row.id });
    return json({ ok: true });
  }

  if (status === "applied") {
    await dbRun(
      env,
      "UPDATE code_change_requests SET status = 'applied', branch = ?, commit_sha = ?, test_output = CASE WHEN ? <> '' THEN ? ELSE test_output END, updated_at = ?, finished_at = ? WHERE id = ?",
      clean(body.branch, 160), clean(body.commit_sha, 80), testOutput, testOutput, now(), now(), row.id,
    );
    if (thread) {
      await addAgentMessage(env, thread, "agent", `Đã áp thay đổi trên máy trung tâm. Nhánh ${clean(body.branch, 160) || "(không rõ)"}, commit ${clean(body.commit_sha, 12) || "(không rõ)"}.`, { author: "agent", requestId: row.id });
    }
    await addAudit(env, `runner:${runnerKey}`, "code_request.applied", "code_request", row.id, row.dashboard_id, {
      branch: clean(body.branch, 160), commit: clean(body.commit_sha, 80), auto: Boolean(row.auto_applied),
    });
    return json({ ok: true });
  }

  // status === "awaiting_approval": runner đã có patch và đã chạy test.
  let scope;
  try { scope = JSON.parse(row.scope_json || "{}"); } catch { scope = {}; }
  scope.allow_globs = Array.isArray(scope.allow_globs) ? scope.allow_globs : [];
  const files = Array.isArray(body.files) ? body.files : [];
  const { paths, outside, protectedPaths } = auditChangedFiles(files, scope);
  const filesChanged = paths.length;

  // Diff lưu lại có thể bị cắt, còn số dòng thì do runner báo.  Nếu chỉ tin số
  // runner báo thì người duyệt có thể nhìn một diff cắt dở mà tưởng đã đọc hết,
  // và một runner báo thiếu sẽ lách được trần số dòng.  Lấy số lớn hơn giữa
  // "runner báo" và "đếm được trong chính diff người duyệt sẽ nhìn".
  const diffText = cleanBlock(body.diff_text);
  const diffTruncated = String(body.diff_text ?? "").length > diffText.length ? 1 : 0;
  const linesInDiff = countDiffLines(diffText);
  const linesReported = Math.max(0, Number.parseInt(body.lines_changed, 10) || 0);
  const linesChanged = Math.max(linesReported, linesInDiff);

  const violations = [];
  if (outside.length) violations.push(`ngoài phạm vi được cấp: ${outside.slice(0, 8).join(", ")}`);
  if (filesChanged > (Number(scope.max_files) || 0)) violations.push(`đổi ${filesChanged} file, vượt mức ${scope.max_files}`);
  if (linesChanged > (Number(scope.max_lines) || 0)) violations.push(`đổi ${linesChanged} dòng, vượt mức ${scope.max_lines}`);
  if (violations.length) {
    const detail = `Thay đổi bị chặn vì ${violations.join("; ")}. Không có file nào được ghi.`;
    await dbRun(
      env,
      "UPDATE code_change_requests SET status = 'failed', plan_summary = ?, files_json = ?, diff_text = ?, diff_truncated = ?, files_changed = ?, lines_changed = ?, test_output = ?, tests_passed = ?, error = ?, updated_at = ?, finished_at = ? WHERE id = ?",
      summary, JSON.stringify(paths), diffText, diffTruncated, filesChanged, linesChanged, testOutput, testsPassed, detail, now(), now(), row.id,
    );
    if (thread) await addAgentMessage(env, thread, "system", detail, { author: "system", requestId: row.id });
    await addAudit(env, `runner:${runnerKey}`, "code_request.out_of_scope", "code_request", row.id, row.dashboard_id, { outside, files_changed: filesChanged, lines_changed: linesChanged });
    return json({ ok: true, blocked: true, error: detail });
  }

  const touchesProtected = protectedPaths.length ? 1 : 0;
  const autoApply = Boolean(scope.auto_apply) && !touchesProtected && testsPassed === 1 && filesChanged > 0;
  const nextStatus = autoApply ? "approved" : "awaiting_approval";
  await dbRun(
    env,
    "UPDATE code_change_requests SET status = ?, plan_summary = ?, files_json = ?, diff_text = ?, diff_truncated = ?, files_changed = ?, lines_changed = ?, touches_protected = ?, test_output = ?, tests_passed = ?, branch = ?, auto_applied = ?, decided_by = CASE WHEN ? THEN 'auto' ELSE decided_by END, decided_at = CASE WHEN ? THEN ? ELSE decided_at END, updated_at = ? WHERE id = ?",
    nextStatus, summary, JSON.stringify(paths), diffText, diffTruncated, filesChanged, linesChanged,
    touchesProtected, testOutput, testsPassed, clean(body.branch, 160), autoApply ? 1 : 0,
    autoApply ? 1 : 0, autoApply ? 1 : 0, now(), now(), row.id,
  );
  if (thread) {
    const note = autoApply
      ? `${summary}\n\nNằm trong phạm vi được cấp và test đã xanh, nên thay đổi được áp thẳng.`
      : `${summary}\n\nĐổi ${filesChanged} file, ${linesChanged} dòng${touchesProtected ? " (có chạm file được bảo vệ — cần Owner duyệt)" : ""}. Đang chờ duyệt.`;
    await addAgentMessage(env, thread, "agent", note, { author: "agent", requestId: row.id });
  }
  await addAudit(env, `runner:${runnerKey}`, `code_request.${nextStatus}`, "code_request", row.id, row.dashboard_id, {
    files: paths, lines_changed: linesChanged, tests_passed: Boolean(testsPassed), protected: Boolean(touchesProtected),
  });
  return json({ ok: true, status: nextStatus, auto_applied: autoApply });
}

// ─── Agent trung tâm: đường lệnh có cấu trúc, thực thi trong Worker ──────────

async function runnerRunApprovals(env, runId, runnerKey) {
  const run = await dbFirst(env, "SELECT id, runner_key FROM bot_runs WHERE id = ?", runId);
  if (!run || run.runner_key !== runnerKey) return error("Không tìm thấy lần chạy của runner này.", 404);
  const approvals = await dbAll(
    env,
    "SELECT id, status, artifact_url, reviewed_by, reviewed_at FROM approvals WHERE run_id = ? ORDER BY created_at ASC",
    runId,
  );
  return json({ approvals });
}

// Dòng theo email thắng dòng theo vai trò: ngoại lệ cho một người phải mở (hoặc
// siết) được mà không đụng tới cả vai trò.  Không có dòng nào và không phải
// Owner thì không có phạm vi — đóng mặc định.
async function resolveControlScope(env, dashboard, user, role) {
  const rows = await dbAll(
    env,
    "SELECT subject_type, subject, allow_runner_keys, allow_actions, max_commands_per_day, allowed_hours, note FROM agent_control_scopes WHERE dashboard_id = ? AND ((subject_type = 'user' AND subject = ?) OR (subject_type = 'role' AND subject = ?))",
    dashboard.id, user.email, role,
  );
  const row = rows.find((item) => item.subject_type === "user") || rows.find((item) => item.subject_type === "role");
  // Owner có dòng riêng thì dùng dòng đó: cấp một phạm vi hẹp cho Owner phải
  // siết được thật, không bị mặc định "mọi bot" ghi đè lên.
  if (!row) return role === "owner" ? { ...OWNER_DEFAULT_CONTROL_SCOPE } : null;
  return normaliseControlScopeRow(row);
}

// Trần lệnh tính theo NGÀY GIỜ VN, không theo ngày UTC: người dùng ở đây hiểu
// "hôm nay" theo lịch của họ, và mốc UTC sẽ reset trần vào 07:00 sáng.
// Chỉ đếm lệnh đã thực thi — lệnh bị chặn không tiêu quota, nếu không thì một
// chuỗi lệnh sai của mô hình sẽ khoá luôn người dùng thật.
async function countControlCommandsToday(env, dashboard, email, atMillis) {
  const row = await dbFirst(
    env,
    "SELECT COUNT(*) AS value FROM agent_control_commands WHERE dashboard_id = ? AND requested_by = ? AND status = 'executed' AND created_at >= ?",
    dashboard.id, email, vietnamDayStartIso(atMillis),
  );
  return Number(row?.value || 0);
}

async function controlStatusSnapshot(env, bot, atMillis) {
  const [runner, activeRun, lastRun] = await Promise.all([
    bot.runner_key
      ? dbFirst(env, "SELECT runner_key, label, status, version, last_seen_at, last_error FROM runners WHERE runner_key = ?", bot.runner_key)
      : null,
    dbFirst(env, "SELECT id, status, title, created_at, started_at FROM bot_runs WHERE bot_id = ? AND status IN ('queued', 'running', 'cancel_requested') ORDER BY created_at DESC LIMIT 1", bot.id),
    dbFirst(env, "SELECT id, status, title, error, created_at, finished_at FROM bot_runs WHERE bot_id = ? AND status NOT IN ('queued', 'running', 'cancel_requested') ORDER BY created_at DESC LIMIT 1", bot.id),
  ]);
  return {
    bot: {
      id: bot.id, name: bot.name, runner_key: bot.runner_key,
      status: bot.status, last_run_status: bot.last_run_status, last_run_at: bot.last_run_at,
    },
    runner: runner ? { ...runner, online: runnerIsOnline(runner, atMillis) } : null,
    active_run: activeRun || null,
    last_finished_run: lastRun || null,
  };
}

// Ép một run mồ côi thành failed.  "Mồ côi" = runner của nó im lặng quá
// ORPHAN_AFTER_MS; runner còn sống thì đây là lệnh sai, không phải lệnh dọn
// dẹp — từ chối chứ không giết một run đang chạy thật.
async function recoverOrphanRun(env, dashboard, actorEmail, bot, atMillis) {
  const run = await dbFirst(
    env,
    "SELECT id, runner_key, status FROM bot_runs WHERE bot_id = ? AND status IN ('running', 'cancel_requested') ORDER BY created_at DESC LIMIT 1",
    bot.id,
  );
  if (!run) return { ok: false, status: 409, message: "Bot này không có run nào đang chạy để khôi phục." };
  const runner = await dbFirst(env, "SELECT status, last_seen_at FROM runners WHERE runner_key = ?", run.runner_key || bot.runner_key);
  const silentFor = runner?.last_seen_at ? atMillis - Date.parse(runner.last_seen_at) : Number.POSITIVE_INFINITY;
  if (silentFor < ORPHAN_AFTER_MS) {
    return { ok: false, status: 409, message: "Runner của run này vẫn còn báo sống. Hãy dùng lệnh dừng thay vì khôi phục." };
  }
  const reason = `Run mồ côi, khôi phục bởi ${actorEmail}`;
  // Có điều kiện trên status: nếu runner tỉnh lại và báo cáo xong ngay trước
  // câu này, kết quả thật của nó phải thắng, không bị ghi đè thành failed.
  const result = await dbRun(
    env,
    "UPDATE bot_runs SET status = 'failed', error = ?, finished_at = ?, updated_at = ? WHERE id = ? AND status IN ('running', 'cancel_requested')",
    reason, now(), now(), run.id,
  );
  if (!result?.meta?.changes) {
    return { ok: false, status: 409, message: "Run đã kết thúc trước khi lệnh khôi phục kịp chạy." };
  }
  await dbRun(env, "UPDATE bots SET status = 'error', last_run_status = 'failed', updated_at = ? WHERE id = ?", now(), bot.id);
  await addAudit(env, actorEmail, "bot.run_recovered", "bot_run", run.id, dashboard.id, {
    bot_id: bot.id, runner_key: run.runner_key || bot.runner_key, silent_ms: Number.isFinite(silentFor) ? Math.round(silentFor) : null,
  });
  return { ok: true, run: { id: run.id, status: "failed" }, message: `Đã đánh dấu run mồ côi là thất bại. ${reason}.` };
}

async function recordControlCommand(env, entry) {
  await dbRun(
    env,
    "INSERT INTO agent_control_commands (id, request_id, dashboard_id, seq, action, target_bot_id, target_runner_key, target_run_id, params_json, status, reject_reason, result_json, requested_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    entry.id, entry.requestId, entry.dashboardId, entry.seq, entry.action,
    entry.targetBotId || "", entry.targetRunnerKey || "", entry.targetRunId || "",
    JSON.stringify(entry.params || {}), entry.status, entry.rejectReason || "",
    JSON.stringify(entry.result || {}), entry.requestedBy, now(),
  );
}

// Chạy một chuỗi lệnh đã có phạm vi đóng băng.  Dừng ở lệnh đầu tiên bị từ
// chối: chạy tiếp những lệnh sau sẽ để lại một chuỗi nửa vời mà người đọc
// audit không đoán được hệ thống đang ở đâu.
//
// scope là scope ĐÃ ĐÓNG BĂNG (đọc từ scope_json), không tra lại bảng — đổi
// quyền giữa chừng không được nới rộng một yêu cầu đang chạy.
async function executeControlCommands(env, dashboard, requestRow, scope, commands, context) {
  const results = [];
  let commandsToday = context.commandsToday;
  let seq = 0;
  for (const raw of commands) {
    seq += 1;
    const action = clean(raw?.action, 20).toLowerCase();
    const botId = clean(raw?.bot_id, 120);
    const bot = botId
      ? await dbFirst(env, "SELECT * FROM bots WHERE id = ? AND dashboard_id = ?", botId, dashboard.id)
      : null;
    const verdict = validateControlCommand({ action, bot }, scope, {
      dashboardId: dashboard.id, canRecover: context.canRecover, commandsToday, at: context.at,
    });
    const entryBase = {
      id: id(), requestId: requestRow.id, dashboardId: dashboard.id, seq,
      action: CONTROL_ACTIONS.includes(action) ? action : "status",
      targetBotId: bot?.id || botId, targetRunnerKey: bot?.runner_key || "",
      params: sanitiseControlParams(action, raw?.params),
      requestedBy: context.actorEmail,
    };

    if (!verdict.ok) {
      await recordControlCommand(env, { ...entryBase, status: "rejected", rejectReason: verdict.reason });
      await addAudit(env, context.actorEmail, "agent_command.rejected", "agent_control_command", entryBase.id, dashboard.id, {
        request_id: requestRow.id, seq, action, bot_id: entryBase.targetBotId, code: verdict.code,
      });
      results.push({ seq, action, status: "rejected", code: verdict.code, message: verdict.reason });
      return { results, stoppedAt: seq, rejected: true };
    }

    let outcome;
    if (verdict.action === "status") {
      outcome = { ok: true, snapshot: await controlStatusSnapshot(env, bot, context.at), message: `Đã đọc trạng thái của "${bot.name}".` };
    } else if (verdict.action === "recover") {
      outcome = await recoverOrphanRun(env, dashboard, context.actorEmail, bot, context.at);
    } else {
      // start/stop đi đúng con đường của nút bấm, kể cả các guard 409 của nó.
      outcome = await runBotCommand(env, dashboard, context.actorEmail, bot.id, verdict.action === "start" ? "run" : "pause", entryBase.params);
    }

    if (!outcome.ok) {
      // Lệnh hợp quyền nhưng không chạy được (runner offline, bot đang bận…):
      // 'failed' chứ không phải 'rejected' — hai thứ này dẫn tới hai cách sửa
      // khác nhau, gộp lại thì người đọc audit đi sai đường.
      await recordControlCommand(env, { ...entryBase, status: "failed", rejectReason: outcome.message });
      await addAudit(env, context.actorEmail, "agent_command.failed", "agent_control_command", entryBase.id, dashboard.id, {
        request_id: requestRow.id, seq, action: verdict.action, bot_id: bot.id, runner_key: verdict.runnerKey,
      });
      results.push({ seq, action: verdict.action, status: "failed", message: outcome.message });
      return { results, stoppedAt: seq, rejected: false, failed: true };
    }

    commandsToday += 1;
    await recordControlCommand(env, {
      ...entryBase, status: "executed", targetRunId: outcome.run?.id || "",
      result: { message: outcome.message, run: outcome.run || null, snapshot: outcome.snapshot || null },
    });
    await addAudit(env, context.actorEmail, "agent_command.executed", "agent_control_command", entryBase.id, dashboard.id, {
      request_id: requestRow.id, seq, action: verdict.action, bot_id: bot.id,
      runner_key: verdict.runnerKey, run_id: outcome.run?.id || null,
    });
    results.push({
      seq, action: verdict.action, status: "executed", message: outcome.message,
      run: outcome.run || null, snapshot: outcome.snapshot || null,
    });
  }
  return { results, stoppedAt: seq, rejected: false };
}

// Chỉ giữ lại tham số mà lệnh đó thật sự dùng.  Nhận nguyên object của client
// (hoặc của mô hình) rồi chuyển thẳng xuống runBotCommand là cách để một khoá
// lạ đi vào chỗ không ai ngờ.
function sanitiseControlParams(action, params) {
  if (clean(action, 20).toLowerCase() !== "start") return {};
  const source = params && typeof params === "object" ? params : {};
  return {
    prompt: cleanText(source.prompt, 3000),
    aspect: clean(source.aspect || "landscape", 24).toLowerCase(),
    count: Math.max(1, Math.min(4, Number.parseInt(source.count, 10) || 1)),
    title: clean(source.title, 120),
  };
}

async function controlOverview(env, dashboard, role, user) {
  const scope = await resolveControlScope(env, dashboard, user, role);
  const atMillis = Date.now();
  const [bots, centralRunner, threads, requests, scopes] = await Promise.all([
    dbAll(env, "SELECT b.id, b.name, b.runner_key, b.status, b.last_run_status, r.status AS runner_status, r.last_seen_at AS runner_last_seen_at FROM bots b LEFT JOIN runners r ON r.runner_key = b.runner_key WHERE b.dashboard_id = ? ORDER BY b.created_at ASC", dashboard.id),
    dbFirst(env, "SELECT runner_key, label, status, version, last_seen_at, last_error FROM runners WHERE runner_key = ?", AGENT_CONTROL_RUNNER_KEY),
    dbAll(env, "SELECT id, title, created_by, status, created_at, updated_at FROM agent_threads WHERE dashboard_id = ? ORDER BY updated_at DESC LIMIT 30", dashboard.id),
    dbAll(env, "SELECT id, thread_id, requested_by, requested_role, instruction, scope_json, status, plan_summary, error, created_at, finished_at FROM agent_control_requests WHERE dashboard_id = ? ORDER BY created_at DESC LIMIT 20", dashboard.id),
    capability(role, "manage_members")
      ? dbAll(env, "SELECT id, subject_type, subject, allow_runner_keys, allow_actions, max_commands_per_day, allowed_hours, note, updated_by, updated_at FROM agent_control_scopes WHERE dashboard_id = ? ORDER BY subject_type, subject", dashboard.id)
      : [],
  ]);
  const commands = requests.length
    ? await dbAll(
      env,
      `SELECT id, request_id, seq, action, target_bot_id, target_runner_key, target_run_id, status, reject_reason, requested_by, created_at FROM agent_control_commands WHERE request_id IN (${requests.map(() => "?").join(", ")}) ORDER BY created_at DESC, seq ASC`,
      ...requests.map((row) => row.id),
    )
    : [];
  return {
    // Ai cũng xem được trạng thái (view là đủ); chỉ người có phạm vi mới gửi
    // được lệnh.  UI dựa vào can_control để không mời người ta bấm nút hỏng.
    can_control: capability(role, "agent_control") && Boolean(scope),
    can_recover: capability(role, "agent_recover"),
    can_manage_scopes: capability(role, "manage_members"),
    scope: scope ? { ...scope, protected_runner_keys: PROTECTED_RUNNER_KEYS } : null,
    control_actions: CONTROL_ACTIONS,
    protected_runner_keys: PROTECTED_RUNNER_KEYS,
    commands_today: capability(role, "agent_control") ? await countControlCommandsToday(env, dashboard, user.email, atMillis) : 0,
    // Runner trung tâm chết không làm hỏng đường B; UI phải nói rõ điều đó thay
    // vì để người dùng đoán vì sao chat im mà nút bấm vẫn chạy.
    central_runner: centralRunner ? { ...centralRunner, online: runnerIsOnline(centralRunner, atMillis) } : null,
    bots: bots.map((bot) => ({
      id: bot.id, name: bot.name, runner_key: bot.runner_key, status: bot.status,
      last_run_status: bot.last_run_status,
      runner_online: runnerIsOnline({ status: bot.runner_status, last_seen_at: bot.runner_last_seen_at }, atMillis),
      protected: isProtectedRunnerKey(bot.runner_key),
      controllable: Boolean(scope) && !isProtectedRunnerKey(bot.runner_key)
        && (scope.any_runner_key || scope.allow_runner_keys.includes(bot.runner_key)),
    })),
    threads,
    // frozen_scope là phạm vi đã đóng băng lúc xếp yêu cầu.  Hiện nó ra để
    // người đọc lịch sử thấy yêu cầu cũ chạy dưới quyền nào, chứ không phải
    // quyền hiện tại của người gửi — hai thứ đó có thể đã khác nhau.
    requests: requests.map(({ scope_json, ...row }) => ({
      ...row,
      frozen_scope: safeJson(scope_json, null),
    })),
    commands,
    scopes,
  };
}

async function postControlCommands(request, env, user, slug) {
  const { dashboard, role } = await requireDashboard(env, slug, user, "agent_control");
  const body = await readJson(request);
  const scope = await resolveControlScope(env, dashboard, user, role);
  if (!scope) {
    return error("Bạn chưa được cấp phạm vi điều khiển agent trong dashboard này. Hãy nhờ Owner/Admin cấp trong mục Agent trung tâm.", 403);
  }
  const rawCommands = Array.isArray(body.commands) ? body.commands : [];
  if (!rawCommands.length) return error("Cần ít nhất một lệnh điều khiển.");
  if (rawCommands.length > 10) return error("Tối đa 10 lệnh trong một yêu cầu.");

  const atMillis = Date.now();
  const instruction = cleanText(body.instruction, 2000)
    || rawCommands.map((item) => `${clean(item?.action, 20)} ${clean(item?.bot_id, 120)}`).join("; ").slice(0, 2000);
  const requestRow = { id: id() };
  await dbRun(
    env,
    "INSERT INTO agent_control_requests (id, dashboard_id, thread_id, runner_key, requested_by, requested_role, instruction, scope_json, status, created_at, updated_at, started_at) VALUES (?, ?, '', ?, ?, ?, ?, ?, 'executing', ?, ?, ?)",
    requestRow.id, dashboard.id, AGENT_CONTROL_RUNNER_KEY, user.email, role, instruction,
    JSON.stringify(scope), now(), now(), now(),
  );
  await addAudit(env, user.email, "agent_control_request.queued", "agent_control_request", requestRow.id, dashboard.id, {
    path: "button", commands: rawCommands.length, scope_source: scope.source,
  });

  const outcome = await executeControlCommands(env, dashboard, requestRow, scope, rawCommands, {
    actorEmail: user.email,
    canRecover: capability(role, "agent_recover"),
    commandsToday: await countControlCommandsToday(env, dashboard, user.email, atMillis),
    at: atMillis,
  });
  const status = outcome.rejected ? "rejected" : outcome.failed ? "failed" : "completed";
  const firstProblem = outcome.results.find((item) => item.status !== "executed");
  await dbRun(
    env,
    "UPDATE agent_control_requests SET status = ?, plan_summary = ?, error = ?, updated_at = ?, finished_at = ? WHERE id = ?",
    status,
    `${outcome.results.filter((item) => item.status === "executed").length}/${rawCommands.length} lệnh đã chạy.`,
    firstProblem?.message || "", now(), now(), requestRow.id,
  );
  // Một lệnh bị chặn là kết quả bình thường của hệ thống phân quyền, không phải
  // lỗi HTTP: 200 kèm chi tiết từng lệnh để UI hiện đúng lệnh nào hỏng vì sao.
  return json({ ok: !outcome.rejected && !outcome.failed, request_id: requestRow.id, status, results: outcome.results });
}

async function saveControlScope(request, env, user, slug) {
  const { dashboard } = await requireDashboard(env, slug, user, "manage_members");
  const body = await readJson(request);
  const subjectType = clean(body.subject_type, 10).toLowerCase();
  if (!["role", "user"].includes(subjectType)) return error("Loại đối tượng phải là role hoặc user.");
  const domain = clean(env.COMPANY_EMAIL_DOMAIN || "havigroup.llc", 120).toLowerCase();
  const subject = subjectType === "role" ? clean(body.subject, 20).toLowerCase() : clean(body.subject, 254).toLowerCase();
  if (subjectType === "role" && !["admin", "operator", "reviewer", "viewer"].includes(subject)) {
    return error("Vai trò không hợp lệ.");
  }
  if (subjectType === "user" && !subject.endsWith(`@${domain}`)) return error("Email phải thuộc công ty.");
  // Cấp quyền cho vai trò vốn không có capability agent_control là cấp một
  // phạm vi không bao giờ dùng được; nói thẳng thay vì để nó nằm im trong bảng
  // rồi ai đó tưởng đã cấp xong.
  if (subjectType === "role" && !capability(subject, "agent_control")) {
    return error(`Vai trò "${subject}" không có quyền điều khiển agent, cấp phạm vi cũng không dùng được.`);
  }

  const runnerKeys = parseRunnerKeyList(body.allow_runner_keys);
  const actions = parseActionList(body.allow_actions);
  const blocked = runnerKeys.filter(isProtectedRunnerKey);
  if (blocked.length) {
    return error(`Không cấp được phạm vi cho runner được bảo vệ: ${blocked.join(", ")}.`, 403);
  }
  const allowedHours = clean(body.allowed_hours, 12);
  if (parseAllowedHours(allowedHours).kind === "invalid") {
    return error("Khung giờ phải có dạng HH-HH (ví dụ 08-18), hoặc để trống nếu cho mọi giờ.");
  }
  // Danh sách rỗng là cách gỡ quyền: xoá hẳn dòng thay vì để lại một allowlist
  // trống mà người đọc bảng dễ tưởng là "cho tất cả".
  if (!runnerKeys.length || !actions.length) {
    await dbRun(env, "DELETE FROM agent_control_scopes WHERE dashboard_id = ? AND subject_type = ? AND subject = ?", dashboard.id, subjectType, subject);
    await addAudit(env, user.email, "agent_control_scope.revoked", "agent_control_scope", `${subjectType}:${subject}`, dashboard.id, {});
    return json({ ok: true, removed: true });
  }
  const maxPerDay = Math.max(1, Math.min(200, Number.parseInt(body.max_commands_per_day, 10) || 20));
  await dbRun(
    env,
    "INSERT INTO agent_control_scopes (id, dashboard_id, subject_type, subject, allow_runner_keys, allow_actions, max_commands_per_day, allowed_hours, note, updated_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(dashboard_id, subject_type, subject) DO UPDATE SET allow_runner_keys = excluded.allow_runner_keys, allow_actions = excluded.allow_actions, max_commands_per_day = excluded.max_commands_per_day, allowed_hours = excluded.allowed_hours, note = excluded.note, updated_by = excluded.updated_by, updated_at = excluded.updated_at",
    id(), dashboard.id, subjectType, subject, runnerKeys.join("\n"), actions.join(","),
    maxPerDay, allowedHours, clean(body.note, 420), user.email, now(), now(),
  );
  await addAudit(env, user.email, "agent_control_scope.updated", "agent_control_scope", `${subjectType}:${subject}`, dashboard.id, {
    runner_keys: runnerKeys.length, actions, max_commands_per_day: maxPerDay, allowed_hours: allowedHours,
  });
  return json({ ok: true });
}

// ─── Agent trung tâm: đường A (chat tiếng Việt → runner trung tâm) ───────────
//
// Khác đường B đúng một chỗ: ai sinh ra danh sách lệnh.  Người dùng nhắn tiếng
// Việt, runner trung tâm hỏi mô hình, mô hình đề xuất lệnh — rồi lệnh đi qua
// CHÍNH executeControlCommands với CHÍNH scope đã đóng băng lúc xếp yêu cầu.
// Không có đường tắt nào cho runner: nó không được cấp quyền nào hơn người gửi.

// Mỗi tin nhắn của người dùng sinh đúng một yêu cầu điều khiển.  Phạm vi đóng
// băng ngay tại đây — mô hình chạy sau đó vài giây hay vài phút cũng chỉ được
// dùng phạm vi của lúc gửi.
// Xem codeRequestGate: cùng lý do, cùng thứ tự — kiểm trước, ghi luồng sau.
async function controlRequestGate(env, dashboard, user, role) {
  const scope = await resolveControlScope(env, dashboard, user, role);
  if (!scope) {
    throw new Response("Bạn chưa được cấp phạm vi điều khiển agent trong dashboard này. Hãy nhờ Owner/Admin cấp trong mục Agent trung tâm.", { status: 403 });
  }
  const runner = await dbFirst(env, "SELECT status, last_seen_at FROM runners WHERE runner_key = ?", AGENT_CONTROL_RUNNER_KEY);
  // Runner trung tâm chết thì đường chat không có ai xử lý.  Nói ngay thay vì
  // xếp một yêu cầu nằm im mãi — nút start/stop/status (đường B) vẫn chạy được.
  if (!runnerIsOnline(runner)) {
    throw new Response("Agent trung tâm chưa kết nối nên chưa nhắn được. Các nút chạy/dừng/xem trạng thái vẫn dùng bình thường.", { status: 409 });
  }
  return scope;
}

async function queueControlRequest(env, dashboard, user, role, thread, instruction, gated = null) {
  const scope = gated || await controlRequestGate(env, dashboard, user, role);
  const requestId = id();
  await addAgentMessage(env, thread, "user", instruction, { author: user.email, requestId });
  await dbRun(
    env,
    "INSERT INTO agent_control_requests (id, dashboard_id, thread_id, runner_key, requested_by, requested_role, instruction, scope_json, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?)",
    requestId, dashboard.id, thread.id, AGENT_CONTROL_RUNNER_KEY, user.email, role,
    cleanBlock(instruction, 6000), JSON.stringify(scope), now(), now(),
  );
  await addAudit(env, user.email, "agent_control_request.queued", "agent_control_request", requestId, dashboard.id, {
    path: "chat", thread_id: thread.id, role, scope_source: scope.source,
  });
  return { requestId, scope };
}

async function createControlThread(request, env, user, slug) {
  const { dashboard, role } = await requireDashboard(env, slug, user, "agent_control");
  const body = await readJson(request);
  const instruction = cleanBlock(body.message, 6000).trim();
  if (instruction.length < 8) return error("Hãy mô tả yêu cầu rõ hơn (ít nhất 8 ký tự).");
  const gated = await controlRequestGate(env, dashboard, user, role);
  const thread = { id: id(), dashboard_id: dashboard.id };
  await dbRun(
    env,
    "INSERT INTO agent_threads (id, dashboard_id, title, created_by, status, created_at, updated_at) VALUES (?, ?, ?, ?, 'open', ?, ?)",
    thread.id, dashboard.id, clean(body.title || instruction, 120), user.email, now(), now(),
  );
  const { requestId } = await queueControlRequest(env, dashboard, user, role, thread, instruction, gated);
  return json({ thread_id: thread.id, request_id: requestId }, 201);
}

async function postControlMessage(request, env, user, slug, threadId) {
  const { dashboard, role } = await requireDashboard(env, slug, user, "agent_control");
  const thread = await dbFirst(env, "SELECT * FROM agent_threads WHERE id = ? AND dashboard_id = ?", threadId, dashboard.id);
  if (!thread) return error("Không tìm thấy luồng trao đổi.", 404);
  if (thread.status !== "open") return error("Luồng này đã đóng.", 409);
  const body = await readJson(request);
  const instruction = cleanBlock(body.message, 6000).trim();
  if (instruction.length < 8) return error("Hãy mô tả yêu cầu rõ hơn (ít nhất 8 ký tự).");
  // Một luồng chỉ có một yêu cầu đang chạy: hai yêu cầu song song trong cùng
  // một luồng sẽ đọc cùng một lịch sử chat và có thể ra hai chuỗi lệnh mâu thuẫn.
  const pending = await dbFirst(
    env,
    "SELECT id FROM agent_control_requests WHERE thread_id = ? AND status IN ('queued', 'planning', 'executing') LIMIT 1",
    thread.id,
  );
  if (pending) return error("Agent trung tâm đang xử lý yêu cầu trước trong luồng này. Hãy chờ nó trả lời.", 409);
  const { requestId } = await queueControlRequest(env, dashboard, user, role, thread, instruction);
  return json({ request_id: requestId }, 201);
}

async function controlThreadDetail(env, dashboard, threadId) {
  const thread = await dbFirst(env, "SELECT * FROM agent_threads WHERE id = ? AND dashboard_id = ?", threadId, dashboard.id);
  if (!thread) throw new Response("Không tìm thấy luồng trao đổi.", { status: 404 });
  const [messages, requests] = await Promise.all([
    dbAll(env, "SELECT id, kind, author_email, content, request_id, created_at FROM agent_messages WHERE thread_id = ? ORDER BY created_at ASC LIMIT 200", thread.id),
    dbAll(env, "SELECT id, requested_by, requested_role, instruction, status, plan_summary, error, created_at, finished_at FROM agent_control_requests WHERE thread_id = ? ORDER BY created_at ASC LIMIT 50", thread.id),
  ]);
  const commands = requests.length
    ? await dbAll(
      env,
      `SELECT id, request_id, seq, action, target_bot_id, target_runner_key, target_run_id, status, reject_reason, created_at FROM agent_control_commands WHERE request_id IN (${requests.map(() => "?").join(", ")}) ORDER BY seq ASC`,
      ...requests.map((row) => row.id),
    )
    : [];
  return { thread, messages, requests, commands };
}

// Rút lại yêu cầu khi runner chưa đụng tới (hoặc mới đang hỏi mô hình).  Đang
// executing thì không rút: lệnh có thể đã chạy một nửa, và một "cancelled" ghi
// đè lên đó sẽ nói dối về những gì đã xảy ra.
async function cancelControlRequest(request, env, user, slug, requestId) {
  const { dashboard, role } = await requireDashboard(env, slug, user);
  const row = await dbFirst(env, "SELECT * FROM agent_control_requests WHERE id = ? AND dashboard_id = ?", requestId, dashboard.id);
  if (!row) return error("Không tìm thấy yêu cầu điều khiển.", 404);
  if (row.requested_by !== user.email && !capability(role, "agent_control")) {
    return error("Chỉ người gửi hoặc người có quyền điều khiển agent mới rút được yêu cầu.", 403);
  }
  const result = await dbRun(
    env,
    "UPDATE agent_control_requests SET status = 'cancelled', decided_by = ?, updated_at = ?, finished_at = ? WHERE id = ? AND status IN ('queued', 'planning')",
    user.email, now(), now(), row.id,
  );
  if (!result?.meta?.changes) return error(`Yêu cầu đang ở trạng thái "${row.status}" nên không rút lại được.`, 409);
  const thread = row.thread_id ? await dbFirst(env, "SELECT * FROM agent_threads WHERE id = ?", row.thread_id) : null;
  if (thread) await addAgentMessage(env, thread, "system", `${user.email} đã rút lại yêu cầu này.`, { author: "system", requestId: row.id });
  await addAudit(env, user.email, "agent_control_request.cancelled", "agent_control_request", row.id, dashboard.id, {});
  return json({ ok: true, status: "cancelled" });
}

// ─── Agent trung tâm · phía runner ──────────────────────────────────────────

async function runnerClaimControlRequest(request, env) {
  const body = await readJson(request);
  const runnerKey = clean(body.runner_key, 120);
  if (!runnerKey) return error("Runner key là bắt buộc.");
  const runner = await dbFirst(env, "SELECT runner_key, status FROM runners WHERE runner_key = ?", runnerKey);
  if (!runner || runner.status !== "online") return error("Runner chưa heartbeat hoặc đang offline.", 409);
  const queued = await dbFirst(
    env,
    "SELECT * FROM agent_control_requests WHERE runner_key = ? AND status = 'queued' ORDER BY created_at ASC LIMIT 1",
    runnerKey,
  );
  if (!queued) return json({ request: null });
  const claimed = await dbRun(
    env,
    "UPDATE agent_control_requests SET status = 'planning', started_at = ?, updated_at = ? WHERE id = ? AND status = 'queued'",
    now(), now(), queued.id,
  );
  // Hai runner cùng key cùng claim: bên thua thấy changes = 0 và không nhận việc.
  if (!claimed?.meta?.changes) return json({ request: null });

  const scope = safeJson(queued.scope_json, {}) || {};
  const atMillis = Date.now();
  const [history, bots] = await Promise.all([
    queued.thread_id
      ? dbAll(env, "SELECT kind, author_email, content, created_at FROM agent_messages WHERE thread_id = ? ORDER BY created_at ASC LIMIT 40", queued.thread_id)
      : [],
    dbAll(env, "SELECT b.id, b.name, b.purpose, b.status, b.runner_key, r.status AS runner_status, r.last_seen_at AS runner_last_seen_at FROM bots b LEFT JOIN runners r ON r.runner_key = b.runner_key WHERE b.dashboard_id = ? ORDER BY b.name ASC", queued.dashboard_id),
  ]);
  // Mô hình chỉ nhìn thấy bot mà người gửi thật sự điều khiển được.  Không thấy
  // thì không gọi tên được — và kể cả nó bịa ra một bot_id, Worker vẫn kiểm lại
  // từng lệnh bằng đúng validateControlCommand mà nút bấm đi qua.
  const visible = bots.filter((bot) => !isProtectedRunnerKey(bot.runner_key)
    && (scope.any_runner_key || (scope.allow_runner_keys || []).includes(bot.runner_key)));
  return json({
    request: {
      id: queued.id,
      thread_id: queued.thread_id,
      instruction: queued.instruction,
      requested_by: queued.requested_by,
      requested_role: queued.requested_role,
      scope,
      control_actions: CONTROL_ACTIONS,
      protected_runner_keys: PROTECTED_RUNNER_KEYS,
      bots: visible.map((bot) => ({
        id: bot.id, name: bot.name, purpose: bot.purpose, status: bot.status,
        runner_key: bot.runner_key,
        runner_online: runnerIsOnline({ status: bot.runner_status, last_seen_at: bot.runner_last_seen_at }, atMillis),
      })),
      history,
    },
  });
}

async function runnerControlRequestStatus(env, requestId, runnerKey) {
  const row = await dbFirst(env, "SELECT id, status, runner_key FROM agent_control_requests WHERE id = ?", requestId);
  if (!row || row.runner_key !== runnerKey) return error("Không tìm thấy yêu cầu của runner này.", 404);
  return json({ request: { id: row.id, status: row.status } });
}

// Runner báo kết quả.  Với status "commands" đây là chỗ danh sách lệnh do mô
// hình đề xuất gặp lớp phân quyền: Worker không tin lời runner về việc lệnh nằm
// trong phạm vi, nó tự kiểm lại bằng scope đã đóng băng trong chính dòng này.
async function runnerUpdateControlRequest(request, env, requestId) {
  const body = await readJson(request);
  const runnerKey = clean(body.runner_key, 120);
  const status = clean(body.status, 32).toLowerCase();
  if (!runnerKey || !["planning", "answered", "commands", "failed"].includes(status)) {
    return error("Cập nhật yêu cầu điều khiển không hợp lệ.");
  }
  const row = await dbFirst(env, "SELECT * FROM agent_control_requests WHERE id = ? AND runner_key = ?", requestId, runnerKey);
  if (!row) return error("Không tìm thấy yêu cầu của runner này.", 404);
  // Trạng thái cuối là bất biến: báo cáo đến muộn (runner tỉnh lại sau khi
  // người gửi đã rút yêu cầu) bị bỏ qua chứ không ghi đè.
  if (["completed", "answered", "failed", "rejected", "cancelled"].includes(row.status)) {
    return json({ ok: true, idempotent: true, status: row.status });
  }
  const thread = row.thread_id ? await dbFirst(env, "SELECT * FROM agent_threads WHERE id = ?", row.thread_id) : null;
  const summary = cleanBlock(body.plan_summary, 4000);

  if (status === "planning") {
    await dbRun(env, "UPDATE agent_control_requests SET status = 'planning', updated_at = ? WHERE id = ?", now(), row.id);
    return json({ ok: true });
  }

  if (status === "failed") {
    const detail = cleanBlock(body.error, 2000) || "Agent trung tâm không hoàn thành được yêu cầu.";
    await dbRun(
      env,
      "UPDATE agent_control_requests SET status = 'failed', plan_summary = ?, error = ?, updated_at = ?, finished_at = ? WHERE id = ?",
      summary, detail, now(), now(), row.id,
    );
    if (thread) await addAgentMessage(env, thread, "agent", `Không thực hiện được: ${detail}`, { author: "agent", requestId: row.id });
    await addAudit(env, `runner:${runnerKey}`, "agent_control_request.failed", "agent_control_request", row.id, row.dashboard_id, {});
    return json({ ok: true });
  }

  if (status === "answered") {
    await dbRun(
      env,
      "UPDATE agent_control_requests SET status = 'answered', plan_summary = ?, updated_at = ?, finished_at = ? WHERE id = ?",
      summary, now(), now(), row.id,
    );
    if (thread) await addAgentMessage(env, thread, "agent", summary || "(agent không trả lời gì)", { author: "agent", requestId: row.id });
    return json({ ok: true });
  }

  // status === "commands": mô hình đã chốt một chuỗi lệnh.
  const commands = Array.isArray(body.commands) ? body.commands.slice(0, 10) : [];
  if (!commands.length) {
    const detail = "Agent nói sẽ điều khiển bot nhưng không đưa ra lệnh nào.";
    await dbRun(
      env,
      "UPDATE agent_control_requests SET status = 'failed', plan_summary = ?, error = ?, updated_at = ?, finished_at = ? WHERE id = ?",
      summary, detail, now(), now(), row.id,
    );
    if (thread) await addAgentMessage(env, thread, "system", detail, { author: "system", requestId: row.id });
    return json({ ok: false, error: detail });
  }
  // Quyền lấy từ VAI TRÒ ĐÃ ĐÓNG BĂNG của người gửi, không phải quyền của
  // runner: runner chỉ là đường ống, nó không tự có quyền điều khiển bot nào.
  if (!capability(row.requested_role, "agent_control")) {
    const detail = "Người gửi yêu cầu không có quyền điều khiển agent.";
    await dbRun(
      env,
      "UPDATE agent_control_requests SET status = 'rejected', plan_summary = ?, error = ?, updated_at = ?, finished_at = ? WHERE id = ?",
      summary, detail, now(), now(), row.id,
    );
    if (thread) await addAgentMessage(env, thread, "system", detail, { author: "system", requestId: row.id });
    return json({ ok: false, blocked: true, error: detail });
  }
  const dashboard = await dbFirst(env, "SELECT * FROM dashboards WHERE id = ?", row.dashboard_id);
  if (!dashboard) return error("Không tìm thấy dashboard của yêu cầu.", 404);
  const scope = normaliseFrozenScope(safeJson(row.scope_json, null));
  if (!scope) {
    const detail = "Yêu cầu không kèm phạm vi hợp lệ nên không lệnh nào được chạy.";
    await dbRun(
      env,
      "UPDATE agent_control_requests SET status = 'rejected', plan_summary = ?, error = ?, updated_at = ?, finished_at = ? WHERE id = ?",
      summary, detail, now(), now(), row.id,
    );
    if (thread) await addAgentMessage(env, thread, "system", detail, { author: "system", requestId: row.id });
    return json({ ok: false, blocked: true, error: detail });
  }

  await dbRun(env, "UPDATE agent_control_requests SET status = 'executing', updated_at = ? WHERE id = ?", now(), row.id);
  const atMillis = Date.now();
  const outcome = await executeControlCommands(env, dashboard, row, scope, commands, {
    actorEmail: row.requested_by,
    canRecover: capability(row.requested_role, "agent_recover"),
    commandsToday: await countControlCommandsToday(env, dashboard, row.requested_by, atMillis),
    at: atMillis,
  });
  const finalStatus = outcome.rejected ? "rejected" : outcome.failed ? "failed" : "completed";
  const firstProblem = outcome.results.find((item) => item.status !== "executed");
  await dbRun(
    env,
    "UPDATE agent_control_requests SET status = ?, plan_summary = ?, error = ?, updated_at = ?, finished_at = ? WHERE id = ?",
    finalStatus, summary,
    firstProblem?.message || "", now(), now(), row.id,
  );
  if (thread) {
    const lines = outcome.results.map((item) => `${item.status === "executed" ? "✓" : "✗"} ${item.action}: ${item.message}`);
    if (firstProblem) lines.push(`Chuỗi lệnh dừng ở lệnh ${firstProblem.seq}.`);
    await addAgentMessage(env, thread, "agent", [summary, ...lines].filter(Boolean).join("\n"), { author: "agent", requestId: row.id });
  }
  await addAudit(env, `agent:${row.requested_by}`, `agent_control_request.${finalStatus}`, "agent_control_request", row.id, row.dashboard_id, {
    path: "chat", commands: outcome.results.length,
  });
  return json({ ok: finalStatus === "completed", status: finalStatus, results: outcome.results });
}

async function handleApi(request, env) {
  const identity = identityFromRequest(request, env);
  if (!identity) {
    return error("Cần đăng nhập bằng tài khoản @havigroup.llc qua Cloudflare Access.", 401);
  }
  let user;
  try {
    user = await ensureUser(env, identity);
  } catch {
    return error("Cơ sở dữ liệu Automation Center chưa sẵn sàng. Hãy chạy D1 migration trước khi mở ứng dụng.", 503);
  }
  if (!user.active) return error("Tài khoản của bạn đã bị vô hiệu hóa.", 403);

  const { pathname } = new URL(request.url);
  const segments = pathname.split("/").filter(Boolean);
  try {
    if (request.method === "GET" && pathname === "/api/bootstrap") return json(await bootstrap(env, user));
    if (request.method === "GET" && pathname === "/api/health") return json(await healthOverview(env));
    if (request.method === "POST" && pathname === "/api/dashboards") return await createDashboard(request, env, user);
    if (segments[1] === "dashboards" && segments[2]) {
      const slug = decodeURIComponent(segments[2]);
      if (request.method === "GET" && segments.length === 3) {
        const { dashboard, role } = await requireDashboard(env, slug, user);
        return json(await dashboardDetail(env, dashboard, role, user));
      }
      if (request.method === "POST" && segments[3] === "members" && segments.length === 4) {
        return await grantMember(request, env, user, slug);
      }
      if (request.method === "POST" && segments[3] === "bots" && segments.length === 4) {
        return await createBot(request, env, user, slug);
      }
      if (request.method === "POST" && segments[3] === "bots" && segments[4] && segments[5] === "action") {
        return await botAction(request, env, user, slug, decodeURIComponent(segments[4]));
      }
      if (request.method === "POST" && segments[3] === "approvals" && segments[4]) {
        return await reviewApproval(request, env, user, slug, decodeURIComponent(segments[4]));
      }
      if (segments[3] === "agent") {
        if (request.method === "GET" && segments.length === 4) {
          const { dashboard, role } = await requireDashboard(env, slug, user);
          return json(await agentOverview(env, dashboard, role, user));
        }
        if (request.method === "GET" && segments[4] === "threads" && segments[5]) {
          const { dashboard } = await requireDashboard(env, slug, user);
          return json(await agentThreadDetail(env, dashboard, decodeURIComponent(segments[5])));
        }
        if (request.method === "POST" && segments[4] === "threads" && segments.length === 5) {
          return await createAgentThread(request, env, user, slug);
        }
        if (request.method === "POST" && segments[4] === "threads" && segments[5] && segments[6] === "messages") {
          return await postAgentMessage(request, env, user, slug, decodeURIComponent(segments[5]));
        }
        if (request.method === "GET" && segments[4] === "requests" && segments[5] && segments[6] === "diff") {
          const { dashboard } = await requireDashboard(env, slug, user);
          return json(await agentRequestDiff(env, dashboard, decodeURIComponent(segments[5])));
        }
        if (request.method === "POST" && segments[4] === "requests" && segments[5] && segments.length === 6) {
          return await decideCodeRequest(request, env, user, slug, decodeURIComponent(segments[5]));
        }
        if (request.method === "POST" && segments[4] === "scopes" && segments.length === 5) {
          return await saveCodeScope(request, env, user, slug);
        }
      }
      // Xem trạng thái agent trung tâm chỉ cần "view": người không điều khiển
      // được vẫn phải biết bot nào đang chạy, ai vừa gửi lệnh gì.
      if (request.method === "GET" && segments[3] === "control" && segments.length === 4) {
        const { dashboard, role } = await requireDashboard(env, slug, user);
        return json(await controlOverview(env, dashboard, role, user));
      }
      if (request.method === "POST" && segments[3] === "control" && segments[4] === "commands" && segments.length === 5) {
        return await postControlCommands(request, env, user, slug);
      }
      if (request.method === "POST" && segments[3] === "control" && segments[4] === "scopes" && segments.length === 5) {
        return await saveControlScope(request, env, user, slug);
      }
      if (segments[3] === "control" && segments[4] === "threads") {
        if (request.method === "POST" && segments.length === 5) {
          return await createControlThread(request, env, user, slug);
        }
        const threadId = segments[5] ? decodeURIComponent(segments[5]) : "";
        if (request.method === "GET" && segments.length === 6) {
          const { dashboard } = await requireDashboard(env, slug, user);
          return json(await controlThreadDetail(env, dashboard, threadId));
        }
        if (request.method === "POST" && segments[6] === "messages" && segments.length === 7) {
          return await postControlMessage(request, env, user, slug, threadId);
        }
      }
      if (request.method === "POST" && segments[3] === "control" && segments[4] === "requests"
          && segments[5] && segments[6] === "cancel" && segments.length === 7) {
        return await cancelControlRequest(request, env, user, slug, decodeURIComponent(segments[5]));
      }
    }
    return error("Không tìm thấy API.", 404);
  } catch (caught) {
    if (caught instanceof Response) return error(await caught.text(), caught.status);
    if (caught instanceof Error) return error(caught.message, 400);
    return error("Không thể xử lý yêu cầu.", 500);
  }
}

// Hằng số kiểu nguyên thuỷ gom vào một object trước khi xuất.  workerd coi MỌI
// named export của module entrypoint là một service entrypoint và chỉ nhận
// function hoặc object; "export const ORPHAN_AFTER_MS = 300000" làm
// `wrangler dev` chết ngay lúc khởi động với "Incorrect type for map entry".
// Object và mảng thì đi qua được, nên phần còn lại xuất thẳng.
const CONTROL_LIMITS = {
  AGENT_CONTROL_RUNNER_KEY,
  ORPHAN_AFTER_MS,
  RUNNER_ONLINE_WITHIN_MS,
  VN_OFFSET_MS,
};

// Xuất ra cho ba bộ test trong tests/.  Đây là phần quyết định ai được chạm vào
// cái gì, nên nó phải kiểm được ngoài môi trường Worker.
export {
  ROLE_CAPABILITIES, PROTECTED_GLOBS, OWNER_DEFAULT_SCOPE,
  capability, permissionsFor, normaliseRepoPath, globToRegExp, matchesAnyGlob,
  isProtectedPath, parseGlobList, auditChangedFiles, countDiffLines, cleanBlock,
  healthThresholds,
  staleRunners, orphanRuns, accessTokenIncident, describeStaleRunner, alertText,
  runHealthChecks, healthOverview,
  CONTROL_ACTIONS, PROTECTED_RUNNER_KEYS, OWNER_DEFAULT_CONTROL_SCOPE, CONTROL_LIMITS,
  isProtectedRunnerKey, parseRunnerKeyList, parseActionList,
  normaliseControlScopeRow, normaliseFrozenScope, validateControlCommand,
  sanitiseControlParams, runnerIsOnline,
  codeRequestGate, controlRequestGate, createAgentThread, createControlThread,
  parseAllowedHours, isWithinAllowedHours, vietnamHour, vietnamDayStartIso,
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.startsWith("/api/runner/")) return securityHeaders(await handleRunnerApi(request, env));
    if (url.pathname.startsWith("/api/")) return securityHeaders(await handleApi(request, env));
    const response = await env.ASSETS.fetch(request);
    return securityHeaders(response);
  },

  // Cron mỗi 5 phút.  Một lần chạy hỏng không được phép làm chết lịch, nên lỗi
  // được nuốt và ghi log thay vì ném ra ngoài.
  async scheduled(event, env, ctx) {
    ctx.waitUntil(
      runHealthChecks(env)
        .then((report) => {
          if (report.opened) console.log("watchdog:", JSON.stringify(report));
        })
        .catch((caught) => {
          console.error("watchdog thất bại:", caught instanceof Error ? caught.message : caught);
        }),
    );
  },
};
