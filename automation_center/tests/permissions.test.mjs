// Ranh giới quyền của Agent điều phối.
//
// Chạy: node --test automation_center/tests
//
// Những gì kiểm ở đây là thứ duy nhất đứng giữa "nhân viên nhắn cho agent" và
// "agent sửa được cả repo".  Lời nhắc gửi cho ChatGPT không được tính là một
// lớp bảo vệ, nên nó không xuất hiện trong file này.

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  ROLE_CAPABILITIES, PROTECTED_GLOBS,
  capability, permissionsFor, normaliseRepoPath, matchesAnyGlob,
  isProtectedPath, parseGlobList, auditChangedFiles, countDiffLines, cleanBlock,
} from "../src/worker.js";

test("chỉ những vai trò được chọn mới gửi và duyệt được thay đổi code", () => {
  assert.equal(capability("owner", "code_request"), true);
  assert.equal(capability("admin", "code_request"), true);
  assert.equal(capability("operator", "code_request"), true);
  assert.equal(capability("reviewer", "code_request"), false);
  assert.equal(capability("viewer", "code_request"), false);

  // Operator gửi được yêu cầu nhưng không tự duyệt được — đó là chỗ tách
  // "ai cũng nhắn được" khỏi "ai cũng sửa được".
  assert.equal(capability("operator", "code_approve"), false);
  assert.equal(capability("admin", "code_approve"), true);
  assert.equal(capability("reviewer", "code_approve"), false);
});

test("vai trò lạ không mượn được quyền của vai trò có thật", () => {
  assert.equal(capability("", "code_request"), false);
  assert.equal(capability("superuser", "code_request"), false);
  assert.equal(capability("constructor", "code_request"), false);
  assert.equal(ROLE_CAPABILITIES.viewer.includes("code_request"), false);
});

test("đường dẫn bước ra khỏi repo bị loại", () => {
  assert.equal(normaliseRepoPath("../../etc/passwd"), "");
  assert.equal(normaliseRepoPath("flow_web/../.env.local"), "");
  assert.equal(normaliseRepoPath("/etc/passwd"), "");
  assert.equal(normaliseRepoPath("C:/Windows/system32/x.dll"), "");
  assert.equal(normaliseRepoPath("flow_web//service.py"), "");
  assert.equal(normaliseRepoPath("./service.py"), "");
  assert.equal(normaliseRepoPath("a\nb.py"), "");
  assert.equal(normaliseRepoPath(""), "");
  // Dấu \ của Windows được đưa về / chứ không dùng để lách allowlist.
  assert.equal(normaliseRepoPath("flow_web\\static\\app.js"), "flow_web/static/app.js");
});

test("một dấu sao không đi qua dấu gạch chéo, hai dấu sao thì có", () => {
  assert.equal(matchesAnyGlob("flow_web/static/app.js", ["flow_web/*"]), false);
  assert.equal(matchesAnyGlob("flow_web/static/app.js", ["flow_web/*/*.js"]), true);
  assert.equal(matchesAnyGlob("flow_web/static/app.js", ["flow_web/**"]), true);
  assert.equal(matchesAnyGlob("flow_web/a/b/c/app.js", ["flow_web/**"]), true);
  // "a/**/b" phải khớp cả khi ở giữa không có thư mục nào.
  assert.equal(matchesAnyGlob("flow_web/app.js", ["flow_web/**/app.js"]), true);
  assert.equal(matchesAnyGlob("flow_web/x/app.js", ["flow_web/**/app.js"]), true);
  // Khớp một phần không tính: mẫu phải phủ hết đường dẫn.
  assert.equal(matchesAnyGlob("flow_web_secret/app.js", ["flow_web/**"]), false);
  assert.equal(matchesAnyGlob("other/flow_web/app.js", ["flow_web/**"]), false);
});

test("dấu chấm trong mẫu là dấu chấm, không phải ký tự bất kỳ", () => {
  assert.equal(matchesAnyGlob("docs/readme.md", ["docs/*.md"]), true);
  assert.equal(matchesAnyGlob("docs/readmeXmd", ["docs/*.md"]), false);
});

test("file bí mật và file hạ tầng luôn nằm trong danh sách bảo vệ", () => {
  for (const path of [
    ".env", ".env.local", "flow-v2/.env.local", "runner/listing2-erp.env",
    "automation_center/src/worker.js",
    "automation_center/migrations/0004_orchestrator_agent.sql",
    "automation_center/runner/orchestrator_runner.py",
    "automation_center/scripts/set-runner-secret.sh",
    "automation_center/wrangler.jsonc",
    ".github/workflows/deploy.yml",
    ".gitignore",
    "keys/server.pem",
  ]) {
    assert.equal(isProtectedPath(path), true, `${path} phải được bảo vệ`);
  }
});

test("code bình thường không bị nhầm là file được bảo vệ", () => {
  for (const path of [
    "flow_web/service.py", "flow_web/static/app.js", "README.md",
    "automation_center/public/app.js", "tests/test_erp_review.py",
  ]) {
    assert.equal(isProtectedPath(path), false, `${path} không nên bị chặn`);
  }
});

test("phạm vi rộng nhất vẫn không mở được file được bảo vệ", () => {
  // "**" cho phép ghi mọi nơi, nhưng worker.js vẫn bị đánh dấu protected nên
  // luôn phải Owner duyệt tay — đó là cái chặn agent tự sửa phần phân quyền.
  const scope = { allow_globs: ["**"] };
  const audit = auditChangedFiles([{ path: "automation_center/src/worker.js" }], scope);
  assert.deepEqual(audit.outside, []);
  assert.deepEqual(audit.protectedPaths, ["automation_center/src/worker.js"]);
});

test("file ngoài phạm vi bị chỉ mặt, không bị bỏ qua im lặng", () => {
  const scope = { allow_globs: ["automation_center/public/**"] };
  const audit = auditChangedFiles([
    { path: "automation_center/public/app.js" },
    { path: "flow_web/service.py" },
    { path: "../../etc/passwd" },
  ], scope);
  assert.deepEqual(audit.paths, ["automation_center/public/app.js", "flow_web/service.py"]);
  // Đường dẫn không chuẩn hoá được vẫn phải xuất hiện trong danh sách vi
  // phạm — bỏ nó đi thì một patch bẩn lại trông như một patch sạch.
  assert.deepEqual(audit.outside, ["flow_web/service.py", "../../etc/passwd"]);
  assert.deepEqual(audit.protectedPaths, []);
});

test("phạm vi trống không âm thầm trở thành phạm vi mở", () => {
  assert.deepEqual(parseGlobList(""), []);
  assert.deepEqual(parseGlobList("   \n  \n"), []);
  const audit = auditChangedFiles([{ path: "flow_web/service.py" }], { allow_globs: [] });
  assert.deepEqual(audit.outside, ["flow_web/service.py"]);
});

test("danh sách mẫu chấp nhận nhiều dòng và bỏ mẫu rác", () => {
  assert.deepEqual(
    parseGlobList("flow_web/static/**\n../../etc/**\n\nautomation_center/public/**,docs/*.md"),
    ["flow_web/static/**", "automation_center/public/**", "docs/*.md"],
  );
  // Dấu / thừa ở cuối bị cắt để "flow_web/static/" và "flow_web/static" là một.
  assert.deepEqual(parseGlobList("flow_web/static/"), ["flow_web/static"]);
});

test("danh sách bảo vệ không rỗng và phủ được cả .env lẫn worker", () => {
  assert.ok(PROTECTED_GLOBS.length > 5);
  assert.ok(PROTECTED_GLOBS.includes("automation_center/src/worker.js"));
});

test("đổi hoa thường không lách được danh sách bảo vệ", () => {
  // Máy trung tâm chạy Windows: ở đó "Secrets.json" và "secrets.json" là cùng
  // một file, nên phân biệt hoa thường ở đây chỉ tạo cảm giác an toàn.
  for (const path of [
    ".ENV", ".Env.Local", "Flow-v2/.Env.Local", "keys/Server.PEM",
    "src/Secrets.json", "docs/CREDENTIALS.md", "AUTOMATION_CENTER/src/Worker.js",
  ]) {
    assert.equal(isProtectedPath(path), true, `${path} phải được bảo vệ`);
  }
  // Phạm vi do người cấp thì vẫn phân biệt hoa thường: nó là danh sách tường
  // minh, đoán mò hộ người cấp sẽ mở rộng quyền ngoài ý họ.
  assert.equal(matchesAnyGlob("Flow_Web/app.js", ["flow_web/**"]), false);
});

test("số dòng đếm từ chính diff mà người duyệt nhìn thấy", () => {
  const diff = [
    "--- a/flow_web/service.py",
    "+++ b/flow_web/service.py",
    "@@ -1,3 +1,3 @@",
    " giữ nguyên",
    "-dòng cũ",
    "+dòng mới",
    "+dòng thêm",
  ].join("\n");
  // Tiêu đề "---"/"+++" là tên file, không phải nội dung thay đổi.
  assert.equal(countDiffLines(diff), 3);
  assert.equal(countDiffLines(""), 0);
  assert.equal(countDiffLines(null), 0);
});

test("agent điều khiển bot đúng bằng quyền của người gửi, không hơn", () => {
  // Nhánh bot_action của worker kiểm capability(requested_role, "run") — đúng
  // cái quyền mà nút Chạy/Dừng trên web dùng, và lấy vai trò đã đóng băng lúc
  // xếp việc.  Nhắn cho agent không được trở thành đường vòng để chạy bot mà
  // tự mình không bấm được.
  assert.equal(capability("operator", "run"), true);
  assert.equal(capability("admin", "run"), true);
  assert.equal(capability("owner", "run"), true);
  assert.equal(capability("reviewer", "run"), false);
  assert.equal(capability("viewer", "run"), false);
  assert.equal(capability("", "run"), false);
});


// ─── Port từ erplisting khi gộp hai nửa ─────────────────────────────────────

test("mỗi vai trò chỉ có đúng quyền của nó", () => {
  assert.equal(capability("owner", "create_dashboard"), true);
  assert.equal(capability("admin", "create_dashboard"), false);
  assert.equal(capability("admin", "manage_members"), true);
  assert.equal(capability("operator", "manage_members"), false);
  assert.equal(capability("operator", "run"), true);
  assert.equal(capability("reviewer", "run"), false);
  assert.equal(capability("reviewer", "review"), true);
  assert.equal(capability("viewer", "review"), false);
  assert.deepEqual(ROLE_CAPABILITIES.viewer, ["view"]);
  assert.deepEqual(permissionsFor("khong-co-vai-tro-nay"), []);
});

test("gộp hai nửa không nới quyền của vai trò thấp", () => {
  // Bảng quyền vừa nhận thêm agent_control/agent_recover từ nửa điều khiển.
  // Chỗ dễ hỏng nhất khi gộp là cho nhầm vai trò chỉ-xem một quyền ghi, nên
  // ranh giới đó được viết thẳng ra đây thay vì để suy từ bảng.
  assert.equal(capability("operator", "agent_control"), true);
  assert.equal(capability("operator", "agent_recover"), false);
  assert.equal(capability("admin", "agent_recover"), true);
  for (const role of ["reviewer", "viewer"]) {
    for (const permission of ["agent_control", "agent_recover", "code_request", "code_approve", "run"]) {
      assert.equal(capability(role, permission), false, `${role} không được có ${permission}`);
    }
  }
});

test("văn bản nhiều dòng giữ được xuống dòng", () => {
  // Kế hoạch của agent và log test đều là văn bản nhiều dòng; gộp hết thành
  // một dòng thì người duyệt không đọc được thứ họ đang duyệt.
  assert.equal(cleanBlock("a\r\nb\r\nc"), "a\nb\nc");
  assert.equal(cleanBlock("a   \nb\t\n"), "a\nb\n");
  assert.equal(cleanBlock("x".repeat(50), 10), "x".repeat(10));
  assert.equal(cleanBlock(null), "");
});
