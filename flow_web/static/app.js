const ACTIVE_STATUSES = new Set(["queued", "running", "polling"]);
const EDIT_JOB_TYPES = new Set(["extend", "upscale", "camera_motion", "camera_position", "insert", "remove"]);
const FALLBACK_VIDEO_MODELS = [
  { value: "Veo 3.1 - Fast", label: "Veo 3.1 - Fast" },
  { value: "Veo 3.1 - Quality", label: "Veo 3.1 - Quality" },
  { value: "Veo 2 - Fast", label: "Veo 2 - Fast" },
  { value: "Veo 2 - Quality", label: "Veo 2 - Quality" },
];
const FALLBACK_IMAGE_MODELS = [
  { value: "NARWHAL", label: "Nano Banana 2" },
  { value: "IMAGEN_3", label: "Imagen 3" },
];

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
  promptAiResults: {
    video: null,
    image: null,
  },
  drafts: {
    video: { prompt: "", model: "Veo 3.1 - Fast", aspect: "landscape", count: 1 },
    image: { prompt: "", model: "NARWHAL", aspect: "square", count: 2 },
    edit: { prompt: "", model: "", aspect: "landscape", count: 1 },
  },
  promptAiDrafts: {
    video: { brief: "", style: "", mustInclude: "", avoid: "", audience: "" },
    image: { brief: "", style: "", mustInclude: "", avoid: "", audience: "" },
  },
};

const elements = {
  projectStatus: document.querySelector("#projectStatus"),
  authStatus: document.querySelector("#authStatus"),
  topbarHint: document.querySelector("#topbarHint"),
  logoutButton: document.querySelector("#logoutButton"),
  setupToggle: document.querySelector("#setupToggle"),
  setupPanel: document.querySelector("#setupPanel"),
  configForm: document.querySelector("#configForm"),
  projectId: document.querySelector("#projectId"),
  projectName: document.querySelector("#projectName"),
  generationTimeout: document.querySelector("#generationTimeout"),
  loginButton: document.querySelector("#loginButton"),
  messageBar: document.querySelector("#messageBar"),
  composerTitle: document.querySelector("#composerTitle"),
  composerHint: document.querySelector("#composerHint"),
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
  promptLabel: document.querySelector("#promptLabel"),
  promptInput: document.querySelector("#promptInput"),
  composerSummaryMode: document.querySelector("#composerSummaryMode"),
  composerSummaryText: document.querySelector("#composerSummaryText"),
  editActionStrip: document.querySelector("#editActionStrip"),
  editActionButtons: Array.from(document.querySelectorAll("[data-edit-action]")),
  editSourceWrap: document.querySelector("#editSourceWrap"),
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
  imageReferenceList: document.querySelector("#imageReferenceList"),
  imageReferenceStatus: document.querySelector("#imageReferenceStatus"),
  generationOptionsWrap: document.querySelector("#generationOptionsWrap"),
  modelSelect: document.querySelector("#modelSelect"),
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
  modeButtons: Array.from(document.querySelectorAll(".mode-button")),
};

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
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
    if (raw === "NARWHAL") {
      return "Nano Banana 2";
    }
    if (raw === "IMAGEN_3") {
      return "Imagen 3";
    }
  }
  return raw;
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

function isReady() {
  return Boolean(state.config?.project_id) && Boolean(state.auth?.authenticated);
}

function renderTopbar() {
  const projectId = state.config?.project_id || "";
  const projectName = String(state.config?.project_name || "").trim();
  const activeJobs = (state.jobs || []).filter((job) => ACTIVE_STATUSES.has(job.status)).length;
  elements.projectStatus.textContent = projectId ? projectName || `Project ${truncate(projectId, 18)}` : "Chưa có project";
  elements.projectStatus.dataset.state = projectId ? "ready" : "pending";
  elements.authStatus.textContent = state.auth?.authenticated ? "Đã đăng nhập" : "Chưa đăng nhập";
  elements.authStatus.dataset.state = state.auth?.authenticated ? "ready" : "pending";
  elements.logoutButton.hidden = !state.auth?.authenticated;
  elements.logoutButton.disabled = activeJobs > 0;
  elements.logoutButton.title = activeJobs > 0 ? "Hãy chờ các tác vụ đang chạy hoàn tất rồi đăng xuất." : "";
  elements.setupToggle.textContent = state.setupOpen ? "Ẩn thiết lập" : "Thiết lập";
  elements.setupPanel.hidden = !state.setupOpen;

  if (!projectId) {
    elements.topbarHint.textContent = "Lưu project một lần rồi chỉ việc nhập prompt.";
  } else if (!state.auth?.authenticated) {
    elements.topbarHint.textContent = "Project đã có. Chỉ còn đăng nhập Google Flow là chạy được.";
  } else if (activeJobs) {
    elements.topbarHint.textContent = `Đang có ${activeJobs} lượt chạy. Tab Google Flow vẫn được giữ mở để bạn theo dõi trực tiếp.`;
  } else {
    elements.topbarHint.textContent = "Mọi thứ đã sẵn sàng. Nhập prompt rồi bấm chạy, tab Google Flow sẽ được giữ mở.";
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

function renderComposer() {
  const config = currentOperationConfig();
  elements.composerTitle.textContent = config.title;
  elements.composerHint.textContent = config.hint;
  elements.promptLabel.textContent = config.promptLabel;
  elements.promptInput.placeholder = config.placeholder || "";
  elements.submitButton.textContent = config.submitLabel;
  elements.startImageWrap.hidden = !(state.mode === "video" && config.showStartImage);
  elements.imageReferenceWrap.hidden = state.mode !== "image";
  elements.readyHint.textContent = isReady()
    ? `${config.readyText} Tab Google Flow sẽ được giữ mở sau khi gửi.`
    : "Lưu project và đăng nhập một lần rồi bấm chạy.";
  elements.promptLabel.parentElement.hidden = Boolean(state.mode === "edit" && !config.showPrompt);

  for (const button of elements.modeButtons) {
    button.classList.toggle("active", button.dataset.mode === state.mode);
  }

  applyDraftToForm();
  renderEditControls();
  renderComposerSummary();
  renderUploadStatus();
  renderImageReferenceStatus();
  if (currentModeConfig().showPromptAi) {
    renderPromptAssistant();
  }
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
    return;
  }

  if (state.mode === "image") {
    const modelLabel = modelLabelForMode("image", currentDraft().model);
    if (state.imageReferenceItems.length) {
      elements.composerSummaryMode.textContent = "Chỉnh ảnh từ ảnh tham chiếu";
      elements.composerSummaryText.textContent = `Đang dùng ${fileKindLabel(state.imageReferenceItems.length)} để ghép hoặc chỉnh theo prompt vừa nhập bằng model ${modelLabel}.`;
      return;
    }
    elements.composerSummaryMode.textContent = "Ảnh từ prompt";
    elements.composerSummaryText.textContent = `App sẽ tạo ảnh trực tiếp từ mô tả vừa nhập bằng model ${modelLabel}.`;
    return;
  }

  const videoModelLabel = modelLabelForMode("video", currentDraft().model);
  if (state.startImagePath) {
    elements.composerSummaryMode.textContent = "Video từ ảnh";
    elements.composerSummaryText.textContent = `Đang dùng ${state.startImageName || "ảnh đầu vào"} làm khung đầu tiên bằng model ${videoModelLabel}.`;
    return;
  }

  elements.composerSummaryMode.textContent = "Video từ prompt";
  elements.composerSummaryText.textContent = `Không có ảnh đầu vào. App sẽ tạo video trực tiếp từ mô tả vừa nhập bằng model ${videoModelLabel}.`;
}

function renderUploadStatus() {
  if (state.mode !== "video") {
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
  elements.startImageStatus.textContent = "Không có ảnh đầu vào. Nếu bỏ trống, app sẽ tạo video từ prompt.";
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

  const sources = availableVideoSources();
  const options = ['<option value="">Chọn một video</option>']
    .concat(
      sources.map(
        (item) => `<option value="${escapeHtml(item.key)}">${escapeHtml(item.label)}</option>`
      )
    )
    .join("");
  elements.editSourceSelect.innerHTML = options;
  if (!sources.some((item) => item.key === state.selectedEditSourceKey)) {
    state.selectedEditSourceKey = "";
  }

  applyEditInputsToForm();

  const config = currentEditConfig();
  const hasOptions = config.showMotion || config.showPosition || config.showResolution;
  elements.editOptionsWrap.hidden = !hasOptions;
  elements.motionField.hidden = !config.showMotion;
  elements.positionField.hidden = !config.showPosition;
  elements.resolutionField.hidden = !config.showResolution;
}

function renderImageReferenceStatus() {
  if (state.mode !== "image") {
    return;
  }

  const items = state.imageReferenceItems || [];
  if (state.uploading && !items.length) {
    elements.imageReferenceList.hidden = true;
    elements.imageReferenceList.innerHTML = "";
    elements.imageReferenceStatus.textContent = "Đang tải ảnh tham chiếu...";
    return;
  }
  if (!items.length) {
    elements.imageReferenceList.hidden = true;
    elements.imageReferenceList.innerHTML = "";
    elements.imageReferenceStatus.textContent = "Chưa có ảnh tham chiếu. Nếu thêm ảnh ở đây, app sẽ dùng chúng để ghép/chỉnh ảnh.";
    return;
  }

  elements.imageReferenceList.hidden = false;
  elements.imageReferenceList.innerHTML = items
    .map((item, index) => {
      const source = item.publicUrl || uploadPublicUrlFromPath(item.path);
      return `
        <article class="upload-preview reference-card">
          <img class="upload-preview-image" src="${escapeHtml(source)}" alt="${escapeHtml(item.name || "Ảnh tham chiếu")}" />
          <div class="upload-preview-copy">
            <strong>${escapeHtml(item.name || "Ảnh tham chiếu")}</strong>
            <p>${escapeHtml(index === 0 ? "Ảnh chính hoặc ảnh người mẫu." : "Ảnh phụ để ghép logo, họa tiết hoặc chi tiết cần chèn.")}</p>
          </div>
          <button type="button" class="ghost-button card-button" data-action="remove-reference-image" data-index="${index}">Bỏ ảnh</button>
        </article>
      `;
    })
    .join("");
  elements.imageReferenceStatus.textContent = `Đã gắn ${fileKindLabel(items.length)}. App sẽ dùng chúng làm ảnh tham chiếu khi tạo ảnh.`;
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
    "AI sẽ viết prompt chi tiết hơn để dùng ngay.";
  elements.promptAiHint.textContent = ready
    ? (assistant.summary || `Đã nạp ${skillCount} skill để gợi ý prompt.`)
    : "Kho skill viết prompt đang được chuẩn bị. Bạn vẫn có thể thử bấm viết prompt.";

  applyPromptAiDraftToForm();
  renderPromptAiResult();
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
    state.imageReferenceItems = [];
  } else if (resolvedMode === "image") {
    state.startImagePath = "";
    state.startImageName = "";
    state.startImagePublicUrl = "";
    state.imageReferenceItems = (payload.reference_image_paths || [])
      .map((path) => String(path || "").trim())
      .filter(Boolean)
      .map((path) => ({
        path,
        name: basename(path),
        publicUrl: uploadPublicUrlFromPath(path),
      }));
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
  const sourceLabel = sourceImagePath
    ? `Ảnh gốc: ${basename(sourceImagePath)}`
    : referenceImageCount
    ? `Ảnh tham chiếu: ${referenceImageCount}`
    : "";
  const canRetry =
    latestJob.status === "failed" ||
    latestJob.status === "interrupted" ||
    (latestJob.type === "video" && latestJob.status === "completed" && !(latestJob.artifacts || []).length);
  const canReuse = Boolean(String(latestJob.input?.prompt || "").trim());

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
      ${sourceLabel ? `<p class="run-source">${escapeHtml(sourceLabel)}</p>` : ""}
      <p class="run-prompt">${escapeHtml(prompt)}</p>
      <p class="run-note">${escapeHtml(note)}</p>
      <p class="run-note flow-open-note">Tab Google Flow vẫn được giữ mở để bạn xem trực tiếp trên đó.</p>
      <div class="card-actions">
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
  renderComposer();
  renderLatestStatus();
}

async function loadState({ silent = false } = {}) {
  try {
    const payload = await api("/api/state");
    state.config = payload.config || {};
    state.auth = payload.auth || { authenticated: false };
    state.jobs = (payload.jobs || []).filter((job) => job.type !== "login");
    state.outputShelf = payload.output_shelf || { items: [] };
    state.promptAssistant = payload.prompt_assistant || null;
    state.skillLibraryCount = Array.isArray(payload.skills) ? payload.skills.length : 0;

    if (state.setupOpen == null) {
      state.setupOpen = !isReady();
    }

    renderAll();
    if (isReady() && !state.modelOptionsLoaded) {
      void loadModelOptions();
    }
    if (!silent) {
      showMessage("");
    }
  } catch (error) {
    showMessage(error.message, "error");
  }
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
    showMessage("Đang mở cửa sổ đăng nhập Google Flow. Em sẽ để nguyên tab này để dùng tiếp.", "success");
    state.setupOpen = true;
    renderTopbar();
  } catch (error) {
    showMessage(error.message, "error");
  }
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
    state.startImagePath = "";
    state.startImageName = "";
    renderUploadStatus();
    return;
  }

  const data = new FormData();
  data.append("file", file);
  state.uploading = true;
  renderUploadStatus();
  try {
    const payload = await api("/api/uploads", { method: "POST", body: data });
    state.startImagePath = payload.saved_path || "";
    state.startImageName = payload.file_name || file.name;
    state.startImagePublicUrl = payload.public_url || uploadPublicUrlFromPath(payload.saved_path || file.name);
    showMessage("Đã tải ảnh đầu vào.", "success");
  } catch (error) {
    state.startImagePath = "";
    state.startImageName = "";
    state.startImagePublicUrl = "";
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
    showMessage("Tối đa 4 ảnh tham chiếu cho một lượt ghép/chỉnh ảnh.", "error");
    return;
  }

  state.uploading = true;
  renderImageReferenceStatus();
  try {
    for (const file of files) {
      const data = new FormData();
      data.append("file", file);
      const payload = await api("/api/uploads", { method: "POST", body: data });
      state.imageReferenceItems.push({
        path: payload.saved_path || "",
        name: payload.file_name || file.name,
        publicUrl: payload.public_url || uploadPublicUrlFromPath(payload.saved_path || file.name),
      });
    }
    showMessage("Đã tải ảnh tham chiếu để ghép/chỉnh ảnh.", "success");
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
  state.startImagePath = "";
  state.startImageName = "";
  state.startImagePublicUrl = "";
  elements.startImageFile.value = "";
  renderComposerSummary();
  renderUploadStatus();
  showMessage("Đã bỏ ảnh đầu vào.", "success");
}

function removeReferenceImage(indexValue) {
  const index = Number(indexValue);
  if (!Number.isInteger(index) || index < 0 || index >= state.imageReferenceItems.length) {
    return;
  }
  state.imageReferenceItems.splice(index, 1);
  renderComposerSummary();
  renderImageReferenceStatus();
  showMessage("Đã bỏ một ảnh tham chiếu.", "success");
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
    if (state.startImagePath) {
      payload.start_image_path = state.startImagePath;
    }
  }

  if (state.mode === "image") {
    payload.type = "image";
    if (state.imageReferenceItems.length) {
      payload.reference_image_paths = state.imageReferenceItems.map((item) => item.path).filter(Boolean);
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
      state.mode === "video" && state.startImagePath
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

async function retryJob(jobId) {
  const job = (state.jobs || []).find((item) => item.id === jobId);
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

function reuseJob(jobId) {
  const job = (state.jobs || []).find((item) => item.id === jobId);
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
    if (document.hidden) {
      return;
    }
    loadState({ silent: true });
  }, 5000);
}

elements.modeButtons.forEach((button) => {
  button.addEventListener("click", () => changeMode(button.dataset.mode));
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
elements.logoutButton.addEventListener("click", logoutFlow);
elements.startImageFile.addEventListener("change", uploadStartImage);
elements.imageReferenceFiles.addEventListener("change", uploadImageReferences);
elements.clearStartImageButton.addEventListener("click", clearStartImage);
elements.editSourceSelect.addEventListener("change", () => {
  syncEditInputsFromForm();
  renderComposerSummary();
});
elements.manualMediaId.addEventListener("input", () => {
  syncEditInputsFromForm();
  renderComposerSummary();
});
elements.manualWorkflowId.addEventListener("input", () => {
  syncEditInputsFromForm();
  renderComposerSummary();
});
elements.motionSelect.addEventListener("change", syncEditInputsFromForm);
elements.positionSelect.addEventListener("change", syncEditInputsFromForm);
elements.resolutionSelect.addEventListener("change", syncEditInputsFromForm);
elements.composerForm.addEventListener("submit", submitCreate);
elements.refreshButton.addEventListener("click", () => loadState());
elements.promptAiSubmit.addEventListener("click", submitPromptAi);
elements.usePromptAiResultButton.addEventListener("click", usePromptAiResult);
elements.promptAiBrief.addEventListener("input", syncPromptAiDraftFromForm);
elements.promptAiStyle.addEventListener("input", syncPromptAiDraftFromForm);
elements.promptAiMustInclude.addEventListener("input", syncPromptAiDraftFromForm);
elements.promptAiAvoid.addEventListener("input", syncPromptAiDraftFromForm);
elements.promptAiAudience.addEventListener("input", syncPromptAiDraftFromForm);
elements.promptInput.addEventListener("input", syncDraftFromForm);
elements.modelSelect.addEventListener("change", () => {
  syncDraftFromForm();
  renderComposerSummary();
});
elements.aspectSelect.addEventListener("change", syncDraftFromForm);
elements.countInput.addEventListener("input", syncDraftFromForm);
elements.latestStatusCard.addEventListener("click", (event) => {
  const actionTarget = event.target.closest("[data-action]");
  if (!actionTarget) {
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
elements.imageReferenceList.addEventListener("click", (event) => {
  const actionTarget = event.target.closest("[data-action='remove-reference-image']");
  if (!actionTarget) {
    return;
  }
  removeReferenceImage(actionTarget.dataset.index);
});

loadState();
setupPolling();
