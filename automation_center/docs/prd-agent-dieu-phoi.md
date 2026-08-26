# PRD — Agent điều phối (nhắn để sửa code, có giới hạn theo quyền)

Tài liệu này viết **sau** khi tính năng đã được xây, để chốt lại yêu cầu sản
phẩm, phạm vi và tiêu chí nghiệm thu. Mọi khẳng định dưới đây bám theo code
hiện có trong `automation_center/` (Worker `src/worker.js`, migration
`0004_orchestrator_agent.sql`, runner `runner/orchestrator_runner.py`, test
`tests/permissions.test.mjs`). Chỗ nào ý định sản phẩm và code chưa khớp nhau
được ghi thẳng ở mục 8 và 10, không giấu.

## 1. Bối cảnh và vấn đề

Automation Center (`automation.havigroup.llc`) đã có nhiều agent chạy trên
runner riêng (tạo ảnh Content, Listing 2 ERP). Nhưng mọi thay đổi **code** —
dù nhỏ như sửa một câu chữ trên giao diện — đều phải qua tay chủ sở hữu
(Owner): nhận yêu cầu, tự sửa trên máy cá nhân, tự test, tự deploy. Owner là
nút thắt duy nhất, và máy cá nhân của Owner là nơi duy nhất xử lý code.

Yêu cầu gốc của chủ sở hữu (giữ nguyên ý): tích hợp một agent dùng ChatGPT để
điều khiển/điều phối, cho phép **mọi người nhắn với agent để nó tự sửa code
theo ý họ mà không cần qua Owner**, nhưng phải có **giới hạn theo quyền** để
không ai sửa được toàn bộ code, và **máy trung tâm xử lý code thay cho máy của
Owner**.

Tính năng "Agent điều phối" giải đúng bài này: nhân viên mô tả thay đổi bằng
tiếng Việt trên web, runner trên máy trung tâm (PC `100.75.125.80`) gọi
ChatGPT đọc repo, sửa file, chạy test, trả diff về để duyệt. Ranh giới nằm ở
bảng allowlist trong D1 và code Worker/runner, **không** nằm ở lời nhắc gửi
cho ChatGPT — một mô hình ngôn ngữ có thể bị thuyết phục, một allowlist thì
không.

## 2. Mục tiêu và không nằm trong phạm vi

### Mục tiêu

1. Nhân viên có quyền gửi được yêu cầu sửa code bằng tiếng Việt, không cần
   biết git, không cần môi trường dev.
2. Mọi thay đổi bị chặn theo ba lớp độc lập (vai trò, phạm vi glob + trần
   file/dòng, danh sách bảo vệ toàn cục) — kể cả khi ChatGPT "muốn" làm khác.
3. Toàn bộ việc đọc repo, gọi ChatGPT, ghi file, chạy test, merge diễn ra
   trên máy trung tâm; máy cá nhân của Owner không tham gia bước nào.
4. Thay đổi chỉ vào nhánh base sau khi có người đủ quyền duyệt (hoặc phạm vi
   được Owner bật `auto_apply` và test xanh).
5. Agent không tự nới được quyền của chính nó: file phân quyền
   (`worker.js`, migrations, runner, scripts) nằm trong danh sách bảo vệ.

### Không nằm trong phạm vi (non-goals)

1. **Không tự deploy.** `applied` nghĩa là đã merge vào nhánh base của **bản
   sao repo riêng** trên máy trung tâm (`AGENT_REPO_DIR`); đẩy remote chỉ khi
   bật `AGENT_PUSH_REMOTE` (mặc định tắt). Đưa code đã merge vào service đang
   chạy vẫn là bước tay.
2. **Không điều khiển các agent/bot khác.** Yêu cầu gốc nói "điều khiển toàn
   bộ agent còn lại"; bản hiện tại chỉ làm phần **sửa code theo yêu cầu** —
   agent điều phối không gửi lệnh chạy/dừng cho bot tạo ảnh hay bot ERP.
   Xem mục 10.
3. Không có review nhiều người, không có comment trên từng dòng diff — chỉ
   duyệt/từ chối cả yêu cầu.
4. Không hỗ trợ repo nào ngoài `flow-v2` (cột `repo` đã có sẵn cho tương lai
   nhưng luôn là `'flow-v2'`).
5. Không dùng khoá OpenAI ở phía Worker/D1/trình duyệt dưới bất kỳ hình thức
   nào.

## 3. Người dùng và vai trò

Vai trò tính theo từng dashboard (Owner là global). Hai capability mới:
`code_request` (gửi yêu cầu) và `code_approve` (duyệt), khai báo trong
`ROLE_CAPABILITIES` của `src/worker.js`:

| Vai trò | Gửi yêu cầu (`code_request`) | Duyệt (`code_approve`) | Cấp phạm vi | Bật `auto_apply` | Duyệt yêu cầu chạm file bảo vệ |
| --- | --- | --- | --- | --- | --- |
| Owner | ✔ (phạm vi mặc định `**`, 40 file / 4000 dòng) | ✔ (kể cả yêu cầu của chính mình) | ✔ | ✔ (chỉ Owner) | ✔ (chỉ Owner) |
| Admin | ✔ | ✔ (trừ yêu cầu của chính mình) | ✔ | ✘ | ✘ |
| Operator | ✔ | ✘ | ✘ | ✘ | ✘ |
| Reviewer | ✘ | ✘ | ✘ | ✘ | ✘ |
| Viewer | ✘ | ✘ | ✘ | ✘ | ✘ |

Ghi chú:

- Reviewer duyệt được **ảnh** (capability `review`) nhưng cố ý **không** duyệt
  được code — duyệt code là quyết định cấu hình hệ thống, xếp cùng nhóm với
  Admin.
- Có capability chưa đủ: người gửi (trừ Owner) còn phải có một dòng
  `code_scopes` áp cho email hoặc vai trò của mình. Đóng mặc định, mở theo
  từng vai trò/người.
- Người gửi rút lại (`cancelled`) được yêu cầu của chính mình khi nó chưa kết
  thúc; người có `code_approve` cũng rút lại được yêu cầu của người khác.

## 4. Luồng người dùng chính

```
Nhắn yêu cầu ──► Worker đóng băng phạm vi, xếp hàng ──► Runner máy trung tâm claim
                                                            │
                                              ChatGPT (tối đa 4 lượt read/answer/edit)
                                                            │
                             nhánh agent/<id> ◄── ghi file trong phạm vi, chạy test, commit
                                                            │
Worker kiểm lại file/dòng ◄── runner báo diff + log test ───┘
        │
        ├─ vi phạm phạm vi ────────────────► failed (không ai duyệt được)
        ├─ chạm file bảo vệ ───────────────► awaiting_approval, chỉ Owner duyệt
        ├─ trong phạm vi + auto_apply + test xanh ─► approved (decided_by = 'auto')
        └─ còn lại ────────────────────────► awaiting_approval, chờ code_approve
                                                            │
                              approved ──► runner merge agent/<id> vào base ──► applied
```

1. Người dùng mở màn hình **Agent điều phối**, tạo thread hoặc nhắn tiếp vào
   thread cũ (mỗi tin nhắn tối thiểu 8 ký tự, tối đa 6000). Mỗi tin nhắn của
   người dùng sinh đúng một `code_change_request`.
2. Worker kiểm `code_request`, resolve phạm vi (dòng theo email thắng dòng
   theo vai trò), **đóng băng** phạm vi vào `scope_json`. Không có phạm vi →
   403. Runner chưa heartbeat trong 45 giây → 409, không xếp lệnh giả.
3. Runner claim (`queued` → `planning`), nhận chỉ thị, phạm vi đã đóng băng,
   `PROTECTED_GLOBS` và 40 tin nhắn gần nhất của thread.
4. Runner checkout `agent/<12 ký tự đầu của id>` từ nhánh base trong bản sao
   repo riêng, hội thoại với ChatGPT tối đa 4 lượt: `read` (đọc thêm file,
   file bảo vệ chỉ trả về "(file được bảo vệ, không gửi nội dung)"),
   `answer` (chỉ trả lời, trạng thái `answered`, không đổi file) hoặc `edit`
   (nội dung file mới hoàn chỉnh). Ghi file → chạy `AGENT_TEST_COMMAND` →
   commit.
5. Runner báo về diff, danh sách file, số dòng, log test. Worker **đối chiếu
   lại** danh sách file với phạm vi đã đóng băng; vi phạm → ép `failed` và
   runner xoá nhánh. Agent tóm tắt bằng tiếng Việt (`plan_summary`) cho người
   không đọc diff.
6. Người có `code_approve` xem diff trong thread và duyệt/từ chối. Duyệt →
   runner merge nhánh vào base, báo `applied`, kèm commit sha. Merge lỗi →
   `git merge --abort`, `failed`. Mọi lỗi giữa chừng: `reset --hard`,
   `clean -fd`, quay về base, xoá nhánh tạm.
7. Mọi bước ghi audit log (`code_request.queued/approved/rejected/applied/
   out_of_scope`, `code_scope.saved/revoked`) trong dashboard.

## 5. Yêu cầu chức năng

| # | Yêu cầu | Bám vào code |
| --- | --- | --- |
| FR-1 | Người có `code_request` tạo được thread và gửi tin nhắn; mỗi tin nhắn sinh một yêu cầu sửa code. | `createAgentThread`, `postAgentMessage`, `queueCodeRequest` |
| FR-2 | Không có bản ghi phạm vi (và không phải Owner) → gửi bị 403 kèm hướng dẫn nhờ Owner/Admin mở phạm vi. | `resolveCodeScope` trả `null` → 403 trong `queueCodeRequest` |
| FR-3 | Runner offline (>45 s không heartbeat) → 409, không xếp yêu cầu nào. | `queueCodeRequest` kiểm bảng `runners` |
| FR-4 | Phạm vi (glob + trần file + trần dòng + cờ `auto_apply`) được đóng băng vào `scope_json` lúc xếp hàng; sửa `code_scopes` sau đó không ảnh hưởng yêu cầu đang chờ. | `queueCodeRequest` ghi `JSON.stringify(scope)`; `runnerUpdateCodeRequest` chỉ đọc `row.scope_json` |
| FR-5 | Một thread chỉ có một yêu cầu đang chạy (`queued`/`planning`/`applying`); nhắn thêm khi đó → 409. | `postAgentMessage` (lưu ý: `awaiting_approval` không khoá — xem mục 10) |
| FR-6 | Agent phân biệt câu hỏi và lệnh sửa: câu hỏi → `answered`, chỉ trả lời trong thread, không đổi file. | `plan_change` action `answer`; `runnerUpdateCodeRequest` nhánh `answered` |
| FR-7 | Mọi thay đổi nằm trên nhánh riêng `agent/<id>` tách từ nhánh base trong bản sao repo riêng (`AGENT_REPO_DIR`), không phải bản đang chạy service. | `handle_request` trong `orchestrator_runner.py` |
| FR-8 | Runner từ chối **ghi** file: ngoài phạm vi, trong danh sách bảo vệ, đường dẫn không chuẩn (tuyệt đối, `..`, `\\`), quá 400 KB, hoặc vượt trần file/dòng. | `write_files`, `normalise_path`, `staged_stats` |
| FR-9 | Worker kiểm lại **độc lập với runner logic** danh sách file báo về so với `scope_json`: file ngoài phạm vi, vượt trần file/dòng → ép `failed`, ghi audit `out_of_scope`, runner xoá nhánh. | `auditChangedFiles`, `runnerUpdateCodeRequest` |
| FR-10 | Diff chạm file trong `PROTECTED_GLOBS` → `touches_protected = 1`: không bao giờ auto-apply, chỉ Owner duyệt được. | `runnerUpdateCodeRequest`, `decideCodeRequest` |
| FR-11 | `auto_apply` bật + trong phạm vi + không chạm file bảo vệ + test xanh + có ít nhất 1 file đổi → `approved` thẳng, `decided_by = 'auto'`. Mặc định mọi phạm vi tắt `auto_apply`. | `runnerUpdateCodeRequest` |
| FR-12 | Người gửi không tự duyệt yêu cầu của mình (403), trừ Owner. | `decideCodeRequest` |
| FR-13 | Người gửi rút lại được yêu cầu chưa kết thúc; người có `code_approve` rút lại được yêu cầu của người khác. Yêu cầu đã `cancelled` là trạng thái cuối — báo cáo runner đến sau bị bỏ qua (idempotent). | `decideCodeRequest` nhánh `cancelled`; `runnerUpdateCodeRequest` danh sách trạng thái cuối |
| FR-14 | Owner/Admin (`manage_members`) cấp/sửa/gỡ phạm vi theo vai trò hoặc theo email; glob rỗng = gỡ hẳn dòng; trần tối đa 60 file / 6000 dòng; chỉ Owner bật được `auto_apply`. | `saveCodeScope` |
| FR-15 | Không cấp được phạm vi trùng khít một glob bảo vệ (ví dụ `automation_center/src/worker.js`). | `saveCodeScope` (chỉ so khớp glob bằng nhau — xem mục 10) |
| FR-16 | Yêu cầu `approved` được runner nhận qua hàng đợi riêng và merge vào base; `AGENT_PUSH_REMOTE` bật thì push origin. | `runnerApprovedCodeRequests`, `apply_approved` |
| FR-17 | Mọi chuyển trạng thái đáng kể ghi audit log theo dashboard; secret không xuất hiện trong audit. | `addAudit` tại các điểm chuyển trạng thái |
| FR-18 | Trạng thái runner (online/last_seen/last_error) và danh sách file bảo vệ hiển thị cho người dùng trong màn hình Agent điều phối. | `agentOverview` trả `runner` + `protected_globs`; UI `public/app.js` |
| FR-19 | Chưa cấu hình `AGENT_TEST_COMMAND` → mọi thay đổi coi là "chưa có test xanh", không bao giờ auto-apply. | `run_tests` trả `(False, …)` |
| FR-20 | Ranh giới quyền (vai trò, glob, danh sách bảo vệ, chuẩn hoá đường dẫn, audit file) phải kiểm được ngoài môi trường Worker bằng `node --test --experimental-sqlite tests/permissions.test.mjs`. | export cuối `worker.js`; toàn bộ `permissions.test.mjs` |

## 6. Mô hình phân quyền — ba lớp giới hạn

Ba lớp **độc lập nhau**; vượt một lớp không mở được lớp kia. Không lớp nào
nằm trong prompt gửi cho ChatGPT.

### Lớp 1 — Vai trò (capability)

`code_request`: Owner/Admin/Operator. `code_approve`: Owner/Admin. Tra
capability qua `Object.hasOwn` để vai trò lạ (`constructor`, `superuser`)
không mượn được quyền qua prototype của Object.

### Lớp 2 — Phạm vi glob + trần, đóng băng lúc xếp hàng

Bảng `code_scopes`: mỗi dòng cấp cho một vai trò hoặc một email cụ thể (email
thắng vai trò) một danh sách glob (`**` đi qua `/`, `*` thì không), trần
`max_files` (mặc định 3, tối đa 60) và `max_lines` (mặc định 200, tối đa
6000). Không có dòng nào → không gửi được (đóng mặc định). Owner không cần
dòng nào: mặc định `**`, 40 file / 4000 dòng, `auto_apply = 0` — quyền sửa
mọi file và quyền áp thẳng không cần ai xem là hai chuyện khác nhau.

Phạm vi được **đóng băng** vào `code_change_requests.scope_json` ngay lúc xếp
hàng: đổi quyền về sau không âm thầm nới rộng (hay siết chặt sai) một yêu cầu
đang chờ. Phạm vi được kiểm **hai lần** trùng nhau có chủ ý: runner từ chối
*ghi* file ngoài phạm vi, Worker từ chối *nhận* kết quả ngoài phạm vi.

### Lớp 3 — Danh sách bảo vệ toàn cục (`PROTECTED_GLOBS`)

`.env*`, `*.pem`, `*.key`, `*secret*`, `*credentials*`, `.gitignore`,
`.github/**`, `wrangler.*`, `automation_center/migrations/**`,
`automation_center/runner/**`, `automation_center/scripts/**` và chính
`automation_center/src/worker.js`. Phạm vi rộng đến `**` cũng không vượt
được: chạm vào là `touches_protected`, không bao giờ auto-apply, chỉ Owner
duyệt tay được.

**Vì sao `worker.js` tự nằm trong danh sách bảo vệ:** toàn bộ lớp 1–3 sống
trong file này. Nếu agent sửa được `worker.js` (hoặc migrations, hoặc chính
runner) thì nó sửa được luật đang ràng buộc nó, và mọi giới hạn phía dưới chỉ
còn là gợi ý. Tương tự, runner giữ **bản sao cứng riêng** của
`PROTECTED_GLOBS`: một Center bị cấu hình sai vẫn không khiến runner đọc hay
ghi file bí mật — file bảo vệ không bao giờ được gửi nội dung sang OpenAI.

## 7. Yêu cầu phi chức năng

### Bảo mật

- `OPENAI_API_KEY` **chỉ** nằm trong `runner/orchestrator.env` trên máy trung
  tâm (ACL giới hạn, bỏ kế thừa): không vào D1, `public/`, form của Automation
  Center, Git hay audit log.
- Runner xác thực về Worker bằng `RUNNER_SHARED_SECRET` (header) + Cloudflare
  Access Service Token; người dùng đi qua Cloudflare Access SSO, Worker chỉ
  tin email từ header do Access ký.
- Nội dung file bảo vệ không rời máy trung tâm — không gửi sang OpenAI, không
  trả về Worker.
- Đường dẫn được chuẩn hoá cả hai phía: loại `..`, đường dẫn tuyệt đối, ổ đĩa
  Windows, ký tự điều khiển; `\` đưa về `/` chứ không dùng để lách allowlist.

### Cô lập

- Agent làm việc trên **bản clone riêng** (`C:\HaviGroup\agent-workspace\flow-v2`),
  tách khỏi bản đang chạy service — agent checkout qua lại giữa các nhánh,
  dùng chung sẽ làm Flow đọc code nửa chừng.
- Mỗi yêu cầu một nhánh `agent/<id>`; nhánh base chỉ nhận sau quyết định
  duyệt. Runner đòi repo sạch (`git status --porcelain` rỗng) trước khi làm.

### Khả năng hoàn tác

- Mỗi thay đổi là một merge có `commit_sha` ghi trong D1 và audit log — hoàn
  tác bằng `git revert` thủ công trên máy trung tâm. Lỗi giữa chừng tự dọn:
  `reset --hard`, `clean -fd`, xoá nhánh tạm. Chưa có nút revert trên UI
  (mục 10).

### Hiệu năng / độ trễ

- Runner poll mỗi 3 giây (cấu hình được); heartbeat coi là offline sau 45 giây.
- Mỗi yêu cầu: tối đa 4 lượt ChatGPT (timeout 300 s/lượt), test timeout 900 s.
  Độ trễ điển hình do ChatGPT + test quyết định, không phải do Worker.
- Trần dữ liệu: đọc file gửi ChatGPT 120 KB/file, ghi 400 KB/file, diff lưu và
  hiển thị tối đa 60 000 ký tự, log test 8 000 ký tự, liệt kê tối đa 400 file
  trong context.

## 8. Rủi ro và cách giảm thiểu

| Rủi ro | Giảm thiểu hiện có | Còn hở |
| --- | --- | --- |
| **Prompt injection từ nội dung repo/thread**: file hoặc tin nhắn chứa "chỉ thị" khiến ChatGPT ghi file ngoài ý muốn. | Ranh giới nằm ngoài prompt: allowlist glob + danh sách bảo vệ được enforce bằng code ở cả runner lẫn Worker; ghi sai là `failed`, không phải "ghi rồi tính sau". | ChatGPT vẫn có thể sửa *nội dung sai* trong phạm vi hợp lệ — lớp duyệt của con người là chốt cuối; với `auto_apply` chốt đó không còn, nên chỉ Owner bật được và nên bật cho phạm vi hẹp. |
| **Agent tự nới quyền** (sửa worker.js/migrations/runner). | Toàn bộ file phân quyền nằm trong `PROTECTED_GLOBS` ở cả hai phía; chạm vào là chỉ Owner duyệt tay; test khoá điều này (`phạm vi rộng nhất vẫn không mở được file được bảo vệ`). | `saveCodeScope` chỉ chặn glob **trùng khít** glob bảo vệ; glob bao trùm (`automation_center/**`) vẫn cấp được — vô hại vì bị chặn lúc audit, nhưng dễ gây hiểu nhầm là "đã cấp được". |
| **Worker tin số liệu runner báo về.** Lớp kiểm lại của Worker dùng `files` do runner gửi. | Số dòng nay lấy `max(runner báo, đếm được trong chính diff người duyệt nhìn)`, nên báo thiếu không lách được trần và con số luôn khớp diff hiển thị. Runner nằm trên máy công ty, xác thực bằng secret + Service Token; lớp Worker chống lỗi logic/model ở runner, không nhằm chống runner bị chiếm. | Danh sách `files` vẫn do runner cung cấp. Runner bị chiếm = mất cả repo; niềm tin đặt vào việc giữ máy trung tâm và secret, cần nói rõ trong vận hành. |
| **Merge xung đột giữa các yêu cầu.** Hai nhánh `agent/<id>` cùng tách từ base có thể đè nhau. | Merge lỗi → `git merge --abort`, báo `failed` kèm lý do; không bao giờ để repo ở trạng thái merge dở. | Thread chỉ khoá khi `queued/planning/applying`; yêu cầu đang `awaiting_approval` **không** khoá thread, nên có thể tồn tại nhiều nhánh chờ duyệt chồng lấn — người duyệt sau có thể gặp `failed` vì conflict và phải nhắn lại yêu cầu. |
| **Diff hiển thị bị cắt ở 60 000 ký tự** trong khi commit thật đầy đủ. | Cột `diff_truncated` đánh dấu lần cắt; UI hiện cảnh báo đỏ kèm tên nhánh để người duyệt xem bản đầy đủ trên máy trung tâm trước khi bấm. `diffHtml` cũng báo khi cắt tiếp ở 900 dòng. | Người duyệt vẫn có thể bỏ qua cảnh báo và bấm duyệt; không có cách ép đọc. |
| **Chi phí token.** Mỗi yêu cầu tối đa 4 lượt gọi model (`gpt-5` mặc định), kèm nội dung file đã đọc. | Trần 4 lượt, 12 file/lượt đọc, 120 KB/file; yêu cầu tối đa 6000 ký tự. | Chưa có đo đếm chi phí theo yêu cầu/người gửi; chưa có hạn mức ngày. |
| **Runner offline hoặc chết giữa chừng.** | Offline → Worker trả 409 ngay lúc gửi, không có lệnh treo "ảo". | Chết **giữa** `planning`/`applying` thì yêu cầu kẹt ở trạng thái đó, không có watchdog dọn (giống run mồ côi của bot tạo ảnh trong runbook) — xử lý tay. |
| **Rút lại yêu cầu chỉ có tác dụng một phần.** | Runner kiểm `cancelled` một lần trước khi chạy test; Worker bỏ qua báo cáo đến sau khi đã `cancelled`. | Rút sau thời điểm kiểm thì runner vẫn commit xong nhánh; kết quả bị bỏ qua nhưng nhánh `agent/<id>` mồ côi nằm lại trong workspace, cần dọn tay. |
| **Đọc rộng hơn ghi.** ChatGPT được đọc mọi file không-bảo-vệ trong repo (kể cả ngoài phạm vi ghi) để hiểu ngữ cảnh. | File bảo vệ không bao giờ gửi đi; chỉ file git đang theo dõi. | Phạm vi ghi hẹp **không** giới hạn phần code rời máy sang OpenAI — chấp nhận có chủ ý, cần ghi nhận khi cấp quyền cho người ngoài nhóm dev. |
| **Hai bản cài glob bảo vệ phải giữ đồng bộ.** Worker dùng regex `**` tự viết, runner dùng `fnmatch` (dấu `*` của fnmatch đi qua `/`, nên phía runner rộng hơn — lệch về phía an toàn). | `tests/test_scope_parity.py` chạy cùng một tập đường dẫn qua **cả hai** bản cài và bắt lỗi nếu runner lỏng hơn Worker; đã tìm ra hai chỗ lệch thật (runner nhận đường dẫn có `\n`; danh sách bảo vệ phân biệt hoa thường) và cả hai đã sửa. | Thêm glob mới vẫn phải sửa **hai chỗ** — test bắt được nhưng không tự đồng bộ hộ. |

## 9. Tiêu chí nghiệm thu

Checklist kiểm được, gắn với test/endpoint thật:

- [ ] `node --test --experimental-sqlite tests/permissions.test.mjs` xanh toàn bộ (capability theo
      vai trò, vai trò lạ, chuẩn hoá đường dẫn, ngữ nghĩa glob, danh sách bảo
      vệ, audit file ngoài phạm vi, phạm vi trống).
- [ ] `python3 tests/test_scope_parity.py` xanh: Worker và runner cho cùng
      kết quả về phạm vi, chuẩn hoá đường dẫn và danh sách bảo vệ.
- [ ] Migration `0004_orchestrator_agent.sql` đã áp lên D1 remote: đủ 4 bảng
      `code_scopes`, `agent_threads`, `agent_messages`, `code_change_requests`.
- [ ] Scheduled Task `HaviGroup Orchestrator Runner` chạy trên PC
      `100.75.125.80` với `runner/orchestrator.env` riêng; dashboard hiện
      **Runner trực tuyến**; `SELECT ... FROM runners` thấy
      `orchestrator-runner` heartbeat.
- [ ] Tắt runner → `POST /api/dashboards/:slug/agent/threads` trả **409**,
      không có dòng `code_change_requests` mới.
- [ ] Người chưa có phạm vi (không phải Owner) gửi yêu cầu → **403** kèm
      hướng dẫn xin cấp phạm vi.
- [ ] Nhắn tiếp vào thread đang có yêu cầu `queued/planning/applying` →
      **409**.
- [ ] Yêu cầu dạng câu hỏi → trạng thái `answered`, có tin nhắn agent trong
      thread, **không** có nhánh/diff nào.
- [ ] Yêu cầu sửa 1 file trong phạm vi → `awaiting_approval` với diff, danh
      sách file, log test hiển thị; Operator gửi yêu cầu bấm duyệt → **403**;
      Admin khác duyệt → `approved` → runner merge → `applied` với
      `commit_sha` khớp `git log` của `AGENT_REPO_DIR`.
- [ ] Admin tự duyệt yêu cầu của chính mình → **403**; Owner tự duyệt của
      mình → được.
- [ ] Sửa `code_scopes` **sau** khi yêu cầu đã xếp hàng → `scope_json` của
      yêu cầu không đổi, kết quả audit vẫn theo phạm vi cũ.
- [ ] Yêu cầu (giả lập qua Owner scope `**`) chạm
      `automation_center/src/worker.js` → `touches_protected = 1`; Admin
      duyệt → **403**, chỉ Owner duyệt được; không bao giờ auto-apply.
- [ ] Admin gọi `POST .../agent/scopes` với `auto_apply: true` → **403**;
      Owner bật được; phạm vi có `auto_apply`, thay đổi hợp lệ, test xanh →
      `approved` thẳng với `decided_by = 'auto'` và tin nhắn "áp thẳng"
      trong thread.
- [ ] `grep` toàn repo không thấy giá trị `OPENAI_API_KEY`,
      `RUNNER_SHARED_SECRET`, Access client secret; khoá OpenAI chỉ có trong
      `orchestrator.env` trên PC (file có ACL giới hạn).
- [ ] Audit log của dashboard ghi đủ chuỗi
      `code_request.queued → awaiting_approval/approved → applied` và
      `code_scope.saved/revoked`, không chứa secret.

## 10. Việc còn lại / giai đoạn sau

1. **Nghiệm thu đầu-cuối trên PC.** Runbook (`docs/runner-host-runbook.md`)
   đã có Scheduled Task và `orchestrator.env`, nhưng bảng trạng thái mục 1
   chưa ghi nhận orchestrator runner heartbeat/chạy thật một yêu cầu — cần
   chạy checklist mục 9 trên môi trường thật và cập nhật runbook.
2. ~~**"Điều khiển toàn bộ agent còn lại"** — chạy/dừng/tiếp tục bot tạo ảnh và
   bot ERP.~~ **Đã làm** — action `bot` của runner, status `bot_done`, nhánh
   `bot_action` trong Worker dùng chung `runBotCommand` với nút bấm trên web;
   quyền lấy từ `capability(requested_role, "run")` đã đóng băng. Còn lại của
   ý "xâu chuỗi": chưa có cách mô tả một chuỗi nhiều bước phụ thuộc nhau (chạy
   bot A xong mới chạy bot B) — mỗi lượt hiện là tối đa 5 lệnh độc lập.
3. **Khoá thread khi `awaiting_approval`** (hoặc rebase nhánh trước merge) để
   giảm xung đột giữa các yêu cầu chờ duyệt chồng lấn — xem mục 8.
4. **Watchdog cho yêu cầu kẹt** ở `planning`/`applying` khi runner chết giữa
   chừng; dọn nhánh `agent/<id>` mồ côi (sau rút lại yêu cầu muộn).
5. ~~Cảnh báo trên UI khi diff bị cắt; Worker tự tính lại số dòng.~~ **Đã làm** —
   cột `diff_truncated`, cảnh báo đỏ trên thẻ yêu cầu, số dòng lấy `max(runner
   báo, đếm trong diff)`.
6. **Đóng thread.** Schema có `agent_threads.status = 'closed'` nhưng chưa có
   endpoint/UI nào đóng thread.
7. **Đo chi phí token** theo yêu cầu và theo người gửi; hạn mức ngày nếu cần.
8. **Nút revert trên UI** cho thay đổi đã `applied` (hiện hoàn tác bằng
   `git revert` tay trên máy trung tâm).
9. ~~Đồng bộ hai danh sách bảo vệ bằng test đối chiếu.~~ **Đã làm** —
   `tests/test_scope_parity.py`.
10. ~~Làm rõ tài liệu API về quyền huỷ.~~ **Đã làm** — bảng trong
    `architecture.md` đã ghi đúng.
