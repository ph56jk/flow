const app = document.querySelector("#app");
const modal = document.querySelector("#modal");
const toast = document.querySelector("#toast");

const state = {
  data: null, detail: null, selected: "", screen: "programs", tab: "overview",
  preview: new URLSearchParams(location.search).has("preview"),
  // Màn hình Agent điều phối giữ state riêng: overview (luồng + yêu cầu +
  // phạm vi), luồng đang mở, bản nháp đang gõ, và các diff đang bung ra.
  agent: null, thread: null, draft: "", openDiffs: new Set(), diffCache: new Map(), agentTimer: 0, agentError: "",
};

const esc = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
const short = (value = "") => String(value).split("@")[0].split(/[._-]/).map((part) => part[0]?.toUpperCase() || "").join("").slice(0, 2) || "HG";
const localTime = (value) => value ? new Intl.DateTimeFormat("vi-VN", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "Chưa có";
const statusText = (status) => ({ active: "Đang hoạt động", running: "Đang tạo ảnh", queued: "Đang chờ runner", cancel_requested: "Đang dừng", cancelled: "Đã huỷ", completed: "Hoàn tất", paused: "Sẵn sàng", draft: "Chờ thiết lập", needs_runner: "Cần runner", online: "Runner trực tuyến", offline: "Runner chưa kết nối", pending: "Chờ duyệt", approved: "Đã duyệt", rejected: "Đã từ chối", error: "Có lỗi", planning: "Agent đang soạn", awaiting_approval: "Chờ duyệt", applying: "Đang áp thay đổi", applied: "Đã áp", answered: "Đã trả lời", bot_done: "Đã chuyển lệnh cho bot", failed: "Không thực hiện được" })[status] || status;
const can = (capability) => state.detail?.permissions?.includes(capability) || state.data?.capabilities?.includes(capability) || false;
// Màn hình Agent có bộ quyền riêng do /agent trả về; đừng đọc nhầm sang
// permissions của dashboard detail, hai lần tải đó không đồng bộ với nhau.
const canAgent = (capability) => state.agent?.permissions?.includes(capability) || false;
function safeExternalUrl(value) {
  try {
    const url = new URL(String(value || ""));
    return url.protocol === "https:" ? url.href : "";
  } catch { return ""; }
}

function icon(name) {
  const paths = {
    grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.2" cy="9" r="1.6"/><path d="m4 17 4.8-4.8 3.2 3.2 2.2-2.2L20 19"/>',
    arrows: '<path d="M7 7h12l-3-3"/><path d="m19 7-3 3"/><path d="M17 17H5l3 3"/><path d="m5 17 3-3"/>',
    check: '<circle cx="12" cy="12" r="8.5"/><path d="m8.3 12.1 2.5 2.6 5-5"/>',
    branch: '<circle cx="6" cy="5" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="18" cy="18" r="2"/><path d="M8 5h3a3 3 0 0 1 3 3v7a3 3 0 0 0 3 3h-1"/><path d="M14 8a3 3 0 0 0 3-2"/>',
    home: '<path d="m3 11 9-8 9 8"/><path d="M5.5 10v10h13V10"/>',
    bot: '<rect x="4" y="7" width="16" height="12" rx="3"/><path d="M12 3v4M8 12h.01M16 12h.01M8 16h8"/>',
    project: '<path d="M3 7h6l2 2h10v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/><path d="M3 7V5a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v2"/>',
    review: '<path d="m4 4 16 16"/><path d="M20 10v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h9"/><path d="m8 13 2.3 2.3L19 6.6"/>',
    users: '<circle cx="9" cy="8" r="3"/><path d="M3 20c.5-3.5 2.5-5 6-5s5.5 1.5 6 5"/><path d="M17 11.5a3 3 0 1 0-1.2-5.8"/><path d="M17 15c2.3.1 3.7 1.5 4 4"/>',
    audit: '<path d="M12 8v5l3 2"/><circle cx="12" cy="12" r="9"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.1 2.1-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-3v-.2a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1-2.1-2.1.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.6-1H5v-3h.2a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1 2.1-2.1.1.1a1.7 1.7 0 0 0 1.9.3 1.7 1.7 0 0 0 1-1.6V3h3v.2a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1 2.1 2.1-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v3h-.2a1.7 1.7 0 0 0-1.6 1Z"/>',
    play: '<path d="m9 7 8 5-8 5Z"/>',
    pause: '<path d="M9 6v12M15 6v12"/>',
    back: '<path d="m14 5-7 7 7 7"/><path d="M7 12h12"/>',
  };
  return `<svg viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.grid}</svg>`;
}

function sampleData() {
  const dashboards = [
    { id: "content-image-agent", slug: "agent-tao-anh-content", name: "Agent tạo ảnh Content", description: "Tạo ảnh theo idea, chờ duyệt từng ảnh và gửi kết quả đã duyệt về đúng nguồn.", icon: "image", color: "teal", status: "active", role: "owner", counts: { bots: 1, running: 0, approvals: 2, projects: 0 }, last_activity_at: "2026-08-12T04:00:00.000Z" },
  ];
  return { session: { email: "phong.hothanh@havigroup.llc", display_name: "Hồ Thanh Phong", global_role: "owner", is_owner: true }, capabilities: ["view", "run", "review", "configure", "manage_members", "create_dashboard"], dashboards, role_definitions: [] };
}

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { "content-type": "application/json", ...(options.headers || {}) } });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || "Không thể kết nối Automation Center.");
  return payload;
}

function showToast(message, isError = false) {
  toast.textContent = message;
  toast.className = `toast${isError ? " error" : ""}`;
  toast.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.hidden = true; }, 4600);
}

async function load() {
  if (state.preview) {
    state.data = sampleData();
    state.selected ||= state.data.dashboards[0].slug;
    state.detail = sampleDetail(state.selected);
    render();
    return;
  }
  try {
    state.data = await api("/api/bootstrap");
    state.selected ||= state.data.dashboards[0]?.slug || "";
    if (state.selected) state.detail = await api(`/api/dashboards/${encodeURIComponent(state.selected)}`);
    render();
  } catch (caught) {
    app.innerHTML = loginState(caught.message);
  }
}

function sampleDetail(slug) {
  const dashboard = sampleData().dashboards.find((item) => item.slug === slug) || sampleData().dashboards[0];
  return {
    dashboard,
    permissions: ["view", "run", "review", "configure", "manage_members"],
    projects: [],
    bots: dashboard.slug === "agent-tao-anh-content" ? [
      { id: "content-image-agent-runner", name: "Agent tạo ảnh Content", purpose: "Tạo ảnh theo idea; mỗi ảnh sẽ chờ duyệt trên dashboard.", runner_key: "content-image-runner", status: "paused", runner_status: "online", runner_online: true, runner_last_seen_at: new Date().toISOString(), last_run_status: "ready", active_run: null },
    ] : [],
    approvals: dashboard.slug === "agent-tao-anh-content" ? [
      { id: "sample-a", title: "Ảnh concept mùa lễ", detail: "Chờ người duyệt quyết định trước khi đẩy về nguồn idea.", artifact_url: "", status: "pending", requested_by: "Flow Image Agent", created_at: "2026-08-12T03:50:00.000Z" },
      { id: "sample-b", title: "Ảnh chỉnh sửa thủ công", detail: "Ảnh bổ sung vào bộ idea, cần duyệt riêng.", status: "pending", requested_by: "Hồ Thanh Phong", created_at: "2026-08-12T03:56:00.000Z" },
    ] : [],
    runs: [],
    logs: [{ id: "1", actor_email: "phong.hothanh@havigroup.llc", action: "dashboard.opened", target_type: "dashboard", target_id: dashboard.id, created_at: "2026-08-12T04:00:00.000Z" }],
    members: [{ email: "phong.hothanh@havigroup.llc", display_name: "Hồ Thanh Phong", role: "admin", granted_by: "system", created_at: "2026-08-12T03:00:00.000Z" }],
  };
}

function loginState(message) {
  return `<main class="login-state"><div class="brand-mark">H</div><h1>Automation HaviGroup</h1><p>${esc(message)}</p><p>Trang này chỉ nhận tài khoản công ty qua Cloudflare Access. Sau khi Access được cấu hình, hãy đăng nhập bằng email <strong>@havigroup.llc</strong>.</p></main>`;
}

function sidebar() {
  const session = state.data.session;
  const nav = [
    ["programs", "grid", "Chương trình"], ["agent", "branch", "Agent điều phối"], ["bots", "bot", "Bot"], ["approvals", "review", "Yêu cầu duyệt"], ["projects", "project", "Dự án"], ["audit", "audit", "Lịch sử hoạt động"],
  ];
  return `<aside class="sidebar"><div class="brand"><div class="brand-mark">H</div><div class="brand-copy"><strong>Automation HaviGroup</strong><small>automation.havigroup.llc</small></div></div><nav class="nav-list" aria-label="Điều hướng">${nav.map(([screen, iconName, label]) => `<button class="nav-button ${state.screen === screen ? "active" : ""}" data-screen="${screen}"><span class="nav-icon">${icon(iconName)}</span><span>${label}</span></button>`).join("")}</nav><div class="nav-divider"></div><div class="nav-list"><button class="nav-button" data-action="open-members"><span class="nav-icon">${icon("users")}</span><span>Quyền truy cập</span></button><button class="nav-button" data-action="open-create-dashboard"><span class="nav-icon">${icon("settings")}</span><span>Cài đặt hệ thống</span></button></div><div class="sidebar-spacer"></div><div class="account-chip"><span class="avatar">${esc(short(session.email))}</span><div class="account-copy"><strong>${esc(session.display_name || session.email)}</strong><small>${esc(session.global_role === "owner" ? "Owner" : session.global_role)}</small></div></div></aside>`;
}

function metric(label, value, hint) {
  return `<article class="metric"><span class="metric-label">${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(hint)}</small></article>`;
}

function programsView() {
  const dashboards = state.data.dashboards;
  const totalBots = dashboards.reduce((sum, item) => sum + item.counts.bots, 0);
  const running = dashboards.reduce((sum, item) => sum + item.counts.running, 0);
  const approvals = dashboards.reduce((sum, item) => sum + item.counts.approvals, 0);
  const projects = dashboards.reduce((sum, item) => sum + item.counts.projects, 0);
  const selected = dashboards.find((item) => item.slug === state.selected) || dashboards[0];
  return `<div class="topbar"><div><h1 class="page-title">Chương trình tự động hóa</h1><p class="page-subtitle">Mỗi chương trình là một dashboard độc lập: bot, project, dữ liệu, quyền và lịch sử hoạt động không dùng chung nếu chưa được cấp.</p></div><div class="top-actions">${state.data.session.is_owner ? `<button class="primary-button" data-action="open-create-dashboard"><span class="button-icon">${icon("plus")}</span>Tạo chương trình</button>` : ""}</div></div><section class="overview-grid">${metric("Dashboard được cấp", dashboards.length, "Theo quyền của bạn")}${metric("Tổng bot", totalBots, `${running} bot đang chạy`)}${metric("Chờ duyệt", approvals, "Cần Reviewer hoặc Admin")}${metric("Dự án được gán", projects, "Phạm vi theo dashboard")}</section><section class="program-layout"><div class="program-list">${dashboards.length ? dashboards.map(programCard).join("") : `<div class="empty-state"><div><h2>Chưa có dashboard được cấp</h2><p>Owner có thể tạo chương trình hoặc Admin thêm bạn vào dashboard phù hợp.</p></div></div>`}</div>${selected ? dashboardSummaryPanel(selected) : ""}</section>`;
}

function programCard(dashboard) {
  const selected = dashboard.slug === state.selected;
  return `<article class="program-card ${selected ? "selected" : ""}"><div class="program-icon ${esc(dashboard.color)}">${icon(dashboard.icon)}</div><div class="program-copy"><h2>${esc(dashboard.name)}</h2><p>${esc(dashboard.description)}</p></div><div class="program-stats"><div class="program-stat"><span>Bot</span><strong>${dashboard.counts.bots}</strong></div><div class="program-stat"><span>Dự án</span><strong>${dashboard.counts.projects}</strong></div><div class="program-stat"><span>Duyệt chờ</span><strong>${dashboard.counts.approvals}</strong></div><div class="program-stat"><span>Quyền của bạn</span><strong>${esc(dashboard.role)}</strong></div></div><div class="program-actions"><span class="status ${esc(dashboard.status)}">${esc(statusText(dashboard.status))}</span><button class="secondary-button" data-action="open-dashboard" data-slug="${esc(dashboard.slug)}">Mở dashboard</button></div></article>`;
}

function dashboardSummaryPanel(dashboard) {
  const detail = state.detail?.dashboard?.slug === dashboard.slug ? state.detail : null;
  const bots = detail?.bots || [];
  const projects = detail?.projects || [];
  return `<aside class="detail-panel"><div class="detail-title-row"><div class="program-icon ${esc(dashboard.color)}">${icon(dashboard.icon)}</div><div><h2>${esc(dashboard.name)}</h2><p>${esc(dashboard.description)}</p></div></div><div class="tabs"><button class="tab active">Tổng quan</button><button class="tab" data-action="open-dashboard" data-slug="${esc(dashboard.slug)}">Bot & duyệt</button><button class="tab" data-action="open-members">Quyền truy cập</button></div><section class="detail-section"><h3>Bot trong chương trình</h3><div class="mini-list">${bots.length ? bots.slice(0, 4).map((bot) => `<div class="mini-row"><div><strong>${esc(bot.name)}</strong><small>${esc(bot.purpose || "Chưa có mô tả")}</small></div><span class="status ${esc(bot.status)}">${esc(statusText(bot.status))}</span></div>`).join("") : `<div class="mini-row"><small>Chưa có bot. Tạo bot khi runner đã sẵn sàng.</small></div>`}</div></section><section class="detail-section"><h3>Project được gán</h3><div class="mini-list">${projects.length ? projects.map((project) => `<div class="mini-row"><div><strong>${esc(project.project_name || project.project_id)}</strong><small>${esc(project.project_id)}</small></div></div>`).join("") : `<div class="mini-row"><small>Chưa gán project nào.</small></div>`}</div></section><section class="detail-section"><h3>Ranh giới quyền</h3><div class="permission-note">Vai trò <strong>${esc(dashboard.role)}</strong> chỉ có hiệu lực trong dashboard này. Cấp quyền ở một chương trình không tự mở quyền ở chương trình khác.</div></section></aside>`;
}

function dashboardView() {
  const detail = state.detail;
  if (!detail) return `<div class="empty-state"><div><h2>Đang tải dashboard</h2></div></div>`;
  const { dashboard, bots = [], approvals = [], logs = [], projects = [], runs = [] } = detail;
  const activeCount = bots.filter((item) => item.active_run).length;
  return `<div class="topbar"><div><button class="quiet-button" data-action="back-programs"><span class="button-icon">${icon("back")}</span>Danh mục chương trình</button><h1 class="page-title" style="margin-top:17px">${esc(dashboard.name)}</h1><p class="page-subtitle">${esc(dashboard.description)}</p></div><div class="top-actions">${can("manage_members") ? `<button class="quiet-button" data-action="open-members">Quyền truy cập</button>` : ""}</div></div><section class="overview-grid">${metric("Bot", bots.length, `${activeCount} lệnh đang xử lý`)}${metric("Chờ duyệt", approvals.filter((item) => item.status === "pending").length, "Phải có quyết định từng ảnh")}${metric("Runner", bots.some((item) => item.runner_online) ? "Sẵn sàng" : "Chưa kết nối", bots.some((item) => item.runner_online) ? "Có thể tạo ảnh" : "Không tạo lệnh giả")}${metric("Quyền hiện tại", detail.dashboard.role, `${(detail.permissions || []).join(", ") || "view"}`)}</section><section class="dashboard-shell"><div class="panel"><div class="panel-header"><div><h2>Agent tạo ảnh</h2><p>Bấm tạo ảnh sẽ mở yêu cầu; huỷ/đóng không lưu gì. Sau khi gửi lệnh, nút Dừng luôn khả dụng.</p></div></div>${renderBotTable(bots, dashboard.slug)}</div><div class="panel"><div class="panel-header"><div><h2>Yêu cầu duyệt</h2><p>Ảnh đã tạo sẽ nằm tại đây để duyệt từng ảnh.</p></div></div>${approvals.length ? approvals.map((item) => approvalCard(item, dashboard.slug)).join("") : `<div class="empty-state" style="min-height:180px;margin:0"><div><h2>Chưa có ảnh chờ duyệt</h2><p>Kết quả từ runner sẽ xuất hiện tại đây.</p></div></div>`}</div><div class="panel"><div class="panel-header"><div><h2>Lần chạy gần đây</h2><p>Trạng thái thật từ runner và Google Flow.</p></div></div>${renderRuns(runs)}</div><div class="panel"><div class="panel-header"><div><h2>Hoạt động gần đây</h2><p>Audit theo người thao tác và dashboard.</p></div></div><div class="audit-list">${logs.length ? logs.slice(0, 8).map((log) => `<div class="audit-item"><span class="audit-dot"></span><div><strong>${esc(log.action.replaceAll(".", " · "))}</strong><span>${esc(log.actor_email)} · ${esc(log.target_type)}</span></div><time>${esc(localTime(log.created_at))}</time></div>`).join("") : `<p class="page-subtitle">Chưa có hoạt động được ghi nhận.</p>`}</div></div></section>`;
}

function renderBotTable(bots, slug) {
  if (!bots.length) return `<div class="empty-state" style="min-height:260px;margin:0"><div><h2>Chưa có bot</h2><p>Thêm bot sau khi đã có runner bảo mật hoặc connector phù hợp.</p></div></div>`;
  return `<div style="overflow-x:auto"><table class="bot-table"><thead><tr><th>Bot</th><th>Runner</th><th>Trạng thái</th><th>Lần gần nhất</th><th></th></tr></thead><tbody>${bots.map((bot) => {
    const execution = bot.active_run?.status || bot.status;
    const runnerState = bot.runner_online ? "online" : "offline";
    let control = "";
    if (can("run")) {
      if (["queued", "running"].includes(bot.active_run?.status)) control = `<button class="action-button danger-action" data-action="bot-action" data-bot-id="${esc(bot.id)}" data-bot-action="pause" data-slug="${esc(slug)}">Dừng</button>`;
      else if (bot.active_run?.status === "cancel_requested") control = `<button class="action-button" disabled>Đang dừng…</button>`;
      else if (bot.runner_online) control = `<button class="action-button" data-action="open-content-run" data-bot-id="${esc(bot.id)}" data-slug="${esc(slug)}">Tạo ảnh</button>`;
      else control = `<button class="action-button" data-action="open-runner-setup" data-bot-id="${esc(bot.id)}">Thiết lập runner</button>`;
    }
    return `<tr><td><div class="bot-name"><span class="bot-dot">${icon("bot")}</span><div><strong>${esc(bot.name)}</strong><small>${esc(bot.purpose || "Chưa có mô tả")}</small></div></div></td><td><strong>${esc(bot.runner_key || "Chưa gán")}</strong><small class="runner-state"><span class="status ${runnerState}">${esc(statusText(runnerState))}</span></small></td><td><span class="status ${esc(execution)}">${esc(statusText(execution))}</span></td><td>${esc(localTime(bot.active_run?.created_at || bot.last_run_at))}</td><td><div class="table-actions">${control}</div></td></tr>`;
  }).join("")}</tbody></table></div>`;
}

function renderRuns(runs) {
  if (!runs.length) return `<div class="mini-row"><small>Chưa có lần tạo ảnh nào.</small></div>`;
  return `<div class="mini-list">${runs.slice(0, 8).map((run) => `<div class="mini-row"><div><strong>${esc(run.title || "Ảnh Content")}</strong><small>${esc(run.error || `${run.image_count || 1} ảnh · ${run.aspect || "landscape"}`)}</small></div><span class="status ${esc(run.status)}">${esc(statusText(run.status))}</span></div>`).join("")}</div>`;
}

function approvalCard(item, slug) {
  const isPending = item.status === "pending";
  const artifactUrl = safeExternalUrl(item.artifact_url);
  const artifact = artifactUrl ? `<a class="artifact-link" href="${esc(artifactUrl)}" target="_blank" rel="noopener noreferrer">Mở ảnh kết quả</a>` : "";
  return `<article class="approval-card"><div style="display:flex;justify-content:space-between;gap:12px"><h3>${esc(item.title)}</h3><span class="status ${esc(item.status)}">${esc(statusText(item.status))}</span></div><p>${esc(item.detail)}</p>${artifact}<p>Yêu cầu bởi ${esc(item.requested_by || "Hệ thống")} · ${esc(localTime(item.created_at))}</p>${isPending && can("review") ? `<div class="approval-actions"><button class="secondary-button" data-action="review-approval" data-approval-id="${esc(item.id)}" data-status="approved" data-slug="${esc(slug)}">Duyệt</button><button class="quiet-button" data-action="review-approval" data-approval-id="${esc(item.id)}" data-status="rejected" data-slug="${esc(slug)}">Từ chối</button></div>` : ""}</article>`;
}

// ─── Agent điều phối ────────────────────────────────────────────────────────

// Các trạng thái mà máy trung tâm còn đang làm gì đó; màn hình tự làm mới khi
// có ít nhất một yêu cầu đang ở đây.
const AGENT_BUSY = ["queued", "planning", "applying", "approved"];

function parseList(value) {
  try {
    const parsed = JSON.parse(value || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch { return []; }
}

function diffHtml(text) {
  const lines = String(text || "").split("\n");
  const shown = lines.slice(0, 900);
  const body = shown.map((line) => {
    const marker = line.startsWith("+++") || line.startsWith("---") ? ""
      : line.startsWith("+") ? "add"
      : line.startsWith("-") ? "del"
      : line.startsWith("@@") ? "hunk" : "";
    return marker ? `<span class="${marker}">${esc(line)}</span>` : esc(line);
  }).join("\n");
  const cut = lines.length > shown.length ? `\n… còn ${lines.length - shown.length} dòng nữa.` : "";
  return `<pre class="diff-view">${body}${esc(cut)}</pre>`;
}

function requestCard(request) {
  const files = parseList(request.files_json);
  const mine = request.requested_by === state.data.session.email;
  const canDecide = canAgent("code_approve") && request.status === "awaiting_approval" && (!mine || state.data.session.is_owner);
  const canCancel = ["queued", "planning", "awaiting_approval"].includes(request.status) && (mine || canAgent("code_approve"));
  const diffOpen = state.openDiffs.has(request.id);
  const testLine = request.test_output
    ? `<p>${request.tests_passed ? "Test đã chạy và xanh." : "Test chưa xanh — cần người xem trước khi áp."}</p>`
    : "";
  const protectedNote = request.touches_protected
    ? `<p class="scope-chip danger">Chạm file được bảo vệ · chỉ Owner duyệt được</p>` : "";
  // Diff bị cắt lúc lưu thì bản commit vẫn đầy đủ.  Không nói ra thì người
  // duyệt tưởng mình đã đọc hết trong khi thực tế chưa.
  const truncatedNote = request.diff_truncated
    ? `<p class="scope-chip danger">Diff quá dài nên đã bị cắt khi lưu · bản commit vẫn đầy đủ, hãy xem nhánh ${esc(request.branch || "")} trên máy trung tâm trước khi duyệt</p>` : "";
  // Yêu cầu điều khiển bot không có diff để soi, nên từng lệnh phải hiện ra
  // nguyên văn — nếu không, dòng duy nhất người xem thấy là "Đã chuyển lệnh"
  // mà không biết đã chuyển cho bot nào.
  const botLine = parseList(request.bot_commands_json)
    .map((item) => `<span class="scope-chip ${item.ok ? "" : "danger"}">${esc(`${item.ok ? "✓" : "✗"} ${item.command || "?"} · ${item.bot_id || "?"} · ${item.message || ""}`)}</span>`)
    .join("");
  const failure = request.error ? `<p>${esc(request.error)}</p>` : "";
  return `<article class="approval-card">
    <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start">
      <h3>${esc(request.instruction.slice(0, 120))}</h3>
      <span class="status ${esc(request.status)}">${esc(statusText(request.status))}</span>
    </div>
    <p>${esc(request.requested_by)} · ${esc(localTime(request.created_at))}${request.auto_applied ? " · áp thẳng theo phạm vi" : ""}</p>
    ${request.plan_summary ? `<p>${esc(request.plan_summary)}</p>` : ""}
    ${files.length ? `<div>${files.map((path) => `<span class="scope-chip">${esc(path)}</span>`).join("")}</div>` : ""}
    ${request.files_changed ? `<p>${request.files_changed} file · ${request.lines_changed} dòng${request.branch ? ` · nhánh ${esc(request.branch)}` : ""}</p>` : ""}
    ${botLine ? `<div>${botLine}</div>` : ""}
    ${testLine}${protectedNote}${truncatedNote}${failure}
    ${request.diff_length ? `<button class="quiet-button" data-action="toggle-diff" data-request-id="${esc(request.id)}">${diffOpen ? "Ẩn thay đổi" : "Xem thay đổi"}</button>` : ""}
    ${diffOpen ? (state.diffCache.has(request.id) ? diffHtml(state.diffCache.get(request.id)) : `<pre class="diff-view">Đang tải thay đổi…</pre>`) : ""}
    ${diffOpen && request.test_output ? `<pre class="diff-view">${esc(request.test_output)}</pre>` : ""}
    ${canDecide || canCancel ? `<div class="approval-actions">
      ${canDecide ? `<button class="secondary-button" data-action="decide-request" data-request-id="${esc(request.id)}" data-decision="approved">Duyệt và áp</button>
      <button class="quiet-button" data-action="decide-request" data-request-id="${esc(request.id)}" data-decision="rejected">Từ chối</button>` : ""}
      ${canCancel ? `<button class="quiet-button" data-action="decide-request" data-request-id="${esc(request.id)}" data-decision="cancelled">Rút lại</button>` : ""}
    </div>` : ""}
    ${mine && request.status === "awaiting_approval" && !state.data.session.is_owner ? `<p>Bạn không tự duyệt được thay đổi của chính mình; cần một Admin hoặc Owner khác.</p>` : ""}
  </article>`;
}

function chatPanel() {
  const scope = state.agent.scope;
  const thread = state.thread?.thread || null;
  const messages = state.thread?.messages || [];
  const requests = state.thread?.requests || [];
  const busy = requests.some((request) => AGENT_BUSY.includes(request.status));
  const log = messages.length
    ? messages.map((message) => `<div class="chat-bubble ${esc(message.kind)}"><span class="chat-meta">${esc(message.kind === "agent" ? "Agent điều phối" : message.kind === "system" ? "Hệ thống" : message.author_email)} · ${esc(localTime(message.created_at))}</span>${esc(message.content)}</div>`).join("")
    : `<div class="chat-bubble system">Chưa có trao đổi nào. Hãy mô tả thứ bạn muốn sửa — agent sẽ đọc code trên máy trung tâm và soạn thay đổi.</div>`;

  let composer = "";
  if (!canAgent("code_request")) {
    composer = `<div class="chat-form"><small>Vai trò của bạn chỉ được xem. Hãy nhờ Owner hoặc Admin cấp quyền gửi yêu cầu sửa code.</small></div>`;
  } else if (!scope) {
    composer = `<div class="chat-form"><small>Bạn chưa được cấp phạm vi sửa code trong chương trình này, nên chưa gửi được yêu cầu. Owner hoặc Admin mở phạm vi ở khung bên trái.</small></div>`;
  } else if (!state.agent.runner.online) {
    composer = `<div class="chat-form"><small>Máy trung tâm chưa kết nối nên yêu cầu sẽ không có ai xử lý. Hãy bật <code>orchestrator-runner</code> trước.</small></div>`;
  } else {
    composer = `<div class="chat-form">
      <textarea data-draft placeholder="Ví dụ: đổi nhãn nút Tạo ảnh trên dashboard thành &quot;Tạo ảnh mới&quot;" maxlength="6000" ${busy ? "disabled" : ""}>${esc(state.draft)}</textarea>
      <div class="chat-form-actions">
        <small>Agent chỉ ghi được vào ${scope.allow_globs.length} nhóm đường dẫn đã cấp, tối đa ${scope.max_files} file và ${scope.max_lines} dòng mỗi lần.${scope.auto_apply ? " Thay đổi hợp lệ và test xanh sẽ được áp thẳng." : " Thay đổi luôn chờ người có quyền duyệt."}</small>
        <button class="primary-button" data-action="send-agent" ${busy ? "disabled" : ""}>${busy ? "Agent đang xử lý…" : "Gửi cho agent"}</button>
      </div>
    </div>`;
  }

  return `<div class="panel">
    <div class="panel-header"><div><h2>${esc(thread ? thread.title : "Luồng mới")}</h2><p>${esc(thread ? `Mở bởi ${thread.created_by} · ${localTime(thread.created_at)}` : "Tin nhắn đầu tiên sẽ mở một luồng mới.")}</p></div></div>
    <div class="chat-log">${log}</div>
    ${composer}
    ${requests.length ? `<div style="margin-top:20px"><h3 style="margin:0 0 11px;font-size:.86rem">Thay đổi trong luồng này</h3>${requests.slice().reverse().map(requestCard).join("")}</div>` : ""}
  </div>`;
}

function scopeListPanel() {
  const scope = state.agent.scope;
  const scopes = state.agent.scopes;
  const mine = scope
    ? `<div>${scope.allow_globs.map((glob) => `<span class="scope-chip">${esc(glob)}</span>`).join("")}</div>
       <div class="permission-note">Tối đa ${scope.max_files} file và ${scope.max_lines} dòng mỗi lần. ${scope.auto_apply ? "Thay đổi hợp lệ, test xanh được áp thẳng." : "Mọi thay đổi đều chờ duyệt."}</div>`
    : `<div class="permission-note">Bạn chưa được cấp phạm vi sửa code trong chương trình này.</div>`;
  const table = scopes
    ? `<section class="detail-section"><h3>Phạm vi đã cấp</h3><div class="mini-list">${scopes.length ? scopes.map((row) => `<div class="mini-row"><div><strong>${esc(row.subject_type === "role" ? `Vai trò ${row.subject}` : row.subject)}</strong><small>${esc(String(row.allow_globs).split("\n").join(" · "))}</small></div><span class="status ${row.auto_apply ? "approved" : "pending"}">${row.auto_apply ? "Áp thẳng" : "Chờ duyệt"}</span></div>`).join("") : `<div class="mini-row"><small>Chưa cấp phạm vi cho ai. Chưa ai gửi được yêu cầu sửa code.</small></div>`}</div><button class="secondary-button" data-action="open-code-scope">Cấp hoặc sửa phạm vi</button></section>`
    : "";
  return `<div class="panel">
    <div class="panel-header"><div><h2>Luồng trao đổi</h2><p>Mỗi luồng là một mạch yêu cầu riêng.</p></div><button class="action-button" data-action="new-thread">Luồng mới</button></div>
    <div class="mini-list">${state.agent.threads.length ? state.agent.threads.map((thread) => `<button class="mini-row thread-row ${state.thread?.thread?.id === thread.id ? "selected" : ""}" data-action="open-thread" data-thread-id="${esc(thread.id)}"><div><strong>${esc(thread.title)}</strong><small>${esc(thread.created_by)} · ${esc(localTime(thread.updated_at))}</small></div></button>`).join("") : `<div class="mini-row"><small>Chưa có luồng nào.</small></div>`}</div>
    <section class="detail-section"><h3>Phạm vi của bạn</h3>${mine}</section>
    ${table}
    <section class="detail-section"><h3>Luôn ngoài tầm với</h3><div class="permission-note">Bí mật, cấu hình triển khai, migration và chính phần phân quyền không bao giờ được sửa tự động. Diff chạm vào chúng bắt buộc Owner duyệt tay.</div><div>${state.agent.protected_globs.slice(0, 8).map((glob) => `<span class="scope-chip danger">${esc(glob)}</span>`).join("")}</div></section>
  </div>`;
}

function agentView() {
  if (!state.agent) {
    return state.agentError
      ? `<div class="empty-state"><div><h2>Không tải được Agent điều phối</h2><p>${esc(state.agentError)}</p><div class="chat-form-actions"><button class="secondary-button" data-action="retry-agent">Thử lại</button><button class="quiet-button" data-action="back-programs">Danh mục chương trình</button></div></div></div>`
      : `<div class="empty-state"><div><h2>Đang tải Agent điều phối</h2></div></div>`;
  }
  const runner = state.agent.runner;
  const requests = state.agent.requests || [];
  const waiting = requests.filter((request) => request.status === "awaiting_approval").length;
  const scope = state.agent.scope;
  return `<div class="topbar"><div><button class="quiet-button" data-action="back-programs"><span class="button-icon">${icon("back")}</span>Danh mục chương trình</button><h1 class="page-title" style="margin-top:17px">Agent điều phối</h1><p class="page-subtitle">Nhắn yêu cầu sửa code cho agent. Máy trung tâm đọc repo, hỏi ChatGPT, ghi file và chạy test — máy cá nhân không tham gia. Phạm vi theo quyền quyết định agent được chạm vào đâu.</p></div></div>
  <section class="overview-grid">
    ${metric("Máy trung tâm", runner.online ? "Trực tuyến" : "Chưa kết nối", runner.last_seen_at ? `Lần cuối ${localTime(runner.last_seen_at)}` : `Runner ${runner.runner_key}`)}
    ${metric("Phạm vi của bạn", scope ? `${scope.allow_globs.length} nhóm` : "Chưa cấp", scope ? `${scope.max_files} file · ${scope.max_lines} dòng` : "Nhờ Owner hoặc Admin mở")}
    ${metric("Chờ duyệt", waiting, "Cần Admin hoặc Owner")}
    ${metric("Yêu cầu đã gửi", requests.length, "30 yêu cầu gần nhất")}
  </section>
  <section class="agent-shell">${scopeListPanel()}${chatPanel()}</section>`;
}

// Diff không đi kèm danh sách vì nó lớn và ít khi được mở.  Tải một lần rồi
// giữ lại: nội dung của một yêu cầu đã có diff thì không đổi nữa.
async function toggleDiff(requestId) {
  if (state.openDiffs.has(requestId)) {
    state.openDiffs.delete(requestId);
    render();
    return;
  }
  state.openDiffs.add(requestId);
  render();
  if (state.diffCache.has(requestId)) return;
  try {
    const payload = await api(`/api/dashboards/${encodeURIComponent(state.selected)}/agent/requests/${encodeURIComponent(requestId)}/diff`);
    state.diffCache.set(requestId, String(payload.diff_text || ""));
  } catch (caught) {
    // Mở ra rồi mà không tải được thì phải đóng lại: một khung trống trông
    // hệt như "thay đổi này không có gì", và đó là hiểu nhầm nguy hiểm nhất
    // ngay trước lúc bấm Duyệt.
    state.openDiffs.delete(requestId);
    showToast(caught.message, true);
  }
  render();
}

async function refreshAgent({ threadId = state.thread?.thread?.id || "", quiet = false } = {}) {
  clearTimeout(state.agentTimer);
  const base = `/api/dashboards/${encodeURIComponent(state.selected)}/agent`;
  try {
    state.agent = await api(base);
    state.thread = threadId ? await api(`${base}/threads/${encodeURIComponent(threadId)}`) : null;
    state.agentError = "";
    render();
    scheduleAgentRefresh();
  } catch (caught) {
    if (!quiet) showToast(caught.message, true);
    // Một yêu cầu chạy vài phút, nên một lần rớt mạng không được phép dừng hẳn
    // vòng làm mới — nếu dừng, người dùng nhìn thấy trạng thái đứng im và tưởng
    // agent treo.  Thử lại chậm hơn nhịp thường.
    state.agentError = caught.message;
    render();
    if (state.screen === "agent") {
      state.agentTimer = setTimeout(() => { void refreshAgent({ threadId, quiet: true }); }, 12000);
    }
  }
}

function scheduleAgentRefresh() {
  clearTimeout(state.agentTimer);
  if (state.screen !== "agent") return;
  const pool = [...(state.thread?.requests || []), ...(state.agent?.requests || [])];
  if (!pool.some((request) => AGENT_BUSY.includes(request.status))) return;
  state.agentTimer = setTimeout(() => { void refreshAgent({ quiet: true }); }, 4500);
}

async function openAgent(threadId = "") {
  if (!state.selected) return showToast("Hãy chọn một chương trình trước.", true);
  if (state.preview) return showToast("Preview: Agent điều phối cần dữ liệu thật từ máy trung tâm.", true);
  state.screen = "agent";
  state.thread = null;
  render();
  await refreshAgent({ threadId });
}

async function sendAgentMessage() {
  const message = state.draft.trim();
  if (message.length < 8) return showToast("Hãy mô tả yêu cầu rõ hơn (ít nhất 8 ký tự).", true);
  const base = `/api/dashboards/${encodeURIComponent(state.selected)}/agent`;
  const threadId = state.thread?.thread?.id || "";
  try {
    let target = threadId;
    if (threadId) {
      await api(`${base}/threads/${encodeURIComponent(threadId)}/messages`, { method: "POST", body: JSON.stringify({ message }) });
    } else {
      const created = await api(`${base}/threads`, { method: "POST", body: JSON.stringify({ title: message.slice(0, 120), message }) });
      target = created.thread_id;
    }
    state.draft = "";
    showToast("Đã gửi cho agent. Máy trung tâm đang xử lý.");
    await refreshAgent({ threadId: target });
  } catch (caught) { showToast(caught.message, true); }
}

async function decideCodeRequest(requestId, decision) {
  try {
    await api(`/api/dashboards/${encodeURIComponent(state.selected)}/agent/requests/${encodeURIComponent(requestId)}`, { method: "POST", body: JSON.stringify({ decision }) });
    showToast({ approved: "Đã duyệt. Máy trung tâm sẽ áp thay đổi.", rejected: "Đã từ chối. Không file nào bị đổi.", cancelled: "Đã rút lại yêu cầu." }[decision]);
    await refreshAgent({});
  } catch (caught) { showToast(caught.message, true); }
}

async function openCodeScope() {
  if (!state.agent?.scopes) return showToast("Bạn không có quyền cấp phạm vi.", true);
  const isOwner = state.data.session.is_owner;
  const result = await showModal(
    "Cấp phạm vi sửa code",
    "Phạm vi là ranh giới thật: agent chỉ ghi được vào những đường dẫn khớp danh sách này. Để trống danh sách nghĩa là gỡ quyền.",
    `<label>Áp cho<select name="subject_type"><option value="role">Một vai trò trong dashboard</option><option value="user">Một người cụ thể</option></select></label>
     <label>Vai trò hoặc email<input name="subject" required maxlength="254" placeholder="operator hoặc ten@havigroup.llc" /></label>
     <label>Đường dẫn được sửa <small>(mỗi dòng một mẫu, ví dụ flow_web/static/**)</small><textarea name="allow_globs" placeholder="flow_web/static/**&#10;automation_center/public/**"></textarea></label>
     <div class="form-row"><label>Tối đa số file<input name="max_files" type="number" min="1" max="60" value="3" /></label><label>Tối đa số dòng<input name="max_lines" type="number" min="1" max="6000" value="200" /></label></div>
     ${isOwner ? `<label><input type="checkbox" name="auto_apply" /> Áp thẳng khi hợp lệ và test xanh (không cần ai duyệt)</label>` : `<div class="setup-note">Chỉ Owner mới bật được chế độ áp thẳng.</div>`}
     <label>Ghi chú<input name="note" maxlength="240" placeholder="Vì sao nhóm này được sửa phần đó" /></label>`,
    "Lưu phạm vi",
  );
  if (!result.submitted) return;
  try {
    await api(`/api/dashboards/${encodeURIComponent(state.selected)}/agent/scopes`, { method: "POST", body: JSON.stringify({
      subject_type: result.data.subject_type, subject: result.data.subject, allow_globs: result.data.allow_globs,
      max_files: result.data.max_files, max_lines: result.data.max_lines, auto_apply: result.data.auto_apply === true, note: result.data.note,
    }) });
    showToast("Đã lưu phạm vi.");
    await refreshAgent({});
  } catch (caught) { showToast(caught.message, true); }
}

function filteredView() {
  if (state.screen === "agent") return agentView();
  if (state.screen === "programs") return programsView();
  if (state.screen === "bots") return dashboardView();
  if (state.screen === "approvals") return dashboardView();
  if (state.screen === "projects") return dashboardView();
  if (state.screen === "audit") return dashboardView();
  return programsView();
}

function render() {
  app.innerHTML = `${sidebar()}<main class="main">${filteredView()}</main>`;
  // Màn hình Agent tự làm mới trong lúc máy trung tâm chạy. Nếu người dùng
  // đang gõ thì trả con trỏ về ô soạn — không thì mỗi vòng làm mới lại cướp
  // mất chỗ đang gõ dở.
  if (state.composerFocused) {
    const composer = app.querySelector("[data-draft]");
    if (composer) {
      composer.focus();
      composer.selectionStart = composer.selectionEnd = composer.value.length;
    }
  }
}

async function selectDashboard(slug, screen = "programs") {
  // Đổi chương trình là đổi cả phạm vi quyền; giữ lại luồng chat cũ sẽ hiển
  // thị dữ liệu của dashboard trước dưới nhãn dashboard mới.
  clearTimeout(state.agentTimer);
  state.agent = null;
  state.thread = null;
  state.draft = "";
  state.agentError = "";
  state.selected = slug;
  state.screen = screen;
  state.tab = "overview";
  try {
    state.detail = state.preview ? sampleDetail(slug) : await api(`/api/dashboards/${encodeURIComponent(slug)}`);
    render();
  } catch (caught) { showToast(caught.message, true); }
}

modal.addEventListener("click", (event) => {
  if (event.target === modal) modal.close("cancel");
});

function showModal(title, intro, body, onSubmitLabel = "Lưu", { submit = true } = {}) {
  const actions = submit
    ? `<button type="button" class="quiet-button" data-modal-close>Huỷ</button><button type="submit" class="primary-button">${esc(onSubmitLabel)}</button>`
    : `<button type="button" class="primary-button" data-modal-close>Đóng</button>`;
  modal.innerHTML = `<form class="modal-body" novalidate><h2>${esc(title)}</h2><p>${esc(intro)}</p><div class="form-grid">${body}</div><div class="modal-actions">${actions}</div></form>`;
  const form = modal.querySelector("form");
  return new Promise((resolve) => {
    const finish = () => {
      const data = Object.fromEntries(new FormData(form).entries());
      for (const input of form.querySelectorAll('input[type="checkbox"]')) data[input.name] = input.checked;
      resolve({ submitted: modal.returnValue === "submit", data });
    };
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      modal.close("submit");
    });
    form.querySelector("[data-modal-close]")?.addEventListener("click", () => modal.close("cancel"));
    modal.addEventListener("close", finish, { once: true });
    modal.showModal();
  });
}

async function openCreateDashboard() {
  if (!state.data.session.is_owner) return showToast("Chỉ Owner có thể tạo chương trình.", true);
  const result = await showModal("Tạo chương trình", "Mỗi chương trình là một dashboard tách biệt về dữ liệu, bot và quyền. Bấm Huỷ, Escape hoặc ra ngoài hộp để bỏ qua hoàn toàn.", `<label>Tên chương trình<input name="name" required maxlength="120" placeholder="Ví dụ: Agent chăm sóc khách hàng" /></label><label>Mô tả<textarea name="description" maxlength="420" placeholder="Mục đích và ranh giới vận hành"></textarea></label><label>Slug (tùy chọn)<input name="slug" maxlength="64" placeholder="agent-cham-soc-khach-hang" /></label><label><input type="checkbox" name="runner_required" checked /> Cần runner để thực thi bot</label>`);
  if (!result.submitted) return;
  try {
    if (state.preview) { showToast("Preview: dashboard sẽ được tạo sau khi triển khai."); return; }
    const output = await api("/api/dashboards", { method: "POST", body: JSON.stringify({ name: result.data.name, description: result.data.description, slug: result.data.slug, runner_required: result.data.runner_required }) });
    showToast("Đã tạo chương trình ở trạng thái chờ thiết lập.");
    await load();
    await selectDashboard(output.dashboard.slug);
  } catch (caught) { showToast(caught.message, true); }
}

async function openCreateBot() {
  if (!state.detail || !can("configure")) return showToast("Bạn không có quyền cấu hình bot.", true);
  const result = await showModal("Tạo bot", "Bot mới sẽ chưa tự chạy nếu chưa được nối với runner bảo mật.", `<label>Tên bot<input name="name" required maxlength="120" placeholder="Ví dụ: Image Generation Runner" /></label><label>Mục đích<textarea name="purpose" maxlength="500" placeholder="Bot thực hiện việc gì, trong phạm vi nào?"></textarea></label><label>Runner key (tùy chọn)<input name="runner_key" maxlength="120" placeholder="Ví dụ: flow-runner-hcm" /></label>`);
  if (!result.submitted) return;
  try {
    if (state.preview) { showToast("Preview: bot sẽ được tạo sau khi triển khai."); return; }
    await api(`/api/dashboards/${encodeURIComponent(state.selected)}/bots`, { method: "POST", body: JSON.stringify({ name: result.data.name, purpose: result.data.purpose, runner_key: result.data.runner_key }) });
    showToast("Đã tạo bot. Hãy nối runner trước khi chạy.");
    await selectDashboard(state.selected, "bots");
  } catch (caught) { showToast(caught.message, true); }
}

async function openMembers() {
  if (!state.detail || !can("manage_members")) return showToast("Chọn một dashboard mà bạn có quyền quản lý thành viên.", true);
  const members = state.detail.members || [];
  const result = await showModal("Quyền truy cập dashboard", "Cấp quyền chỉ cho dashboard đang mở; không cấp quyền sang chương trình khác.", `<div class="mini-list">${members.length ? members.map((member) => `<div class="mini-row"><div><strong>${esc(member.display_name || member.email)}</strong><small>${esc(member.email)}</small></div><span class="status ${esc(member.role)}">${esc(member.role)}</span></div>`).join("") : `<div class="mini-row"><small>Chưa có thành viên được gán riêng.</small></div>`}</div><label>Email công ty<input name="email" type="email" required placeholder="ten@havigroup.llc" /></label><label>Vai trò<select name="role"><option value="viewer">Viewer — chỉ xem</option><option value="reviewer">Reviewer — xem và duyệt</option><option value="operator">Operator — xem và chạy bot</option><option value="admin">Admin — cấu hình và cấp quyền</option></select></label>`, "Cấp quyền");
  if (!result.submitted) return;
  try {
    if (state.preview) { showToast("Preview: quyền sẽ được lưu sau khi triển khai."); return; }
    await api(`/api/dashboards/${encodeURIComponent(state.selected)}/members`, { method: "POST", body: JSON.stringify({ email: result.data.email, role: result.data.role }) });
    showToast("Đã cấp quyền theo dashboard.");
    await selectDashboard(state.selected, state.screen);
  } catch (caught) { showToast(caught.message, true); }
}

async function openRunnerSetup(botId) {
  const bot = state.detail?.bots?.find((item) => item.id === botId);
  if (!bot) return;
  await showModal("Runner chưa kết nối", "Agent sẽ không nhận lệnh và không tự báo chạy khi runner chưa online.", `<div class="setup-note"><strong>Để bật Agent tạo ảnh Content:</strong><ol><li>Chạy Flow v2 trên Mac/VM công ty và đăng nhập Google Flow.</li><li>Tạo Cloudflare Access Service Token giới hạn riêng cho Automation.</li><li>Điền các giá trị vào file runner rồi chạy Content Image Runner.</li></ol><p>Không có thay đổi nào được lưu khi bạn đóng hộp này.</p></div>`, "Đóng", { submit: false });
}

async function openContentRun(slug, botId) {
  const bot = state.detail?.bots?.find((item) => item.id === botId);
  // Bot ERP cần biết ghi ảnh đã duyệt về Task nào.  Để trống thì Flow tự lấy
  // Task từ danh sách nguồn của PROJ-0049, nên ô này không bắt buộc.
  const erpField = bot?.runner_key === "listing2-erp-runner"
    ? `<label>Mã Task ERP nguồn <small>(để trống nếu muốn Flow tự chọn Task trong PROJ-0049)</small><input name="erp_task_id" maxlength="140" pattern="[Tt][Aa][Ss][Kk]-[A-Za-z0-9-]{1,120}" placeholder="TASK-0001" /></label>`
    : "";
  const result = await showModal("Tạo ảnh Content", "Nhập idea rõ ràng. Bấm Huỷ, Escape hoặc ra ngoài hộp sẽ không tạo lệnh nào.", `<label>Idea / prompt<input name="title" maxlength="120" placeholder="Ví dụ: Ảnh lifestyle bình giữ nhiệt cho mùa tựu trường" /></label><label>Mô tả chi tiết<textarea name="prompt" required minlength="5" maxlength="3000" placeholder="Sản phẩm, phong cách, màu sắc, đối tượng, chữ cần tránh…"></textarea></label>${erpField}<div class="form-row"><label>Số ảnh<select name="count"><option value="1">1 ảnh</option><option value="2">2 ảnh</option><option value="3">3 ảnh</option><option value="4">4 ảnh</option></select></label><label>Tỷ lệ<select name="aspect"><option value="landscape">Ngang</option><option value="portrait">Dọc</option><option value="square">Vuông</option></select></label></div>`, "Bắt đầu tạo ảnh");
  if (!result.submitted) return;
  await botAction(slug, botId, "run", result.data);
}

async function botAction(slug, botId, action, options = {}) {
  try {
    if (state.preview) {
      const bot = state.detail?.bots?.find((item) => item.id === botId);
      if (!bot) return;
      if (action === "run") {
        bot.status = "running";
        bot.last_run_at = new Date().toISOString();
        bot.active_run = { id: `preview-${Date.now()}`, title: options.title || "Ảnh Content", prompt: options.prompt, image_count: Number(options.count || 1), aspect: options.aspect || "landscape", status: "queued", created_at: bot.last_run_at };
        showToast("Preview: đã xếp lệnh; nút Dừng đang hoạt động.");
      } else {
        bot.status = "paused";
        bot.last_run_status = "cancelled_before_start";
        bot.active_run = null;
        showToast("Preview: đã huỷ lệnh trước khi runner nhận việc.");
      }
      render();
      return;
    }
    const output = await api(`/api/dashboards/${encodeURIComponent(slug)}/bots/${encodeURIComponent(botId)}/action`, { method: "POST", body: JSON.stringify({ action, ...options }) });
    showToast(output.message || "Đã ghi nhận lệnh bot.");
    await selectDashboard(slug, "bots");
  } catch (caught) { showToast(caught.message, true); }
}

async function reviewApproval(slug, approvalId, status) {
  try {
    if (state.preview) { showToast(`Preview: đã ${status === "approved" ? "duyệt" : "từ chối"} yêu cầu.`); return; }
    await api(`/api/dashboards/${encodeURIComponent(slug)}/approvals/${encodeURIComponent(approvalId)}`, { method: "POST", body: JSON.stringify({ status }) });
    showToast(status === "approved" ? "Đã duyệt yêu cầu." : "Đã từ chối yêu cầu.");
    await selectDashboard(slug, "approvals");
  } catch (caught) { showToast(caught.message, true); }
}

app.addEventListener("input", (event) => {
  if (event.target.matches("[data-draft]")) state.draft = event.target.value;
});
app.addEventListener("focusin", (event) => {
  if (event.target.matches("[data-draft]")) state.composerFocused = true;
});
app.addEventListener("focusout", (event) => {
  if (event.target.matches("[data-draft]")) state.composerFocused = false;
});

app.addEventListener("click", (event) => {
  const target = event.target.closest("[data-action], [data-screen]");
  if (!target) return;
  if (target.dataset.screen) {
    if (target.dataset.screen === "agent") { void openAgent(); return; }
    clearTimeout(state.agentTimer);
    state.screen = target.dataset.screen;
    render();
    return;
  }
  const action = target.dataset.action;
  if (action === "open-thread") void refreshAgent({ threadId: target.dataset.threadId });
  if (action === "retry-agent") void refreshAgent();
  if (action === "new-thread") { state.thread = null; state.draft = ""; render(); }
  if (action === "send-agent") void sendAgentMessage();
  if (action === "decide-request") void decideCodeRequest(target.dataset.requestId, target.dataset.decision);
  if (action === "open-code-scope") void openCodeScope();
  if (action === "toggle-diff") void toggleDiff(target.dataset.requestId);
  if (action === "open-dashboard") void selectDashboard(target.dataset.slug, "bots");
  if (action === "back-programs") { clearTimeout(state.agentTimer); state.agentError = ""; state.screen = "programs"; render(); }
  if (action === "open-create-dashboard") void openCreateDashboard();
  if (action === "open-create-bot") void openCreateBot();
  if (action === "open-members") void openMembers();
  if (action === "open-runner-setup") void openRunnerSetup(target.dataset.botId);
  if (action === "open-content-run") void openContentRun(target.dataset.slug, target.dataset.botId);
  if (action === "bot-action") void botAction(target.dataset.slug, target.dataset.botId, target.dataset.botAction);
  if (action === "review-approval") void reviewApproval(target.dataset.slug, target.dataset.approvalId, target.dataset.status);
});

load();
