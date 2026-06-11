# CHƯƠNG 1. CƠ SỞ LÝ THUYẾT

Chương này trình bày các cơ sở lý thuyết và công nghệ chính được sử dụng để xây dựng hệ thống quản trị tri thức doanh nghiệp. Nội dung được tổ chức theo trình tự từ bài toán quản trị tài liệu, nền tảng trí tuệ nhân tạo cục bộ, kiến trúc Retrieval-Augmented Generation, các phương pháp xử lý và truy xuất tài liệu, đến kiến trúc phần mềm và hạ tầng triển khai.

## 1.1. Tổng quan về hệ thống quản trị tri thức doanh nghiệp

### 1.1.1. Khái niệm và vai trò

Hệ thống quản trị tri thức, tiếng Anh là Knowledge Management System, là hệ thống hỗ trợ tổ chức thu thập, lưu trữ, tổ chức, chia sẻ và khai thác tri thức. Trong doanh nghiệp, tri thức thường tồn tại dưới nhiều dạng như quy trình nghiệp vụ, quy định nội bộ, hợp đồng, báo cáo, biểu mẫu, bảng tính, tài liệu đào tạo và hướng dẫn kỹ thuật.

Khác với hệ thống lưu trữ tệp thông thường, hệ thống quản trị tri thức không chỉ quản lý vị trí của tài liệu mà còn phải giúp người dùng tìm được nội dung bên trong tài liệu. Một hệ thống phù hợp với môi trường doanh nghiệp cần đáp ứng các yêu cầu:

- Quản lý tài liệu theo phòng ban, thư mục và phạm vi truy cập.
- Hỗ trợ nhiều định dạng tài liệu.
- Quản lý phiên bản và trạng thái hiệu lực.
- Tìm kiếm theo từ khóa và theo ngữ nghĩa.
- Hỏi đáp bằng ngôn ngữ tự nhiên.
- Cung cấp nguồn trích dẫn để kiểm chứng câu trả lời.
- Kiểm soát quyền truy cập trước khi cung cấp nội dung.
- Ghi nhận lịch sử thao tác phục vụ quản trị và kiểm tra.

### 1.1.2. Hạn chế của phương pháp tìm kiếm truyền thống

Các hệ thống quản lý tài liệu truyền thống thường tìm kiếm dựa trên tên tệp, metadata hoặc sự xuất hiện của từ khóa. Phương pháp này hiệu quả với mã số, tên riêng và cụm từ chính xác nhưng gặp khó khăn khi người dùng diễn đạt câu hỏi bằng từ đồng nghĩa hoặc ngôn ngữ tự nhiên.

Ví dụ, câu hỏi “Nhân viên được hưởng quyền lợi gì khi sinh con?” có thể cần truy xuất phần có tiêu đề “Chế độ thai sản” dù hai câu không sử dụng cùng từ ngữ. Ngoài ra, tài liệu doanh nghiệp còn chứa bảng, hình ảnh, sơ đồ và dữ liệu theo phiên bản mà tìm kiếm từ khóa đơn thuần khó khai thác đầy đủ.

Sự phát triển của mô hình ngôn ngữ lớn và kỹ thuật tìm kiếm ngữ nghĩa cho phép xây dựng hệ thống có khả năng đọc, truy xuất và tổng hợp nội dung tài liệu. Tuy nhiên, để sử dụng trong doanh nghiệp, câu trả lời phải dựa trên tài liệu được cấp quyền và phải có nguồn kiểm chứng.

## 1.2. Trí tuệ nhân tạo cục bộ và các mô hình nền tảng

### 1.2.1. Xử lý ngôn ngữ tự nhiên và Transformer

Xử lý ngôn ngữ tự nhiên, tiếng Anh là Natural Language Processing, là lĩnh vực giúp máy tính phân tích, biểu diễn và sinh ngôn ngữ của con người. Trong đề tài, NLP được ứng dụng để:

- Trích xuất và chuẩn hóa nội dung tài liệu.
- Nhận diện tiêu đề, đoạn văn và bảng.
- Phân tích ý định câu hỏi.
- Tạo biểu diễn vector cho văn bản.
- Tìm kiếm nội dung liên quan.
- Tóm tắt và sinh câu trả lời.

Với tiếng Việt, hệ thống cần xử lý được văn bản có dấu, không dấu, từ ghép, thuật ngữ chuyên ngành và cấu trúc văn bản hành chính như chương, mục, điều và khoản.

Transformer là kiến trúc học sâu được Vaswani và cộng sự giới thiệu năm 2017 [1]. Thành phần quan trọng của Transformer là cơ chế Attention, cho phép mô hình xác định mối liên hệ giữa các token trong chuỗi đầu vào. Transformer có khả năng xử lý song song tốt và mô hình hóa quan hệ giữa các nội dung ở khoảng cách xa. Đây là nền tảng của các mô hình ngôn ngữ và mô hình embedding được sử dụng trong đề tài.

### 1.2.2. Mô hình ngôn ngữ lớn

Mô hình ngôn ngữ lớn, hay Large Language Model, là mô hình được huấn luyện trên tập văn bản quy mô lớn để thực hiện các nhiệm vụ như trả lời câu hỏi, tóm tắt, giải thích và sinh văn bản.

LLM có khả năng tổng hợp câu trả lời tự nhiên nhưng tồn tại một số hạn chế:

- Không tự biết tài liệu mới được tải lên hệ thống.
- Tri thức trong tham số mô hình có thể không còn cập nhật.
- Có thể tạo thông tin nghe hợp lý nhưng không có bằng chứng.
- Không tự cung cấp được nguồn chính xác cho dữ liệu nội bộ.

Do đó, LLM trong đề tài đóng vai trò tổng hợp câu trả lời từ ngữ cảnh đã được truy xuất, thay vì được xem là nguồn tri thức duy nhất.

Hệ thống sử dụng **Qwen3-4B-Instruct-2507** để sinh câu trả lời [17]. Mô hình nhận câu hỏi, lịch sử hội thoại và ngữ cảnh RAG, sau đó tạo câu trả lời theo chỉ dẫn. Phiên bản 4 tỷ tham số được lựa chọn nhằm cân bằng giữa khả năng xử lý ngôn ngữ, yêu cầu phần cứng và tốc độ phản hồi.

### 1.2.3. Triển khai AI cục bộ

Trí tuệ nhân tạo cục bộ, hay Local AI, là phương thức triển khai mô hình AI trên hạ tầng do tổ chức quản lý thay vì gửi dữ liệu tới dịch vụ AI công cộng. Mô hình có thể chạy trên máy trạm, máy chủ nội bộ hoặc cụm máy chủ của doanh nghiệp.

Trong phạm vi đề tài, mô hình ngôn ngữ, mô hình embedding và mô hình thị giác-ngôn ngữ được triển khai cục bộ. Cách tiếp cận này mang lại các lợi ích:

- Tăng quyền kiểm soát đối với tài liệu và truy vấn.
- Hạn chế phụ thuộc vào dịch vụ AI bên thứ ba.
- Chủ động cấu hình mô hình và tài nguyên phần cứng.
- Có thể vận hành trong mạng nội bộ khi các thành phần đã được cài đặt.
- Hạn chế chi phí phát sinh theo số lượng token của API thương mại.

Triển khai cục bộ không mặc nhiên bảo đảm an toàn tuyệt đối hoặc đáp ứng một tiêu chuẩn như ISO 27001. Mức độ an toàn còn phụ thuộc vào cấu hình mạng, quản lý tài khoản, phân quyền, mã hóa, nhật ký kiểm toán, sao lưu và quy trình vận hành.

Thách thức chính của Local AI là yêu cầu về RAM, VRAM, năng lực tính toán, độ dài ngữ cảnh và khả năng xử lý đồng thời. Doanh nghiệp phải cân bằng giữa kích thước mô hình, chất lượng đầu ra và tài nguyên sẵn có.

### 1.2.4. Lượng tử hóa, GGUF và llama.cpp

Lượng tử hóa, hay Quantization, là kỹ thuật biểu diễn trọng số mô hình bằng kiểu dữ liệu có độ chính xác thấp hơn, chẳng hạn chuyển từ 16-bit xuống 8-bit hoặc 4-bit. Kỹ thuật này giúp giảm dung lượng mô hình, giảm nhu cầu RAM và VRAM, đồng thời cho phép chạy mô hình trên phần cứng có tài nguyên hạn chế hơn.

Đổi lại, lượng tử hóa có thể làm giảm một phần chất lượng hoặc độ ổn định của mô hình. Mức ảnh hưởng phụ thuộc vào phương pháp lượng tử hóa, kích thước mô hình và loại tác vụ.

Đề tài sử dụng Qwen3-4B-Instruct-2507 với mức lượng tử hóa `Q4_K_M`. Đây là cấu hình 4-bit được lựa chọn để cân bằng giữa dung lượng, tốc độ và chất lượng suy luận.

GGUF là định dạng lưu trữ mô hình được sử dụng trong hệ sinh thái `llama.cpp` [14]. Định dạng này lưu trọng số, thông tin tokenizer và metadata cần thiết để suy luận, đồng thời hỗ trợ nhiều mức lượng tử hóa.

`llama.cpp` là công cụ suy luận mô hình được tối ưu cho nhiều loại phần cứng [15]. Trong hệ thống, `llama.cpp` chạy dưới dạng máy chủ và cung cấp API tương thích với OpenAI. Backend sử dụng API này để gửi prompt, nhận câu trả lời và truyền nội dung theo dạng streaming.

## 1.3. Kiến trúc Retrieval-Augmented Generation đa phương thức

### 1.3.1. Khái niệm RAG

Retrieval-Augmented Generation, viết tắt là RAG, là phương pháp kết hợp truy xuất thông tin với mô hình sinh ngôn ngữ [2]. Khi người dùng đặt câu hỏi, hệ thống tìm các đoạn tài liệu liên quan và cung cấp chúng cho LLM làm ngữ cảnh.

Một hệ thống RAG gồm hai thành phần chính:

1. **Retriever:** tìm kiếm các đoạn tài liệu liên quan.
2. **Generator:** sử dụng câu hỏi và nội dung truy xuất để sinh câu trả lời.

Quy trình tổng quát:

```text
Câu hỏi
   -> Phân tích truy vấn
   -> Xác định phạm vi tài liệu
   -> Truy xuất các đoạn liên quan
   -> Xếp hạng lại
   -> Xây dựng ngữ cảnh
   -> LLM sinh câu trả lời
   -> Kiểm tra và gắn trích dẫn
```

RAG giúp cập nhật tri thức bằng cách bổ sung hoặc thay đổi tài liệu mà không phải huấn luyện lại mô hình ngôn ngữ. Đồng thời, nguồn được truy xuất có thể được sử dụng làm bằng chứng cho câu trả lời.

### 1.3.2. RAG đa phương thức

RAG đa phương thức, hay Multimodal RAG, mở rộng RAG từ văn bản sang nhiều loại dữ liệu như hình ảnh, bảng và sơ đồ. Tài liệu doanh nghiệp thường chứa cả văn bản và thành phần trực quan, do đó chỉ trích xuất chữ có thể làm mất thông tin.

Các nguồn dữ liệu thường được xử lý trong RAG đa phương thức gồm:

- Văn bản theo trang và cấu trúc tài liệu.
- Bảng trong tài liệu và bảng tính.
- Hình ảnh được trích xuất từ PDF, Word hoặc Excel.
- Nội dung chữ trong ảnh thông qua OCR.
- Mô tả ngữ nghĩa của ảnh thông qua mô hình thị giác-ngôn ngữ.

Văn bản, nội dung OCR và mô tả hình ảnh có thể được biểu diễn trong cùng một không gian truy xuất hoặc được quản lý bằng các chỉ mục riêng. Kết quả từ các nguồn được hợp nhất để cung cấp ngữ cảnh đầy đủ hơn cho mô hình ngôn ngữ.

## 1.4. Xử lý, chia nhỏ và biểu diễn tài liệu

### 1.4.1. Các phương pháp chunking

Chunking là quá trình chia tài liệu dài thành những đoạn nhỏ hơn gọi là chunk. Đây là bước quan trọng vì mô hình embedding và LLM đều có giới hạn độ dài đầu vào.

Chunk quá lớn có thể chứa nhiều chủ đề và làm giảm độ chính xác tìm kiếm. Chunk quá nhỏ có thể làm mất ngữ cảnh. Vì vậy, hệ thống kết hợp các phương pháp sau:

- **Token-window chunking:** chia theo cửa sổ token và sử dụng phần chồng lấp giữa các chunk liên tiếp.
- **Page-aware chunking:** chia theo trang trước khi tạo các chunk nhỏ trong từng trang, giúp citation xác định đúng vị trí.
- **Structure-aware chunking:** ưu tiên biên tiêu đề, đoạn văn, bảng và mục nội dung.
- **Spreadsheet chunking:** chia theo bảng, sheet và hàng, đồng thời lưu tên sheet, số hàng và ký hiệu cột.

Đối với câu hỏi xác định như “ô B12 có giá trị gì?”, hệ thống ưu tiên truy xuất theo địa chỉ bảng tính thay vì chỉ sử dụng tìm kiếm vector.

### 1.4.2. Embedding và mô hình BGE-M3

Embedding là phương pháp chuyển văn bản thành vector số thực. Các nội dung có ý nghĩa gần nhau thường có vector nằm gần nhau trong không gian embedding.

Trong hệ thống:

- Mỗi chunk tài liệu được chuyển thành vector.
- Câu hỏi của người dùng được chuyển thành vector.
- Vector câu hỏi được so sánh với vector tài liệu để tìm nội dung tương đồng.

Độ tương đồng cosine được dùng để đo mức gần nhau giữa hai vector. Tuy nhiên, điểm tương đồng chỉ là một tín hiệu truy xuất, không tự khẳng định đoạn tìm được là bằng chứng chính xác.

Đề tài sử dụng **BGE-M3** làm mô hình embedding [3]. Đây là mô hình đa ngôn ngữ, hỗ trợ văn bản có độ dài khác nhau và ba dạng truy xuất: dense, sparse và multi-vector.

Phiên bản hiện tại sử dụng dense embedding 1024 chiều của BGE-M3 thông qua thư viện FlagEmbedding. Mô hình được chạy cục bộ trên CPU hoặc GPU và tạo embedding theo lô để giảm thời gian xử lý.

### 1.4.3. OCR và mô hình thị giác-ngôn ngữ

OCR, viết tắt của Optical Character Recognition, là kỹ thuật nhận dạng chữ từ hình ảnh. Hệ thống hỗ trợ PaddleOCR và Tesseract để xử lý hình ảnh hoặc tài liệu scan.

OCR phù hợp với ảnh chứa chữ nhưng chưa đủ để hiểu biểu đồ hoặc sơ đồ. Do đó, hệ thống sử dụng **Qwen2.5-VL-3B-Instruct** để tạo mô tả hình ảnh [16]. Mô hình được triển khai cục bộ bằng `llama.cpp` với tệp mô hình lượng tử hóa và tệp chiếu thị giác.

Nội dung OCR, caption do mô hình thị giác sinh ra và đoạn văn xung quanh được kết hợp để tạo embedding cho asset. Vector asset được lưu trong collection `document_assets` của Qdrant.

## 1.5. Các thuật toán truy xuất và xếp hạng

### 1.5.1. Tìm kiếm từ khóa và BM25

BM25 là thuật toán xếp hạng tài liệu dựa trên tần suất xuất hiện của từ khóa, độ hiếm của từ trong tập tài liệu và độ dài văn bản [4]. BM25 phù hợp với các truy vấn chứa mã số, tên riêng, thuật ngữ hoặc cụm từ chính xác.

Trong hệ thống hiện tại, tầng tìm kiếm thưa sử dụng PostgreSQL Full-Text Search và `SearchRank`, sau đó bổ sung điểm đối sánh từ vựng. Vì không triển khai nguyên bản toàn bộ công thức Robertson BM25, cách gọi chính xác là **tìm kiếm BM25-like dựa trên PostgreSQL Full-Text Search**.

### 1.5.2. Tìm kiếm vector và Hybrid Search

Tìm kiếm vector sử dụng embedding để tìm các đoạn tương đồng về ý nghĩa. Phương pháp này có thể tìm được nội dung liên quan dù câu hỏi và tài liệu không sử dụng cùng từ ngữ. Tuy nhiên, nó có thể kém chính xác với mã số, địa chỉ ô hoặc dữ kiện cần khớp tuyệt đối.

Hybrid Search kết hợp:

- Sparse retrieval để giữ tín hiệu từ khóa chính xác.
- Dense retrieval để phát hiện tương đồng ngữ nghĩa.

Hai danh sách kết quả có thang điểm khác nhau nên không được cộng trực tiếp. Hệ thống sử dụng **Weighted Reciprocal Rank Fusion** để hợp nhất dựa trên thứ hạng [5]. Phiên bản có trọng số cho phép điều chỉnh vai trò của dense và sparse retrieval theo loại câu hỏi.

### 1.5.3. Reranking và MMR

Retriever thường lấy một tập kết quả rộng để tăng khả năng không bỏ sót bằng chứng. Reranking đánh giá lại tập ứng viên và chọn các kết quả phù hợp nhất.

Reranker của hệ thống kết hợp:

- Điểm retrieval ban đầu.
- Độ tương đồng embedding.
- Mức trùng khớp từ khóa.
- Loại câu hỏi.
- Đặc điểm metadata.

Sau khi xếp hạng lại, hệ thống loại bỏ các kết quả gần trùng lặp và sử dụng **Maximal Marginal Relevance** để cân bằng giữa độ liên quan và tính đa dạng. Điều này giúp tránh đưa nhiều chunk gần giống nhau vào ngữ cảnh LLM.

### 1.5.4. Phân loại và mở rộng truy vấn

Hệ thống phân loại truy vấn thành các nhóm như dữ kiện, định nghĩa, liệt kê, bảng, phân tích, so sánh, quy trình, hình ảnh và bảng tính. Mỗi nhóm sử dụng số lượng kết quả, trọng số tìm kiếm và cách mở rộng ngữ cảnh khác nhau.

Các kỹ thuật hỗ trợ gồm:

- **Query rewriting:** viết lại câu hỏi rõ nghĩa hơn.
- **Query decomposition:** tách câu hỏi phức tạp thành câu hỏi con.
- **HyDE:** tạo một đoạn trả lời giả định, sau đó dùng embedding của đoạn này để tìm tài liệu thật [6].

Những kỹ thuật cần gọi LLM được ưu tiên trong chế độ tìm kiếm sâu do làm tăng độ trễ.

### 1.5.5. Qdrant và HNSW

Qdrant là cơ sở dữ liệu vector mã nguồn mở được dùng để lưu và tìm kiếm embedding [7]. Trong hệ thống, Qdrant lưu:

- Vector của chunk chi tiết.
- Vector của nút tóm tắt RAPTOR.
- Vector của nội dung hình ảnh.
- Payload phục vụ lọc theo tài liệu, trang, loại nút và phiên bản.

Qdrant sử dụng chỉ mục **Hierarchical Navigable Small World** để tìm láng giềng gần đúng [8]. HNSW tổ chức các vector thành đồ thị nhiều tầng. Các tầng trên hỗ trợ di chuyển nhanh qua không gian tìm kiếm, trong khi tầng dưới dùng để tinh chỉnh kết quả.

PostgreSQL lưu dữ liệu nghiệp vụ và metadata có quan hệ, còn Qdrant lưu chỉ mục vector phục vụ tìm kiếm ngữ nghĩa. Mỗi vector được liên kết với chunk trong PostgreSQL thông qua `vector_id`.

## 1.6. RAG phân cấp và thuật toán RAPTOR

### 1.6.1. Hạn chế của RAG phẳng

Trong RAG phẳng, các chunk được xem là những đơn vị ngang hàng. Phương pháp này hiệu quả với câu hỏi cục bộ nhưng gặp khó khăn với yêu cầu tóm tắt toàn bộ tài liệu hoặc tổng hợp thông tin nằm rải rác ở nhiều phần.

Một câu hỏi khái quát có thể không tương đồng mạnh với bất kỳ chunk chi tiết nào. Đây là lý do hệ thống bổ sung RAG phân cấp.

### 1.6.2. Nguyên lý RAPTOR

RAPTOR là phương pháp xây dựng cây tóm tắt từ các đoạn tài liệu [9]. Các chunk chi tiết tạo thành tầng lá. Những chunk có nội dung liên quan được phân cụm và tóm tắt thành các nút ở tầng cao hơn. Quá trình tiếp tục theo nhiều tầng để tạo biểu diễn từ chi tiết đến khái quát.

```text
Chunk chi tiết
   -> Tạo embedding
   -> Giảm chiều và phân cụm
   -> Tóm tắt từng cụm
   -> Tạo nút summary
   -> Tiếp tục xây tầng cao hơn
```

Khi nhận câu hỏi tổng hợp, hệ thống tìm kiếm trên các nút summary để xác định vùng nội dung phù hợp, sau đó truy xuất các chunk chi tiết bên dưới làm bằng chứng.

### 1.6.3. UMAP và Gaussian Mixture Model

Hệ thống sử dụng hai thuật toán chính trong quá trình phân cụm RAPTOR:

- **UMAP:** giảm số chiều của embedding để thuận lợi cho phân cụm.
- **Gaussian Mixture Model:** phân cụm vector theo mô hình xác suất.

GMM cho phép một chunk có thể thuộc nhiều cụm nếu nội dung liên quan đến nhiều chủ đề. Số cụm được lựa chọn dựa trên tiêu chí BIC trong phạm vi cấu hình cho phép.

Nếu UMAP không thực hiện được, hệ thống có thể sử dụng PCA làm phương án giảm chiều dự phòng. Nếu thiếu embedding hoặc thư viện phân cụm không sẵn sàng, hệ thống bỏ qua bước xây RAPTOR thay vì tạo cây không đáng tin cậy.

RAPTOR chỉ được áp dụng cho tài liệu đủ dài hoặc bảng tính đủ lớn. Việc xây cây được đưa vào tác vụ nền để không chặn quá trình tải tài liệu.

## 1.7. Kiến trúc phần mềm và công nghệ triển khai

### 1.7.1. Mô hình Client-Server

Client-Server là mô hình trong đó client gửi yêu cầu và server tiếp nhận, xử lý rồi trả kết quả. Trong hệ thống:

- Trình duyệt là client.
- Ứng dụng Next.js cung cấp giao diện người dùng.
- Django backend cung cấp REST API và luồng trả lời chat.
- Các dịch vụ dữ liệu và AI xử lý yêu cầu từ backend.

Client và server trao đổi qua HTTP hoặc HTTPS. Dữ liệu API chủ yếu sử dụng JSON; tệp được tải lên bằng `multipart/form-data`; câu trả lời có thể được truyền dần bằng Server-Sent Events.

Mô hình này giúp tách giao diện khỏi nghiệp vụ, cho phép nhiều client sử dụng chung backend và thuận lợi cho bảo trì. Hạn chế là server cần được bảo vệ, giám sát và cung cấp đủ tài nguyên để tránh trở thành điểm nghẽn.

### 1.7.2. Frontend Next.js

Next.js là framework xây dựng ứng dụng web dựa trên React [18]. React tổ chức giao diện theo component, còn Next.js cung cấp routing, tối ưu build và cấu trúc ứng dụng.

Frontend của đề tài sử dụng:

- **Next.js:** framework và hệ thống định tuyến.
- **React:** xây dựng giao diện theo component.
- **TypeScript:** kiểm tra kiểu dữ liệu.
- **TanStack Query:** quản lý server state và cache.
- **Axios:** giao tiếp với REST API.

Ứng dụng sử dụng cấu trúc App Router. Việc dùng Next.js không có nghĩa mọi trang đều được render phía server; phương thức render phụ thuộc vào cách triển khai từng trang và component.

Frontend cung cấp các chức năng quản lý tài liệu, thư mục, phòng ban, người dùng, vai trò và hội thoại RAG. Các thành phần xem trước PDF, Word và Excel giúp người dùng đối chiếu citation với tài liệu gốc.

### 1.7.3. Backend Django REST Framework

Django là framework web Python được sử dụng làm nền tảng backend [19]. Django cung cấp ORM, migration, hệ thống xác thực, middleware, quản lý cấu hình và các cơ chế bảo mật ứng dụng web.

Django REST Framework được sử dụng để xây dựng REST API. DRF hỗ trợ serializer, validation, authentication, permission và xử lý request/response.

Backend được tổ chức theo kiến trúc phân lớp:

```text
API
   -> Service
   -> Repository
   -> Django ORM
   -> PostgreSQL
```

Các dịch vụ xử lý tài liệu, embedding, retrieval, reranking và LLM được tách khỏi lớp API. Cách tổ chức này giúp giảm phụ thuộc và thuận lợi hơn khi kiểm thử hoặc thay đổi thành phần AI.

FastAPI là framework Python phù hợp với API bất đồng bộ và tự động sinh tài liệu OpenAPI. Tuy nhiên, backend hiện tại của đề tài sử dụng **Django và Django REST Framework, không sử dụng FastAPI**. FastAPI chỉ là công nghệ tham khảo, không phải thành phần trong kiến trúc triển khai.

### 1.7.4. PostgreSQL, Redis và Celery

PostgreSQL là hệ quản trị cơ sở dữ liệu quan hệ được dùng làm nguồn dữ liệu nghiệp vụ chính [10]. PostgreSQL lưu tài khoản, vai trò, quyền, phòng ban, thư mục, tài liệu, chunk, metadata embedding, phiên bản, hội thoại, tin nhắn và nhật ký kiểm toán.

Hệ thống sử dụng khóa ngoại, transaction, chỉ mục, JSON, Full-Text Search và chỉ mục GIN. Những tính năng này phù hợp với dữ liệu doanh nghiệp có quan hệ rõ ràng nhưng vẫn cần metadata linh hoạt.

Xử lý tài liệu là tác vụ tốn thời gian vì gồm parsing, chunking, embedding, OCR, xử lý hình ảnh và xây RAPTOR. Celery được sử dụng để thực hiện tác vụ ở tiến trình nền, còn Redis đóng vai trò message broker [11].

```text
Django tạo tác vụ
   -> Redis nhận thông điệp
   -> Celery Worker xử lý
   -> PostgreSQL lưu trạng thái
```

Nhờ xử lý bất đồng bộ, API có thể phản hồi sau khi tiếp nhận tài liệu mà không phải giữ kết nối cho đến khi toàn bộ pipeline hoàn thành.

### 1.7.5. Xác thực và phân quyền

JSON Web Token là chuẩn truyền các claim xác thực giữa client và server [12]. Hệ thống sử dụng access token để gọi API và refresh token để cấp lại access token khi cần.

Role-Based Access Control là mô hình gán quyền cho vai trò, sau đó gán vai trò cho người dùng [13]. Ngoài RBAC, hệ thống còn hỗ trợ quyền trực tiếp trên thư mục và tài liệu. Quyết định truy cập dựa trên vai trò, tài khoản, phòng ban, phạm vi personal/department/company và quyền kế thừa.

Quyền được kiểm tra trước khi truy xuất nội dung. Điều này bảo đảm các chunk ngoài phạm vi truy cập không được đưa vào ngữ cảnh của LLM.

### 1.7.6. Docker và kiến trúc triển khai

Docker đóng gói ứng dụng cùng dependency thành container. Docker Compose được sử dụng để định nghĩa và vận hành các dịch vụ [20]:

- Django backend.
- PostgreSQL.
- Qdrant.
- Redis.
- Celery worker.
- Máy chủ LLM `llama.cpp`.
- Máy chủ mô hình thị giác.

Frontend có cấu hình triển khai riêng bằng Next.js. Các volume được sử dụng để duy trì dữ liệu PostgreSQL, Qdrant, tệp tải lên và mô hình sau khi container được khởi động lại.

Kiến trúc của đề tài nên được mô tả là **ứng dụng phân lớp được triển khai bằng nhiều dịch vụ container**. Không nên khẳng định đây là microservices hoàn chỉnh vì các module backend vẫn cùng repository và chia sẻ mô hình dữ liệu, cấu hình và vòng đời triển khai.

## 1.8. Khoảng trống kỹ thuật và định hướng đóng góp của đề tài

Các công nghệ trình bày trong chương này như RAG, BM25, embedding, Qdrant, RAPTOR, OCR, mô hình thị giác-ngôn ngữ, RBAC và Celery là những nền tảng đã được công bố hoặc cung cấp sẵn. Vì vậy, đóng góp của đề tài không nằm ở việc đề xuất một mô hình ngôn ngữ hay một thuật toán truy xuất hoàn toàn mới. Giá trị chính của đề tài nằm ở việc **lựa chọn, điều chỉnh và kết hợp các kỹ thuật trên thành một hệ thống quản trị tri thức nội bộ có thể vận hành được**, phù hợp với đặc điểm tài liệu doanh nghiệp.

Qua phân tích cơ sở lý thuyết, đề tài xác định bốn khoảng trống cần giải quyết:

1. **Tài liệu doanh nghiệp có cấu trúc không đồng nhất.** Nội dung có thể nằm trong PDF, Word, Excel, CSV, văn bản thuần, bảng hoặc hình ảnh. Nếu chỉ trích xuất văn bản và chia đoạn theo kích thước cố định, hệ thống dễ làm mất quan hệ giữa trang, tiêu đề, hàng, cột và nội dung trực quan.
2. **Một chiến lược truy xuất duy nhất không phù hợp với mọi câu hỏi.** Tìm kiếm từ khóa phù hợp với mã số và cụm từ chính xác; tìm kiếm vector phù hợp với diễn đạt ngữ nghĩa; truy vấn bảng cần giữ cấu trúc hàng và cột; câu hỏi tổng quan trên tài liệu dài cần ngữ cảnh phân cấp.
3. **Câu trả lời của LLM cần có khả năng kiểm chứng.** Việc chỉ sinh câu trả lời tự nhiên là chưa đủ đối với dữ liệu nội bộ. Hệ thống cần cung cấp tên tài liệu, trang, sheet, đoạn trích hoặc hình ảnh làm bằng chứng, đồng thời kiểm tra mức độ bám nguồn của câu trả lời.
4. **Truy xuất tri thức phải tuân theo quyền truy cập.** Tài liệu không có quyền đọc không được xuất hiện trong kết quả tìm kiếm, ngữ cảnh RAG hoặc câu trả lời của mô hình.

Từ các khoảng trống trên, đề tài định hướng các đóng góp triển khai như sau:

| Khoảng trống | Định hướng giải quyết trong đề tài |
| --- | --- |
| Tài liệu đa định dạng và nhiều cấu trúc | Xây dựng pipeline page-aware/structured, chunking riêng cho văn bản và bảng tính, đồng thời xử lý ảnh bằng OCR và mô hình thị giác-ngôn ngữ. |
| Nhiều loại câu hỏi khác nhau | Xây dựng cơ chế định tuyến truy vấn, kết hợp deterministic retrieval, BM25, tìm kiếm vector, spreadsheet retrieval và RAPTOR. |
| Nguy cơ câu trả lời thiếu căn cứ | Xây dựng ngữ cảnh có đánh số nguồn, kiểm tra grounding và tạo citation tới trang, sheet, chunk hoặc asset. |
| Nguy cơ lộ dữ liệu nội bộ | Kết hợp JWT, RBAC, ACL và phạm vi personal/department/company; lọc tài liệu trước khi retrieval và trước khi tạo prompt. |

Các định hướng trên là cầu nối từ cơ sở lý thuyết sang phần phân tích, thiết kế và triển khai. Nội dung đóng góp cụ thể, phạm vi thực hiện và bằng chứng triển khai được trình bày tại Chương 3.

## 1.9. Kết luận chương

Chương này đã trình bày các cơ sở lý thuyết và công nghệ chính của đề tài, gồm hệ thống quản trị tri thức doanh nghiệp, Local AI, lượng tử hóa, GGUF, `llama.cpp`, Transformer, Qwen3, RAG đa phương thức, chunking, BGE-M3, tìm kiếm BM25-like, Hybrid Search, Weighted RRF, reranking, MMR, Qdrant, HNSW, RAPTOR, UMAP, GMM, OCR, Qwen2.5-VL, mô hình Client-Server, Next.js, Django REST Framework, PostgreSQL, Redis, Celery, JWT, RBAC và Docker.

Các nội dung trên tạo nền tảng cho việc phân tích yêu cầu, thiết kế kiến trúc và trình bày quá trình xây dựng hệ thống ở các chương tiếp theo. Trên nền tảng đó, đề tài tập trung đóng góp ở cấp độ thiết kế và tích hợp hệ thống: xử lý tài liệu đa cấu trúc, truy xuất thích ứng theo loại câu hỏi, kiểm chứng câu trả lời bằng nguồn và kiểm soát quyền xuyên suốt pipeline RAG.

## Tài liệu tham khảo

[1] A. Vaswani et al., “Attention Is All You Need,” 2017. https://arxiv.org/abs/1706.03762

[2] P. Lewis et al., “Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,” 2020. https://arxiv.org/abs/2005.11401

[3] J. Chen et al., “M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings,” 2024. https://arxiv.org/abs/2402.03216

[4] S. Robertson and H. Zaragoza, “The Probabilistic Relevance Framework: BM25 and Beyond,” 2009.

[5] G. V. Cormack, C. L. A. Clarke, and S. Büttcher, “Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods,” 2009.

[6] L. Gao, X. Ma, J. Lin, and J. Callan, “Precise Zero-Shot Dense Retrieval without Relevance Labels,” 2022. https://arxiv.org/abs/2212.10496

[7] Qdrant, “Qdrant Documentation.” https://qdrant.tech/documentation/

[8] Y. A. Malkov and D. A. Yashunin, “Efficient and Robust Approximate Nearest Neighbor Search Using HNSW Graphs,” 2020. https://arxiv.org/abs/1603.09320

[9] P. Sarthi et al., “RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval,” 2024. https://arxiv.org/abs/2401.18059

[10] PostgreSQL Global Development Group, “PostgreSQL Documentation.” https://www.postgresql.org/docs/

[11] Celery Project, “Celery Documentation.” https://docs.celeryq.dev/

[12] M. Jones, J. Bradley, and N. Sakimura, “JSON Web Token,” RFC 7519, 2015. https://datatracker.ietf.org/doc/rfc7519/

[13] R. Sandhu, D. Ferraiolo, and D. R. Kuhn, “The NIST Model for Role-Based Access Control,” 2000.

[14] GGML, “GGUF File Format.” https://github.com/ggml-org/ggml/blob/master/docs/gguf.md

[15] GGML Organization, “llama.cpp: LLM Inference in C/C++.” https://github.com/ggml-org/llama.cpp

[16] S. Bai et al., “Qwen2.5-VL Technical Report,” 2025. https://arxiv.org/abs/2502.13923

[17] Qwen Team, “Qwen3 Technical Report,” 2025. https://arxiv.org/abs/2505.09388

[18] Vercel, “Next.js App Router Documentation.” https://nextjs.org/docs/app

[19] Django Software Foundation, “Django Documentation.” https://docs.djangoproject.com/

[20] Docker Inc., “Docker Compose Documentation.” https://docs.docker.com/compose/
