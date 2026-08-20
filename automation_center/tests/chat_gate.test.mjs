// Cửa vào của hai đường chat trong panel "Agent trung tâm".
//
//   node --test --experimental-sqlite tests/chat_gate.test.mjs
//
// Hai tab Chat và Điều khiển bot dùng CHUNG bảng agent_threads, và danh sách
// luồng chỉ hiện 30 hàng mới nhất.  Nên một luồng rỗng sinh ra do yêu cầu bị từ
// chối không phải rác vô hại: đủ 30 lần bị từ chối là luồng thật biến mất khỏi
// màn hình của CẢ hai tab.  Vì vậy test này chạy trên SQLite thật và đếm hàng,
// chứ không chỉ kiểm mã lỗi HTTP trả về.
import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { createAgentThread, createControlThread } from "../src/worker.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const MIGRATIONS = join(HERE, "..", "migrations");

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

const OWNER = { email: "chu@havigroup.llc", global_role: "owner" };

function fresh() {
  const db = new DatabaseSync(":memory:");
  for (const file of readdirSync(MIGRATIONS).filter((n) => n.endsWith(".sql")).sort()) {
    db.exec(readFileSync(join(MIGRATIONS, file), "utf8"));
  }
  db.exec(`INSERT INTO users (email, display_name, global_role) VALUES ('${OWNER.email}', 'Chu', 'owner')`);
  db.exec(`INSERT INTO dashboards (id, slug, name, status, created_by)
           VALUES ('dash-1', 'listing-2-erp', 'Listing 2', 'active', '${OWNER.email}')`);
  return { db, env: { DB: d1(db) } };
}

const post = (body) => new Request("https://x/api", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify(body),
});

const threadCount = (db) => db.prepare("SELECT COUNT(*) AS n FROM agent_threads").get().n;

// Cả hai runner đều vắng mặt trong cơ sở dữ liệu trắng, nên cả hai đường chat
// đều phải từ chối ở bước "chưa có ai xử lý" — đúng tình huống hay gặp nhất
// ngoài đời: người dùng nhắn lúc máy trung tâm đang tắt.
describe("runner chưa kết nối thì không để lại luồng rỗng", () => {
  test("tab Chat: từ chối 409 và agent_threads vẫn trống", async () => {
    const { db, env } = fresh();
    const thrown = await createAgentThread(post({ message: "sửa giúp hàm gửi ảnh" }), env, OWNER, "listing-2-erp")
      .then(() => null, (caught) => caught);
    assert.ok(thrown instanceof Response, "phải ném Response chứ không âm thầm đi tiếp");
    assert.equal(thrown.status, 409);
    assert.equal(threadCount(db), 0, "luồng rỗng bị bỏ lại");
  });

  test("tab Điều khiển bot: từ chối 409 và agent_threads vẫn trống", async () => {
    const { db, env } = fresh();
    const thrown = await createControlThread(post({ message: "dừng con bot ảnh lại" }), env, OWNER, "listing-2-erp")
      .then(() => null, (caught) => caught);
    assert.ok(thrown instanceof Response);
    assert.equal(thrown.status, 409);
    assert.equal(threadCount(db), 0, "luồng rỗng bị bỏ lại");
  });

  // Bị từ chối nhiều lần cũng không được tích luỹ: đây mới là kịch bản làm mất
  // luồng thật, vì hai tab chia nhau đúng một danh sách 30 hàng.
  test("từ chối nhiều lần vẫn không tích luỹ luồng", async () => {
    const { db, env } = fresh();
    for (let i = 0; i < 5; i += 1) {
      await createAgentThread(post({ message: `yêu cầu số ${i} cần sửa code` }), env, OWNER, "listing-2-erp").catch(() => {});
      await createControlThread(post({ message: `yêu cầu số ${i} cần dừng bot` }), env, OWNER, "listing-2-erp").catch(() => {});
    }
    assert.equal(threadCount(db), 0);
  });
});

// Người chưa được cấp phạm vi phải bị chặn TRƯỚC khi có bất kỳ hàng nào được
// ghi.  operator có capability code_request nhưng không mặc nhiên có code_scope.
describe("chưa được cấp phạm vi thì không để lại luồng rỗng", () => {
  test("operator không có code_scope: 403, không có luồng", async () => {
    const { db, env } = fresh();
    db.exec(`INSERT INTO users (email, global_role) VALUES ('nv@havigroup.llc', 'operator')`);
    db.exec(`INSERT INTO dashboard_members (dashboard_id, user_email, role, granted_by)
             VALUES ('dash-1', 'nv@havigroup.llc', 'operator', '${OWNER.email}')`);
    // Runner sống, để chắc chắn lỗi đến từ phạm vi chứ không từ kết nối.
    db.exec(`INSERT INTO runners (runner_key, label, status, last_seen_at)
             VALUES ('orchestrator-runner', 'Trung tâm', 'online', '${new Date().toISOString()}')`);
    const user = { email: "nv@havigroup.llc", global_role: "operator" };
    const thrown = await createAgentThread(post({ message: "đổi giúp mức log sang DEBUG" }), env, user, "listing-2-erp")
      .then(() => null, (caught) => caught);
    assert.ok(thrown instanceof Response);
    assert.equal(thrown.status, 403);
    assert.equal(threadCount(db), 0);
  });
});
