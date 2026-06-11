# CHƯƠNG 3. TRIỂN KHAI HỆ THỐNG

Chương này trình bày quá trình xây dựng các chức năng chính của hệ thống quản trị tri thức doanh nghiệp ứng dụng Retrieval-Augmented Generation. Cách trình bày tập trung theo từng chức năng nghiệp vụ, làm rõ dữ liệu đầu vào, quy trình xử lý, các bước triển khai trong hệ thống và kết quả đầu ra. Trước khi đi vào từng chức năng, chương xác định các bài toán kỹ thuật trọng tâm và cách chúng được giải quyết trong hệ thống; qua đó làm rõ những điểm khác biệt so với một hệ thống hỏi đáp tài liệu chỉ sử dụng quy trình RAG cơ bản.

## 3.1. Các bài toán kỹ thuật trọng tâm và giải pháp triển khai

Hệ thống sử dụng các mô hình, thuật toán và nền tảng như BGE-M3, BM25, Qdrant, RAPTOR, Qwen, Django và Celery. Vấn đề trọng tâm không nằm ở việc sử dụng riêng lẻ từng công nghệ, mà ở cách tổ chức và phối hợp chúng thành một quy trình thống nhất, có khả năng xử lý tài liệu đa cấu trúc, lựa chọn phương pháp truy xuất theo câu hỏi, kiểm chứng nguồn và tuân thủ quyền truy cập dữ liệu.

### 3.1.1. Xử lý tài liệu đa định dạng và bảo toàn cấu trúc

Đề tài xây dựng một pipeline thống nhất để tiếp nhận và lập chỉ mục PDF, DOC, DOCX, PPTX, XLS, XLSX, CSV, TXT và Markdown. Khác với cách chỉ đọc toàn bộ file thành văn bản phẳng, pipeline giữ lại thông tin trang, heading, block, bảng, sheet, hàng và cột để phục vụ truy xuất và trích dẫn.

Các điểm triển khai nổi bật:

- Chuẩn hóa file, MIME type, phạm vi truy cập và trạng thái xử lý.
- Parse theo từng định dạng nhưng đưa về biểu diễn page-aware và structured document thống nhất.
- Áp dụng chiến lược chunking riêng cho tài liệu văn bản và bảng tính.
- Tạo embedding theo batch và đồng bộ dữ liệu giữa PostgreSQL với Qdrant.
- Trích xuất hình ảnh, chạy OCR, sinh caption và lập chỉ mục nội dung ảnh.
- Tách base indexing khỏi asset/RAPTOR indexing để tài liệu sớm có thể sử dụng.
- Hỗ trợ xử lý nền bằng Celery và fallback khi hàng đợi không khả dụng.

Quy trình này được trình bày chi tiết tại mục 3.4 về tải lên và xử lý tài liệu.

### 3.1.2. Truy xuất thích ứng theo loại câu hỏi

Đề tài không sử dụng một phương pháp tìm kiếm duy nhất cho mọi truy vấn. Hệ thống phân tích ý định và lựa chọn chiến lược phù hợp với đặc điểm câu hỏi:

- Truy xuất trực tiếp đối với bảng, heading, section và hình ảnh được chỉ định rõ.
- Truy xuất riêng theo sheet, hàng, cột hoặc ô đối với spreadsheet.
- Kết hợp BM25, tìm kiếm vector và asset search đối với câu hỏi tổng quát.
- Sử dụng RAPTOR đối với câu hỏi rộng trên tài liệu dài.
- Mở rộng truy vấn, nối chunk liên tiếp, loại trùng, rerank và kiểm tra lại mức liên quan khi cần.
- Nhận biết phiên bản tài liệu và mở rộng phạm vi khi câu hỏi đề cập lịch sử hoặc nội dung sửa đổi.

Điểm cốt lõi là hệ thống lựa chọn đường truy xuất theo câu hỏi, thay vì luôn lấy top-K vector giống nhau. Cơ chế này được trình bày chi tiết tại mục 3.6 về chat hỏi đáp bằng RAG.

### 3.1.3. Bảo đảm câu trả lời có căn cứ và có thể kiểm chứng

Đề tài xây dựng lớp hậu xử lý để liên kết câu trả lời với dữ liệu nguồn. Mỗi nguồn được đánh số và chứa metadata như tên tài liệu, trang, sheet, hàng, chunk, phiên bản hoặc vị trí hình ảnh. Sau khi sinh câu trả lời, hệ thống kiểm tra grounding, tạo citation payload và lưu cùng lịch sử hội thoại.

Kết quả đầu ra không chỉ là đoạn văn do LLM sinh ra mà còn gồm:

- Tên tài liệu nguồn.
- Trang, sheet, hàng hoặc vị trí liên quan.
- Đoạn trích hỗ trợ câu trả lời.
- Liên kết tới chunk hoặc asset.
- Thông tin grounding và mức độ bao phủ nguồn.

Cơ chế này giúp người dùng kiểm tra lại thông tin và giảm rủi ro chấp nhận câu trả lời không có bằng chứng.

### 3.1.4. Kiểm soát quyền xuyên suốt pipeline RAG

Đề tài kết hợp quyền chức năng và quyền dữ liệu trong cùng quy trình:

- JWT xác thực người gửi yêu cầu.
- RBAC kiểm tra người dùng có được upload, đọc tài liệu hoặc truy vấn RAG hay không.
- ACL kiểm soát quyền trên từng thư mục và tài liệu.
- Phạm vi `personal`, `department`, `company` xác định phạm vi tổ chức.
- Danh sách tài liệu được lọc theo quyền trước khi tìm kiếm.
- Qdrant và BM25 chỉ truy xuất trong tập document ID đã được phép.
- Chỉ các chunk hợp lệ mới được đưa vào prompt của LLM.

Như vậy, quyền truy cập không chỉ được kiểm tra tại giao diện hoặc API tải file, mà được duy trì đến tận bước xây dựng ngữ cảnh RAG.

### 3.1.5. Giá trị kỹ thuật nổi bật của hệ thống

Các chức năng quản lý người dùng, phòng ban, thư mục, hội thoại, phiên bản và audit log tạo thành nền tảng vận hành trong bối cảnh doanh nghiệp. Trên nền tảng đó, giá trị kỹ thuật nổi bật của hệ thống được thể hiện qua ba khả năng:

1. Chuyển tài liệu đa cấu trúc thành kho tri thức có thể truy xuất.
2. Lựa chọn và phối hợp nhiều chiến lược retrieval theo loại câu hỏi.
3. Bảo đảm câu trả lời đúng phạm vi quyền và có nguồn kiểm chứng.
Nhóm hội thoại AI: conversations, conversations_attached_documents, conversations_attached_folders, messages, human_feedback.
Ma trận sau tổng hợp mối liên hệ giữa bài toán đặt ra, giải pháp được triển khai và kết quả đạt được.

| Bài toán kỹ thuật | Giải pháp triển khai | Kết quả đạt được |
| --- | --- | --- |
| Pipeline tài liệu đa cấu trúc | Page-aware parser, structured parser, text/spreadsheet chunker, embedding, asset pipeline, Celery | Tài liệu được lập chỉ mục theo trang, bảng, sheet và hình ảnh; trạng thái xử lý được theo dõi. |
| Truy xuất thích ứng | Query intent, deterministic retrieval, BM25, Qdrant, spreadsheet retriever, RAPTOR, reranker | Hệ thống chọn cách tìm kiếm phù hợp thay vì áp dụng một chiến lược cố định. |
| Grounding và citation | Numbered context, grounding verification, citation payload, source viewer | Câu trả lời có nguồn tới tài liệu, trang, sheet, chunk hoặc ảnh. |
| Kiểm soát truy cập | JWT, RBAC, ACL, document scope filtering | Tài liệu ngoài quyền không được đưa vào retrieval và prompt. |

Các mục tiếp theo trình bày chi tiết cách những giải pháp trên được hiện thực hóa trong từng chức năng của hệ thống.

## 3.2. Xây dựng chức năng quản lý người dùng và phân quyền

Chức năng quản lý người dùng được xây dựng nhằm kiểm soát việc truy cập hệ thống, phân quyền thao tác và giới hạn phạm vi dữ liệu mà từng người dùng được phép khai thác. Đây là chức năng nền tảng, vì mọi thao tác liên quan đến tài liệu và chat RAG đều phải dựa trên thông tin tài khoản, vai trò, quyền chức năng, phòng ban và quyền truy cập tài liệu.

Chức năng được triển khai trên kiến trúc web API với backend Django REST Framework và frontend Next.js/React. Backend chịu trách nhiệm xác thực, kiểm tra trạng thái tài khoản, sinh token, kiểm tra quyền và ghi nhật ký kiểm toán. Frontend sử dụng thông tin quyền trả về sau đăng nhập để hiển thị menu, nút thao tác và các màn hình phù hợp với từng người dùng.

Quy trình xử lý tổng thể:

- Thu thập thông tin đăng nhập:
  - Nhận email hoặc username từ người dùng.
  - Nhận mật khẩu.
  - Gửi thông tin đăng nhập đến API xác thực.
- Xác thực tài khoản:
  - Tìm tài khoản theo email hoặc username.
  - Kiểm tra tài khoản có tồn tại hay không.
  - Kiểm tra tài khoản có bị khóa, inactive hoặc bị xóa mềm hay không.
  - Kiểm tra mật khẩu bằng cơ chế hash của Django.
- Sinh phiên đăng nhập:
  - Sinh access token và refresh token theo chuẩn JWT.
  - Trả về thông tin người dùng, phòng ban, vai trò và danh sách quyền.
  - Cập nhật thời điểm đăng nhập gần nhất.
- Kiểm soát thao tác:
  - Mỗi API kiểm tra quyền tương ứng trước khi xử lý.
  - Với chức năng tài liệu, hệ thống kiểm tra thêm quyền trên thư mục hoặc tài liệu cụ thể.
  - Với chức năng chat, hệ thống kiểm tra người dùng có quyền gửi tin nhắn và truy vấn RAG.
- Ghi nhật ký:
  - Các thao tác quan trọng như đăng nhập, đăng xuất, tạo người dùng, thay đổi trạng thái, gán quyền, upload tài liệu và truy vấn chat được ghi vào audit log.

### 3.2.1. Mô hình dữ liệu tài khoản người dùng

Hệ thống tách dữ liệu đăng nhập và dữ liệu hồ sơ người dùng thành hai nhóm riêng. Bảng `accounts` lưu thông tin phục vụ xác thực, còn bảng `users` lưu hồ sơ cá nhân và phòng ban. Cách tách này giúp hệ thống quản lý bảo mật tài khoản độc lập với thông tin nhân sự.

Bảng 3.1. Các trường dữ liệu chính của tài khoản người dùng

| STT | Trường dữ liệu | Mô tả |
| --- | --- | --- |
| 1 | `id` | Định danh UUID của tài khoản. |
| 2 | `username` | Tên đăng nhập của người dùng. |
| 3 | `email` | Email dùng để đăng nhập hoặc nhận thông báo reset mật khẩu. |
| 4 | `password` | Mật khẩu đã được hash bằng cơ chế của Django. |
| 5 | `status` | Trạng thái tài khoản gồm `active`, `blocked`, `inactive`. |
| 6 | `is_deleted` | Cờ xóa mềm, dùng để ẩn tài khoản mà không xóa vật lý khỏi cơ sở dữ liệu. |
| 7 | `deleted_at` | Thời điểm tài khoản bị xóa mềm. |
| 8 | `last_login_at` | Thời điểm đăng nhập gần nhất. |
| 9 | `created_at`, `updated_at` | Thời điểm tạo và cập nhật tài khoản. |

Bảng 3.2. Các trường dữ liệu chính của hồ sơ người dùng

| STT | Trường dữ liệu | Mô tả |
| --- | --- | --- |
| 1 | `id` | Định danh UUID của hồ sơ. |
| 2 | `account` | Liên kết một-một tới tài khoản đăng nhập. |
| 3 | `full_name` | Họ tên đầy đủ của người dùng. |
| 4 | `avatar_url` | Đường dẫn ảnh đại diện. |
| 5 | `department` | Phòng ban mà người dùng thuộc về. |
| 6 | `address` | Địa chỉ liên hệ. |
| 7 | `birthday` | Ngày sinh. |
| 8 | `metadata` | Dữ liệu mở rộng như số điện thoại hoặc thông tin bổ sung. |

Trong đó:

- `Account` tập trung vào xác thực và trạng thái đăng nhập.
- `UserProfile` tập trung vào thông tin nhân sự.
- `Department` giúp hệ thống xác định phạm vi quản lý và phạm vi tài liệu theo tổ chức.

### 3.2.2. Đăng nhập và xác thực bằng JWT

Khi người dùng đăng nhập, frontend gửi request đến endpoint:

```text
POST /api/v1/auth/login
```

Dữ liệu gửi lên gồm:

```json
{
  "email": "user@example.com",
  "username": "user",
  "password": "********"
}
```

Backend xử lý đăng nhập thông qua `UserLoginView` và `UserService.authenticate`. Quy trình xử lý:

- Bước 1: Kiểm tra email/username và mật khẩu không được bỏ trống.
- Bước 2: Tìm tài khoản theo email hoặc username.
- Bước 3: Nếu tài khoản không tồn tại, hệ thống trả lỗi thông tin đăng nhập không chính xác.
- Bước 4: Nếu tài khoản có trạng thái `blocked`, hệ thống từ chối đăng nhập và yêu cầu liên hệ quản trị viên.
- Bước 5: Nếu tài khoản có trạng thái `inactive` hoặc `is_active=false`, hệ thống từ chối đăng nhập.
- Bước 6: Kiểm tra mật khẩu với password hash đã lưu.
- Bước 7: Nếu hợp lệ, hệ thống sinh refresh token và access token.
- Bước 8: Hệ thống lấy danh sách vai trò và quyền của người dùng.
- Bước 9: Hệ thống lấy phòng ban từ hồ sơ người dùng.
- Bước 10: Hệ thống cập nhật thời điểm đăng nhập và ghi audit log.

Kết quả trả về cho frontend gồm:

```json
{
  "user": {
    "id": "uuid",
    "username": "user",
    "email": "user@example.com"
  },
  "access_token": "...",
  "refresh_token": "...",
  "permissions": ["document_read", "chat_send", "rag_query"],
  "roles": [
    {
      "id": "uuid",
      "code": "user",
      "name": "Regular User"
    }
  ],
  "department_id": "uuid"
}
```

Thông tin `permissions` được frontend dùng để quyết định người dùng có được xem trang quản trị, upload tài liệu, tạo thư mục, quản lý người dùng hoặc sử dụng chat RAG hay không.

### 3.2.3. Làm mới token và đăng xuất

Access token có thời hạn ngắn nên hệ thống cung cấp API làm mới token:

```text
POST /api/v1/auth/refresh
```

Khi làm mới token, backend không chỉ sinh token mới mà còn kiểm tra lại trạng thái tài khoản. Nếu tài khoản đã bị khóa, xóa mềm hoặc chuyển sang inactive sau lần đăng nhập trước, request sẽ bị từ chối. Điều này giúp quản trị viên có thể thu hồi quyền truy cập bằng cách đổi trạng thái tài khoản.

Đăng xuất được thực hiện qua endpoint:

```text
POST /api/v1/auth/logout
```

Khi đăng xuất, hệ thống ghi hành động `LOGOUT` vào bảng audit log. Trong triển khai hiện tại, client ngừng sử dụng token và refresh token sẽ hết hạn theo thời gian cấu hình.

### 3.2.4. Quản lý vai trò và quyền

Hệ thống sử dụng mô hình Role-Based Access Control. Người dùng không được cấp quyền trực tiếp cho từng API, mà được gán một hoặc nhiều vai trò. Mỗi vai trò chứa tập quyền tương ứng.

Bảng 3.3. Các bảng dữ liệu phục vụ phân quyền

| STT | Bảng dữ liệu | Vai trò |
| --- | --- | --- |
| 1 | `roles` | Lưu thông tin vai trò như admin, manager, user. |
| 2 | `permissions` | Lưu mã quyền chi tiết theo dạng `{resource}_{action}`. |
| 3 | `account_roles` | Liên kết tài khoản với vai trò. |
| 4 | `role_permissions` | Liên kết vai trò với quyền. |

Bảng 3.4. Một số nhóm quyền chính trong hệ thống

| STT | Nhóm quyền | Mã quyền tiêu biểu | Ý nghĩa |
| --- | --- | --- | --- |
| 1 | Người dùng | `user_create`, `user_read`, `user_update`, `user_delete` | Quản lý tài khoản và hồ sơ người dùng. |
| 2 | Vai trò | `role_manage`, `permission_manage` | Quản lý vai trò và quyền trong hệ thống. |
| 3 | Phòng ban | `department_read`, `department_manage` | Xem và quản lý cây phòng ban. |
| 4 | Thư mục | `folder_create`, `folder_read`, `folder_update`, `folder_delete` | Quản lý thư mục tài liệu. |
| 5 | Tài liệu | `document_create`, `document_read`, `document_update`, `document_delete`, `document_share` | Upload, xem, cập nhật, xóa và chia sẻ tài liệu. |
| 6 | RAG/AI | `rag_query`, `embedding_generate` | Truy vấn RAG và tạo embedding. |
| 7 | Chat | `chat_create`, `chat_read`, `chat_send` | Tạo hội thoại, xem hội thoại và gửi câu hỏi. |
| 8 | Kiểm toán | `audit_log_view`, `system_admin` | Xem nhật ký và quản trị toàn hệ thống. |

Quy trình gán quyền:

- Quản trị viên tạo hoặc chọn vai trò.
- Quản trị viên gán các permission cho vai trò.
- Quản trị viên gán vai trò cho tài khoản.
- Khi người dùng gọi API, backend lấy quyền từ các vai trò đang hoạt động.
- Nếu người dùng có quyền cần thiết, request được xử lý; ngược lại trả về lỗi 403.

### 3.2.5. Quản lý tài khoản bởi quản trị viên

Các API quản lý tài khoản được triển khai để admin hoặc người có quyền phù hợp có thể quản lý người dùng trong hệ thống.

Các chức năng chính:

- Xem danh sách người dùng có phân trang, tìm kiếm và lọc.
- Tạo tài khoản mới.
- Tạo hàng loạt tài khoản.
- Xem chi tiết tài khoản.
- Cập nhật thông tin tài khoản.
- Khóa hoặc mở khóa tài khoản.
- Gán hoặc thu hồi vai trò.
- Chuyển phòng ban cho tài khoản.
- Xóa mềm tài khoản.

Các endpoint tiêu biểu:

```text
GET    /api/v1/accounts
POST   /api/v1/accounts/create
POST   /api/v1/accounts/bulk-create
GET    /api/v1/accounts/{account_id}
DELETE /api/v1/accounts/{account_id}
POST   /api/v1/accounts/{account_id}/change-status
GET    /api/v1/accounts/{account_id}/roles
POST   /api/v1/accounts/{account_id}/roles
DELETE /api/v1/accounts/{account_id}/roles/{role_id}
PATCH  /api/v1/accounts/{account_id}/department
```

Khi xóa tài khoản, hệ thống không xóa vật lý mà cập nhật `is_deleted=true` và `deleted_at`. Hồ sơ người dùng liên quan cũng được xóa mềm. Cách làm này giúp bảo toàn lịch sử audit log, lịch sử upload và lịch sử hội thoại.

### 3.2.6. Quản lý phòng ban

Phòng ban được lưu bằng model `Department` với cấu trúc cây. Mỗi phòng ban có thể có phòng ban cha, quản lý chính và nhiều quản lý bổ sung.

Các chức năng chính:

- Tạo phòng ban.
- Cập nhật thông tin phòng ban.
- Xóa mềm phòng ban.
- Xem cây phòng ban.
- Xem người dùng trong phòng ban.
- Xem thư mục và tài liệu thuộc phòng ban.

Các endpoint tiêu biểu:

```text
GET/POST /api/v1/departments
GET/PUT/DELETE /api/v1/departments/{dept_id}
GET /api/v1/departments/{dept_id}/users
GET /api/v1/departments/{dept_id}/folders
GET /api/v1/departments/{dept_id}/documents
```

Phòng ban được sử dụng trong kiểm soát tài liệu. Khi tài liệu có `access_scope=department`, hệ thống dùng `department_id` để xác định người dùng nào có khả năng truy cập hoặc quản lý tài liệu đó.

### 3.2.7. Nhật ký kiểm toán

Nhật ký kiểm toán được triển khai bằng bảng `audit_logs`. Hệ thống ghi lại các thao tác quan trọng như đăng nhập, đăng xuất, tạo người dùng, thay đổi quyền, upload tài liệu, tải xuống tài liệu, truy vấn chat và gửi feedback.

Bảng 3.5. Các trường dữ liệu chính của audit log

| STT | Trường dữ liệu | Mô tả |
| --- | --- | --- |
| 1 | `account` | Người thực hiện hành động. |
| 2 | `action` | Loại hành động như `LOGIN`, `DOCUMENT_UPLOAD`, `QUERY`. |
| 3 | `resource_id` | Tài nguyên liên quan, ví dụ document id hoặc user id. |
| 4 | `query_text` | Nội dung truy vấn nếu hành động là chat hoặc tìm kiếm. |
| 5 | `ip_address` | Địa chỉ IP của client. |
| 6 | `user_agent` | Thông tin trình duyệt hoặc thiết bị. |
| 7 | `created_at` | Thời điểm ghi nhận hành động. |

Nhật ký kiểm toán giúp hệ thống truy vết khi xảy ra lỗi nghiệp vụ, kiểm tra hành vi bất thường và hỗ trợ yêu cầu quản trị trong môi trường doanh nghiệp.

## 3.3. Xây dựng chức năng quản lý thư mục và phạm vi truy cập tài liệu

Chức năng quản lý thư mục được xây dựng để tổ chức tài liệu theo cây thư mục và phân loại tài liệu theo phạm vi truy cập. Đây là lớp trung gian giữa người dùng và tài liệu, giúp hệ thống kiểm soát tài liệu nào thuộc cá nhân, phòng ban hoặc toàn công ty.

Quy trình xử lý tổng thể:

- Tạo cấu trúc thư mục:
  - Người dùng có quyền tạo thư mục nhập tên, mô tả, thư mục cha và phạm vi truy cập.
  - Backend kiểm tra quyền và lưu thư mục vào PostgreSQL.
- Gắn thư mục với phòng ban:
  - Nếu thư mục thuộc phòng ban, hệ thống lưu `department_id`.
  - Nếu thư mục thuộc toàn công ty hoặc cá nhân, `department_id` có thể để trống.
- Kiểm soát quyền:
  - Hệ thống kiểm tra quyền chức năng như `folder_read`, `folder_create`, `folder_update`.
  - Hệ thống kiểm tra thêm ACL trên folder nếu thao tác cần đọc, ghi hoặc xóa.
- Kế thừa sang tài liệu:
  - Tài liệu được upload vào thư mục sẽ chịu ảnh hưởng bởi phạm vi truy cập của thư mục.
  - Tài liệu có thể được cấp ACL riêng để override hoặc deny.

### 3.3.1. Mô hình dữ liệu thư mục

Bảng 3.6. Các trường dữ liệu chính của thư mục

| STT | Trường dữ liệu | Mô tả |
| --- | --- | --- |
| 1 | `id` | Định danh UUID của thư mục. |
| 2 | `name` | Tên thư mục. |
| 3 | `parent` | Thư mục cha, dùng để tạo cây thư mục nhiều cấp. |
| 4 | `department` | Phòng ban liên kết nếu thư mục thuộc phạm vi phòng ban. |
| 5 | `access_scope` | Phạm vi truy cập gồm `personal`, `department`, `company`. |
| 6 | `description` | Mô tả thư mục. |
| 7 | `metadata` | Dữ liệu mở rộng. |
| 8 | `created_by` | Người tạo thư mục. |

### 3.3.2. Phạm vi truy cập

Hệ thống sử dụng ba phạm vi truy cập:

- `personal`: tài liệu hoặc thư mục cá nhân.
- `department`: tài liệu hoặc thư mục thuộc phòng ban.
- `company`: tài liệu hoặc thư mục dùng chung toàn công ty.

Bảng 3.7. Ý nghĩa các phạm vi truy cập

| STT | Phạm vi | Ý nghĩa | Ví dụ sử dụng |
| --- | --- | --- | --- |
| 1 | `personal` | Chỉ người sở hữu hoặc người được chia sẻ có thể truy cập. | Tài liệu ghi chú cá nhân. |
| 2 | `department` | Tài liệu thuộc một phòng ban cụ thể. | Quy trình nội bộ của phòng Kế toán. |
| 3 | `company` | Tài liệu dùng chung toàn doanh nghiệp. | Nội quy công ty, quy chế chung. |

Phạm vi truy cập không thay thế hoàn toàn quyền chi tiết. Một tài liệu có phạm vi company vẫn cần người dùng có quyền đọc tài liệu. Ngược lại, một tài liệu department có thể được chia sẻ riêng cho người ngoài phòng ban thông qua ACL.

### 3.3.3. Quyền trên thư mục và tài liệu

Hệ thống triển khai ACL bằng hai bảng:

- `folder_permissions`: quyền trên thư mục.
- `document_permissions`: quyền trên tài liệu.

Quyền có thể cấp cho:

- Một tài khoản cụ thể.
- Một vai trò cụ thể.

Các mức quyền gồm:

| STT | Mức quyền | Ý nghĩa |
| --- | --- | --- |
| 1 | `read` | Được xem thư mục hoặc tài liệu. |
| 2 | `write` | Được cập nhật hoặc upload vào thư mục. |
| 3 | `delete` | Được xóa hoặc có toàn quyền với tài nguyên. |
| 4 | `deny` | Từ chối truy cập rõ ràng đối với tài liệu. |

Khi người dùng upload tài liệu vào thư mục, backend kiểm tra người dùng có quyền `write` trên thư mục đó. Khi người dùng chat với tài liệu, backend chỉ đưa vào truy xuất các tài liệu mà người dùng có quyền đọc.

## 3.4. Xây dựng chức năng tải lên và xử lý tài liệu

Chức năng tải lên tài liệu là chức năng cốt lõi của hệ thống vì đây là điểm bắt đầu để biến tài liệu nội bộ thành dữ liệu có thể tìm kiếm và hỏi đáp. Tài liệu sau khi upload không chỉ được lưu file mà còn đi qua nhiều giai đoạn xử lý gồm kiểm tra file, xác định phạm vi truy cập, lưu bản ghi tài liệu, trích xuất văn bản, chia chunk, tạo embedding, lưu vector vào Qdrant, xử lý ảnh và cập nhật trạng thái.

> **Điểm kỹ thuật trọng tâm:** quá trình tải lên không dừng ở việc lưu file mà thực hiện một luồng ingest thống nhất cho nhiều định dạng, bảo toàn cấu trúc trang, bảng và sheet, áp dụng chunking theo loại tài liệu, đồng bộ PostgreSQL với Qdrant và tách các tác vụ nặng sang xử lý nền. Kết quả của quy trình là dữ liệu tri thức có thể truy xuất và trích dẫn.

Chức năng được xây dựng dựa trên web API `POST /api/v1/documents/upload`, frontend gửi dữ liệu dạng `multipart/form-data`, backend xử lý bằng `DocumentUploadView`, `DocumentUploadService` và `DocumentIngestPipeline`.

Quy trình xử lý tổng thể:

- Thu thập dữ liệu upload:
  - Nhận file tài liệu từ người dùng.
  - Nhận thư mục đích nếu có.
  - Nhận phòng ban nếu tài liệu thuộc phạm vi phòng ban.
  - Nhận phạm vi truy cập gồm cá nhân, phòng ban hoặc toàn công ty.
  - Nhận mô tả và tag.
- Kiểm tra dữ liệu:
  - Kiểm tra người dùng đã đăng nhập.
  - Kiểm tra quyền `document_create`.
  - Kiểm tra quyền ghi vào thư mục nếu người dùng chọn thư mục.
  - Kiểm tra dung lượng file và định dạng file.
  - Kiểm tra sự tương thích giữa folder, department và access scope.
- Lưu tài liệu:
  - Hash nội dung file để tạo tên lưu trữ.
  - Lưu file vào thư mục media.
  - Tạo bản ghi `Document` với trạng thái `pending`.
- Xử lý tài liệu:
  - Chuyển trạng thái sang `processing`.
  - Parse tài liệu theo định dạng file.
  - Xây dựng cấu trúc trang, heading, bảng và block.
  - Chia tài liệu thành chunk.
  - Tạo embedding cho từng chunk.
  - Lưu chunk vào PostgreSQL và vector vào Qdrant.
- Xử lý nâng cao:
  - Trích xuất ảnh, OCR và sinh caption nếu asset pipeline được bật.
  - Xây dựng RAPTOR tree nếu tài liệu đủ dài.
  - Cập nhật trạng thái tài liệu thành `completed` hoặc `failed`.

### 3.4.1. Giao diện tải tài liệu

Frontend cung cấp modal upload tài liệu. Người dùng có thể chọn file hoặc kéo thả file vào vùng upload. Giao diện cho phép nhập các thông tin sau:

Bảng 3.8. Các trường dữ liệu người dùng nhập khi upload

| STT | Trường dữ liệu | Mô tả |
| --- | --- | --- |
| 1 | `file` | File tài liệu cần upload. |
| 2 | `access_scope` | Phạm vi truy cập: cá nhân, phòng ban hoặc công ty. |
| 3 | `department_id` | Phòng ban của tài liệu nếu scope là department. |
| 4 | `folder_id` | Thư mục đích chứa tài liệu. |
| 5 | `description` | Mô tả ngắn về tài liệu. |
| 6 | `tags` | Danh sách tag phân tách bằng dấu phẩy. |

Frontend kiểm tra sơ bộ trước khi gửi request:

- File không được bỏ trống.
- File không vượt quá giới hạn dung lượng cấu hình.
- Nếu chọn folder personal thì tài liệu phải có scope personal.
- Nếu chọn folder department thì tài liệu không được có scope company.
- Nếu chọn scope department thì phải có department hợp lệ.

Sau khi hợp lệ, frontend tạo `FormData` và gửi request bằng `XMLHttpRequest` để có thể theo dõi tiến trình upload.

### 3.4.2. API tiếp nhận file upload

Backend tiếp nhận file tại endpoint:

```text
POST /api/v1/documents/upload
```

`DocumentUploadView` thực hiện các bước:

- Kiểm tra quyền `document_create`.
- Dùng `DocumentUploadSerializer` để kiểm tra request.
- Lấy file và metadata từ request.
- Nếu người dùng không chỉ định folder và access scope, hệ thống tự xác định scope mặc định.
- Nếu có folder, kiểm tra quyền `write` trên folder.
- Gọi `DocumentUploadService.upload`.
- Ghi audit log `DOCUMENT_UPLOAD`.
- Trả về thông tin tài liệu vừa tạo.

Kết quả trả về gồm:

```json
{
  "id": "document_uuid",
  "original_name": "quy_che_noi_bo.pdf",
  "status": "pending",
  "file_size": 123456,
  "access_scope": "department",
  "department": "department_uuid",
  "folder": "folder_uuid",
  "chunk_count": 0,
  "metadata": {}
}
```

Tùy cấu hình xử lý đồng bộ hay bất đồng bộ, trạng thái trả về có thể là `pending`, `processing` hoặc `completed`.

### 3.4.3. Kiểm tra định dạng và dung lượng file

Trong `DocumentUploadService`, bước đầu tiên là kiểm tra file. Hệ thống đọc file một lần thành bytes, sau đó kiểm tra dung lượng và MIME type.

Các định dạng hỗ trợ:

| STT | Định dạng | Phần mở rộng |
| --- | --- | --- |
| 1 | PDF | `.pdf` |
| 2 | Word | `.doc`, `.docx` |
| 3 | PowerPoint | `.pptx` |
| 4 | Text | `.txt`, `.md` |
| 5 | Spreadsheet | `.xlsx`, `.xls`, `.csv` |

Nếu trình duyệt gửi MIME type không rõ ràng, hệ thống suy luận lại dựa trên phần mở rộng. Nếu file không thuộc danh sách cho phép, backend trả lỗi validation. Nếu file vượt quá giới hạn dung lượng, backend trả lỗi file quá lớn.

### 3.4.4. Xác định phạm vi tài liệu

Sau khi file hợp lệ, hệ thống xác định phạm vi lưu trữ bằng hàm `_resolve_scope`. Đây là bước quan trọng vì kết quả của nó quyết định tài liệu thuộc cá nhân, phòng ban hay toàn công ty.

Các luật nghiệp vụ:

- Nếu tài liệu được upload vào folder personal, tài liệu bắt buộc phải có `access_scope=personal`.
- Nếu tài liệu được upload vào folder department, tài liệu chỉ được là `department` hoặc `personal`, không được là `company`.
- Nếu tài liệu được upload vào folder company, tài liệu có thể là `company`, `department` hoặc `personal`.
- Nếu tài liệu có `access_scope=department`, hệ thống bắt buộc phải xác định được `department_id`.
- Nếu không có folder, hệ thống xác định scope dựa trên request hoặc phòng ban của người upload.

Bảng 3.9. Các trường hợp xác định phạm vi tài liệu

| STT | Trường hợp | Kết quả |
| --- | --- | --- |
| 1 | Folder personal + scope personal | Tài liệu thuộc cá nhân, không gắn phòng ban. |
| 2 | Folder personal + scope khác personal | Từ chối upload. |
| 3 | Folder department + scope department | Tài liệu kế thừa phòng ban của folder. |
| 4 | Folder department + scope personal | Tài liệu cá nhân nằm trong folder được chọn. |
| 5 | Folder department + scope company | Từ chối upload. |
| 6 | Folder company + scope company | Tài liệu dùng chung toàn công ty. |
| 7 | Folder company + scope department | Tài liệu thuộc phòng ban được chỉ định. |
| 8 | Không có folder + department_id | Tài liệu thuộc phòng ban. |
| 9 | Không có folder + không department_id | Tài liệu company hoặc personal tùy thông tin người dùng. |

### 3.4.5. Lưu file và tạo bản ghi tài liệu

Sau khi xác định scope, hệ thống lưu file vào thư mục media. Tên file lưu trữ được tạo bằng hash MD5 của nội dung file kết hợp phần mở rộng. Cách này giúp tránh trùng tên file và có thể nhận biết file có cùng nội dung.

Đường dẫn lưu trữ có dạng:

```text
MEDIA_ROOT/documents/{user_id}/{md5_hash}.{extension}
```

Sau khi lưu file, backend tạo bản ghi `Document` với trạng thái ban đầu là `pending`.

Bảng 3.10. Các trường dữ liệu chính của tài liệu

| STT | Trường dữ liệu | Mô tả |
| --- | --- | --- |
| 1 | `id` | Định danh UUID của tài liệu. |
| 2 | `filename` | Tên file đã hash trong hệ thống lưu trữ. |
| 3 | `original_name` | Tên file gốc người dùng upload. |
| 4 | `storage_path` | Đường dẫn lưu file vật lý. |
| 5 | `file_type` | Loại file đã chuẩn hóa. |
| 6 | `file_size` | Kích thước file. |
| 7 | `mime_type` | MIME type của file. |
| 8 | `uploader` | Người upload tài liệu. |
| 9 | `department` | Phòng ban liên kết nếu có. |
| 10 | `folder` | Thư mục chứa tài liệu nếu có. |
| 11 | `access_scope` | Phạm vi truy cập. |
| 12 | `metadata` | Metadata như mô tả, tag, model embedding, trạng thái pipeline. |
| 13 | `status` | Trạng thái xử lý: `pending`, `processing`, `completed`, `failed`. |
| 14 | `version` | Số phiên bản của tài liệu. |
| 15 | `logical_document_id` | Định danh logic dùng chung giữa các phiên bản. |
| 16 | `is_current` | Đánh dấu phiên bản hiện hành. |

### 3.4.6. Kích hoạt pipeline xử lý tài liệu

Sau khi tạo bản ghi `Document`, hệ thống kích hoạt pipeline xử lý. Nếu Celery được bật, backend đưa tác vụ xử lý vào hàng đợi:

```text
process_document_task.delay(document_id)
```

Nếu Celery không khả dụng, hệ thống chuyển sang xử lý đồng bộ. Cơ chế fallback này giúp pipeline vẫn hoạt động trong môi trường phát triển hoặc khi worker gặp sự cố.

Trạng thái tài liệu được cập nhật theo luồng:

```text
pending -> processing -> completed
```

Nếu xảy ra lỗi:

```text
pending -> processing -> failed
```

Lỗi được lưu vào `metadata.processing_error`.

### 3.4.7. Trích xuất văn bản từ tài liệu

Pipeline xử lý tài liệu sử dụng `ParsingStage` để trích xuất nội dung theo từng loại file.

Bảng 3.11. Phương pháp parse theo định dạng tài liệu

| STT | Loại file | Phương pháp xử lý |
| --- | --- | --- |
| 1 | PDF | Trích xuất text theo trang, có thể dùng OCR fallback. |
| 2 | DOCX | Trích xuất paragraph, bảng và căn chỉnh theo trang. |
| 3 | DOC | Chuyển sang PDF preview rồi trích xuất theo trang. |
| 4 | PPTX | Trích xuất nội dung slide. |
| 5 | XLS/XLSX | Mỗi sheet được xử lý như một trang logic, giữ cấu trúc bảng. |
| 6 | CSV | Nhóm dòng thành các trang logic. |
| 7 | TXT/MD | Đọc văn bản thuần và ước lượng trang. |

Kết quả của bước parse là đối tượng page-aware text gồm:

- Nội dung văn bản đầy đủ.
- Số trang hoặc số sheet.
- Ranh giới trang.
- Metadata bảng tính nếu có.
- Thông tin phục vụ định vị trích dẫn.

Sau đó hệ thống dùng `LocalStructuredParser` để xây dựng cấu trúc tài liệu gồm page, block, heading và table. Cấu trúc này giúp chunking giữ được ngữ cảnh thay vì cắt văn bản tùy tiện.

### 3.4.8. Chia nhỏ nội dung thành chunk

Sau khi có nội dung đã parse, hệ thống chuyển sang `ChunkingStage`. Mục tiêu của bước này là chia tài liệu thành các đoạn đủ nhỏ để embedding và truy hồi, nhưng vẫn giữ đủ ngữ cảnh để LLM trả lời chính xác.

Với tài liệu văn bản, mỗi chunk lưu:

- Nội dung chunk.
- Số trang.
- Chỉ số chunk.
- Heading hoặc section nếu có.
- Liên kết chunk trước và chunk sau.
- Metadata vị trí.

Với bảng tính, hệ thống dùng `ExcelChunkerV2`. Chunk của bảng tính lưu thêm:

- Tên sheet.
- Vùng dòng.
- Cột.
- Bảng markdown.
- Metadata hỗ trợ truy vấn theo ô, hàng, cột hoặc lookup.

Bảng 3.12. Các trường dữ liệu chính của chunk

| STT | Trường dữ liệu | Mô tả |
| --- | --- | --- |
| 1 | `document` | Tài liệu chứa chunk. |
| 2 | `content` | Nội dung văn bản của chunk. |
| 3 | `page_number` | Trang hoặc sheet logic chứa chunk. |
| 4 | `chunk_index` | Thứ tự chunk trong tài liệu. |
| 5 | `node_type` | Loại node: detail, summary hoặc section. |
| 6 | `vector_id` | ID vector trong Qdrant. |
| 7 | `metadata` | Vị trí, heading, sheet, row, column, token count. |
| 8 | `search_vector` | Trường full-text search trong PostgreSQL. |

### 3.4.9. Tạo embedding và lưu vào Qdrant

Sau khi tạo chunk, hệ thống gọi `EmbeddingClient` để chuyển nội dung chunk thành vector embedding. Vector này biểu diễn ngữ nghĩa của đoạn văn bản trong không gian số.

Quy trình:

- Lấy danh sách nội dung chunk.
- Gọi embedding model để tạo vector.
- Lưu chunk vào PostgreSQL.
- Lưu vector vào Qdrant.
- Lưu `qdrant_vector_id` vào bảng `document_embeddings`.

Trong Qdrant, mỗi vector có payload kèm theo:

- `document_id`
- `chunk_id`
- `page_number`
- `chunk_index`
- `node_type`
- `is_current`
- metadata phiên bản

Payload này giúp hệ thống lọc kết quả truy hồi theo tài liệu, phiên bản, trang, loại node và quyền truy cập.

### 3.4.10. Xử lý hình ảnh trong tài liệu

Nếu asset pipeline được bật, hệ thống trích xuất hình ảnh và đối tượng nhúng từ tài liệu. Chức năng này giúp hệ thống có thể truy vấn không chỉ văn bản mà cả nội dung trong hình ảnh.

Quy trình xử lý asset:

- Trích xuất ảnh từ PDF, DOCX, DOC, XLSX hoặc XLS.
- Lưu ảnh vào thư mục media.
- Loại bỏ ảnh quá nhỏ.
- Resize ảnh quá lớn.
- Chạy OCR để lấy text trong ảnh.
- Dùng vision-language model để sinh caption tiếng Việt.
- Nếu model không khả dụng, tạo caption theo luật fallback.
- Gắn asset với chunk gần nhất theo trang hoặc vị trí.
- Lưu `DocumentAsset` vào PostgreSQL.
- Embed caption, OCR và context ảnh vào Qdrant.

Bảng 3.13. Các trường dữ liệu chính của asset

| STT | Trường dữ liệu | Mô tả |
| --- | --- | --- |
| 1 | `document` | Tài liệu chứa ảnh. |
| 2 | `chunk` | Chunk gần nhất với ảnh. |
| 3 | `asset_type` | Loại ảnh như ảnh trong PDF, DOCX, XLSX. |
| 4 | `page_number` | Trang chứa ảnh. |
| 5 | `sheet_name`, `anchor_cell` | Vị trí ảnh trong bảng tính nếu có. |
| 6 | `image_path` | Đường dẫn ảnh đã lưu. |
| 7 | `ocr_text` | Text trích xuất từ ảnh. |
| 8 | `caption` | Mô tả nội dung ảnh. |
| 9 | `context_text` | Nội dung văn bản xung quanh ảnh. |
| 10 | `caption_embedding_id` | Vector ID của caption trong Qdrant. |
| 11 | `processing_status` | Trạng thái xử lý asset. |

### 3.4.11. Xây dựng RAPTOR cho tài liệu dài

Với tài liệu dài hoặc bảng tính lớn, hệ thống có thể xây dựng cây RAPTOR. Mục tiêu của RAPTOR là tạo các node tóm tắt phân cấp để hỗ trợ câu hỏi tổng quan hoặc câu hỏi cần hiểu toàn bộ tài liệu.

Điều kiện áp dụng:

- Tài liệu có số trang vượt ngưỡng cấu hình.
- Spreadsheet có số sheet, số dòng hoặc số chunk vượt ngưỡng.
- Cấu hình `RAG_BUILD_RAPTOR_ON_UPLOAD` cho phép build trong nền.

Quy trình:

- Tải các detail chunk của tài liệu.
- Gom nhóm các chunk liên quan.
- Tạo summary node ở cấp trang, section hoặc tài liệu.
- Tạo embedding cho summary node.
- Lưu summary node vào PostgreSQL và Qdrant.
- Cập nhật metadata `raptor_status`, `raptor_ready`, `raptor_node_count`.

RAPTOR không bắt buộc phải hoàn tất trước khi tài liệu dùng được. Hệ thống ưu tiên `base_ready` để người dùng có thể chat với tài liệu sớm, sau đó RAPTOR hoàn thiện trong nền.

### 3.4.12. Theo dõi trạng thái xử lý

Người dùng có thể kiểm tra trạng thái tài liệu qua endpoint:

```text
GET /api/v1/documents/{doc_id}/status
```

Thông tin trạng thái gồm:

- `document_status`: trạng thái tài liệu.
- `processing_error`: lỗi nếu có.
- `chunk_count`: số chunk đã tạo.
- `page_count`: số trang.
- `asset_status`: trạng thái xử lý ảnh.
- `raptor_status`: trạng thái xây dựng RAPTOR.
- `base_ready`: tài liệu đã sẵn sàng cho truy vấn cơ bản hay chưa.

## 3.5. Xây dựng chức năng quản lý phiên bản tài liệu

Chức năng quản lý phiên bản được xây dựng để tránh ghi đè trực tiếp lên tài liệu cũ. Mỗi lần cập nhật tài liệu, hệ thống tạo một bản ghi tài liệu mới nhưng giữ cùng `logical_document_id`. Nhờ đó, hệ thống có thể truy vết lịch sử, so sánh phiên bản và đảm bảo chỉ phiên bản đã xử lý thành công mới được kích hoạt.

Quy trình xử lý tổng thể:

- Người dùng chọn tài liệu cần cập nhật.
- Frontend gửi file phiên bản mới, mô tả thay đổi và version lock.
- Backend kiểm tra quyền `document_update` hoặc `document_write`.
- Backend kiểm tra quyền `embedding_generate`.
- Hệ thống tạo document mới ở trạng thái `staging`.
- Pipeline xử lý phiên bản mới như một tài liệu bình thường.
- Nếu xử lý thành công, phiên bản mới được kích hoạt.
- Phiên bản cũ chuyển sang `superseded`.
- Nếu xử lý thất bại, phiên bản mới chuyển `failed`, phiên bản cũ vẫn là bản hiện hành.

Endpoint tạo phiên bản mới:

```text
POST /api/v1/documents/{doc_id}/versions
```

Bảng 3.14. Các trường dữ liệu phục vụ versioning

| STT | Trường dữ liệu | Mô tả |
| --- | --- | --- |
| 1 | `logical_document_id` | Định danh chung cho các phiên bản của cùng một tài liệu. |
| 2 | `version` | Số phiên bản. |
| 3 | `previous_version` | Phiên bản liền trước. |
| 4 | `is_current` | Đánh dấu phiên bản hiện hành. |
| 5 | `version_state` | Trạng thái phiên bản: staging, active, superseded, failed. |
| 6 | `valid_from` | Thời điểm bắt đầu hiệu lực. |
| 7 | `valid_to` | Thời điểm hết hiệu lực. |
| 8 | `change_summary` | Mô tả thay đổi. |
| 9 | `version_lock` | Khóa lạc quan để tránh cập nhật đồng thời. |

Khi truy vấn RAG, hệ thống mặc định ưu tiên phiên bản `is_current=true`. Nếu câu hỏi yêu cầu lịch sử, amendment hoặc so sánh phiên bản, phạm vi truy xuất có thể được mở rộng sang các phiên bản liên quan.

## 3.6. Xây dựng chức năng chat hỏi đáp tài liệu bằng RAG

Chức năng chat hỏi đáp được xây dựng để người dùng có thể khai thác nội dung tài liệu bằng ngôn ngữ tự nhiên. Người dùng không cần tìm thủ công trong từng file mà có thể đặt câu hỏi trực tiếp. Hệ thống sẽ xác định phạm vi tài liệu, truy xuất các đoạn liên quan, xây dựng ngữ cảnh RAG, gọi mô hình ngôn ngữ lớn và trả về câu trả lời có trích dẫn.

> **Điểm kỹ thuật trọng tâm:** hệ thống sử dụng cơ chế truy xuất thích ứng thay vì chỉ tìm kiếm vector top-K. Câu hỏi được phân loại để lựa chọn deterministic retrieval, spreadsheet retrieval, hybrid search hoặc RAPTOR; kết quả sau đó được kiểm tra grounding và gắn nguồn kiểm chứng.

Chức năng được triển khai bằng API hội thoại và API stream:

```text
POST /api/v1/chat/messages/stream
```

Quy trình xử lý tổng thể:

- Thu thập câu hỏi:
  - Nhận nội dung câu hỏi từ người dùng.
  - Nhận `conversation_id` nếu đang tiếp tục cuộc trò chuyện.
  - Nhận danh sách tài liệu hoặc thư mục được chọn.
  - Nhận chế độ RAG như `fast` hoặc `deep`.
- Xác thực và phân quyền:
  - Kiểm tra JWT.
  - Kiểm tra quyền `chat_send`.
  - Kiểm tra quyền `rag_query`.
- Xác định phạm vi tài liệu:
  - Ưu tiên `document_ids` từ request.
  - Mở rộng `folder_ids` thành danh sách tài liệu.
  - Nếu request không truyền tài liệu, dùng tài liệu đã gắn vào conversation.
  - Nếu vẫn không có, fallback sang tài liệu người dùng có quyền truy cập.
- Truy xuất ngữ cảnh:
  - Phân loại ý định câu hỏi.
  - Truy xuất deterministic nếu câu hỏi hỏi bảng, heading hoặc ảnh cụ thể.
  - Dùng hybrid retrieval nếu câu hỏi tổng quát.
  - Dùng spreadsheet retrieval nếu câu hỏi liên quan Excel/CSV.
  - Dùng RAPTOR nếu tài liệu dài và câu hỏi có phạm vi rộng.
  - Rerank và lọc kết quả.
- Sinh câu trả lời:
  - Tạo prompt RAG có đánh số nguồn.
  - Gọi LLM cục bộ qua `LlamaClient`.
  - Stream câu trả lời về frontend.
- Kiểm chứng và lưu kết quả:
  - Tạo citation payload.
  - Kiểm tra grounding.
  - Lưu assistant message và citations vào PostgreSQL.

### 3.6.1. Giao diện chat

Frontend cung cấp giao diện chat gồm:

- Danh sách cuộc trò chuyện.
- Vùng hiển thị tin nhắn.
- Ô nhập câu hỏi.
- Bộ chọn tài liệu và thư mục.
- Chức năng upload nhanh file trong chat.
- Hiển thị citation, nguồn, trang, đoạn trích hoặc hình ảnh.
- Chức năng gửi feedback cho câu trả lời.

Khi người dùng gửi câu hỏi, frontend tạo trước một tin nhắn user và một tin nhắn assistant rỗng để nhận stream. Khi backend gửi từng chunk text, frontend cập nhật dần nội dung tin nhắn assistant.

### 3.6.2. Quản lý hội thoại

Hội thoại được lưu trong bảng `conversations`, còn từng tin nhắn được lưu trong bảng `messages`.

Bảng 3.15. Các trường dữ liệu chính của hội thoại

| STT | Trường dữ liệu | Mô tả |
| --- | --- | --- |
| 1 | `id` | Định danh UUID của hội thoại. |
| 2 | `account` | Người sở hữu hội thoại. |
| 3 | `title` | Tiêu đề hội thoại. |
| 4 | `summary` | Tóm tắt hội thoại nếu có. |
| 5 | `created_at`, `updated_at` | Thời điểm tạo và cập nhật. |

Bảng 3.16. Các trường dữ liệu chính của tin nhắn

| STT | Trường dữ liệu | Mô tả |
| --- | --- | --- |
| 1 | `conversation` | Hội thoại chứa tin nhắn. |
| 2 | `role` | Vai trò tin nhắn: user, assistant hoặc system. |
| 3 | `content` | Nội dung tin nhắn. |
| 4 | `citations` | Danh sách nguồn trích dẫn dạng JSON. |
| 5 | `tokens_used` | Số token sử dụng. |

Tài liệu và thư mục được gắn vào hội thoại được lưu trong:

- `conversations_attached_documents`
- `conversations_attached_folders`

Nhờ đó, người dùng có thể hỏi nhiều câu liên tiếp trên cùng một tập tài liệu mà không cần chọn lại.

### 3.6.3. Xác thực và kiểm tra quyền trước khi chat

`ChatStreamView` không dùng DRF ViewSet vì cần trả về `StreamingHttpResponse`. View này tự đọc body JSON, xác thực access token trong Authorization header và kiểm tra quyền.

Các quyền bắt buộc:

| STT | Quyền | Ý nghĩa |
| --- | --- | --- |
| 1 | `chat_send` | Cho phép gửi câu hỏi trong chat. |
| 2 | `rag_query` | Cho phép sử dụng pipeline truy vấn RAG. |

Nếu thiếu một trong hai quyền, backend trả lỗi 403 và không thực hiện truy xuất tài liệu. Đây là lớp bảo vệ đầu tiên của chức năng chat.

### 3.6.4. Xác định phạm vi tài liệu khi truy vấn

Trước khi tìm kiếm, hệ thống xác định danh sách tài liệu được phép sử dụng làm nguồn.

Thứ tự ưu tiên:

- Dùng `document_ids` được truyền trực tiếp từ request.
- Mở rộng `folder_ids` thành danh sách tài liệu trong các thư mục được chọn.
- Nếu request không có tài liệu, dùng tài liệu đã gắn với conversation.
- Nếu conversation chưa có tài liệu, dùng danh sách tài liệu người dùng có quyền truy cập.
- Nếu câu hỏi liên quan phiên bản hoặc amendment, mở rộng sang các phiên bản liên quan trong giới hạn quyền.

Tất cả tài liệu đều phải đi qua kiểm tra quyền đọc trước khi được đưa vào retrieval. Hệ thống không đưa chunk của tài liệu không có quyền vào prompt, kể cả khi vector search tìm thấy kết quả liên quan.

### 3.6.5. Phân loại ý định câu hỏi

Hệ thống sử dụng `QueryRouter` và `QueryIntentClassifier` để xác định loại câu hỏi. Việc phân loại giúp chọn chiến lược retrieval phù hợp.

Bảng 3.17. Một số loại ý định truy vấn

| STT | Loại ý định | Cách xử lý phù hợp |
| --- | --- | --- |
| 1 | Định nghĩa | Truy xuất đoạn giải thích khái niệm. |
| 2 | Liệt kê | Mở rộng retrieval để lấy đầy đủ các mục. |
| 3 | Quy trình | Giữ thứ tự bước trong tài liệu. |
| 4 | So sánh | Lấy nhiều nguồn và có thể trình bày dạng bảng. |
| 5 | Bảng | Ưu tiên truy xuất bảng chính xác. |
| 6 | Spreadsheet row/column/cell | Dùng `SpreadsheetRetriever`. |
| 7 | Hình ảnh | Tìm trong asset caption, OCR và context ảnh. |
| 8 | Heading/section | Truy xuất đúng section hoặc heading được hỏi. |
| 9 | Tổng quan tài liệu dài | Dùng RAPTOR nếu có. |

### 3.6.6. Truy xuất deterministic

Với các câu hỏi có đối tượng rõ ràng, hệ thống ưu tiên truy xuất deterministic thay vì chỉ dùng vector search.

Các trường hợp:

- Hỏi nội dung một bảng cụ thể.
- Hỏi section hoặc heading cụ thể.
- Hỏi chức năng, nhiệm vụ, quyền hạn hoặc trách nhiệm của một đơn vị.
- Hỏi hình ảnh cụ thể trong tài liệu.

Ưu điểm của cách này là giảm rủi ro lấy nhầm đoạn gần nghĩa nhưng thiếu thông tin. Ví dụ khi người dùng hỏi “nội dung bảng phân quyền người dùng”, hệ thống cần lấy đúng bảng thay vì lấy một đoạn mô tả phân quyền chung.

### 3.6.7. Hybrid retrieval

Nếu câu hỏi không thuộc nhóm deterministic, hệ thống dùng hybrid retrieval. Cách này kết hợp tìm kiếm từ khóa và tìm kiếm ngữ nghĩa.

Các thành phần:

- `BM25Searcher`: tìm kiếm full-text trong PostgreSQL.
- `Qdrant.search_similar`: tìm kiếm vector dense trong Qdrant.
- Asset search: tìm kiếm trong caption, OCR và context của ảnh.
- Weighted RRF: hợp nhất kết quả từ nhiều nguồn.
- Reranker: sắp xếp lại candidate theo mức liên quan với câu hỏi.

Quy trình:

- Tạo embedding cho câu hỏi.
- Tìm kiếm sparse bằng BM25.
- Tìm kiếm dense bằng Qdrant.
- Tìm asset nếu câu hỏi liên quan hình ảnh.
- Hợp nhất kết quả.
- Loại trùng.
- Mở rộng chunk lân cận nếu cần.
- Rerank kết quả.

### 3.6.8. Truy xuất dữ liệu bảng tính

Với Excel hoặc CSV, hệ thống dùng `SpreadsheetRetriever`. Mục tiêu là giữ chính xác cấu trúc bảng, hàng, cột và ô dữ liệu.

Các dạng truy vấn hỗ trợ:

- Truy vấn theo sheet.
- Truy vấn theo hàng.
- Truy vấn theo cột.
- Truy vấn theo ô.
- Lookup theo khóa.
- Trả lời bằng bảng markdown nếu câu hỏi yêu cầu bảng.

Ví dụ, với câu hỏi “KPI của phòng Kinh doanh trong tháng 3 là bao nhiêu?”, hệ thống cần xác định đúng sheet, hàng phòng Kinh doanh và cột tháng 3. Nếu chỉ dùng vector search thông thường, khả năng lấy thiếu cột hoặc sai hàng sẽ cao hơn.

### 3.6.9. Truy xuất bằng RAPTOR

Khi tài liệu có RAPTOR tree và câu hỏi mang tính tổng quan, hệ thống có thể truy xuất qua summary node.

Quy trình:

- Embed câu hỏi.
- Tìm summary node liên quan trong Qdrant.
- Đi xuống các detail chunk con.
- Kết hợp điểm summary và điểm detail.
- Bổ sung hybrid fallback nếu cần.

RAPTOR phù hợp với câu hỏi như:

- “Tóm tắt tài liệu này.”
- “Tài liệu gồm những nội dung chính nào?”
- “Quy trình tổng thể được mô tả như thế nào?”
- “So sánh các nhóm chính sách trong tài liệu.”

### 3.6.10. Xây dựng prompt RAG

Sau khi có các candidate chunk, hệ thống xây dựng ngữ cảnh RAG có đánh số nguồn.

Cấu trúc ngữ cảnh:

```text
NGUỒN [1]
Tài liệu: quy_che_noi_bo.pdf
Trang: 5
Nội dung trích: ...

NGUỒN [2]
Tài liệu: huong_dan_kpi.xlsx
Sheet: KPI_2026
Dòng: 10-15
Nội dung trích: ...
```

Prompt yêu cầu LLM:

- Chỉ trả lời dựa trên nội dung tài liệu tham khảo.
- Không dùng kiến thức bên ngoài nếu tài liệu không cung cấp.
- Nếu tài liệu không có thông tin, nói rõ tài liệu không có thông tin.
- Mỗi ý quan trọng phải có trích dẫn.
- Giữ đúng cấu trúc bảng nếu nguồn là bảng.
- Với tài liệu nhiều phiên bản, ưu tiên phiên bản hiệu lực.
- Với ảnh, trả lời vị trí ảnh và để giao diện hiển thị ảnh.

### 3.6.11. Sinh câu trả lời và stream về giao diện

Nếu câu hỏi có thể trả lời deterministic từ bảng hoặc section, hệ thống có thể dựng câu trả lời trực tiếp. Nếu cần tổng hợp tự nhiên, hệ thống gọi LLM qua `LlamaClient`.

Trong chế độ stream:

- Backend nhận từng phần output từ LLM.
- Backend gửi từng chunk text về frontend.
- Frontend cập nhật nội dung assistant message theo thời gian thực.
- Khi stream kết thúc, backend gửi citations.
- Frontend gắn citations vào tin nhắn.

Cách stream giúp người dùng thấy phản hồi nhanh hơn thay vì phải chờ toàn bộ câu trả lời hoàn tất.

### 3.6.12. Kiểm chứng grounding và tạo trích dẫn

Sau khi có câu trả lời, hệ thống xây dựng citation payload và kiểm tra grounding. Mục tiêu là đảm bảo câu trả lời có căn cứ từ tài liệu.

Citation có thể gồm:

- `document_id`
- `chunk_id`
- `title`
- `page`
- `line_start`, `line_end`
- `row_start`, `row_end`
- `excerpt`
- `score`
- `grounding_score`
- thông tin asset nếu nguồn là hình ảnh

Bảng 3.18. Các thông tin hiển thị trong trích dẫn

| STT | Thông tin | Ý nghĩa |
| --- | --- | --- |
| 1 | Tên tài liệu | Cho biết câu trả lời dựa trên tài liệu nào. |
| 2 | Trang hoặc sheet | Giúp người dùng tìm lại vị trí nguồn. |
| 3 | Đoạn trích | Cung cấp bằng chứng ngắn từ tài liệu. |
| 4 | Chunk id | Liên kết đến đoạn nguồn trong hệ thống. |
| 5 | Điểm liên quan | Cho biết mức phù hợp của nguồn với câu hỏi. |
| 6 | Asset id | Dùng khi nguồn là hình ảnh. |
| 7 | Thumbnail hoặc image URL | Cho phép frontend hiển thị ảnh nguồn. |

Nhờ citation, người dùng có thể kiểm chứng câu trả lời thay vì chỉ tin vào nội dung do LLM sinh ra.

### 3.6.13. Lưu lịch sử chat và phản hồi người dùng

Sau khi trả lời, hệ thống lưu assistant message vào bảng `messages`. Nội dung citations được lưu dưới dạng JSON để khi người dùng mở lại hội thoại, nguồn trích dẫn vẫn được hiển thị đầy đủ.

Người dùng có thể đánh giá câu trả lời qua endpoint:

```text
POST /api/v1/chat/messages/{message_id}/feedback
```

Feedback gồm:

- Message được đánh giá.
- Người đánh giá.
- Số sao hoặc mức rating.
- Nhận xét bổ sung.

Dữ liệu feedback giúp đánh giá chất lượng retrieval, chất lượng grounding và độ hữu ích của câu trả lời.

## 3.7. Xử lý lỗi và đảm bảo an toàn dữ liệu

Trong quá trình triển khai, hệ thống được thiết kế để các lỗi ở từng giai đoạn không làm hỏng toàn bộ quy trình.

Các trường hợp lỗi thường gặp:

- File vượt quá dung lượng cho phép.
- File không thuộc định dạng hỗ trợ.
- Người dùng không có quyền upload.
- Người dùng không có quyền ghi vào thư mục.
- Folder hoặc document không tồn tại.
- Parse tài liệu thất bại.
- Embedding service không khả dụng.
- Qdrant lưu vector thất bại.
- Celery không queue được task.
- Asset pipeline lỗi.
- RAPTOR build lỗi.
- LLM stream lỗi.

Cách xử lý:

- Lỗi validation trả về HTTP 400.
- File quá lớn trả về HTTP 413.
- Thiếu quyền trả về HTTP 403.
- Không tìm thấy tài nguyên trả về HTTP 404.
- Lỗi pipeline được lưu vào `metadata.processing_error`.
- Tài liệu lỗi được đánh dấu `failed`.
- Nếu Celery không khả dụng, hệ thống fallback sang xử lý đồng bộ hoặc thread nền.
- Nếu asset hoặc RAPTOR lỗi, base RAG vẫn có thể hoạt động nếu chunk và embedding đã sẵn sàng.

Các lớp an toàn dữ liệu:

- JWT authentication cho API.
- RBAC cho quyền chức năng.
- ACL cho thư mục và tài liệu.
- Scope cá nhân, phòng ban và công ty.
- Kiểm tra quyền trước retrieval.
- Không đưa tài liệu không có quyền vào prompt.
- Soft delete cho tài khoản, thư mục và tài liệu.
- Versioning để tránh mất phiên bản cũ.
- Audit log cho thao tác quan trọng.

## 3.8. Kết luận chương

Chương này đã trình bày quá trình xây dựng các chức năng chính của hệ thống theo hướng triển khai thực tế. Chức năng quản lý người dùng đảm nhiệm xác thực, phân quyền, quản lý phòng ban, vai trò và audit log. Chức năng quản lý thư mục và phạm vi truy cập giúp tổ chức tài liệu theo cá nhân, phòng ban và toàn công ty. Chức năng upload tài liệu xử lý đầy đủ các giai đoạn từ nhận file, kiểm tra, lưu trữ, parse, chunking, embedding, lưu vector, OCR ảnh, RAPTOR và cập nhật trạng thái. Chức năng quản lý phiên bản giúp bảo toàn lịch sử tài liệu và chỉ kích hoạt phiên bản mới khi xử lý thành công. Chức năng chat RAG cho phép người dùng hỏi đáp tài liệu bằng ngôn ngữ tự nhiên, đồng thời đảm bảo kiểm soát quyền, truy xuất đúng phạm vi, sinh câu trả lời có căn cứ và hiển thị nguồn trích dẫn.

Với cách triển khai này, hệ thống không chỉ là nơi lưu trữ tài liệu mà còn là nền tảng khai thác tri thức nội bộ có kiểm soát, có truy vết và có khả năng kiểm chứng nguồn.

Tóm lại, quá trình triển khai hệ thống đạt được bốn kết quả kỹ thuật nổi bật:

1. Xây dựng pipeline xử lý và lập chỉ mục tài liệu đa định dạng, có khả năng bảo toàn cấu trúc văn bản, bảng và hình ảnh.
2. Xây dựng cơ chế truy xuất thích ứng, phối hợp tìm kiếm chính xác, BM25, vector, spreadsheet retrieval và RAPTOR theo đặc điểm câu hỏi.
3. Xây dựng cơ chế grounding và citation để câu trả lời có nguồn kiểm chứng đến đúng tài liệu và vị trí liên quan.
4. Tích hợp kiểm soát quyền vào toàn bộ vòng đời dữ liệu, từ upload, lưu trữ, retrieval đến xây dựng prompt cho LLM.
