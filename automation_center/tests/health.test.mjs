// Watchdog sức khoẻ host runner.
//
//   node --test --experimental-sqlite tests/health.test.mjs
//
// Chạy trên SQLite thật với chính các file trong migrations/, không phải trên
// một bản giả lập D1 tự viết.  Lý do: chốt chống cảnh báo trùng của watchdog là
// một UNIQUE INDEX ... WHERE resolved_at IS NULL, tức là nó nằm ở tầng cơ sở dữ
// liệu.  Một bản giả lập sẽ vui vẻ "chống trùng" đúng như code mong đợi và test
// vẫn xanh kể cả khi chỉ số kia bị gõ sai hoặc bị quên.
import { test, describe, before, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import {
  staleRunners, orphanRuns, accessTokenIncident, describeStaleRunner, alertText,
  runHealthChecks, healthOverview, healthThresholds,
} from "../src/worker.js";

// Không import thẳng hằng số: workerd đòi mọi named export của worker.js phải là
// hàm, nên ngưỡng chỉ ra ngoài qua healthThresholds().
const { runnerStaleMs: RUNNER_STALE_MS, runOrphanMs: RUN_ORPHAN_MS } = healthThresholds();

const HERE = dirname(fileURLToPath(import.meta.url));
const MIGRATIONS = join(HERE, "..", "migrations");
const HOUR = 3600000;

// D1 trả {meta:{changes}} cho run() và {results:[...]} cho all(); node:sqlite trả
// hình dạng khác.  Lớp mỏng này chỉ dịch giữa hai hình dạng đó.
function d1(db) {
  return {
    prepare(sql) {
      const statement = db.prepare(sql);
      let values = [];
      const api = {
        bind(...bound) { values = bound; return api; },
        async first() { return statement.get(...values) ?? null; },
        async all() { return { results: statement.all(...values) }; },
        async run() {
          const result = statement.run(...values);
          return { meta: { changes: Number(result.changes), last_row_id: Number(result.lastInsertRowid) } };
        },
      };
      return api;
    },
  };
}

function freshDb() {
  const db = new DatabaseSync(":memory:");
  for (const file of readdirSync(MIGRATIONS).filter((name) => name.endsWith(".sql")).sort()) {
    db.exec(readFileSync(join(MIGRATIONS, file), "utf8"));
  }
  return db;
}

const NOW = Date.parse("2026-08-16T02:00:00.000Z");
const iso = (offsetMs) => new Date(NOW + offsetMs).toISOString();

describe("nhận diện runner mất tín hiệu", () => {
  test("còn thở thì không bị gọi là chết", () => {
    const rows = [{ runner_key: "a", last_seen_at: iso(-2000) }];
    assert.deepEqual(staleRunners(rows, NOW), []);
  });

  test("quá ngưỡng thì bị gọi tên", () => {
    const rows = [
      { runner_key: "song", last_seen_at: iso(-RUNNER_STALE_MS + 1000) },
      { runner_key: "chet", last_seen_at: iso(-RUNNER_STALE_MS - 1000) },
    ];
    assert.deepEqual(staleRunners(rows, NOW).map((row) => row.runner_key), ["chet"]);
  });

  // Có hàng trong bảng runners nghĩa là đã từng heartbeat thành công, nên một
  // last_seen_at không đọc được là bất thường và phải nổi lên, không được im.
  test("mốc thời gian hỏng bị coi là mất tín hiệu", () => {
    for (const bad of [null, "", "hôm qua"]) {
      assert.equal(staleRunners([{ runner_key: "x", last_seen_at: bad }], NOW).length, 1, `giá trị ${JSON.stringify(bad)}`);
    }
  });

  test("mô tả nói rõ mất tín hiệu bao lâu", () => {
    const row = { runner_key: "content-image-runner", label: "Content", last_seen_at: iso(-25 * HOUR) };
    assert.match(describeStaleRunner(row, NOW), /25 giờ/);
    assert.match(describeStaleRunner({ ...row, last_seen_at: iso(-7 * 60000) }, NOW), /7 phút/);
  });
});

describe("nhận diện run mồ côi", () => {
  test("run vừa được cập nhật thì để yên", () => {
    assert.deepEqual(orphanRuns([{ id: "r", updated_at: iso(-60000) }], NOW), []);
  });

  test("run không ai đụng đến quá lâu là mồ côi", () => {
    const rows = [{ id: "r", updated_at: iso(-RUN_ORPHAN_MS - 1000) }];
    assert.deepEqual(orphanRuns(rows, NOW).map((row) => row.id), ["r"]);
  });

  // Ngược chiều với staleRunners: ở đây nghi ngờ thì KHÔNG đụng vào, vì hậu quả
  // là ghi đè một run có thể đang chạy thật.
  test("mốc thời gian hỏng thì không đụng vào", () => {
    assert.deepEqual(orphanRuns([{ id: "r", updated_at: "???", started_at: null, created_at: null }], NOW), []);
  });

  test("thiếu updated_at thì lùi về started_at rồi created_at", () => {
    const rows = [{ id: "r", updated_at: null, started_at: null, created_at: iso(-RUN_ORPHAN_MS - 1000) }];
    assert.deepEqual(orphanRuns(rows, NOW).map((row) => row.id), ["r"]);
  });
});

describe("cảnh báo Service Token hết hạn", () => {
  test("còn xa thì im", () => {
    assert.equal(accessTokenIncident("2027-08-13", NOW), null);
  });

  test("gần tới ngày thì mở cảnh báo", () => {
    const incident = accessTokenIncident(iso(30 * 24 * HOUR).slice(0, 10), NOW);
    assert.equal(incident.kind, "access_token_expiring");
    assert.match(incident.detail, /hết hạn sau 2\d ngày|hết hạn sau 30 ngày/);
  });

  test("đã quá hạn thì nói thẳng là đã hết hạn", () => {
    assert.match(accessTokenIncident("2026-08-01", NOW).detail, /đã hết hạn/);
  });

  test("cấu hình trống thì không tự bịa ra cảnh báo", () => {
    assert.equal(accessTokenIncident(undefined, NOW), null);
    assert.equal(accessTokenIncident("không phải ngày", NOW), null);
  });
});

test("nội dung cảnh báo liệt kê từng sự cố", () => {
  const text = alertText([
    { kind: "runner_offline", detail: "Content: mất tín hiệu 25 giờ." },
    { kind: "run_orphaned", detail: "Run abc kẹt." },
  ]);
  assert.match(text, /2 sự cố/);
  assert.match(text, /\[runner_offline\] Content: mất tín hiệu 25 giờ\./);
  assert.match(text, /\[run_orphaned\] Run abc kẹt\./);
});

describe("runHealthChecks trên cơ sở dữ liệu thật", () => {
  let db;
  let env;
  let posted;
  let webhookStatus;
  let realFetch;

  before(() => { realFetch = globalThis.fetch; });

  beforeEach(() => {
    db = freshDb();
    posted = [];
    webhookStatus = 200;
    env = {
      DB: d1(db),
      ALERT_WEBHOOK_URL: "https://alert.example.com/hook",
      ACCESS_TOKEN_EXPIRES_AT: "2027-08-13",
    };
    globalThis.fetch = async (url, init) => {
      posted.push({ url, body: JSON.parse(init.body) });
      if (webhookStatus === 0) throw new Error("mạng hỏng");
      return new Response("", { status: webhookStatus });
    };
    db.exec(`
      INSERT INTO users (email, display_name, global_role, active, created_at, updated_at)
        VALUES ('owner@havigroup.llc', 'Owner', 'owner', 1, '2026-08-01', '2026-08-01');
      INSERT INTO dashboards (id, slug, name, description, icon, color, status, runner_required, created_by, created_at, updated_at)
        VALUES ('dash', 'dash', 'Dash', '', 'image', 'teal', 'active', 1, 'owner@havigroup.llc', '2026-08-01', '2026-08-01');
      INSERT INTO bots (id, dashboard_id, name, purpose, runner_key, status, last_run_status, created_by, created_at, updated_at)
        VALUES ('bot', 'dash', 'Bot', '', 'content-image-runner', 'running', 'running', 'owner@havigroup.llc', '2026-08-01', '2026-08-01');
    `);
  });

  afterEach(() => {
    globalThis.fetch = realFetch;
    db.close();
  });

  const addRunner = (key, seenOffsetMs, status = "online") => db.exec(
    `INSERT INTO runners (runner_key, label, status, version, last_seen_at, created_at, updated_at)
     VALUES ('${key}', '${key}', '${status}', '1.0.0', '${iso(seenOffsetMs)}', '2026-08-01', '2026-08-01')`,
  );

  const addRun = (id, status, updatedOffsetMs) => db.exec(
    `INSERT INTO bot_runs (id, dashboard_id, bot_id, runner_key, requested_by, title, status, created_at, started_at, updated_at)
     VALUES ('${id}', 'dash', 'bot', 'content-image-runner', 'owner@havigroup.llc', 'Thử', '${status}',
             '${iso(updatedOffsetMs)}', '${iso(updatedOffsetMs)}', '${iso(updatedOffsetMs)}')`,
  );

  const incidents = () => db.prepare("SELECT * FROM health_incidents ORDER BY opened_at, kind").all();

  test("runner chết được đánh dấu offline, mở sự cố và báo ra ngoài", async () => {
    addRunner("content-image-runner", -25 * HOUR);
    const report = await runHealthChecks(env, NOW);

    assert.equal(report.opened, 1);
    assert.equal(db.prepare("SELECT status FROM runners WHERE runner_key = ?").get("content-image-runner").status, "offline");

    const rows = incidents();
    assert.equal(rows.length, 1);
    assert.equal(rows[0].kind, "runner_offline");
    assert.equal(rows[0].subject, "content-image-runner");
    assert.match(rows[0].detail, /25 giờ/);
    assert.ok(rows[0].notified_at, "phải đánh dấu đã báo");

    assert.equal(posted.length, 1);
    assert.equal(posted[0].url, "https://alert.example.com/hook");
    assert.match(posted[0].body.text, /mất tín hiệu 25 giờ/);
  });

  // Cron chạy mỗi 5 phút.  Nếu mỗi vòng mở thêm một sự cố thì một runner chết
  // qua đêm sẽ đẻ ra hàng trăm hàng và spam webhook đúng bằng số đó.
  test("chạy lại nhiều vòng không đẻ thêm sự cố cho cùng một runner", async () => {
    addRunner("content-image-runner", -25 * HOUR);
    await runHealthChecks(env, NOW);
    const second = await runHealthChecks(env, NOW + 5 * 60000);
    const third = await runHealthChecks(env, NOW + 10 * 60000);

    assert.equal(second.opened, 0);
    assert.equal(third.opened, 0);
    assert.equal(incidents().length, 1);
    assert.equal(posted.length, 1, "chỉ báo một lần");
  });

  test("runner sống lại thì sự cố được đóng, và lần chết sau mở sự cố mới", async () => {
    addRunner("content-image-runner", -25 * HOUR);
    await runHealthChecks(env, NOW);

    db.exec(`UPDATE runners SET status = 'online', last_seen_at = '${iso(5 * HOUR)}' WHERE runner_key = 'content-image-runner'`);
    await runHealthChecks(env, NOW + 5 * HOUR);
    assert.ok(incidents()[0].resolved_at, "sự cố cũ phải được đóng");

    db.exec(`UPDATE runners SET last_seen_at = '${iso(5 * HOUR)}' WHERE runner_key = 'content-image-runner'`);
    const report = await runHealthChecks(env, NOW + 30 * HOUR);
    assert.equal(report.opened, 1, "chết lần nữa phải mở sự cố mới");
    assert.equal(incidents().length, 2);
  });

  test("run mồ côi bị đóng lại, bot thoát trạng thái chạy, có vết trong audit", async () => {
    addRunner("content-image-runner", -25 * HOUR);
    addRun("run-cu", "running", -3 * HOUR);
    addRun("run-moi", "running", -60000);

    await runHealthChecks(env, NOW);

    const cu = db.prepare("SELECT status, error, finished_at FROM bot_runs WHERE id = 'run-cu'").get();
    assert.equal(cu.status, "failed");
    assert.match(cu.error, /mồ côi/);
    assert.ok(cu.finished_at);

    assert.equal(db.prepare("SELECT status FROM bot_runs WHERE id = 'run-moi'").get().status, "running", "run mới phải được để yên");
    assert.equal(db.prepare("SELECT status FROM bots WHERE id = 'bot'").get().status, "error");
    assert.equal(db.prepare("SELECT COUNT(*) AS n FROM audit_logs WHERE action = 'bot_run.orphaned'").get().n, 1);
    assert.ok(incidents().some((row) => row.kind === "run_orphaned" && row.resolved_at), "sự cố đã xử lý xong thì đóng luôn");
  });

  test("cancel_requested kẹt cũng được coi là mồ côi", async () => {
    addRunner("content-image-runner", -25 * HOUR);
    addRun("run-huy", "cancel_requested", -3 * HOUR);
    await runHealthChecks(env, NOW);
    assert.equal(db.prepare("SELECT status FROM bot_runs WHERE id = 'run-huy'").get().status, "failed");
  });

  // Cảnh báo gửi hỏng mà bị đánh dấu là đã gửi thì im lặng mất luôn, đúng cái
  // watchdog sinh ra để tránh.
  test("webhook lỗi thì giữ hàng đợi và thử lại vòng sau", async () => {
    addRunner("content-image-runner", -25 * HOUR);
    webhookStatus = 500;
    await runHealthChecks(env, NOW);

    let row = incidents()[0];
    assert.equal(row.notified_at, null);
    assert.match(row.notify_error, /HTTP 500/);

    webhookStatus = 200;
    await runHealthChecks(env, NOW + 5 * 60000);
    row = incidents()[0];
    assert.ok(row.notified_at, "vòng sau phải gửi lại được");
    assert.equal(posted.length, 2);
  });

  test("webhook ném lỗi mạng cũng giữ hàng đợi", async () => {
    addRunner("content-image-runner", -25 * HOUR);
    webhookStatus = 0;
    await runHealthChecks(env, NOW);
    assert.equal(incidents()[0].notified_at, null);
    assert.match(incidents()[0].notify_error, /mạng hỏng/);
  });

  test("chưa cấu hình webhook thì vẫn ghi sự cố, không kẹt hàng đợi", async () => {
    addRunner("content-image-runner", -25 * HOUR);
    env.ALERT_WEBHOOK_URL = "";
    await runHealthChecks(env, NOW);
    const row = incidents()[0];
    assert.ok(row.notified_at);
    assert.match(row.notify_error, /ALERT_WEBHOOK_URL/);
    assert.equal(posted.length, 0);
  });

  // http:// tới một webhook nghĩa là đẩy tình trạng hạ tầng qua mạng không mã hoá.
  test("webhook không phải https thì bị từ chối như chưa cấu hình", async () => {
    addRunner("content-image-runner", -25 * HOUR);
    env.ALERT_WEBHOOK_URL = "http://alert.example.com/hook";
    await runHealthChecks(env, NOW);
    assert.equal(posted.length, 0);
    assert.match(incidents()[0].notify_error, /ALERT_WEBHOOK_URL/);
  });

  test("mọi thứ khoẻ thì không mở sự cố nào và không gọi webhook", async () => {
    addRunner("content-image-runner", -2000);
    const report = await runHealthChecks(env, NOW);
    assert.equal(report.opened, 0);
    assert.equal(incidents().length, 0);
    assert.equal(posted.length, 0);
    assert.equal(db.prepare("SELECT status FROM runners WHERE runner_key = ?").get("content-image-runner").status, "online");
  });

  test("Service Token gần hết hạn mở đúng một cảnh báo", async () => {
    addRunner("content-image-runner", -2000);
    env.ACCESS_TOKEN_EXPIRES_AT = new Date(NOW + 10 * 24 * HOUR).toISOString().slice(0, 10);
    await runHealthChecks(env, NOW);
    await runHealthChecks(env, NOW + 5 * 60000);
    const rows = incidents().filter((row) => row.kind === "access_token_expiring");
    assert.equal(rows.length, 1);
    assert.match(rows[0].detail, /hết hạn sau/);
  });

  test("healthOverview nói đúng runner nào đang sống", async () => {
    addRunner("content-image-runner", -25 * HOUR);
    addRunner("listing2-erp-runner", -2000);
    await runHealthChecks(env, NOW);

    const view = await healthOverview(env, NOW);
    assert.equal(view.healthy, false);
    assert.deepEqual(
      view.runners.map((row) => [row.runner_key, row.online]),
      [["content-image-runner", false], ["listing2-erp-runner", true]],
    );
    assert.equal(view.open_incidents.length, 1);
  });
});
