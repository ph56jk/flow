const ACTIVE_STATUSES = new Set(["queued", "running", "polling"]);

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
  },
  image: {
    title: "Bạn muốn tạo ảnh gì?",
    hint: "Nhập mô tả ngắn gọn rồi bấm chạy.",
    promptLabel: "Mô tả ảnh",
    placeholder: "Ví dụ: Ảnh sản phẩm chuối tối giản trên nền đen, ánh sáng studio mềm",
    promptAiLabel: "Bạn muốn ảnh như thế nào?",
    promptAiPlaceholder: "Ví dụ: ảnh poster đàn piano sang trọng trên nền đen, ánh sáng studio mềm",
    submitLabel: "Tạo ảnh",
    resultsTitle: "Kết quả ảnh gần đây",
    runsTitle: "Lượt chạy ảnh gần đây",
    readyText: "Sẵn sàng tạo ảnh.",
    emptyResult: "Chưa có ảnh nào gần đây.",
    emptyRun: "Chưa có lượt chạy ảnh nào.",
    defaultAspect: "square",
    defaultCount: 2,
    showStartImage: false,
  },
};

const state = {
  mode: "video",
  config: null,
  auth: { authenticated: false },
  jobs: [],
  outputShelf: { items: [] },
  skillLibraryCount: 0,
  startImagePath: "",
  startImageName: "",
  startImagePublicUrl: "",
  uploading: false,
  setupOpen: null,
  promptAssistant: null,
  promptAiResults: {
    video: null,
    image: null,
  },
  drafts: {
    video: { prompt: "", aspect: "landscape", count: 1 },
    image: { prompt: "", aspect: "square", count: 2 },
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
  promptLabel: document.querySelector("#promptLabel"),
  promptInput: document.querySelector("#promptInput"),
  composerSummaryMode: document.querySelector("#composerSummaryMode"),
  composerSummaryText: document.querySelector("#composerSummaryText"),
  startImageWrap: document.querySelector("#startImageWrap"),
  startImageFile: document.querySelector("#startImageFile"),
  startImageStatus: document.querySelector("#startImageStatus"),
  startImagePreview: document.querySelector("#startImagePreview"),
  startImagePreviewImage: document.querySelector("#startImagePreviewImage"),
  startImagePreviewName: document.querySelector("#startImagePreviewName"),
  startImagePreviewHint: document.querySelector("#startImagePreviewHint"),
  clearStartImageButton: document.querySelector("#clearStartImageButton"),
  aspectSelect: document.querySelector("#aspectSelect"),
  countInput: document.querySelector("#countInput"),
  readyHint: document.querySelector("#readyHint"),
  submitButton: document.querySelector("#submitButton"),
  composerForm: document.querySelector("#composerForm"),
  refreshButton: document.querySelector("#refreshButton"),
  resultsTitle: document.querySelector("#resultsTitle"),
  runsTitle: document.querySelector("#runsTitle"),
  outputShelfList: document.querySelector("#outputShelfList"),
  jobList: document.querySelector("#jobList"),
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

function currentDraft() {
  return state.drafts[state.mode];
}

function currentPromptAiDraft() {
  return state.promptAiDrafts[state.mode];
}

function currentPromptAiResult() {
  return state.promptAiResults[state.mode];
}

function syncDraftFromForm() {
  const draft = currentDraft();
  draft.prompt = elements.promptInput.value;
  draft.aspect = elements.aspectSelect.value;
  draft.count = Math.max(1, Math.min(4, Number(elements.countInput.value || draft.count || 1)));
}

function syncPromptAiDraftFromForm() {
  const draft = currentPromptAiDraft();
  draft.brief = elements.promptAiBrief.value;
  draft.style = elements.promptAiStyle.value;
  draft.mustInclude = elements.promptAiMustInclude.value;
  draft.avoid = elements.promptAiAvoid.value;
  draft.audience = elements.promptAiAudience.value;
}

function applyDraftToForm() {
  const draft = currentDraft();
  const config = currentModeConfig();
  elements.promptInput.value = draft.prompt || "";
  elements.aspectSelect.value = draft.aspect || config.defaultAspect;
  elements.countInput.value = String(draft.count || config.defaultCount);
}

function applyPromptAiDraftToForm() {
  const draft = currentPromptAiDraft();
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
  elements.setupToggle.textContent = state.setupOpen ? "Ẩn thiết lập" : "Thiết lập";
  elements.setupPanel.hidden = !state.setupOpen;

  if (!projectId) {
    elements.topbarHint.textContent = "Lưu project một lần rồi chỉ việc nhập prompt.";
  } else if (!state.auth?.authenticated) {
    elements.topbarHint.textContent = "Project đã có. Chỉ còn đăng nhập Google Flow là chạy được.";
  } else if (activeJobs) {
    elements.topbarHint.textContent = `Đang có ${activeJobs} lượt chạy. Bạn vẫn có thể gửi thêm yêu cầu mới.`;
  } else {
    elements.topbarHint.textContent = "Mọi thứ đã sẵn sàng. Chỉ cần nhập prompt rồi bấm chạy.";
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
  const config = currentModeConfig();
  elements.composerTitle.textContent = config.title;
  elements.composerHint.textContent = config.hint;
  elements.promptLabel.textContent = config.promptLabel;
  elements.promptInput.placeholder = config.placeholder;
  elements.submitButton.textContent = config.submitLabel;
  elements.resultsTitle.textContent = config.resultsTitle;
  elements.runsTitle.textContent = config.runsTitle;
  elements.startImageWrap.hidden = !config.showStartImage;
  elements.readyHint.textContent = isReady()
    ? config.readyText
    : "Lưu project và đăng nhập một lần rồi bấm chạy.";

  for (const button of elements.modeButtons) {
    button.classList.toggle("active", button.dataset.mode === state.mode);
  }

  applyDraftToForm();
  renderComposerSummary();
  renderUploadStatus();
  renderPromptAssistant();
}

function renderComposerSummary() {
  if (state.mode === "image") {
    elements.composerSummaryMode.textContent = "Ảnh từ prompt";
    elements.composerSummaryText.textContent = "App sẽ tạo ảnh trực tiếp từ mô tả vừa nhập.";
    return;
  }

  if (state.startImagePath) {
    elements.composerSummaryMode.textContent = "Video từ ảnh";
    elements.composerSummaryText.textContent = `Đang dùng ${state.startImageName || "ảnh đầu vào"} làm khung đầu tiên cho video này.`;
    return;
  }

  elements.composerSummaryMode.textContent = "Video từ prompt";
  elements.composerSummaryText.textContent = "Không có ảnh đầu vào. App sẽ tạo video trực tiếp từ mô tả vừa nhập.";
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

function outputItemsForMode() {
  const items = state.outputShelf?.items || [];
  return items.filter((item) => item.job_type === state.mode);
}

function fillComposerFromSource(mode, payload = {}) {
  if (!MODE_CONFIG[mode]) {
    return;
  }
  syncDraftFromForm();
  syncPromptAiDraftFromForm();
  state.mode = mode;
  state.drafts[mode] = {
    prompt: String(payload.prompt || "").trim(),
    aspect: String(payload.aspect || MODE_CONFIG[mode].defaultAspect).trim() || MODE_CONFIG[mode].defaultAspect,
    count: Math.max(1, Math.min(4, Number(payload.count || MODE_CONFIG[mode].defaultCount))),
  };
  state.promptAiDrafts[mode] = {
    ...state.promptAiDrafts[mode],
    brief: String(payload.prompt || "").trim(),
  };

  if (mode === "video") {
    state.startImagePath = String(payload.start_image_path || "").trim();
    state.startImageName = basename(state.startImagePath);
    state.startImagePublicUrl = uploadPublicUrlFromPath(state.startImagePath);
  } else {
    state.startImagePath = "";
    state.startImageName = "";
    state.startImagePublicUrl = "";
  }

  renderAll();
  window.scrollTo({ top: 0, behavior: "smooth" });
  elements.promptInput.focus();
}

function previewMarkup(item) {
  const source = item.local_file_url || item.preview_url || item.source_url || "";
  if (!source) {
    return '<div class="result-placeholder">Chưa có preview</div>';
  }

  if ((item.mime_type || "").startsWith("video/") || item.job_type === "video") {
    return `<video class="result-media" src="${escapeHtml(source)}" controls playsinline preload="metadata"></video>`;
  }
  return `<img class="result-media" src="${escapeHtml(source)}" alt="${escapeHtml(item.title || item.job_title || "Kết quả")}" />`;
}

function renderOutputs() {
  const config = currentModeConfig();
  const items = outputItemsForMode().slice(0, 8);
  if (!items.length) {
    elements.outputShelfList.className = "results-grid empty-state";
    elements.outputShelfList.textContent = config.emptyResult;
    return;
  }

  elements.outputShelfList.className = "results-grid";
  elements.outputShelfList.innerHTML = items
    .map((item, index) => {
      const source = item.local_file_url || item.preview_url || item.source_url || "";
      const actionText = item.local_file_url ? "Mở bản tải về" : "Mở kết quả";
      const sourceJob = (state.jobs || []).find((job) => job.id === item.job_id);
      const sourceImagePath = String(sourceJob?.input?.start_image_path || "").trim();
      const sourceBadge = sourceImagePath ? `Từ ảnh ${basename(sourceImagePath)}` : item.job_type_label || "";
      return `
        <article class="result-card${index === 0 ? " featured" : ""}${sourceImagePath ? " from-image" : ""}">
          ${previewMarkup(item)}
          <div class="result-copy">
            <div class="result-meta">
              <span class="mini-pill">${escapeHtml(sourceBadge)}</span>
              <span>${escapeHtml(formatTime(item.created_at))}</span>
            </div>
            <strong>${escapeHtml(item.title || item.job_title || "Kết quả")}</strong>
            <p>${escapeHtml(truncate(item.prompt || "", 120) || "Không có mô tả được lưu.")}</p>
            <div class="card-actions">
              ${
                source
                  ? `<a class="inline-link action-link" href="${escapeHtml(source)}" target="_blank" rel="noreferrer">${actionText}</a>`
                  : ""
              }
              <button
                type="button"
                class="ghost-button card-button"
                data-action="reuse-output"
                data-output-index="${index}"
              >
                Dùng lại prompt
              </button>
            </div>
          </div>
        </article>
      `;
    })
    .join("");
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

function renderMilestones(job) {
  const source = job.progress_snapshot?.milestones || [];
  const selected = source.filter((item) =>
    ["connecting", "sending_request", "awaiting_response", "saving_artifacts", "completed"].includes(item.key)
  );
  if (!selected.length) {
    return "";
  }

  const shortLabels = {
    connecting: "Kết nối",
    sending_request: "Gửi",
    awaiting_response: "Chờ",
    saving_artifacts: "Lưu",
    completed: "Xong",
  };

  return `
    <div class="milestone-strip">
      ${selected
        .map((item) => {
          const status = item.status || "pending";
          return `<span class="milestone-chip" data-status="${escapeHtml(status)}">${escapeHtml(shortLabels[item.key] || item.label || item.key)}</span>`;
        })
        .join("")}
    </div>
  `;
}

function renderJobs() {
  const config = currentModeConfig();
  const jobs = (state.jobs || []).filter((job) => job.type === state.mode).slice(0, 6);
  if (!jobs.length) {
    elements.jobList.className = "run-list empty-state";
    elements.jobList.textContent = config.emptyRun;
    return;
  }

  elements.jobList.className = "run-list";
  elements.jobList.innerHTML = jobs
    .map((job) => {
      const prompt = truncate(job.input?.prompt || "", 120) || "Không có mô tả.";
      const note = describeJob(job);
      const duration = jobDuration(job);
      const sourceImagePath = String(job.input?.start_image_path || "").trim();
      const sourceLabel = sourceImagePath ? `Ảnh gốc: ${basename(sourceImagePath)}` : "";
      const canRetry =
        job.status === "failed" ||
        job.status === "interrupted" ||
        (job.type === "video" && job.status === "completed" && !(job.artifacts || []).length);
      const canReuse = Boolean(String(job.input?.prompt || "").trim());
      return `
        <article class="run-card">
          <div class="run-head">
            <div>
              <strong>${escapeHtml(job.title || config.submitLabel)}</strong>
              <small>${escapeHtml(formatTime(job.created_at))}${duration ? ` · ${escapeHtml(duration)}` : ""}</small>
            </div>
            <span class="status-chip" data-status="${escapeHtml(jobProgressTone(job))}">${escapeHtml(jobProgressLabel(job))}</span>
          </div>
          ${renderMilestones(job)}
          ${sourceLabel ? `<p class="run-source">${escapeHtml(sourceLabel)}</p>` : ""}
          <p class="run-prompt">${escapeHtml(prompt)}</p>
          <p class="run-note">${escapeHtml(note)}</p>
          <div class="card-actions">
            ${
              canReuse
                ? `<button type="button" class="ghost-button card-button" data-action="reuse-job" data-job-id="${escapeHtml(job.id)}">Dùng lại prompt</button>`
                : ""
            }
            ${
              canRetry
                ? `<button type="button" class="ghost-button card-button" data-action="retry-job" data-job-id="${escapeHtml(job.id)}">Chạy lại</button>`
                : ""
            }
          </div>
        </article>
      `;
    })
    .join("");
}

function renderAll() {
  renderTopbar();
  renderComposer();
  renderOutputs();
  renderJobs();
}

async function loadState({ silent = false } = {}) {
  try {
    const payload = await api("/api/state");
    state.config = payload.config || {};
    state.auth = payload.auth || { authenticated: false };
    state.jobs = (payload.jobs || []).filter((job) => job.type === "video" || job.type === "image");
    state.outputShelf = payload.output_shelf || { items: [] };
    state.promptAssistant = payload.prompt_assistant || null;
    state.skillLibraryCount = Array.isArray(payload.skills) ? payload.skills.length : 0;

    if (state.setupOpen == null) {
      state.setupOpen = !isReady();
    }

    renderAll();
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
    showMessage("Đang mở cửa sổ đăng nhập Google Flow.", "success");
    state.setupOpen = true;
    renderTopbar();
  } catch (error) {
    showMessage(error.message, "error");
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

function clearStartImage() {
  state.startImagePath = "";
  state.startImageName = "";
  state.startImagePublicUrl = "";
  elements.startImageFile.value = "";
  renderComposerSummary();
  renderUploadStatus();
  showMessage("Đã bỏ ảnh đầu vào.", "success");
}

async function submitCreate(event) {
  event.preventDefault();
  syncDraftFromForm();

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
  if (!draft.prompt.trim()) {
    showMessage("Hãy nhập mô tả trước khi chạy.", "error");
    elements.promptInput.focus();
    return;
  }

  const payload = {
    type: state.mode,
    prompt: draft.prompt.trim(),
    aspect: draft.aspect || currentModeConfig().defaultAspect,
    count: Math.max(1, Math.min(4, Number(draft.count || currentModeConfig().defaultCount))),
    timeout_s: Math.max(30, Number(elements.generationTimeout.value || state.config?.generation_timeout_s || 300)),
  };

  if (state.mode === "video" && state.startImagePath) {
    payload.start_image_path = state.startImagePath;
  }

  elements.submitButton.disabled = true;
  try {
    await api("/api/jobs", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showMessage(
      state.mode === "video" && state.startImagePath
        ? "Đã gửi yêu cầu tạo video từ ảnh."
        : `Đã gửi yêu cầu ${state.mode === "video" ? "tạo video" : "tạo ảnh"}.`,
      "success"
    );
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
    aspect: String(input.aspect || MODE_CONFIG[job.type]?.defaultAspect || "landscape").trim(),
    count: Math.max(1, Math.min(4, Number(input.count || MODE_CONFIG[job.type]?.defaultCount || 1))),
    start_image_path: String(input.start_image_path || "").trim(),
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
    showMessage("Đã gửi lại lượt chạy với đúng cấu hình cũ.", "success");
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

function reuseOutput(indexValue) {
  const index = Number(indexValue);
  const item = outputItemsForMode().slice(0, 8)[index];
  if (!item) {
    showMessage("Không tìm thấy kết quả để dùng lại.", "error");
    return;
  }

  const sourceJob = (state.jobs || []).find((job) => job.id === item.job_id);
  fillComposerFromSource(item.job_type, {
    prompt: item.prompt || "",
    start_image_path: String(sourceJob?.input?.start_image_path || "").trim(),
  });
  showMessage("Đã chép prompt từ kết quả lên form.", "success");
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

elements.setupToggle.addEventListener("click", () => {
  state.setupOpen = !state.setupOpen;
  renderTopbar();
});

elements.configForm.addEventListener("submit", saveConfig);
elements.loginButton.addEventListener("click", loginFlow);
elements.startImageFile.addEventListener("change", uploadStartImage);
elements.clearStartImageButton.addEventListener("click", clearStartImage);
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
elements.aspectSelect.addEventListener("change", syncDraftFromForm);
elements.countInput.addEventListener("input", syncDraftFromForm);
elements.outputShelfList.addEventListener("click", (event) => {
  const actionTarget = event.target.closest("[data-action]");
  if (!actionTarget) {
    return;
  }
  if (actionTarget.dataset.action === "reuse-output") {
    reuseOutput(actionTarget.dataset.outputIndex);
  }
});
elements.jobList.addEventListener("click", (event) => {
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

loadState();
setupPolling();
