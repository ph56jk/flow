const $ = (selector) => document.querySelector(selector);
const ETSY_SHOP_MANAGER_URL = "https://www.etsy.com/your/shops/me/tools/listings/stats:true";
// Live board "ETSY - VN32" (shortLink). The old 2025 board (gpy5eAiG) and the "2026" board
// (I2ti3PbI) were retired, so their hardcoded C5/C6/Ready/Idea source options were removed —
// a stale click used to 404. Any other column/board is added at runtime via "Load cột".
const DEFAULT_TRELLO_BOARD_ID = "mZJYmYJi";
const DEFAULT_TRELLO_VN32_LIST_ID = "6a41f0dd41358bebf0229283";
const LAST_FLOW_RUN_STORAGE_KEY = "flow-last-flow-run-v1";
const TOOL_MODE = detectToolMode();
const TRELLO_SOURCE_OPTIONS = {
  // Single default column on the live board. product:"" = whole-column run. Extra columns are
  // registered dynamically by renderBoardColumns() after "Load cột", keyed by their list id.
  c6: {
    label: "C6 VN32",
    product: "",
    boardId: DEFAULT_TRELLO_BOARD_ID,
    listId: DEFAULT_TRELLO_VN32_LIST_ID,
  },
};

const els = {
  healthPill: $("#healthPill"),
  flowPill: $("#flowPill"),
  etsyPill: $("#etsyPill"),
  refreshButton: $("#refreshButton"),
  flowState: $("#flowState"),
  flowDetail: $("#flowDetail"),
  etsyState: $("#etsyState"),
  etsyDetail: $("#etsyDetail"),
  extensionState: $("#extensionState"),
  extensionDetail: $("#extensionDetail"),
  jobState: $("#jobState"),
  jobDetail: $("#jobDetail"),
  flowStatusButton: $("#flowStatusButton"),
  etsyStatusButton: $("#etsyStatusButton"),
  extensionStatusButton: $("#extensionStatusButton"),
  jobsStatusButton: $("#jobsStatusButton"),
  flowDrawer: $("#flowDrawer"),
  etsyDrawer: $("#etsyDrawer"),
  jobsDrawer: $("#jobsDrawer"),
  consoleDrawer: $("#consoleDrawer"),
  flowSetupStatus: $("#flowSetupStatus"),
  flowProjectId: $("#flowProjectId"),
  flowProjectName: $("#flowProjectName"),
  flowTimeout: $("#flowTimeout"),
  flowCdpUrl: $("#flowCdpUrl"),
  geminiApiKey: $("#geminiApiKey"),
  geminiModel: $("#geminiModel"),
  imageEngineSelect: $("#imageEngineSelect"),
  saveFlowButton: $("#saveFlowButton"),
  saveGeminiButton: $("#saveGeminiButton"),
  openFlowFromSetupButton: $("#openFlowFromSetupButton"),
  flowBadge: $("#flowBadge"),
  etsyBadge: $("#etsyBadge"),
  trelloBadge: $("#trelloBadge"),
  openFlowButton: $("#openFlowButton"),
  openLoginButton: $("#openLoginButton"),
  preflightButton: $("#preflightButton"),
  quickPrompt: $("#quickPrompt"),
  imageCount: $("#imageCount"),
  aspectSelect: $("#aspectSelect"),
  quickTrelloEnabled: $("#quickTrelloEnabled"),
  quickEtsyEnabled: $("#quickEtsyEnabled"),
  runQuickJobButton: $("#runQuickJobButton"),
  etsyWarning: $("#etsyWarning"),
  etsyShopId: $("#etsyShopId"),
  etsyUserId: $("#etsyUserId"),
  etsyApiKey: $("#etsyApiKey"),
  etsyApiSecret: $("#etsyApiSecret"),
  etsyTaxonomyId: $("#etsyTaxonomyId"),
  etsyShippingProfileId: $("#etsyShippingProfileId"),
  etsyPrice: $("#etsyPrice"),
  etsyQuantity: $("#etsyQuantity"),
  saveEtsyButton: $("#saveEtsyButton"),
  saveEtsyShortcutButton: $("#saveEtsyShortcutButton"),
  etsySetupStatus: $("#etsySetupStatus"),
  previewEtsyButton: $("#previewEtsyButton"),
  connectEtsyTopButton: $("#connectEtsyTopButton"),
  connectEtsyButton: $("#connectEtsyButton"),
  runEtsyCopyButton: $("#runEtsyCopyButton"),
  disconnectEtsyButton: $("#disconnectEtsyButton"),
  etsyConnectDot: $("#etsyConnectDot"),
  etsyConnectLabel: $("#etsyConnectLabel"),
  etsyCallbackHint: $("#etsyCallbackHint"),
  copyCallbackButton: $("#copyCallbackButton"),
  autoProduct: $("#autoProduct"),
  boardLinkInput: $("#boardLinkInput"),
  loadBoardColumnsButton: $("#loadBoardColumnsButton"),
  autoSourceGroup: $("#autoSourceGroup"),
  autoSourceChecks: $("#autoSourceChecks"),
  autoLimit: $("#autoLimit"),
  autoContinuous: $("#autoContinuous"),
  autoCreateEtsy: $("#autoCreateEtsy"),
  runAutoButton: $("#runAutoButton"),
  listLatestEtsyButton: $("#listLatestEtsyButton"),
  latestEtsyHint: $("#latestEtsyHint"),
  checkAutoButton: $("#checkAutoButton"),
  jobsRefreshButton: $("#jobsRefreshButton"),
  jobsList: $("#jobsList"),
  consoleOutput: $("#consoleOutput"),
  clearConsoleButton: $("#clearConsoleButton"),
  autoAccountSelect: $("#autoAccountSelect"),
  accountsDrawer: $("#accountsDrawer"),
  accountsRefreshButton: $("#accountsRefreshButton"),
  accountsList: $("#accountsList"),
  accountForm: $("#accountForm"),
  accSlug: $("#accSlug"),
  accLabel: $("#accLabel"),
  accBoard: $("#accBoard"),
  accList: $("#accList"),
  accShop: $("#accShop"),
  addAccountButton: $("#addAccountButton"),
  accountStatus: $("#accountStatus"),
};

const state = {
  payload: {},
  hydratedFlow: false,
  hydratedEtsy: false,
  hydratedIntegrations: false,
  extensionNonce: "",
  externalExtensionId: "",
  polling: null,
  lastFlowRun: readLastFlowRunContext(),
  etsyAccounts: { accounts: [], default_slug: "" },
};

const EXTERNAL_EXTENSION_IDS = [
  "jpamdibjfnnneopokijhcmopgamlncmp",
  "fchedljplejnjllckaafaggdnebngehe",
  "hjnjmjmjiijifklidikbhblblcnbkfae",
  "fignfifoniblkonapihmkfakmlgkbkcf",
  "efmoofpdlibfmmhkehcilcoigfneklon",
];

function text(value, fallback = "-") {
  const result = String(value ?? "").trim();
  return result || fallback;
}

function clampInt(value, min, max, fallback) {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return Math.max(min, Math.min(max, parsed));
}

function setBadge(element, label, tone = "") {
  if (!element) return;
  element.textContent = label;
  element.className = ["pill", tone].filter(Boolean).join(" ");
}

function setToolBadge(element, label, tone = "") {
  if (!element) return;
  element.textContent = label;
  element.className = ["tool-badge", tone].filter(Boolean).join(" ");
}

// Set once the user loads a board's columns via "Load cột": after that, an empty selection
// means "nothing picked yet" instead of silently defaulting to the hardcoded C6 column.
let boardColumnsLoaded = false;

function selectedTrelloSourceKeys() {
  const checked = Array.from(document.querySelectorAll("input[name='autoSource']:checked"))
    .map((box) => box.value)
    .filter((key) => TRELLO_SOURCE_OPTIONS[key]);
  if (checked.length) return checked;
  return boardColumnsLoaded ? [] : ["c6"];
}

function selectedTrelloSourceKey() {
  // The Flow path and all labels still work off a single column: use the first
  // checked column. The Etsy draft path uses selectedTrelloSourceKeys() for multi.
  return selectedTrelloSourceKeys()[0];
}

function selectedTrelloSource() {
  return TRELLO_SOURCE_OPTIONS[selectedTrelloSourceKey()] || TRELLO_SOURCE_OPTIONS.c6;
}

function selectedImageEngine() {
  return els.imageEngineSelect?.value === "gemini_api" ? "gemini_api" : "google_flow";
}

function imageEngineLabel() {
  return selectedImageEngine() === "gemini_api" ? "Gemini API" : "Google Flow";
}

function autoRouteLabel() {
  if (TOOL_MODE === "etsy") {
    return `${selectedTrelloSource().label} -> kiểm ảnh Trello -> Etsy Draft`;
  }
  if (TOOL_MODE === "amazon") {
    return `${selectedTrelloSource().label} -> kiểm ảnh Trello -> Amazon Draft`;
  }
  if (TOOL_MODE === "flow") {
    return `${selectedTrelloSource().label} -> ${imageEngineLabel()}`;
  }
  return `${selectedTrelloSource().label} -> ${imageEngineLabel()} -> Listing Etsy riêng`;
}

function updateAutoSourceUi() {
  if (!els.trelloBadge) return;
  els.trelloBadge.textContent = autoRouteLabel();
  renderEtsyListingAction(state.payload);
}

function detectToolMode() {
  const params = new URLSearchParams(window.location.search);
  const queryMode = params.get("tool");
  if (queryMode === "flow" || queryMode === "etsy" || queryMode === "amazon") return queryMode;
  const path = window.location.pathname.replace(/\/+$/, "");
  if (path.endsWith("/flow") || path.endsWith("/flow-tool")) return "flow";
  if (path.endsWith("/etsy") || path.endsWith("/etsy-tool")) return "etsy";
  if (path.endsWith("/amazon") || path.endsWith("/amazon-tool")) return "amazon";
  return "combined";
}

function listingMarketplaceKey() {
  return TOOL_MODE === "amazon" ? "amazon" : "etsy";
}

function listingMarketplaceName() {
  return listingMarketplaceKey() === "amazon" ? "Amazon" : "Etsy";
}

function listingCopyResultKey() {
  return listingMarketplaceKey() === "amazon" ? "amazon_browser_copy" : "etsy_browser_copy";
}

function listingQueueEndpoint() {
  return listingMarketplaceKey() === "amazon" ? "/api/amazon/browser-copy/queue" : "/api/etsy/browser-copy/queue";
}

function listingEnqueueEndpoint() {
  return listingMarketplaceKey() === "amazon" ? "/api/amazon/browser-copy/enqueue" : "/api/etsy/browser-copy/enqueue";
}

function listingJobEnqueueEndpoint(jobId) {
  const encoded = encodeURIComponent(jobId);
  return listingMarketplaceKey() === "amazon"
    ? `/api/jobs/${encoded}/amazon-browser-copy/enqueue`
    : `/api/jobs/${encoded}/etsy-browser-copy/enqueue`;
}

function applyListingJobFlags(job = {}) {
  const isAmazon = listingMarketplaceKey() === "amazon";
  job.etsy_enabled = !isAmazon;
  job.etsy_browser_copy_enabled = !isAmazon;
  job.etsy_publish = false;
  job.amazon_enabled = isAmazon;
  job.amazon_browser_copy_enabled = isAmazon;
  job.amazon_publish = false;
  job.amazon_delete_existing_images = true;
  return job;
}

function setHidden(selector, hidden) {
  document.querySelectorAll(selector).forEach((element) => {
    element.hidden = hidden;
  });
}

function setFirstText(selector, value) {
  const element = document.querySelector(selector);
  if (element) element.textContent = value;
}

function setToolModeActive(mode) {
  document.querySelectorAll("[data-tool-link]").forEach((link) => {
    const isActive = link.getAttribute("data-tool-link") === mode;
    link.classList.toggle("active", isActive || (mode === "combined" && link.getAttribute("data-tool-link") === "combined"));
  });
}

function applyToolMode() {
  document.body.dataset.toolMode = TOOL_MODE;
  setToolModeActive(TOOL_MODE);
  const listingOnly = TOOL_MODE === "etsy" || TOOL_MODE === "amazon";
  setHidden(".etsy-only", !listingOnly);
  setHidden(".account-pick", TOOL_MODE === "amazon");

  if (TOOL_MODE === "flow") {
    document.title = "Flow Tool";
    setFirstText(".kicker", "Flow Tool");
    setFirstText(".topbar h1", "Tạo ảnh từ Trello");
    setHidden(".setup-etsy, .etsy-listing-step, #etsyDrawer, #etsyPill, #extensionStatusButton, .small-status > a[href='/api/extension/download']", true);
    setHidden(".setup-flow, .check-step, .run-step, .auto-step, #flowDrawer, #flowPill", false);
    if (els.autoProduct) {
      els.autoProduct.placeholder = "Để trống: lấy cột đang chọn. Hoặc nhập SKU/tên sản phẩm để chạy Flow...";
    }
    return;
  }

  if (listingOnly) {
    const marketplace = listingMarketplaceName();
    document.title = `${marketplace} Draft Tool`;
    setFirstText(".kicker", `${marketplace} Tool`);
    setFirstText(".topbar h1", "Listing ảnh vào Draft");
    setHidden(".setup-flow, .check-step, .run-step, #flowDrawer, #flowPill, #runAutoButton, #checkAutoButton, .auto-continuous", true);
    setHidden(".setup-etsy, .etsy-listing-step, #etsyDrawer, #etsyPill, #extensionStatusButton, .small-status > a[href='/api/extension/download']", false);
    setHidden("#previewEtsyButton, .advanced-etsy-api", TOOL_MODE === "amazon");
    // Renumber the reused step headers for the listing-only sequence (1 source -> 2 listing -> 3 VM).
    setFirstText(".etsy-listing-step .step-no", "2");
    setFirstText(".setup-etsy .step-no", "3");
    setFirstText(".setup-etsy strong", `Máy ảo ${marketplace}`);
    setFirstText(".etsy-listing-main strong", `Listing ảnh ${marketplace}`);
    setFirstText("#etsyDrawer summary span", `Cấu hình máy ảo ${marketplace}`);
    setFirstText(".mode-intro small", `Chọn cột Trello hoặc nhập SKU đã có ảnh output, rồi bấm Listing ảnh ${marketplace} bên dưới.`);
    if (els.autoProduct) {
      els.autoProduct.placeholder = `Dán link card Trello để đăng đúng card đó lên ${marketplace} — hoặc để trống lấy cột, hoặc nhập SKU...`;
    }
    return;
  }

  document.title = "Flow Etsy Console";
  setFirstText(".kicker", "Flow / Etsy");
  setFirstText(".topbar h1", "Làm theo từng bước");
  setHidden(".setup-flow, .setup-etsy, .check-step, .run-step, .auto-step, .etsy-listing-step, #flowDrawer, #etsyDrawer, #flowPill, #etsyPill, #extensionStatusButton, .small-status > a[href='/api/extension/download']", false);
  setHidden(".account-pick", false);
  setHidden("#previewEtsyButton, .advanced-etsy-api", false);
  if (els.autoProduct) {
    els.autoProduct.placeholder = "Dán link card Trello, hoặc để trống lấy cột, hoặc nhập tên sản phẩm...";
  }
}

function normalizeLookup(value) {
  return text(value, "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

// A pasted Trello card link (or bare card id) lets the user draft ONE specific card to Etsy
// without pre-configuring a column ("thay v\u00ec c\u00e0i c\u1ed1 \u0111\u1ecbnh"). The backend's explicit-card path
// already turns a card id/shortLink into a straight-to-Etsy draft when the card already has
// output images, so this is purely a frontend routing detail: send the ref as trello_card_id
// instead of using the box as a product-search query.
function parseTrelloCardRef(value) {
  const raw = text(value, "").trim();
  if (!raw) return "";
  // Full or partial Trello card URL: .../c/<shortLink>/<slug>
  const urlMatch = raw.match(/\/c\/([A-Za-z0-9]{6,})/);
  if (urlMatch) return urlMatch[1];
  // Bare 24-char hex card id (unambiguous; a product name never looks like this).
  if (/^[a-f0-9]{24}$/i.test(raw)) return raw;
  return "";
}

function parseTrelloCardRefs(value) {
  const tokens = text(value, "")
    .split(/[\s,]+/)
    .map((token) => token.trim())
    .filter(Boolean);
  const refs = [];
  const seen = new Set();
  for (const token of tokens) {
    const ref = parseTrelloCardRef(token);
    if (ref && !seen.has(ref)) {
      seen.add(ref);
      refs.push(ref);
    }
  }
  return refs;
}

// Paste a Trello BOARD link -> load that board's columns dynamically and let the user tick
// which columns to draft ("thay vì cài cố định"). The backend resolves the board id from the
// link and returns its open lists; we register each as a dynamic source so the existing
// multi-column draft path works unchanged.
async function loadBoardColumns(boardInput) {
  const board = text(boardInput, "");
  const query = board ? `?board=${encodeURIComponent(board)}` : "";
  const result = await api(`/api/trello/board/lists${query}`);
  if (!result?.ok) {
    boardColumnsLoaded = false;
    const missing = Array.isArray(result?.missing) ? result.missing.join(", ") : "";
    throw new Error(result?.error || (missing ? `thiếu ${missing}` : "không đọc được board"));
  }
  const lists = Array.isArray(result.lists) ? result.lists : [];
  if (!lists.length) {
    throw new Error("Board không có cột mở nào.");
  }
  renderBoardColumns(lists, result.board_id || board);
  logLine(
    `Đã load ${lists.length} cột từ board ${result.board_id || board}. Tick cột muốn đăng rồi bấm Listing ảnh Etsy.`
  );
  return result;
}

function renderBoardColumns(lists, boardId) {
  if (!els.autoSourceChecks) return;
  const board = text(boardId, DEFAULT_TRELLO_BOARD_ID);
  // Register each loaded column as a dynamic source keyed by its list id, mirroring the shape
  // of TRELLO_SOURCE_OPTIONS so selectedTrelloSourceKeys() / autoBatchPayload() / the whole
  // multi-column Etsy draft path keep working with no further changes.
  for (const col of lists) {
    const id = text(col.id, "");
    if (!id) continue;
    TRELLO_SOURCE_OPTIONS[id] = {
      label: text(col.name, id),
      product: "",
      listId: id,
      boardId: board,
    };
  }
  els.autoSourceChecks.innerHTML = lists
    .map((col) => {
      const id = text(col.id, "");
      if (!id) return "";
      const count = Number.isFinite(col.card_count) ? col.card_count : 0;
      const label = `${escapeHtml(text(col.name, id))}${count ? ` (${count})` : ""}`;
      return `<label class="source-check"><input type="checkbox" name="autoSource" value="${escapeHtml(
        id
      )}" /><span>${label}</span></label>`;
    })
    .filter(Boolean)
    .join("");
  boardColumnsLoaded = true;
  updateAutoSourceUi();
}

function readLastFlowRunContext() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(LAST_FLOW_RUN_STORAGE_KEY) || "{}");
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function rememberLastFlowRunContext(context = {}) {
  const next = {
    sourceKey: text(context.sourceKey, ""),
    sourceLabel: text(context.sourceLabel, ""),
    product: text(context.product, ""),
    cardId: text(context.cardId, ""),
    listId: text(context.listId, ""),
    jobId: text(context.jobId, ""),
    startedAt: Number(context.startedAt || Date.now()),
  };
  state.lastFlowRun = next;
  try {
    window.localStorage.setItem(LAST_FLOW_RUN_STORAGE_KEY, JSON.stringify(next));
  } catch {}
  renderEtsyListingAction(state.payload);
  return next;
}

function logLine(message, payload) {
  const stamp = new Date().toLocaleTimeString("vi-VN", { hour12: false });
  const next = [`[${stamp}] ${message}`];
  if (payload !== undefined) {
    next.push(typeof payload === "string" ? payload : JSON.stringify(payload, null, 2));
  }
  const current = els.consoleOutput.textContent.trim();
  els.consoleOutput.textContent = current && current !== "Sẵn sàng." ? `${next.join("\n")}\n\n${current}` : next.join("\n");
}

function showConsole() {
  if (els.consoleDrawer) {
    els.consoleDrawer.open = true;
  }
}

function compactQueueTask(task = {}) {
  const created = Date.parse(task.created_at || "");
  const ageSeconds = Number.isFinite(created) ? Math.max(0, Math.round((Date.now() - created) / 1000)) : null;
  const result = task.result || {};
  return {
    task_id: task.id || "",
    status: task.status || "",
    sku: task.sku || "",
    card: task.card_url || task.card_id || "",
    images: Number(task.image_count || 0),
    account: task.account_id || "",
    worker: task.worker_id || "",
    age_seconds: ageSeconds,
    error: task.error || result.error || result.message || result.reason || "",
  };
}

function vmQueueHint(queue = {}) {
  const tasks = Array.isArray(queue.tasks) ? queue.tasks : [];
  const active = tasks.find((task) => ["queued", "in_progress"].includes(task.status));
  if (!active) return "Queue VM đang trống.";
  if (active.status === "in_progress") {
    return `VM đã nhận task ${active.id || ""}${active.worker_id ? ` (${active.worker_id})` : ""}.`;
  }
  return "Task vẫn đang chờ VM. Nếu đứng lâu, kiểm tra VM proxy/tunnel và popup extension: Backend URL phải trỏ được tới backend này.";
}

function setVmQueueUi(queue = {}) {
  const queued = Number(queue.queued || 0);
  const inProgress = Number(queue.in_progress || 0);
  const latest = queue.latest || {};
  const latestCompact = compactQueueTask(latest);
  const marketplace = listingMarketplaceName();
  const active = Array.isArray(queue.tasks)
    ? queue.tasks.find((task) => ["queued", "in_progress"].includes(task.status))
    : null;
  if (els.etsyState) {
    if (inProgress) els.etsyState.textContent = "VM đang chạy";
    else if (queued) els.etsyState.textContent = "Chờ VM";
    else if (latest.status === "failed") els.etsyState.textContent = "VM lỗi";
    else els.etsyState.textContent = "Queue trống";
  }
  if (els.etsyDetail) {
    const sku = active?.sku || latest?.sku || "";
    els.etsyDetail.textContent = latest.status === "failed"
      ? `${marketplace} lỗi: ${latestCompact.error || "không rõ lỗi"}`
      : queued || inProgress
      ? `Queue ${marketplace}: ${queued} chờ, ${inProgress} đang chạy${sku ? ` · ${sku}` : ""}`
      : `Extension trên VM sẽ lấy task ${marketplace} Draft khi có hàng.`;
  }
  if (els.etsyConnectDot) {
    els.etsyConnectDot.className = `dot ${queued || inProgress ? "ok" : ""}`.trim();
  }
  if (els.etsyConnectLabel) {
    els.etsyConnectLabel.textContent = queued || inProgress
      ? `VM queue: ${queued} chờ, ${inProgress} đang chạy`
      : "VM queue đang trống";
  }
}

function logAutoRunResult(result = {}) {
  const mode = result.mode || "";
  if (mode === "flow_batch") {
    logLine(result.message || "Đã tạo batch Flow.", {
      mode,
      job_id: result.job?.id || "",
      status: result.job?.status || "",
      ready_for_ai: result.trello_status?.message || "",
    });
    return;
  }

  if (mode === "etsy_from_existing_outputs") {
    const tasks = Array.isArray(result.tasks) ? result.tasks : [];
    const queued = tasks.filter((task) => task.enqueued).length;
    const duplicates = tasks.filter((task) => task.duplicate).length;
    const compactTasks = tasks.map((task) => compactQueueTask(task.queue_task || {}));
    const waitingForVm = compactTasks.some((task) => task.status === "queued" && !task.worker);
    logLine(result.message || `Đã queue ${queued} Etsy Draft.`, {
      mode,
      queued,
      duplicates,
      ready_for_ai: result.trello_status?.message || "",
      tasks: compactTasks,
      next: waitingForVm
        ? "Đã queue vào backend; chờ extension trên VM polling và lưu Draft."
        : "Theo dõi queue để xem VM xử lý.",
    });
    return;
  }

  logLine(result.message || "Đã chạy Auto Trello một chạm.", {
    mode,
    ok: Boolean(result.ok),
    job_id: result.job?.id || "",
  });
}

function waitForExtensionResponse(payload, timeoutMs = 5000) {
  return new Promise((resolve, reject) => {
    const requestId =
      globalThis.crypto && typeof globalThis.crypto.randomUUID === "function"
        ? globalThis.crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const timer = window.setTimeout(() => {
      window.removeEventListener("message", onMessage);
      reject(new Error("Không thấy extension trả lời. Cài/reload extension mới, cấp quyền origin Cloudflare, rồi refresh trang."));
    }, timeoutMs);
    function onMessage(event) {
      if (event.source !== window || event.origin !== window.location.origin) return;
      const data = event.data || {};
      if (data.source !== "flow-ext" || data.type !== "RESPONSE" || data.requestId !== requestId) return;
      window.clearTimeout(timer);
      window.removeEventListener("message", onMessage);
      resolve(data.result || {});
    }
    window.addEventListener("message", onMessage);
    window.postMessage({ ...payload, requestId }, window.location.origin);
  });
}

function sendExternalExtensionMessage(extensionId, message, timeoutMs = 10000) {
  return new Promise((resolve, reject) => {
    if (!globalThis.chrome?.runtime?.sendMessage) {
      reject(new Error("Trang này chưa có chrome.runtime external messaging."));
      return;
    }
    const timer = window.setTimeout(() => reject(new Error(`External extension timeout: ${extensionId}`)), timeoutMs);
    chrome.runtime.sendMessage(extensionId, message, (result) => {
      window.clearTimeout(timer);
      const lastError = chrome.runtime.lastError;
      if (lastError) {
        reject(new Error(lastError.message));
        return;
      }
      resolve(result || {});
    });
  });
}

async function pingExternalExtension() {
  for (const extensionId of EXTERNAL_EXTENSION_IDS) {
    try {
      const result = await sendExternalExtensionMessage(extensionId, { type: "PING_EXT" }, 4000);
      if (result?.ok) {
        state.externalExtensionId = extensionId;
        return { ...result, external: true, extensionId };
      }
    } catch (_error) {
      // Try the next known extension id.
    }
  }
  return null;
}

async function ensureExtensionNonce() {
  if (state.extensionNonce) return state.extensionNonce;
  let result;
  try {
    result = await waitForExtensionResponse({ source: "flow-web", type: "PING_EXT" });
  } catch (error) {
    const external = await pingExternalExtension();
    if (external?.ok) {
      state.extensionNonce = "external";
      return state.extensionNonce;
    }
    throw error;
  }
  if (!result?.ok || !result?.nonce) {
    throw new Error(result?.message || "Extension chưa sẵn sàng trên trang này.");
  }
  state.extensionNonce = result.nonce;
  return state.extensionNonce;
}

async function extensionCommand(message) {
  const nonce = await ensureExtensionNonce();
  if (state.externalExtensionId) {
    return await sendExternalExtensionMessage(state.externalExtensionId, message, 30000);
  }
  let result = await waitForExtensionResponse({ source: "flow-web", nonce, message });
  if (result?.reason === "bad_nonce") {
    state.extensionNonce = "";
    const freshNonce = await ensureExtensionNonce();
    result = await waitForExtensionResponse({ source: "flow-web", nonce: freshNonce, message });
  }
  return result;
}

function summarizePreflight(result) {
  const lines = [result?.summary || (result?.ready ? "Sẵn sàng chạy." : "Còn mục cần xử lý.")];
  const blockers = Array.isArray(result?.blockers) ? result.blockers : [];
  const warnings = Array.isArray(result?.warnings) ? result.warnings : [];
  if (blockers.length) {
    lines.push("Blocker:");
    blockers.forEach((item) => lines.push(`- ${item.label}: ${item.detail || item.action || "cần xử lý"}`));
  }
  if (warnings.length) {
    lines.push("Cần tự kiểm:");
    warnings.forEach((item) => lines.push(`- ${item.label}: ${item.action || item.detail || "kiểm tra thủ công"}`));
  }
  const nextActions = Array.isArray(result?.next_actions) ? result.next_actions.filter(Boolean) : [];
  if (nextActions.length) {
    lines.push("Việc tiếp theo:");
    nextActions.forEach((item) => lines.push(`- ${item}`));
  }
  return lines.join("\n");
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof body === "object" ? body.detail || body.error || JSON.stringify(body) : body;
    throw new Error(detail || `HTTP ${response.status}`);
  }
  return body;
}

function jobStatusTone(status) {
  if (["completed", "ready", "ok"].includes(status)) return "ready";
  if (["queued", "running", "polling"].includes(status)) return "warn";
  if (["failed", "stopped", "cancelled"].includes(status)) return "bad";
  return "";
}

function isFlowReady(payload) {
  return Boolean(payload?.auth?.authenticated && payload?.config?.project_id);
}

function renderTopStatus(payload) {
  setBadge(els.healthPill, "Backend OK", "ready");

  if (isFlowReady(payload)) {
    setBadge(els.flowPill, "Flow ready", "ready");
    els.flowState.textContent = "Sẵn sàng";
    els.flowDetail.textContent = `Project ${text(payload.config.project_id)}`;
    if (els.flowSetupStatus) els.flowSetupStatus.textContent = "Đã setup";
    setToolBadge(els.flowBadge, "Ready", "ready");
  } else if (payload?.auth?.authenticated) {
    setBadge(els.flowPill, "Thiếu project", "warn");
    els.flowState.textContent = "Thiếu project";
    els.flowDetail.textContent = "Đã đăng nhập, chưa lưu project Flow";
    if (els.flowSetupStatus) els.flowSetupStatus.textContent = "Cần Project ID";
    setToolBadge(els.flowBadge, "Needs project", "warn");
  } else {
    setBadge(els.flowPill, "Cần login", "warn");
    els.flowState.textContent = "Cần đăng nhập";
    els.flowDetail.textContent = "Mở Flow rồi login Google";
    if (els.flowSetupStatus) els.flowSetupStatus.textContent = "Cần login";
    setToolBadge(els.flowBadge, "Login", "warn");
  }

  const etsy = payload?.etsy || {};
  const marketplace = listingMarketplaceName();
  setBadge(els.etsyPill, `VM ${marketplace}`, "ready");
  els.etsyState.textContent = "Queue VM";
  els.etsyDetail.textContent = `Extension trên máy ảo tự lấy task ${marketplace} và lưu Draft`;
  if (els.etsySetupStatus) els.etsySetupStatus.textContent = "Extension trên VM sẽ tự lấy queue";
  setToolBadge(els.etsyBadge, "VM queue", "ready");
  els.etsyWarning.hidden = false;
  els.etsyWarning.textContent = `Luồng chính không setup ${marketplace} ở máy này. Nút Chạy Flow chỉ tạo ảnh/Trello; nút Listing ảnh ${marketplace} mới gửi queue cho VM lưu Draft.`;
  renderEtsyConnect(etsy);

  const extension = payload?.extensions || {};
  const readyCount = Number(extension.ready_count || 0);
  const totalCount = Array.isArray(extension.items) ? extension.items.length : 0;
  els.extensionState.textContent = `${readyCount}/${totalCount || 0}`;
  els.extensionDetail.textContent = totalCount ? "tool sẵn sàng" : "chưa đọc registry";

  const trello = payload?.trello || {};
  if (els.trelloBadge) {
    els.trelloBadge.className = trello.configured ? "flow-route-badge ready" : "flow-route-badge warn";
    els.trelloBadge.textContent = trello.configured ? autoRouteLabel() : "Cần setup Trello trước";
  }
}

function renderEtsyConnect(etsy = {}) {
  const marketplace = listingMarketplaceName();
  if (els.etsyConnectDot) els.etsyConnectDot.className = "dot ok";
  if (els.etsyConnectLabel) {
    els.etsyConnectLabel.textContent = "VM extension polling queue";
  }
  if (els.disconnectEtsyButton) els.disconnectEtsyButton.hidden = true;
  const label = "Xem queue";
  if (els.connectEtsyButton) els.connectEtsyButton.textContent = label;
  if (els.connectEtsyTopButton) els.connectEtsyTopButton.textContent = label;
  const hint = document.querySelector(".connect-hint");
  if (hint) {
    hint.textContent = `Extension ${marketplace} nằm trên máy ảo và đang polling backend. Máy này không cần login ${marketplace}, không mở tab ${marketplace} local. Nút Listing ảnh ${marketplace} mới queue task để máy ảo tự copy listing và lưu Draft.`;
  }
}

function hydrateFlowForm(config = {}) {
  if (state.hydratedFlow) return;
  els.flowProjectId.value = text(config.project_id, "");
  els.flowProjectName.value = text(config.project_name, "");
  els.flowTimeout.value = String(config.generation_timeout_s || 300);
  els.flowCdpUrl.value = text(config.cdp_url, "");
  state.hydratedFlow = true;
}

function hydrateIntegrationForm(integrations = {}) {
  if (state.hydratedIntegrations) return;
  const gemini = integrations.gemini || {};
  if (els.geminiModel) {
    const model = text(gemini.image_model, "");
    els.geminiModel.value = model && model.includes("image") ? model : "gemini-2.5-flash-image";
  }
  if (els.imageEngineSelect) {
    const savedEngine = window.localStorage.getItem("flow-image-engine") || "";
    els.imageEngineSelect.value = savedEngine === "gemini_api" ? "gemini_api" : "google_flow";
  }
  state.hydratedIntegrations = true;
}

function hydrateEtsyForm(etsy = {}) {
  if (state.hydratedEtsy) return;
  els.etsyShopId.value = text(etsy.shop_id, "");
  els.etsyUserId.value = text(etsy.user_id, "");
  els.etsyTaxonomyId.value = text(etsy.taxonomy_id, "");
  els.etsyShippingProfileId.value = text(etsy.shipping_profile_id, "");
  els.etsyPrice.value = text(etsy.price, "9.99");
  els.etsyQuantity.value = String(etsy.quantity || 1);
  state.hydratedEtsy = true;
}

function renderJobs(payload) {
  const jobs = Array.isArray(payload?.jobs) ? [...payload.jobs] : [];
  const active = jobs.filter((job) => ["queued", "running", "polling"].includes(job.status)).length;
  const failed = jobs.filter((job) => ["failed", "stopped"].includes(job.status)).length;
  els.jobState.textContent = String(jobs.length);
  els.jobDetail.textContent = `${active} active, ${failed} cần xem`;

  const recent = jobs.slice(0, 20);
  if (!recent.length) {
    els.jobsList.innerHTML = `<div class="empty">Chưa có job.</div>`;
    return;
  }

  els.jobsList.innerHTML = recent
    .map((job) => {
      const title = text(job.title || job.input?.title || job.type, "Untitled");
      const status = text(job.status, "unknown");
      const count = Array.isArray(job.artifacts) ? job.artifacts.length : 0;
      const canQueueEtsy = jobCanQueueEtsy(job);
      return `
        <article class="job-card">
          <div class="job-main">
            <strong title="${escapeHtml(job.error || job.progress_snapshot?.detail || "")}">${escapeHtml(title)}</strong>
            <small>${escapeHtml(job.id || "")}</small>
          </div>
          <div class="job-side">
            <span class="tool-badge ${jobStatusTone(status)}">${escapeHtml(status)}${count ? ` · ${count}` : ""}</span>
            ${
              canQueueEtsy
                ? `<button class="job-etsy-button" type="button" data-action="queue-etsy" data-job-id="${escapeHtml(job.id || "")}">Listing ảnh ${escapeHtml(listingMarketplaceName())}</button>`
                : ""
            }
          </div>
        </article>
      `;
    })
    .join("");
}

function jobCanQueueEtsy(job = {}) {
  const input = job.input || {};
  const artifacts = Array.isArray(job.artifacts) ? job.artifacts : [];
  const cardId = text(input.trello_source_card_id || input.trello_card_id, "");
  return job.type === "image" && job.status === "completed" && artifacts.length > 0 && Boolean(cardId);
}

function jobMatchesEtsyContext(job = {}, context = {}) {
  if (!jobCanQueueEtsy(job)) return false;
  const input = job.input || {};
  const jobCard = text(input.trello_source_card_id || input.trello_card_id, "");
  const jobList = text(input.trello_list_id, "");
  const jobProduct = normalizeLookup(
    [
      input.prompt_product,
      input.prompt_product_key,
      input.title,
      job.title,
    ].filter(Boolean).join(" ")
  );
  const cardId = text(context.cardId, "");
  const listId = text(context.listId, "");
  const product = normalizeLookup(context.product || "");

  if (cardId) return jobCard === cardId;
  if (product) return jobProduct.includes(product);
  if (context.allowListOnly && listId) return jobList === listId;
  return false;
}

function latestQueueableEtsyJob(payload = state.payload) {
  const jobs = Array.isArray(payload?.jobs) ? payload.jobs : [];
  const queueable = jobs.filter((job) => jobCanQueueEtsy(job));
  const source = selectedTrelloSource();
  const sourceKey = selectedTrelloSourceKey();
  const typedProduct = text(els.autoProduct?.value, "");
  const sourceContext = {
    sourceKey,
    product: typedProduct || source.product || "",
    cardId: source.cardId || "",
    listId: source.listId || "",
    allowListOnly: false,
  };
  const lastRun = state.lastFlowRun || {};

  if (lastRun.jobId) {
    const exactJob = queueable.find((job) => job.id === lastRun.jobId);
    if (exactJob) return exactJob;
  }

  if (lastRun.sourceKey === sourceKey) {
    const startedAt = Number(lastRun.startedAt || 0);
    const minCreatedAt = startedAt ? startedAt - 60_000 : 0;
    const runContext = {
      product: lastRun.product || sourceContext.product,
      cardId: lastRun.cardId || sourceContext.cardId,
      listId: lastRun.listId || sourceContext.listId,
      allowListOnly: true,
    };
    const fromCurrentRun = queueable.find((job) => {
      const createdAt = Date.parse(job.created_at || job.updated_at || "");
      return Number.isFinite(createdAt)
        && createdAt >= minCreatedAt
        && jobMatchesEtsyContext(job, runContext);
    });
    if (fromCurrentRun) return fromCurrentRun;
  }

  return queueable.find((job) => jobMatchesEtsyContext(job, sourceContext)) || null;
}

function renderEtsyListingAction(payload) {
  if (!els.listLatestEtsyButton || !els.latestEtsyHint) return;
  const marketplace = listingMarketplaceName();
  setFirstText(".etsy-listing-main strong", `Listing ảnh ${marketplace}`);
  const cardRefs = parseTrelloCardRefs(els.autoProduct?.value);
  if (cardRefs.length) {
    // A pasted card link bypasses column config entirely: draft exactly that/those card(s).
    const trelloReady = Boolean(state.payload?.trello?.configured);
    els.listLatestEtsyButton.disabled = !trelloReady;
    els.latestEtsyHint.textContent = trelloReady
      ? `Lấy ${cardRefs.length} card từ link Trello -> ${marketplace} Draft`
      : `Cấu hình Trello trước khi gửi link card sang ${marketplace} Draft`;
    return;
  }
  if (boardColumnsLoaded && !document.querySelector("input[name='autoSource']:checked")) {
    // A board's columns are loaded but none ticked yet — prompt for a selection.
    els.listLatestEtsyButton.disabled = true;
    els.latestEtsyHint.textContent = `Tick ít nhất 1 cột vừa load để gửi ${marketplace} Draft`;
    return;
  }
  const sourceKeys = selectedTrelloSourceKeys();
  const multiColumn = sourceKeys.length > 1;
  const job = multiColumn ? null : latestQueueableEtsyJob(payload);
  const source = selectedTrelloSource();
  const product = text(els.autoProduct?.value || source.product, "");
  // Whole-column drafting only needs a list id (always present for a picked column); a
  // typed product/cardId also works. So the button stays clickable whenever a column is
  // selected and Trello is configured.
  const canCheckTrello = Boolean(
    state.payload?.trello?.configured && (multiColumn || source.cardId || product || source.listId)
  );
  els.listLatestEtsyButton.disabled = !job && !canCheckTrello;
  if (job) {
    const title = text(job.title || job.input?.title || job.id, "job Flow đã xong");
    const count = Array.isArray(job.artifacts) ? job.artifacts.length : 0;
    const countLabel = count && !title.includes(`${count} ảnh`) ? ` · ${count} ảnh` : "";
    els.latestEtsyHint.textContent = `${title}${countLabel} -> ${marketplace} Draft`;
  } else if (multiColumn) {
    const labels = sourceKeys.map((key) => TRELLO_SOURCE_OPTIONS[key]?.label || key).join(", ");
    els.latestEtsyHint.textContent = `Kiểm ${sourceKeys.length} cột (${labels}); card nào có ảnh thì gửi ${marketplace} Draft`;
  } else if (canCheckTrello) {
    els.latestEtsyHint.textContent = `Kiểm Trello ${product || source.label}; nếu đã có ảnh thì gửi ${marketplace} Draft`;
  } else {
    els.latestEtsyHint.textContent = product
      ? `Chưa có ảnh Flow xong cho ${product}`
      : `Nhập SKU/tên sản phẩm hoặc chạy Flow trước khi gửi ${marketplace} Draft`;
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderState(payload) {
  state.payload = payload || {};
  hydrateFlowForm(state.payload.config || {});
  hydrateIntegrationForm(state.payload.integrations || {});
  hydrateEtsyForm(state.payload.etsy || {});
  renderTopStatus(state.payload);
  renderJobs(state.payload);
  renderEtsyListingAction(state.payload);
}

async function refreshState({ quiet = false } = {}) {
  try {
    const payload = await api("/api/state");
    renderState(payload);
    if (!quiet) logLine("Đã refresh state.");
  } catch (error) {
    setBadge(els.healthPill, "Backend lỗi", "bad");
    logLine(`Refresh lỗi: ${error.message}`);
  }
}

async function withBusy(button, label, task) {
  const oldText = button.textContent;
  const oldHtml = button.innerHTML;
  button.disabled = true;
  button.textContent = label;
  try {
    return await task();
  } catch (error) {
    logLine(`${oldText} lỗi: ${error.message}`);
    return null;
  } finally {
    button.disabled = false;
    button.innerHTML = oldHtml || oldText;
  }
}

function baseAutomationGraph(options = {}) {
  const config = typeof options === "boolean" ? { includeEtsy: options } : (options || {});
  const includeEtsy = Boolean(config.includeEtsy);
  const includeAmazon = Boolean(config.includeAmazon);
  const includeListing = includeEtsy || includeAmazon;
  const includeTrello = config.includeTrello !== false;
  const etsyMode = text(config.etsyMode, "browser_copy");
  const imageCount = clampInt(config.imageCount, 1, 4, 4);
  const imageEngine = config.imageEngine === "gemini_api" ? "gemini_api" : selectedImageEngine();
  const flowAgentEnabled = imageEngine !== "gemini_api";
  const modules = [
    { id: "master-bot", type: "master_bot", title: "Master Bot", enabled: true },
  ];
  if (includeTrello) {
    modules.push({ id: "trello-source", type: "trello_source", title: "Trello Image Source", enabled: true });
  }
  modules.push({
    id: "flow",
    type: "flow",
    title: imageEngine === "gemini_api" ? "Gemini API Images" : "Google Flow",
    enabled: true,
    settings: {
      imageCount,
      imageEngine,
      flowAgentEnabled,
      flowAgentAutoApprove: flowAgentEnabled,
    },
  });
  if (includeTrello) {
    modules.push({ id: "trello-archive", type: "trello", title: "Trello Archive", enabled: true });
  }
  if (includeEtsy) {
    if (etsyMode === "api_draft") {
      modules.push({ id: "etsy", type: "etsy", title: "Etsy API Draft", enabled: true });
    } else {
      modules.push({
        id: "etsy-copy",
        type: "etsy_browser_copy",
        title: "Etsy Copy Listing",
        enabled: true,
        settings: { keepColorChart: true, deleteExistingImages: true },
      });
    }
  }
  if (includeAmazon) {
    modules.push({
      id: "amazon-copy",
      type: "amazon_browser_copy",
      title: "Amazon Copy Listing",
      enabled: true,
      settings: { deleteExistingImages: true },
    });
  }
  const edges = [];
  if (includeTrello) {
    edges.push(
      { source: "master-bot", target: "trello-source", condition: "success" },
      { source: "trello-source", target: "flow", condition: "success" },
    );
  } else {
    edges.push({ source: "master-bot", target: "flow", condition: "success" });
  }
  const listingTarget = includeAmazon ? "amazon-copy" : (etsyMode === "api_draft" ? "etsy" : "etsy-copy");
  if (includeListing && includeTrello) {
    edges.push({ source: "flow", target: "trello-archive", condition: "success" });
    edges.push({ source: "trello-archive", target: listingTarget, condition: "success" });
  } else if (includeListing) {
    edges.push({ source: "flow", target: listingTarget, condition: "success" });
  } else if (includeTrello) {
    edges.push({ source: "flow", target: "trello-archive", condition: "success" });
  }
  return {
    version: 1,
    selected_module_id: "flow",
    modules,
    edges,
  };
}

function quickJobPayload() {
  const prompt = text(
    els.quickPrompt.value,
    "Tạo bộ ảnh sản phẩm thương mại, nền sáng, giữ đúng hình dáng, chất liệu và chi tiết chính từ ảnh nguồn."
  );
  const trelloEnabled = Boolean(els.quickTrelloEnabled.checked);
  const imageCount = clampInt(els.imageCount.value, 1, 4, 4);
  const imageEngine = selectedImageEngine();
  const flowAgentEnabled = imageEngine !== "gemini_api";
  const etsy = state.payload.etsy || {};
  return {
    type: "image",
    title: "Quick Flow image set",
    prompt,
    count: imageCount,
    image_engine: imageEngine,
    aspect: els.aspectSelect.value || "square",
    trello_enabled: trelloEnabled,
    etsy_enabled: false,
    etsy_browser_copy_enabled: false,
    etsy_publish: false,
    amazon_enabled: false,
    amazon_browser_copy_enabled: false,
    amazon_publish: false,
    flow_agent_enabled: flowAgentEnabled,
    flow_agent_auto_approve: flowAgentEnabled,
    automation_graph: baseAutomationGraph({ includeEtsy: false, includeTrello: trelloEnabled, imageCount, imageEngine }),
    etsy_price: text(els.etsyPrice.value || etsy.price, ""),
    etsy_quantity: clampInt(els.etsyQuantity.value || etsy.quantity, 1, 999, 1),
    etsy_taxonomy_id: text(els.etsyTaxonomyId.value || etsy.taxonomy_id, ""),
    etsy_shipping_profile_id: text(els.etsyShippingProfileId.value || etsy.shipping_profile_id, ""),
  };
}

function autoBatchPayload(sourceKey) {
  const source =
    sourceKey && TRELLO_SOURCE_OPTIONS[sourceKey] ? TRELLO_SOURCE_OPTIONS[sourceKey] : selectedTrelloSource();
  // Empty product box = run the whole selected column (per the field's placeholder).
  // Do NOT fall back to source.product (the column name), or it becomes a search
  // query that matches zero cards and the backend rejects the run with a 400.
  const product = text(els.autoProduct.value, "");
  const includeEtsy = false;
  const imageEngine = selectedImageEngine();
  const flowAgentEnabled = imageEngine !== "gemini_api";
  const trelloBoard = text(source.boardId || state.payload.trello?.board_id || DEFAULT_TRELLO_BOARD_ID, DEFAULT_TRELLO_BOARD_ID);
  return {
    title: "Auto Trello Flow",
    limit: clampInt(els.autoLimit.value, 1, 100, 40),
    auto_trello: true,
    continuous: Boolean(els.autoContinuous.checked),
    run_until_empty: Boolean(els.autoContinuous.checked),
    create_etsy_draft: false,
    poll_interval_s: 30,
    items: [],
    job: {
      type: "image",
      title: "Auto AI Trello",
      prompt: text(
        els.quickPrompt.value,
        imageEngine === "gemini_api"
          ? "Tự phân tích ảnh nguồn Trello và tạo bộ ảnh sản phẩm thương mại đúng sản phẩm."
          : "Flow Agent tự phân tích ảnh nguồn Trello, viết prompt và tạo bộ ảnh sản phẩm."
      ),
      count: 4,
      image_engine: imageEngine,
      aspect: "square",
      trello_enabled: true,
      etsy_enabled: includeEtsy,
      etsy_browser_copy_enabled: includeEtsy,
      etsy_publish: false,
      etsy_keep_color_chart: true,
      etsy_delete_existing_images: true,
      amazon_enabled: false,
      amazon_browser_copy_enabled: false,
      amazon_publish: false,
      amazon_delete_existing_images: true,
      flow_agent_enabled: flowAgentEnabled,
      flow_agent_auto_approve: flowAgentEnabled,
      trello_board_id: trelloBoard,
      trello_list_id: source.listId,
      trello_card_id: source.cardId || "",
      trello_source_card_id: source.cardId || "",
      prompt_product: product,
      prompt_product_key: product,
      prompt_notes: product ? `Trello search trong ${source.label}: ${product}` : "",
      automation_graph: baseAutomationGraph({ includeEtsy, includeTrello: true, imageCount: 4, imageEngine }),
    },
  };
}

async function runPreflight() {
  const payload = {
    instruction: text(els.quickPrompt.value, "Kiểm tra trạng thái Flow/Etsy/Trello trước khi chạy."),
    auto_trello: true,
    continuous: Boolean(els.autoContinuous.checked),
    limit: clampInt(els.autoLimit.value, 0, 100, 0),
    create_etsy_draft: false,
  };
  const result = await api("/api/master-bot/preflight", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  logLine(result.ready ? "Preflight OK." : "Preflight còn blocker.", summarizePreflight(result));
  return result;
}

async function saveEtsy() {
  const payload = {
    api_key: els.etsyApiKey.value.trim(),
    api_secret: els.etsyApiSecret.value.trim(),
    user_id: els.etsyUserId.value.trim(),
    shop_id: els.etsyShopId.value.trim(),
    taxonomy_id: els.etsyTaxonomyId.value.trim(),
    shipping_profile_id: els.etsyShippingProfileId.value.trim(),
    quantity: clampInt(els.etsyQuantity.value, 1, 999, 1),
    price: text(els.etsyPrice.value, "9.99"),
  };
  const result = await api("/api/integrations/etsy", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  els.etsyApiKey.value = "";
  els.etsyApiSecret.value = "";
  state.hydratedEtsy = false;
  logLine("Đã lưu Etsy.", result);
  await refreshState({ quiet: true });
}

function accountStatusNote(text, tone = "") {
  if (!els.accountStatus) return;
  els.accountStatus.hidden = !text;
  els.accountStatus.textContent = text || "";
  els.accountStatus.className = `status${tone ? ` ${tone}` : ""}`;
}

function selectedEtsyAccountId() {
  return String(els.autoAccountSelect?.value || "").trim();
}

function renderEtsyAccounts(snapshot = {}) {
  state.etsyAccounts = {
    accounts: Array.isArray(snapshot.accounts) ? snapshot.accounts : [],
    default_slug: snapshot.default_slug || "",
  };
  const accounts = state.etsyAccounts.accounts;

  // Keep the one-click selector in sync (preserve current pick if still valid).
  if (els.autoAccountSelect) {
    const current = els.autoAccountSelect.value;
    const options = accounts.map((acc) => {
      const slug = acc.is_default ? "" : String(acc.slug || "");
      const label = acc.is_default
        ? "Mặc định (trung6)"
        : `${acc.label || acc.slug} (${acc.slug})`;
      return `<option value="${escapeHtml(slug)}">${escapeHtml(label)}</option>`;
    });
    // Always ensure a default option exists even before the first load resolves.
    if (!accounts.some((acc) => acc.is_default)) {
      options.unshift('<option value="">Mặc định (trung6)</option>');
    }
    els.autoAccountSelect.innerHTML = options.join("");
    const stillValid = Array.from(els.autoAccountSelect.options).some((opt) => opt.value === current);
    els.autoAccountSelect.value = stillValid ? current : "";
  }

  if (!els.accountsList) return;
  if (!accounts.length) {
    els.accountsList.innerHTML = '<p class="account-empty">Chưa có tài khoản nào.</p>';
    return;
  }
  els.accountsList.innerHTML = accounts
    .map((acc) => {
      const isDefault = Boolean(acc.is_default);
      const slug = isDefault ? "" : String(acc.slug || "");
      const name = isDefault ? "Mặc định (trung6)" : `${acc.label || acc.slug}`;
      const board = acc.trello_board_id || "(global)";
      const list = acc.trello_list_id || "(cả board)";
      const shop = acc.etsy_shop_id || "-";
      const enabled = acc.enabled === false ? " · TẮT" : "";
      const del = isDefault
        ? ""
        : `<button class="link-button" type="button" data-action="del-account" data-slug="${escapeHtml(slug)}">Xoá</button>`;
      return `<div class="account-row">
        <div class="account-meta">
          <strong>${escapeHtml(name)}</strong>
          <small>slug: <code>${escapeHtml(slug || "(default)")}</code>${escapeHtml(enabled)}</small>
          <small>board: <code>${escapeHtml(board)}</code> · list: <code>${escapeHtml(list)}</code> · shop: <code>${escapeHtml(shop)}</code></small>
        </div>
        <div class="account-actions">${del}</div>
      </div>`;
    })
    .join("");
}

async function loadEtsyAccounts({ quiet = true } = {}) {
  try {
    const data = await api("/api/etsy/accounts");
    renderEtsyAccounts(data.etsy_accounts || {});
    if (!quiet) logLine("Đã tải danh sách tài khoản Etsy.");
  } catch (error) {
    if (!quiet) logLine(`Tải tài khoản Etsy lỗi: ${error.message}`);
  }
}

async function upsertEtsyAccount() {
  const slug = text(els.accSlug?.value, "");
  if (!slug) {
    accountStatusNote("Nhập slug cho tài khoản (vd: shop-2).", "error");
    return;
  }
  const payload = {
    slug,
    label: text(els.accLabel?.value, ""),
    trello_board_id: text(els.accBoard?.value, ""),
    trello_list_id: text(els.accList?.value, ""),
    etsy_shop_id: text(els.accShop?.value, ""),
    enabled: true,
  };
  try {
    const data = await api("/api/etsy/accounts", { method: "POST", body: JSON.stringify(payload) });
    renderEtsyAccounts(data.etsy_accounts || {});
    accountStatusNote(`Đã lưu tài khoản "${slug}".`, "success");
    if (els.accSlug) els.accSlug.value = "";
    if (els.accLabel) els.accLabel.value = "";
    if (els.accBoard) els.accBoard.value = "";
    if (els.accList) els.accList.value = "";
    if (els.accShop) els.accShop.value = "";
    logLine(`Đã thêm/cập nhật tài khoản Etsy "${slug}".`);
  } catch (error) {
    accountStatusNote(error.message || "Lưu tài khoản thất bại.", "error");
  }
}

async function deleteEtsyAccount(slug) {
  if (!slug) return;
  try {
    const data = await api("/api/etsy/accounts/delete", { method: "POST", body: JSON.stringify({ slug }) });
    renderEtsyAccounts(data.etsy_accounts || {});
    accountStatusNote(`Đã xoá tài khoản "${slug}".`, "success");
    logLine(`Đã xoá tài khoản Etsy "${slug}".`);
  } catch (error) {
    accountStatusNote(error.message || "Xoá tài khoản thất bại.", "error");
  }
}

async function queueEtsyForAccount(accountId) {
  // Multi-account one-click: the board/list come from the account registry on
  // the backend, so we deliberately clear board/list/card scoping and let the
  // server resolve them. Tasks get stamped with this account_id -> only that
  // machine's worker claims them.
  const acc = (state.etsyAccounts.accounts || []).find((a) => String(a.slug || "") === accountId);
  const label = acc ? acc.label || acc.slug : accountId;
  const payload = autoBatchPayload(selectedTrelloSourceKeys()[0] || "");
  payload.create_etsy_draft = true;
  payload.etsy_only = true;
  payload.continuous = false;
  payload.run_until_empty = false;
  payload.limit = clampInt(els.autoLimit?.value, 0, 100, 0);
  payload.title = `Auto Trello -> Etsy (${label})`;
  payload.job.etsy_enabled = true;
  payload.job.etsy_browser_copy_enabled = true;
  payload.job.etsy_publish = false;
  payload.job.etsy_account_id = accountId;
  payload.job.trello_board_id = "";
  payload.job.trello_list_id = "";
  payload.job.trello_card_id = "";
  payload.job.trello_source_card_id = "";
  payload.job.prompt_product = "";
  payload.job.prompt_product_key = "";

  const result = await api("/api/jobs/auto-trello-one-click", { method: "POST", body: JSON.stringify(payload) });
  if (result.mode === "flow_batch" || result.mode === "explicit_trello_card") {
    logLine(`Tài khoản ${label}: card chưa đủ ảnh output để Listing Etsy; thêm ảnh vào board của tài khoản này trước.`);
    throw new Error("Card của tài khoản này chưa có ảnh để Listing Etsy.");
  }
  const tasks = result.tasks || [];
  const queued = tasks.filter((task) => task.enqueued && !task.duplicate).length;
  const duplicate = tasks.filter((task) => task.duplicate).length;
  logLine(`Đã queue Etsy Draft cho tài khoản ${label}: ${queued} mới, ${duplicate} trùng.`, {
    mode: result.mode,
    account: accountId,
    message: result.message || "",
    tasks: tasks.map((task) => ({
      card_id: task.card_id || "",
      card_name: task.card_name || "",
      enqueued: Boolean(task.enqueued),
      duplicate: Boolean(task.duplicate),
      queue_task: compactQueueTask(task.queue_task || {}),
    })),
  });
  if (!queued && !duplicate) {
    throw new Error(`Tài khoản ${label}: không có card nào đủ ảnh để Listing Etsy.`);
  }
  const queue = await inspectEtsyQueue();
  logLine(vmQueueHint(queue));
  await refreshState({ quiet: true });
  return result;
}

async function inspectEtsyQueue() {
  const marketplace = listingMarketplaceName();
  const queue = await api(listingQueueEndpoint());
  const tasks = Array.isArray(queue.tasks) ? queue.tasks : [];
  const completed = tasks.filter((task) => task.status === "completed").length;
  const failed = tasks.filter((task) => task.status === "failed").length;
  const summary = `${Number(queue.queued || 0)} chờ, ${Number(queue.in_progress || 0)} đang chạy, ${completed} xong, ${failed} lỗi`;
  setVmQueueUi(queue);
  logLine(`Queue VM ${marketplace}: ${summary}.`, compactQueueTask(queue.latest || {}));
  return queue;
}

async function connectEtsy() {
  return inspectEtsyQueue();
}

async function disconnectEtsy() {
  const result = await api("/api/integrations/etsy", {
    method: "PUT",
    body: JSON.stringify({ clear_credentials: true }),
  });
  state.hydratedEtsy = false;
  logLine("Đã ngắt kết nối Etsy.", result);
  await refreshState({ quiet: true });
}

async function saveFlowConfig() {
  const current = state.payload.config || {};
  const payload = {
    project_id: els.flowProjectId.value.trim(),
    project_name: els.flowProjectName.value.trim(),
    active_workflow_id: text(current.active_workflow_id, ""),
    headless: Boolean(current.headless),
    cdp_url: els.flowCdpUrl.value.trim(),
    generation_timeout_s: clampInt(els.flowTimeout.value, 60, 3600, 300),
    poll_interval_s: Number(current.poll_interval_s || 5),
    output_dir: text(current.output_dir, ""),
  };
  const result = await api("/api/config", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  state.hydratedFlow = false;
  logLine("Đã lưu Flow.", result);
  await refreshState({ quiet: true });
}

async function saveGeminiConfig() {
  const payload = {
    gemini_api_key: els.geminiApiKey.value.trim(),
    gemini_image_model: text(els.geminiModel.value, "gemini-2.5-flash-image"),
  };
  const result = await api("/api/integrations/settings", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  els.geminiApiKey.value = "";
  state.hydratedIntegrations = false;
  logLine("Đã lưu Gemini.", result);
  await refreshState({ quiet: true });
}

async function previewEtsy() {
  const result = await api("/api/etsy/preview", {
    method: "POST",
    body: JSON.stringify(quickJobPayload()),
  });
  logLine("Preview Etsy.", result);
}

async function runEtsyBrowserCopy() {
  const marketplace = listingMarketplaceName();
  const payload = quickJobPayload();
  applyListingJobFlags(payload);
  const prepare = await api(listingEnqueueEndpoint(), {
    method: "POST",
    body: JSON.stringify({ ...payload, source_job_id: `manual-${Date.now()}` }),
  });
  const copy = prepare[listingCopyResultKey()] || {};
  logLine(`Đã đưa ${marketplace} browser copy vào queue.`, copy);
  if (!copy.enqueued || !copy.browser_automation_ready || !copy.automation_payload) {
    const missing = Array.isArray(copy.missing) && copy.missing.length ? ` Thiếu: ${copy.missing.join(", ")}` : "";
    throw new Error(`${marketplace} browser copy chưa sẵn sàng để queue.${missing}`);
  }
  logLine("VM extension sẽ tự polling queue này.", `Không mở ${marketplace} ở máy local để tránh nhầm profile hoặc logout.`);
  await refreshState({ quiet: true });
  return copy;
}

async function queueEtsyFromFlowJob(jobId) {
  const marketplace = listingMarketplaceName();
  const result = await api(listingJobEnqueueEndpoint(jobId), {
    method: "POST",
    body: "{}",
  });
  const copy = result[listingCopyResultKey()] || {};
  const queueTask = compactQueueTask(copy.queue_task || {});
  logLine(
    copy.enqueued
      ? `Đã queue Listing ảnh ${marketplace} từ job Flow.`
      : `Listing ảnh ${marketplace} chưa queue được.`,
    {
      job_id: jobId,
      enqueued: Boolean(copy.enqueued),
      duplicate: Boolean(copy.duplicate),
      title: copy.title || "",
      sku: copy.sku || "",
      images: copy.image_count || 0,
      missing: copy.missing || [],
      queue_task: queueTask,
      next: copy.enqueued
        ? `VM ${marketplace} sẽ polling task này, copy listing và lưu Draft.`
        : "Kiểm tra job đã archive ảnh Flow lên đúng Trello card chưa.",
    }
  );
  const queue = await inspectEtsyQueue();
  logLine(vmQueueHint(queue));
  await refreshState({ quiet: true });
  setVmQueueUi(queue);
  return copy;
}

async function queueEtsyFromTrelloOutputs() {
  // Multi-account: a non-default account draws cards from its OWN registered
  // Trello board (resolved server-side), not the default-board column picker.
  const marketplace = listingMarketplaceName();
  const isAmazon = listingMarketplaceKey() === "amazon";
  const accountId = isAmazon ? "" : selectedEtsyAccountId();
  if (accountId) {
    return queueEtsyForAccount(accountId);
  }
  // "Chọn cột rồi bấm" — draft every image-ready card in each selected column. One or
  // many columns. A typed SKU/product only makes sense for a single column; with several
  // columns picked we always run whole-column drafts (query stays empty so the backend
  // drafts all complete cards in the column instead of doing a zero-match name search).
  const sourceKeys = selectedTrelloSourceKeys();
  const typedProduct = text(els.autoProduct?.value, "");
  const multiColumn = sourceKeys.length > 1;
  const limit = clampInt(els.autoLimit?.value, 0, 100, 0);

  const summary = { columns: [], totalQueued: 0, totalDuplicate: 0, anyOk: false };

  for (const sourceKey of sourceKeys) {
    const source = TRELLO_SOURCE_OPTIONS[sourceKey];
    if (!source) continue;
    const product = multiColumn ? "" : typedProduct;
    if (!source.cardId && !product && !source.listId) continue;

    const payload = autoBatchPayload(sourceKey);
    payload.create_etsy_draft = true;
    payload.etsy_only = true;
    payload.continuous = false;
    payload.run_until_empty = false;
    payload.limit = limit;
    applyListingJobFlags(payload.job);
    payload.job.automation_graph = baseAutomationGraph({
      includeEtsy: !isAmazon,
      includeAmazon: isAmazon,
      includeTrello: true,
      imageCount: 4,
      imageEngine: selectedImageEngine(),
    });
    // Keep the query empty for a whole-column run (scoped by trello_list_id). Only a real
    // SKU/product typed by the user against a single column becomes a search query.
    payload.job.prompt_product = product;
    payload.job.prompt_product_key = product;
    if (source.cardId && !multiColumn) {
      payload.job.trello_card_id = source.cardId;
      payload.job.trello_source_card_id = source.cardId;
    } else {
      // Whole-column draft: clear card scoping so the backend drafts every image-ready card.
      payload.job.trello_card_id = "";
      payload.job.trello_source_card_id = "";
    }

    let result;
    try {
      result = await api("/api/jobs/auto-trello-one-click", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    } catch (err) {
      // A "nothing to draft" 400 for one column must not abort the remaining columns.
      const message = err?.message || String(err);
      summary.columns.push({ label: source.label, queued: 0, duplicate: 0, error: message });
      logLine(`Cột ${source.label}: ${message}`);
      continue;
    }
    if (result.mode === "flow_batch" || result.mode === "explicit_trello_card") {
      summary.columns.push({ label: source.label, queued: 0, duplicate: 0, error: "chưa đủ ảnh output" });
      logLine(`Cột ${source.label}: chưa đủ ảnh output để Listing ${marketplace}; hãy chạy Flow trước.`);
      continue;
    }

    const tasks = result.tasks || [];
    const queued = tasks.filter((task) => task.enqueued && !task.duplicate).length;
    const duplicate = tasks.filter((task) => task.duplicate).length;
    summary.anyOk = summary.anyOk || Boolean(result.ok);
    summary.totalQueued += queued;
    summary.totalDuplicate += duplicate;
    summary.columns.push({ label: source.label, queued, duplicate, error: "" });
    logLine(`Đã kiểm Trello và queue ${marketplace} Draft: ${source.label}.`, {
      mode: result.mode,
      message: result.message || "",
      source: source.label,
      product,
      tasks: tasks.map((task) => ({
        card_id: task.card_id || "",
        card_name: task.card_name || "",
        enqueued: Boolean(task.enqueued),
        duplicate: Boolean(task.duplicate),
        missing: task.missing || [],
        queue_task: compactQueueTask(task.queue_task || {}),
      })),
    });
  }

  if (!summary.columns.length) {
    throw new Error(`Chọn ít nhất 1 cột (hoặc nhập SKU/tên sản phẩm) để Listing ${marketplace}.`);
  }
  if (!summary.totalQueued) {
    if (summary.totalDuplicate) {
      logLine(`Tất cả ${summary.totalDuplicate} card đã được đưa sang ${marketplace} Draft trước đó; không queue trùng.`);
      await refreshState({ quiet: true });
      return summary;
    }
    throw new Error(`Không có card nào đủ ảnh output để đẩy sang ${marketplace} Draft (hãy chạy Flow trước).`);
  }

  const columnsLabel = summary.columns.map((column) => column.label).join(", ");
  logLine(
    `Tổng: queue ${summary.totalQueued} card mới sang ${marketplace} Draft từ ${summary.columns.length} cột (${columnsLabel})` +
      (summary.totalDuplicate ? `, bỏ qua ${summary.totalDuplicate} card đã Draft.` : ".")
  );
  const queue = await inspectEtsyQueue();
  logLine(vmQueueHint(queue));
  await refreshState({ quiet: true });
  setVmQueueUi(queue);
  return summary;
}

async function queueEtsyFromCardRefs(refs) {
  // "Dán link card -> listing" — draft each specific Trello card the user pasted, regardless of
  // which column is checked. The backend explicit-card path drafts straight to Etsy when the
  // card already has output images (no Flow re-run); a card without images returns a clean 400.
  const marketplace = listingMarketplaceName();
  const isAmazon = listingMarketplaceKey() === "amazon";
  const summary = { total: refs.length, queued: 0, duplicate: 0, failed: 0, items: [] };
  for (const ref of refs) {
    const payload = autoBatchPayload(selectedTrelloSourceKey());
    payload.create_etsy_draft = true;
    payload.etsy_only = true;
    payload.continuous = false;
    payload.run_until_empty = false;
    payload.limit = 1;
    applyListingJobFlags(payload.job);
    payload.job.automation_graph = baseAutomationGraph({
      includeEtsy: !isAmazon,
      includeAmazon: isAmazon,
      includeTrello: true,
      imageCount: 4,
      imageEngine: selectedImageEngine(),
    });
    // The pasted link is a card reference, NOT a product-name search query.
    payload.job.prompt_product = "";
    payload.job.prompt_product_key = "";
    payload.job.prompt_notes = `${marketplace} draft từ link card Trello: ${ref}`;
    payload.job.trello_card_id = ref;
    payload.job.trello_source_card_id = ref;
    // Let the backend resolve the real list from the card itself.
    payload.job.trello_list_id = "";

    let result;
    try {
      result = await api("/api/jobs/auto-trello-one-click", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    } catch (err) {
      const message = err?.message || String(err);
      summary.failed += 1;
      summary.items.push({ ref, error: message });
      logLine(`Card ${ref}: ${message}`);
      continue;
    }

    // etsy_only + a card with no Flow output images returns a 400 (handled above). If the
    // backend still routed to Flow gen, surface it as "needs Flow first" rather than a draft.
    if (result.mode === "explicit_trello_card" || result.mode === "flow_batch") {
      summary.failed += 1;
      summary.items.push({ ref, error: "card chưa có ảnh output" });
      logLine(`Card ${ref}: chưa có ảnh output Flow nên không Listing ${marketplace} được; chạy Flow trước.`);
      continue;
    }

    const tasks = result.tasks || [];
    const enqueued = tasks.filter((task) => task.enqueued).length;
    summary.queued += enqueued;
    summary.items.push({
      ref,
      queued: enqueued,
      card_name: tasks[0]?.card_name || result.job?.title || ref,
    });
    logLine(`Đã queue ${marketplace} Draft từ link card: ${tasks[0]?.card_name || ref}.`, {
      mode: result.mode,
      message: result.message || "",
      card: ref,
      tasks: tasks.map((task) => ({
        card_id: task.card_id || "",
        card_name: task.card_name || "",
        enqueued: Boolean(task.enqueued),
        queue_task: compactQueueTask(task.queue_task || {}),
      })),
    });
  }

  if (!summary.queued) {
    throw new Error(
      summary.failed
        ? `Không queue được link card nào (${summary.failed} lỗi). Card cần có ảnh output Flow trước.`
        : `Không có link card hợp lệ để gửi ${marketplace} Draft.`
    );
  }
  logLine(
    `Tổng: queue ${summary.queued}/${summary.total} card từ link sang ${marketplace} Draft` +
      (summary.failed ? `, ${summary.failed} card chưa có ảnh.` : ".")
  );
  const queue = await inspectEtsyQueue();
  logLine(vmQueueHint(queue));
  await refreshState({ quiet: true });
  setVmQueueUi(queue);
  return summary;
}

function bindEvents() {
  els.refreshButton.addEventListener("click", () => refreshState());
  els.jobsRefreshButton.addEventListener("click", () => refreshState());
  els.jobsStatusButton.addEventListener("click", () => {
    els.jobsDrawer.open = true;
  });
  els.etsyStatusButton.addEventListener("click", () => {
    els.etsyDrawer.open = true;
    els.etsyDrawer.scrollIntoView({ behavior: "smooth", block: "start" });
  });
  els.saveEtsyShortcutButton.addEventListener("click", () => {
    els.etsyDrawer.open = true;
    els.etsyDrawer.scrollIntoView({ behavior: "smooth", block: "start" });
  });
  els.flowStatusButton.addEventListener("click", () => {
    els.flowDrawer.open = true;
    els.flowDrawer.scrollIntoView({ behavior: "smooth", block: "start" });
  });
  els.extensionStatusButton.addEventListener("click", () => {
    window.location.href = "/api/extension/download";
  });
  els.clearConsoleButton.addEventListener("click", () => {
    els.consoleOutput.textContent = "Sẵn sàng.";
  });
  // Delegated so dynamically-rendered board columns (from "Load cột") fire it too.
  els.autoSourceGroup?.addEventListener("change", (event) => {
    if (event.target?.name !== "autoSource") return;
    updateAutoSourceUi();
    const labels = selectedTrelloSourceKeys().map((key) => TRELLO_SOURCE_OPTIONS[key]?.label || key);
    logLine(`Nguồn Trello: ${labels.join(", ") || "(chưa chọn cột)"}.`);
  });
  els.loadBoardColumnsButton?.addEventListener("click", () => {
    withBusy(els.loadBoardColumnsButton, "Đang load", () => loadBoardColumns(els.boardLinkInput?.value || ""));
  });
  els.autoProduct?.addEventListener("input", () => {
    renderEtsyListingAction(state.payload);
  });
  els.imageEngineSelect?.addEventListener("change", () => {
    window.localStorage.setItem("flow-image-engine", selectedImageEngine());
    updateAutoSourceUi();
    logLine(`Chế độ ảnh: ${imageEngineLabel()}.`);
  });
  els.autoCreateEtsy?.addEventListener("change", () => {
    updateAutoSourceUi();
    logLine(`Auto chỉ chạy Flow/Trello; bấm Listing ảnh ${listingMarketplaceName()} sau khi ảnh xong.`);
  });
  els.listLatestEtsyButton?.addEventListener("click", () => {
    // A pasted Trello card link wins over column config: draft exactly that card to Etsy.
    const cardRefs = parseTrelloCardRefs(els.autoProduct?.value);
    if (cardRefs.length) {
      withBusy(els.listLatestEtsyButton, "Đang lấy card", () => queueEtsyFromCardRefs(cardRefs));
      return;
    }
    // Multi-column selection always drafts every image-ready card in the selected columns.
    // Only when a single column is selected do we honor the "just-ran this Flow job" quick
    // path (so a fresh single-card Flow run still queues just that card).
    const multiColumn = selectedTrelloSourceKeys().length > 1;
    const job = multiColumn ? null : latestQueueableEtsyJob();
    withBusy(
      els.listLatestEtsyButton,
      "Đang kiểm Trello",
      () => (job?.id ? queueEtsyFromFlowJob(job.id) : queueEtsyFromTrelloOutputs())
    );
  });
  els.jobsList?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action='queue-etsy']");
    if (!button) return;
    event.preventDefault();
    event.stopPropagation();
    const jobId = button.getAttribute("data-job-id") || "";
    if (!jobId) return;
    withBusy(button, "Đang queue", () => queueEtsyFromFlowJob(jobId));
  });

  els.openFlowButton.addEventListener("click", () =>
    withBusy(els.openFlowButton, "Đang mở", async () => {
      const result = await api("/api/flow/open-project", { method: "POST", body: "{}" });
      logLine("Đã gọi mở Flow project.", result);
      await refreshState({ quiet: true });
    })
  );

  els.openFlowFromSetupButton.addEventListener("click", () =>
    withBusy(els.openFlowFromSetupButton, "Đang mở", async () => {
      const result = await api("/api/flow/open-project", { method: "POST", body: "{}" });
      logLine("Đã gọi mở Flow project.", result);
      await refreshState({ quiet: true });
    })
  );

  els.openLoginButton.addEventListener("click", () =>
    withBusy(els.openLoginButton, "Đang mở", async () => {
      const result = await api("/api/flow/open-login", { method: "POST", body: "{}" });
      logLine("Đã gọi mở trang login Flow.", result);
      await refreshState({ quiet: true });
    })
  );

  els.preflightButton.addEventListener("click", () =>
    withBusy(els.preflightButton, "Đang kiểm", runPreflight)
  );

  els.checkAutoButton.addEventListener("click", () =>
    withBusy(els.checkAutoButton, "Đang kiểm", runPreflight)
  );

  els.runQuickJobButton.addEventListener("click", () =>
    withBusy(els.runQuickJobButton, "Đang chạy", async () => {
      const startedAt = Date.now() - 5_000;
      const payload = quickJobPayload();
      const result = await api("/api/jobs", { method: "POST", body: JSON.stringify(payload) });
      rememberLastFlowRunContext({
        sourceKey: "quick",
        sourceLabel: "Quick Flow",
        jobId: result.job?.id || "",
        startedAt,
      });
      logLine("Đã tạo job Flow.", result);
      await refreshState({ quiet: true });
    })
  );

  els.runAutoButton.addEventListener("click", () =>
    withBusy(els.runAutoButton, "Đang chạy", async () => {
      showConsole();
      logLine(`Start: quét ${selectedTrelloSource().label}, tạo Flow/Trello trước; Listing ảnh ${listingMarketplaceName()} bấm riêng sau khi ảnh xong.`);
      const source = selectedTrelloSource();
      const startedAt = Date.now() - 5_000;
      const payload = autoBatchPayload();
      const result = await api("/api/jobs/auto-trello-one-click", { method: "POST", body: JSON.stringify(payload) });
      rememberLastFlowRunContext({
        sourceKey: selectedTrelloSourceKey(),
        sourceLabel: source.label,
        product: text(els.autoProduct?.value || source.product, ""),
        cardId: source.cardId || "",
        listId: source.listId || "",
        startedAt,
      });
      logAutoRunResult(result);
      let queue = null;
      if (payload.job?.etsy_browser_copy_enabled || payload.job?.etsy_enabled) {
        queue = await inspectEtsyQueue();
        logLine(vmQueueHint(queue));
      } else {
        logLine(`Auto đang tách bước: Flow/Trello chạy trước. Khi job ảnh completed, bấm nút Listing ảnh ${listingMarketplaceName()} trong Jobs.`);
      }
      await refreshState({ quiet: true });
      if (queue) setVmQueueUi(queue);
    })
  );

  els.saveEtsyButton.addEventListener("click", () =>
    withBusy(els.saveEtsyButton, "Đang lưu", saveEtsy)
  );

  if (els.addAccountButton) {
    els.addAccountButton.addEventListener("click", () =>
      withBusy(els.addAccountButton, "Đang lưu", upsertEtsyAccount)
    );
  }
  if (els.accountsRefreshButton) {
    els.accountsRefreshButton.addEventListener("click", (event) => {
      event.preventDefault();
      loadEtsyAccounts({ quiet: false });
    });
  }
  if (els.accountsList) {
    els.accountsList.addEventListener("click", (event) => {
      const button = event.target.closest('[data-action="del-account"]');
      if (!button) return;
      const slug = button.getAttribute("data-slug") || "";
      if (slug && window.confirm(`Xoá tài khoản Etsy "${slug}"?`)) {
        deleteEtsyAccount(slug);
      }
    });
  }
  if (els.autoAccountSelect) {
    els.autoAccountSelect.addEventListener("change", () => {
      const accountId = selectedEtsyAccountId();
      logLine(
        accountId
          ? `One-click sẽ dùng tài khoản "${accountId}" (board riêng đã đăng ký).`
          : "One-click dùng tài khoản mặc định (trung6, board global)."
      );
    });
  }

  els.saveFlowButton.addEventListener("click", () =>
    withBusy(els.saveFlowButton, "Đang lưu", saveFlowConfig)
  );

  els.saveGeminiButton?.addEventListener("click", () =>
    withBusy(els.saveGeminiButton, "Đang lưu", saveGeminiConfig)
  );

  els.previewEtsyButton.addEventListener("click", () =>
    withBusy(els.previewEtsyButton, "Đang preview", previewEtsy)
  );

  if (els.connectEtsyTopButton) {
    els.connectEtsyTopButton.addEventListener("click", () =>
      withBusy(els.connectEtsyTopButton, "Đang xem", () => connectEtsy())
    );
  }
  if (els.connectEtsyButton) {
    els.connectEtsyButton.addEventListener("click", () =>
      withBusy(els.connectEtsyButton, "Đang xem", () => connectEtsy())
    );
  }
  if (els.runEtsyCopyButton) {
    els.runEtsyCopyButton.addEventListener("click", () =>
      withBusy(els.runEtsyCopyButton, "Đang chạy", runEtsyBrowserCopy)
    );
  }
  if (els.disconnectEtsyButton) {
    els.disconnectEtsyButton.addEventListener("click", () =>
      withBusy(els.disconnectEtsyButton, "Đang ngắt", disconnectEtsy)
    );
  }
  if (els.copyCallbackButton) {
    els.copyCallbackButton.addEventListener("click", async () => {
      const url = els.etsyCallbackHint ? els.etsyCallbackHint.textContent.trim() : "";
      if (!url) return;
      try {
        await navigator.clipboard.writeText(url);
        els.copyCallbackButton.textContent = "Đã copy";
        window.setTimeout(() => {
          els.copyCallbackButton.textContent = "Copy";
        }, 1500);
      } catch (error) {
        logLine(`Không copy được Callback URL: ${error.message}`);
      }
    });
  }

  window.addEventListener("message", (event) => {
    if (event.origin !== window.location.origin) return;
    const data = event.data || {};
    if (data.type !== "etsy-oauth") return;
    if (data.ok) {
      logLine("Etsy đã kết nối xong.");
      refreshState({ quiet: true });
    } else {
      logLine(`Kết nối Etsy thất bại: ${data.error || "không rõ lỗi"}`);
    }
  });
}

async function boot() {
  if (els.etsyCallbackHint) {
    els.etsyCallbackHint.textContent = `${window.location.origin}/api/etsy/oauth/callback`;
  }
  applyToolMode();
  bindEvents();
  updateAutoSourceUi();
  await refreshState({ quiet: true });
  await loadEtsyAccounts({ quiet: true });
  state.polling = window.setInterval(() => refreshState({ quiet: true }), 7000);
}

boot();
