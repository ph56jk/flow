---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/brainstorming/brainstorming-session-2026-04-07-10-14-23.md
  - _bmad-output/project-context.md
---

# flow - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for flow, decomposing the requirements from the PRD, Architecture, and the approved brainstorming session into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: Người dùng có thể lưu project đang làm việc bằng `project id` hoặc nguyên URL project Google Flow.  
FR2: Người dùng có thể xem project nào đang được chọn làm project hiện hành.  
FR3: Người dùng có thể xem danh sách project đã lưu và kích hoạt lại một project cũ mà không cần gõ lại.  
FR4: Người dùng có thể khởi tạo luồng đăng nhập Google Flow từ app.  
FR5: Người dùng có thể xem trạng thái đăng nhập hiện tại của phiên Flow.  
FR6: Người dùng có thể tải danh sách workflow hiện có của project đang chọn.  
FR7: Người dùng có thể đặt một workflow làm mặc định cho các thao tác cần workflow.  
FR8: Người dùng có thể tạo video từ prompt văn bản.  
FR9: Người dùng có thể tạo video từ một ảnh đầu vào đã tải lên.  
FR10: Người dùng có thể tạo ảnh từ prompt văn bản.  
FR11: Người dùng có thể tạo nhiều biến thể trong một lần chạy, trong giới hạn cấu hình của app.  
FR12: Người dùng có thể chọn tỉ lệ phù hợp cho loại nội dung đang tạo.  
FR13: Người dùng có thể dùng một hoặc nhiều media ID làm tham chiếu cho tác vụ tạo ảnh.  
FR14: Người dùng có thể kéo dài một video đã có bằng `media id`.  
FR15: Người dùng có thể nâng chất lượng một media đã có.  
FR16: Người dùng có thể áp dụng chuyển động camera cho media đã có.  
FR17: Người dùng có thể thay đổi vị trí camera cho media đã có.  
FR18: Người dùng có thể chèn nội dung mới vào media bằng prompt và vùng thao tác.  
FR19: Người dùng có thể xóa nội dung khỏi media bằng vùng thao tác.  
FR20: Người dùng có thể bắt đầu một tác vụ chỉnh sửa từ artifact hoặc workflow của job cũ thay vì nhập tay toàn bộ.  
FR21: Người dùng có thể xem mọi job với trạng thái, thời gian, log và lỗi tương ứng.  
FR22: Người dùng có thể lọc job theo trạng thái `tất cả`, `đang chạy`, `hoàn tất`, `lỗi`.  
FR23: Người dùng có thể phân biệt job `lỗi` với job `bị ngắt` do server khởi động lại.  
FR24: Người dùng có thể chạy lại một job thất bại hoặc bị ngắt bằng input trước đó.  
FR25: Người dùng có thể làm mới danh sách tác vụ mà không cần tải lại toàn trang.  
FR26: Người dùng có thể dọn dẹp lịch sử job cũ mà không làm mất các file kết quả đã tải về.  
FR27: Người dùng có thể xem preview ảnh và video trực tiếp trong timeline job.  
FR28: Người dùng có thể mở liên kết gốc hoặc bản local của một artifact.  
FR29: Người dùng có thể tải artifact về máy thông qua app.  
FR30: Người dùng có thể chép `media id` và `workflow id` từ artifact hoặc workflow đã lưu.  
FR31: Người dùng có thể dùng artifact hoàn tất như nguồn đầu vào cho tác vụ chỉnh sửa tiếp theo.  
FR32: Người dùng có thể thấy app đang thiếu bước nào để sẵn sàng chạy tác vụ.  
FR33: Người dùng có thể thấy gợi ý hành động tiếp theo phù hợp với trạng thái hiện tại của app.  
FR34: Người dùng có thể hoàn tất các luồng phổ biến mà không cần mở `Cài đặt nâng cao`.  
FR35: Người dùng có thể đọc toàn bộ thông báo hệ thống, lỗi và chỉ dẫn chính bằng tiếng Việt có dấu.  
FR36: Người dùng có thể giữ lại cấu hình, project và lịch sử job sau khi refresh trang.  
FR37: Người dùng có thể khởi động lại app và vẫn xem được trạng thái lịch sử trước đó.  
FR38: Người dùng có thể lưu file upload và file download trong các thư mục app quản lý.  
FR39: Người dùng có thể dùng app mà không cần tạo tài khoản riêng cho web UI ngoài tài khoản Google Flow.

### NonFunctional Requirements

NFR1: Trang chính phải render được nội dung khung và sẵn sàng thao tác trong dưới 2 giây ở lần tải ấm trên máy desktop hiện đại.  
NFR2: Các thao tác local như lưu config, đổi tab, lọc job và mở form phải phản hồi giao diện trong dưới 200 mili giây.  
NFR3: Sau mỗi thao tác API thành công hoặc thất bại, người dùng phải nhận được phản hồi nhìn thấy được trong dưới 1 giây kể từ khi backend trả về.  
NFR4: 100% job đang ở trạng thái `queued`, `running` hoặc `polling` tại thời điểm restart phải được đánh dấu `interrupted` ở lần khởi động kế tiếp.  
NFR5: App phải giữ lại tối đa 50 job gần nhất mà không làm hỏng file state cục bộ.  
NFR6: 100% artifact đã tải local phải có đường dẫn mở được từ app hoặc thông báo lỗi rõ ràng nếu tệp không còn tồn tại.  
NFR7: 100% lỗi hiển thị cho người dùng ở luồng chính phải có bản tiếng Việt dễ hiểu.  
NFR8: Ít nhất 90% phiên đầu tiên có thể hoàn tất mà không cần mở `Cài đặt nâng cao`.  
NFR9: Luồng chính phải usable ở viewport từ 390px trở lên mà không tạo horizontal scrolling cho các panel quan trọng.  
NFR10: Các action chính phải truy cập được bằng bàn phím theo thứ tự tab hợp lý.  
NFR11: App không được lưu trực tiếp thông tin đăng nhập Google thô do người dùng nhập; xác thực phải đi qua browser session của Flow.  
NFR12: Route tải file phải chỉ phục vụ tệp nằm trong thư mục download mà app quản lý.  
NFR13: File upload phải được lưu dưới tên an toàn, không cho phép path traversal.  
NFR14: Logic nghiệp vụ mới phải được đặt ở service/store thay vì dồn vào route handlers.  
NFR15: Khi upstream `flow-py` hoặc Google Flow thay đổi hành vi, app phải có một điểm tập trung để chuẩn hóa lỗi và giảm tác động lên UI.  
NFR16: Mọi mở rộng kiểu job mới phải có mapping rõ ràng ở request model, title/label, render trạng thái và artifact handling.

### Additional Requirements

- Giữ `flow_web/main.py` mỏng; logic nghiệp vụ mới phải đặt ở `flow_web/service.py` hoặc `flow_web/store.py`.
- Không phá shape hiện tại của `/api/state`; nếu bổ sung dữ liệu mới phải theo hướng tương thích ngược.
- Dùng `StateStore` và `paths.py` làm nguồn sự thật cho persistence và đường dẫn nội bộ.
- Duy trì kiến trúc local-first hiện tại: `FastAPI + static frontend + local JSON persistence`.
- Không thêm frontend framework hoặc build pipeline mới trong vòng này.
- Mọi lỗi kỹ thuật liên quan Flow phải đi qua lớp humanize lỗi trước khi lên UI.
- Tác vụ đang chạy khi restart phải chuyển sang `interrupted` và phải có đường khôi phục rõ ràng hơn.
- Không tái đưa hệ thống `skills/preset` tương tác trở lại UI ở vòng nâng cấp này.
- Không có starter template riêng; mọi thay đổi phải mở rộng trên codebase hiện tại.

### UX Design Requirements

Không có tài liệu UX Design riêng trong vòng này. Các yêu cầu UX cần triển khai được suy ra từ PRD, Architecture và brainstorming session:

- UX-DR1: Giao diện phải ưu tiên luồng ba bước rõ ràng cho người mới: project, login, create.
- UX-DR2: Các trạng thái `chưa sẵn sàng`, `sẵn sàng`, `đang chờ`, `lỗi`, `bị ngắt` phải nhìn ra ngay bằng copy và visual state.
- UX-DR3: Các action chính trên artifact và job card phải hiển thị gần ngữ cảnh sử dụng, không bắt người dùng đi tìm.
- UX-DR4: Luồng retry/recovery phải là một phần chính thức của sản phẩm, không chỉ là thông báo lỗi.
- UX-DR5: Trải nghiệm trên viewport hẹp phải vẫn usable cho luồng theo dõi, retry và reuse artifact.

### FR Coverage Map

FR1: Epic 1 - Guided Readiness and First Successful Run  
FR2: Epic 1 - Guided Readiness and First Successful Run  
FR3: Epic 1 - Guided Readiness and First Successful Run  
FR4: Epic 1 - Guided Readiness and First Successful Run  
FR5: Epic 1 - Guided Readiness and First Successful Run  
FR6: Epic 1 - Guided Readiness and First Successful Run  
FR7: Epic 1 - Guided Readiness and First Successful Run  
FR8: Epic 1 - Guided Readiness and First Successful Run  
FR9: Epic 1 - Guided Readiness and First Successful Run  
FR10: Epic 1 - Guided Readiness and First Successful Run  
FR11: Epic 1 - Guided Readiness and First Successful Run  
FR12: Epic 1 - Guided Readiness and First Successful Run  
FR13: Epic 1 - Guided Readiness and First Successful Run  
FR14: Epic 3 - Artifact Reuse and Editing Continuity  
FR15: Epic 3 - Artifact Reuse and Editing Continuity  
FR16: Epic 3 - Artifact Reuse and Editing Continuity  
FR17: Epic 3 - Artifact Reuse and Editing Continuity  
FR18: Epic 3 - Artifact Reuse and Editing Continuity  
FR19: Epic 3 - Artifact Reuse and Editing Continuity  
FR20: Epic 3 - Artifact Reuse and Editing Continuity  
FR21: Epic 2 - Guided Recovery and Safe Retry  
FR22: Epic 4 - Trust Signals, Progress Visibility, and Local Hygiene  
FR23: Epic 2 - Guided Recovery and Safe Retry  
FR24: Epic 2 - Guided Recovery and Safe Retry  
FR25: Epic 2 - Guided Recovery and Safe Retry  
FR26: Epic 4 - Trust Signals, Progress Visibility, and Local Hygiene  
FR27: Epic 3 - Artifact Reuse and Editing Continuity  
FR28: Epic 3 - Artifact Reuse and Editing Continuity  
FR29: Epic 3 - Artifact Reuse and Editing Continuity  
FR30: Epic 3 - Artifact Reuse and Editing Continuity  
FR31: Epic 3 - Artifact Reuse and Editing Continuity  
FR32: Epic 1 - Guided Readiness and First Successful Run  
FR33: Epic 4 - Trust Signals, Progress Visibility, and Local Hygiene  
FR34: Epic 1 - Guided Readiness and First Successful Run  
FR35: Epic 1 - Guided Readiness and First Successful Run  
FR36: Epic 4 - Trust Signals, Progress Visibility, and Local Hygiene  
FR37: Epic 2 - Guided Recovery and Safe Retry  
FR38: Epic 4 - Trust Signals, Progress Visibility, and Local Hygiene  
FR39: Epic 1 - Guided Readiness and First Successful Run

## Epic List

### Epic 1: Guided Readiness and First Successful Run
Người dùng có thể kết nối project, hiểu trạng thái sẵn sàng của app, và hoàn tất lần chạy đầu tiên với ít quyết định thừa hơn.
**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8, FR9, FR10, FR11, FR12, FR13, FR32, FR34, FR35, FR39.

### Epic 2: Guided Recovery and Safe Retry
Người dùng có thể hiểu lỗi, phục hồi tác vụ thất bại hoặc bị ngắt, và chạy lại công việc mà không phải nhập lại từ đầu.
**FRs covered:** FR21, FR23, FR24, FR25, FR37.

### Epic 3: Artifact Reuse and Editing Continuity
Người dùng có thể dùng kết quả vừa tạo làm đầu vào cho bước kế tiếp nhanh hơn, đặc biệt với các luồng chỉnh sửa media.
**FRs covered:** FR14, FR15, FR16, FR17, FR18, FR19, FR20, FR27, FR28, FR29, FR30, FR31.

### Epic 4: Trust Signals, Progress Visibility, and Local Hygiene
Người dùng có thể tin tưởng trạng thái hiện tại của app, hiểu rõ tiến trình chờ, và giữ workspace local gọn gàng theo thời gian.
**FRs covered:** FR22, FR26, FR33, FR36, FR38.

## Epic 1: Guided Readiness and First Successful Run

Người dùng có thể kết nối project, hiểu trạng thái sẵn sàng của app, và hoàn tất lần chạy đầu tiên với ít quyết định thừa hơn.

### Story 1.1: Chuẩn hóa project và readiness snapshot

As a người dùng mới hoặc quay lại,
I want app chuẩn hóa project input và tính readiness snapshot thống nhất,
So that tôi biết ngay workspace hiện có thể chạy hay đang thiếu bước nào.

**Requirements:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR32, FR35, NFR7, NFR14, NFR15.

**Acceptance Criteria:**

**Given** người dùng nhập `project id` hoặc URL project  
**When** lưu cấu hình  
**Then** backend lưu `project_id` đã normalize và `project_url` nhất quán  
**And** project đó xuất hiện đúng trong danh sách project đã lưu.

**Given** frontend gọi `/api/state`  
**When** app hydrate lần đầu hoặc sau refresh  
**Then** payload vẫn giữ shape hiện tại  
**And** có đủ dữ liệu để suy ra trạng thái readiness mà không làm gãy UI cũ.

**Given** trạng thái project, auth hoặc workflow thay đổi  
**When** người dùng bấm tải lại hoặc app tự refresh  
**Then** readiness snapshot được cập nhật đồng bộ  
**And** các thông báo trạng thái hiển thị bằng tiếng Việt có dấu.

### Story 1.2: Chế độ Golden Path cho lần chạy đầu tiên

As a người mới dùng app,
I want một luồng Golden Path chỉ hiển thị các bước cốt lõi,
So that tôi có thể đi từ project tới login rồi tới tác vụ đầu tiên mà không lạc trong giao diện.

**Requirements:** FR4, FR5, FR32, FR34, FR35, FR39, NFR8, NFR9, NFR10.

**Acceptance Criteria:**

**Given** người dùng chưa hoàn tất project hoặc auth  
**When** mở app  
**Then** app hiển thị rõ bước hiện tại trong luồng Golden Path  
**And** CTA chính dẫn tới hành động tiếp theo phù hợp.

**Given** một bước đã hoàn tất  
**When** state được cập nhật  
**Then** giao diện phản ánh ngay bước kế tiếp  
**And** không yêu cầu người dùng tự suy đoán trạng thái.

**Given** người dùng hoàn tất luồng phổ biến  
**When** tạo tác vụ đầu tiên  
**Then** không cần mở `Cài đặt nâng cao`  
**And** các phần phụ vẫn được giữ ngoài đường đi chính.

**Given** người dùng chỉ có phiên Google Flow hợp lệ  
**When** đi qua luồng Golden Path  
**Then** app không yêu cầu tạo hay đăng nhập thêm tài khoản riêng cho web UI  
**And** toàn bộ xác thực tiếp tục dựa trên browser session của Flow.

### Story 1.3: Mặc định theo ý định và preflight gate cho form tạo nội dung

As a người sáng tạo nội dung,
I want form tạo ảnh và video có mặc định phù hợp theo ý định và chặn submit sai điều kiện,
So that tôi tạo tác vụ nhanh hơn và giảm lỗi có thể đoán trước.

**Requirements:** FR8, FR9, FR10, FR11, FR12, FR13, FR32, FR34, NFR1, NFR2, NFR3, NFR7.

**Acceptance Criteria:**

**Given** người dùng chọn `Tạo video`, `Tạo ảnh` hoặc intent tương ứng  
**When** mở form  
**Then** app điền sẵn các giá trị mặc định hợp lý như aspect, count hoặc timeout  
**And** các giá trị đó vẫn có thể chỉnh thủ công.

**Given** thiếu điều kiện tối thiểu để chạy job  
**When** người dùng bấm submit  
**Then** app không enqueue job  
**And** hiển thị rõ điều kiện còn thiếu và cách xử lý.

**Given** input hợp lệ  
**When** người dùng submit  
**Then** tác vụ vẫn đi qua luồng backend hiện tại  
**And** không phá các khả năng create image/video đã có.

## Epic 2: Guided Recovery and Safe Retry

Người dùng có thể hiểu lỗi, phục hồi tác vụ thất bại hoặc bị ngắt, và chạy lại công việc mà không phải nhập lại từ đầu.

### Story 2.1: Phân loại lỗi và action recovery theo ngữ cảnh

As a người dùng vừa gặp lỗi,
I want mỗi job lỗi hiển thị loại lỗi và hành động recovery liên quan,
So that tôi biết nên làm gì tiếp theo thay vì tự đoán.

**Requirements:** FR21, FR23, FR25, FR35, NFR7, NFR15.

**Acceptance Criteria:**

**Given** backend nhận được lỗi từ Flow hoặc browser automation  
**When** job được đánh dấu thất bại  
**Then** lỗi được map vào nhóm rõ ràng như auth, project, timeout, browser lock, workflow  
**And** thông điệp hiển thị bằng tiếng Việt dễ hiểu.

**Given** job có nhóm lỗi đã biết  
**When** render job card  
**Then** app hiển thị các action recovery phù hợp như đăng nhập lại, kiểm tra project, tăng timeout hoặc mở lại browser  
**And** không hiển thị action không liên quan.

**Given** lỗi không map được  
**When** job thất bại  
**Then** app vẫn hiển thị fallback message an toàn  
**And** cung cấp ít nhất một hành động tiếp theo hợp lệ.

### Story 2.2: Retry từ job lỗi hoặc bị ngắt với payload clone

As a người dùng muốn chạy lại nhanh,
I want clone payload từ job lỗi hoặc bị ngắt sang một retry flow,
So that tôi có thể chạy lại tác vụ mà không phải nhập lại từ đầu.

**Requirements:** FR24, FR25, FR35, NFR2, NFR3, NFR5.

**Acceptance Criteria:**

**Given** một job có trạng thái `failed` hoặc `interrupted`  
**When** người dùng bấm `Chạy lại`  
**Then** app tạo một retry flow mới dựa trên input cũ  
**And** không sửa đổi job gốc.

**Given** payload retry được mở  
**When** người dùng điều chỉnh các trường được phép như prompt, timeout hoặc workflow  
**Then** các thay đổi chỉ áp dụng cho lần retry mới  
**And** giá trị còn lại tiếp tục được lấy từ payload clone.

**Given** người dùng xác nhận retry  
**When** enqueue job mới  
**Then** job mới được liên kết ngầm với job gốc trong UI hoặc metadata  
**And** job history vẫn phân biệt được bản gốc và bản retry.

### Story 2.3: Crash replay pack và tóm tắt interrupted work

As a người dùng quay lại sau khi app restart,
I want interrupted work được gom thành một replay pack rõ ràng,
So that tôi có thể khôi phục đà làm việc thay vì đọc log rời rạc.

**Requirements:** FR23, FR24, FR37, NFR4, NFR5, NFR14.

**Acceptance Criteria:**

**Given** server restart khi còn job đang `queued`, `running` hoặc `polling`  
**When** app khởi động lại  
**Then** các job đó được chuyển sang `interrupted`  
**And** giữ lại log cuối và input cần thiết cho recovery.

**Given** có interrupted jobs  
**When** người dùng mở bảng tác vụ hoặc recovery khu vực tương ứng  
**Then** app hiển thị danh sách interrupted work theo cụm rõ ràng  
**And** cho phép mở nhanh retry từ từng item.

**Given** người dùng phục hồi xong hoặc không cần giữ interrupted jobs nữa  
**When** dọn cleanup liên quan  
**Then** metadata có thể được làm sạch an toàn  
**And** không xóa nhầm artifact local đã tải về.

## Epic 3: Artifact Reuse and Editing Continuity

Người dùng có thể dùng kết quả vừa tạo làm đầu vào cho bước kế tiếp nhanh hơn, đặc biệt với các luồng chỉnh sửa media.

### Story 3.1: Output shelf cho artifact gần đây

As a người sáng tạo quay vòng nhiều lần,
I want một output shelf nhỏ hiển thị artifact gần đây với action rõ ràng,
So that tôi có thể mở, tải, chép mã hoặc tái sử dụng output nhanh hơn.

**Requirements:** FR27, FR28, FR29, FR30, FR33, NFR2, NFR6.

**Acceptance Criteria:**

**Given** có artifact từ các job hoàn tất gần đây  
**When** mở app hoặc refresh state  
**Then** output shelf hiển thị các artifact mới nhất với preview phù hợp ảnh hoặc video  
**And** không yêu cầu người dùng cuộn qua toàn bộ lịch sử job để tìm.

**Given** một artifact có URL gốc hoặc file local  
**When** người dùng chọn action tương ứng  
**Then** app mở đúng liên kết hoặc file local  
**And** nếu tệp local không còn, app báo lỗi rõ ràng.

**Given** người dùng cần tái sử dụng artifact  
**When** nhìn vào output shelf  
**Then** có sẵn action `Chép media id`, `Chép workflow id`, `Dùng để sửa`, `Lưu về máy`  
**And** action được đặt cạnh artifact liên quan.

### Story 3.2: Chuỗi hành động artifact-to-edit và prefill sâu cho form sửa

As a người dùng đã có output tốt,
I want đi từ artifact hoặc workflow sang form sửa với prefill sâu,
So that tôi có thể tiếp tục chỉnh sửa trong tối đa hai thao tác.

**Requirements:** FR14, FR15, FR16, FR17, FR18, FR19, FR20, FR31, NFR2, NFR14.

**Acceptance Criteria:**

**Given** một artifact hoặc workflow hợp lệ  
**When** người dùng bấm `Dùng để sửa` hoặc action tương đương  
**Then** app mở đúng form chỉnh sửa  
**And** điền sẵn `media id`, `workflow id` và các field liên quan.

**Given** loại chỉnh sửa được suy ra từ action người dùng chọn  
**When** form mở ra  
**Then** app chọn đúng `edit type` mặc định  
**And** chỉ hiển thị các trường phù hợp với loại chỉnh sửa đó.

**Given** người dùng xác nhận chạy chỉnh sửa  
**When** submit  
**Then** luồng backend hiện có cho extend, upscale, camera, insert, remove tiếp tục hoạt động  
**And** không yêu cầu nhập lại dữ liệu đã có sẵn trong artifact context.

### Story 3.3: Workflow memory cho continuation work

As a người dùng hay lặp lại kiểu continuation giống nhau,
I want app nhớ workflow và context edit gần đây,
So that các lần chỉnh tiếp theo bắt đầu nhanh hơn từ các gợi ý có căn cứ.

**Requirements:** FR6, FR7, FR20, FR30, FR31, NFR14, NFR16.

**Acceptance Criteria:**

**Given** các job chỉnh sửa hoặc generate thành công gần đây  
**When** người dùng vào form sửa  
**Then** app đề xuất workflow hoặc context gần nhất có liên quan  
**And** không biến nó thành thư viện preset riêng trong UI.

**Given** người dùng chọn một gợi ý workflow memory  
**When** áp dụng vào form  
**Then** các field liên quan được điền sẵn  
**And** người dùng vẫn có thể thay đổi hoặc bỏ qua.

**Given** workflow memory không còn hợp lệ  
**When** backend hoặc Flow không còn trả workflow đó  
**Then** app không submit mù  
**And** hiển thị hướng dẫn chọn lại workflow khả dụng.

## Epic 4: Trust Signals, Progress Visibility, and Local Hygiene

Người dùng có thể tin tưởng trạng thái hiện tại của app, hiểu rõ tiến trình chờ, và giữ workspace local gọn gàng theo thời gian.

### Story 4.1: Storyboard tiến trình cho job dài

As a người dùng đang chờ Flow phản hồi,
I want xem storyboard tiến trình của job,
So that tôi biết app còn đang làm việc hay đã mắc ở bước nào.

**Requirements:** FR21, FR22, FR25, FR33, NFR3, NFR7.

**Acceptance Criteria:**

**Given** một job đang chạy hoặc polling  
**When** người dùng xem job card  
**Then** app hiển thị các mốc tiến trình có ý nghĩa như gửi yêu cầu, chờ phản hồi, polling, lưu artifact, hoàn tất  
**And** không chỉ hiển thị một trạng thái chung chung.

**Given** backend có thêm log hoặc progress hint  
**When** job cập nhật  
**Then** storyboard phản ánh mốc mới nhất  
**And** người dùng có thể phân biệt tiến triển với đứng yên.

**Given** người dùng dùng bộ lọc trạng thái tác vụ  
**When** chọn `tất cả`, `đang chạy`, `hoàn tất` hoặc `lỗi`  
**Then** danh sách tác vụ phản ánh đúng bộ lọc đang chọn  
**And** progress storyboard vẫn hiển thị đúng cho các job còn lại trong danh sách lọc.

**Given** job kết thúc thành công hoặc lỗi  
**When** render trạng thái cuối  
**Then** storyboard dừng ở mốc tương ứng  
**And** vẫn giữ được log để người dùng tra lại.

### Story 4.2: Trust signals layer và project health timeline

As a người dùng quay lại app sau một thời gian,
I want thấy trust signals và health timeline của project,
So that tôi quyết định nhanh có nên chạy tiếp hay cần sửa môi trường trước.

**Requirements:** FR22, FR33, FR36, NFR7, NFR8, NFR9.

**Acceptance Criteria:**

**Given** app đã có dữ liệu về auth, project, workflow và artifact local  
**When** render dashboard  
**Then** app hiển thị trust signals ngắn gọn như `Project hợp lệ`, `Đăng nhập còn hiệu lực`, `Workflow có sẵn`, `Artifact local còn tồn tại`  
**And** các tín hiệu này dùng copy nhất quán.

**Given** project có lịch sử hoạt động đủ gần  
**When** người dùng mở khu health timeline  
**Then** app tóm tắt được các dấu hiệu như login ổn, timeout tăng, workflow rỗng hoặc interrupted jobs  
**And** không biến timeline thành màn hình phân tích quá kỹ thuật.

**Given** state được lưu local giữa các lần mở app  
**When** người dùng quay lại  
**Then** trust signals và health timeline vẫn có dữ liệu nền phù hợp  
**And** không buộc thiết lập lại từ đầu.

### Story 4.3: Cleanup assistant cho uploads, downloads và history

As a người vận hành app local lâu dài,
I want một cleanup assistant an toàn cho file và history,
So that workspace luôn gọn mà không làm mất output quan trọng.

**Requirements:** FR26, FR36, FR38, NFR6, NFR11, NFR12, NFR13.

**Acceptance Criteria:**

**Given** uploads, downloads và job history tăng dần theo thời gian  
**When** người dùng mở cleanup assistant  
**Then** app phân loại được file tạm, file đã tải, metadata cũ và mục có thể dọn  
**And** hiển thị rõ mục nào an toàn để xóa.

**Given** người dùng xác nhận dọn một nhóm dữ liệu  
**When** cleanup chạy  
**Then** app chỉ xóa những mục thuộc phạm vi cho phép  
**And** không vi phạm các rào chắn path an toàn hiện có.

**Given** artifact local vẫn đang được tham chiếu là quan trọng hoặc gần đây  
**When** cleanup assistant đề xuất dọn  
**Then** mục đó phải được giữ lại mặc định hoặc yêu cầu xác nhận rõ ràng hơn  
**And** job history có thể được làm gọn mà không xóa nhầm file người dùng cần.
