// Chuỗi migration sau khi gộp hai nửa (ảnh + listing) thành một agent.
//
//   node --test --experimental-sqlite tests/migrations.test.mjs
//
// Chạy thật cả thư mục migrations/ trên SQLite, theo đúng thứ tự wrangler dùng
// (sắp xếp theo tên file).  Một bản giả lập schema viết tay sẽ không phát hiện
// được lỗi thật sự nguy hiểm ở đây: hai nửa từng ALTER cùng bảng `approvals`
// bằng hai tên cột khác nhau, và 0007 xoá một trong hai — nếu thứ tự sai hoặc
// chỉ mục chưa được bỏ trước, lệnh xoá cột sẽ nổ ngay trên D1 thật.
import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const MIGRATIONS = join(HERE, "..", "migrations");

const files = () => readdirSync(MIGRATIONS).filter((name) => name.endsWith(".sql")).sort();

function replay() {
  const db = new DatabaseSync(":memory:");
  for (const file of files()) db.exec(readFileSync(join(MIGRATIONS, file), "utf8"));
  return db;
}

const columns = (db, table) => db.prepare(`PRAGMA table_info(${table})`).all().map((row) => row.name);
const names = (db, type) => db.prepare("SELECT name FROM sqlite_master WHERE type = ?").all(type).map((row) => row.name);

// Sáu file này ĐÃ được ghi vào bảng d1_migrations của cơ sở dữ liệu thật.  Đổi
// tên bất kỳ file nào trong số đó là bảo wrangler rằng nó chưa từng chạy: lần
// apply sau sẽ chạy lại một ALTER TABLE đã chạy rồi và dừng giữa chừng.  Nội
// dung thì sửa được (D1 không so nội dung), tên thì không.
const APPLIED_ON_D1 = [
  "0001_control_center.sql",
  "0002_content_image_runner.sql",
  "0003_listing2_erp_dashboard.sql",
  "0003_listing2_erp_runner.sql",
  "0004_orchestrator_agent.sql",
  "0005_health_watchdog.sql",
];

describe("chuỗi migration sau khi gộp", () => {
  test("chạy lại từ đầu trên cơ sở dữ liệu trắng không lỗi", () => {
    assert.doesNotThrow(() => replay());
  });

  test("không đổi tên file đã áp lên D1 thật", () => {
    const present = new Set(files());
    for (const file of APPLIED_ON_D1) assert.ok(present.has(file), `thiếu ${file}`);
  });

  // Nửa listing thêm approvals.runner_run_id, nửa ảnh thêm approvals.run_id —
  // cùng một ý nghĩa.  Giữ cả hai thì sớm muộn có phiếu chỉ điền một ô.
  test("approvals chỉ còn một cột trỏ về lượt chạy", () => {
    const db = replay();
    const cols = columns(db, "approvals");
    assert.ok(cols.includes("run_id"), "mất run_id");
    assert.ok(!cols.includes("runner_run_id"), "runner_run_id quay lại");
    for (const col of ["artifact_index", "pushed_at", "push_error"]) {
      assert.ok(cols.includes(col), `mất ${col}`);
    }
  });

  test("chỉ mục theo cột đã xoá cũng phải biến mất", () => {
    const db = replay();
    const idx = names(db, "index");
    assert.ok(!idx.includes("idx_approvals_runner_run"), "chỉ mục mồ côi còn lại");
    assert.ok(idx.includes("idx_approvals_pending_push"), "mất chỉ mục hàng đợi đẩy ảnh");
  });

  // Panel agent gộp có ba tab; mỗi tab đọc một họ bảng.  Bỏ sót họ nào thì tab
  // đó rỗng mà không có lỗi nào nổi lên.
  test("còn đủ bảng cho cả ba tab của panel agent", () => {
    const db = replay();
    const tables = new Set(names(db, "table"));
    for (const table of [
      "agent_threads", "agent_messages",                       // tab Chat
      "code_change_requests",                                  // tab Duyệt diff
      "agent_control_scopes", "agent_control_requests", "agent_control_commands", // tab Điều khiển bot
      "health_incidents", "runners", "bots", "bot_runs", "approvals",
    ]) assert.ok(tables.has(table), `thiếu bảng ${table}`);
  });

  test("bot_runs vẫn mang được số thẻ ERP", () => {
    assert.ok(columns(replay(), "bot_runs").includes("erp_task_id"));
  });
});
