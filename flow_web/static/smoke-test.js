const statusEl = document.getElementById("status");
const outputEl = document.getElementById("output");
const params = new URL(location.href).searchParams;

const report = {
  ok: false,
  startedAt: new Date().toISOString(),
  token: params.get("token") || "",
  origin: location.origin,
  steps: [],
};

let bridgeNonce = "";
let externalExtensionId = "";
let externalExtensionVersion = "";
const MIN_ETSY_WORKER_VERSION = "0.8.98";
const ETSY_QUEUE_SETTLE_TIMEOUT_MS = 10 * 60 * 1000;

function versionAtLeast(actual, minimum) {
  const actualParts = String(actual || "")
    .split(".")
    .map((part) => Number.parseInt(part, 10) || 0);
  const minimumParts = String(minimum || "")
    .split(".")
    .map((part) => Number.parseInt(part, 10) || 0);
  const length = Math.max(actualParts.length, minimumParts.length);
  for (let index = 0; index < length; index += 1) {
    const a = actualParts[index] || 0;
    const b = minimumParts[index] || 0;
    if (a > b) return true;
    if (a < b) return false;
  }
  return true;
}

function externalExtensionIds() {
  const ids = [
    params.get("extensionId"),
    "jpamdibjfnnneopokijhcmopgamlncmp",
    "fchedljplejnjllckaafaggdnebngehe",
    "hjnjmjmjiijifklidikbhblblcnbkfae",
    "fignfifoniblkonapihmkfakmlgkbkcf",
    "iolippgjhhgbkliihdclkkjebjhodknc",
    "bpohddiakfkeglpdocffelfeidcajbjg",
    "dnlbkhbhnigplmcombehceongijpooce",
    "efmoofpdlibfmmhkehcilcoigfneklon",
  ]
    .map((item) => String(item || "").trim())
    .filter(Boolean);
  return [...new Set(ids)];
}

function isEtsyOnlyMode() {
  const mode = String(params.get("mode") || "").trim().toLowerCase();
  return mode === "etsy" || mode === "etsy-only" || params.get("etsyOnly") === "1";
}

function isFullChainMode() {
  return params.get("fullChain") === "1" || params.get("mode") === "full-chain";
}

function splitParamList(value) {
  return String(value || "")
    .split(/[,\s]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function backendJson(path, { method = "GET", body } = {}) {
  const response = await fetch(path, {
    method,
    headers: {
      Accept: "application/json",
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await response.text();
  let payload = {};
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch (_error) {
      payload = { detail: text };
    }
  }
  if (!response.ok) {
    throw new Error(payload.detail || payload.error || `HTTP ${response.status}`);
  }
  return payload;
}

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error || new Error("read_failed"));
    reader.readAsDataURL(blob);
  });
}

async function backendImageToDataUrl(relativeOrAbsoluteUrl) {
  const source = String(relativeOrAbsoluteUrl || "");
  const url = source.startsWith("http") ? source : `${location.origin}${source}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Không tải được ảnh nguồn Trello: HTTP ${response.status}`);
  }
  return await blobToDataUrl(await response.blob());
}

function fullChainGraph(target = 4) {
  return {
    version: 1,
    selected_module_id: "flow",
    modules: [
      { id: "master-bot", type: "master_bot", title: "Master Bot", enabled: true },
      { id: "trello-source", type: "trello_source", title: "Trello Image Source", enabled: true },
      { id: "flow", type: "flow", title: "Google Flow", enabled: true, settings: { imageCount: target } },
      { id: "trello-archive", type: "trello", title: "Trello Archive", enabled: true },
      {
        id: "etsy-copy",
        type: "etsy_browser_copy",
        title: "Etsy Copy Listing",
        enabled: true,
        settings: { keepColorChart: true, deleteExistingImages: true },
      },
    ],
    edges: [
      { source: "master-bot", target: "trello-source", condition: "success" },
      { source: "trello-source", target: "flow", condition: "success" },
      { source: "flow", target: "trello-archive", condition: "success" },
      { source: "trello-archive", target: "etsy-copy", condition: "success" },
    ],
  };
}

function render() {
  const failed = report.steps.some((step) => step.ok === false);
  statusEl.textContent = report.ok ? "Xong: test pass." : failed ? "Co buoc loi." : "Dang chay...";
  statusEl.className = report.ok ? "ok" : failed ? "bad" : "";
  outputEl.textContent = JSON.stringify(report, null, 2);
}

async function postReport(event = "report") {
  report.lastEvent = event;
  report.lastPostAt = new Date().toISOString();
  await fetch("/api/extension/smoke-test-report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(report),
  });
}

// A reply of {ok:false} carrying one of these transport phrases means the MV3
// service worker was asleep when the bridge relayed the command — not a real
// command failure. Retrying the whole round-trip gives Chrome more chances to
// spin the worker back up (belt-and-suspenders alongside the content-bridge
// retry, and this layer deploys instantly since the page is served fresh).
const SW_WAKE_PATTERN =
  /Receiving end does not exist|Could not establish connection|message port closed|message channel closed|Extension context invalidated/i;

async function extensionCommand(message, timeout = 30000) {
  let last = null;
  for (let attempt = 0; attempt < 4; attempt += 1) {
    try {
      last = externalExtensionId
        ? await externalCommand(message, timeout)
        : await extensionCommandViaBridge(message, timeout);
    } catch (error) {
      // The external bridge rejects (throws) on a sleeping worker; the content
      // bridge resolves {ok:false}. Treat both transports the same: retry the
      // round-trip so Chrome gets another chance to spin the worker up.
      if (SW_WAKE_PATTERN.test(String(error?.message || error)) && attempt < 3) {
        await sleep(600 + attempt * 600);
        continue;
      }
      throw error;
    }
    if (last && last.ok === false && SW_WAKE_PATTERN.test(String(last.message || "")) && attempt < 3) {
      await sleep(600 + attempt * 600);
      continue;
    }
    return last;
  }
  return last;
}

function extensionCommandViaBridge(message, timeout = 30000) {
  return new Promise((resolve, reject) => {
    const requestId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
    const timer = setTimeout(() => {
      window.removeEventListener("message", onMessage);
      reject(new Error(`Extension timeout: ${message.type}`));
    }, timeout);
    function onMessage(event) {
      if (event.source !== window) return;
      const data = event.data;
      if (!data || data.source !== "flow-ext" || data.type !== "RESPONSE" || data.requestId !== requestId) return;
      clearTimeout(timer);
      window.removeEventListener("message", onMessage);
      externalExtensionVersion = String(data.result?.version || "");
      if (
        params.get("forceExternal") === "1" &&
        isEtsyOnlyMode() &&
        externalExtensionVersion &&
        !versionAtLeast(externalExtensionVersion, MIN_ETSY_WORKER_VERSION)
      ) {
        reject(
          new Error(
            `Content bridge version ${externalExtensionVersion} is older than required ${MIN_ETSY_WORKER_VERSION}; trying external bridge.`
          )
        );
        return;
      }
      resolve(data.result);
    }
    window.addEventListener("message", onMessage);
    window.postMessage({ source: "flow-web", requestId, nonce: bridgeNonce, message }, window.location.origin);
  });
}

function externalCommand(message, timeout = 30000) {
  return new Promise((resolve, reject) => {
    if (!globalThis.chrome?.runtime?.sendMessage || !externalExtensionId) {
      reject(new Error("External extension bridge is not available."));
      return;
    }
    const timer = setTimeout(() => reject(new Error(`External extension timeout: ${message.type}`)), timeout);
    chrome.runtime.sendMessage(externalExtensionId, message, (result) => {
      clearTimeout(timer);
      const lastError = chrome.runtime.lastError;
      if (lastError) {
        reject(new Error(lastError.message));
        return;
      }
      resolve(result);
    });
  });
}

async function pingExternalExtension(timeout = 10000) {
  if (!globalThis.chrome?.runtime?.sendMessage) {
    throw new Error("chrome.runtime external messaging is not available.");
  }
  const errors = [];
  for (const extensionId of externalExtensionIds()) {
    try {
      const result = await new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error(`External ping timeout: ${extensionId}`)), timeout);
        chrome.runtime.sendMessage(extensionId, { type: "PING_EXT" }, (response) => {
          clearTimeout(timer);
          const lastError = chrome.runtime.lastError;
          if (lastError) {
            reject(new Error(lastError.message));
            return;
          }
          resolve(response);
        });
      });
      if (result?.ok) {
        externalExtensionId = extensionId;
        externalExtensionVersion = String(result.version || "");
        bridgeNonce = "external";
        return { ...result, external: true, extensionId };
      }
    } catch (error) {
      errors.push(`${extensionId}: ${String(error?.message || error)}`);
    }
  }
  throw new Error(errors.join("; ") || "No external extension id responded.");
}

function pingExtension(timeout = 10000) {
  const pingContentBridge = () =>
    new Promise((resolve, reject) => {
      const requestId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
      const timer = setTimeout(() => {
        window.removeEventListener("message", onMessage);
        reject(new Error("Extension bridge timeout"));
      }, timeout);
      function onMessage(event) {
        if (event.source !== window) return;
        const data = event.data;
        if (!data || data.source !== "flow-ext" || data.type !== "RESPONSE" || data.requestId !== requestId) return;
        clearTimeout(timer);
        window.removeEventListener("message", onMessage);
        bridgeNonce = data.result?.nonce || "";
        resolve(data.result);
      }
      window.addEventListener("message", onMessage);
      window.postMessage({ source: "flow-web", type: "PING_EXT", requestId }, window.location.origin);
    });

  if (params.get("forceExternal") === "1") {
    return pingExternalExtension(timeout).catch((externalBridgeError) =>
      pingContentBridge().catch((contentBridgeError) => {
        throw new Error(
          `External bridge failed: ${String(externalBridgeError?.message || externalBridgeError)}; content bridge failed: ${String(
            contentBridgeError?.message || contentBridgeError
          )}`
        );
      })
    );
  }
  return pingContentBridge().catch(() => pingExternalExtension(timeout));
}

async function step(name, fn, timeout = 30000) {
  const item = { name, ok: false, startedAt: new Date().toISOString() };
  report.steps.push(item);
  render();
  await postReport("step_started").catch(() => {});
  let timer;
  try {
    const result = await Promise.race([
      Promise.resolve().then(fn),
      new Promise((_resolve, reject) => {
        timer = setTimeout(() => reject(new Error(`${name} timed out after ${timeout}ms`)), timeout);
      }),
    ]);
    item.ok = result?.ok !== false;
    item.result = result;
    return result;
  } catch (error) {
    item.ok = false;
    item.error = String(error?.message || error);
    return item;
  } finally {
    clearTimeout(timer);
    item.finishedAt = new Date().toISOString();
    render();
    await postReport("step_finished").catch(() => {});
  }
}

async function commandWithRetry(message, attempts = 4, delayMs = 5000, timeout = 30000) {
  let last = null;
  const retryableReasons = new Set(["content_unreachable", "flow_surface_entering"]);
  for (let index = 0; index < attempts; index += 1) {
    last = await extensionCommand(message, timeout);
    if (last?.ok !== false || !retryableReasons.has(last?.reason)) {
      return last;
    }
    if (index < attempts - 1) {
      await sleep(Number(last.retryAfterMs) || delayMs);
    }
  }
  return last;
}

async function pollEtsyQueueUntilSettled() {
  if (params.get("pageWorkerOnly") === "1") {
    return await runEtsyQueueViaPageWorkerLoop({ pageWorkerOnly: true });
  }
  const first = await extensionCommand({ type: "POLL_ETSY_COPY_QUEUE", fireAndForget: true }, 30000);
  if (
    first?.ok === false &&
    (first.reason === "queue_poll_failed" || /failed to fetch/i.test(String(first.message || "")))
  ) {
    return await runEtsyQueueViaPageWorkerLoop(first);
  }
  if (!first?.busy && !first?.accepted && !first?.taskId) {
    return first;
  }
  const started = Date.now();
  while (Date.now() - started < ETSY_QUEUE_SETTLE_TIMEOUT_MS) {
    const queue = await backendJson("/api/etsy/browser-copy/queue");
    const latest = queue.latest || null;
    if (latest?.status === "completed") {
      return { ok: true, waitedForBusyTask: true, task: latest };
    }
    if (latest?.status === "failed") {
      return {
        ok: false,
        waitedForBusyTask: true,
        task: latest,
        reason: "etsy_queue_task_failed",
        message: latest.error || latest.result?.message || "Etsy queue task failed.",
      };
    }
    if (!queue.in_progress && !queue.queued) {
      return { ok: true, waitedForBusyTask: true, empty: true, queue };
    }
    await sleep(5000);
  }
  throw new Error("Etsy queue vẫn busy quá lâu; task có thể bị kẹt trong extension.");
}

async function reportEtsyQueueTask(taskId, status, result, workerId) {
  return await backendJson("/api/extension/etsy-browser-copy/report", {
    method: "POST",
    body: {
      taskId,
      status,
      result: result || {},
      workerId: workerId || externalExtensionId || "flow-page-worker",
    },
  });
}

async function runEtsyQueueViaPageWorker(backgroundFailure = {}) {
  const workerId = externalExtensionId || "flow-page-worker";
  const next = await backendJson("/api/extension/etsy-browser-copy/next", {
    method: "POST",
    body: { workerId, workerVersion: externalExtensionVersion, trigger: "page_worker_fallback" },
  });
  if (next?.deferred) {
    return {
      ok: false,
      via: "page_worker_fallback",
      deferred: true,
      reason: next.reason || "etsy_queue_deferred",
      message: next.message || "Etsy queue task was deferred by backend.",
      workerVersion: externalExtensionVersion,
      next,
      backgroundFailure,
    };
  }
  const task = next?.task || null;
  if (!task) {
    return {
      ok: true,
      via: "page_worker_fallback",
      empty: true,
      backgroundFailure,
    };
  }
  const payload = {
    ...(task.payload || {}),
    queueTaskId: task.id,
    queueWorkerId: workerId,
    queueBackendUrl: location.origin,
    queueFireAndForget: true,
  };
  let result = null;
  try {
    result = await extensionCommand({ type: "RUN_ETSY_COPY_LISTING", payload }, ETSY_QUEUE_SETTLE_TIMEOUT_MS);
  } catch (error) {
    result = {
      ok: false,
      reason: "page_worker_extension_error",
      message: String(error?.message || error),
    };
  }
  const status = result?.ok ? "completed" : "failed";
  if (result?.accepted) {
    return {
      ok: true,
      accepted: true,
      via: "page_worker_fallback",
      taskId: task.id,
      status: "accepted",
      result,
      backgroundFailure,
    };
  }
  const reportResult = await reportEtsyQueueTask(task.id, status, result, workerId);
  const requeued = Boolean(result?.requeued || reportResult?.requeued || reportResult?.task?.status === "queued");
  return {
    ok: Boolean(result?.ok),
    via: "page_worker_fallback",
    taskId: task.id,
    status,
    result,
    report: reportResult,
    requeued,
    backgroundFailure,
  };
}

async function runEtsyQueueViaPageWorkerLoop(backgroundFailure = {}) {
  const started = Date.now();
  const runs = [];
  while (Date.now() - started < ETSY_QUEUE_SETTLE_TIMEOUT_MS) {
    const run = await runEtsyQueueViaPageWorker(backgroundFailure);
    runs.push(run);
    if (run.empty) {
      return { ok: true, via: "page_worker_fallback_loop", empty: true, runs };
    }
    const requeued = Boolean(run.requeued || run.report?.requeued || run.report?.task?.status === "queued");
    if (run.ok || run.accepted || requeued) {
      const queue = await backendJson("/api/etsy/browser-copy/queue");
      if (!queue.queued && !queue.in_progress) {
        const failed = (queue.tasks || []).filter((task) => task.status === "failed");
        if (failed.length) {
          return {
            ok: false,
            via: "page_worker_fallback_loop",
            reason: "etsy_queue_task_failed",
            message: failed[failed.length - 1].error || "Etsy queue task failed.",
            queue,
            runs,
          };
        }
        return { ok: true, via: "page_worker_fallback_loop", queue, runs };
      }
      await sleep(requeued ? 1500 : 5000);
      continue;
    }
    return { ...run, via: "page_worker_fallback_loop", runs };
  }
  throw new Error("Page-worker Etsy queue vẫn chạy quá lâu.");
}

async function main() {
  await postReport("script_loaded");
  const prompt =
    params.get("prompt") ||
    "Create one simple clean Etsy product mockup image for an automation smoke test. No text, no logo, no watermark.";
  const shouldSubmit = params.get("submit") !== "0";
  const etsyOnly = isEtsyOnlyMode();
  const fullChain = isFullChainMode();
  const skipEtsy = params.get("skipEtsy") === "1";
  const noOpenEtsy = params.get("noOpenEtsy") === "1";
  const fullChainTarget = Math.max(1, Math.min(4, Number.parseInt(params.get("target") || "4", 10) || 4));
  const lockedTrelloCardId = String(params.get("cardId") || params.get("trelloCardId") || "").trim();
  const lockedTrelloListId = String(params.get("listId") || params.get("trelloListId") || "").trim();
  const lockedTrelloAttachmentIds = splitParamList(params.get("attachmentIds") || params.get("trelloAttachmentIds"));
  const lockedTrelloProduct = String(params.get("product") || params.get("trelloProduct") || "").trim();
  let fullChainPlanItem = null;
  let fullChainSourceDataUrl = "";

  await step("bridge_ping", () => pingExtension(), 12000);
  if (!bridgeNonce) {
    report.ok = false;
    report.finishedAt = new Date().toISOString();
    await postReport("bridge_missing");
    render();
    return;
  }

  await step("set_backend", () => extensionCommand({ type: "SET_BACKEND", url: location.origin }), 20000);
  await step(
    "backend",
    async () => {
      const extensionBackend = await extensionCommand({ type: "PING_BACKEND" }, 20000);
      if (extensionBackend?.ok) {
        return extensionBackend;
      }
      const pageBackend = await backendJson("/api/health");
      return {
        ok: true,
        via: "page_fetch",
        data: pageBackend,
        extensionBackend,
      };
    },
    25000
  );
  if (!etsyOnly) {
    if (fullChain) {
      const plan = await step(
        "plan_full_chain_trello",
        () => {
          const lockedItem =
            lockedTrelloCardId && lockedTrelloAttachmentIds.length
              ? {
                  active: true,
                  used: false,
                  prompt,
                  product: lockedTrelloProduct,
                  product_key: lockedTrelloProduct || lockedTrelloCardId,
                  product_name: lockedTrelloProduct,
                  trello_card_id: lockedTrelloCardId,
                  trello_list_id: lockedTrelloListId,
                  trello_attachment_ids: lockedTrelloAttachmentIds,
                  trello_source_card_id: lockedTrelloCardId,
                  trello_source_attachment_ids: lockedTrelloAttachmentIds,
                }
              : null;
          return backendJson("/api/extension/auto-trello/plan", {
            method: "POST",
            body: {
              batch: {
                title: "Full Chain Flow to Etsy Smoke",
                limit: 1,
                auto_trello: true,
                items: lockedItem ? [lockedItem] : [],
                job: {
                  type: "image",
                  title: "Full Chain Flow to Etsy",
                  prompt,
                  prompt_product: lockedTrelloProduct,
                  count: fullChainTarget,
                  aspect: "square",
                  trello_enabled: true,
                  etsy_enabled: true,
                  flow_agent_enabled: true,
                  flow_agent_auto_approve: true,
                  automation_graph: fullChainGraph(fullChainTarget),
                },
              },
            },
          });
        },
        45000
      );
      fullChainPlanItem = Array.isArray(plan?.items) ? plan.items[0] : null;
      if (!fullChainPlanItem) {
        throw new Error("Không lấy được Trello item để chạy full-chain.");
      }
      await step(
        "load_full_chain_source_image",
        async () => {
          fullChainSourceDataUrl = await backendImageToDataUrl(fullChainPlanItem.image_url);
          return {
            ok: Boolean(fullChainSourceDataUrl),
            imageName: fullChainPlanItem.image_name || "",
            dataUrlBytes: fullChainSourceDataUrl.length,
          };
        },
        45000
      );
      if (!fullChainSourceDataUrl) {
        throw new Error("Không tải được ảnh nguồn Trello cho full-chain.");
      }
    }

    await step("open_flow", () => extensionCommand({ type: "OPEN_FLOW" }), 20000);
    await sleep(12000);
    await step("inspect_flow_before", () => commandWithRetry({ type: "INSPECT_FLOW" }, 4, 5000, 25000), 45000);
    await step(
      "run_flow",
      async () => {
        const before = report.steps.find((item) => item.name === "inspect_flow_before")?.result;
        if (before?.ok === false && before?.reason === "content_unreachable") {
          return before;
        }
        return commandWithRetry(
          {
            type: "RUN_FLOW",
            payload: {
              prompt: fullChainPlanItem?.prompt || prompt,
              submit: shouldSubmit,
              requireImage: fullChain,
              imageDataUrl: fullChain ? fullChainSourceDataUrl : "",
              imageName: fullChain ? fullChainPlanItem?.image_name || "trello-source.jpg" : "",
              target: fullChain ? fullChainTarget : 1,
              autoApprove: true,
            },
          },
          5,
          10000,
          240000
        );
      },
      260000
    );

    if (fullChain) {
      await step(
        "archive_full_chain_to_trello_and_enqueue_etsy",
        async () => {
          const flowRun = report.steps.find((item) => item.name === "run_flow")?.result || {};
          const images = Array.isArray(flowRun.images)
            ? flowRun.images
                .filter((image) => image?.dataUrl)
                .map((image, index) => ({
                  data_url: image.dataUrl,
                  url: image.url || "",
                  name: image.name || `flow-${index + 1}.png`,
                  mime_type: String(image.dataUrl || "").slice(5, 80).split(";")[0] || "image/png",
                }))
            : [];
          if (images.length < fullChainTarget) {
            throw new Error(`Flow mới trả ${images.length}/${fullChainTarget} ảnh có dataUrl; không archive thiếu bộ.`);
          }
          return backendJson("/api/extension/auto-trello/archive", {
            method: "POST",
            body: {
              job: fullChainPlanItem.job,
              item: fullChainPlanItem.item,
              images,
              extension_result: flowRun,
            },
          });
        },
        120000
      );
    }
  }
  if (!skipEtsy) {
    if (!noOpenEtsy) {
      await step("open_etsy", () => extensionCommand({ type: "OPEN_ETSY" }), 20000);
      await sleep(2500);
    }
    await step("inspect_etsy", () => extensionCommand({ type: "INSPECT_ETSY" }), 30000);
  }

  if (params.get("etsyQueuePoll") === "1") {
    await step("poll_etsy_copy_queue", () => pollEtsyQueueUntilSettled(), ETSY_QUEUE_SETTLE_TIMEOUT_MS + 15000);
  }

  const flowRun = report.steps.find((item) => item.name === "run_flow");
  const etsyInspect = report.steps.find((item) => item.name === "inspect_etsy");
  const etsyQueuePoll = report.steps.find((item) => item.name === "poll_etsy_copy_queue");
  const fullChainArchive = report.steps.find((item) => item.name === "archive_full_chain_to_trello_and_enqueue_etsy");
  report.ok = Boolean(
    (etsyOnly || flowRun?.ok) &&
      (!fullChain || fullChainArchive?.ok) &&
      (!etsyInspect ||
        (etsyInspect.ok &&
          etsyInspect.result &&
          !etsyInspect.result.needsLogin &&
          (etsyInspect.result.listingsPage || etsyInspect.result.listingEditor || etsyInspect.result.shopManager))) &&
      (!etsyQueuePoll || etsyQueuePoll.ok)
  );
  report.finishedAt = new Date().toISOString();
  render();
  await postReport("finished");
}

main().catch(async (error) => {
  report.ok = false;
  report.error = String(error?.message || error);
  report.finishedAt = new Date().toISOString();
  render();
  await postReport("fatal");
});
