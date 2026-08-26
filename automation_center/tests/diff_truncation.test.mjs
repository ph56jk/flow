// Cảnh báo "diff đã bị cắt" phải thật sự bật lên được.
//
//   node --test --experimental-sqlite tests/diff_truncation.test.mjs
//
// Đây là cảnh báo duy nhất nói cho người duyệt biết họ đang nhìn một phần chứ
// không phải toàn bộ thay đổi.  Nó hỏng thì không kêu — màn hình vẫn sạch sẽ,
// vẫn có nút Duyệt, chỉ là phần chưa ai đọc thì vẫn được merge.  Vì vậy test
// này đi qua ĐÚNG đường thật: POST vào endpoint runner, rồi đọc lại hàng trong
// cơ sở dữ liệu, chứ không gọi thẳng một hàm thuần.
import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import worker, { CONTROL_LIMITS } from "../src/worker.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const MIGRATIONS = join(HERE, "..", "migrations");

const SECRET = "runner-secret-cho-test";
const RUNNER = "orchestrator-runner";
const REQUEST_ID = "req-diff-1";
// Đọc thẳng trần của Worker: hằng số chép tay ở đây thì ngày trần đổi, test
// vẫn xanh trong khi runner và Worker đã nói hai con số khác nhau.
const LIMIT = CONTROL_LIMITS.DIFF_TEXT_MAX;

// D1 trả {meta:{changes}} / {results:[...]}; node:sqlite trả hình dạng khác.
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

const SCOPE = JSON.stringify({
  allow_globs: ["flow_web/**"], max_files: 5, max_lines: 5000, auto_apply: 0,
});

function fresh() {
  const db = new DatabaseSync(":memory:");
  for (const file of readdirSync(MIGRATIONS).filter((n) => n.endsWith(".sql")).sort()) {
    db.exec(readFileSync(join(MIGRATIONS, file), "utf8"));
  }
  db.exec(`INSERT INTO users (email, display_name, global_role) VALUES ('chu@havigroup.llc', 'Chu', 'owner')`);
  db.exec(`INSERT INTO dashboards (id, slug, name, status, created_by)
           VALUES ('dash-1', 'listing-2-erp', 'Listing 2', 'active', 'chu@havigroup.llc')`);
  db.exec(`INSERT INTO agent_threads (id, dashboard_id, title, created_by)
           VALUES ('thread-1', 'dash-1', 'sửa giúp hàm gửi ảnh', 'chu@havigroup.llc')`);
  db.prepare(`INSERT INTO code_change_requests
      (id, dashboard_id, thread_id, runner_key, requested_by, requested_role, instruction, scope_json, status)
      VALUES (?, 'dash-1', 'thread-1', ?, 'chu@havigroup.llc', 'owner', 'sửa giúp hàm gửi ảnh', ?, 'planning')`)
    .run(REQUEST_ID, RUNNER, SCOPE);
  return { db, env: { DB: d1(db), RUNNER_SHARED_SECRET: SECRET } };
}

async function reportDiff(env, body) {
  const request = new Request(`https://x/api/runner/code/${REQUEST_ID}`, {
    method: "POST",
    headers: { "content-type": "application/json", "x-automation-runner-secret": SECRET },
    body: JSON.stringify({
      runner_key: RUNNER,
      status: "awaiting_approval",
      plan_summary: "sửa một dòng",
      files: [{ path: "flow_web/service.py" }],
      lines_changed: 2,
      tests_passed: true,
      test_output: "ok",
      branch: "agent/abc123",
      ...body,
    }),
  });
  const response = await worker.fetch(request, env);
  assert.equal(response.status, 200, await response.text());
  return response;
}

const stored = (db) => db.prepare(
  "SELECT status, diff_truncated, LENGTH(diff_text) AS len FROM code_change_requests WHERE id = ?",
).get(REQUEST_ID);

describe("cờ diff bị cắt", () => {
  test("runner báo đã cắt thì Center phải tin, dù diff nhận được vừa khít trần", async () => {
    // Ca thật và cũng là ca Center KHÔNG tự nhận ra được: runner cắt ở đúng
    // 60 000 rồi mới gửi, nên thứ đến nơi luôn vừa khít trần.  Suy ra từ độ dài
    // ở đây là luôn suy ra "không bị cắt".
    const { db, env } = fresh();
    await reportDiff(env, { diff_text: "d".repeat(LIMIT), diff_truncated: 1 });
    const row = stored(db);
    assert.equal(row.status, "awaiting_approval");
    assert.equal(row.diff_truncated, 1, "runner đã nói là cắt rồi mà Center vẫn báo nguyên vẹn");
  });

  test("diff nguyên vẹn có khoảng trắng cuối dòng không được báo nhầm là đã cắt", async () => {
    // Center dọn khoảng trắng cuối dòng trước khi lưu, nên bản lưu NGẮN HƠN bản
    // nhận được ở một diff còn nguyên.  Lấy chênh lệch đó làm bằng chứng "bị
    // cắt" là dựng cảnh báo đỏ trên một diff đầy đủ — và cảnh báo nào cũng đỏ
    // thì chẳng còn ai đọc.
    const { db, env } = fresh();
    await reportDiff(env, { diff_text: "diff --git a/x b/x   \n+một dòng   \n" });
    assert.equal(stored(db).diff_truncated, 0, "diff còn nguyên mà bị báo là đã cắt");
  });

  test("runner cũ không gửi cờ nhưng diff dài quá trần thì vẫn phải cảnh báo", async () => {
    // Trần của Center là hàng rào cuối.  Một runner chưa cập nhật vẫn gửi diff
    // đầy đủ; lúc đó chính Center là bên cắt, và bên cắt thì phải nói.
    const { db, env } = fresh();
    await reportDiff(env, { diff_text: "d".repeat(LIMIT + 5000) });
    const row = stored(db);
    assert.equal(row.diff_truncated, 1);
    assert.equal(row.len, LIMIT, "phần lưu lại phải dừng đúng ở trần");
  });
});
