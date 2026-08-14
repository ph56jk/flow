const ACTIVE_STATUSES = new Set(["queued", "running", "polling"]);
const EDIT_JOB_TYPES = new Set(["extend", "upscale", "camera_motion", "camera_position", "insert", "remove"]);
const FALLBACK_VIDEO_MODELS = [
  { value: "Veo 3.1 - Fast", label: "Veo 3.1 - Fast" },
  { value: "Veo 3.1 - Quality", label: "Veo 3.1 - Quality" },
  { value: "Veo 2 - Fast", label: "Veo 2 - Fast" },
  { value: "Veo 2 - Quality", label: "Veo 2 - Quality" },
];
const FALLBACK_IMAGE_MODELS = [
  { value: "GEMINI_3_PRO_IMAGE", label: "Nano Banana Pro" },
  { value: "NARWHAL", label: "Nano Banana 2" },
  { value: "IMAGEN_3", label: "Imagen 3" },
];
const REFERENCE_ROLE_OPTIONS = [
  { value: "base", label: "Ảnh chính", detail: "Ảnh người mẫu hoặc ảnh gốc cần giữ lại." },
  { value: "logo", label: "Logo", detail: "Logo, hoạ tiết, nhãn hiệu hoặc chi tiết brand." },
  { value: "product", label: "Sản phẩm", detail: "Ảnh sản phẩm, quần áo, phụ kiện, vật thể chính." },
  { value: "reference", label: "Tham chiếu", detail: "Ảnh phụ để lấy màu, chất liệu, bố cục hoặc vibe." },
];
const AUTOMATION_STORAGE_KEY = "flow-web-automation-dashboard-v1";
const AUTOMATION_CONFIG_VERSION = 1;
const DEFAULT_PROMPT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1I8J4jkj2p_H2hsbDgh-kzc0WqUFWtmqR0gYqbE9Zp4U/edit?gid=2137274733#gid=2137274733";
const DEFAULT_ERP_PROJECT_URL = "PROJ-0049";

// The app still touches exactly one ERP Project at a time; the owner just picks
// which one instead of being locked to the project this app shipped with.
function normalizeERPProjectId(value) {
  const text = String(value || "").trim().toUpperCase();
  const match = text.match(/PROJ-\d{4,}/);
  return match ? match[0] : "";
}

function currentERPProjectId() {
  return (
    normalizeERPProjectId(state.erp?.project_id) ||
    normalizeERPProjectId(state.automation?.erpProjectId) ||
    DEFAULT_ERP_PROJECT_URL
  );
}
const DEFAULT_ERP_SOURCE_LIST_ID = "Open";
const DEFAULT_ERP_SOURCE_SCOPE_LABEL = "Task trạng thái Open";
const FLOW_AI_SOURCE_TYPE = "flow_ai";
const FLOW_AGENT_DEFAULT_IMAGE_COUNT = 12;
const FLOW_AGENT_TARGET_OUTPUT_COUNT = 12;
const AUTOMATION_STEP_ORDER = ["source", "erp_source", "normalize", "flow", "watermark", "review_hold", "log"];
const AUTOMATION_CANVAS_ZOOM_MIN = 0.72;
const AUTOMATION_CANVAS_ZOOM_MAX = 1.35;
const AUTOMATION_CANVAS_ZOOM_STEP = 0.1;
let promptSourceAutoPreviewStarted = false;
let automationSubmitInFlight = false;
let stateLoadPromise = null;
const AUTOMATION_MODULE_TYPE_CONFIG = {
  source: {
    label: "Flow Agent",
    title: "Flow Agent Request",
    detail: "Yêu cầu cho Tác nhân Flow",
    icon: "T",
    iconClass: "node-icon-erp",
  },
  erp_source: {
    label: "ERP source",
    title: "ERP Task Source",
    detail: "Lấy ảnh gốc từ đúng ERP Task",
    icon: "TS",
    iconClass: "node-icon-erp",
  },
  normalize: {
    label: "Prepare",
    title: "Prepare Request",
    detail: "Chuẩn hóa lệnh cho Flow Agent",
    icon: "S",
    iconClass: "node-icon-sheet",
  },
  flow: {
    label: "Google Flow",
    title: "Google Flow",
    detail: "Tác nhân Flow tạo ảnh",
    icon: "F",
    iconClass: "node-icon-flow",
  },
  watermark: {
    label: "Remove Logo",
    title: "Remove Logo",
    detail: "Xóa watermark Gemini bằng bộ xử lý cục bộ",
    icon: "W",
    iconClass: "node-icon-watermark",
  },
  erp: {
    label: "ERP",
    title: "ERP Task Comment",
    detail: "Ghi URL ảnh đã duyệt vào đúng Task",
    icon: "L",
    iconClass: "node-icon-log",
  },
  approval: {
    label: "Review",
    title: "Dashboard Review",
    detail: "Chờ quyết định duyệt ngay trong app",
    icon: "D",
    iconClass: "node-icon-log",
  },
  custom: {
    label: "Custom",
    title: "Custom Module",
    detail: "Cục tự định nghĩa",
    icon: "C",
    iconClass: "node-icon-custom",
  },
};
const AUTOMATION_STEP_DEFAULTS = {
  source: {
    title: "Flow Agent Request",
    detail: "Yêu cầu cho Tác nhân Flow",
  },
  erp_source: {
    title: "ERP Task Source",
    detail: "Lấy ảnh sản phẩm gốc từ ERP Task",
  },
  normalize: {
    title: "Prepare Request",
    detail: "Chuẩn hóa lệnh cho Flow Agent",
  },
  flow: {
    title: "Google Flow",
    detail: "Tác nhân Flow tạo ảnh",
  },
  watermark: {
    title: "Remove Logo",
    detail: "Xóa watermark Gemini trước khi duyệt",
  },
  log: {
    title: "ERP Task Comment",
    detail: "Ghi URL ảnh đã duyệt vào đúng Task",
  },
  review_hold: {
    title: "Dashboard Review",
    detail: "Chỉ ghi ERP sau khi duyệt trên dashboard",
  },
};
const ASPECT_DETAILS = {
  landscape: { title: "Ngang 16:9", detail: "YouTube, cảnh ngang, widescreen" },
  portrait: { title: "Dọc 9:16", detail: "Reels, Shorts, TikTok" },
  square: { title: "Vuông 1:1", detail: "Feed, poster vuông, thumbnail" },
};
const POLICY_MINOR_TERMS = [
  "tre vi thanh nien",
  "vi thanh nien",
  "tre em",
  "em be",
  "be gai",
  "be trai",
  "thieu nien",
  "tuoi teen",
  "teen",
  "hoc sinh",
  "minor",
  "underage",
  "child",
  "kid",
  "young girl",
  "young boy",
  "schoolgirl",
  "school boy",
];
const POLICY_APPEARANCE_TERMS = [
  "dep trai hon",
  "dep gai hon",
  "dep hon",
  "lam dep",
  "fashion",
  "nguoi mau",
  "model",
  "sexy",
  "goi cam",
  "nong bong",
  "makeup",
  "trang diem",
  "body",
  "than hinh",
  "bo kinh",
  "thay do",
  "mac do",
  "mac ao",
  "thu do",
];
const POLICY_APPAREL_TERMS = [
  "ao",
  "logo",
  "dong phuc",
  "quan ao",
  "quan",
  "vay",
  "thoi trang",
  "outfit",
  "shirt",
  "dress",
  "clothing",
  "fashion",
];
const VIDEO_INPUT_MODE_CONFIG = {
  prompt: {
    note: "Chỉ cần mô tả cảnh. App sẽ tạo video trực tiếp từ prompt.",
    hint: "Nhập mô tả cảnh muốn quay rồi bấm chạy.",
    placeholder: "Ví dụ: một chú mèo nhìn ra cửa sổ, cinematic, gentle motion, ánh sáng buổi sáng",
    readyText: "Sẵn sàng tạo video từ prompt.",
  },
  start: {
    note: "Dùng khi đã có một khung hình đầu tiên và muốn app animate từ chính ảnh đó.",
    hint: "Tải một ảnh đầu vào rồi mô tả chuyển động, góc máy hoặc diễn biến tiếp theo.",
    placeholder: "Ví dụ: nhân vật quay đầu sang trái, tóc bay nhẹ, camera tiến gần, cinematic premium visual treatment",
    readyText: "Sẵn sàng tạo video từ ảnh đầu vào.",
  },
  reference: {
    note: "Dùng khi chỉ có ảnh áo, logo hoặc sản phẩm. App sẽ tự dựng một khung đầu có người mẫu hoặc bố cục phù hợp, rồi mới tạo video.",
    hint: "Tải ảnh sản phẩm hoặc logo vào đây. App sẽ tự dựng người mẫu hoặc keyframe phù hợp rồi tạo video trong một lượt.",
    placeholder: "Ví dụ: người mẫu bước ra trong studio, khoe rõ chiếc áo, ánh sáng premium, camera dolly in, cảm giác quảng cáo cao cấp",
    readyText: "Sẵn sàng dựng khung đầu rồi tạo video.",
  },
};

const MODE_CONFIG = {
  video: {
    title: "Bạn muốn tạo video gì?",
    hint: "Nhập mô tả ngắn gọn rồi bấm chạy.",
    promptLabel: "Mô tả video",
    placeholder: "Ví dụ: Một video cinematic về con mèo đi bộ trong phòng khách đầy nắng",
    promptAiLabel: "Bạn muốn video như thế nào?",
    promptAiPlaceholder: "Ví dụ: video quảng cáo đàn piano sang trọng, có người chơi trong phòng tối và ánh sáng ấm",
    submitLabel: "Tạo video",
    resultsTitle: "Kết quả video gần đây",
    runsTitle: "Lượt chạy video gần đây",
    readyText: "Sẵn sàng tạo video.",
    emptyResult: "Chưa có video nào gần đây.",
    emptyRun: "Chưa có lượt chạy video nào.",
    defaultAspect: "landscape",
    defaultCount: 1,
    showStartImage: true,
    showPromptAi: true,
    promptRequired: true,
  },
  image: {
    title: "Bạn muốn tạo ảnh gì?",
    hint: "Nhập mô tả ngắn gọn hoặc ghép ảnh tham chiếu rồi bấm chạy.",
    promptLabel: "Mô tả ảnh",
    placeholder: "Ví dụ: ghép logo này lên áo của người mẫu, giữ nếp vải thật và ánh sáng đồng nhất",
    promptAiLabel: "Bạn muốn ảnh như thế nào?",
    promptAiPlaceholder: "Ví dụ: ghép logo áo vào ảnh người mẫu, nhìn như ảnh chụp thật trong studio",
    submitLabel: "Tạo ảnh",
    resultsTitle: "Kết quả ảnh gần đây",
    runsTitle: "Lượt chạy ảnh gần đây",
    readyText: "Sẵn sàng tạo ảnh.",
    emptyResult: "Chưa có ảnh nào gần đây.",
    emptyRun: "Chưa có lượt chạy ảnh nào.",
    defaultAspect: "square",
    defaultCount: 2,
    showStartImage: false,
    showPromptAi: true,
    promptRequired: true,
  },
  edit: {
    title: "Bạn muốn chỉnh video như thế nào?",
    hint: "Chọn một video đã có sẵn, chọn thao tác cần sửa, rồi bấm chạy.",
    promptLabel: "Mô tả chỉnh sửa",
    placeholder: "Ví dụ: kéo dài thêm 5 giây với chuyển động tự nhiên",
    submitLabel: "Chạy thao tác",
    resultsTitle: "Kết quả chỉnh video gần đây",
    runsTitle: "Lượt chỉnh video gần đây",
    readyText: "Sẵn sàng chỉnh video.",
    emptyResult: "Chưa có kết quả chỉnh video nào.",
    emptyRun: "Chưa có lượt chỉnh video nào.",
    defaultAspect: "landscape",
    defaultCount: 1,
    showStartImage: false,
    showPromptAi: false,
    promptRequired: false,
  },
};

const EDIT_ACTION_CONFIG = {
  extend: {
    title: "Kéo dài video",
    hint: "Dùng khi muốn nối thêm phần cuối video hiện có.",
    promptLabel: "Mô tả đoạn nối thêm",
    placeholder: "Ví dụ: tiếp tục cảnh này thêm vài giây, chuyển động mượt và giữ đúng nhân vật",
    submitLabel: "Kéo dài video",
    promptRequired: false,
    showPrompt: true,
    showMotion: false,
    showPosition: false,
    showResolution: false,
  },
  upscale: {
    title: "Nâng chất lượng video",
    hint: "Dùng khi muốn tăng chất lượng video đã có.",
    promptLabel: "Không cần mô tả thêm",
    placeholder: "",
    submitLabel: "Nâng chất lượng",
    promptRequired: false,
    showPrompt: false,
    showMotion: false,
    showPosition: false,
    showResolution: true,
  },
  camera_motion: {
    title: "Chỉnh chuyển động camera",
    hint: "Dùng khi muốn đổi cách máy quay di chuyển.",
    promptLabel: "Không cần mô tả thêm",
    placeholder: "",
    submitLabel: "Đổi chuyển động camera",
    promptRequired: false,
    showPrompt: false,
    showMotion: true,
    showPosition: false,
    showResolution: false,
  },
  camera_position: {
    title: "Chỉnh vị trí camera",
    hint: "Dùng khi muốn đổi góc hoặc khoảng cách camera.",
    promptLabel: "Không cần mô tả thêm",
    placeholder: "",
    submitLabel: "Đổi vị trí camera",
    promptRequired: false,
    showPrompt: false,
    showMotion: false,
    showPosition: true,
    showResolution: false,
  },
  insert: {
    title: "Chèn vật thể",
    hint: "Dùng khi muốn thêm vật thể hoặc chi tiết mới vào video.",
    promptLabel: "Mô tả vật thể cần chèn",
    placeholder: "Ví dụ: thêm thanh kiếm phát sáng vào tay nhân vật",
    submitLabel: "Chèn vật thể",
    promptRequired: true,
    showPrompt: true,
    showMotion: false,
    showPosition: false,
    showResolution: false,
  },
  remove: {
    title: "Xóa vật thể",
    hint: "Dùng khi muốn gỡ một vật thể không cần thiết khỏi video.",
    promptLabel: "Không cần mô tả thêm",
    placeholder: "",
    submitLabel: "Xóa vật thể",
    promptRequired: false,
    showPrompt: false,
    showMotion: false,
    showPosition: false,
    showResolution: false,
  },
};

function moduleTypeForLegacyKey(key) {
  if (key === "log") {
    return "erp";
  }
  if (key === "review_hold") {
    return "approval";
  }
  if (key === "erp_source") {
    return "erp_source";
  }
  return AUTOMATION_MODULE_TYPE_CONFIG[key] ? key : "custom";
}

function moduleTypeConfig(type) {
  return AUTOMATION_MODULE_TYPE_CONFIG[type] || AUTOMATION_MODULE_TYPE_CONFIG.custom;
}

function boundedGenerationCount(value, fallback = 1, maxCount = 4) {
  const numeric = Number(value);
  const fallbackNumeric = Number(fallback);
  const maxNumeric = Number(maxCount);
  const resolvedMax = Number.isFinite(maxNumeric) && maxNumeric > 0 ? maxNumeric : 4;
  const resolved = Number.isFinite(numeric) && numeric > 0
    ? numeric
    : Number.isFinite(fallbackNumeric) && fallbackNumeric > 0
      ? fallbackNumeric
      : 1;
  return Math.max(1, Math.min(resolvedMax, resolved));
}

function flowAgentEnabledFromSettings(settings = {}) {
  return settings?.flowAgentEnabled !== false;
}

function flowModuleImageCount(settings = {}, fallbackCount = 1) {
  const maxCount = flowAgentEnabledFromSettings(settings) ? FLOW_AGENT_TARGET_OUTPUT_COUNT : 4;
  const hasExplicitCount = Boolean(settings) && Object.prototype.hasOwnProperty.call(settings, "imageCount");
  if (hasExplicitCount) {
    return boundedGenerationCount(settings.imageCount, FLOW_AGENT_DEFAULT_IMAGE_COUNT, maxCount);
  }
  return boundedGenerationCount(
    flowAgentEnabledFromSettings(settings) ? FLOW_AGENT_DEFAULT_IMAGE_COUNT : fallbackCount,
    fallbackCount,
    maxCount,
  );
}

function createAutomationModule(type = "custom", seed = {}) {
  const safeType = moduleTypeConfig(type) === AUTOMATION_MODULE_TYPE_CONFIG.custom ? (type === "custom" ? "custom" : moduleTypeForLegacyKey(type)) : type;
  const config = moduleTypeConfig(safeType);
  const id = String(seed.id || `${safeType}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`);
  return {
    id,
    type: safeType,
    title: String(seed.title || config.title),
    detail: String(seed.detail || config.detail),
    icon: String(seed.icon || config.icon),
    enabled: seed.enabled !== false,
    settings: {
      ...(seed.settings || {}),
    },
  };
}

function defaultAutomationModules() {
  return AUTOMATION_STEP_ORDER.map((key) => {
    const legacy = AUTOMATION_STEP_DEFAULTS[key] || {};
    return createAutomationModule(moduleTypeForLegacyKey(key), {
      id: key,
      title: legacy.title,
      detail: legacy.detail,
    });
  });
}

function normalizeAutomationModule(value = {}, index = 0) {
  const fallbackType = moduleTypeForLegacyKey(value.id || value.type || "custom");
  const type = moduleTypeConfig(value.type) === AUTOMATION_MODULE_TYPE_CONFIG.custom && value.type !== "custom"
    ? fallbackType
    : (value.type || fallbackType);
  const fallback = createAutomationModule(type, {
    id: value.id || `module_${index + 1}`,
  });
  const sourceTitle = String(value.title || "").trim();
  const sourceDetail = String(value.detail || "").trim();
  const title = type === "source" && ["Prompt Source", "AI Prompt Source", "Flow AI Prompt"].includes(sourceTitle)
    ? fallback.title
    : String(value.title || fallback.title);
  const detail = type === "source" && ["Google Sheet / file / nhập tay", "ERP / Sheet / nhập tay", "AI tự viết / Sheet tùy chọn", "Flow AI tự viết prompt"].includes(sourceDetail)
    ? fallback.detail
    : String(value.detail || fallback.detail);
  return createAutomationModule(type, {
    ...fallback,
    ...value,
    id: String(value.id || fallback.id),
    title,
    detail,
    icon: String(value.icon || fallback.icon),
    enabled: value.enabled !== false,
    settings: value.settings && typeof value.settings === "object" ? value.settings : {},
  });
}

function normalizeAutomationModules(parsed = {}) {
  let modules = [];
  if (Array.isArray(parsed.modules) && parsed.modules.length) {
    modules = parsed.modules.map(normalizeAutomationModule);
  } else {
    const steps = parsed.steps && typeof parsed.steps === "object" ? parsed.steps : {};
    for (const key of AUTOMATION_STEP_ORDER) {
      const legacy = {
        ...(AUTOMATION_STEP_DEFAULTS[key] || {}),
        ...(steps[key] || {}),
        id: key,
        type: moduleTypeForLegacyKey(key),
      };
      modules.push(normalizeAutomationModule(legacy, modules.length));
    }
  }
  modules = modules.filter((module) => module.type !== "telegram");
  modules = modules.length ? modules : defaultAutomationModules();
  const existingTypes = new Set(modules.map((module) => module.type));
  for (const key of AUTOMATION_STEP_ORDER) {
    const requiredType = moduleTypeForLegacyKey(key);
    if (existingTypes.has(requiredType)) {
      continue;
    }
    const legacy = AUTOMATION_STEP_DEFAULTS[key] || {};
    modules.push(createAutomationModule(requiredType, {
      id: key,
      title: legacy.title,
      detail: legacy.detail,
    }));
    existingTypes.add(requiredType);
  }
  // A saved config from before the Remove Logo node gets it appended last, but
  // it only makes sense between Flow and the review gate.
  const watermarkIndex = modules.findIndex((module) => module.type === "watermark");
  const flowIndex = modules.findIndex((module) => module.type === "flow");
  if (watermarkIndex > -1 && flowIndex > -1 && watermarkIndex !== flowIndex + 1) {
    const [watermarkModule] = modules.splice(watermarkIndex, 1);
    modules.splice(modules.findIndex((module) => module.type === "flow") + 1, 0, watermarkModule);
  }
  return modules;
}

function automationStepsFromModules(modules = []) {
  return Object.fromEntries((modules || []).map((module) => [module.id, module]));
}

function defaultAutomationConfig() {
  const modules = defaultAutomationModules();
  return {
    version: AUTOMATION_CONFIG_VERSION,
    enabled: false,
    view: "diagram",
    selectedStep: "flow",
    sourceType: FLOW_AI_SOURCE_TYPE,
    sourceLocation: "",
    promptProductFilter: "",
    sheetLog: "",
    erpProjectId: DEFAULT_ERP_PROJECT_URL,
    erpTaskId: "",
    erpStatusId: DEFAULT_ERP_SOURCE_LIST_ID,
    erpAttachmentIds: [],
    prompt: "",
    appEyebrow: "Flow v2",
    appTitle: "Flow v2",
    appSubtitle: "Auto ERP lấy ảnh từ Task, Flow tạo ảnh, duyệt ngay trên dashboard, rồi ghi URL ảnh đã duyệt vào comment của chính Task.",
    accentColor: "#7c2ee6",
    canvasZoom: 1,
    modules,
    steps: automationStepsFromModules(modules),
  };
}

function normalizeAutomationConfig(value = {}) {
  const fallback = defaultAutomationConfig();
  const parsed = value && typeof value === "object" ? value : {};
  let modules = normalizeAutomationModules(parsed);
  const hasSelected = modules.some((module) => module.id === parsed?.selectedStep);
  const selectedStep = hasSelected ? parsed.selectedStep : (modules.find((module) => module.type === "flow") || modules[0])?.id || "flow";
  const parsedSourceLocation = String(parsed?.sourceLocation || "").trim();
  const rawParsedSourceType = String(parsed?.sourceType || "").trim();
  const parsedSourceType = rawParsedSourceType === "ai" ? FLOW_AI_SOURCE_TYPE : rawParsedSourceType;
  const usedDefaultSheet = !parsedSourceLocation || parsedSourceLocation === DEFAULT_PROMPT_SHEET_URL;
  const shouldMigrateDefaultSheet = (!parsedSourceType || parsedSourceType === "sheets") && usedDefaultSheet;
  const sourceType = shouldMigrateDefaultSheet ? FLOW_AI_SOURCE_TYPE : (parsedSourceType || fallback.sourceType);
  const sourceLocation = shouldMigrateDefaultSheet ? "" : parsedSourceLocation;
  if (shouldMigrateDefaultSheet) {
    modules = modules.map((module) => {
      if (module.type !== "source") {
        return module;
      }
      const settings = { ...(module.settings || {}) };
      if (!settings.sourceType || settings.sourceType === "sheets") {
        settings.sourceType = FLOW_AI_SOURCE_TYPE;
      }
      if (!settings.sourceLocation || settings.sourceLocation === DEFAULT_PROMPT_SHEET_URL) {
        settings.sourceLocation = "";
      }
      return { ...module, settings };
    });
  }
  const erpProjectId = normalizeERPProjectId(parsed?.erpProjectId) || DEFAULT_ERP_PROJECT_URL;
  const erpStatusId = String(parsed?.erpStatusId || "").trim() || fallback.erpStatusId;
  return {
    ...fallback,
    ...parsed,
    version: AUTOMATION_CONFIG_VERSION,
    view: ["diagram", "history", "incomplete"].includes(parsed?.view) ? parsed.view : fallback.view,
    selectedStep,
    sourceType,
    sourceLocation,
    promptProductFilter: String(parsed?.promptProductFilter || ""),
    sheetLog: String(parsed?.sheetLog || ""),
    erpProjectId,
    erpTaskId: String(parsed?.erpTaskId || ""),
    erpStatusId,
    erpAttachmentIds: Array.isArray(parsed?.erpAttachmentIds)
      ? parsed.erpAttachmentIds.map((item) => String(item || "").trim()).filter(Boolean)
      : String(parsed?.erpAttachmentIds || "")
          .split(/[\s,;]+/)
          .map((item) => item.trim())
          .filter(Boolean),
    prompt: String(parsed?.prompt || ""),
    appEyebrow: String(parsed?.appEyebrow || fallback.appEyebrow),
    appTitle: String(parsed?.appTitle || fallback.appTitle),
    appSubtitle: String(parsed?.appSubtitle || fallback.appSubtitle),
    accentColor: normalizeHexColor(parsed?.accentColor || fallback.accentColor, fallback.accentColor),
    canvasZoom: clampAutomationCanvasZoom(parsed?.canvasZoom ?? fallback.canvasZoom),
    modules,
    steps: automationStepsFromModules(modules),
  };
}

function loadAutomationConfig() {
  try {
    const raw = window.localStorage?.getItem(AUTOMATION_STORAGE_KEY);
    if (!raw) {
      return defaultAutomationConfig();
    }
    return normalizeAutomationConfig(JSON.parse(raw));
  } catch (error) {
    return defaultAutomationConfig();
  }
}

function saveAutomationConfig(config) {
  try {
    window.localStorage?.setItem(AUTOMATION_STORAGE_KEY, JSON.stringify(config));
  } catch (error) {
    // Local storage is optional; the workflow still works for this session.
  }
}

function clampAutomationCanvasZoom(value) {
  const zoom = Number(value);
  if (!Number.isFinite(zoom)) {
    return 1;
  }
  return Math.min(AUTOMATION_CANVAS_ZOOM_MAX, Math.max(AUTOMATION_CANVAS_ZOOM_MIN, zoom));
}

function defaultERPState() {
  return {
    configured: false,
    credentials_saved: false,
    api_key_saved: false,
    api_secret_saved: false,
    credentials_source: "",
    base_url: "https://erp.havigroup.llc",
    project_id: DEFAULT_ERP_PROJECT_URL,
    task_id: "",
    status: "",
    updated_at: "",
  };
}

function normalizeERPState(value = {}) {
  const payload = value && typeof value === "object" ? value : {};
  const credentialsSource = ["state", "env"].includes(payload.credentials_source)
    ? payload.credentials_source
    : "";
  return {
    ...defaultERPState(),
    configured: Boolean(payload.configured),
    credentials_saved: Boolean(payload.credentials_saved),
    api_key_saved: Boolean(payload.api_key_saved),
    api_secret_saved: Boolean(payload.api_secret_saved),
    credentials_source: credentialsSource,
    base_url: String(payload.base_url || "https://erp.havigroup.llc"),
    project_id: String(payload.project_id || DEFAULT_ERP_PROJECT_URL),
    task_id: String(payload.task_id || ""),
    status: String(payload.status || ""),
    updated_at: String(payload.updated_at || ""),
  };
}

function defaultIntegrationState() {
  return {
    gemini: {
      configured: false,
      api_key_saved: false,
      model: "gemini-2.5-flash",
    },
    telegram: {
      configured: false,
      bot_token_saved: false,
      chat_id: "",
    },
    runtime: {
      playwright_browsers_path: "",
      playwright_browsers_path_set: false,
    },
    updated_at: "",
  };
}

function normalizeIntegrationState(value = {}) {
  const payload = value && typeof value === "object" ? value : {};
  const fallback = defaultIntegrationState();
  return {
    gemini: {
      ...fallback.gemini,
      ...(payload.gemini || {}),
      configured: Boolean(payload.gemini?.configured),
      api_key_saved: Boolean(payload.gemini?.api_key_saved),
      model: String(payload.gemini?.model || fallback.gemini.model),
    },
    telegram: {
      ...fallback.telegram,
      ...(payload.telegram || {}),
      configured: Boolean(payload.telegram?.configured),
      bot_token_saved: Boolean(payload.telegram?.bot_token_saved),
      chat_id: String(payload.telegram?.chat_id || ""),
    },
    runtime: {
      ...fallback.runtime,
      ...(payload.runtime || {}),
      playwright_browsers_path: String(payload.runtime?.playwright_browsers_path || ""),
      playwright_browsers_path_set: Boolean(payload.runtime?.playwright_browsers_path_set),
    },
    updated_at: String(payload.updated_at || ""),
  };
}

const state = {
  mode: "video",
  editAction: "extend",
  config: null,
  auth: { authenticated: false },
  jobs: [],
  outputShelf: { items: [] },
  skillLibraryCount: 0,
  modelOptions: {
    video: [...FALLBACK_VIDEO_MODELS],
    image: [...FALLBACK_IMAGE_MODELS],
  },
  modelOptionsLoaded: false,
  modelOptionsLoading: false,
  startImagePath: "",
  startImageName: "",
  startImagePublicUrl: "",
  imageReferenceItems: [],
  uploading: false,
  setupOpen: null,
  selectedEditSourceKey: "",
  manualMediaId: "",
  manualWorkflowId: "",
  motion: "truck_left",
  position: "center",
  resolution: "1080p",
  promptAssistant: null,
  userAssistant: {
    busy: false,
    executing: false,
    last: null,
  },
  promptSourcePreview: null,
  integrations: defaultIntegrationState(),
  erp: defaultERPState(),
  promptAiResults: {
    video: null,
    image: null,
  },
  drafts: {
    video: { prompt: "", model: "Veo 3.1 - Fast", aspect: "landscape", count: 1, inputMode: "prompt" },
    image: { prompt: "", model: "GEMINI_3_PRO_IMAGE", aspect: "square", count: 2 },
    edit: { prompt: "", model: "", aspect: "landscape", count: 1 },
  },
  promptAiDrafts: {
    video: { brief: "", style: "", mustInclude: "", avoid: "", audience: "" },
    image: { brief: "", style: "", mustInclude: "", avoid: "", audience: "" },
  },
  storyboardDraft: {
    script: "",
    style: "",
    mustInclude: "",
    avoid: "",
    sceneCount: "0",
  },
  storyboardPlan: null,
  storyboardBusy: false,
  automation: loadAutomationConfig(),
};

let automationCanvasPan = null;
let automationDraggedStepId = "";

const elements = {
  projectStatus: document.querySelector("#projectStatus"),
  authStatus: document.querySelector("#authStatus"),
  topbarHint: document.querySelector("#topbarHint"),
  openFlowButton: document.querySelector("#openFlowButton"),
  logoutButton: document.querySelector("#logoutButton"),
  setupToggle: document.querySelector("#setupToggle"),
  setupPanel: document.querySelector("#setupPanel"),
  configForm: document.querySelector("#configForm"),
  projectId: document.querySelector("#projectId"),
  projectName: document.querySelector("#projectName"),
  generationTimeout: document.querySelector("#generationTimeout"),
  loginButton: document.querySelector("#loginButton"),
  openLoginButton: document.querySelector("#openLoginButton"),
  openProjectButton: document.querySelector("#openProjectButton"),
  focusProjectButton: document.querySelector("#focusProjectButton"),
  automationEnabled: document.querySelector("#automationEnabled"),
  automationEasyPanel: document.querySelector("#automationEasyPanel"),
  easyPromptButton: document.querySelector("#easyPromptButton"),
  easyFlowButton: document.querySelector("#easyFlowButton"),
  easyReviewButton: document.querySelector("#easyReviewButton"),
  easyRunButton: document.querySelector("#easyRunButton"),
  easyPromptStatus: document.querySelector("#easyPromptStatus"),
  easyFlowStatus: document.querySelector("#easyFlowStatus"),
  easyReviewStatus: document.querySelector("#easyReviewStatus"),
  scenarioCanvas: document.querySelector("#scenarioCanvas"),
  scenarioNodeRow: document.querySelector(".scenario-node-row"),
  automationZoomOut: document.querySelector("#automationZoomOut"),
  automationZoomReset: document.querySelector("#automationZoomReset"),
  automationZoomIn: document.querySelector("#automationZoomIn"),
  automationFitButton: document.querySelector("#automationFitButton"),
  breakRoute: document.querySelector(".break-route"),
  automationViewButtons: Array.from(document.querySelectorAll("[data-automation-view]")),
  scenarioHistoryPanel: document.querySelector("#scenarioHistoryPanel"),
  scenarioIncompletePanel: document.querySelector("#scenarioIncompletePanel"),
  automationHistoryPanelList: document.querySelector("#automationHistoryPanelList"),
  automationIncompletePanelList: document.querySelector("#automationIncompletePanelList"),
  automationHistoryRefreshButton: document.querySelector("#automationHistoryRefreshButton"),
  automationIncompleteRefreshButton: document.querySelector("#automationIncompleteRefreshButton"),
  automationUseStudioButton: document.querySelector("#automationUseStudioButton"),
  automationOpenFlowButton: document.querySelector("#automationOpenFlowButton"),
  automationAutoRunButton: document.querySelector("#automationAutoRunButton"),
  automationRunButton: document.querySelector("#automationRunButton"),
  automationRunImageButton: document.querySelector("#automationRunImageButton"),
  automationRefreshButton: document.querySelector("#automationRefreshButton"),
  userAssistantEngine: document.querySelector("#userAssistantEngine"),
  userAssistantQuestion: document.querySelector("#userAssistantQuestion"),
  userAssistantAskButton: document.querySelector("#userAssistantAskButton"),
  userAssistantAnswer: document.querySelector("#userAssistantAnswer"),
  userAssistantQuickButtons: Array.from(document.querySelectorAll("[data-assistant-question]")),
  automationBrandEyebrow: document.querySelector("#automationBrandEyebrow"),
  automationBrandTitle: document.querySelector("#automationBrandTitle"),
  automationPromptInput: document.querySelector("#automationPromptInput"),
  automationSourceType: document.querySelector("#automationSourceType"),
  automationStepNameInput: document.querySelector("#automationStepNameInput"),
  automationStepDetailInput: document.querySelector("#automationStepDetailInput"),
  automationStepIconInput: document.querySelector("#automationStepIconInput"),
  automationModuleTypeInput: document.querySelector("#automationModuleTypeInput"),
  automationModuleEnabledInput: document.querySelector("#automationModuleEnabledInput"),
  automationModuleStatus: document.querySelector("#automationModuleStatus"),
  automationModuleAddButton: document.querySelector("#automationModuleAddButton"),
  automationModuleDuplicateButton: document.querySelector("#automationModuleDuplicateButton"),
  automationModuleMoveLeftButton: document.querySelector("#automationModuleMoveLeftButton"),
  automationModuleMoveRightButton: document.querySelector("#automationModuleMoveRightButton"),
  automationModuleDeleteButton: document.querySelector("#automationModuleDeleteButton"),
  automationModuleSettings: document.querySelector("#automationModuleSettings"),
  automationPromptSourceSection: document.querySelector("#automationPromptSourceSection"),
  automationSheetInput: document.querySelector("#automationSheetInput"),
  automationSheetStatus: document.querySelector("#automationSheetStatus"),
  automationSheetPasteInput: document.querySelector("#automationSheetPasteInput"),
  automationSheetFileInput: document.querySelector("#automationSheetFileInput"),
  automationSheetFileButton: document.querySelector("#automationSheetFileButton"),
  automationSheetPreviewButton: document.querySelector("#automationSheetPreviewButton"),
  automationSheetPreviewList: document.querySelector("#automationSheetPreviewList"),
  automationProductFilterInput: document.querySelector("#automationProductFilterInput"),
  automationERPProjectInput: document.querySelector("#automationERPProjectInput"),
  automationERPProjectStorageInput: document.querySelector("#automationERPProjectStorageInput"),
  automationERPTaskInput: document.querySelector("#automationERPTaskInput"),
  automationERPStatusInput: document.querySelector("#automationERPStatusInput"),
  automationERPKeyInput: document.querySelector("#automationERPKeyInput"),
  automationERPSecretInput: document.querySelector("#automationERPSecretInput"),
  automationERPUploadMode: document.querySelector("#automationERPUploadMode"),
  automationERPUpscale2KInput: document.querySelector("#automationERPUpscale2KInput"),
  automationERPStatus: document.querySelector("#automationERPStatus"),
  automationERPSaveButton: document.querySelector("#automationERPSaveButton"),
  automationERPClearButton: document.querySelector("#automationERPClearButton"),
  automationERPSection: document.querySelector("#automationERPSection"),
  automationERPIdeaTaskInput: document.querySelector("#automationERPIdeaTaskInput"),
  automationERPIdeaCountInput: document.querySelector("#automationERPIdeaCountInput"),
  automationERPIdeaIncludeDoneInput: document.querySelector("#automationERPIdeaIncludeDoneInput"),
  automationERPIdeaRunButton: document.querySelector("#automationERPIdeaRunButton"),
  automationERPIdeaStatus: document.querySelector("#automationERPIdeaStatus"),
  erpSetupWizard: document.querySelector("#erpSetupWizard"),
  erpWizardKeyInput: document.querySelector("#erpWizardKeyInput"),
  erpWizardSecretInput: document.querySelector("#erpWizardSecretInput"),
  erpWizardBoardInput: document.querySelector("#erpWizardBoardInput"),
  erpWizardSaveButton: document.querySelector("#erpWizardSaveButton"),
  erpWizardLaterButton: document.querySelector("#erpWizardLaterButton"),
  erpWizardStatus: document.querySelector("#erpWizardStatus"),
  erpWizardCloseTriggers: Array.from(document.querySelectorAll("[data-erp-wizard-close]")),
  automationEnvStatus: document.querySelector("#automationEnvStatus"),
  automationGeminiKeyInput: document.querySelector("#automationGeminiKeyInput"),
  automationGeminiModelInput: document.querySelector("#automationGeminiModelInput"),
  automationPlaywrightPathInput: document.querySelector("#automationPlaywrightPathInput"),
  automationEnvSaveButton: document.querySelector("#automationEnvSaveButton"),
  automationEnvClearButton: document.querySelector("#automationEnvClearButton"),
  automationAppIntegrationsSection: document.querySelector("#automationAppIntegrationsSection"),
  automationAppEyebrowInput: document.querySelector("#automationAppEyebrowInput"),
  automationAppTitleInput: document.querySelector("#automationAppTitleInput"),
  automationAppSubtitleInput: document.querySelector("#automationAppSubtitleInput"),
  automationSourceLocationInput: document.querySelector("#automationSourceLocationInput"),
  automationAccentInput: document.querySelector("#automationAccentInput"),
  automationExportButton: document.querySelector("#automationExportButton"),
  automationImportButton: document.querySelector("#automationImportButton"),
  automationResetButton: document.querySelector("#automationResetButton"),
  automationImportFile: document.querySelector("#automationImportFile"),
  automationImageTotalCount: document.querySelector("#automationImageTotalCount"),
  automationActiveCount: document.querySelector("#automationActiveCount"),
  automationFailureCount: document.querySelector("#automationFailureCount"),
  automationCompletedCount: document.querySelector("#automationCompletedCount"),
  automationTransferHint: document.querySelector("#automationTransferHint"),
  automationRunningStatus: document.querySelector("#automationRunningStatus"),
  automationHistory: document.querySelector("#automationHistory"),
  messageBar: document.querySelector("#messageBar"),
  composerTitle: document.querySelector("#composerTitle"),
  composerHint: document.querySelector("#composerHint"),
  videoInputModeStrip: document.querySelector("#videoInputModeStrip"),
  videoInputModeNote: document.querySelector("#videoInputModeNote"),
  promptAiSummary: document.querySelector("#promptAiSummary"),
  promptAiBadge: document.querySelector("#promptAiBadge"),
  promptAiBriefLabel: document.querySelector("#promptAiBriefLabel"),
  promptAiBrief: document.querySelector("#promptAiBrief"),
  promptAiStyle: document.querySelector("#promptAiStyle"),
  promptAiMustInclude: document.querySelector("#promptAiMustInclude"),
  promptAiAvoid: document.querySelector("#promptAiAvoid"),
  promptAiAudience: document.querySelector("#promptAiAudience"),
  promptAiHint: document.querySelector("#promptAiHint"),
  promptAiSubmit: document.querySelector("#promptAiSubmit"),
  promptAiResult: document.querySelector("#promptAiResult"),
  promptAiResultTitle: document.querySelector("#promptAiResultTitle"),
  promptAiResultSummary: document.querySelector("#promptAiResultSummary"),
  promptAiSkillChips: document.querySelector("#promptAiSkillChips"),
  promptAiResultText: document.querySelector("#promptAiResultText"),
  usePromptAiResultButton: document.querySelector("#usePromptAiResultButton"),
  promptAiCard: document.querySelector("#promptAiCard"),
  storyboardCard: document.querySelector("#storyboardCard"),
  storyboardBadge: document.querySelector("#storyboardBadge"),
  storyboardScript: document.querySelector("#storyboardScript"),
  storyboardStyle: document.querySelector("#storyboardStyle"),
  storyboardMustInclude: document.querySelector("#storyboardMustInclude"),
  storyboardAvoid: document.querySelector("#storyboardAvoid"),
  storyboardSceneCount: document.querySelector("#storyboardSceneCount"),
  storyboardHint: document.querySelector("#storyboardHint"),
  storyboardPlanButton: document.querySelector("#storyboardPlanButton"),
  storyboardGenerateButton: document.querySelector("#storyboardGenerateButton"),
  storyboardResult: document.querySelector("#storyboardResult"),
  storyboardResultTitle: document.querySelector("#storyboardResultTitle"),
  storyboardResultMeta: document.querySelector("#storyboardResultMeta"),
  storyboardResultSummary: document.querySelector("#storyboardResultSummary"),
  storyboardSkillChips: document.querySelector("#storyboardSkillChips"),
  storyboardSceneList: document.querySelector("#storyboardSceneList"),
  promptLabel: document.querySelector("#promptLabel"),
  promptInput: document.querySelector("#promptInput"),
  composerSummaryMode: document.querySelector("#composerSummaryMode"),
  composerSummaryText: document.querySelector("#composerSummaryText"),
  composerPolicyNotice: document.querySelector("#composerPolicyNotice"),
  composerPolicyPill: document.querySelector("#composerPolicyPill"),
  composerPolicyTitle: document.querySelector("#composerPolicyTitle"),
  composerPolicyText: document.querySelector("#composerPolicyText"),
  composerPolicyList: document.querySelector("#composerPolicyList"),
  editActionStrip: document.querySelector("#editActionStrip"),
  editActionSummary: document.querySelector("#editActionSummary"),
  editActionSummaryTitle: document.querySelector("#editActionSummaryTitle"),
  editActionSummaryText: document.querySelector("#editActionSummaryText"),
  editActionButtons: Array.from(document.querySelectorAll("[data-edit-action]")),
  editSourceWrap: document.querySelector("#editSourceWrap"),
  editSourceCards: document.querySelector("#editSourceCards"),
  editSourceSelect: document.querySelector("#editSourceSelect"),
  manualMediaId: document.querySelector("#manualMediaId"),
  manualWorkflowId: document.querySelector("#manualWorkflowId"),
  startImageWrap: document.querySelector("#startImageWrap"),
  startImageFile: document.querySelector("#startImageFile"),
  startImageStatus: document.querySelector("#startImageStatus"),
  startImagePreview: document.querySelector("#startImagePreview"),
  startImagePreviewImage: document.querySelector("#startImagePreviewImage"),
  startImagePreviewName: document.querySelector("#startImagePreviewName"),
  startImagePreviewHint: document.querySelector("#startImagePreviewHint"),
  clearStartImageButton: document.querySelector("#clearStartImageButton"),
  imageReferenceWrap: document.querySelector("#imageReferenceWrap"),
  imageReferenceFiles: document.querySelector("#imageReferenceFiles"),
  imageReferenceTitle: document.querySelector("#imageReferenceTitle"),
  imageReferenceDescription: document.querySelector("#imageReferenceDescription"),
  imageReferenceFieldLabel: document.querySelector("#imageReferenceFieldLabel"),
  videoReferenceHero: document.querySelector("#videoReferenceHero"),
  videoReferenceHeroImage: document.querySelector("#videoReferenceHeroImage"),
  videoReferenceHeroTitle: document.querySelector("#videoReferenceHeroTitle"),
  videoReferenceHeroText: document.querySelector("#videoReferenceHeroText"),
  imageReferenceList: document.querySelector("#imageReferenceList"),
  imageReferenceStatus: document.querySelector("#imageReferenceStatus"),
  generationOptionsWrap: document.querySelector("#generationOptionsWrap"),
  modelSelect: document.querySelector("#modelSelect"),
  aspectChoices: document.querySelector("#aspectChoices"),
  countChoices: document.querySelector("#countChoices"),
  editOptionsWrap: document.querySelector("#editOptionsWrap"),
  motionField: document.querySelector("#motionField"),
  motionSelect: document.querySelector("#motionSelect"),
  positionField: document.querySelector("#positionField"),
  positionSelect: document.querySelector("#positionSelect"),
  resolutionField: document.querySelector("#resolutionField"),
  resolutionSelect: document.querySelector("#resolutionSelect"),
  aspectSelect: document.querySelector("#aspectSelect"),
  countInput: document.querySelector("#countInput"),
  readyHint: document.querySelector("#readyHint"),
  submitButton: document.querySelector("#submitButton"),
  composerForm: document.querySelector("#composerForm"),
  refreshButton: document.querySelector("#refreshButton"),
  latestStatusCard: document.querySelector("#latestStatusCard"),
  dashboardReviewQueue: document.querySelector("#dashboardReviewQueue"),
  modeButtons: Array.from(document.querySelectorAll(".mode-button")),
  videoInputModeButtons: Array.from(document.querySelectorAll("[data-video-input-mode]")),
};

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function normalizeHexColor(value, fallback = "#7c2ee6") {
  const raw = String(value || "").trim();
  const longMatch = raw.match(/^#?([0-9a-f]{6})$/i);
  if (longMatch) {
    return `#${longMatch[1].toLowerCase()}`;
  }
  const shortMatch = raw.match(/^#?([0-9a-f]{3})$/i);
  if (shortMatch) {
    return `#${shortMatch[1]
      .split("")
      .map((part) => `${part}${part}`)
      .join("")
      .toLowerCase()}`;
  }
  return fallback;
}

function hexToRgb(value) {
  const hex = normalizeHexColor(value).replace("#", "");
  const number = Number.parseInt(hex, 16);
  return {
    r: (number >> 16) & 255,
    g: (number >> 8) & 255,
    b: number & 255,
  };
}

function rgbToHex({ r, g, b }) {
  return `#${[r, g, b]
    .map((channel) => Math.max(0, Math.min(255, Math.round(channel))).toString(16).padStart(2, "0"))
    .join("")}`;
}

function mixHexColor(left, right, ratio = 0.22) {
  const a = hexToRgb(left);
  const b = hexToRgb(right);
  return rgbToHex({
    r: a.r * (1 - ratio) + b.r * ratio,
    g: a.g * (1 - ratio) + b.g * ratio,
    b: a.b * (1 - ratio) + b.b * ratio,
  });
}

function normalizeProjectInput(value) {
  const source = String(value || "").trim();
  if (!source) {
    return "";
  }

  let raw = source;
  try {
    const parsed = new URL(source);
    raw = parsed.pathname || source;
  } catch (error) {
    raw = source;
  }

  if (raw.includes("/project/")) {
    raw = raw.split("/project/").slice(-1)[0].trim();
  }

  raw = raw.split("?")[0].split("#")[0].trim().replace(/^\/+|\/+$/g, "");
  if (raw.includes("/")) {
    raw = raw.split("/")[0].trim();
  }

  try {
    raw = decodeURIComponent(raw);
  } catch (error) {
    raw = raw;
  }

  return raw;
}

function normalizePolicyText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function policyTextHasAny(value, terms) {
  const normalized = normalizePolicyText(value);
  if (!normalized) {
    return false;
  }
  return terms.some((term) => normalized.includes(term));
}

function currentComposerPolicyNotice() {
  if (state.mode === "edit") {
    return null;
  }
  const prompt = currentDraft().prompt || "";
  const hasMinor = policyTextHasAny(prompt, POLICY_MINOR_TERMS);
  const hasAppearance = policyTextHasAny(prompt, POLICY_APPEARANCE_TERMS);
  const hasApparel = policyTextHasAny(prompt, POLICY_APPAREL_TERMS);
  const hasReferenceImages = Boolean(state.startImagePath) || state.imageReferenceItems.length > 0;
  const hasProductImages = state.imageReferenceItems.some((item) => normalizeReferenceRole(item.role) === "product");
  const isProductVideoFlow = state.mode === "video" && currentVideoInputMode() === "reference";
  const isImageEditFlow = state.mode === "image" && state.imageReferenceItems.length > 0;
  const isStartVideoFlow = state.mode === "video" && currentVideoInputMode() === "start";

  if (hasMinor && (hasAppearance || hasApparel || hasReferenceImages)) {
    return {
      tone: "warning",
      pill: "Cảnh báo policy",
      title: "Prompt này có nguy cơ bị Flow chặn vì liên quan người có thể chưa đủ tuổi.",
      text: "Nếu ảnh hoặc mô tả ám chỉ người mẫu còn quá trẻ, Google Flow thường chặn các thao tác thay đồ, ghép logo lên áo, làm đẹp ngoại hình hoặc fashion edit.",
      tips: [
        "Đổi mô tả sang người mẫu trưởng thành rõ ràng, ví dụ: người mẫu trưởng thành 25 tuổi.",
        "Nếu chỉ cần demo sản phẩm, dùng mannequin, flat-lay hoặc áo treo thay vì người thật.",
        "Với luồng sản phẩm thành video, giữ ảnh sản phẩm nhưng mô tả rõ người mẫu trưởng thành.",
      ],
    };
  }

  if ((isProductVideoFlow || isImageEditFlow || isStartVideoFlow) && (hasAppearance || hasApparel || hasProductImages)) {
    return {
      tone: "watch",
      pill: "Gợi ý an toàn",
      title: "Flow có thể chặn nếu ảnh người mẫu trông quá trẻ.",
      text: "Luồng hiện tại đang chạm vào thay đồ, làm đẹp hoặc dựng người mẫu từ sản phẩm. Nếu ảnh tham chiếu là người trông nhỏ tuổi, Google Flow hay từ chối ngay từ bước upload hoặc generate.",
      tips: [
        "Giữ mô tả theo hướng người mẫu trưởng thành, mannequin hoặc ảnh flat-lay.",
        "Nếu chỉ muốn thử áo hoặc logo, dùng ảnh sản phẩm riêng thay vì ảnh người trông quá trẻ.",
      ],
    };
  }

  return null;
}

function formatTime(value) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
  }).format(date);
}

function truncate(value, length = 140) {
  const text = String(value || "").trim();
  if (text.length <= length) {
    return text;
  }
  return `${text.slice(0, length - 1)}…`;
}

function basename(value) {
  const text = String(value || "").trim();
  if (!text) {
    return "";
  }
  return text.split("/").pop() || text;
}

function fileKindLabel(count) {
  return count > 1 ? `${count} ảnh` : "1 ảnh";
}

function uploadPublicUrlFromPath(value) {
  const name = basename(value);
  if (!name) {
    return "";
  }
  return `/files/uploads/${encodeURIComponent(name)}`;
}

function statusLabel(status) {
  const map = {
    queued: "Đang xếp hàng",
    running: "Đang chạy",
    polling: "Đang xử lý",
    completed: "Hoàn tất",
    failed: "Lỗi",
    interrupted: "Bị ngắt",
  };
  return map[status] || status || "Không rõ";
}

function formatDuration(ms) {
  const totalSeconds = Math.max(0, Math.round(ms / 1000));
  if (totalSeconds < 60) {
    return `${totalSeconds} giây`;
  }
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes < 60) {
    return seconds ? `${minutes} phút ${seconds} giây` : `${minutes} phút`;
  }
  const hours = Math.floor(minutes / 60);
  const remainMinutes = minutes % 60;
  return remainMinutes ? `${hours} giờ ${remainMinutes} phút` : `${hours} giờ`;
}

async function api(path, options = {}) {
  const isFormData = options.body instanceof FormData;
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(options.headers || {}),
    },
  });

  const text = await response.text();
  let payload = {};
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch (error) {
      payload = { detail: text };
    }
  }

  if (!response.ok) {
    throw new Error(payload.detail || payload.error || "Có lỗi xảy ra.");
  }

  return payload;
}

function showMessage(message, tone = "neutral") {
  if (!message) {
    elements.messageBar.hidden = true;
    elements.messageBar.textContent = "";
    elements.messageBar.dataset.tone = "";
    return;
  }
  elements.messageBar.hidden = false;
  elements.messageBar.textContent = message;
  elements.messageBar.dataset.tone = tone;
}

function currentModeConfig() {
  return MODE_CONFIG[state.mode];
}

function currentEditConfig() {
  return EDIT_ACTION_CONFIG[state.editAction] || EDIT_ACTION_CONFIG.extend;
}

function currentOperationConfig() {
  if (state.mode === "edit") {
    const modeConfig = currentModeConfig();
    const editConfig = currentEditConfig();
    return {
      ...modeConfig,
      ...editConfig,
    };
  }
  return currentModeConfig();
}

function modeForJobType(jobType) {
  if (jobType === "image") {
    return "image";
  }
  if (EDIT_JOB_TYPES.has(jobType)) {
    return "edit";
  }
  return "video";
}

function currentDraft() {
  return state.drafts[state.mode];
}

function normalizeVideoInputMode(value) {
  const raw = String(value || "").trim().toLowerCase();
  if (raw === "start" || raw === "reference") {
    return raw;
  }
  return "prompt";
}

function currentVideoInputMode() {
  return normalizeVideoInputMode(state.drafts.video?.inputMode || "prompt");
}

function currentVideoInputConfig() {
  return VIDEO_INPUT_MODE_CONFIG[currentVideoInputMode()] || VIDEO_INPUT_MODE_CONFIG.prompt;
}

function currentPromptAiDraft() {
  return state.promptAiDrafts[state.mode] || null;
}

function currentPromptAiResult() {
  return state.promptAiResults[state.mode];
}

function modelOptionsForMode(mode) {
  if (mode === "image") {
    return state.modelOptions.image?.length ? state.modelOptions.image : FALLBACK_IMAGE_MODELS;
  }
  if (mode === "video") {
    return state.modelOptions.video?.length ? state.modelOptions.video : FALLBACK_VIDEO_MODELS;
  }
  return [];
}

function defaultModelForMode(mode) {
  return modelOptionsForMode(mode)[0]?.value || "";
}

function modelLabelForMode(mode, value) {
  const raw = String(value || "").trim();
  const matched = modelOptionsForMode(mode).find((item) => item.value === raw);
  if (matched) {
    return matched.label;
  }
  if (mode === "image") {
    if (raw === "GEMINI_3_PRO_IMAGE") {
      return "Nano Banana Pro";
    }
    if (raw === "NARWHAL") {
      return "Nano Banana 2";
    }
    if (raw === "IMAGEN_3") {
      return "Imagen 3";
    }
  }
  return raw;
}

function aspectTitle(value) {
  return ASPECT_DETAILS[String(value || "").trim()]?.title || "Ngang 16:9";
}

function referenceRoleLabel(value) {
  return REFERENCE_ROLE_OPTIONS.find((item) => item.value === value)?.label || "Tham chiếu";
}

function referenceRoleDetail(value) {
  return REFERENCE_ROLE_OPTIONS.find((item) => item.value === value)?.detail || "Ảnh phụ để tham chiếu.";
}

function normalizeReferenceRole(value) {
  const raw = String(value || "").trim().toLowerCase();
  if (raw === "base" || raw === "logo" || raw === "product" || raw === "reference") {
    return raw;
  }
  return "reference";
}

function referenceRoleOptionsForMode(mode) {
  if (mode === "video") {
    return REFERENCE_ROLE_OPTIONS.filter((item) => item.value !== "base");
  }
  return REFERENCE_ROLE_OPTIONS;
}

function primaryReferenceRoleForMode(mode = state.mode) {
  return mode === "video" ? "product" : "base";
}

function normalizeReferenceRoleForMode(value, mode, index = 0) {
  const role = normalizeReferenceRole(value);
  if (mode === "video" && role === "base") {
    return index === 0 ? "product" : "reference";
  }
  return role;
}

function ensurePrimaryReferenceRole(items, mode = state.mode) {
  if (!Array.isArray(items) || !items.length) {
    return [];
  }
  const primaryRole = primaryReferenceRoleForMode(mode);
  const normalized = items.map((item, index) => ({
    ...item,
    role: normalizeReferenceRoleForMode(item.role, mode, index),
  }));
  if (!normalized.some((item) => item.role === primaryRole)) {
    normalized[0] = { ...normalized[0], role: primaryRole };
  }
  return normalized;
}

function clearStartImageState({ resetInput = true } = {}) {
  state.startImagePath = "";
  state.startImageName = "";
  state.startImagePublicUrl = "";
  if (resetInput && elements.startImageFile) {
    elements.startImageFile.value = "";
  }
}

function clearReferenceImageState({ resetInput = true } = {}) {
  state.imageReferenceItems = [];
  if (resetInput && elements.imageReferenceFiles) {
    elements.imageReferenceFiles.value = "";
  }
}

function setVideoInputMode(mode, { clearConflicts = true, announce = false } = {}) {
  const nextMode = normalizeVideoInputMode(mode);
  const previousMode = currentVideoInputMode();
  state.drafts.video.inputMode = nextMode;

  if (clearConflicts) {
    if (nextMode === "prompt") {
      clearStartImageState();
      clearReferenceImageState();
    } else if (nextMode === "start") {
      clearReferenceImageState();
    } else if (nextMode === "reference") {
      clearStartImageState();
      state.imageReferenceItems = ensurePrimaryReferenceRole(state.imageReferenceItems, "video");
    }
  }

  if (announce && nextMode !== previousMode) {
    showMessage(currentVideoInputConfig().note, "success");
  }
}

function syncDraftFromForm() {
  const draft = currentDraft();
  draft.prompt = elements.promptInput.value;
  draft.model = elements.modelSelect.value || draft.model || defaultModelForMode(state.mode);
  draft.aspect = elements.aspectSelect.value;
  draft.count = Math.max(1, Math.min(4, Number(elements.countInput.value || draft.count || 1)));
}

function syncEditInputsFromForm() {
  state.selectedEditSourceKey = elements.editSourceSelect.value || "";
  state.manualMediaId = elements.manualMediaId.value.trim();
  state.manualWorkflowId = elements.manualWorkflowId.value.trim();
  state.motion = elements.motionSelect.value || "truck_left";
  state.position = elements.positionSelect.value || "center";
  state.resolution = elements.resolutionSelect.value || "1080p";
}

function syncPromptAiDraftFromForm() {
  const draft = currentPromptAiDraft();
  if (!draft) {
    return;
  }
  draft.brief = elements.promptAiBrief.value;
  draft.style = elements.promptAiStyle.value;
  draft.mustInclude = elements.promptAiMustInclude.value;
  draft.avoid = elements.promptAiAvoid.value;
  draft.audience = elements.promptAiAudience.value;
}

function syncStoryboardDraftFromForm() {
  state.storyboardDraft.script = elements.storyboardScript.value;
  state.storyboardDraft.style = elements.storyboardStyle.value;
  state.storyboardDraft.mustInclude = elements.storyboardMustInclude.value;
  state.storyboardDraft.avoid = elements.storyboardAvoid.value;
  state.storyboardDraft.sceneCount = elements.storyboardSceneCount.value || "0";
}

function applyDraftToForm() {
  const draft = currentDraft();
  const config = currentModeConfig();
  const options = modelOptionsForMode(state.mode);
  const fallbackModel = defaultModelForMode(state.mode);
  const nextModel = options.some((item) => item.value === draft.model) ? draft.model : fallbackModel;
  draft.model = nextModel;
  elements.promptInput.value = draft.prompt || "";
  elements.modelSelect.innerHTML = options
    .map((item) => `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`)
    .join("");
  elements.modelSelect.value = nextModel;
  elements.aspectSelect.value = draft.aspect || config.defaultAspect;
  elements.countInput.value = String(draft.count || config.defaultCount);
}

function applyEditInputsToForm() {
  elements.editSourceSelect.value = state.selectedEditSourceKey || "";
  elements.manualMediaId.value = state.manualMediaId || "";
  elements.manualWorkflowId.value = state.manualWorkflowId || "";
  elements.motionSelect.value = state.motion || "truck_left";
  elements.positionSelect.value = state.position || "center";
  elements.resolutionSelect.value = state.resolution || "1080p";
}

function renderAspectChoices() {
  const selected = String(elements.aspectSelect.value || currentDraft().aspect || currentModeConfig().defaultAspect).trim();
  const buttons = Array.from(elements.aspectChoices?.querySelectorAll("[data-aspect-option]") || []);
  for (const button of buttons) {
    button.classList.toggle("active", button.dataset.aspectOption === selected);
  }
}

function renderCountChoices() {
  const selected = String(elements.countInput.value || currentDraft().count || currentModeConfig().defaultCount);
  const buttons = Array.from(elements.countChoices?.querySelectorAll("[data-count-option]") || []);
  for (const button of buttons) {
    button.classList.toggle("active", button.dataset.countOption === selected);
  }
}

function applyPromptAiDraftToForm() {
  const draft = currentPromptAiDraft();
  if (!draft) {
    elements.promptAiBrief.value = "";
    elements.promptAiStyle.value = "";
    elements.promptAiMustInclude.value = "";
    elements.promptAiAvoid.value = "";
    elements.promptAiAudience.value = "";
    return;
  }
  elements.promptAiBrief.value = draft.brief || "";
  elements.promptAiStyle.value = draft.style || "";
  elements.promptAiMustInclude.value = draft.mustInclude || "";
  elements.promptAiAvoid.value = draft.avoid || "";
  elements.promptAiAudience.value = draft.audience || "";
}

function applyStoryboardDraftToForm() {
  elements.storyboardScript.value = state.storyboardDraft.script || "";
  elements.storyboardStyle.value = state.storyboardDraft.style || "";
  elements.storyboardMustInclude.value = state.storyboardDraft.mustInclude || "";
  elements.storyboardAvoid.value = state.storyboardDraft.avoid || "";
  elements.storyboardSceneCount.value = state.storyboardDraft.sceneCount || "0";
}

function isReady() {
  return Boolean(state.config?.project_id) && Boolean(state.auth?.authenticated);
}

function applyAutomationBranding() {
  const automation = normalizeAutomationConfig(state.automation);
  state.automation = automation;
  const eyebrow = automation.appEyebrow || "Flow v2";
  const title = automation.appTitle || "Flow v2";
  const accent = normalizeHexColor(automation.accentColor);
  const accentStrong = mixHexColor(accent, "#000000", 0.22);
  const accentSoft = mixHexColor(accent, "#ffffff", 0.9);
  const accentRing = mixHexColor(accent, "#ffffff", 0.74);
  document.documentElement.style.setProperty("--accent", accent);
  document.documentElement.style.setProperty("--accent-strong", accentStrong);
  document.documentElement.style.setProperty("--accent-soft", accentSoft);
  document.documentElement.style.setProperty("--accent-ring", accentRing);
  if (elements.automationBrandEyebrow) {
    elements.automationBrandEyebrow.textContent = eyebrow;
  }
  if (elements.automationBrandTitle) {
    elements.automationBrandTitle.textContent = title;
  }
  document.title = title && title !== "Flow v2" ? `${title} | Flow v2` : "Flow v2";
}

function renderTopbar() {
  applyAutomationBranding();
  const projectId = state.config?.project_id || "";
  const projectName = String(state.config?.project_name || "").trim();
  const activeJobs = (state.jobs || []).filter((job) => ACTIVE_STATUSES.has(job.status)).length;
  elements.projectStatus.textContent = projectId ? projectName || `Project ${truncate(projectId, 18)}` : "Chưa có project";
  elements.projectStatus.dataset.state = projectId ? "ready" : "pending";
  elements.authStatus.textContent = state.auth?.authenticated ? "Đã đăng nhập" : "Chưa đăng nhập";
  elements.authStatus.dataset.state = state.auth?.authenticated ? "ready" : "pending";
  elements.openFlowButton.textContent = projectId ? "Mở Flow" : "Mở đăng nhập";
  elements.logoutButton.hidden = !state.auth?.authenticated;
  elements.logoutButton.disabled = activeJobs > 0;
  elements.logoutButton.title = activeJobs > 0 ? "Hãy chờ các tác vụ đang chạy hoàn tất rồi đăng xuất." : "";
  elements.setupToggle.textContent = state.setupOpen ? "Ẩn thiết lập" : "Thiết lập";
  elements.setupPanel.hidden = !state.setupOpen;
  if (elements.automationEnabled) {
    elements.automationEnabled.checked = Boolean(state.automation?.enabled);
    elements.automationEnabled.closest(".scenario-toggle")?.querySelector("span")?.replaceChildren(
      document.createTextNode(state.automation?.enabled ? "Active" : "Inactive")
    );
  }

  if (!projectId) {
    elements.topbarHint.textContent = "Lưu project một lần rồi chỉ việc nhập prompt.";
  } else if (!state.auth?.authenticated) {
    elements.topbarHint.textContent = "Project đã có. Chỉ còn đăng nhập Google Flow là chạy được.";
  } else if (activeJobs) {
    elements.topbarHint.textContent = `Đang có ${activeJobs} lượt chạy. Tab Google Flow vẫn được giữ mở để bạn theo dõi trực tiếp.`;
  } else {
    elements.topbarHint.textContent =
      state.automation.appSubtitle || "Mọi thứ đã sẵn sàng. Nhập prompt rồi bấm chạy, tab Google Flow sẽ được giữ mở.";
  }

  if (document.activeElement !== elements.projectId) {
    elements.projectId.value = state.config?.project_url || state.config?.project_id || "";
  }
  if (document.activeElement !== elements.projectName) {
    elements.projectName.value = state.config?.project_name || "";
  }
  if (document.activeElement !== elements.generationTimeout) {
    elements.generationTimeout.value = String(state.config?.generation_timeout_s || 300);
  }
}

function automationStepConfig(stepKey) {
  state.automation.modules = normalizeAutomationModules(state.automation);
  let module = state.automation.modules.find((item) => item.id === stepKey);
  if (!module) {
    module = state.automation.modules.find((item) => item.type === "flow") || state.automation.modules[0] || createAutomationModule("custom", { id: "module_1" });
    state.automation.selectedStep = module.id;
  }
  state.automation.steps = automationStepsFromModules(state.automation.modules);
  return module;
}

function selectedAutomationModule() {
  return automationStepConfig(state.automation.selectedStep);
}

function selectedAutomationModuleIndex() {
  state.automation.modules = normalizeAutomationModules(state.automation);
  return Math.max(0, state.automation.modules.findIndex((module) => module.id === state.automation.selectedStep));
}

function persistAutomationModules() {
  state.automation.steps = automationStepsFromModules(state.automation.modules);
  saveAutomationConfig(state.automation);
}

function renderAutomationCanvasControls() {
  const zoom = clampAutomationCanvasZoom(state.automation.canvasZoom);
  state.automation.canvasZoom = zoom;
  if (elements.scenarioNodeRow) {
    elements.scenarioNodeRow.style.zoom = String(zoom);
  }
  if (elements.automationZoomReset) {
    elements.automationZoomReset.textContent = `${Math.round(zoom * 100)}%`;
  }
  if (elements.automationZoomOut) {
    elements.automationZoomOut.disabled = zoom <= AUTOMATION_CANVAS_ZOOM_MIN + 0.01;
  }
  if (elements.automationZoomIn) {
    elements.automationZoomIn.disabled = zoom >= AUTOMATION_CANVAS_ZOOM_MAX - 0.01;
  }
}

function setAutomationCanvasZoom(value, { keepCenter = true } = {}) {
  const canvas = elements.scenarioCanvas;
  const previousZoom = clampAutomationCanvasZoom(state.automation.canvasZoom);
  const nextZoom = clampAutomationCanvasZoom(value);
  if (Math.abs(previousZoom - nextZoom) < 0.005) {
    renderAutomationCanvasControls();
    return;
  }
  const centerX = canvas ? canvas.scrollLeft + canvas.clientWidth / 2 : 0;
  const centerY = canvas ? canvas.scrollTop + canvas.clientHeight / 2 : 0;
  state.automation.canvasZoom = nextZoom;
  saveAutomationConfig(state.automation);
  renderAutomationCanvasControls();
  if (canvas && keepCenter) {
    const ratio = nextZoom / previousZoom;
    canvas.scrollTo({
      left: Math.max(0, centerX * ratio - canvas.clientWidth / 2),
      top: Math.max(0, centerY * ratio - canvas.clientHeight / 2),
      behavior: "smooth",
    });
  }
}

function fitAutomationCanvas() {
  if (!elements.scenarioCanvas || !elements.scenarioNodeRow) {
    return;
  }
  const currentZoom = clampAutomationCanvasZoom(state.automation.canvasZoom);
  const baseWidth = Math.max(1, (elements.scenarioNodeRow.scrollWidth || 820) / currentZoom);
  const availableWidth = Math.max(320, elements.scenarioCanvas.clientWidth - 96);
  const nextZoom = clampAutomationCanvasZoom(Math.min(1, availableWidth / baseWidth));
  setAutomationCanvasZoom(nextZoom, { keepCenter: false });
  window.setTimeout(() => {
    elements.scenarioCanvas.scrollTo({
      left: Math.max(0, (elements.scenarioNodeRow.scrollWidth - elements.scenarioCanvas.clientWidth) / 2),
      top: 0,
      behavior: "smooth",
    });
  }, 0);
}

function scrollAutomationNodeIntoView(stepId = state.automation.selectedStep) {
  const safeStepId = window.CSS?.escape
    ? CSS.escape(String(stepId))
    : String(stepId).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  const selector = `[data-scenario-step="${safeStepId}"]`;
  const node = elements.scenarioNodeRow?.querySelector(selector);
  node?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
}

function automationModuleEnabled(type) {
  state.automation.modules = normalizeAutomationModules(state.automation);
  return state.automation.modules.some((module) => module.type === type && module.enabled !== false);
}

function selectAutomationModuleByType(type, { create = false } = {}) {
  state.automation.modules = normalizeAutomationModules(state.automation);
  let module = state.automation.modules.find((item) => item.type === type);
  if (!module && create) {
    module = createAutomationModule(type);
    state.automation.modules.push(module);
  }
  if (!module) {
    return null;
  }
  state.automation.selectedStep = module.id;
  persistAutomationModules();
  renderAutomationDashboard();
  window.setTimeout(() => scrollAutomationNodeIntoView(module.id), 0);
  return module;
}

function addAutomationModule({ duplicate = false } = {}) {
  state.automation.modules = normalizeAutomationModules(state.automation);
  const index = selectedAutomationModuleIndex();
  const selected = state.automation.modules[index] || createAutomationModule("custom");
  const seed = duplicate
    ? {
        ...selected,
        id: "",
        title: `${selected.title || moduleTypeConfig(selected.type).title} copy`,
        settings: { ...(selected.settings || {}) },
      }
    : {};
  const module = createAutomationModule(duplicate ? selected.type : "custom", seed);
  state.automation.modules.splice(index + 1, 0, module);
  state.automation.selectedStep = module.id;
  persistAutomationModules();
  renderAutomationDashboard();
  window.setTimeout(() => scrollAutomationNodeIntoView(module.id), 0);
  showMessage(duplicate ? "Đã nhân bản cục đang chọn." : "Đã thêm một cục mới sau module đang chọn.", "success");
}

function deleteSelectedAutomationModule() {
  state.automation.modules = normalizeAutomationModules(state.automation);
  if (state.automation.modules.length <= 1) {
    showMessage("Cần giữ lại ít nhất một cục trong luồng.", "error");
    return;
  }
  const index = selectedAutomationModuleIndex();
  state.automation.modules.splice(index, 1);
  const next = state.automation.modules[Math.max(0, index - 1)] || state.automation.modules[0];
  state.automation.selectedStep = next.id;
  persistAutomationModules();
  renderAutomationDashboard();
  showMessage("Đã xóa cục khỏi luồng.", "success");
}

function moveSelectedAutomationModule(direction) {
  state.automation.modules = normalizeAutomationModules(state.automation);
  const index = selectedAutomationModuleIndex();
  const nextIndex = index + direction;
  if (nextIndex < 0 || nextIndex >= state.automation.modules.length) {
    return;
  }
  const [module] = state.automation.modules.splice(index, 1);
  state.automation.modules.splice(nextIndex, 0, module);
  persistAutomationModules();
  renderAutomationDashboard();
  window.setTimeout(() => scrollAutomationNodeIntoView(module.id), 0);
}

function syncAutomationFromForm() {
  if (!elements.automationPromptInput) {
    return;
  }
  state.automation.enabled = Boolean(elements.automationEnabled?.checked);
  state.automation.prompt = elements.automationPromptInput.value;
  state.automation.sourceType = elements.automationSourceType.value || FLOW_AI_SOURCE_TYPE;
  state.automation.sourceLocation = elements.automationSourceLocationInput.value.trim();
  state.automation.promptProductFilter = elements.automationProductFilterInput?.value?.trim() || "";
  state.automation.sheetLog = elements.automationSheetInput?.value?.trim() || state.automation.sheetLog || "";
  state.automation.erpProjectId =
    elements.automationERPProjectInput?.value?.trim() ||
    elements.automationERPProjectStorageInput?.value?.trim() ||
    "";
  state.automation.erpTaskId = elements.automationERPTaskInput.value.trim();
  state.automation.erpStatusId = elements.automationERPStatusInput.value.trim();
  state.automation.appEyebrow = elements.automationAppEyebrowInput.value.trim() || "Flow v2";
  state.automation.appTitle = elements.automationAppTitleInput.value.trim() || "Flow v2";
  state.automation.appSubtitle =
    elements.automationAppSubtitleInput.value.trim() ||
    "Mọi thứ đã sẵn sàng. Nhập prompt rồi bấm chạy, tab Google Flow sẽ được giữ mở.";
  state.automation.accentColor = normalizeHexColor(elements.automationAccentInput.value, "#7c2ee6");

  const selected = state.automation.selectedStep || "flow";
  const current = automationStepConfig(selected);
  const selectedType = elements.automationModuleTypeInput?.value || current.type || "custom";
  const typeChanged = selectedType !== current.type;
  current.type = selectedType;
  const typeDefaults = moduleTypeConfig(selectedType);
  current.title = typeChanged ? typeDefaults.title : elements.automationStepNameInput.value.trim() || current.title || typeDefaults.title;
  current.detail = typeChanged ? typeDefaults.detail : elements.automationStepDetailInput.value.trim() || current.detail || typeDefaults.detail;
  current.icon = typeChanged ? typeDefaults.icon : (elements.automationStepIconInput?.value || "").trim() || current.icon || typeDefaults.icon;
  current.enabled = elements.automationModuleEnabledInput ? Boolean(elements.automationModuleEnabledInput.checked) : current.enabled !== false;
  state.automation.steps = automationStepsFromModules(state.automation.modules);
  saveAutomationConfig(state.automation);
}

function automationJobs() {
  return (state.jobs || []).filter((job) => job.type === "image" || job.type === "batch_image");
}

function activeContinuousAutoERPJob() {
  return automationJobs().find((job) => {
    if (!ACTIVE_STATUSES.has(job.status) || job.type !== "batch_image") {
      return false;
    }
    const input = job.input || {};
    const result = job.result || {};
    return Boolean(input.continuous || result.continuous);
  }) || null;
}

function automationStepTone(module, stats) {
  const executionNode = latestAutomationExecutionNode(module);
  if (executionNode) {
    const status = String(executionNode.status || "").toLowerCase();
    if (status === "running") {
      return "active";
    }
    if (status === "completed") {
      return "done";
    }
    if (status === "skipped") {
      return "watch";
    }
    if (status === "failed") {
      if ((module.type || module.id) === "erp_source" && erpSourceIsReady(module)) {
        return "ready";
      }
      return "blocked";
    }
  }
  if (module.enabled === false) {
    return "disabled";
  }
  const stepKey = module.type || module.id;
  if (stepKey === "source") {
    return state.automation.prompt.trim() || shouldAutoDiscoverERP() ? "done" : state.automation.sourceType === "manual" ? "watch" : "pending";
  }
  if (stepKey === "erp_source") {
    return erpSourceIsReady(module) ? "ready" : "blocked";
  }
  if (stepKey === "normalize") {
    return state.automation.prompt.trim() || shouldAutoDiscoverERP() ? "done" : "pending";
  }
  if (stepKey === "flow") {
    if (!state.config?.project_id || !state.auth?.authenticated) {
      return "blocked";
    }
    if (stats.active.length) {
      return "active";
    }
    return stats.completed.length ? "done" : "ready";
  }
  if (stepKey === "watermark") {
    if (state.integrations?.removelogo?.enabled === false) {
      return "disabled";
    }
    if (stats.active.length) {
      return "active";
    }
    return stats.completed.length ? "done" : "ready";
  }
  if (stepKey === "approval") {
    if (stats.active.length) {
      return "pending";
    }
    return stats.completed.length ? "watch" : "pending";
  }
  if (stepKey === "erp") {
    return stats.completed.length ? "ready" : "pending";
  }
  return "pending";
}

function erpSourceIsReady(module = {}) {
  if (!state.erp?.credentials_saved) {
    return false;
  }
  const settings = module.settings || {};
  const task = settings.erpTask || state.automation.erpTaskId || state.erp?.task_id || "";
  const status = settings.erpStatus || state.automation.erpStatusId || state.erp?.status || "";
  const project = currentERPProjectId();
  return Boolean(task || (project && status));
}

function latestAutomationExecutionNode(module) {
  const jobs = automationJobs()
    .slice()
    .sort((left, right) => new Date(right.updated_at || right.created_at || 0).getTime() - new Date(left.updated_at || left.created_at || 0).getTime());
  for (const job of jobs) {
    if (!ACTIVE_STATUSES.has(job.status) && job.status !== "completed") {
      continue;
    }
    const execution = job.result?.automation_execution;
    const nodes = Array.isArray(execution?.nodes) ? execution.nodes : [];
    const matched = nodes.find((node) => node.id === module.id) || nodes.find((node) => node.type === module.type);
    if (matched) {
      const nodeStatus = String(matched.status || "").toLowerCase();
      if (nodeStatus === "running" && !ACTIVE_STATUSES.has(job.status)) {
        continue;
      }
      return matched;
    }
  }
  return null;
}

function automationNodeStatusLabel(status) {
  const labels = {
    active: "Đang chạy",
    blocked: "Cần thiết lập",
    disabled: "Đang tắt",
    done: "Xong",
    pending: "Chưa chạy",
    ready: "Sẵn sàng",
    watch: "Chờ duyệt",
  };
  return labels[status] || "Chưa chạy";
}

function renderAutomationNodes(stats) {
  state.automation.modules = normalizeAutomationModules(state.automation);
  if (elements.breakRoute) {
    elements.breakRoute.hidden = true;
  }
  if (!elements.scenarioNodeRow) {
    return;
  }
  elements.scenarioNodeRow.innerHTML = state.automation.modules
    .map((module, index) => {
      const typeConfig = moduleTypeConfig(module.type);
      const iconClass = typeConfig.iconClass || "node-icon-custom";
      const status = automationStepTone(module, stats);
      const active = state.automation.selectedStep === module.id ? " active" : "";
      const disabled = module.enabled === false ? " module-disabled" : "";
      const link = index > 0 ? `<span class="scenario-link" aria-hidden="true"></span>` : "";
      return `
        ${link}
        <button type="button" class="scenario-node${active}${disabled}" data-scenario-step="${escapeHtml(module.id)}" data-status="${escapeHtml(status)}" aria-pressed="${state.automation.selectedStep === module.id ? "true" : "false"}" draggable="true" title="Bấm để chỉnh, kéo để đổi vị trí">
          <span class="node-order">${index + 1}</span>
          <span class="node-icon ${escapeHtml(iconClass)}">${escapeHtml(module.icon || typeConfig.icon)}</span>
          <strong>${escapeHtml(module.title || typeConfig.title)}</strong>
          <small>${escapeHtml(module.detail || typeConfig.detail)}</small>
          <span class="node-state">${escapeHtml(automationNodeStatusLabel(status))}</span>
        </button>
      `;
    })
    .join("");
}

function renderAutomationInspector(stats) {
  const selected = state.automation.selectedStep || "flow";
  const selectedConfig = automationStepConfig(selected);
  const selectedType = selectedConfig.type || "custom";
  const typeDefaults = moduleTypeConfig(selectedType);
  if (document.activeElement !== elements.automationStepNameInput) {
    elements.automationStepNameInput.value = selectedConfig.title || "";
  }
  if (document.activeElement !== elements.automationStepDetailInput) {
    elements.automationStepDetailInput.value = selectedConfig.detail || "";
  }
  if (elements.automationModuleTypeInput && document.activeElement !== elements.automationModuleTypeInput) {
    elements.automationModuleTypeInput.value = selectedType;
  }
  if (elements.automationStepIconInput && document.activeElement !== elements.automationStepIconInput) {
    elements.automationStepIconInput.value = selectedConfig.icon || typeDefaults.icon || "";
  }
  if (elements.automationModuleEnabledInput && document.activeElement !== elements.automationModuleEnabledInput) {
    elements.automationModuleEnabledInput.checked = selectedConfig.enabled !== false;
  }
  if (elements.automationModuleStatus) {
    elements.automationModuleStatus.textContent = `${typeDefaults.label}${selectedConfig.enabled === false ? " tắt" : ""}`;
    elements.automationModuleStatus.dataset.state = selectedConfig.enabled === false ? "pending" : "ready";
  }
  if (elements.automationPromptSourceSection) {
    elements.automationPromptSourceSection.hidden = selectedType !== "source";
  }
  if (elements.automationERPSection) {
    elements.automationERPSection.hidden = selectedType !== "erp";
  }
  if (elements.automationAppIntegrationsSection) {
    elements.automationAppIntegrationsSection.hidden = selectedType !== "flow";
  }
  renderModuleSettings(selectedConfig);
  if (document.activeElement !== elements.automationSheetInput) {
    if (elements.automationSheetInput) {
      elements.automationSheetInput.value = state.automation.sheetLog || "";
    }
  }
  const boardValue = state.automation.erpProjectId || state.erp?.project_id || "";
  if (document.activeElement !== elements.automationERPProjectInput && elements.automationERPProjectInput) {
    elements.automationERPProjectInput.value = boardValue;
  }
  if (document.activeElement !== elements.automationERPProjectStorageInput && elements.automationERPProjectStorageInput) {
    elements.automationERPProjectStorageInput.value = boardValue;
  }
  if (document.activeElement !== elements.automationERPTaskInput) {
    elements.automationERPTaskInput.value = state.automation.erpTaskId || state.erp?.task_id || "";
  }
  if (document.activeElement !== elements.automationERPStatusInput) {
    elements.automationERPStatusInput.value = state.automation.erpStatusId || state.erp?.status || "";
  }
  if (elements.automationGeminiModelInput && document.activeElement !== elements.automationGeminiModelInput) {
    elements.automationGeminiModelInput.value = state.integrations?.gemini?.model || "gemini-2.5-flash";
  }
  if (elements.automationPlaywrightPathInput && document.activeElement !== elements.automationPlaywrightPathInput) {
    elements.automationPlaywrightPathInput.value = state.integrations?.runtime?.playwright_browsers_path || "";
  }
  if (document.activeElement !== elements.automationPromptInput) {
    elements.automationPromptInput.value = state.automation.prompt || "";
  }
  if (document.activeElement !== elements.automationSourceType) {
    elements.automationSourceType.value = state.automation.sourceType || FLOW_AI_SOURCE_TYPE;
  }
  if (document.activeElement !== elements.automationSourceLocationInput) {
    elements.automationSourceLocationInput.value = state.automation.sourceLocation || "";
  }
  if (elements.automationProductFilterInput && document.activeElement !== elements.automationProductFilterInput) {
    elements.automationProductFilterInput.value = state.automation.promptProductFilter || "";
  }
  if (document.activeElement !== elements.automationAppEyebrowInput) {
    elements.automationAppEyebrowInput.value = state.automation.appEyebrow || "Flow v2";
  }
  if (document.activeElement !== elements.automationAppTitleInput) {
    elements.automationAppTitleInput.value = state.automation.appTitle || "Flow v2";
  }
  if (document.activeElement !== elements.automationAppSubtitleInput) {
    elements.automationAppSubtitleInput.value =
      state.automation.appSubtitle || "Mọi thứ đã sẵn sàng. Nhập prompt rồi bấm chạy, tab Google Flow sẽ được giữ mở.";
  }
  if (document.activeElement !== elements.automationAccentInput) {
    elements.automationAccentInput.value = normalizeHexColor(state.automation.accentColor, "#7c2ee6");
  }

  elements.automationImageTotalCount.textContent = String(stats.completed.length);
  elements.automationActiveCount.textContent = String(stats.active.length);
  elements.automationFailureCount.textContent = String(stats.failed.length);
  elements.automationCompletedCount.textContent = String(stats.completed.length);
  elements.automationTransferHint.textContent = modelLabelForMode("image", state.drafts.image.model || defaultModelForMode("image")) || "Flow";
  elements.automationRunningStatus.textContent = stats.active.length ? `${stats.active.length} execution running` : "No execution";
  elements.automationRunningStatus.dataset.state = stats.active.length ? "ready" : "pending";

  if (elements.automationERPStatus) {
    const envBased = state.erp?.credentials_source === "env";
    if (state.erp?.configured) {
      elements.automationERPStatus.textContent = envBased
        ? "Đã sẵn sàng (.env.local)"
        : "Đã sẵn sàng";
      elements.automationERPStatus.dataset.state = "ready";
    } else if (state.erp?.credentials_saved) {
      elements.automationERPStatus.textContent = envBased
        ? "Thiếu Project/Task/trạng thái (API key/secret từ .env.local)"
        : "Thiếu Project/Task/trạng thái";
      elements.automationERPStatus.dataset.state = "pending";
    } else if (state.erp?.project_id || state.erp?.task_id || state.erp?.status) {
      elements.automationERPStatus.textContent = "Thiếu API key/secret";
      elements.automationERPStatus.dataset.state = "pending";
    } else {
      elements.automationERPStatus.textContent = "Chưa lưu";
      elements.automationERPStatus.dataset.state = "pending";
    }
  }

  if (elements.automationEnvStatus) {
    const configuredCount = [
      state.integrations?.gemini?.configured,
      state.integrations?.runtime?.playwright_browsers_path_set,
    ].filter(Boolean).length;
    if (configuredCount >= 2) {
      elements.automationEnvStatus.textContent = `${configuredCount}/2 đã lưu`;
      elements.automationEnvStatus.dataset.state = "ready";
    } else if (configuredCount === 1) {
      elements.automationEnvStatus.textContent = "1/2 đã lưu";
      elements.automationEnvStatus.dataset.state = "pending";
    } else {
      elements.automationEnvStatus.textContent = "Chưa lưu";
      elements.automationEnvStatus.dataset.state = "pending";
    }
  }
  renderPromptSourcePreview();
}

function renderModuleSettings(module) {
  if (!elements.automationModuleSettings) {
    return;
  }
  const type = module.type || "custom";
  const settings = module.settings || {};
  if (type === "source") {
    const rawSourceType = settings.sourceType || state.automation.sourceType || FLOW_AI_SOURCE_TYPE;
    const sourceType = rawSourceType === "ai" ? FLOW_AI_SOURCE_TYPE : rawSourceType;
    elements.automationModuleSettings.innerHTML = `
      <label class="field">
        <span>Nguồn của cục này</span>
        <select data-module-setting="sourceType">
          <option value="flow_ai"${sourceType === FLOW_AI_SOURCE_TYPE ? " selected" : ""}>Tác nhân Flow tự viết prompt</option>
          <option value="manual"${sourceType === "manual" ? " selected" : ""}>Nhập tay / clipboard</option>
          <option value="erp"${sourceType === "erp" ? " selected" : ""}>ERP Task</option>
          <option value="sheets"${sourceType === "sheets" ? " selected" : ""}>Google Sheets / Excel</option>
          <option value="folder"${sourceType === "folder" ? " selected" : ""}>Folder / CSV nội bộ</option>
        </select>
      </label>
      <label class="field">
        <span>Sheet / CSV link tùy chọn</span>
        <input type="text" data-module-setting="sourceLocation" value="${escapeHtml(settings.sourceLocation || state.automation.sourceLocation || "")}" placeholder="Chỉ dán nếu muốn dùng prompt có sẵn" />
      </label>
      <label class="field">
        <span>Lọc sản phẩm</span>
        <input type="text" data-module-setting="promptProductFilter" value="${escapeHtml(settings.promptProductFilter || state.automation.promptProductFilter || "")}" placeholder="Ví dụ: tote_bag, áo, wedding_hoop" />
      </label>
      <div class="customize-actions source-actions">
        <button type="button" class="ghost-button card-button" data-module-action="preview-source">Lấy prompt tùy chọn</button>
        <button type="button" class="ghost-button card-button" data-module-action="upload-source">Upload file</button>
      </div>
    `;
    return;
  }
  if (type === "flow") {
    const imageModel = settings.imageModel || state.drafts.image.model;
    const imageAspect = settings.imageAspect || state.drafts.image.aspect;
    const imageCount = flowModuleImageCount(settings, state.drafts.image.count || MODE_CONFIG.image.defaultCount);
    const flowAgentEnabled = flowAgentEnabledFromSettings(settings);
    const imageCountMax = flowAgentEnabled ? FLOW_AGENT_TARGET_OUTPUT_COUNT : 4;
    const flowAgentAutoApprove = settings.flowAgentAutoApprove !== false;
    elements.automationModuleSettings.innerHTML = `
      <label class="field">
        <span>Model ảnh Flow</span>
        <select data-module-setting="imageModel">
          ${state.modelOptions.image.map((item) => `<option value="${escapeHtml(item.value)}"${imageModel === item.value ? " selected" : ""}>${escapeHtml(item.label)}</option>`).join("")}
        </select>
      </label>
      <div class="detail-grid sidebar-detail-grid">
        <label class="field">
          <span>Tỷ lệ ảnh</span>
          <select data-module-setting="imageAspect">
            <option value="square"${imageAspect === "square" ? " selected" : ""}>Vuông 1:1</option>
            <option value="landscape"${imageAspect === "landscape" ? " selected" : ""}>Ngang 16:9</option>
            <option value="portrait"${imageAspect === "portrait" ? " selected" : ""}>Dọc 9:16</option>
          </select>
        </label>
        <label class="field">
          <span>Số ảnh</span>
          <input type="number" min="1" max="${imageCountMax}" step="1" data-module-setting="imageCount" value="${escapeHtml(imageCount)}" />
        </label>
      </div>
      <label class="inline-check module-check">
        <input type="checkbox" data-module-setting="flowAgentEnabled"${flowAgentEnabled ? " checked" : ""} />
        <span>Dùng nút Tác nhân trong Google Flow khi có thể</span>
      </label>
      <label class="inline-check module-check">
        <input type="checkbox" data-module-setting="flowAgentAutoApprove"${flowAgentAutoApprove ? " checked" : ""} />
        <span>Tự phê duyệt Tác nhân Flow khi Flow hỏi xác nhận</span>
      </label>
    `;
    return;
  }
  if (type === "erp_source") {
    elements.automationModuleSettings.innerHTML = `
      <label class="field">
        <span>HaviGroup ERP Project (theo cấu hình)</span>
        <input type="text" value="${escapeHtml(currentERPProjectId())}" readonly aria-readonly="true" />
      </label>
      <label class="field">
        <span>Task lấy ảnh gốc</span>
        <input type="text" data-module-setting="erpTask" value="${escapeHtml(settings.erpTask || state.automation.erpTaskId || state.erp?.task_id || "")}" placeholder="TASK-xxxx" />
      </label>
      <label class="field">
        <span>Trạng thái nguồn tùy chọn</span>
        <input type="text" data-module-setting="erpStatus" value="${escapeHtml(settings.erpStatus || state.automation.erpStatusId || state.erp?.status || "")}" placeholder="Trạng thái nguồn, ví dụ Open" />
      </label>
      <label class="field">
        <span>Ảnh ERP đã chọn (URL HTTPS công khai)</span>
        <input type="text" data-module-setting="erpAttachmentIds" value="${escapeHtml(
          Array.isArray(settings.erpAttachmentIds)
            ? settings.erpAttachmentIds.join(", ")
            : Array.isArray(state.automation.erpAttachmentIds)
              ? state.automation.erpAttachmentIds.join(", ")
              : "",
        )}" placeholder="Attachment ID, bấm thumbnail trong trợ lý để tự điền" />
      </label>
      <label class="field">
        <span>Số ảnh lấy tối đa</span>
        <input type="number" min="1" max="4" step="1" data-module-setting="erpAttachmentLimit" value="${escapeHtml(settings.erpAttachmentLimit || 1)}" />
      </label>
      <small>Bấm thumbnail trong trợ lý để khóa đúng ảnh. ERP chỉ đọc URL HTTPS công khai; nếu không chọn ảnh cụ thể, app dùng ảnh đầu tiên của Task.</small>
    `;
    return;
  }
  if (type === "erp") {
    elements.automationModuleSettings.innerHTML = `
      <label class="field">
        <span>Task nguồn để ghi comment</span>
        <input type="text" data-module-setting="erpTask" value="${escapeHtml(settings.erpTask || state.automation.erpTaskId || state.erp?.task_id || "")}" placeholder="TASK-xxxx" />
      </label>
      <label class="field">
        <span>Nguyên tắc lưu</span>
        <small>Chỉ URL ảnh HTTPS được duyệt ngay trên dashboard mới được ghi bằng GraphQL comment. App không tạo Task, upload file hoặc đổi trạng thái.</small>
      </label>
      <div class="customize-actions source-actions">
        <button type="button" class="ghost-button card-button" data-module-action="save-erp">Lưu ERP</button>
        <button type="button" class="ghost-button card-button" data-module-action="clear-erp">Xóa API credential</button>
      </div>
    `;
    return;
  }
  if (type === "approval") {
    elements.automationModuleSettings.innerHTML = `
      <label class="field">
        <span>Trạng thái duyệt</span>
        <small>Duyệt ngay trên dashboard. Ảnh bị từ chối hoặc chưa có quyết định sẽ không được ghi vào ERP.</small>
      </label>
      <small>Khi đủ quyết định cho tất cả ảnh, app tự ghi URL artefact đã duyệt vào comment của đúng ERP Task.</small>
    `;
    return;
  }
  elements.automationModuleSettings.innerHTML = `
    <label class="field">
      <span>Ghi chú riêng của cục custom</span>
      <textarea rows="3" data-module-setting="customNote" placeholder="Ghi lại cục này dùng để làm gì">${escapeHtml(settings.customNote || "")}</textarea>
    </label>
    <label class="field">
      <span>Webhook/API URL</span>
      <input type="url" data-module-setting="customWebhookUrl" value="${escapeHtml(settings.customWebhookUrl || "")}" placeholder="https://example.com/webhook" />
    </label>
    <div class="detail-grid sidebar-detail-grid">
      <label class="field">
        <span>Method</span>
        <select data-module-setting="customWebhookMethod">
          ${["POST", "PUT", "PATCH", "GET", "DELETE"].map((method) => `<option value="${method}"${(settings.customWebhookMethod || "POST") === method ? " selected" : ""}>${method}</option>`).join("")}
        </select>
      </label>
      <label class="field">
        <span>Timeout giây</span>
        <input type="number" min="3" max="120" step="1" data-module-setting="customWebhookTimeout" value="${escapeHtml(settings.customWebhookTimeout || 20)}" />
      </label>
    </div>
    <label class="field">
      <span>Headers JSON hoặc từng dòng Key: Value</span>
      <textarea rows="3" data-module-setting="customWebhookHeaders" placeholder='{"Authorization":"Bearer ..."}'>${escapeHtml(settings.customWebhookHeaders || "")}</textarea>
    </label>
    <label class="field">
      <span>Body template</span>
      <textarea rows="6" data-module-setting="customWebhookBody" placeholder='Để trống để app tự gửi job/prompt/artifacts. Có thể dùng {{job_id}}, {{prompt}}, {{first_artifact_url}}, {{artifacts}}.'>${escapeHtml(settings.customWebhookBody || "")}</textarea>
    </label>
    <small>Cục custom sẽ chạy thật nếu có URL. Dữ liệu ảnh/prompt/job tự được gắn vào payload.</small>
  `;
}

function renderPromptSourcePreview() {
  const preview = state.promptSourcePreview;
  if (elements.automationSheetStatus) {
    if (state.automation.sourceType !== "sheets") {
      elements.automationSheetStatus.textContent = "Flow AI";
      elements.automationSheetStatus.dataset.state = "ready";
    } else if (preview?.prompt_count) {
      elements.automationSheetStatus.textContent = `${preview.active_count || preview.prompt_count} prompt`;
      elements.automationSheetStatus.dataset.state = "ready";
    } else if (state.automation.prompt?.trim()) {
      elements.automationSheetStatus.textContent = "Đã có prompt";
      elements.automationSheetStatus.dataset.state = "ready";
    } else {
      elements.automationSheetStatus.textContent = "Chưa lấy";
      elements.automationSheetStatus.dataset.state = "pending";
    }
  }
  if (!elements.automationSheetPreviewList) {
    return;
  }
  const items = preview?.preview || [];
  if (!items.length) {
    elements.automationSheetPreviewList.innerHTML =
      state.automation.sourceType === "sheets"
        ? `<p class="empty-automation-history">Dán link, upload file hoặc paste bảng rồi bấm lấy prompt.</p>`
        : `<p class="empty-automation-history">Đang dùng Tác nhân Flow: app chỉ chọn ảnh ERP và gửi lệnh, prompt ảnh cuối do Google Flow tự viết.</p>`;
    return;
  }
  const totalActive = Number(preview?.active_count || items.length || 0);
  const extraCount = Math.max(0, totalActive - items.length);
  elements.automationSheetPreviewList.innerHTML = items
    .map((item) => {
      const label = [item.product, item.index ? `#${item.index}` : "", item.notes].filter(Boolean).join(" · ");
      return `
        <article class="automation-history-item">
          <strong>${escapeHtml(label || `Row ${item.row}`)}</strong>
          <small>${escapeHtml(item.prompt)}</small>
        </article>
      `;
    })
    .join("") + (extraCount ? `<p class="empty-automation-history">Còn ${extraCount} prompt active nữa sẽ được chạy trong vòng lặp.</p>` : "");
}

function renderAutomationHistory(stats) {
  const items = automationJobs()
    .slice()
    .sort((left, right) => new Date(right.created_at || 0).getTime() - new Date(left.created_at || 0).getTime())
    .slice(0, 5);

  if (!items.length) {
    elements.automationHistory.className = "automation-history empty-automation-history";
    elements.automationHistory.textContent = "Chưa có lượt chạy ảnh nào.";
    return;
  }

  elements.automationHistory.className = "automation-history";
  elements.automationHistory.innerHTML = items
    .map((job) => {
      const prompt = truncate(job.input?.prompt || "", 96) || "Không có prompt";
      return `
        <article class="automation-history-item">
          <div>
            <strong>${escapeHtml(job.title || "Flow image")}</strong>
            <small>${escapeHtml(formatTime(job.created_at))} · ${escapeHtml(statusLabel(job.status))}</small>
          </div>
          <p>${escapeHtml(prompt)}</p>
        </article>
      `;
    })
    .join("");
}

function automationPanelItem(job) {
  const prompt = truncate(job.input?.prompt || "", 132) || "Không có prompt";
  const status = statusLabel(job.status);
  const model = modelLabelForMode("image", job.input?.model || defaultModelForMode("image")) || "Flow";
  return `
    <article class="scenario-table-row">
      <div>
        <strong>${escapeHtml(job.title || "Flow image")}</strong>
        <small>${escapeHtml(formatTime(job.created_at))} · ${escapeHtml(status)} · ${escapeHtml(model)}</small>
      </div>
      <p>${escapeHtml(prompt)}</p>
    </article>
  `;
}

function renderAutomationViewPanels(stats) {
  const selectedView = state.automation.view || "diagram";
  for (const button of elements.automationViewButtons) {
    button.classList.toggle("active", button.dataset.automationView === selectedView);
  }

  elements.scenarioCanvas.hidden = selectedView !== "diagram";
  if (elements.automationEasyPanel) {
    elements.automationEasyPanel.hidden = selectedView !== "diagram";
  }
  elements.scenarioHistoryPanel.hidden = selectedView !== "history";
  elements.scenarioIncompletePanel.hidden = selectedView !== "incomplete";

  const command = document.querySelector(".automation-command");
  const usage = document.querySelector(".scenario-usage");
  if (command) {
    command.hidden = selectedView !== "diagram";
  }
  if (usage) {
    usage.hidden = selectedView !== "diagram";
  }

  const allJobs = automationJobs()
    .slice()
    .sort((left, right) => new Date(right.created_at || 0).getTime() - new Date(left.created_at || 0).getTime());
  const incomplete = allJobs.filter((job) => job.status === "failed" || job.status === "interrupted");

  elements.automationHistoryPanelList.innerHTML = allJobs.length
    ? allJobs.slice(0, 16).map(automationPanelItem).join("")
    : `<div class="scenario-panel-empty">Chưa có lượt chạy ảnh nào.</div>`;
  elements.automationIncompletePanelList.innerHTML = incomplete.length
    ? incomplete.slice(0, 16).map(automationPanelItem).join("")
    : `<div class="scenario-panel-empty">Không có execution nào cần xử lý.</div>`;
}

function activePromptSourceItems({ limit = 40, ignoreFilter = false } = {}) {
  if (state.automation.sourceType !== "sheets") {
    return [];
  }
  const items = Array.isArray(state.promptSourcePreview?.items) ? state.promptSourcePreview.items : [];
  const filter = ignoreFilter ? "" : String(state.automation.promptProductFilter || "").trim();
  const normalizedItems = items
    .filter((item) => item?.active !== false && String(item?.prompt || "").trim())
    .filter((item) => item?.used !== true)
    .filter((item) => {
      if (!filter) {
        return true;
      }
      const haystackValues = [
        item.product,
        item.product_key,
        item.product_name,
        item.notes,
      ];
      return productFilterMatches(haystackValues, filter);
    })
    .map((item) => ({
      row: Number(item.row || 0),
      active: true,
      used: false,
      prompt: String(item.prompt || "").trim(),
      product: String(item.product || "").trim(),
      product_key: String(item.product_key || "").trim(),
      product_name: String(item.product_name || "").trim(),
      index: String(item.index || "").trim(),
      notes: String(item.notes || "").trim(),
      erp_task_id: String(item.erp_task_id || "").trim(),
      erp_status_id: String(item.erp_status_id || "").trim(),
    }));
  return Number.isFinite(limit) ? normalizedItems.slice(0, Math.max(1, limit)) : normalizedItems;
}

function normalizeMatchText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

function matchTokens(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .match(/[a-z0-9]+/g) || [];
}

function productFilterGroups(filter) {
  const tokens = matchTokens(filter).filter((token) => token.length > 1);
  const groups = tokens.length ? [tokens] : [];
  const tokenSet = new Set(tokens);
  const compact = normalizeMatchText(filter);
  const wantsShirt = tokenSet.has("ao") || tokenSet.has("shirt") || tokenSet.has("tshirt") || tokenSet.has("tee");
  const wantsChild =
    ["tre", "em", "kid", "kids", "baby", "child", "children", "youth", "toddler"].some((token) => tokenSet.has(token)) ||
    compact.includes("treem");
  if (wantsShirt && !wantsChild) {
    groups.push(["shirt"], ["tshirt"], ["tee"]);
  }
  if (wantsShirt && wantsChild) {
    groups.push(
      ["shirt", "kids"],
      ["shirt", "kid"],
      ["shirt", "baby"],
      ["shirt", "child"],
      ["shirt", "children"],
      ["shirt", "youth"],
      ["shirt", "toddler"],
      ["tshirt", "kids"],
      ["tshirt", "baby"],
      ["tee", "kids"],
      ["tee", "baby"],
    );
  }
  const seen = new Set();
  return groups.filter((group) => {
    const key = group.join("|");
    if (!group.length || seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function productFilterMatches(values, filter) {
  const query = normalizeMatchText(filter);
  if (!query) {
    return true;
  }
  const haystack = values.map((value) => String(value || "")).join(" ");
  const haystackCompact = normalizeMatchText(haystack);
  if (query && haystackCompact && (haystackCompact.includes(query) || query.includes(haystackCompact))) {
    return true;
  }
  const tokenSet = new Set(matchTokens(haystack));
  return productFilterGroups(filter).some((group) => group.length && group.every((token) => tokenSet.has(token)));
}

function shouldAutoDiscoverERP(batchItems = activePromptSourceItems({ limit: 500 })) {
  if (!automationModuleEnabled("erp_source")) {
    return false;
  }
  const project = currentERPProjectId();
  const sourceType = String(state.automation.sourceType || FLOW_AI_SOURCE_TYPE);
  const hasPrompt = Boolean(String(state.automation.prompt || "").trim());
  return Boolean(
    project &&
      (
        sourceType === FLOW_AI_SOURCE_TYPE ||
        sourceType === "sheets" ||
        sourceType === "erp" ||
        batchItems.length ||
        !hasPrompt
      )
  );
}

function effectiveAutomationBatchLimit({ autoERP = false } = {}) {
  return automationModuleEnabled("erp_source") && !autoERP ? 1 : (autoERP ? 0 : 40);
}

function renderEasyPanel(stats) {
  const batchItems = activePromptSourceItems();
  const autoERPReady = shouldAutoDiscoverERP(batchItems);
  const continuousAutoJob = activeContinuousAutoERPJob();
  const batchLimit = effectiveAutomationBatchLimit({ autoERP: autoERPReady });
  const displayedBatchCount = batchItems.length > 1 ? Math.min(batchItems.length, batchLimit) : batchItems.length;
  const promptReady = Boolean(String(state.automation.prompt || "").trim()) || batchItems.length > 0 || autoERPReady;
  const projectReady = Boolean(state.config?.project_id);
  const flowModuleReady = automationModuleEnabled("flow");
  const flowReady = flowModuleReady && projectReady && Boolean(state.auth?.authenticated);
  const erpReady = automationModuleEnabled("erp") && Boolean(
    state.erp?.configured ||
    state.automation.erpProjectId ||
    state.automation.erpTaskId ||
    state.automation.erpStatusId
  );

  if (elements.easyPromptStatus) {
    elements.easyPromptStatus.textContent = autoERPReady && !batchItems.length
      ? "Tác nhân Flow viết prompt"
      : batchItems.length > 1 ? `${batchItems.length} prompt active` : promptReady ? "Đã có prompt" : "Nhập yêu cầu hoặc Auto ERP";
  }
  if (elements.easyFlowStatus) {
    elements.easyFlowStatus.textContent = flowReady ? "Đã sẵn sàng" : !flowModuleReady ? "Thiếu cục Flow" : projectReady ? "Cần đăng nhập" : "Cần project";
  }
  if (elements.easyReviewStatus) {
    elements.easyReviewStatus.textContent = erpReady ? "Duyệt tại dashboard" : "Cần ERP";
  }
  const runHint = elements.easyRunButton?.querySelector("small");
  if (runHint) {
    runHint.textContent = stats.active.length
      ? "Đang tạo ảnh"
      : autoERPReady && flowReady
        ? `Chạy đến hết ${DEFAULT_ERP_SOURCE_SCOPE_LABEL}`
      : batchItems.length > 1 && flowReady
        ? batchLimit === 1
          ? "Chạy 1 prompt/ERP Task"
          : "Chạy vòng lặp sheet"
        : promptReady && flowReady ? "Sẵn sàng chạy" : "Bấm để chạy";
  }
  if (elements.automationRunImageButton) {
    elements.automationRunImageButton.textContent = autoERPReady
      ? (displayedBatchCount ? `Auto ${displayedBatchCount} prompt` : `Auto hết ${DEFAULT_ERP_SOURCE_SCOPE_LABEL}`)
      : batchItems.length > 1 ? `Tạo ${displayedBatchCount} prompt` : "Tạo ảnh bằng Flow";
  }
  if (elements.automationAutoRunButton) {
    elements.automationAutoRunButton.textContent = continuousAutoJob ? "Dừng auto" : "Bật auto liên tục";
    elements.automationAutoRunButton.disabled = !continuousAutoJob && (stats.active.length > 0 || !automationModuleEnabled("erp_source") || !automationModuleEnabled("erp"));
  }
  if (elements.automationRunButton) {
    elements.automationRunButton.textContent = autoERPReady ? "Chạy 1 lượt" : batchItems.length > 1 ? "Chạy batch" : "Chạy thử";
  }
  elements.easyPromptButton?.classList.toggle("ready", promptReady);
  elements.easyFlowButton?.classList.toggle("ready", flowReady);
  elements.easyReviewButton?.classList.toggle("ready", erpReady);
  elements.easyRunButton?.classList.toggle("ready", promptReady && flowReady && !stats.active.length);
  if (elements.easyRunButton) {
    elements.easyRunButton.disabled = stats.active.length > 0;
  }
}

function renderAutomationDashboard() {
  if (!elements.scenarioCanvas) {
    return;
  }
  const jobs = automationJobs();
  const stats = {
    active: jobs.filter((job) => ACTIVE_STATUSES.has(job.status)),
    completed: jobs.filter((job) => job.status === "completed"),
    failed: jobs.filter((job) => job.status === "failed" || job.status === "interrupted"),
  };
  renderAutomationNodes(stats);
  renderAutomationCanvasControls();
  renderAutomationInspector(stats);
  renderAutomationHistory(stats);
  renderAutomationViewPanels(stats);
  renderEasyPanel(stats);
}

function renderComposer() {
  const config = currentOperationConfig();
  const videoInput = state.mode === "video" ? currentVideoInputConfig() : null;
  elements.composerTitle.textContent = config.title;
  elements.composerHint.textContent = videoInput?.hint || config.hint;
  elements.promptLabel.textContent = config.promptLabel;
  elements.promptInput.placeholder = videoInput?.placeholder || config.placeholder || "";
  elements.submitButton.textContent = config.submitLabel;
  elements.videoInputModeStrip.hidden = state.mode !== "video";
  elements.videoInputModeNote.hidden = state.mode !== "video";
  elements.startImageWrap.hidden = !(state.mode === "video" && config.showStartImage && currentVideoInputMode() === "start");
  elements.imageReferenceWrap.hidden = !(state.mode === "image" || (state.mode === "video" && currentVideoInputMode() === "reference"));
  elements.readyHint.textContent = isReady()
    ? `${videoInput?.readyText || config.readyText} Tab Google Flow sẽ được giữ mở sau khi gửi.`
    : "Lưu project và đăng nhập một lần rồi bấm chạy.";
  elements.promptLabel.parentElement.hidden = Boolean(state.mode === "edit" && !config.showPrompt);

  for (const button of elements.modeButtons) {
    button.classList.toggle("active", button.dataset.mode === state.mode);
  }
  for (const button of elements.videoInputModeButtons) {
    button.classList.toggle("active", button.dataset.videoInputMode === currentVideoInputMode());
  }
  elements.videoInputModeNote.textContent = videoInput?.note || "";

  applyDraftToForm();
  renderAspectChoices();
  renderCountChoices();
  renderEditControls();
  renderComposerSummary();
  renderUploadStatus();
  renderImageReferenceStatus();
  if (currentModeConfig().showPromptAi) {
    renderPromptAssistant();
  }
  renderStoryboardCard();
}

function renderComposerSummary() {
  if (state.mode === "edit") {
    const source = selectedEditSource();
    const action = currentEditConfig();
    elements.composerSummaryMode.textContent = action.title;
    if (source) {
      elements.composerSummaryText.textContent = `Đang dùng ${source.title} làm nguồn để ${action.title.toLowerCase()}.`;
    } else if (state.manualMediaId && state.manualWorkflowId) {
      elements.composerSummaryText.textContent = "Đang dùng Media ID và Workflow ID nhập tay cho thao tác chỉnh video này.";
    } else {
      elements.composerSummaryText.textContent = "Chọn video cần chỉnh rồi bấm chạy.";
    }
    renderComposerPolicyNotice();
    return;
  }

  if (state.mode === "image") {
    const modelLabel = modelLabelForMode("image", currentDraft().model);
    if (state.imageReferenceItems.length) {
      const baseItem = state.imageReferenceItems.find((item) => item.role === "base") || state.imageReferenceItems[0];
      const logoCount = state.imageReferenceItems.filter((item) => item.role === "logo").length;
      const productCount = state.imageReferenceItems.filter((item) => item.role === "product").length;
      elements.composerSummaryMode.textContent = "Chỉnh ảnh từ ảnh tham chiếu";
      elements.composerSummaryText.textContent = `Đang dùng ${fileKindLabel(state.imageReferenceItems.length)} để ghép hoặc chỉnh bằng model ${modelLabel}. Ảnh chính là ${baseItem?.name || "ảnh đầu tiên"}${logoCount ? `, có thêm ${logoCount} logo` : ""}${productCount ? `, ${productCount} ảnh sản phẩm` : ""}.`;
      renderComposerPolicyNotice();
      return;
    }
    elements.composerSummaryMode.textContent = "Ảnh từ prompt";
    elements.composerSummaryText.textContent = `App sẽ tạo ảnh trực tiếp từ mô tả vừa nhập bằng model ${modelLabel}.`;
    renderComposerPolicyNotice();
    return;
  }

  const videoModelLabel = modelLabelForMode("video", currentDraft().model);
  if (currentVideoInputMode() === "reference") {
    if (!state.imageReferenceItems.length) {
      elements.composerSummaryMode.textContent = "Sản phẩm -> người mẫu -> video";
      elements.composerSummaryText.textContent = `Thêm ít nhất 1 ảnh sản phẩm, logo hoặc ảnh tham chiếu. App sẽ tự dựng khung đầu rồi tạo video bằng model ${videoModelLabel}.`;
      renderComposerPolicyNotice();
      return;
    }
    const productCount = state.imageReferenceItems.filter((item) => normalizeReferenceRole(item.role) === "product").length;
    const logoCount = state.imageReferenceItems.filter((item) => normalizeReferenceRole(item.role) === "logo").length;
    elements.composerSummaryMode.textContent = "Sản phẩm -> người mẫu -> video";
    elements.composerSummaryText.textContent = `App sẽ tự dựng một ảnh khung đầu từ ${fileKindLabel(state.imageReferenceItems.length)} rồi tạo video luôn bằng model ${videoModelLabel}.${productCount ? ` Có ${productCount} ảnh sản phẩm` : ""}${logoCount ? ` và ${logoCount} logo` : ""}.`;
    renderComposerPolicyNotice();
    return;
  }
  if (currentVideoInputMode() === "start") {
    if (!state.startImagePath) {
      elements.composerSummaryMode.textContent = "Video từ ảnh";
      elements.composerSummaryText.textContent = `Chọn một ảnh đầu vào để app animate từ khung đầu tiên bằng model ${videoModelLabel}.`;
      renderComposerPolicyNotice();
      return;
    }
    elements.composerSummaryMode.textContent = "Video từ ảnh";
    elements.composerSummaryText.textContent = `Đang dùng ${state.startImageName || "ảnh đầu vào"} làm khung đầu tiên bằng model ${videoModelLabel}.`;
    renderComposerPolicyNotice();
    return;
  }

  elements.composerSummaryMode.textContent = "Video từ prompt";
  elements.composerSummaryText.textContent = `Không có ảnh đầu vào. App sẽ tạo video trực tiếp từ mô tả vừa nhập bằng model ${videoModelLabel}.`;
  renderComposerPolicyNotice();
}

function renderComposerPolicyNotice() {
  const notice = currentComposerPolicyNotice();
  if (!notice) {
    elements.composerPolicyNotice.hidden = true;
    elements.composerPolicyNotice.dataset.tone = "";
    elements.composerPolicyPill.textContent = "";
    elements.composerPolicyTitle.textContent = "";
    elements.composerPolicyText.textContent = "";
    elements.composerPolicyList.innerHTML = "";
    return;
  }
  elements.composerPolicyNotice.hidden = false;
  elements.composerPolicyNotice.dataset.tone = notice.tone || "watch";
  elements.composerPolicyPill.textContent = notice.pill || "Gợi ý an toàn";
  elements.composerPolicyTitle.textContent = notice.title || "";
  elements.composerPolicyText.textContent = notice.text || "";
  elements.composerPolicyList.innerHTML = (notice.tips || [])
    .map((tip) => `<li>${escapeHtml(tip)}</li>`)
    .join("");
}

function renderUploadStatus() {
  if (state.mode !== "video" || currentVideoInputMode() !== "start") {
    return;
  }
  const hasImage = Boolean(state.startImagePath);
  elements.startImagePreview.hidden = !hasImage;
  if (hasImage) {
    elements.startImagePreviewImage.src = state.startImagePublicUrl || uploadPublicUrlFromPath(state.startImagePath);
    elements.startImagePreviewName.textContent = state.startImageName || "Ảnh đầu vào";
    elements.startImagePreviewHint.textContent = "Video sẽ bám theo ảnh này khi render trên Google Flow.";
  } else {
    elements.startImagePreviewImage.removeAttribute("src");
    elements.startImagePreviewName.textContent = "Ảnh đầu vào";
    elements.startImagePreviewHint.textContent = "Video sẽ bám theo ảnh này khi render.";
  }
  if (state.uploading) {
    elements.startImageStatus.textContent = "Đang tải ảnh đầu vào...";
    return;
  }
  if (hasImage) {
    elements.startImageStatus.textContent = `Đã gắn ${state.startImageName || "ảnh đầu vào"}. App sẽ tạo video từ ảnh này.`;
    return;
  }
  elements.startImageStatus.textContent = "Chưa có ảnh đầu vào. Hãy chọn một ảnh để app animate từ khung đầu này.";
}

function availableVideoSources() {
  const shelfItems = (state.outputShelf?.items || []).filter((item) => {
    const mimeType = String(item.mime_type || "");
    return mimeType.startsWith("video/") || item.job_type === "video" || EDIT_JOB_TYPES.has(item.job_type);
  });

  const deduped = [];
  const seen = new Set();
  for (const item of shelfItems) {
    const mediaId = String(item.media_id || "").trim();
    const workflowId = String(item.workflow_id || "").trim();
    if (!mediaId || !workflowId) {
      continue;
    }
    const key = `${mediaId}::${workflowId}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    deduped.push({
      key,
      mediaId,
      workflowId,
      label: `${item.job_title || item.title || "Video"} · ${formatTime(item.created_at)}`,
      title: item.title || item.job_title || "Video gần đây",
      previewUrl: item.preview_url || item.local_file_url || item.source_url || "",
      prompt: String(item.prompt || "").trim(),
      createdAt: item.created_at || "",
      mimeType: item.mime_type || "",
    });
  }
  return deduped;
}

function selectedEditSource() {
  const items = availableVideoSources();
  return items.find((item) => item.key === state.selectedEditSourceKey) || null;
}

function renderEditControls() {
  const isEdit = state.mode === "edit";
  elements.editActionStrip.hidden = !isEdit;
  elements.editActionSummary.hidden = !isEdit;
  elements.editSourceWrap.hidden = !isEdit;
  elements.generationOptionsWrap.hidden = isEdit;
  elements.promptAiCard.hidden = !currentModeConfig().showPromptAi;

  if (!isEdit) {
    elements.editOptionsWrap.hidden = true;
    return;
  }

  for (const button of elements.editActionButtons) {
    button.classList.toggle("active", button.dataset.editAction === state.editAction);
  }

  const action = currentEditConfig();
  elements.editActionSummaryTitle.textContent = action.title;
  elements.editActionSummaryText.textContent = action.hint;

  const sources = availableVideoSources();
  const options = ['<option value="">Chọn một video</option>']
    .concat(
      sources.map(
        (item) => `<option value="${escapeHtml(item.key)}">${escapeHtml(item.label)}</option>`
      )
    )
    .join("");
  elements.editSourceSelect.innerHTML = options;
  if (!state.selectedEditSourceKey && !state.manualMediaId && !state.manualWorkflowId && sources[0]) {
    state.selectedEditSourceKey = sources[0].key;
  }
  if (!sources.some((item) => item.key === state.selectedEditSourceKey)) {
    state.selectedEditSourceKey = "";
  }

  elements.editSourceCards.innerHTML = sources.length
    ? sources
        .map((item) => {
          const active = item.key === state.selectedEditSourceKey;
          const prompt = truncate(item.prompt || "", 88) || "Không có prompt lưu cùng video này.";
          const mediaPreview = String(item.previewUrl || "").trim();
          return `
            <button
              type="button"
              class="source-card${active ? " active" : ""}"
              data-action="pick-edit-source"
              data-key="${escapeHtml(item.key)}"
            >
              ${
                mediaPreview
                  ? mediaPreview.includes(".mp4") || String(item.mimeType || "").startsWith("video/")
                    ? `<video class="source-card-media" src="${escapeHtml(mediaPreview)}" muted playsinline preload="metadata"></video>`
                    : `<img class="source-card-media" src="${escapeHtml(mediaPreview)}" alt="${escapeHtml(item.title)}" />`
                  : `<div class="source-card-placeholder">Không có preview</div>`
              }
              <div class="source-card-copy">
                <strong>${escapeHtml(item.title)}</strong>
                <small>${escapeHtml(formatTime(item.createdAt))}</small>
                <p>${escapeHtml(prompt)}</p>
              </div>
            </button>
          `;
        })
        .join("")
    : `<div class="empty-inline-card">Chưa có video gần đây để chọn. Khi chưa thấy nguồn ở đây, có thể mở phần nhập tay bên dưới.</div>`;

  applyEditInputsToForm();

  const hasOptions = action.showMotion || action.showPosition || action.showResolution;
  elements.editOptionsWrap.hidden = !hasOptions;
  elements.motionField.hidden = !action.showMotion;
  elements.positionField.hidden = !action.showPosition;
  elements.resolutionField.hidden = !action.showResolution;
}

function renderImageReferenceStatus() {
  if (state.mode !== "image" && !(state.mode === "video" && currentVideoInputMode() === "reference")) {
    return;
  }

  const isVideo = state.mode === "video";
  elements.imageReferenceTitle.textContent = isVideo
    ? "Ảnh sản phẩm hoặc ảnh tham chiếu"
    : "Ảnh tham chiếu để ghép hoặc chỉnh";
  elements.imageReferenceDescription.textContent = isVideo
    ? "Ví dụ: đưa ảnh áo hoặc sản phẩm vào đây. App sẽ tự dựng một ảnh người mẫu/keyframe trước, rồi dùng chính ảnh đó để tạo video luôn."
    : "Ví dụ: một ảnh người mẫu và một ảnh logo áo. Sau đó viết yêu cầu như “ghép logo này lên áo của người mẫu”.";
  elements.imageReferenceFieldLabel.textContent = isVideo
    ? "Chọn 1 đến 4 ảnh sản phẩm hoặc ảnh tham chiếu"
    : "Chọn 1 đến 4 ảnh tham chiếu";

  const items = state.imageReferenceItems || [];
  if (state.uploading && !items.length) {
    elements.videoReferenceHero.hidden = true;
    elements.imageReferenceList.hidden = true;
    elements.imageReferenceList.innerHTML = "";
    elements.imageReferenceStatus.textContent = isVideo ? "Đang tải ảnh sản phẩm/tham chiếu..." : "Đang tải ảnh tham chiếu...";
    return;
  }
  if (!items.length) {
    elements.videoReferenceHero.hidden = true;
    elements.videoReferenceHeroImage.removeAttribute("src");
    elements.videoReferenceHeroTitle.textContent = "Chưa có ảnh chính";
    elements.videoReferenceHeroText.textContent = "App sẽ ưu tiên ảnh này để dựng người mẫu hoặc keyframe trước khi tạo video.";
    elements.imageReferenceList.hidden = true;
    elements.imageReferenceList.innerHTML = "";
    elements.imageReferenceStatus.textContent = isVideo
      ? "Chưa có ảnh tham chiếu. Nếu thêm ảnh ở đây, app sẽ tự dựng khung đầu rồi tạo video luôn."
      : "Chưa có ảnh tham chiếu. Nếu thêm ảnh ở đây, app sẽ dùng chúng để ghép/chỉnh ảnh.";
    return;
  }

  elements.imageReferenceList.hidden = false;
  const primaryItem = isVideo
    ? items.find((item) => normalizeReferenceRole(item.role) === "product") || items[0]
    : items.find((item) => normalizeReferenceRole(item.role) === "base") || items[0];
  elements.videoReferenceHero.hidden = !isVideo;
  if (isVideo && primaryItem) {
    elements.videoReferenceHeroImage.src = primaryItem.publicUrl || uploadPublicUrlFromPath(primaryItem.path);
    elements.videoReferenceHeroTitle.textContent = primaryItem.name || "Ảnh sản phẩm chính";
    elements.videoReferenceHeroText.textContent = "App sẽ ưu tiên ảnh này để dựng người mẫu hoặc keyframe đầu tiên trước khi tạo video.";
  }
  elements.imageReferenceList.innerHTML = items
    .map((item, index) => {
      const source = item.publicUrl || uploadPublicUrlFromPath(item.path);
      const role = normalizeReferenceRoleForMode(item.role || (index === 0 ? primaryReferenceRoleForMode(state.mode) : "reference"), state.mode, index);
      const roleOptions = referenceRoleOptionsForMode(state.mode).map(
        (option) => `<option value="${escapeHtml(option.value)}"${option.value === role ? " selected" : ""}>${escapeHtml(option.label)}</option>`
      ).join("");
      const isPrimary = isVideo ? role === "product" : role === "base";
      return `
        <article class="upload-preview reference-card${isPrimary ? " is-primary" : ""}">
          <img class="upload-preview-image" src="${escapeHtml(source)}" alt="${escapeHtml(item.name || "Ảnh tham chiếu")}" />
          <div class="upload-preview-copy">
            <strong>${escapeHtml(item.name || "Ảnh tham chiếu")}</strong>
            <p>${escapeHtml(referenceRoleDetail(role))}</p>
            <div class="reference-card-actions">
              <span class="reference-role-pill">${escapeHtml(referenceRoleLabel(role))}</span>
              ${
                isVideo && !isPrimary
                  ? `<button type="button" class="ghost-button card-button" data-action="promote-reference-image" data-index="${index}">Ưu tiên ảnh này</button>`
                  : ""
              }
            </div>
            <label class="field inline-role-field">
              <span>Vai trò</span>
              <select data-action="reference-role" data-index="${index}">
                ${roleOptions}
              </select>
            </label>
          </div>
          <button type="button" class="ghost-button card-button" data-action="remove-reference-image" data-index="${index}">Bỏ ảnh</button>
        </article>
      `;
    })
    .join("");
  elements.imageReferenceStatus.textContent = isVideo
    ? `Đã gắn ${fileKindLabel(items.length)}. App sẽ dùng ${primaryItem?.name || "ảnh đầu tiên"} làm sản phẩm hoặc ảnh chính để dựng khung đầu, rồi mới tạo video.`
    : `Đã gắn ${fileKindLabel(items.length)}. Ảnh chính hiện là ${primaryItem?.name || "ảnh đầu tiên"}, các ảnh còn lại sẽ được dùng theo vai trò đã chọn.`;
}

function renderPromptAiResult() {
  const result = currentPromptAiResult();
  if (!result?.prompt) {
    elements.promptAiResult.hidden = true;
    elements.promptAiResultSummary.textContent = "";
    elements.promptAiResultText.textContent = "";
    elements.promptAiSkillChips.hidden = true;
    elements.promptAiSkillChips.innerHTML = "";
    return;
  }

  elements.promptAiResult.hidden = false;
  elements.promptAiResultTitle.textContent = result.title || (state.mode === "video" ? "Prompt video" : "Prompt ảnh");
  elements.promptAiResultSummary.textContent = result.summary || "AI đã viết prompt xong.";
  elements.promptAiResultText.textContent = result.prompt || "";

  const skills = Array.isArray(result.applied_skills) ? result.applied_skills.filter(Boolean) : [];
  if (skills.length) {
    elements.promptAiSkillChips.hidden = false;
    elements.promptAiSkillChips.innerHTML = skills
      .slice(0, 6)
      .map((skill) => `<span class="skill-chip">${escapeHtml(skill)}</span>`)
      .join("");
  } else {
    elements.promptAiSkillChips.hidden = true;
    elements.promptAiSkillChips.innerHTML = "";
  }
}

function renderPromptAssistant() {
  const config = currentModeConfig();
  const assistant = state.promptAssistant || {};
  elements.promptAiBriefLabel.textContent = config.promptAiLabel || "Bạn muốn tạo gì?";
  elements.promptAiBrief.placeholder = config.promptAiPlaceholder || "Mô tả ý muốn ở đây.";

  const skillCount = Number(assistant.skill_count || 0);
  const ready = Boolean(assistant.ready) && skillCount > 0;
  const engineLabel = assistant.engine_label || "Nội bộ";

  elements.promptAiBadge.textContent = ready ? engineLabel : "Đang nạp skill";
  elements.promptAiBadge.dataset.state = ready ? "ready" : "pending";
  elements.promptAiSummary.textContent =
    assistant.headline ||
    "Công cụ gợi ý lệnh đang sẵn sàng nếu chủ nhân muốn chỉnh tay.";
  elements.promptAiHint.textContent = ready
    ? (assistant.summary || `Đã nạp ${skillCount} skill để gợi ý prompt.`)
    : "Kho skill viết prompt đang được chuẩn bị. Bạn vẫn có thể thử bấm viết prompt.";

  applyPromptAiDraftToForm();
  renderPromptAiResult();
}

function userAssistantContextSummary() {
  const config = state.config || {};
  const erp = state.erp || defaultERPState();
  const promptItems = Array.isArray(state.promptSourcePreview?.items) ? state.promptSourcePreview.items : [];
  const promptRows = promptItems.length;
  const activeRows = activePromptSourceItems({ limit: 500 }).length;
  const sampleProducts = promptItems
    .map((item) => item.product_key || item.product_name || item.product || item.notes)
    .filter(Boolean)
    .slice(0, 5)
    .join(", ");
  const enabledModules = normalizeAutomationModules(state.automation)
    .filter((module) => module.enabled !== false)
    .map((module) => module.type)
    .join(" -> ");
  const activeJobs = (state.jobs || []).filter((job) => ACTIVE_STATUSES.has(job.status)).length;
  const failedJobs = (state.jobs || []).filter((job) => ["failed", "interrupted"].includes(job.status)).length;
  return [
    `Quy trình chuẩn: ERP Task nguồn -> app chọn ảnh HTTPS -> Tác nhân Google Flow tự viết prompt/tạo ảnh -> duyệt trên dashboard -> GraphQL thêm URL artifact vào comment của đúng Task`,
    `Nguồn sản phẩm: URL ảnh HTTPS công khai trên ERP Task trong trạng thái ${DEFAULT_ERP_SOURCE_SCOPE_LABEL}`,
    `Màn hình đang ở chế độ ${state.mode}`,
    `Module bật: ${enabledModules || "chưa có"}`,
    `Nguồn prompt ${state.automation.sourceType || "flow_ai"} tại ${state.automation.sourceLocation || "Tác nhân Flow tự viết, Sheet tùy chọn"}`,
    `Bộ lọc sản phẩm ${state.automation.promptProductFilter || "chưa lọc"}`,
    `Sản phẩm/prompt mẫu ${sampleProducts || "chưa preview"}`,
    `Flow project ${config.project_id ? "đã lưu" : "chưa lưu"}`,
    `đăng nhập ${state.auth?.authenticated ? "đã có" : "chưa thấy"}`,
    `ERP ${erp.configured ? "đã cấu hình" : "chưa đủ cấu hình"}`,
    "Duyệt artefact: thực hiện trực tiếp trên dashboard trước khi app ghi ERP",
    `Gemini ${integrations.gemini?.configured ? "đã bật" : "chưa bật"}`,
    `prompt preview ${promptRows} dòng, ${activeRows} dòng active sau lọc`,
    `${activeJobs} job đang chạy`,
    `${failedJobs} job lỗi`,
  ].join("; ");
}

function renderUserAssistant() {
  if (!elements.userAssistantEngine || !elements.userAssistantAnswer) {
    return;
  }
  const last = state.userAssistant?.last || null;
  const gemini = state.integrations?.gemini || {};
  const engineLabel = last?.engine_label || (gemini.configured ? "Gemini" : "Nội bộ");
  const modelLabel = last?.model ? ` · ${last.model}` : "";
  elements.userAssistantEngine.textContent = `${engineLabel}${modelLabel}`;
  elements.userAssistantEngine.dataset.state = gemini.configured || last?.engine === "gemini" ? "ready" : "pending";
  if (elements.userAssistantAskButton) {
    elements.userAssistantAskButton.disabled = Boolean(state.userAssistant?.busy);
    elements.userAssistantAskButton.textContent = state.userAssistant?.busy ? "Đang hỏi..." : "Hỏi AI";
  }

  if (!last?.answer) {
    elements.userAssistantAnswer.textContent =
      "Hỏi lỗi ERP, Sheet hoặc Flow tại đây. Trợ lý sẽ nhìn trạng thái app hiện tại và chỉ dẫn bước cần bấm tiếp theo.";
    return;
  }

  const paragraphs = String(last.answer || "")
    .split(/\n{2,}/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => `<p>${escapeHtml(line)}</p>`)
    .join("");
  const actions = Array.isArray(last.suggested_actions) ? last.suggested_actions.filter(Boolean) : [];
  const executableActions = actions.filter((action) => action.action);
  const erpCandidates = Array.isArray(last.erp_candidates) ? last.erp_candidates.filter(Boolean) : [];
  const flowPlan = last.flow_operator_plan && typeof last.flow_operator_plan === "object" ? last.flow_operator_plan : null;
  const selectedAttachmentCount = Array.isArray(state.automation?.erpAttachmentIds)
    ? state.automation.erpAttachmentIds.filter(Boolean).length
    : 0;
  const hasRunAction = executableActions.some((action) => action.action === "run_auto_erp");
  const canRunSelectedERPImage = Boolean(erpCandidates.length && state.automation?.erpTaskId && selectedAttachmentCount);
  const planButtonLabel = state.userAssistant?.executing
    ? "Đang làm..."
    : canRunSelectedERPImage
      ? "Chạy ảnh đã chọn"
      : hasRunAction
        ? "Làm theo kế hoạch"
        : erpCandidates.length
          ? "Bấm thumbnail ảnh trước"
          : "Làm theo kế hoạch";
  const planButton = executableActions.length
    ? `<button type="button" class="secondary-button assistant-plan-button" data-assistant-action-plan ${
        state.userAssistant?.executing ? "disabled" : ""
      }>${planButtonLabel}</button>`
    : "";
  const flowPlanSteps = Array.isArray(flowPlan?.steps) ? flowPlan.steps.filter(Boolean).slice(0, 5) : [];
  const flowPlanHtml = flowPlan
    ? `<div class="assistant-flow-plan">
        <div class="assistant-flow-plan-head">
          <strong>${escapeHtml(flowPlan.title || "Flow AI Operator")}</strong>
          <span>${escapeHtml(flowPlan.summary || "AI đã lập kế hoạch thao tác Flow.")}</span>
        </div>
        ${
          flowPlanSteps.length
            ? `<div class="assistant-flow-steps">${flowPlanSteps
                .map(
                  (step) => `<div class="assistant-flow-step">
                    <strong>${escapeHtml(step.label || "Bước automation")}</strong>
                    <span>${escapeHtml(step.detail || "")}</span>
                    <em>${escapeHtml(step.status || "sẵn sàng")}</em>
                  </div>`,
                )
                .join("")}</div>`
            : ""
        }
        <div class="assistant-flow-prompt">Prompt ảnh cuối sẽ do Tác nhân Flow tự viết bên trong Google Flow.</div>
      </div>`
    : "";
  const candidateHtml = erpCandidates.length
    ? `<div class="assistant-candidate-list">
        <strong>ERP Task tìm được</strong>
        ${erpCandidates
          .map((candidate) => {
            const inReady = Boolean(candidate.in_ready_list);
            const status = inReady ? `Đúng ${DEFAULT_ERP_SOURCE_SCOPE_LABEL}` : "Có thể chọn trực tiếp";
            const value = candidate.short_link || candidate.task_id || candidate.url || "";
            const previews = Array.isArray(candidate.image_previews) ? candidate.image_previews.filter(Boolean).slice(0, 4) : [];
            const firstAttachmentId = previews.map((preview) => String(preview?.id || "").trim()).find(Boolean) || "";
            const previewHtml = previews.length
              ? `<div class="assistant-candidate-thumbs" aria-label="Ảnh trong ERP Task">
                  ${previews
                    .map((preview, index) => {
                      const src = String(preview.preview_url || preview.url || "").trim();
                      if (!src) return "";
                      const label = preview.name || `Ảnh ${index + 1}`;
                      return `<button type="button" class="assistant-candidate-thumb" data-assistant-card-value="${escapeHtml(
                        value,
                      )}" data-assistant-list-id="${escapeHtml(candidate.status || "")}" data-assistant-attachment-id="${escapeHtml(
                        preview.id || "",
                      )}" ${preview.id ? "data-assistant-run-after-select=\"true\"" : ""} ${
                        state.userAssistant?.executing || !value ? "disabled" : ""
                      } title="${escapeHtml(
                        `Chọn và chạy ảnh này trong ${candidate.name || "ERP Task"}`,
                      )}">
                        <img src="${escapeHtml(src)}" alt="${escapeHtml(label)}" loading="lazy">
                      </button>`;
                    })
                    .join("")}
                </div>`
              : "";
            const pinButton =
              value
                ? `<button type="button" class="ghost-button card-button assistant-candidate-pin" data-assistant-card-value="${escapeHtml(
                    value,
                  )}" data-assistant-list-id="${escapeHtml(candidate.status || "")}" data-assistant-attachment-id="${escapeHtml(
                    firstAttachmentId,
                  )}" ${firstAttachmentId ? "data-assistant-run-after-select=\"true\"" : ""} ${
                    state.userAssistant?.executing ? "disabled" : ""
                  }>${firstAttachmentId ? "Chọn & chạy" : "Chọn card"}</button>`
                : "";
            return `
              <div class="assistant-candidate-item" data-ready="${inReady ? "true" : "false"}">
                <div class="assistant-candidate-main">
                  <strong>${escapeHtml(candidate.name || candidate.short_link || "ERP Task")}</strong>
                  <span>${escapeHtml(candidate.list_name || "Không rõ list")} · ${Number(candidate.image_count || 0)} ảnh · ${status}</span>
                  ${previewHtml ? `<span>Bấm đúng thumbnail để dùng chính ảnh đó làm ảnh gốc.</span>` : ""}
                  ${previewHtml}
                  ${
                    candidate.url
                      ? `<a href="${escapeHtml(candidate.url)}" target="_blank" rel="noreferrer">Mở card</a>`
                      : ""
                  }
                </div>
                ${pinButton}
              </div>
            `;
          })
          .join("")}
      </div>`
    : "";
  const actionHtml = actions.length
    ? `<div class="assistant-action-list">${actions
        .map((action, index) => {
          const canExecute = Boolean(action.action);
          const buttonLabel = action.action === "set_erp_task" && action.payload?.run_after_select ? "Chọn & chạy" : "Thực hiện";
          const button = canExecute
            ? `<button type="button" class="ghost-button card-button assistant-action-button" data-assistant-action-index="${index}" ${
                state.userAssistant?.executing ? "disabled" : ""
              }>${buttonLabel}</button>`
            : "";
          return `
            <div class="assistant-action-item">
              <div>
                <strong>${escapeHtml(action.label || "Việc cần làm")}</strong>
                <span>${escapeHtml(action.detail || "")}</span>
              </div>
              ${button}
            </div>
          `;
        })
        .join("")}</div>`
    : "";
  elements.userAssistantAnswer.innerHTML = `${paragraphs}${flowPlanHtml}${candidateHtml}${planButton}${actionHtml}`;
}

function renderStoryboardResult() {
  const plan = state.storyboardPlan;
  const items = Array.isArray(plan?.items) ? plan.items : [];
  if (!items.length) {
    elements.storyboardResult.hidden = true;
    elements.storyboardResultTitle.textContent = "Storyboard ảnh";
    elements.storyboardResultMeta.textContent = "0 cảnh";
    elements.storyboardResultSummary.textContent = "";
    elements.storyboardSkillChips.hidden = true;
    elements.storyboardSkillChips.innerHTML = "";
    elements.storyboardSceneList.innerHTML = "";
    return;
  }

  elements.storyboardResult.hidden = false;
  elements.storyboardResultTitle.textContent = plan.title || "Storyboard ảnh";
  elements.storyboardResultMeta.textContent = `${items.length} cảnh`;
  elements.storyboardResultSummary.textContent =
    plan.summary || `Đã tách ${items.length} cảnh storyboard từ kịch bản.`;

  const skills = Array.isArray(plan.applied_skills) ? plan.applied_skills.filter(Boolean) : [];
  if (skills.length) {
    elements.storyboardSkillChips.hidden = false;
    elements.storyboardSkillChips.innerHTML = skills
      .slice(0, 6)
      .map((skill) => `<span class="skill-chip">${escapeHtml(skill)}</span>`)
      .join("");
  } else {
    elements.storyboardSkillChips.hidden = true;
    elements.storyboardSkillChips.innerHTML = "";
  }

  elements.storyboardSceneList.innerHTML = items
    .map((item) => {
      const title = String(item.title || `Cảnh ${item.index || 1}`).trim();
      const beat = String(item.beat || "").trim();
      const continuity = String(item.continuity || "").trim();
      const prompt = String(item.image_prompt || "").trim();
      return `
        <article class="storyboard-scene-card">
          <div class="storyboard-scene-head">
            <strong>${escapeHtml(title)}</strong>
            <span class="mini-pill">Cảnh ${escapeHtml(String(item.index || 1))}</span>
          </div>
          ${beat ? `<p class="storyboard-scene-beat">${escapeHtml(beat)}</p>` : ""}
          ${continuity ? `<p class="storyboard-scene-note">${escapeHtml(continuity)}</p>` : ""}
          <div class="prompt-ai-text storyboard-scene-prompt">${escapeHtml(prompt)}</div>
        </article>
      `;
    })
    .join("");
}

function renderStoryboardCard() {
  const visible = state.mode === "video";
  elements.storyboardCard.hidden = !visible;
  if (!visible) {
    return;
  }

  applyStoryboardDraftToForm();
  const busy = Boolean(state.storyboardBusy);
  const ready = isReady();
  elements.storyboardBadge.textContent = ready ? "Storyboard ảnh" : "Lên cảnh trước";
  elements.storyboardBadge.dataset.state = ready ? "ready" : "pending";
  elements.storyboardHint.textContent = ready
    ? "Dán kịch bản, app sẽ tách cảnh rồi có thể tạo luôn các ảnh keyframe bằng luồng tạo ảnh hiện tại."
    : "Có thể tách cảnh trước. Muốn tạo luôn ảnh storyboard thì cần lưu project và đăng nhập Google Flow.";
  elements.storyboardPlanButton.disabled = busy;
  elements.storyboardGenerateButton.disabled = busy;
  renderStoryboardResult();
}

function jobsForCurrentMode() {
  return (state.jobs || [])
    .filter((job) => (state.mode === "edit" ? EDIT_JOB_TYPES.has(job.type) : job.type === state.mode))
    .filter((job) => ACTIVE_STATUSES.has(job.status))
    .sort((left, right) => new Date(right.created_at || 0).getTime() - new Date(left.created_at || 0).getTime());
}

function fillComposerFromSource(mode, payload = {}) {
  const resolvedMode = MODE_CONFIG[mode] ? mode : modeForJobType(payload.type || mode);
  if (!MODE_CONFIG[resolvedMode]) {
    return;
  }
  syncDraftFromForm();
  syncPromptAiDraftFromForm();
  syncEditInputsFromForm();
  state.mode = resolvedMode;
  state.drafts[resolvedMode] = {
    prompt: String(payload.prompt || "").trim(),
    model: String(payload.model || defaultModelForMode(resolvedMode)).trim() || defaultModelForMode(resolvedMode),
    aspect: String(payload.aspect || MODE_CONFIG[resolvedMode].defaultAspect).trim() || MODE_CONFIG[resolvedMode].defaultAspect,
    count: Math.max(1, Math.min(4, Number(payload.count || MODE_CONFIG[resolvedMode].defaultCount))),
  };
  state.promptAiDrafts[resolvedMode] = {
    ...state.promptAiDrafts[resolvedMode],
    brief: String(payload.prompt || "").trim(),
  };

  if (resolvedMode === "video") {
    state.startImagePath = String(payload.start_image_path || "").trim();
    state.startImageName = basename(state.startImagePath);
    state.startImagePublicUrl = uploadPublicUrlFromPath(state.startImagePath);
    state.imageReferenceItems = ensurePrimaryReferenceRole(
      (payload.reference_image_paths || [])
      .map((path) => String(path || "").trim())
      .filter(Boolean)
      .map((path, index) => ({
        path,
        name: basename(path),
        publicUrl: uploadPublicUrlFromPath(path),
        role: normalizeReferenceRoleForMode(payload.reference_image_roles?.[index] || (index === 0 ? "product" : "reference"), "video", index),
      })),
      "video"
    );
    state.drafts.video.inputMode = state.startImagePath ? "start" : state.imageReferenceItems.length ? "reference" : "prompt";
  } else if (resolvedMode === "image") {
    state.startImagePath = "";
    state.startImageName = "";
    state.startImagePublicUrl = "";
    state.imageReferenceItems = ensurePrimaryReferenceRole(
      (payload.reference_image_paths || [])
      .map((path) => String(path || "").trim())
      .filter(Boolean)
      .map((path, index) => ({
        path,
        name: basename(path),
        publicUrl: uploadPublicUrlFromPath(path),
        role: normalizeReferenceRoleForMode(payload.reference_image_roles?.[index] || (index === 0 ? "base" : "reference"), "image", index),
      })),
      "image"
    );
  } else {
    state.startImagePath = "";
    state.startImageName = "";
    state.startImagePublicUrl = "";
    state.imageReferenceItems = [];
    state.editAction = EDIT_JOB_TYPES.has(payload.type) ? payload.type : state.editAction;
    state.manualMediaId = String(payload.media_id || "").trim();
    state.manualWorkflowId = String(payload.workflow_id || "").trim();
    state.motion = String(payload.motion || state.motion || "truck_left").trim() || "truck_left";
    state.position = String(payload.position || state.position || "center").trim() || "center";
    state.resolution = String(payload.resolution || state.resolution || "1080p").trim() || "1080p";
    const matchedKey = availableVideoSources().find(
      (item) => item.mediaId === state.manualMediaId && item.workflowId === state.manualWorkflowId
    )?.key;
    state.selectedEditSourceKey = matchedKey || "";
  }

  renderAll();
  window.scrollTo({ top: 0, behavior: "smooth" });
  elements.promptInput.focus();
}

function describeJob(job) {
  if (job.status === "failed" || job.status === "interrupted") {
    return job.error || job.progress_snapshot?.detail || "Tác vụ chưa hoàn tất.";
  }
  if (job.type === "video" && job.status === "completed" && !(job.artifacts || []).length) {
    return "Flow báo đã xong nhưng app chưa thấy clip video để hiển thị.";
  }
  return (
    job.progress_snapshot?.detail ||
    job.progress_hint?.detail ||
    (job.logs || []).slice(-1)[0]?.message ||
    "Đã gửi yêu cầu."
  );
}

function jobProgressLabel(job) {
  if (job.type === "video" && job.status === "completed" && !(job.artifacts || []).length) {
    return "Chưa thấy clip";
  }
  return job.progress_snapshot?.stage_label || statusLabel(job.status);
}

function jobProgressTone(job) {
  if (job.type === "video" && job.status === "completed" && !(job.artifacts || []).length) {
    return "watch";
  }
  if (job.status === "completed") {
    return "done";
  }
  if (job.status === "failed" || job.status === "interrupted") {
    return "error";
  }
  return "active";
}

function jobDuration(job) {
  const start = new Date(job.created_at || "").getTime();
  const end = new Date((job.status === "completed" || job.status === "failed" || job.status === "interrupted") ? (job.updated_at || job.created_at || "") : Date.now()).getTime();
  if (Number.isNaN(start) || Number.isNaN(end)) {
    return "";
  }
  return formatDuration(Math.max(0, end - start));
}

function parseDateValue(value) {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date;
}

function formatStepMoment(value) {
  const date = parseDateValue(value);
  if (!date) {
    return "";
  }
  return new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function formatStepDuration(startValue, endValue) {
  const start = parseDateValue(startValue);
  const end = parseDateValue(endValue);
  if (!start || !end) {
    return "";
  }
  return formatDuration(Math.max(0, end.getTime() - start.getTime()));
}

function isReferenceToVideoJob(job) {
  return job?.type === "video" && !String(job?.input?.start_image_path || "").trim() && Array.isArray(job?.input?.reference_image_paths) && job.input.reference_image_paths.length > 0;
}

function jobJourneySteps(job) {
  if (isReferenceToVideoJob(job)) {
    return [
      { key: "prepare_frame", label: "Dựng khung đầu" },
      { key: "send_video", label: "Gửi video" },
      { key: "wait_video", label: "Chờ clip" },
      { key: "save", label: "Lưu" },
      { key: "done", label: "Xong" },
    ];
  }
  return [
    { key: "connect", label: "Kết nối" },
    { key: "send", label: "Gửi" },
    { key: "wait", label: "Chờ" },
    { key: "save", label: "Lưu" },
    { key: "done", label: "Xong" },
  ];
}

function jobJourneyCurrentKey(job) {
  const stage = String(job?.progress_snapshot?.stage || "").trim();
  const blockedStage = String(job?.progress_hint?.stage || "").trim() || stage;
  const isAutoReference = isReferenceToVideoJob(job);
  const hasAutoStartFrame = Boolean(String(job?.result?.auto_start_frame_path || "").trim() || String(job?.result?.auto_start_frame_public_url || "").trim());
  const effectiveStage = job?.status === "failed" || job?.status === "interrupted" ? blockedStage : stage;

  if (job?.status === "completed") {
    return "done";
  }

  if (effectiveStage === "saving_artifacts") {
    return "save";
  }
  if (effectiveStage === "awaiting_response" || effectiveStage === "polling") {
    return isAutoReference ? "wait_video" : "wait";
  }
  if (effectiveStage === "sending_request") {
    if (isAutoReference) {
      return hasAutoStartFrame ? "send_video" : "prepare_frame";
    }
    return "send";
  }
  if (effectiveStage === "connecting" || effectiveStage === "queued") {
    return isAutoReference ? "prepare_frame" : "connect";
  }
  return isAutoReference ? "prepare_frame" : "connect";
}

function renderJobJourney(job) {
  const steps = jobJourneySteps(job);
  const currentKey = jobJourneyCurrentKey(job);
  const currentIndex = Math.max(0, steps.findIndex((step) => step.key === currentKey));
  const isBlocked = job.status === "failed" || job.status === "interrupted";
  const allDone = job.status === "completed";

  return `
    <div class="job-journey" aria-label="Tiến trình chi tiết">
      ${steps
        .map((step, index) => {
          let tone = "pending";
          if (allDone) {
            tone = "done";
          } else if (isBlocked) {
            if (index < currentIndex) {
              tone = "done";
            } else if (index === currentIndex) {
              tone = "blocked";
            }
          } else if (index < currentIndex) {
            tone = "done";
          } else if (index === currentIndex) {
            tone = "current";
          }

          return `<span class="job-journey-step" data-tone="${escapeHtml(tone)}">${escapeHtml(step.label)}</span>`;
        })
        .join("")}
    </div>
  `;
}

function renderJobStepNotes(job) {
  const notes = [];
  const currentKey = jobJourneyCurrentKey(job);
  const currentStep = jobJourneySteps(job).find((step) => step.key === currentKey);
  const detail = describeJob(job);
  const lastSignalAt = String(job?.progress_snapshot?.last_signal_at || job?.updated_at || "").trim();
  const autoStartFrameAt = String(job?.result?.auto_start_frame_at || "").trim();
  const autoStartFramePath = String(job?.result?.auto_start_frame_path || "").trim();

  if (isReferenceToVideoJob(job) && autoStartFrameAt) {
    const frameDuration = formatStepDuration(job.created_at, autoStartFrameAt);
    notes.push({
      title: "Dựng khung đầu",
      meta: frameDuration ? `Xong sau ${frameDuration}` : formatStepMoment(autoStartFrameAt),
      detail: autoStartFramePath
        ? `Đã dựng xong ${basename(autoStartFramePath)} để dùng làm keyframe đầu tiên.`
        : "App đã dựng xong ảnh khung đầu để dùng cho bước tạo video.",
      tone: "done",
    });
  }

  if (currentStep) {
    const activePrefix =
      job.status === "completed"
        ? "Hoàn tất"
        : job.status === "failed" || job.status === "interrupted"
        ? "Dừng ở bước này"
        : "Đang xử lý";
    const activeDuration = job.status === "completed"
      ? formatStepDuration(job.created_at, job.updated_at)
      : formatStepDuration(lastSignalAt || job.created_at, new Date().toISOString());
    notes.push({
      title: currentStep.label,
      meta: activeDuration ? `${activePrefix} · ${activeDuration}` : `${activePrefix}${formatStepMoment(lastSignalAt) ? ` · ${formatStepMoment(lastSignalAt)}` : ""}`,
      detail,
      tone: job.status === "failed" || job.status === "interrupted" ? "blocked" : job.status === "completed" ? "done" : "current",
    });
  }

  const deduped = [];
  const seen = new Set();
  for (const note of notes) {
    const key = `${note.title}::${note.detail}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    deduped.push(note);
  }

  if (!deduped.length) {
    return "";
  }

  return `
    <div class="job-step-notes">
      ${deduped
        .map(
          (note) => `
            <article class="job-step-note" data-tone="${escapeHtml(note.tone)}">
              <div class="job-step-note-head">
                <strong>${escapeHtml(note.title)}</strong>
                ${note.meta ? `<span>${escapeHtml(note.meta)}</span>` : ""}
              </div>
              <p>${escapeHtml(note.detail)}</p>
            </article>
          `
        )
        .join("")}
    </div>
  `;
}

function dashboardApprovalStatus(job, artifactIndex) {
  const approvals = job?.result?.dashboard_approvals;
  const item = approvals && typeof approvals === "object" ? approvals[String(artifactIndex)] : null;
  const status = String(item?.status || "").toLowerCase();
  return ["approved", "rejected"].includes(status) ? status : "pending";
}

function jobAwaitsDashboardReview(job) {
  if (job?.type !== "image" || !Array.isArray(job?.artifacts) || !job.artifacts.length) {
    return false;
  }
  const nodes = Array.isArray(job?.result?.automation_execution?.nodes)
    ? job.result.automation_execution.nodes
    : [];
  return nodes.some((node) => node?.type === "approval" && node?.status === "running");
}

function dashboardArtifactPreview(artifact) {
  return String(artifact?.public_url || artifact?.url || "").trim();
}

function renderDashboardReviewQueue() {
  if (!elements.dashboardReviewQueue) {
    return;
  }
  const jobs = (state.jobs || [])
    .filter(jobAwaitsDashboardReview)
    .sort((left, right) => new Date(right.updated_at || right.created_at || 0).getTime() - new Date(left.updated_at || left.created_at || 0).getTime());
  if (!jobs.length) {
    elements.dashboardReviewQueue.hidden = true;
    elements.dashboardReviewQueue.innerHTML = "";
    return;
  }

  elements.dashboardReviewQueue.hidden = false;
  elements.dashboardReviewQueue.innerHTML = `
    <div class="dashboard-review-head">
      <div>
        <p class="eyebrow">Dashboard review</p>
        <h3>Ảnh đang chờ duyệt</h3>
        <p>Chỉ ảnh được duyệt ở đây mới được ghi URL vào comment của Task ERP nguồn.</p>
      </div>
      <span class="status-pill" data-state="pending">${jobs.length} lượt chờ</span>
    </div>
    <div class="dashboard-review-job-list">
      ${jobs
        .map((job) => {
          const sourceTask = String(job.input?.erp_source_task_id || job.input?.erp_task_id || "").trim();
          const sourceAttachments = Array.isArray(job.input?.erp_source_attachment_ids)
            ? job.input.erp_source_attachment_ids.filter(Boolean)
            : Array.isArray(job.input?.erp_attachment_ids)
              ? job.input.erp_attachment_ids.filter(Boolean)
              : [];
          const ideaSource = sourceTask
            ? `Bộ idea của Task ${sourceTask}${sourceAttachments.length ? ` · ${sourceAttachments.length} ảnh nguồn` : ""}`
            : "Bộ idea của lượt chạy này";
          const decisions = job.artifacts.map((artifact, artifactIndex) => {
            const status = dashboardApprovalStatus(job, artifactIndex);
            const preview = dashboardArtifactPreview(artifact);
            const title = artifact.media_name || artifact.label || `Ảnh ${artifactIndex + 1}`;
            const statusLabel = status === "approved" ? "Đã duyệt" : status === "rejected" ? "Đã từ chối" : "Chờ duyệt";
            return `
              <article class="dashboard-review-artifact" data-status="${escapeHtml(status)}">
                ${preview ? `<img src="${escapeHtml(preview)}" alt="${escapeHtml(title)}" />` : `<div class="dashboard-review-placeholder">Chưa có preview</div>`}
                <div class="dashboard-review-artifact-copy">
                  <strong>${escapeHtml(title)}</strong>
                  <span class="status-pill" data-state="${escapeHtml(status === "approved" ? "ready" : status === "rejected" ? "error" : "pending")}">${escapeHtml(statusLabel)}</span>
                </div>
                ${
                  status === "pending"
                    ? `<div class="card-actions">
                        <button type="button" class="secondary-button dashboard-review-approve" data-dashboard-approval="approved" data-job-id="${escapeHtml(job.id)}" data-artifact-index="${artifactIndex}">Duyệt</button>
                        <button type="button" class="ghost-button card-button" data-dashboard-approval="rejected" data-job-id="${escapeHtml(job.id)}" data-artifact-index="${artifactIndex}">Từ chối</button>
                      </div>`
                    : ""
                }
              </article>
            `;
          }).join("");
          return `
            <section class="dashboard-review-job">
              <div class="dashboard-review-job-head">
                <strong>${escapeHtml(job.title || "Flow image")}</strong>
                <small>${escapeHtml(formatTime(job.created_at))}</small>
              </div>
              <p class="dashboard-review-idea-source">${escapeHtml(ideaSource)}</p>
              <p>${escapeHtml(truncate(job.input?.prompt || "", 180) || "Không có prompt")}</p>
              <div class="dashboard-review-artifact-grid">${decisions}</div>
              <div class="dashboard-review-add" data-dashboard-review-job="${escapeHtml(job.id)}">
                <div>
                  <strong>Thêm ảnh vào bộ idea</strong>
                  <small>Chỉ nhận URL ảnh HTTPS. Ảnh thêm vào cũng phải được duyệt trước khi ghi vào đúng Task nguồn.</small>
                </div>
                <input type="url" inputmode="url" autocomplete="url" placeholder="https://…/anh-da-chinh-sua.jpg" aria-label="URL ảnh bổ sung" data-dashboard-artifact-url />
                <input type="text" maxlength="180" placeholder="Tên ảnh (tùy chọn)" aria-label="Tên ảnh bổ sung" data-dashboard-artifact-label />
                <button type="button" class="secondary-button" data-dashboard-artifact-add data-job-id="${escapeHtml(job.id)}">Thêm ảnh</button>
              </div>
            </section>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderLatestStatus() {
  const latestJob = jobsForCurrentMode()[0];
  if (!latestJob) {
    elements.latestStatusCard.className = "latest-status empty-state";
    elements.latestStatusCard.textContent = "Chưa có lượt chạy nào. Sau khi bấm chạy, tab Google Flow sẽ được giữ mở.";
    return;
  }

  const prompt = truncate(latestJob.input?.prompt || "", 180) || "Không có mô tả.";
  const note = describeJob(latestJob);
  const duration = jobDuration(latestJob);
  const sourceImagePath = String(latestJob.input?.start_image_path || "").trim();
  const referenceImageCount = Array.isArray(latestJob.input?.reference_image_paths)
    ? latestJob.input.reference_image_paths.length
    : 0;
  const autoStartFramePath = String(latestJob.result?.auto_start_frame_path || "").trim();
  const autoStartFramePreview = String(latestJob.result?.auto_start_frame_public_url || "").trim()
    || uploadPublicUrlFromPath(autoStartFramePath);
  const autoStartFramePrompt = truncate(latestJob.result?.auto_start_frame_prompt || "", 150);
  const sourceLabel = sourceImagePath
    ? `Ảnh gốc: ${basename(sourceImagePath)}`
    : latestJob.type === "video" && referenceImageCount
    ? `Ảnh tham chiếu: ${referenceImageCount}`
    : referenceImageCount
    ? `Ảnh tham chiếu: ${referenceImageCount}`
    : "";
  const canRetry =
    latestJob.status === "failed" ||
    latestJob.status === "interrupted" ||
    (latestJob.type === "video" && latestJob.status === "completed" && !(latestJob.artifacts || []).length);
  const canReuse = Boolean(String(latestJob.input?.prompt || "").trim());
  const canOpenFlow = Boolean(state.config?.project_id);

  elements.latestStatusCard.className = "latest-status";
  elements.latestStatusCard.innerHTML = `
    <article class="status-summary-card">
      <div class="run-head">
        <div>
          <strong>${escapeHtml(latestJob.title || currentOperationConfig().submitLabel)}</strong>
          <small>${escapeHtml(formatTime(latestJob.created_at))}${duration ? ` · ${escapeHtml(duration)}` : ""}</small>
        </div>
        <span class="status-chip" data-status="${escapeHtml(jobProgressTone(latestJob))}">${escapeHtml(jobProgressLabel(latestJob))}</span>
      </div>
      ${renderJobJourney(latestJob)}
      ${renderJobStepNotes(latestJob)}
      ${
        latestJob.type === "video" && autoStartFramePreview
          ? `
            <div class="status-start-frame">
              <img class="status-start-frame-image" src="${escapeHtml(autoStartFramePreview)}" alt="Ảnh khung đầu tự dựng" />
              <div class="status-start-frame-copy">
                <span class="mini-pill">Khung đầu đã dựng</span>
                <strong>${escapeHtml(basename(autoStartFramePath) || "Ảnh khung đầu tự dựng")}</strong>
                <p>${escapeHtml(autoStartFramePrompt || "App sẽ dùng chính ảnh này làm keyframe đầu tiên trước khi render video.")}</p>
              </div>
            </div>
          `
          : ""
      }
      ${sourceLabel ? `<p class="run-source">${escapeHtml(sourceLabel)}</p>` : ""}
      <p class="run-prompt">${escapeHtml(prompt)}</p>
      <p class="run-note">${escapeHtml(note)}</p>
      <p class="run-note flow-open-note">Tab Google Flow vẫn được giữ mở để bạn xem trực tiếp trên đó.</p>
      <div class="card-actions">
        ${
          canOpenFlow
            ? `<button type="button" class="ghost-button card-button" data-action="open-flow-project">Mở Flow</button>`
            : ""
        }
        ${
          canReuse
            ? `<button type="button" class="ghost-button card-button" data-action="reuse-job" data-job-id="${escapeHtml(latestJob.id)}">Dùng lại prompt</button>`
            : ""
        }
        ${
          canRetry
            ? `<button type="button" class="ghost-button card-button" data-action="retry-job" data-job-id="${escapeHtml(latestJob.id)}">Chạy lại</button>`
            : ""
        }
      </div>
    </article>
  `;
}

function renderAll() {
  renderTopbar();
  renderAutomationDashboard();
  renderUserAssistant();
  renderComposer();
  renderLatestStatus();
  renderDashboardReviewQueue();
}

async function loadState({ silent = false } = {}) {
  if (stateLoadPromise) {
    return stateLoadPromise;
  }

  const request = (async () => {
    try {
      const payload = await api("/api/state");
      state.config = payload.config || {};
      state.auth = payload.auth || { authenticated: false };
      state.jobs = (payload.jobs || []).filter((job) => job.type !== "login");
      state.outputShelf = payload.output_shelf || { items: [] };
      state.promptAssistant = payload.prompt_assistant || null;
      state.integrations = normalizeIntegrationState(payload.integrations || {});
      state.erp = normalizeERPState(payload.erp || {});
      state.skillLibraryCount = Array.isArray(payload.skills) ? payload.skills.length : 0;

      if (state.setupOpen == null) {
        state.setupOpen = !isReady();
      }

      renderAll();
      maybeAutoPreviewPromptSource();
      maybeShowERPWizard();
      if (isReady() && !state.modelOptionsLoaded) {
        void loadModelOptions();
      }
      if (!silent) {
        showMessage("");
      }
    } catch (error) {
      showMessage(error.message, "error");
    }
  })();

  stateLoadPromise = request;
  try {
    return await request;
  } finally {
    if (stateLoadPromise === request) {
      stateLoadPromise = null;
    }
  }
}

function maybeAutoPreviewPromptSource() {
  if (promptSourceAutoPreviewStarted || state.promptSourcePreview?.prompt_count) {
    return;
  }
  if (state.automation.sourceType !== "sheets" || !String(state.automation.sourceLocation || "").trim()) {
    return;
  }
  promptSourceAutoPreviewStarted = true;
  void previewPromptSource(null, { silent: true });
}

async function saveConfig(event) {
  event.preventDefault();
  const projectId = normalizeProjectInput(elements.projectId.value);
  if (!projectId) {
    showMessage("Hãy dán link project hoặc mã project.", "error");
    elements.projectId.focus();
    return;
  }

  syncDraftFromForm();
  try {
    await api("/api/config", {
      method: "PUT",
      body: JSON.stringify({
        project_id: projectId,
        project_name: elements.projectName.value.trim(),
        active_workflow_id: state.config?.active_workflow_id || "",
        headless: Boolean(state.config?.headless),
        cdp_url: state.config?.cdp_url || "",
        generation_timeout_s: Math.max(30, Number(elements.generationTimeout.value || 300)),
        poll_interval_s: state.config?.poll_interval_s || 5,
        output_dir: state.config?.output_dir || "",
      }),
    });
    showMessage("Đã lưu project.", "success");
    await loadState({ silent: true });
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function loginFlow() {
  try {
    await api("/api/auth/login", { method: "POST" });
    showMessage("Đang mở cửa sổ đăng nhập Google Flow. Nếu chưa thấy Chromium hiện ra, bấm thêm nút Mở Flow.", "success");
    state.setupOpen = true;
    renderTopbar();
  } catch (error) {
    showMessage(formatFlowWindowError(error.message), "error");
  }
}

async function openFlowLoginSurface() {
  try {
    const payload = await api("/api/flow/open-login", { method: "POST" });
    showMessage(`Đã gọi lại cửa sổ đăng nhập Flow. Nếu vẫn chưa thấy, hãy kiểm tra Chromium/Chrome for Testing trên màn hình.`, "success");
    state.setupOpen = true;
    renderTopbar();
    return payload;
  } catch (error) {
    showMessage(formatFlowWindowError(error.message), "error");
    return null;
  }
}

async function openFlowProjectSurface() {
  try {
    const payload = await api("/api/flow/open-project", { method: "POST" });
    const hasProject = Boolean(state.config?.project_id);
    showMessage(
      hasProject
        ? "Đã gọi lại tab project Flow đang dùng."
        : "Đã mở lại Flow. Hãy lưu project hoặc đăng nhập nếu cần.",
      "success"
    );
    return payload;
  } catch (error) {
    showMessage(formatFlowWindowError(error.message), "error");
    return null;
  }
}

function formatFlowWindowError(message) {
  const text = String(message || "").trim();
  if (/session 0|session nền của windows/i.test(text)) {
    return `${text} Nếu đang dùng Windows, hãy chạy Flow v2 ngay trên màn hình desktop rồi đăng nhập lại trong cửa sổ đó.`;
  }
  return text;
}

async function logoutFlow() {
  if (!state.auth?.authenticated) {
    showMessage("Phiên Google Flow hiện đã ở trạng thái đăng xuất.", "success");
    return;
  }

  elements.logoutButton.disabled = true;
  try {
    const payload = await api("/api/auth/logout", { method: "POST" });
    state.setupOpen = true;
    await loadState({ silent: true });
    showMessage(
      payload.had_session
        ? "Đã đăng xuất Google Flow. Khi cần chạy tiếp, chỉ việc đăng nhập lại."
        : "Phiên Google Flow đã ở trạng thái đăng xuất.",
      "success"
    );
  } catch (error) {
    showMessage(error.message, "error");
  } finally {
    renderTopbar();
  }
}

async function uploadStartImage(event) {
  const file = event.target.files?.[0];
  if (!file) {
    clearStartImageState({ resetInput: false });
    renderUploadStatus();
    return;
  }

  const data = new FormData();
  data.append("file", file);
  state.uploading = true;
  renderUploadStatus();
  try {
    const payload = await api("/api/uploads", { method: "POST", body: data });
    if (state.mode === "video") {
      setVideoInputMode("start", { clearConflicts: true });
      renderComposer();
    }
    state.startImagePath = payload.saved_path || "";
    state.startImageName = payload.file_name || file.name;
    state.startImagePublicUrl = payload.public_url || uploadPublicUrlFromPath(payload.saved_path || file.name);
    showMessage("Đã tải ảnh đầu vào.", "success");
  } catch (error) {
    clearStartImageState({ resetInput: false });
    event.target.value = "";
    showMessage(error.message, "error");
  } finally {
    state.uploading = false;
    renderComposerSummary();
    renderUploadStatus();
  }
}

async function uploadImageReferences(event) {
  const files = Array.from(event.target.files || []);
  if (!files.length) {
    return;
  }

  if (state.imageReferenceItems.length + files.length > 4) {
    event.target.value = "";
    showMessage(
      state.mode === "video"
        ? "Tối đa 4 ảnh sản phẩm/tham chiếu cho một lượt dựng ảnh rồi tạo video."
        : "Tối đa 4 ảnh tham chiếu cho một lượt ghép/chỉnh ảnh.",
      "error"
    );
    return;
  }

  state.uploading = true;
  if (state.mode === "video") {
    setVideoInputMode("reference", { clearConflicts: true });
    renderComposer();
  }
  renderImageReferenceStatus();
  try {
    for (const file of files) {
      const data = new FormData();
      data.append("file", file);
      const payload = await api("/api/uploads", { method: "POST", body: data });
      const primaryRole = primaryReferenceRoleForMode(state.mode);
      const hasPrimary = state.imageReferenceItems.some((item) => normalizeReferenceRole(item.role) === primaryRole);
      const defaultRole = hasPrimary ? "reference" : primaryRole;
      state.imageReferenceItems.push({
        path: payload.saved_path || "",
        name: payload.file_name || file.name,
        publicUrl: payload.public_url || uploadPublicUrlFromPath(payload.saved_path || file.name),
        role: defaultRole,
      });
    }
    state.imageReferenceItems = ensurePrimaryReferenceRole(state.imageReferenceItems, state.mode);
    showMessage(
      state.mode === "video"
        ? "Đã tải ảnh tham chiếu. App có thể tự dựng khung đầu rồi tạo video luôn."
        : "Đã tải ảnh tham chiếu để ghép/chỉnh ảnh.",
      "success"
    );
  } catch (error) {
    showMessage(error.message, "error");
  } finally {
    state.uploading = false;
    event.target.value = "";
    renderComposerSummary();
    renderImageReferenceStatus();
  }
}

function clearStartImage() {
  clearStartImageState();
  if (state.mode === "video" && currentVideoInputMode() === "start") {
    state.drafts.video.inputMode = "prompt";
  }
  renderComposerSummary();
  renderUploadStatus();
  renderComposer();
  showMessage("Đã bỏ ảnh đầu vào.", "success");
}

function removeReferenceImage(indexValue) {
  const index = Number(indexValue);
  if (!Number.isInteger(index) || index < 0 || index >= state.imageReferenceItems.length) {
    return;
  }
  state.imageReferenceItems.splice(index, 1);
  if (state.imageReferenceItems.length) {
    state.imageReferenceItems = ensurePrimaryReferenceRole(state.imageReferenceItems, state.mode);
  } else if (state.mode === "video" && currentVideoInputMode() === "reference") {
    state.drafts.video.inputMode = "prompt";
  }
  renderComposerSummary();
  renderImageReferenceStatus();
  renderComposer();
  showMessage("Đã bỏ một ảnh tham chiếu.", "success");
}

function setReferenceImageRole(indexValue, roleValue) {
  const index = Number(indexValue);
  if (!Number.isInteger(index) || index < 0 || index >= state.imageReferenceItems.length) {
    return;
  }
  const role = normalizeReferenceRoleForMode(roleValue, state.mode, index);
  const primaryRole = primaryReferenceRoleForMode(state.mode);
  state.imageReferenceItems = state.imageReferenceItems.map((item, itemIndex) => ({
    ...item,
    role:
      role === primaryRole && itemIndex !== index
        ? normalizeReferenceRole(item.role) === primaryRole
          ? "reference"
          : normalizeReferenceRoleForMode(item.role, state.mode, itemIndex)
        : normalizeReferenceRoleForMode(item.role, state.mode, itemIndex),
  }));
  state.imageReferenceItems[index].role = role;
  state.imageReferenceItems = ensurePrimaryReferenceRole(state.imageReferenceItems, state.mode);
  renderComposerSummary();
  renderImageReferenceStatus();
  showMessage(`Đã đổi vai trò ảnh sang ${referenceRoleLabel(role).toLowerCase()}.`, "success");
}

function promoteReferenceImage(indexValue) {
  const index = Number(indexValue);
  if (!Number.isInteger(index) || index < 0 || index >= state.imageReferenceItems.length) {
    return;
  }
  setReferenceImageRole(index, primaryReferenceRoleForMode(state.mode));
}

function useAutomationPromptInStudio() {
  syncAutomationFromForm();
  renderAutomationDashboard();
  document.querySelector(".scenario-sidebar")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  elements.automationStepNameInput?.focus();
  elements.automationStepNameInput?.select();
  showMessage("Đang chỉnh module ngay trong dashboard. Logic Flow vẫn chạy ngầm khi bấm Run once.", "success");
}

function exportAutomationConfig() {
  syncAutomationFromForm();
  const payload = normalizeAutomationConfig(state.automation);
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "flow-automation-config.json";
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
  showMessage("Đã export cấu hình custom. File JSON này có thể import lại trên Windows hoặc MacBook.", "success");
}

async function importAutomationConfig(event) {
  const file = event.target.files?.[0];
  if (!file) {
    return;
  }
  try {
    const imported = JSON.parse(await file.text());
    state.automation = normalizeAutomationConfig(imported);
    saveAutomationConfig(state.automation);
    renderAll();
    showMessage("Đã import cấu hình custom cho automation.", "success");
  } catch (error) {
    showMessage("File cấu hình không hợp lệ. Hãy chọn file JSON đã export từ Flow v2.", "error");
  } finally {
    event.target.value = "";
  }
}

function resetAutomationConfig() {
  state.automation = defaultAutomationConfig();
  saveAutomationConfig(state.automation);
  renderAll();
  showMessage("Đã reset phần custom về mặc định.", "success");
}

async function prepareReadyForAutoERP() {
  syncAutomationFromForm();
  const boardId = String(state.erp?.project_id || state.automation.erpProjectId || DEFAULT_ERP_PROJECT_URL).trim();
  const listId = String(state.erp?.status || state.automation.erpStatusId || DEFAULT_ERP_SOURCE_LIST_ID).trim();
  try {
    const status = await api("/api/erp/ready/status", {
      method: "POST",
      body: JSON.stringify({
        erp_project_id: boardId,
        erp_status_id: listId,
      }),
    });
    const eligible = Number(status.eligible || 0);
    const complete = Number(status.complete || 0);
    const cardsSeen = Number(status.cards_seen || 0);
    const targetOutputCount = Number(status.target_output_count || FLOW_AGENT_TARGET_OUTPUT_COUNT);
    if (eligible > 0 || !cardsSeen) {
      return true;
    }
    if (complete > 0) {
      showMessage(
        `${complete} Task đã có artefact Flow. App sẽ không xóa dữ liệu ERP; hãy chọn Task khác hoặc chạy lại có chủ đích.`,
        "info",
      );
      return true;
    }
    if (Number(status.without_source || 0) > 0) {
      showMessage(`${DEFAULT_ERP_SOURCE_SCOPE_LABEL} có Task nhưng chưa có URL ảnh nguồn hợp lệ.`, "error");
      return false;
    }
  } catch (error) {
    showMessage(`Chưa kiểm tra được ${DEFAULT_ERP_SOURCE_SCOPE_LABEL} trước khi chạy: ${error.message}. App vẫn sẽ thử Auto.`, "error");
  }
  return true;
}

async function saveERPConfig({ clearCredentials = false } = {}) {
  syncAutomationFromForm();
  const payload = {
    api_key: clearCredentials ? "" : elements.automationERPKeyInput?.value?.trim() || "",
    api_secret: clearCredentials ? "" : elements.automationERPSecretInput?.value?.trim() || "",
    base_url: "https://erp.havigroup.llc",
    project_id:
      normalizeERPProjectId(elements.automationERPProjectStorageInput?.value) ||
      currentERPProjectId(),
    task_id: elements.automationERPTaskInput?.value?.trim() || "",
    status: elements.automationERPStatusInput?.value?.trim() || "",
    clear_credentials: clearCredentials,
  };

  if (elements.automationERPSaveButton) {
    elements.automationERPSaveButton.disabled = true;
  }
  if (elements.automationERPClearButton) {
    elements.automationERPClearButton.disabled = true;
  }

  try {
    const response = await api("/api/integrations/erp", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    state.erp = normalizeERPState(response.erp || {});
    state.automation.erpProjectId = state.erp.project_id || payload.project_id;
    state.automation.erpTaskId = state.erp.task_id || payload.task_id;
    state.automation.erpStatusId = state.erp.status || payload.status;
    saveAutomationConfig(state.automation);

    if (elements.automationERPKeyInput) {
      elements.automationERPKeyInput.value = "";
    }
    if (elements.automationERPSecretInput) {
      elements.automationERPSecretInput.value = "";
    }

    renderAutomationDashboard();
    if (clearCredentials) {
      showMessage("Đã xóa API key/secret ERP cục bộ.", "success");
    } else if (state.erp.configured) {
      showMessage("Đã lưu ERP. Chỉ URL ảnh được duyệt trên dashboard mới được ghi vào comment của Task nguồn.", "success");
    } else if (state.erp.credentials_saved) {
      showMessage("Đã lưu API key/secret ERP. Hãy chọn Task nguồn có ảnh URL và trạng thái nguồn.", "success");
    } else {
      showMessage("Cần API key và API secret ERP để bật tự động.", "success");
    }
  } catch (error) {
    showMessage(error.message, "error");
  } finally {
    if (elements.automationERPSaveButton) {
      elements.automationERPSaveButton.disabled = false;
    }
    if (elements.automationERPClearButton) {
      elements.automationERPClearButton.disabled = false;
    }
  }
}

// ── Idea fan-out ────────────────────────────────────────────────
// One child card of "Phân rã công việc" = one idea. The app reads the idea
// image from the parent card, runs the images for each idea, and — only after
// the dashboard approval — writes them back into that idea's own card.
function setIdeaBatchStatus(text, state = "ready") {
  if (!elements.automationERPIdeaStatus) {
    return;
  }
  elements.automationERPIdeaStatus.textContent = text;
  elements.automationERPIdeaStatus.dataset.state = state;
}

async function runERPIdeaBatch() {
  syncAutomationFromForm();
  const taskId =
    elements.automationERPIdeaTaskInput?.value?.trim() ||
    state.automation.erpTaskId ||
    state.erp?.task_id ||
    "";
  if (!taskId) {
    showMessage("Hãy điền mã thẻ Idea cha, ví dụ TASK-2026-00202.", "error");
    return;
  }
  const count = Number.parseInt(elements.automationERPIdeaCountInput?.value || "", 10);
  const payload = {
    task_id: taskId,
    count: Number.isFinite(count) && count > 0 ? count : 0,
    include_done: Boolean(elements.automationERPIdeaIncludeDoneInput?.checked),
    child_task_ids: [],
  };
  if (elements.automationERPIdeaRunButton) {
    elements.automationERPIdeaRunButton.disabled = true;
  }
  setIdeaBatchStatus("Đang xếp hàng...", "pending");
  try {
    const response = await api("/api/erp/idea-batch", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    const queued = Array.isArray(response.queued) ? response.queued : [];
    const skipped = Array.isArray(response.skipped) ? response.skipped : [];
    setIdeaBatchStatus(`${queued.length} idea đang chạy`, queued.length ? "ready" : "pending");
    const skippedNote = skipped.length ? `; bỏ qua ${skipped.length} thẻ đã có ảnh Flow` : "";
    showMessage(
      queued.length
        ? `Đã xếp hàng ${queued.length} idea (${response.count} ảnh/idea)${skippedNote}. Ảnh sẽ chờ bạn duyệt trên dashboard trước khi gửi vào từng thẻ con.`
        : `Không có idea nào cần chạy${skippedNote}.`,
      queued.length ? "success" : "error",
    );
    await loadState({ silent: true });
  } catch (error) {
    setIdeaBatchStatus("Lỗi", "pending");
    showMessage(error.message, "error");
  } finally {
    if (elements.automationERPIdeaRunButton) {
      elements.automationERPIdeaRunButton.disabled = false;
    }
  }
}

// ── ERP first-run setup wizard ──────────────────────────────────
// Pops a modal the first time chủ nhân opens the app without ERP creds,
// then writes the 3 values straight into `.env.local` so the next launches
// don't need any setup. Dismissed state lives in sessionStorage so a fresh
// browser tab still gets the nudge.
const ERP_WIZARD_DISMISS_KEY = "flow.v2.erpWizard.dismissedThisSession";

function isERPWizardDismissedForSession() {
  try {
    return window.sessionStorage?.getItem(ERP_WIZARD_DISMISS_KEY) === "1";
  } catch (error) {
    return false;
  }
}

function rememberERPWizardDismissal() {
  try {
    window.sessionStorage?.setItem(ERP_WIZARD_DISMISS_KEY, "1");
  } catch (error) {
    // sessionStorage may be blocked; the wizard will simply reappear next
    // load, which is the safer default for a setup nudge.
  }
}

function showERPWizardStatus(message, tone = "info") {
  const node = elements.erpWizardStatus;
  if (!node) {
    return;
  }
  if (!message) {
    node.hidden = true;
    node.textContent = "";
    node.removeAttribute("data-tone");
    return;
  }
  node.hidden = false;
  node.textContent = message;
  node.dataset.tone = tone;
}

function openERPWizard() {
  const wizard = elements.erpSetupWizard;
  if (!wizard) {
    return;
  }
  wizard.hidden = false;
  wizard.setAttribute("aria-hidden", "false");
  showERPWizardStatus("");
  // Focus first empty input so the user can paste immediately.
  const inputs = [
    elements.erpWizardKeyInput,
    elements.erpWizardSecretInput,
    elements.erpWizardBoardInput,
  ];
  const firstEmpty = inputs.find((input) => input && !input.value.trim()) || inputs[0];
  setTimeout(() => firstEmpty?.focus(), 30);
  document.body.style.overflow = "hidden";
}

function closeERPWizard({ remember = true } = {}) {
  const wizard = elements.erpSetupWizard;
  if (!wizard) {
    return;
  }
  wizard.hidden = true;
  wizard.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
  if (remember) {
    rememberERPWizardDismissal();
  }
}

function maybeShowERPWizard() {
  if (!elements.erpSetupWizard) {
    return;
  }
  if (state.erp?.credentials_saved && state.erp?.configured) {
    closeERPWizard({ remember: false });
    return;
  }
  if (state.erp?.credentials_saved && !state.erp?.configured) {
    // Creds OK but Project/Task/trạng thái missing → user can fix inside the
    // inspector, no need to block the dashboard with a modal.
    return;
  }
  if (isERPWizardDismissedForSession()) {
    return;
  }
  openERPWizard();
}

async function submitERPWizard() {
  const key = elements.erpWizardKeyInput?.value?.trim() || "";
  const apiSecret = elements.erpWizardSecretInput?.value?.trim() || "";
  const project = normalizeERPProjectId(elements.erpWizardBoardInput?.value) || currentERPProjectId();

  if (!key || !apiSecret) {
    showERPWizardStatus("Cần điền đủ ERP API key và API secret.", "error");
    return;
  }

  const saveButton = elements.erpWizardSaveButton;
  if (saveButton) {
    saveButton.disabled = true;
  }
  showERPWizardStatus("Đang ghi creds vào .env.local…", "info");

  try {
    const response = await api("/api/integrations/erp", {
      method: "PUT",
      body: JSON.stringify({
        api_key: key,
        api_secret: apiSecret,
        base_url: "https://erp.havigroup.llc",
        project_id: project,
        task_id: state.erp?.task_id || "",
        status: state.erp?.status || "",
        clear_credentials: false,
        persist_to_env: true,
      }),
    });

    const nextERP = normalizeERPState(response.erp || response || {});
    state.erp = nextERP;
    state.automation.erpProjectId = nextERP.project_id || project;
    saveAutomationConfig(state.automation);

    const persisted = response?.persisted_to_env === true;
    const persistError = String(response?.persist_error || "").trim();

    if (persisted) {
      showERPWizardStatus(
        "Đã lưu vào .env.local. Lần sau chỉ việc chạy — không cần nhập lại.",
        "success"
      );
      showMessage(
        "Đã setup ERP vĩnh viễn vào .env.local. Auto ERP đã sẵn sàng.",
        "success"
      );
    } else {
      // Saved to state.json but couldn't touch .env.local (permissions /
      // sandboxed FS). Surface the error so chủ nhân can copy values
      // manually if needed.
      const fallback = persistError
        ? `Đã lưu vào app, nhưng không ghi được vào .env.local: ${persistError}. App vẫn dùng được trong phiên này.`
        : "Đã lưu vào app, nhưng không ghi được vào .env.local. Hãy thêm thủ công để giữ qua các lần khởi động.";
      showERPWizardStatus(fallback, "error");
    }

    renderAutomationDashboard();

    if (persisted) {
      setTimeout(() => closeERPWizard({ remember: false }), 1100);
    }
  } catch (error) {
    showERPWizardStatus(error.message || "Lưu thất bại. Hãy kiểm tra creds.", "error");
  } finally {
    if (saveButton) {
      saveButton.disabled = false;
    }
  }
}

async function saveIntegrationConfig({ clearSecrets = false } = {}) {
  syncAutomationFromForm();
  const payload = {
    gemini_api_key: clearSecrets ? "" : elements.automationGeminiKeyInput?.value?.trim() || "",
    gemini_model: elements.automationGeminiModelInput?.value?.trim() || state.integrations?.gemini?.model || "gemini-2.5-flash",
    telegram_bot_token: "",
    telegram_chat_id: state.integrations?.telegram?.chat_id || "",
    playwright_browsers_path: elements.automationPlaywrightPathInput?.value?.trim() || "",
    clear_gemini_api_key: clearSecrets,
    clear_telegram_bot_token: false,
  };

  if (elements.automationEnvSaveButton) {
    elements.automationEnvSaveButton.disabled = true;
  }
  if (elements.automationEnvClearButton) {
    elements.automationEnvClearButton.disabled = true;
  }

  try {
    const response = await api("/api/integrations/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    state.integrations = normalizeIntegrationState(response.integrations || {});
    saveAutomationConfig(state.automation);

    if (elements.automationGeminiKeyInput) {
      elements.automationGeminiKeyInput.value = "";
    }
    renderAutomationDashboard();
    if (clearSecrets) {
      showMessage("Đã xóa Gemini key trong app. Các field không nhạy cảm vẫn giữ lại.", "success");
    } else {
      showMessage("Đã lưu cấu hình app. Từ giờ không cần sửa file .env cho Gemini hoặc Playwright path.", "success");
    }
  } catch (error) {
    showMessage(error.message, "error");
  } finally {
    if (elements.automationEnvSaveButton) {
      elements.automationEnvSaveButton.disabled = false;
    }
    if (elements.automationEnvClearButton) {
      elements.automationEnvClearButton.disabled = false;
    }
  }
}

async function previewPromptSource(file = null, { silent = false } = {}) {
  syncAutomationFromForm();
  const data = new FormData();
  data.append("source_url", state.automation.sourceLocation || "");
  data.append("text", elements.automationSheetPasteInput?.value || "");
  if (file) {
    data.append("file", file);
  }

  if (elements.automationSheetPreviewButton) {
    elements.automationSheetPreviewButton.disabled = true;
  }
  if (elements.automationSheetFileButton) {
    elements.automationSheetFileButton.disabled = true;
  }

  try {
    const payload = await api("/api/prompt-sources/preview", {
      method: "POST",
      body: data,
    });
    state.promptSourcePreview = payload;
    state.automation.sourceType = "sheets";
    state.automation.prompt = payload.prompt || state.automation.prompt || "";
    saveAutomationConfig(state.automation);
    renderAll();
    const count = Number(payload.active_count || payload.prompt_count || 0);
    if (!silent) {
      showMessage(`Đã lấy ${count} prompt từ sheet/file. Bấm tạo ảnh để app chạy lần lượt các dòng active rồi chờ duyệt trên dashboard.`, "success");
    }
    return payload;
  } catch (error) {
    if (!silent) {
      showMessage(error.message, "error");
    }
    return null;
  } finally {
    if (elements.automationSheetPreviewButton) {
      elements.automationSheetPreviewButton.disabled = false;
    }
    if (elements.automationSheetFileButton) {
      elements.automationSheetFileButton.disabled = false;
    }
    if (elements.automationSheetFileInput) {
      elements.automationSheetFileInput.value = "";
    }
  }
}

function syncModuleSettingFromControl(control) {
  const module = selectedAutomationModule();
  const setting = control.dataset.moduleSetting;
  const value = control.type === "checkbox" ? Boolean(control.checked) : control.value;
  module.settings = module.settings || {};
  module.settings[setting] = value;
  if (setting === "sourceType") {
    state.automation.sourceType = value || FLOW_AI_SOURCE_TYPE;
    if (elements.automationSourceType) {
      elements.automationSourceType.value = state.automation.sourceType;
    }
  } else if (setting === "sourceLocation") {
    state.automation.sourceLocation = String(value || "").trim();
    if (elements.automationSourceLocationInput) {
      elements.automationSourceLocationInput.value = state.automation.sourceLocation;
    }
  } else if (setting === "promptProductFilter") {
    state.automation.promptProductFilter = String(value || "").trim();
    if (elements.automationProductFilterInput) {
      elements.automationProductFilterInput.value = state.automation.promptProductFilter;
    }
  } else if (setting === "imageModel") {
    state.drafts.image.model = value || defaultModelForMode("image");
  } else if (setting === "imageAspect") {
    state.drafts.image.aspect = value || "square";
  } else if (setting === "imageCount") {
    const maxCount = flowAgentEnabledFromSettings(module.settings) ? FLOW_AGENT_TARGET_OUTPUT_COUNT : 4;
    const count = Math.max(1, Math.min(maxCount, Number(value || 1)));
    state.drafts.image.count = count;
    module.settings[setting] = count;
  } else if (setting === "erpProject") {
    state.automation.erpProjectId = String(value || "").trim();
    if (elements.automationERPProjectInput) {
      elements.automationERPProjectInput.value = state.automation.erpProjectId;
    }
    if (elements.automationERPProjectStorageInput) {
      elements.automationERPProjectStorageInput.value = state.automation.erpProjectId;
    }
  } else if (setting === "erpTask") {
    state.automation.erpTaskId = String(value || "").trim();
    if (elements.automationERPTaskInput) {
      elements.automationERPTaskInput.value = state.automation.erpTaskId;
    }
  } else if (setting === "erpStatus") {
    state.automation.erpStatusId = String(value || "").trim();
    if (elements.automationERPStatusInput) {
      elements.automationERPStatusInput.value = state.automation.erpStatusId;
    }
  } else if (setting === "erpAttachmentIds") {
    const ids = String(value || "")
      .split(/[\s,;]+/)
      .map((item) => item.trim())
      .filter(Boolean);
    state.automation.erpAttachmentIds = ids;
    module.settings[setting] = ids;
  } else if (setting === "erpAttachmentLimit") {
    module.settings[setting] = Math.max(1, Math.min(4, Number(value || 1)));
  }
  persistAutomationModules();
}

function automationExecutionGraphPayload() {
  const modules = normalizeAutomationModules(state.automation)
    .map((module) => ({
      id: module.id,
      type: module.type || "custom",
      title: module.title || moduleTypeConfig(module.type).title,
      detail: module.detail || moduleTypeConfig(module.type).detail,
      enabled: module.enabled !== false,
      settings: {
        ...(module.settings || {}),
      },
    }));
  const enabledModules = modules.filter((module) => module.enabled);
  const edges = enabledModules.slice(1).map((module, index) => ({
    source: enabledModules[index].id,
    target: module.id,
    condition: "success",
  }));
  return {
    version: AUTOMATION_CONFIG_VERSION,
    selected_module_id: state.automation.selectedStep || "",
    modules,
    edges,
  };
}

async function handleModuleSettingsAction(action) {
  if (action === "preview-source") {
    await previewPromptSource();
  } else if (action === "upload-source") {
    elements.automationSheetFileInput?.click();
  } else if (action === "save-erp") {
    await saveERPConfig();
  } else if (action === "clear-erp") {
    await saveERPConfig({ clearCredentials: true });
  }
}

async function submitDashboardApproval(jobId, artifactIndex, status) {
  const decision = String(status || "").trim().toLowerCase();
  if (!["approved", "rejected"].includes(decision)) {
    return;
  }
  try {
    await api(`/api/jobs/${encodeURIComponent(jobId)}/artifacts/${encodeURIComponent(artifactIndex)}/approval`, {
      method: "POST",
      body: JSON.stringify({ status: decision }),
    });
    await loadState({ silent: true });
    showMessage(decision === "approved" ? "Đã duyệt ảnh trên dashboard." : "Đã từ chối ảnh trên dashboard.", "success");
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function submitDashboardArtifact(jobId, container, button) {
  const urlInput = container?.querySelector("[data-dashboard-artifact-url]");
  const labelInput = container?.querySelector("[data-dashboard-artifact-label]");
  const url = String(urlInput?.value || "").trim();
  if (!url) {
    showMessage("Hãy dán URL HTTPS của ảnh muốn thêm vào bộ idea.", "error");
    urlInput?.focus();
    return;
  }
  button.disabled = true;
  try {
    await api(`/api/jobs/${encodeURIComponent(jobId)}/artifacts`, {
      method: "POST",
      body: JSON.stringify({
        url,
        label: String(labelInput?.value || "").trim(),
      }),
    });
    await loadState({ silent: true });
    showMessage("Đã thêm ảnh vào bộ idea. Ảnh này đang chờ duyệt.", "success");
  } catch (error) {
    showMessage(error.message, "error");
  } finally {
    button.disabled = false;
  }
}

function automationImageJobPayload(prompt) {
  const imageDraft = state.drafts.image;
  const graph = automationExecutionGraphPayload();
  const flowModule = graph.modules.find((module) => module.enabled && module.type === "flow") || {};
  const flowSettings = flowModule.settings || {};
  const flowAgentEnabled = flowAgentEnabledFromSettings(flowSettings);
  const erpEnabled = automationModuleEnabled("erp");
  return {
    type: "image",
    title: "Automation image from prompt",
    prompt: String(prompt || "").trim(),
    model: flowSettings.imageModel || imageDraft.model || defaultModelForMode("image"),
    aspect: flowSettings.imageAspect || imageDraft.aspect || "square",
    count: flowModuleImageCount(flowSettings, imageDraft.count || MODE_CONFIG.image.defaultCount),
    timeout_s: Math.max(30, Number(elements.generationTimeout.value || state.config?.generation_timeout_s || 300)),
    telegram_enabled: false,
    telegram_chat_id: "",
    erp_enabled: erpEnabled,
    flow_agent_enabled: flowAgentEnabled,
    flow_agent_auto_approve: flowSettings.flowAgentAutoApprove !== false,
    automation_graph: graph,
    erp_project_id: erpEnabled ? currentERPProjectId() : "",
    erp_task_id: erpEnabled ? state.automation.erpTaskId || state.erp?.task_id || "" : "",
    erp_status_id: erpEnabled ? state.automation.erpStatusId || state.erp?.status || "" : "",
    erp_attachment_ids: erpEnabled
      ? Array.isArray(state.automation.erpAttachmentIds)
        ? state.automation.erpAttachmentIds.filter(Boolean)
        : []
      : [],
    prompt_product: state.automation.promptProductFilter || "",
    prompt_product_key: state.automation.promptProductFilter || "",
    prompt_notes: state.automation.promptProductFilter ? `ERP search: ${state.automation.promptProductFilter}` : "",
  };
}

function forcePayloadToReadyERPScope(payload) {
  if (!payload || typeof payload !== "object") {
    return payload;
  }
  const projectId = currentERPProjectId();
  const readyListId = String(state.erp?.status || payload.erp_status_id || "").trim();
  payload.erp_project_id = projectId;
  payload.erp_status_id = readyListId;
  payload.erp_task_id = "";
  payload.erp_attachment_ids = [];
  payload.prompt = "";
  payload.prompt_product = "";
  payload.prompt_product_key = "";
  payload.prompt_notes = "";
  payload.aspect = "square";
  payload.count = FLOW_AGENT_DEFAULT_IMAGE_COUNT;
  payload.flow_agent_enabled = true;
  payload.flow_agent_auto_approve = true;
  const modules = Array.isArray(payload.automation_graph?.modules) ? payload.automation_graph.modules : [];
  modules.forEach((module) => {
    if (!module || !["erp_source", "erp", "flow"].includes(module.type)) {
      return;
    }
    module.settings = module.settings && typeof module.settings === "object" ? module.settings : {};
    if (module.type === "flow") {
      module.settings.imageAspect = "square";
      module.settings.imageCount = FLOW_AGENT_DEFAULT_IMAGE_COUNT;
      module.settings.flowAgentEnabled = true;
      module.settings.flowAgentAutoApprove = true;
      return;
    }
    module.settings.erpProject = projectId;
    if (readyListId) {
      module.settings.erpStatus = readyListId;
    }
    module.settings.erpTask = "";
    module.settings.erpAttachmentIds = [];
    delete module.settings.erpAttachmentId;
  });
  return payload;
}

async function stopContinuousAutoERP() {
  const job = activeContinuousAutoERPJob();
  if (!job) {
    showMessage("Không có Auto AI ERP liên tục nào đang chạy.", "error");
    return;
  }
  if (automationSubmitInFlight) {
    return;
  }
  automationSubmitInFlight = true;
  if (elements.automationAutoRunButton) {
    elements.automationAutoRunButton.disabled = true;
  }
  try {
    await api(`/api/jobs/${encodeURIComponent(job.id)}/stop`, { method: "POST" });
    showMessage("Đã gửi lệnh dừng. App sẽ không nhận thêm Task mới sau tác vụ hiện tại.", "success");
    await loadState({ silent: true });
  } catch (error) {
    showMessage(error.message, "error");
  } finally {
    automationSubmitInFlight = false;
    renderAutomationDashboard();
  }
}

async function submitAutomationImage({ autoERP = false, batchLimit = null, continuousAutoERP = false } = {}) {
  if (automationSubmitInFlight) {
    return;
  }
  syncAutomationFromForm();
  const selectedERPAttachmentIds = Array.isArray(state.automation.erpAttachmentIds)
    ? state.automation.erpAttachmentIds.filter(Boolean)
    : [];
  const selectedERPTask = String(state.automation.erpTaskId || "").trim();
  const selectedERPImageCandidate = Boolean(selectedERPTask && selectedERPAttachmentIds.length);
  const selectedERPImageRun = Boolean(
    !autoERP &&
      selectedERPImageCandidate &&
      (shouldAutoDiscoverERP([]) || String(state.automation.sourceType || FLOW_AI_SOURCE_TYPE) === FLOW_AI_SOURCE_TYPE)
  );
  let batchItems = selectedERPImageRun ? [] : activePromptSourceItems({ limit: autoERP ? Infinity : 500 });
  const erpSearchQuery = String(state.automation.promptProductFilter || "").trim();
  const autoDiscoverERP = Boolean(autoERP || shouldAutoDiscoverERP(batchItems));
  const prompt = String(batchItems[0]?.prompt || state.automation.prompt || "").trim();
  const aiWillWritePrompt = Boolean(autoDiscoverERP && !prompt);
  if (!state.config?.project_id) {
    state.setupOpen = true;
    renderTopbar();
    showMessage("Hãy lưu project Flow trước khi chạy automation.", "error");
    return;
  }
  if (!state.auth?.authenticated) {
    state.setupOpen = true;
    renderTopbar();
    showMessage("Hãy đăng nhập Google Flow trước khi automation tạo ảnh.", "error");
    return;
  }
  if (!prompt && !aiWillWritePrompt) {
    showMessage(
      erpSearchQuery
        ? `Chưa có lệnh nhập tay. Có thể bấm Auto ERP để Tác nhân Flow tự viết prompt cho "${erpSearchQuery}".`
        : "Hãy nhập yêu cầu ngắn, hoặc bấm Auto ERP để Tác nhân Flow tự viết prompt từ Task có ảnh.",
      "error",
    );
    elements.automationPromptInput.focus();
    return;
  }
  if (!automationModuleEnabled("flow")) {
    showMessage("Luồng cần có một cục Google Flow đang bật để tạo ảnh.", "error");
    selectAutomationModuleByType("flow", { create: true });
    return;
  }
  if (autoDiscoverERP && !automationModuleEnabled("erp_source")) {
    showMessage("Auto ERP cần bật cục ERP Task Source để tự tìm ảnh trong Task.", "error");
    selectAutomationModuleByType("erp_source", { create: true });
    return;
  }
  if (autoDiscoverERP && !automationModuleEnabled("erp")) {
    showMessage("Auto ERP cần bật cục ERP Task Comment để ghi URL artifact sau khi duyệt trên dashboard.", "error");
    selectAutomationModuleByType("erp", { create: true });
    return;
  }

  const payload = automationImageJobPayload(prompt);
  const selectedImageDefaultLimit = selectedERPImageRun ? 1 : 0;
  const explicitBatchLimit = Number(batchLimit || 0);
  const runUntilReadyEmpty = Boolean(autoDiscoverERP && !selectedERPImageRun && !(Number.isFinite(explicitBatchLimit) && explicitBatchLimit > 0));
  if (autoDiscoverERP && !selectedERPImageRun) {
    batchItems = [];
    state.automation.promptProductFilter = "";
    forcePayloadToReadyERPScope(payload);
    saveAutomationConfig(state.automation);
  }
  const resolvedBatchLimit = runUntilReadyEmpty
    ? 0
    : Math.max(
        1,
        Math.min(40, Number(explicitBatchLimit || selectedImageDefaultLimit || effectiveAutomationBatchLimit({ autoERP: autoDiscoverERP }) || 1)),
      );
  const queuedCount = autoDiscoverERP
    ? (runUntilReadyEmpty ? 0 : (batchItems.length ? Math.min(batchItems.length, resolvedBatchLimit) : resolvedBatchLimit))
    : batchItems.length > 1 ? Math.min(batchItems.length, resolvedBatchLimit) : 1;

  automationSubmitInFlight = true;
  elements.automationRunButton.disabled = true;
  elements.automationRunImageButton.disabled = true;
  if (elements.automationAutoRunButton) {
    elements.automationAutoRunButton.disabled = true;
  }
  if (elements.easyRunButton) {
    elements.easyRunButton.disabled = true;
  }
  try {
    if (batchItems.length > 1 || autoDiscoverERP) {
      await api("/api/jobs/batch", {
        method: "POST",
        body: JSON.stringify({
          title: continuousAutoERP ? "Auto AI ERP: chờ sản phẩm mới liên tục" : autoDiscoverERP ? "Auto ERP: quét Task có ảnh" : `Chạy ${batchItems.length} prompt từ sheet`,
          limit: continuousAutoERP ? 0 : resolvedBatchLimit,
          auto_erp: autoDiscoverERP,
          run_until_empty: continuousAutoERP || runUntilReadyEmpty,
          continuous: Boolean(continuousAutoERP),
          poll_interval_s: 30,
          job: {
            ...payload,
            title: autoDiscoverERP ? "Auto image from ERP Task" : "Automation image from sheet row",
          },
          items: autoDiscoverERP && !selectedERPImageRun ? [] : batchItems,
        }),
      });
    } else {
      await api("/api/jobs", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    }
    state.mode = "image";
    state.setupOpen = false;
    state.automation.enabled = true;
    saveAutomationConfig(state.automation);
    showMessage(
      autoDiscoverERP
        ? continuousAutoERP
          ? `Đã bật auto liên tục. App sẽ chờ Task mới trong ${DEFAULT_ERP_SOURCE_SCOPE_LABEL} và chạy tới khi bạn bấm Dừng auto.`
          : runUntilReadyEmpty
          ? `Đã xếp hàng chạy 1 lượt. App sẽ quét toàn bộ Task có ảnh trong ${DEFAULT_ERP_SOURCE_SCOPE_LABEL} và chạy tới khi hết danh sách hiện tại.`
          : `Đã xếp hàng chạy 1 lượt. App sẽ quét ${queuedCount} Task có ảnh, nhờ Tác nhân Flow tạo ảnh, chờ duyệt trên dashboard rồi thêm URL artifact vào comment của đúng Task.`
        : batchItems.length > 1
        ? `Đã xếp hàng ${queuedCount} prompt active. App sẽ lấy ảnh ERP, chỉnh bằng Flow, chờ duyệt trên dashboard rồi thêm URL artifact vào Task.`
        : "Đã gửi prompt sang Flow để tạo ảnh. Sau khi duyệt trên dashboard, app sẽ thêm URL artifact vào ERP Task nếu cục ERP đang bật.",
      "success"
    );
    await loadState({ silent: true });
  } catch (error) {
    showMessage(error.message, "error");
  } finally {
    automationSubmitInFlight = false;
    elements.automationRunButton.disabled = false;
    elements.automationRunImageButton.disabled = false;
    if (elements.automationAutoRunButton) {
      elements.automationAutoRunButton.disabled = false;
    }
    if (elements.easyRunButton) {
      elements.easyRunButton.disabled = false;
    }
    renderAutomationDashboard();
  }
}

async function submitCreate(event) {
  event.preventDefault();
  syncDraftFromForm();
  syncEditInputsFromForm();

  if (!state.config?.project_id) {
    state.setupOpen = true;
    renderTopbar();
    showMessage("Hãy lưu project trước.", "error");
    return;
  }

  if (!state.auth?.authenticated) {
    state.setupOpen = true;
    renderTopbar();
    showMessage("Hãy đăng nhập Google Flow trước.", "error");
    return;
  }

  const draft = currentDraft();
  const operationConfig = currentOperationConfig();
  if (operationConfig.promptRequired && !draft.prompt.trim()) {
    showMessage("Hãy nhập mô tả trước khi chạy.", "error");
    elements.promptInput.focus();
    return;
  }

  const payload = {
    type: state.mode,
    prompt: draft.prompt.trim(),
    model: draft.model || defaultModelForMode(state.mode),
    aspect: draft.aspect || currentModeConfig().defaultAspect,
    count: Math.max(1, Math.min(4, Number(draft.count || currentModeConfig().defaultCount))),
    timeout_s: Math.max(30, Number(elements.generationTimeout.value || state.config?.generation_timeout_s || 300)),
  };

  if (state.mode === "video") {
    payload.type = "video";
    if (currentVideoInputMode() === "start") {
      if (!state.startImagePath) {
        showMessage("Hãy tải ảnh đầu vào trước khi chạy video từ ảnh.", "error");
        return;
      }
      payload.start_image_path = state.startImagePath;
    }
    if (currentVideoInputMode() === "reference") {
      if (!state.imageReferenceItems.length) {
        showMessage("Hãy tải ít nhất 1 ảnh sản phẩm hoặc ảnh tham chiếu trước khi chạy.", "error");
        return;
      }
      payload.reference_image_paths = state.imageReferenceItems.map((item) => item.path).filter(Boolean);
      payload.reference_image_roles = state.imageReferenceItems.map((item, index) =>
        normalizeReferenceRoleForMode(item.role || (index === 0 ? "product" : "reference"), "video", index)
      );
    }
  }

  if (state.mode === "image") {
    payload.type = "image";
    if (state.imageReferenceItems.length) {
      payload.reference_image_paths = state.imageReferenceItems.map((item) => item.path).filter(Boolean);
      payload.reference_image_roles = state.imageReferenceItems.map((item, index) => normalizeReferenceRole(item.role || (index === 0 ? "base" : "reference")));
    }
  }

  if (state.mode === "edit") {
    const source = selectedEditSource();
    payload.type = state.editAction;
    payload.prompt = draft.prompt.trim();
    payload.aspect = "landscape";
    payload.count = 1;
    payload.motion = state.motion;
    payload.position = state.position;
    payload.resolution = state.resolution;
    payload.media_id = source?.mediaId || state.manualMediaId.trim();
    payload.workflow_id = source?.workflowId || state.manualWorkflowId.trim();

    if (!payload.media_id || !payload.workflow_id) {
      showMessage("Hãy chọn video cần chỉnh hoặc nhập Media ID và Workflow ID.", "error");
      return;
    }
  }

  elements.submitButton.disabled = true;
  try {
    await api("/api/jobs", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    const submitMessage =
      state.mode === "video" && currentVideoInputMode() === "reference"
        ? "Đã gửi yêu cầu dựng khung đầu rồi tạo video. Tab Google Flow sẽ được giữ mở."
        : state.mode === "video" && currentVideoInputMode() === "start"
        ? "Đã gửi yêu cầu tạo video từ ảnh. Tab Google Flow sẽ được giữ mở."
        : state.mode === "image" && state.imageReferenceItems.length
        ? "Đã gửi yêu cầu chỉnh ảnh từ ảnh tham chiếu. Tab Google Flow sẽ được giữ mở."
        : state.mode === "edit"
        ? `Đã gửi yêu cầu ${currentEditConfig().title.toLowerCase()}. Tab Google Flow sẽ được giữ mở.`
        : `Đã gửi yêu cầu ${state.mode === "video" ? "tạo video" : "tạo ảnh"}. Tab Google Flow sẽ được giữ mở.`;
    showMessage(submitMessage, "success");
    state.setupOpen = false;
    await loadState({ silent: true });
  } catch (error) {
    showMessage(error.message, "error");
  } finally {
    elements.submitButton.disabled = false;
  }
}

function applyGeneratedPromptToComposer(prompt) {
  const text = String(prompt || "").trim();
  if (!text) {
    return;
  }
  elements.promptInput.value = text;
  syncDraftFromForm();
}

async function submitPromptAi() {
  syncPromptAiDraftFromForm();
  const draft = currentPromptAiDraft();
  const brief = String(draft.brief || elements.promptInput.value || "").trim();
  if (!brief) {
    showMessage("Hãy mô tả ngắn gọn điều muốn tạo để AI viết prompt.", "error");
    elements.promptAiBrief.focus();
    return;
  }

  if (!draft.brief.trim()) {
    elements.promptAiBrief.value = brief;
    syncPromptAiDraftFromForm();
  }

  elements.promptAiSubmit.disabled = true;
  try {
    const payload = await api("/api/prompt-ai/generate", {
      method: "POST",
      body: JSON.stringify({
        mode: state.mode,
        brief,
        style: draft.style.trim(),
        must_include: draft.mustInclude.trim(),
        avoid: draft.avoid.trim(),
        audience: draft.audience.trim(),
        aspect: elements.aspectSelect.value || currentModeConfig().defaultAspect,
      }),
    });
    state.promptAiResults[state.mode] = payload;
    applyGeneratedPromptToComposer(payload.prompt || "");
    renderPromptAiResult();
    showMessage("AI đã viết prompt và đổ ngay vào ô tạo.", "success");
    elements.promptInput.focus();
  } catch (error) {
    showMessage(error.message, "error");
  } finally {
    elements.promptAiSubmit.disabled = false;
  }
}

function usePromptAiResult() {
  const result = currentPromptAiResult();
  if (!result?.prompt) {
    showMessage("Chưa có prompt AI nào để dùng lại.", "error");
    return;
  }
  applyGeneratedPromptToComposer(result.prompt);
  showMessage("Đã chép prompt AI xuống ô tạo.", "success");
  elements.promptInput.focus();
}

async function askUserAssistant(questionOverride = "") {
  const question = String(questionOverride || elements.userAssistantQuestion?.value || "").trim();
  if (!question) {
    showMessage("Nhập câu hỏi cho trợ lý trước đã.", "error");
    elements.userAssistantQuestion?.focus();
    return;
  }
  if (elements.userAssistantQuestion && questionOverride) {
    elements.userAssistantQuestion.value = question;
  }

  state.userAssistant.busy = true;
  renderUserAssistant();
  try {
    const payload = await api("/api/assistant/help", {
      method: "POST",
      body: JSON.stringify({
        question,
        context: userAssistantContextSummary(),
      }),
    });
    state.userAssistant.last = { ...payload, question };
    applyAssistantImmediateHints(payload);
    renderUserAssistant();
    showMessage("Trợ lý đã trả lời.", "success");
  } catch (error) {
    showMessage(error.message, "error");
  } finally {
    state.userAssistant.busy = false;
    renderUserAssistant();
  }
}

function mergeAssistantActions(...groups) {
  const merged = [];
  const seen = new Set();
  groups.flat().filter(Boolean).forEach((action) => {
    const payloadKey = action.payload ? JSON.stringify(action.payload).slice(0, 240) : "";
    const key = `${action.action || ""}:${action.label || ""}:${payloadKey}`;
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    merged.push(action);
  });
  return merged.slice(0, 10);
}

async function requestFlowAiOperatorPlan(instructionOverride = "") {
  const instruction = String(
    instructionOverride ||
      elements.userAssistantQuestion?.value ||
      state.userAssistant?.last?.flow_operator_plan?.instruction ||
      "",
  ).trim();
  if (!instruction) {
    showMessage("Nhập yêu cầu cho Flow AI Operator trước đã.", "error");
    elements.userAssistantQuestion?.focus();
    return null;
  }
  const payload = await api("/api/flow-ai/plan", {
    method: "POST",
    body: JSON.stringify({
      instruction,
      context: userAssistantContextSummary(),
      run_mode: "plan",
    }),
  });
  const previous = state.userAssistant.last || {};
  state.userAssistant.last = {
    ...previous,
    answer:
      previous.answer ||
      "Flow AI Operator đã lập kế hoạch. Chủ nhân có thể bấm từng hành động hoặc dùng Làm theo kế hoạch.",
    flow_operator_plan: payload,
    suggested_actions: mergeAssistantActions(payload.suggested_actions || [], previous.suggested_actions || []),
    erp_candidates: payload.erp_candidates || previous.erp_candidates || [],
    engine: payload.engine || previous.engine,
    engine_label: payload.engine_label || previous.engine_label,
    model: payload.model || previous.model,
  };
  applyAssistantImmediateHints(state.userAssistant.last);
  renderUserAssistant();
  showMessage("Flow AI Operator đã sẵn sàng thao tác.", "success");
  return payload;
}

function applyFlowAiPrompt(prompt) {
  const text = String(prompt || "").trim();
  if (!text) {
    showMessage("Flow Agent chưa có lệnh để chuẩn bị.", "error");
    return false;
  }
  applyGeneratedPromptToComposer(text);
  if (elements.automationPromptInput) {
    elements.automationPromptInput.value = text;
  }
  syncAutomationFromForm();
  state.automation.prompt = text;
  saveAutomationConfig(state.automation);
  renderAll();
  showMessage("Đã chuẩn bị lệnh cho Tác nhân Flow. Prompt ảnh cuối sẽ do Google Flow tự viết.", "success");
  return true;
}

function applyAssistantImmediateHints(payload) {
  const actions = Array.isArray(payload?.suggested_actions) ? payload.suggested_actions : [];
  const productAction = actions.find((action) => action?.action === "apply_product_filter" && action?.requires_confirmation !== true);
  const productValue = String(productAction?.payload?.value || "").trim();
  if (productValue && productValue !== String(state.automation.promptProductFilter || "").trim()) {
    setAssistantProductFilter(productValue);
  }
}

function setAssistantProductFilter(value) {
  const filter = String(value || "").trim();
  if (!filter) {
    showMessage("AI chưa nhận ra tên sản phẩm để lọc.", "error");
    return false;
  }
  syncAutomationFromForm();
  state.automation.promptProductFilter = filter;
  state.automation.sourceType = FLOW_AI_SOURCE_TYPE;
  if (state.automation.sourceLocation === DEFAULT_PROMPT_SHEET_URL) {
    state.automation.sourceLocation = "";
  }
  state.automation.modules = normalizeAutomationModules(state.automation).map((module) => {
    if (module.type !== "source") {
      return module;
    }
    return {
      ...module,
      settings: {
        ...(module.settings || {}),
        sourceType: FLOW_AI_SOURCE_TYPE,
        sourceLocation: "",
        promptProductFilter: filter,
      },
    };
  });
  if (elements.automationSourceType) {
    elements.automationSourceType.value = FLOW_AI_SOURCE_TYPE;
  }
  if (elements.automationSourceLocationInput && elements.automationSourceLocationInput.value === DEFAULT_PROMPT_SHEET_URL) {
    elements.automationSourceLocationInput.value = "";
  }
  if (elements.automationProductFilterInput) {
    elements.automationProductFilterInput.value = filter;
  }
  persistAutomationModules();
  renderAll();
  showMessage(`AI đã lọc sản phẩm theo "${filter}".`, "success");
  return true;
}

function setAssistantERPTask(value, options = {}) {
  const card = String(value || "").trim();
  if (!card) {
    showMessage("AI chưa nhận ra ERP Task cần ghim.", "error");
    return false;
  }
  const listId = String(options.listId || "").trim();
  const attachmentId = String(options.attachmentId || "").trim();
  syncAutomationFromForm();
  state.automation.erpTaskId = card;
  if (listId) {
    state.automation.erpStatusId = listId;
  }
  state.automation.erpAttachmentIds = attachmentId ? [attachmentId] : [];
  state.automation.modules = normalizeAutomationModules(state.automation).map((module) => {
    if (!["erp_source", "erp"].includes(module.type)) {
      return module;
    }
    const settings = {
      ...(module.settings || {}),
      erpTask: card,
      ...(listId ? { erpStatus: listId } : {}),
    };
    if (attachmentId) {
      settings.erpAttachmentIds = [attachmentId];
    } else {
      delete settings.erpAttachmentIds;
      delete settings.erpAttachmentId;
    }
    return {
      ...module,
      settings,
    };
  });
  if (elements.automationERPTaskInput) {
    elements.automationERPTaskInput.value = card;
  }
  if (elements.automationERPStatusInput && listId) {
    elements.automationERPStatusInput.value = listId;
  }
  persistAutomationModules();
  renderAll();
  showMessage(
    attachmentId ? `AI đã chọn đúng ảnh ERP "${attachmentId}" trong Task "${card}".` : `AI đã ghim đúng ERP Task "${card}".`,
    "success",
  );
  return true;
}

function assistantTextForBatchIntent() {
  return String(
    state.userAssistant?.last?.question ||
      state.userAssistant?.last?.flow_operator_plan?.instruction ||
      elements.userAssistantQuestion?.value ||
      "",
  ).trim();
}

function normalizedAssistantIntentText() {
  return assistantTextForBatchIntent()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function assistantRequestedSingleTestRun() {
  const text = normalizedAssistantIntentText();
  if (!text) {
    return false;
  }
  return (
    /\b(test|thu|kiem tra|demo)\b/.test(text) ||
    /\b(1|mot|one)\s+(anh|image|prompt|san pham|card)\b/.test(text)
  );
}

function assistantRequestedNumericBatchLimit() {
  const text = normalizedAssistantIntentText();
  if (!text) {
    return null;
  }
  const numberMatch = text.match(/\b(\d{1,2})\s*(prompt|card|san pham)\b/);
  if (numberMatch) {
    return Math.max(1, Math.min(6, Number(numberMatch[1] || 1)));
  }
  const words = {
    mot: 1,
    one: 1,
    hai: 2,
    two: 2,
    ba: 3,
    three: 3,
    bon: 4,
    four: 4,
    nam: 5,
    five: 5,
    sau: 6,
    six: 6,
  };
  for (const [word, value] of Object.entries(words)) {
    if (new RegExp(`\\b${word}\\s*(prompt|card|san pham)\\b`).test(text)) {
      return value;
    }
  }
  return assistantRequestedSingleTestRun() ? 1 : null;
}

function assistantPlanBatchLimit(actions = []) {
  const runAction = actions.find((action) => action?.action === "run_auto_erp");
  const explicitLimit = Number(runAction?.payload?.limit || 0);
  if (Number.isFinite(explicitLimit) && explicitLimit > 0) {
    return explicitLimit;
  }
  return assistantRequestedNumericBatchLimit();
}

async function executeUserAssistantAction(action, { skipConfirmation = false } = {}) {
  if (!action?.action || state.userAssistant.executing) {
    return;
  }
  const actionName = String(action.action || "");
  if (action.requires_confirmation && !skipConfirmation) {
    const ok = window.confirm(`${action.label || "Thực hiện hành động"}?\n\n${action.detail || ""}`);
    if (!ok) {
      return;
    }
  }

  state.userAssistant.executing = true;
  renderUserAssistant();
  try {
    if (actionName === "apply_product_filter") {
      setAssistantProductFilter(action.payload?.value || "");
    } else if (actionName === "set_erp_task") {
      const selected = setAssistantERPTask(action.payload?.value || "", {
        listId: action.payload?.status || "",
        attachmentId: action.payload?.attachment_id || "",
      });
      if (selected && action.payload?.run_after_select) {
        await submitAutomationImage({
          autoERP: true,
          batchLimit: assistantPlanBatchLimit(state.userAssistant?.last?.suggested_actions || []),
        });
      }
    } else if (actionName === "plan_flow_ai_operator") {
      await requestFlowAiOperatorPlan(action.payload?.instruction || "");
    } else if (actionName === "apply_flow_ai_prompt") {
      applyFlowAiPrompt(action.payload?.prompt || state.userAssistant?.last?.flow_operator_plan?.flow_prompt || "");
    } else if (actionName === "preview_prompt_source") {
      await previewPromptSource();
    } else if (actionName === "open_dashboard_review") {
      elements.dashboardReviewQueue?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      showMessage("Các artefact chờ duyệt đang hiển thị ngay trên dashboard.", "success");
    } else if (actionName === "open_flow_project") {
      await openFlowProjectSurface();
    } else if (actionName === "select_erp_source") {
      selectAutomationModuleByType("erp_source", { create: true });
      showMessage("AI đã mở cục ERP Task Source để kiểm tra nguồn ảnh.", "success");
    } else if (actionName === "run_auto_erp") {
      if (state.automation.sourceType === "sheets" && String(state.automation.sourceLocation || "").trim() && !activePromptSourceItems({ limit: 500 }).length) {
        await previewPromptSource(null, { silent: true });
      }
      await submitAutomationImage({ autoERP: true, batchLimit: action.payload?.limit || null });
    } else {
      showMessage("Hành động AI này chưa được app hỗ trợ.", "error");
    }
  } catch (error) {
    showMessage(error.message || "AI chưa thực hiện được hành động này.", "error");
  } finally {
    state.userAssistant.executing = false;
    renderUserAssistant();
  }
}

async function executeUserAssistantPlan() {
  const actions = Array.isArray(state.userAssistant?.last?.suggested_actions)
    ? state.userAssistant.last.suggested_actions.filter((action) => action?.action)
    : [];
  if (!actions.length || state.userAssistant.executing) {
    return;
  }
  const hasRunAction = actions.some((action) => action.action === "run_auto_erp");
  const erpCandidates = Array.isArray(state.userAssistant?.last?.erp_candidates)
    ? state.userAssistant.last.erp_candidates.filter(Boolean)
    : [];
  const selectedAttachmentIds = Array.isArray(state.automation?.erpAttachmentIds)
    ? state.automation.erpAttachmentIds.filter(Boolean)
    : [];
  if (!hasRunAction && erpCandidates.length) {
    if (state.automation?.erpTaskId && selectedAttachmentIds.length) {
      showMessage("Đã có ảnh ERP được chọn, app bắt đầu chạy Auto ERP cho đúng ảnh đó.", "success");
      await submitAutomationImage({ autoERP: true, batchLimit: assistantPlanBatchLimit(actions) });
      return;
    }
    showMessage("Hãy bấm đúng thumbnail ảnh ERP trước, rồi bấm Chạy ảnh đã chọn.", "error");
    return;
  }
  const needsConfirmation = actions.some((action) => action.requires_confirmation);
  if (needsConfirmation) {
    const ok = window.confirm("AI sẽ thực hiện các bước có thể làm trong app. Nếu có bước chạy Auto ERP, app sẽ bắt đầu tạo/chỉnh ảnh bằng Flow. Tiếp tục?");
    if (!ok) {
      return;
    }
  }
  const setCardActions = actions.filter((action) => action.action === "set_erp_task");
  const orderedActions = actions.slice().sort((left, right) => {
    if (left.action === "run_auto_erp") {
      return 1;
    }
    if (right.action === "run_auto_erp") {
      return -1;
    }
    return 0;
  });
  for (const action of orderedActions) {
    if (setCardActions.length > 1 && action.action === "set_erp_task") {
      continue;
    }
    await executeUserAssistantAction(action, { skipConfirmation: true });
  }
}

async function requestStoryboardPlan() {
  syncStoryboardDraftFromForm();
  const script = String(state.storyboardDraft.script || "").trim();
  if (!script) {
    showMessage("Hãy dán kịch bản trước khi tách cảnh.", "error");
    elements.storyboardScript.focus();
    return null;
  }

  const payload = await api("/api/storyboard/plan", {
    method: "POST",
    body: JSON.stringify({
      script,
      style: String(state.storyboardDraft.style || "").trim(),
      must_include: String(state.storyboardDraft.mustInclude || "").trim(),
      avoid: String(state.storyboardDraft.avoid || "").trim(),
      aspect: elements.aspectSelect.value || currentModeConfig().defaultAspect,
      scene_count: Math.max(0, Number(state.storyboardDraft.sceneCount || 0)),
    }),
  });
  state.storyboardPlan = payload;
  renderStoryboardCard();
  return payload;
}

async function submitStoryboardPlan() {
  state.storyboardBusy = true;
  renderStoryboardCard();
  try {
    const payload = await requestStoryboardPlan();
    if (!payload) {
      return;
    }
    showMessage(`Đã tách ${payload.scene_count || 0} cảnh storyboard từ kịch bản.`, "success");
  } catch (error) {
    showMessage(error.message, "error");
  } finally {
    state.storyboardBusy = false;
    renderStoryboardCard();
  }
}

async function submitStoryboardImages() {
  state.storyboardBusy = true;
  renderStoryboardCard();
  let createdCount = 0;
  try {
    const plan = await requestStoryboardPlan();
    if (!plan) {
      return;
    }
    if (!isReady()) {
      showMessage(
        `Đã tách ${plan.scene_count || 0} cảnh. Hãy đăng nhập Google Flow rồi bấm lại để app tạo luôn các ảnh storyboard.`,
        "error"
      );
      return;
    }

    const imageModel = state.drafts.image.model || defaultModelForMode("image");
    const aspect = elements.aspectSelect.value || currentModeConfig().defaultAspect;
    const items = Array.isArray(plan.items) ? plan.items : [];
    for (const item of items) {
      const sceneIndex = Math.max(1, Number(item.index || createdCount + 1));
      const title = String(item.title || `Cảnh ${sceneIndex}`).trim();
      const prompt = String(item.image_prompt || "").trim();
      if (!prompt) {
        continue;
      }
      await api("/api/jobs", {
        method: "POST",
        body: JSON.stringify({
          type: "image",
          title: `Storyboard ảnh cảnh ${sceneIndex} · ${title}`,
          prompt,
          model: imageModel,
          aspect,
          count: 1,
          timeout_s: Math.max(30, Number(state.config?.generation_timeout_s || 300)),
        }),
      });
      createdCount += 1;
    }

    state.mode = "image";
    state.setupOpen = false;
    await loadState({ silent: true });
    showMessage(
      `Đã xếp ${createdCount} ảnh storyboard từ kịch bản. Em đã chuyển sang tab Ảnh để chủ nhân theo dõi kết quả.`,
      "success"
    );
  } catch (error) {
    if (createdCount > 0) {
      state.mode = "image";
      await loadState({ silent: true });
      showMessage(
        `Đã xếp ${createdCount} ảnh storyboard rồi, nhưng các cảnh tiếp theo dừng lại vì: ${error.message}`,
        "error"
      );
    } else {
      showMessage(error.message, "error");
    }
  } finally {
    state.storyboardBusy = false;
    renderStoryboardCard();
  }
}

function buildRetryPayload(job) {
  const input = job?.input || {};
  return {
    type: job.type,
    prompt: String(input.prompt || "").trim(),
    title: "",
    timeout_s: Math.max(30, Number(input.timeout_s || state.config?.generation_timeout_s || 300)),
    source_job_id: job.id,
    model: String(input.model || defaultModelForMode(modeForJobType(job.type))).trim(),
    aspect: String(input.aspect || MODE_CONFIG[job.type]?.defaultAspect || "landscape").trim(),
    count: Math.max(1, Math.min(4, Number(input.count || MODE_CONFIG[job.type]?.defaultCount || 1))),
    start_image_path: String(input.start_image_path || "").trim(),
    reference_image_paths: Array.isArray(input.reference_image_paths) ? input.reference_image_paths : [],
    reference_image_roles: Array.isArray(input.reference_image_roles) ? input.reference_image_roles : [],
    reference_media_names: Array.isArray(input.reference_media_names) ? input.reference_media_names : [],
    media_id: String(input.media_id || "").trim(),
    workflow_id: String(input.workflow_id || "").trim(),
    motion: String(input.motion || "").trim(),
    position: String(input.position || "").trim(),
    resolution: String(input.resolution || "1080p").trim() || "1080p",
    mask_x: Number(input.mask_x ?? 0.5),
    mask_y: Number(input.mask_y ?? 0.5),
    brush_size: Number(input.brush_size ?? 40),
  };
}

async function fetchFullJob(jobId) {
  const id = String(jobId || "").trim();
  if (!id) {
    return null;
  }
  const payload = await api(`/api/jobs/${encodeURIComponent(id)}`);
  return payload?.item || (state.jobs || []).find((item) => item.id === id) || null;
}

async function retryJob(jobId) {
  let job = (state.jobs || []).find((item) => item.id === jobId);
  try {
    job = await fetchFullJob(jobId);
  } catch (error) {
    showMessage(error.message, "error");
    return;
  }
  if (!job) {
    showMessage("Không tìm thấy lượt chạy để thử lại.", "error");
    return;
  }

  try {
    await api("/api/jobs", {
      method: "POST",
      body: JSON.stringify(buildRetryPayload(job)),
    });
    showMessage("Đã gửi lại lượt chạy với đúng cấu hình cũ. Tab Google Flow sẽ được giữ mở.", "success");
    state.setupOpen = false;
    await loadState({ silent: true });
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function reuseJob(jobId) {
  let job = (state.jobs || []).find((item) => item.id === jobId);
  try {
    job = await fetchFullJob(jobId);
  } catch (error) {
    showMessage(error.message, "error");
    return;
  }
  if (!job) {
    showMessage("Không tìm thấy lượt chạy để dùng lại.", "error");
    return;
  }

  fillComposerFromSource(job.type, job.input || {});
  showMessage("Đã đổ lại prompt và thông số lên form.", "success");
}

function changeMode(mode) {
  if (!MODE_CONFIG[mode] || mode === state.mode) {
    return;
  }
  syncDraftFromForm();
  syncPromptAiDraftFromForm();
  state.mode = mode;
  if (mode === "video" && !state.drafts.video.inputMode) {
    state.drafts.video.inputMode = "prompt";
  }
  renderAll();
}

function parseVideoModelOptions(payload) {
  const items = Array.isArray(payload?.result?.videoModels) ? payload.result.videoModels : [];
  const seen = new Set();
  const options = [];
  for (const item of items) {
    const label = String(item?.displayName || "").trim();
    const caps = Array.isArray(item?.capabilities) ? item.capabilities : [];
    const deprecated = String(item?.modelStatus || "").toUpperCase().includes("DEPRECATED");
    if (!label || deprecated || label.includes("[Lower Priority]")) {
      continue;
    }
    const supportsCreate =
      caps.includes("VIDEO_MODEL_CAPABILITY_TEXT") ||
      caps.includes("VIDEO_MODEL_CAPABILITY_START_IMAGE");
    if (!supportsCreate || seen.has(label)) {
      continue;
    }
    seen.add(label);
    options.push({ value: label, label });
  }
  return options.length ? options : [...FALLBACK_VIDEO_MODELS];
}

async function loadModelOptions() {
  if (state.modelOptionsLoading || !isReady()) {
    return;
  }
  state.modelOptionsLoading = true;
  try {
    const payload = await api("/api/models");
    state.modelOptions.video = parseVideoModelOptions(payload);
    state.modelOptions.image = [...FALLBACK_IMAGE_MODELS];
    state.modelOptionsLoaded = true;
    state.drafts.video.model = state.modelOptions.video.some((item) => item.value === state.drafts.video.model)
      ? state.drafts.video.model
      : defaultModelForMode("video");
    state.drafts.image.model = state.modelOptions.image.some((item) => item.value === state.drafts.image.model)
      ? state.drafts.image.model
      : defaultModelForMode("image");
    if (state.mode !== "edit") {
      renderComposer();
    }
  } catch (error) {
    state.modelOptions.video = [...FALLBACK_VIDEO_MODELS];
    state.modelOptions.image = [...FALLBACK_IMAGE_MODELS];
  } finally {
    state.modelOptionsLoading = false;
  }
}

function setupPolling() {
  window.setInterval(() => {
    if (document.hidden || stateLoadPromise) {
      return;
    }
    loadState({ silent: true });
  }, 5000);
}

function isAutomationCanvasControl(target) {
  return Boolean(target.closest(".scenario-canvas-tools, button, a, input, textarea, select, [contenteditable='true']"));
}

function handleAutomationCanvasPointerDown(event) {
  if (event.button !== 0 || !elements.scenarioCanvas || isAutomationCanvasControl(event.target)) {
    return;
  }
  event.preventDefault();
  automationCanvasPan = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    scrollLeft: elements.scenarioCanvas.scrollLeft,
    scrollTop: elements.scenarioCanvas.scrollTop,
  };
  elements.scenarioCanvas.classList.add("is-panning");
  elements.scenarioCanvas.setPointerCapture?.(event.pointerId);
}

function handleAutomationCanvasPointerMove(event) {
  if (!automationCanvasPan || automationCanvasPan.pointerId !== event.pointerId || !elements.scenarioCanvas) {
    return;
  }
  event.preventDefault();
  const dx = event.clientX - automationCanvasPan.startX;
  const dy = event.clientY - automationCanvasPan.startY;
  elements.scenarioCanvas.scrollLeft = automationCanvasPan.scrollLeft - dx;
  elements.scenarioCanvas.scrollTop = automationCanvasPan.scrollTop - dy;
}

function stopAutomationCanvasPan(event) {
  if (!automationCanvasPan || (event?.pointerId && automationCanvasPan.pointerId !== event.pointerId)) {
    return;
  }
  if (event?.pointerId) {
    elements.scenarioCanvas?.releasePointerCapture?.(event.pointerId);
  }
  elements.scenarioCanvas?.classList.remove("is-panning");
  automationCanvasPan = null;
}

function clearAutomationDragState() {
  automationDraggedStepId = "";
  elements.scenarioNodeRow?.querySelectorAll(".is-dragging, .is-drop-target").forEach((node) => {
    node.classList.remove("is-dragging", "is-drop-target");
  });
}

function reorderAutomationModules(dragStepId, targetStepId) {
  if (!dragStepId || !targetStepId || dragStepId === targetStepId) {
    clearAutomationDragState();
    return;
  }
  syncAutomationFromForm();
  state.automation.modules = normalizeAutomationModules(state.automation);
  const fromIndex = state.automation.modules.findIndex((module) => module.id === dragStepId);
  const toIndex = state.automation.modules.findIndex((module) => module.id === targetStepId);
  if (fromIndex < 0 || toIndex < 0) {
    clearAutomationDragState();
    return;
  }
  const [module] = state.automation.modules.splice(fromIndex, 1);
  state.automation.modules.splice(toIndex, 0, module);
  state.automation.selectedStep = module.id;
  persistAutomationModules();
  renderAutomationDashboard();
  window.setTimeout(() => scrollAutomationNodeIntoView(module.id), 0);
  showMessage("Đã đổi vị trí module trên sơ đồ.", "success");
}

function handleAutomationKeyboard(event) {
  if (state.automation.view !== "diagram" || event.metaKey || event.ctrlKey || event.altKey) {
    return;
  }
  const active = document.activeElement;
  if (active?.matches?.("input, textarea, select, [contenteditable='true']")) {
    return;
  }
  if (event.key === "+" || event.key === "=") {
    event.preventDefault();
    setAutomationCanvasZoom(state.automation.canvasZoom + AUTOMATION_CANVAS_ZOOM_STEP);
  } else if (event.key === "-") {
    event.preventDefault();
    setAutomationCanvasZoom(state.automation.canvasZoom - AUTOMATION_CANVAS_ZOOM_STEP);
  } else if (event.key === "0") {
    event.preventDefault();
    setAutomationCanvasZoom(1);
  }
}

elements.modeButtons.forEach((button) => {
  button.addEventListener("click", () => changeMode(button.dataset.mode));
});

elements.videoInputModeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    if (state.mode !== "video") {
      return;
    }
    setVideoInputMode(button.dataset.videoInputMode, { clearConflicts: true, announce: true });
    renderAll();
  });
});

elements.editActionButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.editAction = button.dataset.editAction || "extend";
    renderAll();
  });
});

elements.setupToggle.addEventListener("click", () => {
  state.setupOpen = !state.setupOpen;
  renderTopbar();
});

elements.configForm.addEventListener("submit", saveConfig);
elements.loginButton.addEventListener("click", loginFlow);
elements.openFlowButton.addEventListener("click", openFlowProjectSurface);
elements.openLoginButton.addEventListener("click", openFlowLoginSurface);
elements.openProjectButton.addEventListener("click", openFlowProjectSurface);
elements.focusProjectButton.addEventListener("click", openFlowProjectSurface);
elements.automationEnabled.addEventListener("change", () => {
  syncAutomationFromForm();
  renderTopbar();
  renderAutomationDashboard();
});
elements.automationOpenFlowButton.addEventListener("click", openFlowProjectSurface);
elements.automationRefreshButton.addEventListener("click", () => loadState());
elements.automationHistoryRefreshButton.addEventListener("click", () => loadState());
elements.automationIncompleteRefreshButton.addEventListener("click", () => loadState());
elements.automationRunButton.addEventListener("click", submitAutomationImage);
elements.automationRunImageButton.addEventListener("click", submitAutomationImage);
elements.automationAutoRunButton?.addEventListener("click", async () => {
  if (activeContinuousAutoERPJob()) {
    void stopContinuousAutoERP();
    return;
  }
  const ready = await prepareReadyForAutoERP();
  if (!ready) {
    return;
  }
  void submitAutomationImage({ autoERP: true, continuousAutoERP: true });
});
elements.automationUseStudioButton.addEventListener("click", useAutomationPromptInStudio);
elements.automationExportButton.addEventListener("click", exportAutomationConfig);
elements.automationImportButton.addEventListener("click", () => elements.automationImportFile.click());
elements.automationImportFile.addEventListener("change", importAutomationConfig);
elements.automationResetButton.addEventListener("click", resetAutomationConfig);
elements.automationZoomOut?.addEventListener("click", () => setAutomationCanvasZoom(state.automation.canvasZoom - AUTOMATION_CANVAS_ZOOM_STEP));
elements.automationZoomIn?.addEventListener("click", () => setAutomationCanvasZoom(state.automation.canvasZoom + AUTOMATION_CANVAS_ZOOM_STEP));
elements.automationZoomReset?.addEventListener("click", () => setAutomationCanvasZoom(1));
elements.automationFitButton?.addEventListener("click", fitAutomationCanvas);
elements.easyPromptButton?.addEventListener("click", () => {
  state.automation.view = "diagram";
  selectAutomationModuleByType("source", { create: true });
  window.setTimeout(() => {
    if (state.automation.sourceType !== "sheets") {
      elements.automationProductFilterInput?.focus();
    } else if (!String(state.automation.prompt || "").trim()) {
      elements.automationSheetPasteInput?.focus();
    } else {
      elements.automationPromptInput?.focus();
    }
  }, 0);
});
elements.easyFlowButton?.addEventListener("click", async () => {
  state.automation.view = "diagram";
  selectAutomationModuleByType("flow", { create: true });
  if (!state.config?.project_id) {
    state.setupOpen = true;
    renderTopbar();
    elements.projectId?.focus();
    showMessage("Dán link project Flow rồi bấm Lưu project.", "error");
    return;
  }
  if (!state.auth?.authenticated) {
    await loginFlow();
    return;
  }
  await openFlowProjectSurface();
});
elements.easyReviewButton?.addEventListener("click", () => {
  state.automation.view = "diagram";
  selectAutomationModuleByType("approval", { create: true });
  window.setTimeout(() => {
    elements.dashboardReviewQueue?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, 0);
});
elements.easyRunButton?.addEventListener("click", submitAutomationImage);
elements.automationModuleAddButton?.addEventListener("click", () => addAutomationModule());
elements.automationModuleDuplicateButton?.addEventListener("click", () => addAutomationModule({ duplicate: true }));
elements.automationModuleDeleteButton?.addEventListener("click", deleteSelectedAutomationModule);
elements.automationModuleMoveLeftButton?.addEventListener("click", () => moveSelectedAutomationModule(-1));
elements.automationModuleMoveRightButton?.addEventListener("click", () => moveSelectedAutomationModule(1));
elements.automationModuleSettings?.addEventListener("input", (event) => {
  const control = event.target.closest("[data-module-setting]");
  if (!control) {
    return;
  }
  syncModuleSettingFromControl(control);
});
elements.automationModuleSettings?.addEventListener("change", (event) => {
  const control = event.target.closest("[data-module-setting]");
  if (!control) {
    return;
  }
  syncModuleSettingFromControl(control);
  renderAutomationDashboard();
});
elements.automationModuleSettings?.addEventListener("click", (event) => {
  const action = event.target.closest("[data-module-action]")?.dataset.moduleAction;
  if (!action) {
    return;
  }
  handleModuleSettingsAction(action);
});
elements.automationSheetPreviewButton?.addEventListener("click", () => previewPromptSource());
elements.automationSheetFileButton?.addEventListener("click", () => elements.automationSheetFileInput?.click());
elements.automationSheetFileInput?.addEventListener("change", (event) => {
  const file = event.target.files?.[0];
  if (file) {
    previewPromptSource(file);
  }
});
elements.automationERPSaveButton?.addEventListener("click", () => saveERPConfig());
elements.automationERPIdeaRunButton?.addEventListener("click", () => runERPIdeaBatch());
elements.automationERPClearButton?.addEventListener("click", () => saveERPConfig({ clearCredentials: true }));

elements.erpWizardSaveButton?.addEventListener("click", () => {
  void submitERPWizard();
});
elements.erpWizardCloseTriggers.forEach((node) => {
  node.addEventListener("click", () => closeERPWizard({ remember: true }));
});
document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") {
    return;
  }
  const wizard = elements.erpSetupWizard;
  if (wizard && !wizard.hidden) {
    closeERPWizard({ remember: true });
  }
});
elements.userAssistantAskButton?.addEventListener("click", () => askUserAssistant());
elements.userAssistantQuestion?.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    event.preventDefault();
    void askUserAssistant();
  }
});
elements.userAssistantQuickButtons.forEach((button) => {
  button.addEventListener("click", () => askUserAssistant(button.dataset.assistantQuestion || ""));
});
elements.userAssistantAnswer?.addEventListener("click", (event) => {
  const candidateButton = event.target.closest("[data-assistant-card-value]");
  if (candidateButton) {
    const selected = setAssistantERPTask(candidateButton.dataset.assistantCardValue || "", {
      listId: candidateButton.dataset.assistantListId || "",
      attachmentId: candidateButton.dataset.assistantAttachmentId || "",
    });
    if (selected && candidateButton.dataset.assistantRunAfterSelect === "true") {
      window.setTimeout(() => {
        const actions = Array.isArray(state.userAssistant?.last?.suggested_actions)
          ? state.userAssistant.last.suggested_actions.filter((action) => action?.action)
          : [];
        void submitAutomationImage({ autoERP: true, batchLimit: assistantPlanBatchLimit(actions) });
      }, 0);
    }
    return;
  }
  const planButton = event.target.closest("[data-assistant-action-plan]");
  if (planButton) {
    void executeUserAssistantPlan();
    return;
  }
  const actionButton = event.target.closest("[data-assistant-action-index]");
  if (!actionButton) {
    return;
  }
  const index = Number(actionButton.dataset.assistantActionIndex);
  const action = state.userAssistant?.last?.suggested_actions?.[index];
  void executeUserAssistantAction(action);
});
elements.automationEnvSaveButton?.addEventListener("click", () => saveIntegrationConfig());
elements.automationEnvClearButton?.addEventListener("click", () => saveIntegrationConfig({ clearSecrets: true }));
elements.automationViewButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.automation.view = button.dataset.automationView || "diagram";
    saveAutomationConfig(state.automation);
    renderAutomationDashboard();
  });
});
elements.scenarioCanvas?.addEventListener("pointerdown", handleAutomationCanvasPointerDown);
elements.scenarioCanvas?.addEventListener("pointermove", handleAutomationCanvasPointerMove);
elements.scenarioCanvas?.addEventListener("pointerup", stopAutomationCanvasPan);
elements.scenarioCanvas?.addEventListener("pointercancel", stopAutomationCanvasPan);
elements.scenarioCanvas?.addEventListener("wheel", (event) => {
  if (!event.ctrlKey && !event.metaKey) {
    return;
  }
  event.preventDefault();
  setAutomationCanvasZoom(state.automation.canvasZoom + (event.deltaY > 0 ? -AUTOMATION_CANVAS_ZOOM_STEP : AUTOMATION_CANVAS_ZOOM_STEP));
}, { passive: false });
elements.scenarioNodeRow?.addEventListener("dragstart", (event) => {
  const node = event.target.closest(".scenario-node");
  if (!node) {
    return;
  }
  automationDraggedStepId = node.dataset.scenarioStep || "";
  node.classList.add("is-dragging");
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", automationDraggedStepId);
});
elements.scenarioNodeRow?.addEventListener("dragover", (event) => {
  const node = event.target.closest(".scenario-node");
  if (!node || !automationDraggedStepId || node.dataset.scenarioStep === automationDraggedStepId) {
    return;
  }
  event.preventDefault();
  event.dataTransfer.dropEffect = "move";
  elements.scenarioNodeRow.querySelectorAll(".is-drop-target").forEach((item) => item.classList.remove("is-drop-target"));
  node.classList.add("is-drop-target");
});
elements.scenarioNodeRow?.addEventListener("dragleave", (event) => {
  event.target.closest(".scenario-node")?.classList.remove("is-drop-target");
});
elements.scenarioNodeRow?.addEventListener("drop", (event) => {
  const node = event.target.closest(".scenario-node");
  if (!node) {
    clearAutomationDragState();
    return;
  }
  event.preventDefault();
  reorderAutomationModules(automationDraggedStepId || event.dataTransfer.getData("text/plain"), node.dataset.scenarioStep || "");
});
elements.scenarioNodeRow?.addEventListener("dragend", clearAutomationDragState);
document.addEventListener("keydown", handleAutomationKeyboard);
elements.scenarioCanvas.addEventListener("click", (event) => {
  const target = event.target.closest("[data-scenario-step]");
  if (!target) {
    return;
  }
  const nextStep = target.dataset.scenarioStep || "flow";
  if (!state.automation.modules.some((module) => module.id === nextStep)) {
    return;
  }
  syncAutomationFromForm();
  state.automation.selectedStep = nextStep;
  saveAutomationConfig(state.automation);
  renderAutomationDashboard();
  window.setTimeout(() => scrollAutomationNodeIntoView(nextStep), 0);
});
[
  elements.automationPromptInput,
  elements.automationSourceType,
  elements.automationStepNameInput,
  elements.automationStepDetailInput,
  elements.automationStepIconInput,
  elements.automationModuleTypeInput,
  elements.automationModuleEnabledInput,
  elements.automationSheetInput,
  elements.automationERPProjectInput,
  elements.automationERPProjectStorageInput,
  elements.automationERPTaskInput,
  elements.automationERPStatusInput,
  elements.automationAppEyebrowInput,
  elements.automationAppTitleInput,
  elements.automationAppSubtitleInput,
  elements.automationSourceLocationInput,
  elements.automationProductFilterInput,
  elements.automationAccentInput,
]
  .filter(Boolean)
  .forEach((control) => {
  const isBrandControl = [
    elements.automationAppEyebrowInput,
    elements.automationAppTitleInput,
    elements.automationAppSubtitleInput,
    elements.automationAccentInput,
  ].includes(control);
  control.addEventListener("input", () => {
    syncAutomationFromForm();
    if (isBrandControl) {
      renderAll();
    } else {
      renderAutomationDashboard();
    }
  });
  control.addEventListener("change", () => {
    syncAutomationFromForm();
    if (isBrandControl) {
      renderAll();
    } else {
      renderAutomationDashboard();
    }
  });
});
elements.logoutButton.addEventListener("click", logoutFlow);
elements.startImageFile.addEventListener("change", uploadStartImage);
elements.imageReferenceFiles.addEventListener("change", uploadImageReferences);
elements.clearStartImageButton.addEventListener("click", clearStartImage);
elements.editSourceSelect.addEventListener("change", () => {
  if (elements.editSourceSelect.value) {
    state.manualMediaId = "";
    state.manualWorkflowId = "";
  }
  syncEditInputsFromForm();
  renderComposerSummary();
  renderEditControls();
});
elements.editSourceCards.addEventListener("click", (event) => {
  const actionTarget = event.target.closest("[data-action='pick-edit-source']");
  if (!actionTarget) {
    return;
  }
  state.selectedEditSourceKey = actionTarget.dataset.key || "";
  state.manualMediaId = "";
  state.manualWorkflowId = "";
  applyEditInputsToForm();
  renderComposerSummary();
  renderEditControls();
});
elements.manualMediaId.addEventListener("input", () => {
  if (elements.manualMediaId.value.trim()) {
    state.selectedEditSourceKey = "";
  }
  syncEditInputsFromForm();
  renderComposerSummary();
  renderEditControls();
});
elements.manualWorkflowId.addEventListener("input", () => {
  if (elements.manualWorkflowId.value.trim()) {
    state.selectedEditSourceKey = "";
  }
  syncEditInputsFromForm();
  renderComposerSummary();
  renderEditControls();
});
elements.motionSelect.addEventListener("change", syncEditInputsFromForm);
elements.positionSelect.addEventListener("change", syncEditInputsFromForm);
elements.resolutionSelect.addEventListener("change", syncEditInputsFromForm);
elements.composerForm.addEventListener("submit", submitCreate);
elements.refreshButton.addEventListener("click", () => loadState());
elements.promptAiSubmit.addEventListener("click", submitPromptAi);
elements.usePromptAiResultButton.addEventListener("click", usePromptAiResult);
elements.storyboardPlanButton.addEventListener("click", submitStoryboardPlan);
elements.storyboardGenerateButton.addEventListener("click", submitStoryboardImages);
elements.promptAiBrief.addEventListener("input", syncPromptAiDraftFromForm);
elements.promptAiStyle.addEventListener("input", syncPromptAiDraftFromForm);
elements.promptAiMustInclude.addEventListener("input", syncPromptAiDraftFromForm);
elements.promptAiAvoid.addEventListener("input", syncPromptAiDraftFromForm);
elements.promptAiAudience.addEventListener("input", syncPromptAiDraftFromForm);
elements.storyboardScript.addEventListener("input", syncStoryboardDraftFromForm);
elements.storyboardStyle.addEventListener("input", syncStoryboardDraftFromForm);
elements.storyboardMustInclude.addEventListener("input", syncStoryboardDraftFromForm);
elements.storyboardAvoid.addEventListener("input", syncStoryboardDraftFromForm);
elements.storyboardSceneCount.addEventListener("change", syncStoryboardDraftFromForm);
elements.promptInput.addEventListener("input", syncDraftFromForm);
elements.promptInput.addEventListener("input", renderComposerSummary);
elements.modelSelect.addEventListener("change", () => {
  syncDraftFromForm();
  renderComposerSummary();
});
elements.aspectSelect.addEventListener("change", () => {
  syncDraftFromForm();
  renderAspectChoices();
});
elements.aspectChoices.addEventListener("click", (event) => {
  const button = event.target.closest("[data-aspect-option]");
  if (!button) {
    return;
  }
  elements.aspectSelect.value = button.dataset.aspectOption || currentModeConfig().defaultAspect;
  syncDraftFromForm();
  renderAspectChoices();
});
elements.countInput.addEventListener("input", () => {
  syncDraftFromForm();
  renderCountChoices();
});
elements.countChoices.addEventListener("click", (event) => {
  const button = event.target.closest("[data-count-option]");
  if (!button) {
    return;
  }
  elements.countInput.value = button.dataset.countOption || String(currentModeConfig().defaultCount);
  syncDraftFromForm();
  renderCountChoices();
});
elements.latestStatusCard.addEventListener("click", (event) => {
  const actionTarget = event.target.closest("[data-action]");
  if (!actionTarget) {
    return;
  }
  if (actionTarget.dataset.action === "open-flow-project") {
    openFlowProjectSurface();
    return;
  }
  if (actionTarget.dataset.action === "retry-job") {
    retryJob(actionTarget.dataset.jobId);
    return;
  }
  if (actionTarget.dataset.action === "reuse-job") {
    reuseJob(actionTarget.dataset.jobId);
  }
});
elements.dashboardReviewQueue?.addEventListener("click", (event) => {
  const addTarget = event.target.closest("[data-dashboard-artifact-add]");
  if (addTarget) {
    const container = addTarget.closest("[data-dashboard-review-job]");
    void submitDashboardArtifact(addTarget.dataset.jobId || "", container, addTarget);
    return;
  }
  const actionTarget = event.target.closest("[data-dashboard-approval]");
  if (!actionTarget) {
    return;
  }
  void submitDashboardApproval(
    actionTarget.dataset.jobId || "",
    Number(actionTarget.dataset.artifactIndex || -1),
    actionTarget.dataset.dashboardApproval || "",
  );
});
elements.imageReferenceList.addEventListener("click", (event) => {
  const promoteTarget = event.target.closest("[data-action='promote-reference-image']");
  if (promoteTarget) {
    promoteReferenceImage(promoteTarget.dataset.index);
    return;
  }
  const actionTarget = event.target.closest("[data-action='remove-reference-image']");
  if (!actionTarget) {
    return;
  }
  removeReferenceImage(actionTarget.dataset.index);
});
elements.imageReferenceList.addEventListener("change", (event) => {
  const select = event.target.closest("[data-action='reference-role']");
  if (!select) {
    return;
  }
  setReferenceImageRole(select.dataset.index, select.value);
});

loadState();
setupPolling();
