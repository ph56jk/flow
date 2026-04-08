---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
  - step-12-complete
inputDocuments:
  - README.md
  - pyproject.toml
  - _bmad-output/project-context.md
  - _bmad-output/planning-artifacts/architecture.md
  - flow_web/main.py
  - flow_web/service.py
  - flow_web/store.py
  - flow_web/schemas.py
  - flow_web/messages.py
  - flow_web/paths.py
  - flow_web/static/index.html
  - flow_web/static/app.js
  - flow_web/static/styles.css
workflowType: 'prd'
documentCounts:
  briefCount: 0
  researchCount: 0
  brainstormingCount: 0
  projectDocsCount: 3
classification:
  projectType: web_app
  domain: scientific
  complexity: medium
  projectContext: brownfield
project_name: 'flow'
user_name: 'admin'
date: '2026-04-07'
---

# Product Requirements Document - flow

**Author:** admin  
**Date:** 2026-04-07

## Executive Summary

`Flow Web UI` là một ứng dụng web cục bộ bọc `flow-py` để giúp người dùng điều khiển Google Flow bằng giao diện trực quan, tiếng Việt, ít thao tác kỹ thuật. Bản hiện tại đã hỗ trợ đăng nhập, kết nối project, tạo ảnh/video, chỉnh sửa media, xem workflow, theo dõi job và tải kết quả về máy. Tuy nhiên trải nghiệm thực tế vẫn còn các điểm nghẽn: người mới dễ vướng ở bước project/login, lỗi từ browser automation còn gây bối rối, job bị ngắt sau restart chưa có đường quay lại rõ ràng, và việc tái sử dụng kết quả cũ để chỉnh sửa vẫn cần nhiều thao tác tay.

PRD này định nghĩa vòng nâng cấp tiếp theo của sản phẩm với trọng tâm: rút ngắn thời gian tới tác vụ thành công đầu tiên, giảm ngõ cụt khi lỗi, tăng khả năng tái sử dụng artifact và giữ ứng dụng đơn giản, local-first, dễ tiếp cận. Vòng này không ưu tiên mở rộng sang hệ thống preset/skill mới, không thêm frontend framework, và không biến sản phẩm thành nền tảng cộng tác nhiều người dùng.

### Người dùng mục tiêu

- Người sáng tạo nội dung dùng Google Flow nhưng không muốn thao tác hoàn toàn bằng code.
- Người vận hành local workflow cần một bảng điều khiển tiếng Việt để lặp lại các tác vụ ảnh/video nhanh hơn.
- Người dùng đã có artifact cũ và muốn chuyển ngay sang bước chỉnh sửa, kéo dài hoặc upscale mà không phải tìm tay nhiều thông tin.

### Giá trị khác biệt

- Local-first, không cần backend cloud riêng cho web app.
- Giao diện tiếng Việt, thân thiện cho người mới.
- Biến kết quả cũ thành đầu vào mới ngay trong cùng màn hình.
- Bao bọc browser automation bằng hướng dẫn và lỗi dễ hiểu thay vì để lộ thông báo kỹ thuật thô.

## Success Criteria

- SC1: Ít nhất 80% người dùng có tài khoản Google Flow hợp lệ có thể hoàn tất tác vụ tạo ảnh hoặc video đầu tiên trong vòng 5 phút kể từ lúc mở app lần đầu.
- SC2: Ít nhất 90% lỗi phát sinh từ các luồng chính hiển thị bằng tiếng Việt kèm hành động tiếp theo rõ ràng.
- SC3: Từ một artifact đã hoàn tất, người dùng có thể bắt đầu một tác vụ chỉnh sửa tiếp theo trong tối đa 2 thao tác.
- SC4: 100% job đang chạy khi server khởi động lại được hiển thị là `Bị ngắt`, không ở trạng thái mơ hồ.
- SC5: Ít nhất 90% tác vụ thường dùng được thực hiện mà không cần mở `Cài đặt nâng cao`.
- SC6: Người dùng có thể phân biệt rõ ba trạng thái: chưa sẵn sàng, sẵn sàng chạy, và cần xử lý lỗi, ngay từ màn hình chính.

## Product Scope

### Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Tập trung vào `time-to-first-success` và `time-to-next-edit`. Mục tiêu không phải thêm nhiều tính năng mới nhất, mà làm cho luồng đang có bớt gãy, bớt rối và dễ dùng lặp lại.

**Nguyên tắc scope:**

- Ưu tiên sửa các điểm nghẽn ở onboarding, theo dõi job, và tái sử dụng kết quả.
- Giữ local-first architecture hiện tại.
- Không thêm hệ thống skill/preset tương tác lại vào UI trong vòng này.
- Không thêm framework frontend hoặc queue ngoài tiến trình trong MVP.

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**

- Bắt đầu nhanh từ project hợp lệ tới lần generate đầu tiên.
- Tái chạy sau lỗi hoặc bị ngắt mà không phải nhập lại toàn bộ.
- Đi từ artifact cũ sang form chỉnh sửa đúng ngữ cảnh.
- Tải, mở và quản lý kết quả local rõ ràng.

**Must-Have Capabilities:**

- Luồng kiểm tra sẵn sàng trước khi chạy job.
- Nút chạy lại từ job lỗi hoặc bị ngắt.
- Prefill mạnh hơn từ artifact/job cũ sang form sửa.
- Trạng thái lỗi và cách khắc phục rõ ràng hơn.
- Job history dễ lọc, dễ dọn dẹp, dễ hiểu.
- Quản lý output local và đường dẫn tệp rõ hơn.

### Post-MVP Features

**Phase 2 (Growth):**

- Tìm kiếm và lọc nâng cao theo project, loại tác vụ, thời gian và trạng thái.
- Nhóm artifact theo workflow hoặc phiên làm việc.
- Batch actions cho tải về, xóa lịch sử, chạy lại.
- Bảng chẩn đoán dành cho tác vụ Flow chậm hoặc bất thường.

**Phase 3 (Expansion):**

- Worker nền bền vững hơn qua restart.
- Đồng bộ session và lịch sử giữa nhiều môi trường local tùy chọn.
- Hàng đợi tác vụ dài hơi và resume tốt hơn.
- Chế độ quản lý nhiều project với dashboard tổng hợp.

### Out of Scope for This PRD

- Hệ thống skill/preset do người dùng tự dạy trong giao diện.
- Multi-user collaboration.
- API cloud công khai cho ứng dụng web này.
- Tái cấu trúc toàn bộ frontend sang framework mới.

## User Journeys

### Journey 1: Lần đầu kết nối và chạy tác vụ đầu tiên

1. Người dùng mở app và thấy ngay ba bước cần làm.
2. Người dùng dán `project id` hoặc cả URL project.
3. Người dùng đăng nhập Google Flow qua Chromium được mở ra.
4. App xác nhận trạng thái sẵn sàng.
5. Người dùng nhập prompt đầu tiên và chạy tạo ảnh hoặc video.
6. Người dùng thấy log, trạng thái và artifact đầu ra trong cùng màn hình.

### Journey 2: Người dùng quay lại để tạo nội dung mới

1. Người dùng mở app lần sau.
2. Project, auth status và lịch sử cũ vẫn còn.
3. Người dùng chọn form tạo video hoặc ảnh.
4. Người dùng chạy tác vụ mới mà không cần cấu hình lại từ đầu.

### Journey 3: Đi từ kết quả cũ sang chỉnh sửa tiếp

1. Người dùng xem một job đã hoàn tất.
2. Người dùng chọn artifact hoặc workflow liên quan.
3. App tự điền `media id`, `workflow id` và loại sửa phù hợp.
4. Người dùng chỉ điều chỉnh vài trường cần thiết rồi chạy tiếp.

### Journey 4: Xử lý lỗi hoặc job bị ngắt

1. Người dùng thấy job thất bại hoặc bị ngắt.
2. App giải thích bằng tiếng Việt điều gì đã xảy ra.
3. Người dùng biết ngay nên đăng nhập lại, kiểm tra project, tăng timeout, hay chạy lại.
4. Người dùng có thể khởi tạo lại job từ input cũ thay vì nhập lại thủ công.

### Journey 5: Quản lý và tải kết quả local

1. Người dùng xem artifact trong timeline job.
2. Người dùng mở bản gốc hoặc lưu file về máy.
3. Người dùng phân biệt được link gốc, file local và media ID để tái sử dụng.

## Domain Requirements

Sản phẩm thuộc nhóm công cụ điều phối quy trình tạo media bằng AI, nhưng chạy như một local companion app cho browser automation. Không có ràng buộc pháp lý ngành dọc như y tế hay fintech, nhưng có các yêu cầu miền đặc thù sau:

- DR1: Hệ thống phải giữ mô hình `human-in-the-loop` cho đăng nhập Google Flow; người dùng là người trực tiếp hoàn tất xác thực.
- DR2: Hệ thống phải làm rõ đâu là lỗi từ app local, đâu là lỗi từ Google Flow, và đâu là lỗi do phiên đăng nhập hết hạn.
- DR3: Hệ thống phải cho phép người dùng tiếp tục làm việc ngay cả khi project không có workflow lưu sẵn.
- DR4: Hệ thống phải làm rõ các giới hạn của browser automation, bao gồm khả năng time out, đổi giao diện upstream và đóng trình duyệt giữa chừng.
- DR5: Hệ thống phải giữ artifact và cấu hình chính ở môi trường local của người dùng, không buộc chuyển dữ liệu qua dịch vụ ngoài của web app.

## Innovation Analysis

Sản phẩm không cạnh tranh bằng khả năng tạo media gốc, vì phần đó do Google Flow và `flow-py` đảm nhiệm. Điểm khác biệt của sản phẩm nằm ở orchestration experience:

- IA1: Biến một workflow kỹ thuật thành luồng ba bước dễ hiểu cho người mới.
- IA2: Tập trung vào `next best action` thay vì chỉ liệt kê raw controls.
- IA3: Dùng kết quả cũ làm điểm vào cho tác vụ tiếp theo ngay trong timeline job.
- IA4: Việt hóa và ngữ cảnh hóa lỗi kỹ thuật để rút ngắn vòng thử lại.
- IA5: Giữ sản phẩm nhẹ, local-first, sửa nhanh, không cần hệ sinh thái cài đặt phức tạp.

## Project-Type Requirements

Dự án được phân loại là `web_app` brownfield. Các yêu cầu loại dự án cần được duy trì:

- PTR1: Giao diện phải usable trên desktop browser hiện đại mà không cần build tool phía client.
- PTR2: Màn hình chính phải responsive ở laptop và mobile-width cơ bản, không tạo horizontal scrolling cho luồng chính.
- PTR3: Ứng dụng phải ưu tiên accessibility cơ bản: label rõ ràng, thứ tự thao tác hợp lý, trạng thái hiển thị dễ phân biệt.
- PTR4: SEO không phải mục tiêu.
- PTR5: App phải phản hồi phù hợp trong môi trường local, nơi round-trip mạng chủ yếu là tới backend cục bộ và Google Flow từ browser automation.

## Functional Requirements

### Kết Nối Project Và Phiên

- FR1: Người dùng có thể lưu project đang làm việc bằng `project id` hoặc nguyên URL project Google Flow.
- FR2: Người dùng có thể xem project nào đang được chọn làm project hiện hành.
- FR3: Người dùng có thể xem danh sách project đã lưu và kích hoạt lại một project cũ mà không cần gõ lại.
- FR4: Người dùng có thể khởi tạo luồng đăng nhập Google Flow từ app.
- FR5: Người dùng có thể xem trạng thái đăng nhập hiện tại của phiên Flow.
- FR6: Người dùng có thể tải danh sách workflow hiện có của project đang chọn.
- FR7: Người dùng có thể đặt một workflow làm mặc định cho các thao tác cần workflow.

### Tạo Nội Dung Mới

- FR8: Người dùng có thể tạo video từ prompt văn bản.
- FR9: Người dùng có thể tạo video từ một ảnh đầu vào đã tải lên.
- FR10: Người dùng có thể tạo ảnh từ prompt văn bản.
- FR11: Người dùng có thể tạo nhiều biến thể trong một lần chạy, trong giới hạn cấu hình của app.
- FR12: Người dùng có thể chọn tỉ lệ phù hợp cho loại nội dung đang tạo.
- FR13: Người dùng có thể dùng một hoặc nhiều media ID làm tham chiếu cho tác vụ tạo ảnh.

### Chỉnh Sửa Media Đã Có

- FR14: Người dùng có thể kéo dài một video đã có bằng `media id`.
- FR15: Người dùng có thể nâng chất lượng một media đã có.
- FR16: Người dùng có thể áp dụng chuyển động camera cho media đã có.
- FR17: Người dùng có thể thay đổi vị trí camera cho media đã có.
- FR18: Người dùng có thể chèn nội dung mới vào media bằng prompt và vùng thao tác.
- FR19: Người dùng có thể xóa nội dung khỏi media bằng vùng thao tác.
- FR20: Người dùng có thể bắt đầu một tác vụ chỉnh sửa từ artifact hoặc workflow của job cũ thay vì nhập tay toàn bộ.

### Theo Dõi, Phục Hồi Và Chạy Lại

- FR21: Người dùng có thể xem mọi job với trạng thái, thời gian, log và lỗi tương ứng.
- FR22: Người dùng có thể lọc job theo trạng thái `tất cả`, `đang chạy`, `hoàn tất`, `lỗi`.
- FR23: Người dùng có thể phân biệt job `lỗi` với job `bị ngắt` do server khởi động lại.
- FR24: Người dùng có thể chạy lại một job thất bại hoặc bị ngắt bằng input trước đó.
- FR25: Người dùng có thể làm mới danh sách tác vụ mà không cần tải lại toàn trang.
- FR26: Người dùng có thể dọn dẹp lịch sử job cũ mà không làm mất các file kết quả đã tải về.

### Artifact, Workflow Và Tái Sử Dụng Kết Quả

- FR27: Người dùng có thể xem preview ảnh và video trực tiếp trong timeline job.
- FR28: Người dùng có thể mở liên kết gốc hoặc bản local của một artifact.
- FR29: Người dùng có thể tải artifact về máy thông qua app.
- FR30: Người dùng có thể chép `media id` và `workflow id` từ artifact hoặc workflow đã lưu.
- FR31: Người dùng có thể dùng artifact hoàn tất như nguồn đầu vào cho tác vụ chỉnh sửa tiếp theo.

### Hướng Dẫn Và Khả Năng Tiếp Cận

- FR32: Người dùng có thể thấy app đang thiếu bước nào để sẵn sàng chạy tác vụ.
- FR33: Người dùng có thể thấy gợi ý hành động tiếp theo phù hợp với trạng thái hiện tại của app.
- FR34: Người dùng có thể hoàn tất các luồng phổ biến mà không cần mở cài đặt nâng cao.
- FR35: Người dùng có thể đọc toàn bộ thông báo hệ thống, lỗi và chỉ dẫn chính bằng tiếng Việt có dấu.

### Dữ Liệu Cục Bộ Và Vận Hành

- FR36: Người dùng có thể giữ lại cấu hình, project và lịch sử job sau khi refresh trang.
- FR37: Người dùng có thể khởi động lại app và vẫn xem được trạng thái lịch sử trước đó.
- FR38: Người dùng có thể lưu file upload và file download trong các thư mục app quản lý.
- FR39: Người dùng có thể dùng app mà không cần tạo tài khoản riêng cho web UI ngoài tài khoản Google Flow.

## Non-Functional Requirements

### Hiệu Năng Và Tương Tác

- NFR1: Trang chính phải render được nội dung khung và sẵn sàng thao tác trong dưới 2 giây ở lần tải ấm trên máy desktop hiện đại.
- NFR2: Các thao tác local như lưu config, đổi tab, lọc job và mở form phải phản hồi giao diện trong dưới 200 mili giây.
- NFR3: Sau mỗi thao tác API thành công hoặc thất bại, người dùng phải nhận được phản hồi nhìn thấy được trong dưới 1 giây kể từ khi backend trả về.

### Độ Tin Cậy Và Khả Năng Phục Hồi

- NFR4: 100% job đang ở trạng thái `queued`, `running` hoặc `polling` tại thời điểm restart phải được đánh dấu `interrupted` ở lần khởi động kế tiếp.
- NFR5: App phải giữ lại tối đa 50 job gần nhất mà không làm hỏng file state cục bộ.
- NFR6: 100% artifact đã tải local phải có đường dẫn mở được từ app hoặc thông báo lỗi rõ ràng nếu tệp không còn tồn tại.

### Trải Nghiệm Người Dùng

- NFR7: 100% lỗi hiển thị cho người dùng ở luồng chính phải có bản tiếng Việt dễ hiểu.
- NFR8: Ít nhất 90% phiên đầu tiên có thể hoàn tất mà không cần mở `Cài đặt nâng cao`.
- NFR9: Luồng chính phải usable ở viewport từ 390px trở lên mà không tạo horizontal scrolling cho các panel quan trọng.
- NFR10: Các action chính phải truy cập được bằng bàn phím theo thứ tự tab hợp lý.

### Bảo Mật Và Quyền Riêng Tư

- NFR11: App không được lưu trực tiếp thông tin đăng nhập Google thô do người dùng nhập; xác thực phải đi qua browser session của Flow.
- NFR12: Route tải file phải chỉ phục vụ tệp nằm trong thư mục download mà app quản lý.
- NFR13: File upload phải được lưu dưới tên an toàn, không cho phép path traversal.

### Khả Năng Bảo Trì

- NFR14: Logic nghiệp vụ mới phải được đặt ở service/store thay vì dồn vào route handlers.
- NFR15: Khi upstream `flow-py` hoặc Google Flow thay đổi hành vi, app phải có một điểm tập trung để chuẩn hóa lỗi và giảm tác động lên UI.
- NFR16: Mọi mở rộng kiểu job mới phải có mapping rõ ràng ở request model, title/label, render trạng thái và artifact handling.

## Assumptions

- A1: Vòng PRD này phục vụ bản nâng cấp kế tiếp của app hiện tại, không phải viết lại sản phẩm từ đầu.
- A2: Chủ nhân ưu tiên trải nghiệm dễ tiếp cận, đẹp, rõ ràng và ổn định hơn là mở rộng sang hệ thống skills/presets tương tác.
- A3: Kiến trúc local-first hiện tại vẫn được giữ ở vòng này.

## Open Questions

- OQ1: Có cần cho phép `retry` sửa lại một vài tham số trước khi chạy lại, hay chỉ cần clone nguyên input cũ?
- OQ2: Với mobile-width, có cần hỗ trợ chạy đầy đủ form chỉnh sửa phức tạp, hay chỉ cần theo dõi và thao tác cơ bản?
- OQ3: Khi dọn lịch sử job, có cần thêm cơ chế nhóm theo project hoặc theo phiên làm việc để giảm nhiễu không?

## Summary

PRD này định nghĩa vòng nâng cấp tiếp theo của `Flow Web UI` theo hướng rõ ràng: ít ngõ cụt hơn, nhanh vào việc hơn, tái sử dụng kết quả cũ tốt hơn, và vẫn giữ sản phẩm nhẹ, local-first, dễ sửa. Toàn bộ thiết kế, kiến trúc, epic và implementation tiếp theo cần bám vào các mục tiêu, user journeys, FR và NFR trong tài liệu này.
