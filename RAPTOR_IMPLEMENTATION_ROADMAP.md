# RAPTOR + Contextual Retrieval Roadmap

Tài liệu này mô tả lộ trình để nâng cấp pipeline hiện tại của đồ án thành một hệ RAG chất lượng cao hơn, có:

- parse theo trang thực tế của PDF/DOCX,
- chunk theo đoạn trong từng trang,
- mỗi chunk có summary riêng,
- hybrid retrieval + rerank,
- RAPTOR chỉ áp dụng có điều kiện cho tài liệu phù hợp,
- có đường lùi an toàn để vẫn giữ hệ thống chạy ổn định.

---

## 1. Mục tiêu cuối cùng

Hệ thống mục tiêu không còn chỉ là "chia chunk -> embed -> search" nữa. Thay vào đó:

1. Tài liệu được đọc theo trang hoặc theo layout logic của file.
2. Mỗi trang được tách thành các đoạn nhỏ hơn nếu cần.
3. Mỗi chunk có 2 lớp thông tin:
   - raw chunk: nội dung gốc để tra cứu chi tiết,
   - contextual summary: đoạn tóm tắt ngắn để thêm ngữ cảnh.
4. Tài liệu dài sẽ có thêm cây RAPTOR:
   - leaf chunks ở đáy cây,
   - summary nodes ở tầng cao hơn,
   - query có thể retrieve từ root/summary hoặc từ leaf chi tiết.
5. Query phức tạp sẽ đi qua bộ điều phối:
   - phân loại query,
   - chọn retrieval mode phù hợp,
   - rerank,
   - tổng hợp đáp án có trích dẫn.

---

## 2. Kiến trúc đề xuất

### 2.1. Ingest layer

Dùng pipeline:

1. Parse file.
2. Xác định page boundaries.
3. Tách page thành các paragraph/section.
4. Tạo chunk con trong từng page.
5. Tạo summary cho từng chunk.
6. Tạo contextual summary cho chunk dựa trên nguyên page hoặc văn bản liên quan.
7. Embed chunk raw và embed chunk contextual nếu cần.
8. Nếu tài liệu đạt điều kiện RAPTOR, tạo thêm summary nodes theo tầng.
9. Lưu metadata đầy đủ vào PostgreSQL + vector store.

### 2.2. Retrieval layer

Khi query:

1. Nếu query đơn giản -> hybrid search trên leaf chunks.
2. Nếu query có từ khóa, mã số, tên riêng -> ưu tiên lexical/BM25.
3. Nếu query cần nguyên cảnh -> ưu tiên contextual chunks.
4. Nếu query dài, tổng hợp, liên quan nhiều mục -> leo RAPTOR tree.
5. Rerank top-k kết quả trước khi đưa vào LLM.

### 2.3. Generation layer

Mô hình trả lời phải:

- dựa trên evidence,
- có citation,
- có chunk id / page id / summary node id nếu có,
- không bao giờ chỉ trả lời chạy theo tư duy tự do không có nguồn.

---

## 3. Lộ trình chi tiết theo từng bước

## Phase 0 - Ổn định hệ thống hiện tại

Mục tiêu: giữ nguyên hệ thống đang chạy, chỉ thêm metadata và chuẩn hóa luồng xử lý.

Công việc:

1. Chốt lại một schema thống nhất cho Document, DocumentChunk, DocumentEmbedding.
2. Thêm các trường metadata cần thiết:
   - page_number,
   - paragraph_index,
   - chunk_level,
   - parent_chunk_id,
   - summary_text,
   - contextual_text,
   - is_raptor_node,
   - raptor_level,
   - source_span.
3. Ghi rõ version của pipeline trong metadata để dễ rollback.
4. Giữ thread background hiện tại, chưa đổi sang job queue ngay.

Output mong đợi:

- Hệ thống vẫn upload bình thường.
- Có dữ liệu đầy đủ để phục vụ phase sau.

---

## Phase 1 - Parse theo page thật

Mục tiêu: không chỉ parse ra 1 khối text lớn, mà xác định rõ page boundaries.

### PDF

1. Giữ nguyên extractor hiện tại vì đã tối ưu.
2. Lấy số trang thật nếu có.
3. Gán mỗi đoạn text vào page tương ứng.
4. Nếu extractor chỉ trả markdown không có page mapping rõ ràng, cần lưu thêm:
   - page markers,
   - hoac page metadata tu PDF reader,
   - hoac mot parser bo tro de xac dinh page.

### DOCX

1. Đánh giá Docling nếu tốt hơn parser hiện tại (docx parser); nếu không, giữ nguyên.
2. Nếu dùng Docling: extract layout, font/style, tables/images.
3. Gán paragraph vào page logic nếu có thể.
4. Nếu không có page thực tế trong DOCX, dùng page logic theo block:
   - section,
   - heading,
   - paragraph group.

### Quy tắc page chunking

1. Mỗi page là đơn vị cha.
2. Trong page, mỗi đoạn văn / heading / table row là đơn vị con.
3. Nếu page quá dài, split tiếp theo câu và overlap nhỏ.
4. Nếu page quá ngắn, gom với page kế cận nếu cùng section.

Output mong đợi:

- Mỗi chunk luôn biết mình thuộc page nào.
- Demo có thể show "page-aware retrieval".

---

## Phase 2 - Chunk theo đoạn trong page

Mục tiêu: chunk không bị vô nghĩa trong trang.

Công việc:

1. Đổi chunker thành 2 tầng:
   - tang 1: page split,
   - tang 2: paragraph split trong page.
2. Mỗi paragraph chunk có overlap nhỏ giữa các chunk liên tiếp.
3. Không cắt ngang heading nếu có thể tránh được.
4. Đối với bảng biểu hoặc bullet list:
   - giữ nguyên block nếu nhỏ,
   - nếu dài thì split theo row hoặc bullet group.
5. Lưu chunk order theo:
   - page_number,
   - paragraph_index,
   - chunk_index.

Output mong đợi:

- Chunk có ý nghĩa hơn.
- Retrieval thất bại ít hơn so với cắt chuỗi dài vô ngữ.

---

## Phase 3 - Summary riêng cho mỗi chunk

Mục tiêu: mỗi chunk có 1 tóm tắt ngắn để phục vụ contextual retrieval.

### Cách làm

1. Mỗi chunk raw sẽ có 1 summary 1-3 câu.
2. Summary phải trả lời:
   - chunk này nói về gì,
   - chunk thuộc phần nào của tài liệu,
   - chunk liên quan đến biến thể / số liệu / mục nào.
3. Có thể tạo 2 loại summary:
   - local summary: tóm tắt nội dung chunk,
   - contextual summary: tóm tắt trong bối cảnh của tài liệu.
4. Lưu summary vào:
   - DB metadata,
   - vector store neu can truy van bang summary,
   - RAPTOR summary tree neu tai lieu du dieu kien.

### Cách sinh summary

#### Chiến lược lựa chọn LLM

**Dùng Ollama Qwen3-4B** (không dùng OpenAI):
- ✅ Chạy local, không tốn tiền API
- ✅ Model Qwen3-4B tốt cho tác vụ summarization tiếng Việt
- ✅ Sử dụng `LlamaClient` đã có sẵn trong backend

#### Prompt Template cho Qwen3-4B

```
Bạn là chuyên gia tóm tắt tài liệu kỹ thuật và pháp lý.
Nhiệm vụ: Tóm tắt đoạn text sau thành 1-3 câu ngắn gọn.

[CHUNK_CONTENT]

Yêu cầu tóm tắt:
- Trả lời: Đoạn này nói về gì?
- Giữ ý chính, không mất thông tin quan trọng
- Tối đa 150 ký tự
- Ngôn ngữ: Tiếng Việt

Tóm tắt:
```

#### Timing Strategy

**Case 1: Tài liệu ngắn (< 5 trang hoặc < 500 từ)**
- Sinh summary **SYNC** (đồng bộ) lúc ingest
- Time: ~1-3 giây mỗi chunk (acceptable)
- Lợi: Hoàn tất ngay, không cần xử lý background

**Case 2: Tài liệu lớn (≥ 5 trang hoặc ≥ 500 từ)**
- Sinh summary **ASYNC** (bất đồng bộ) qua background thread
- Có thể ghi status = 'pending_summary' lúc ingest
- Ghi status = 'summary_generated' khi hoàn tất
- Lợi: Không block upload flow

**Case 3: Nhu cầu chi phí cao (nhiều chunk × summarization)**
- Cache summary theo hash chunk
- TTL: 7 ngày (tương tự parse cache)
- Key: `summary:{file_hash}:{chunk_index}`

#### Implementation Code Example

```python
from services.ai.llama_client import LlamaClient
import hashlib

class ChunkSummaryService:
    def __init__(self):
        self.llama = LlamaClient()
        self.cache_ttl = 7 * 24 * 3600  # 7 days
    
    # Timing: SYNC cho file ngắn
    def generate_summary_sync(self, chunk_text: str) -> str:
        prompt = self._build_summary_prompt(chunk_text)
        summary = self.llama.complete(
            prompt=prompt,
            max_tokens=100,
            temperature=0.3,  # Thấp để output ổn định
            timeout=30
        )
        return summary.strip()
    
    # Timing: ASYNC cho file lớn
    def generate_summary_async(self, chunk_id: str, chunk_text: str):
        import threading
        thread = threading.Thread(
            target=self._summarize_in_background,
            args=(chunk_id, chunk_text)
        )
        thread.daemon = True
        thread.start()
    
    def _summarize_in_background(self, chunk_id: str, chunk_text: str):
        try:
            summary = self.generate_summary_sync(chunk_text)
            # Lưu vào DB
            chunk = DocumentChunk.objects.get(id=chunk_id)
            chunk.summary = summary
            chunk.save(update_fields=['summary'])
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
    
    # Cache strategy
    def get_or_generate_summary(self, chunk_text: str, chunk_hash: str) -> str:
        cache_key = f"summary:{chunk_hash}"
        
        # Kiểm tra cache
        cached = self.redis_client.get(cache_key)
        if cached:
            return cached
        
        # Sinh mới
        summary = self.generate_summary_sync(chunk_text)
        
        # Lưu cache
        self.redis_client.setex(cache_key, self.cache_ttl, summary)
        
        return summary
    
    def _build_summary_prompt(self, chunk_text: str) -> str:
        return f"""Bạn là chuyên gia tóm tắt tài liệu kỹ thuật và pháp lý.
Nhiệm vụ: Tóm tắt đoạn text sau thành 1-3 câu ngắn gọn.

[CHUNK_CONTENT]
{chunk_text}
[/CHUNK_CONTENT]

Yêu cầu tóm tắt:
- Trả lời: Đoạn này nói về gì?
- Giữ ý chính, không mất thông tin quan trọng
- Tối đa 150 ký tự
- Ngôn ngữ: Tiếng Việt

Tóm tắt:"""
```

#### Quy định về timing decision

```python
def should_generate_summary_sync(document_size: int, page_count: int) -> bool:
    """Quyết định có nên sinh summary SYNC hay ASYNC"""
    return page_count < 5 or document_size < 500000  # bytes
```

#### Benchmark hiệu suất

- **Parse time**: ~2-5 giây (tùy format)
- **Chunk time**: ~1 giây per 10KB text
- **Summary sync**: ~1-3 giây per chunk (650 tokens)
- **Summary async**: Background, không block

#### Lưu trữ output

- **summary_text**: Lưu text tóm tắt trong DB
- **metadata['summary_timestamp']**: Thời điểm sinh
- **metadata['summary_method']**: 'sync' hoặc 'async'
- **metadata['summary_model']**: 'qwen3-4b' hoặc model name

Output mong đợi:

- Mỗi chunk có 1 mô tả ngắn, rõ ý nghĩa.
- Query tương lai không bị mất context.

---

## Phase 4 - Contextual Retrieval

Mục tiêu: thêm ngữ cảnh vào chunk trước khi embed.

### Định nghĩa

Contextual chunk = raw chunk + context ngắn được sinh từ:

- ten file,
- title,
- page number,
- section heading,
- đoạn trước / sau,
- cac chuoi giong nhau trong cung page,
- metadata nghiep vu.

### Quy tắc contextualization

1. Context không được quá dài.
2. Chỉ thêm thông tin thực sự giúp truy hồi.
3. Không nhai lại toàn bộ tài liệu.
4. Context phải được prepended trước khi embed.
5. Có thể lưu:
   - raw_text,
   - contextual_text,
   - summary_text,
   - source_context.

### Lợi ích

- Chunk không bị "mất gốc" khi bị cắt nhỏ.
- Search theo semantic và lexical đều tốt hơn.
- RAG dễ trả lời đúng ngữ cảnh hơn.

---

## Phase 5 - Hybrid retrieval + rerank

Mục tiêu: không chỉ phụ thuộc vào embedding.

### Hybrid retrieval nên có

1. Dense retrieval cho ý nghĩa.
2. Sparse/lexical retrieval cho:
   - mã số,
   - tên file,
   - số trang,
   - tên người,
   - từ khóa chính xác,
   - cảnh báo, error code, điều khoản.
3. Rerank de chon top chunk tot nhat.

### Kịch bản nên ưu tiên lexical

- query có mã số văn bản,
- query có tên file,
- query có ID, code, điều khoản, số hiệu,
- query có tên riêng rất đặc thù.

### Kịch bản nên ưu tiên dense

- query hỏi ý nghĩa,
- query hỏi tóm tắt,
- query hỏi so sánh,
- query hỏi nguyên nhân.

### Rerank

1. Lấy top 20-50 candidate từ retrieval.
2. Rerank lại lấy top 5-10.
3. Đưa vào context cho LLM.

Output mong đợi:

- Recall tốt hơn.
- Sai số do nhiều chunk vô nghĩa giảm mạnh.

---

## Phase 6 - RAPTOR tree

Mục tiêu: chỉ áp dụng cho tài liệu phù hợp, tạo cây summary để tìm ở mức cao và mức thấp.

### 6.1. RAPTOR là gì trong đồ án này

RAPTOR se tao:

1. leaf nodes: chunk chi tiet,
2. summary nodes: tom tat theo nhom chunk,
3. higher-level summary nodes: tom tat cua tom tat,
4. root/cluster nodes: bieu dien y lon cua tai lieu.

### 6.2. Khi nào áp dụng RAPTOR

Ap dung RAPTOR khi file co mot trong cac dieu kien sau:

1. Tai lieu rat dai.
2. Tai lieu co cau truc nhieu tang.
3. Tai lieu co chuan muc, quy trinh, luat, bao cao, de cuong, tai lieu nghien cuu.
4. Query thuong can tong hop nhieu phan cua file.
5. File co nhieu heading, section, sub-section.
6. Tai lieu co nhieu trang va mot page khong du de hieu y nghia.

### 6.3. Không nên áp dụng RAPTOR khi

1. File ngan.
2. File chi la mot doan text it noi dung.
3. File chi can search nhanh theo tu khoa.
4. File co cau truc qua don gian.
5. File chi dung cho tra cuu nhanh, khong can summary tree.

### 6.4. Ngưỡng để xét RAPTOR

Để đơn giản, có thể dùng quy tắc ban đầu:

- neu file > 10 trang hoac > 3,000-5,000 tu: can xet RAPTOR,
- neu file co > 5 section/heading lon: can xet RAPTOR,
- neu file co nhieu bang, bullets, canh bao, quy trinh: can xet RAPTOR,
- neu file la PDF scan ngan, chi 1-3 trang: khong can RAPTOR,
- neu file la CV, thong bao ngan, form ngan: khong can RAPTOR.

Bạn có thể sửa ngưỡng này sau khi benchmark.

### 6.5. Cách build RAPTOR tree

1. Tao leaf chunks.
2. Cluster cac leaf chunks theo semantic similarity.
3. Sinh summary cho tung cluster.
4. Gom cac summary thanh cluster cap cao hon.
5. Lap lai toi khi con 1-2 summary cao nhat.
6. Luu parent-child relation ro rang.

### 6.6. Query RAPTOR

Co 2 mode:

1. Collapsed mode:
   - retrieve tren toan cay,
   - phu hop khi can lay dong noi dung quan trong nhat.
2. Tree traversal mode:
   - di tu summary cao xuong leaf,
   - phu hop khi can giai thich va co ngu canh day du.

### 6.7. Thực tế nên dùng mode nào

1. Query tong hop, tim y lon: collapsed.
2. Query can truc tiep dan giai, trich dan canh: tree traversal.
3. Query co the can ca 2: lay root summary truoc, sau do descend leaf.

Output mong đợi:

- Tai lieu dai co the tra loi tot hon so voi chunk thuong.
- Co the show duoc hinh cay tri thuc khi demo.

---

## Phase 7 - Agentic query planner

Mục tiêu: chỉ dùng khi câu hỏi thật sự phức tạp.

### Khi nào cần agent

1. Cau hoi co nhieu dieu kien.
2. Cau hoi so sanh nhieu tai lieu.
3. Cau hoi can suy luan qua nhieu buoc.
4. Cau hoi yeu cau tim nguyen nhan, hau qua, quy trinh.
5. Cau hoi co tu "tai sao", "lam the nao", "so sanh", "tong hop", "neu ... thi ...".

### Khi nào không cần agent

1. Cau hoi fact don gian.
2. Cau hoi chi can tim mot doan cu the.
3. Cau hoi chi can tra nguon.

### Luồng agent

1. Plan query.
2. Chia thanh subquery.
3. Chon retrieval mode cho tung subquery.
4. Retrieve + rerank.
5. Refine ket qua.
6. Synthesise final answer.

Output mong đợi:

- Query phuc tap tra loi co chieu sau hon.
- Demo do an co tinh "agentic" ro rang.

---

## 8. Quy tắc áp dụng RAPTOR theo loại file

### 8.1. PDF

Áp dụng RAPTOR nếu:

- PDF dai nhieu trang,
- PDF co nhieu heading/section,
- PDF la bao cao, luan van, tai lieu ky thuat, quy trinh, hop dong dai,
- PDF co cac trang noidung lien ket voi nhau.

Không áp dụng RAPTOR nếu:

- PDF ngan,
- PDF scan 1-2 trang,
- PDF chi la thong bao, ho so ngan, form.

### 8.2. Word / DOCX

Áp dụng RAPTOR nếu:

- file co nhieu heading cap 1/2/3,
- file chua quy trinh, guideline, policy, tai lieu huong dan,
- file co nhieu section can doc theo muc.

Không áp dụng RAPTOR nếu:

- file chi la 1-2 trang,
- file mo ta ngan,
- file khong co cau truc ro.

### 8.3. Excel / bảng biểu

Chưa nên áp RAPTOR là mặc định.

Neu can:

- chunk theo sheet,
- chunk theo row group,
- summary ngan cho group,
- retrieval chu yeu dua vao lexical + table-aware parsing.

### 8.4. Text / Markdown

Áp dụng RAPTOR nếu:

- noi dung dai,
- co nhieu muc,
- co nhieu section ro.

Nếu ngắn thì chỉ cần contextual retrieval + hybrid search.

---

## 9. Schema gợi ý

### Document

- id
- original_name
- file_type
- page_count
- chunking_strategy
- embedding_model
- status
- metadata

### DocumentChunk

- id
- document_id
- page_number
- paragraph_index
- chunk_index
- chunk_level
- parent_chunk_id
- node_type
- content
- summary_text
- contextual_text
- vector_id
- raptor_level
- metadata

### DocumentEmbedding

- chunk_id
- embedding_model
- embedding_dimension
- qdrant_vector_id
- embedding_vector
- embedding_computed_at

### Suggested addition

Nếu muốn RAPTOR ổn định hơn, nên thêm:

- `document_nodes` hoac dung ngay `document_chunks` voi `node_type = summary|detail|section`.

---

## 10. Thứ tự triển khai để an toàn nhất

### Bước 1

Không đổi retrieval ngay. Chỉ thêm metadata page/paragraph/summary.

### Bước 2

Cap nhat parser de co page-aware output va paragraph-aware output.

### Bước 3

Sinh summary cho tung chunk va luu cache.

### Bước 4

Them contextual text truoc khi embed.

### Bước 5

Them hybrid retrieval va rerank.

### Bước 6

Build RAPTOR tree cho file du dieu kien.

### Bước 7

Them query router/agent de tu dong chon:

- simple search,
- hybrid search,
- RAPTOR,
- multi-step agent.

### Bước 8

Benchmark va tinh chinh nguong.

---

## 11. Benchmark cần chạy

### Ingest metrics

- parse time,
- chunk time,
- summary time,
- embedding time,
- RAPTOR tree build time.

### Retrieval metrics

- recall@k,
- precision@k,
- MRR,
- nDCG neu can.

### Quality metrics

- do dung citation,
- do dung page reference,
- do dung theo case su dung,
- muc do giam hallucination.

### Demo scenarios

1. Tim 1 thong tin don gian.
2. Tim 1 so lieu co ma so.
3. Tong hop 1 quy trinh dai.
4. So sanh 2 phan trong 2 file khac nhau.
5. Cau hoi can leo RAPTOR.

---

## 12. Đề xuất implementation thực tế cho đồ án này

Nếu mục tiêu là đồ án hoàn chỉnh, mình khuyên:

### Level A - Bắt buộc

1. Parse theo page / paragraph.
2. Summary cho chunk.
3. Contextual retrieval.
4. Hybrid retrieval.
5. Rerank.

### Level B - Nên có

1. RAPTOR cho file dai.
2. Query router theo do kho.
3. Multi-stage retrieval.

### Level C - Nếu còn thời gian

1. Agentic deep-thinking query planner.
2. Cache summary va cache retrieval.
3. Auto benchmark dashboard.

---

## 13. Quy tắc ra quyết định RAPTOR nhanh

Dùng RAPTOR nếu file có ít nhất 2 trong số các điều kiện sau:

1. > 10 trang.
2. > 3,000-5,000 tu.
3. Co nhieu heading / subheading.
4. Co nhieu section can tong hop.
5. Query muc tieu thuong la hoi "y chinh", "tom tat", "so sanh", "ly do", "quy trinh".

Không dùng RAPTOR nếu:

1. File ngan.
2. File chi can search mot doan.
3. File la du lieu co cau truc don gian.
4. Chi can lexical search la du.

---

## 14. Ghi chú cuối

Mục tiêu của roadmap này là làm cho đồ án của bạn có 3 điểm mạnh:

1. Co co so khoa hoc ro rang.
2. Co thuc thi duoc tren code hien tai.
3. Co kha nang demo va bao ve tot.

Nếu triển khai đúng thứ tự, bạn sẽ có một hệ thống:

- hieu tai lieu theo trang,
- hieu doan trong trang,
- hieu ngu canh chunk,
- hieu cay tong hop RAPTOR,
- va biet luc nao can agent de suy luan.

---

## 15. Kết luận đề xuất

Giải pháp uy tín nhất và cũng thực tế nhất cho codebase hiện tại là: contextual retrieval + hybrid retrieval + reranking làm nền, rồi chỉ thêm RAPTOR cho tài liệu dài/quan trọng, và thêm một lớp agentic query router cho câu hỏi khó. Đây là hướng vừa đủ mạnh để đồ án nổi bật, vừa không quá nặng để vỡ tiến độ.

### Kế hoạch triển khai

Giữ nguyên pipeline parse/chunk/embedding hiện tại làm nền tảng, nhưng chỉnh ingestion để mỗi chunk được gắn thêm contextual summary ngắn trước khi embed. Đây là nâng cấp có lợi nhất trên chi phí thấp nhất.
Đổi embedding sang mô hình mạnh hơn và phù hợp retrieval hơn, ưu tiên BGE-M3 nếu bạn chấp nhận dùng model riêng cho embedding. Lý do là nó hỗ trợ dense + sparse + multi-vector, rất hợp với bài toán tài liệu tiếng Việt và câu hỏi kỹ thuật.
Thêm hybrid retrieval: semantic search bằng vector kết hợp lexical/BM25. Đây là phần rất quan trọng vì đồ án của bạn có tài liệu dạng PDF, Word, quy trình, thuật ngữ, mã tài liệu, tên riêng, số hiệu.
Thêm reranker ở bước sau retrieval để chọn top kết quả tốt nhất trước khi trả lời. Cái này giúp giảm nhiễu rất rõ.
Chỉ áp RAPTOR cho nhóm tài liệu dài, nhiều tầng, nhiều mục hoặc báo cáo lớn. Không nên áp RAPTOR cho toàn bộ file vì ingest sẽ phức tạp và tốn công hơn mức cần thiết.
Thêm agentic query planner cho các câu hỏi khó, kiểu cần so sánh, tổng hợp nhiều phần, truy nguyên nhân, hoặc cần nhiều bước suy luận. Câu hỏi đơn giản vẫn đi đường ngắn.
Chuẩn hóa reprocess, job queue, và logging để pipeline có thể chạy lại, theo dõi, và demo ổn định.

### Thiết kế tối ưu nhất cho đồ án

**Tầng ingest:**
Parse PDF bằng extractor hiện có.
Parse Word bằng docx parser hiện có.
Chunk theo cấu trúc tài liệu.
Tạo contextual chunk.
Embed bằng model tốt hơn.
Lưu leaf chunks, summary chunks, và metadata.

**Tầng retrieval:**
Bước 1: hybrid retrieve.
Bước 2: rerank.
Bước 3: nếu tài liệu dài thì leo cây RAPTOR.
Bước 4: nếu query phức tạp thì agent phân rã truy vấn.

**Tầng generation:**
Dùng LLM hiện tại để tổng hợp câu trả lời.
Bắt buộc trả nguồn, chunk id, và nếu có thì summary node id.

### Cách làm để đồ án "hoàn thiện nhất"

Làm MVP mạnh trước: contextual retrieval + hybrid search + rerank.
Sau đó thêm RAPTOR có điều kiện cho tài liệu dài.
Cuối cùng mới thêm agentic planner cho query phức tạp.
Làm benchmark rõ ràng trước/sau:
recall@k
precision@k
latency ingest
latency query
tỷ lệ trả lời đúng cho bộ câu hỏi test tự tạo
Demo phải có 3 chế độ:
tìm nhanh theo tài liệu thường
tìm sâu cho tài liệu dài bằng RAPTOR
hỏi khó bằng agentic query

### Nếu chỉ chọn một hướng duy nhất

Tôi khuyên chọn: contextual retrieval + hybrid retrieval + reranker làm lõi, RAPTOR là lớp nâng cao cho tài liệu dài, agentic planner là lớp điều phối cho query khó. Đây là phương án cân bằng nhất giữa chất lượng, tính thuyết phục khi bảo vệ, và độ khả thi khi triển khai trên project hiện tại.

---

## 16. Ví dụ triển khai RAPTOR

Dựa trên bài viết "RAPTOR: A Smarter Way to Retrieve and Use Information in AI" của Tuhin Sharma, dưới đây là các bước triển khai RAPTOR với ví dụ thực tế sử dụng LlamaIndex và OpenAI API.

### Công cụ đã sử dụng:
- ChromaDB: Cơ sở dữ liệu vector để lưu trữ embedding.
- LlamaIndex: Công cụ xây dựng và truy vấn cơ sở tri thức AI.
- OpenAI API: Sử dụng GPT-4 để tóm tắt và trả lời.

### Bước 1: Cài đặt các thư viện cần thiết
```
!pip install -r requirements.txt
```

### Bước 2: Thiết lập khóa API
```python
import nest_asyncio 
import os 

if "OPENAI_API_KEY" not in os.environ: 
    os.environ["OPENAI_API_KEY"] = "your-openai-api-key"
    
nest_asyncio.apply()
```

### Bước 3: Tải xuống các bài nghiên cứu mẫu
Tải 2 bài nghiên cứu về LLM trong lĩnh vực tài chính.
```
!wget https://arxiv.org/pdf/2309.13064 -O ./invest_lm.pdf 
!wget https://arxiv.org/pdf/2306.12659 -O ./instruct_fingpt.pdf
```

### Bước 4: Tải tài liệu
```python
from llama_index.core import SimpleDirectoryReader 

fin_documents = SimpleDirectoryReader(input_files=["./invest_lm.pdf", "./instruct_fingpt.pdf"]).load_data()
```

### Bước 5: Khởi tạo cơ sở dữ liệu vector
```python
import chromadb 
from llama_index.vector_stores.chroma import ChromaVectorStore 

client = chromadb.PersistentClient(path="./finance_knowledge_db") 
collection = client.get_or_create_collection("fin_raptor") 

vector_store = ChromaVectorStore(chroma_collection=collection)
```

### Bước 6: Định nghĩa Mô-đun Tóm tắt
```python
from llama_index.llms.openai import OpenAI 
from llama_index.packs.raptor.base import SummaryModule 

summary_prompt = "Với tư cách là người tóm tắt chuyên nghiệp, hãy tạo một bản tóm tắt ngắn gọn và đầy đủ về văn bản được cung cấp, \
                    cho dù đó là bài báo, bài đăng, cuộc hội thoại hoặc đoạn văn với càng nhiều chi tiết càng tốt."

summary_module = SummaryModule( 
    llm=OpenAI(model="gpt-3.5-turbo", temperature=0.1), summary_prompt=summary_prompt, num_workers=16
)
```

### Bước 7: Định nghĩa gói RAPTOR và nhập các tài liệu
```python
from llama_index.core.node_parser import SentenceSplitter 
from llama_index.embeddings.openai import OpenAIEmbedding 
from llama_index.packs.raptor import RaptorPack 

raptor_pack = RaptorPack( 
    fin_documents, 
    embed_model=OpenAIEmbedding( 
        model="text-embedding-3-small"
    ),   # được sử dụng để nhúng các cụm
    vector_store=vector_store,   # được sử dụng để lưu trữ
    similarity_top_k=2,   # top k cho mỗi lớp, hoặc top-k tổng thể cho chế độ thu gọn
    mode="collapsed",   # đặt chế độ mặc định
    transformations=[ 
        SentenceSplitter(chunk_size=400, chunk_overlap=50) 
    ],   # các phép biến đổi được áp dụng cho quá trình nhập
    summary_module=summary_module,   # được sử dụng để tạo tóm tắt
)
```

### Bước 8: Truy vấn RAPTOR để tìm câu trả lời
Có hai chế độ: collapsed tree và tree traversal.

**Chế độ thu gọn cây:**
```python
nodes = raptor_pack.run( 
    "InvestLM được so sánh với những tiêu chuẩn cơ sở nào?", mode="collapsed"
) 
print(len(nodes)) 
print(nodes[0].text)
```

**Chế độ duyệt cây:**
```python
nodes = raptor_pack.run( 
    "InvestLM được so sánh với những tiêu chuẩn cơ sở nào?", mode="tree_traversal"
) 
print(len(nodes)) 
print(nodes[0].text)
```

### Bước 9: Định nghĩa bộ truy xuất và công cụ truy vấn
```python
from llama_index.packs.raptor import RaptorRetriever 
from llama_index.embeddings.openai import OpenAIEmbedding 
from llama_index.vector_stores.chroma import ChromaVectorStore 
from llama_index.llms.openai import OpenAI 
import chromadb 

client = chromadb.PersistentClient(path="./finance_knowledge_db") 
collection = client.get_or_create_collection("fin_raptor") 
vector_store = ChromaVectorStore(chroma_collection=collection) 

retriever = RaptorRetriever( 
    [], 
    embed_model=OpenAIEmbedding( 
        model="text-embedding-3-small"
    ),   
    vector_store=vector_store,   # được sử dụng để lưu trữ
    similarity_top_k=2,   # top k cho mỗi lớp, hoặc top-k tổng thể cho chế độ thu gọn
    mode="tree_traversal",   # đặt chế độ mặc định
) 

from llama_index.core.query_engine import RetrieverQueryEngine 

query_engine = RetrieverQueryEngine.from_args( 
    retriever, llm=OpenAI(model="gpt-4o-mini", temperature=0.1) 
)
```

### Bước 10: Đặt câu hỏi
```python
query = "InvestLM được so sánh với những tiêu chuẩn cơ sở nào?"
response = query_engine.query(query) 
print(str(response))
```

### Tác động thực tế
RAPTOR có thể áp dụng cho:
- Phân tích văn bản pháp lý.
- Tóm tắt nghiên cứu khoa học.
- Báo cáo tài chính.

### Tài liệu tham khảo
- https://arxiv.org/html/2401.18059v1
- https://docs.llamaindex.ai/en/stable/api_reference/packs/raptor/
- https://github.com/tuhinsharma121/ai-playground/
- https://github.com/tuhinsharma121/ai-playground/blob/master/rag/raptor/rag-raptor-llamaindex.ipynb
