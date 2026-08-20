// Cron watchdog: một lần gộp code không được phép làm rơi nó.
//
// Chạy: node --experimental-sqlite --test 'automation_center/tests/*.test.mjs'
//
// Handler `scheduled` và `triggers.crons` phải đi cùng nhau: thiếu handler thì
// Cloudflare gọi vào chỗ trống, thiếu crons thì handler không bao giờ được gọi.
// Cả hai kiểu hỏng đều im lặng — Worker vẫn trả 200 cho mọi request, chỉ có
// phần tự kiểm tra sức khoẻ là chết. Đó là lý do nó được viết thành test chứ
// không để ai nhớ hộ.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import worker from "../src/worker.js";

const config = new URL("../wrangler.jsonc", import.meta.url);

// wrangler.jsonc cho phép comment; bỏ comment trước khi parse.
const readConfig = () => JSON.parse(
  readFileSync(config, "utf8")
    .replace(/^\s*\/\/.*$/gm, "")
    .replace(/\/\*[\s\S]*?\*\//g, ""),
);

test("worker vẫn xuất cả fetch lẫn scheduled", () => {
  assert.equal(typeof worker.fetch, "function");
  assert.equal(typeof worker.scheduled, "function", "mất handler scheduled là mất watchdog");
});

test("cấu hình vẫn có lịch cron gọi vào scheduled", () => {
  const crons = readConfig()?.triggers?.crons;
  assert.ok(Array.isArray(crons) && crons.length > 0, "triggers.crons trống thì scheduled không bao giờ chạy");
  for (const cron of crons) {
    assert.equal(typeof cron, "string");
    assert.equal(cron.trim().split(/\s+/).length, 5, `lịch cron "${cron}" phải có đúng 5 trường`);
  }
});

test("scheduled nuốt lỗi thay vì làm chết lịch", async () => {
  // env rỗng: mọi truy vấn D1 bên trong runHealthChecks sẽ ném lỗi. Nếu lỗi đó
  // thoát ra ngoài thì Cloudflare tính lần chạy là thất bại; watchdog phải tự
  // chịu lỗi của chính nó.
  const waited = [];
  const ctx = { waitUntil: (promise) => waited.push(promise) };
  await worker.scheduled({}, {}, ctx);
  assert.equal(waited.length, 1, "scheduled phải giao việc qua waitUntil");
  await assert.doesNotReject(waited[0]);
});
