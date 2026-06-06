"""
Chat Service - Bộ điều phối (Orchestrator) hệ thống RAG.
Quy trình: 
1. Nhận yêu cầu của User
2. Lấy lịch sử chat via MessageRepository
3. Tìm kiếm kiến thức liên quan từ Vector DB (Qdrant) [khi có tài liệu đính kèm]
4. Xây dựng Prompt tổng hợp
5. Gọi LLM (LlamaClient) 
6. Lưu tin nhắn vào Database via MessageRepository

Pattern:
    ✅ CORRECT: Service → ConversationRepository/MessageRepository → ORM
    ❌ NEVER: Service → Conversation.objects.*, Message.objects.* directly
"""
import logging
import re
import time
import unicodedata
from typing import List, Dict, Any, Optional, Tuple, Generator
from django.apps import apps
from django.conf import settings
from django.utils import timezone
from core.exceptions import BusinessLogicError, LLMServiceError
from services.ai.llama_client import LlamaClient
from services.ai.embedding_client import EmbeddingClient
from services.ai.qdrant_client import QdrantClient
from services.chat_attachment_service import ChatAttachmentService
from repositories.conversation_repository import ConversationRepository
from repositories.message_repository import MessageRepository
from repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)


class ChatService:
    """
    RAG Chat Orchestrator - Trái tim của hệ thống hỏi đáp tri thức
    
    ✅ CORRECT DATA FLOW:
    View → ChatService → ConversationRepository/MessageRepository → ORM → Models
    
    RAG Pipeline (khi có tài liệu đính kèm):
    1. Nhận query + document_ids/folder_ids
    2. Resolve folder_ids → document_ids (expand all docs in folders)
    3. Nếu không có IDs từ request → đọc từ ConversationAttachedDocument trong DB
    4. Hybrid retrieval (BM25 + Vector) → rerank → top-K chunks
    5. Build context prompt với citations
    6. Stream LLM response
    """
    
    SYSTEM_PROMPT = """Bạn là trợ lý ảo AI thông minh, hỗ trợ người dùng giải đáp các thắc mắc.
    Nếu có 'Nội dung tham khảo' bên dưới, hãy ưu tiên sử dụng nó để trả lời và trích dẫn nguồn (ví dụ: '[Nguồn: Tên tài liệu.pdf]').
    Nếu nội dung tham khảo không chứa thông tin cần thiết hoặc không có tài liệu liên quan, bạn hãy sử dụng kiến thức tổng quát của mình để trả lời người dùng một cách chính xác và hữu ích nhất.
    Luôn duy trì thái độ chuyên nghiệp, lịch sự và hỗ trợ.
    """

    # Universal RAG prompt: strict grounding, complete extraction when asked, compact otherwise.
    RAG_SYSTEM_PROMPT = """Bạn là trợ lý RAG cho tài liệu nội bộ. Chỉ trả lời dựa trên tài liệu tham khảo được cung cấp.

Nguyên tắc bắt buộc:
1. Chỉ dùng "NỘI DUNG TÀI LIỆU THAM KHẢO" để trả lời. Không dùng kiến thức bên ngoài, không suy đoán.
2. Trả lời đúng câu hỏi hiện tại. Bỏ qua đoạn tham khảo không trả lời trực tiếp câu hỏi.
3. Nếu tài liệu không đủ thông tin, nói rõ: "Tài liệu không có thông tin này." Nếu chỉ thiếu một phần, trả lời phần có bằng chứng và nêu phần nào không thấy trong tài liệu.
4. Mỗi ý quan trọng phải có trích dẫn đúng dạng: [Nguồn: tên_file, trang X] [1]. Số [1], [2] phải đúng số NGUỒN trong tài liệu tham khảo.
5. Luôn viết tiếng Việt có dấu. Không viết không dấu như "Co anh phu hop" hoặc "Nguon".
6. Nếu câu hỏi yêu cầu xem/hiển thị ảnh và phần "THÔNG TIN HÌNH ẢNH TRONG TÀI LIỆU" có ảnh phù hợp, trả lời ngắn gọn rằng có ảnh phù hợp và nêu vị trí ảnh. Ảnh sẽ được giao diện hiển thị, không cần tạo markdown image.
7. Với tài liệu nội bộ dạng quy định, quy chế, nội quy, điều khoản, chính sách, quy trình, biểu mẫu, bảng lương, KPI hoặc thống kê: phải giữ đúng cấu trúc nguồn. Không tự rút gọn, không bỏ bullet/hàng/cột nếu người dùng hỏi "các", "những", "nội dung", "bao gồm", "gồm", "quy định", "quy chế", "điều khoản", "biểu mẫu", "bảng".
8. Nếu nguồn chỉ có một phần nội dung liên quan, trả lời phần có bằng chứng và nói rõ "Tài liệu tham khảo hiện chỉ cung cấp phần này". Không tự bổ sung phần còn thiếu.

Cách làm việc:
1. Tự xác định kiểu câu hỏi:
   - Định nghĩa/giải thích: trả lời rõ khái niệm và các ý giải thích có trong tài liệu.
   - Liệt kê/đầy đủ/chi tiết: trích xuất đầy đủ các mục chính, mục con, dấu gạch, số thứ tự liên quan.
   - So sánh: nếu điểm giống, khác, tiêu chí so sánh có trong tài liệu thì trình bày theo bảng hoặc bullet.
   - Quy trình/các bước: giữ đúng thứ tự bước trong tài liệu.
    - Số liệu/bảng biểu: chép đúng số, đơn vị, điều kiện, mốc thời gian.
    - Bảng dữ liệu / hàng cột: nếu tài liệu có bảng (dạng |cột1|cột2| hoặc bảng HTML/Excel/DOCX), PHẢI trả lời bằng bảng markdown giữ NGUYÊN cấu trúc |cột|cột|, không chuyển thành bullet hay paragraph. Giữ tên cột và số liệu đúng như tài liệu. Nếu bảng dài, trả lời toàn bộ bảng theo phần nguồn được cung cấp, không cắt xén phần đã có trong nguồn.
    - Nếu bảng trong nguồn bị parse thành text phẳng, các dòng bắt đầu bằng số thứ tự như "1 Email ...", "2 Mật khẩu ..." là CÁC HÀNG DỮ LIỆU. Không được dùng số bảng (ví dụ Bảng 10, Bảng 34) làm STT của hàng. Không được tạo bảng chỉ có header trống khi nguồn có dòng dữ liệu.
    - Thuật ngữ / định nghĩa: chỉ khi người dùng hỏi ý nghĩa của một khái niệm thì mới trả lời theo kiểu giải thích ngắn, không lẫn với role bảng.
   - Hỏi xem ảnh/hình/minh chứng: trả lời ngắn gọn "Có ảnh phù hợp" kèm vị trí ảnh và trích dẫn; không lặp lại mô tả caption dài nếu không cần.
2. Khi câu hỏi yêu cầu đầy đủ, giữ cấu trúc tài liệu: mục chính -> ý con -> chi tiết.
3. Khi câu hỏi không yêu cầu đầy đủ, trả lời ngắn gọn, đúng trọng tâm, vẫn phải có trích dẫn.
4. Nếu các đoạn tài liệu mâu thuẫn nhau, nêu cả hai thông tin và trích dẫn từng nguồn.
5. Nếu nguồn không có trang thì dùng vị trí có trong NGUỒN. Không gọi chunk kỹ thuật là "đoạn" trong trích dẫn hiển thị cho người dùng.
6. Không viết lời dẫn dài, không nhắc lại quy tắc, không nói về quá trình suy luận nội bộ."""

    def __init__(self):
        """Khởi tạo với các repository và client AI"""
        self.llama = LlamaClient()
        self.embedding = EmbeddingClient()
        self.qdrant = QdrantClient()
        # ✅ CORRECT: Use repositories instead of ORM direct
        self.conversation_repo = ConversationRepository()
        self.message_repo = MessageRepository()
        self.document_repo = DocumentRepository()
        self.chat_attachment_service = ChatAttachmentService()
        # QueryRouter khởi tạo lazy (tránh overhead khi không cần RAG)
        self._router = None

    def _get_router(self):
        """Lazy-init QueryRouter để tránh overhead khi không cần RAG."""
        if self._router is None:
            from services.retrieval.query_router import QueryRouter
            self._router = QueryRouter(
                qdrant_client=self.qdrant,
                embedding_client=self.embedding,
                llama_client=self.llama,
            )
        return self._router

    def _get_intent_classifier(self):
        """Lazy-init QueryIntentClassifier."""
        if not hasattr(self, '_intent_classifier'):
            from services.retrieval.query_intent import QueryIntentClassifier
            self._intent_classifier = QueryIntentClassifier(embedding_client=self.embedding)
        return self._intent_classifier

    def _get_query_intent(self, query: str):
        """Classify query intent once and cache."""
        if not hasattr(self, '_query_intent_cache'):
            self._query_intent_cache = {}
        key = query.strip()[:80]
        if key not in self._query_intent_cache:
            classifier = self._get_intent_classifier()
            intent = classifier.classify(query)
            config = classifier.get_retrieval_config(intent)
            self._query_intent_cache[key] = (intent, config)
        return self._query_intent_cache[key]

    def _normalize_query_text(self, text: str) -> str:
        """Lowercase Vietnamese text and remove accents for intent checks."""
        normalized = unicodedata.normalize('NFD', text or '')
        without_marks = ''.join(
            ch for ch in normalized
            if unicodedata.category(ch) != 'Mn'
        )
        without_marks = (
            without_marks
            .replace('đ', 'd').replace('Đ', 'D')
            .replace('Ä‘', 'd').replace('Ä', 'd')
        )
        without_punctuation = re.sub(r'[^\w\s]+', ' ', without_marks.lower())
        return re.sub(r'\s+', ' ', without_punctuation).strip()

    def _extract_attribute_section_request(self, query: str) -> Dict[str, str]:
        """Detect generic "attribute of subject" section requests.

        Examples: "chuc nang nhiem vu cua phong X", "quyen han cua ban Y".
        The subject is used as the anchor; the attribute terms help classify the
        query as a section/list request without hardcoding a specific document.
        """
        query_norm = self._normalize_query_text(query)
        if not query_norm:
            return {}

        attribute_pattern = (
            r'\b(chuc nang|nhiem vu|quyen han|trach nhiem|vai tro|'
            r'chuc trach|nhiem quyen|moi quan he)\b'
        )
        if not re.search(attribute_pattern, query_norm):
            return {}

        subject = ''
        attribute_matches = list(re.finditer(attribute_pattern, query_norm))
        first_attribute = attribute_matches[0] if attribute_matches else None
        if first_attribute:
            # Prefer a relation that appears after the requested attribute.
            # In "cho toi noi dung cua Chuc nang, nhiem vu cua phong X",
            # the first "cho" is only the command prefix, not the subject.
            tail = query_norm[first_attribute.end():]
            relation_match = re.search(r'\b(?:cua|cho|ve)\s+(.+)$', tail)
            if relation_match:
                subject = relation_match.group(1)

        if not subject:
            relation_matches = list(re.finditer(r'\b(?:cua|cho|ve)\s+(.+)$', query_norm))
            if relation_matches:
                subject = relation_matches[-1].group(1)

        if not subject:
            subject_match = re.search(
                rf'(.+?)\s+(?:co\s+|gom\s+|bao\s+gom\s+)?{attribute_pattern}',
                query_norm,
            )
            if subject_match:
                subject = subject_match.group(1)

        subject = re.sub(
            r'\b(toi|minh|hay|cho|biet|cho toi biet|muon|can|xem|lay|trich|'
            r'noi dung|la gi|nhu the nao|gom|bao gom|gom nhung gi|'
            r'nhung gi|gi|nao|cac|nhung|cua|ve)\b',
            ' ',
            subject,
        )
        subject = re.sub(attribute_pattern, ' ', subject)
        subject = re.sub(r'\s+', ' ', subject).strip(' .:-')
        if len(subject) < 4:
            return {}

        attributes = ' '.join(dict.fromkeys(re.findall(attribute_pattern, query_norm)))
        heading = re.sub(r'\s+', ' ', f"{attributes} {subject}").strip()
        return {'subject': subject, 'attributes': attributes, 'heading': heading}

    def _extract_requested_heading(self, query: str) -> str:
        """Extract a likely section heading from queries asking for full section content."""
        query_norm = self._normalize_query_text(query)
        if not query_norm:
            return ''

        figure_match = re.search(r'\b(?:hinh|figure|image|anh)\s*\d+\b.*', query_norm)
        if figure_match:
            heading = figure_match.group(0)
            heading = re.sub(
                r'\b(toi|minh|muon|can|xem|lay|trich|in|hien|thi|noi dung|cua|ve)\b',
                ' ',
                heading,
            )
            heading = re.sub(r'\s+', ' ', heading).strip(' .:-')
            return heading if len(heading) >= 8 else ''

        attribute_request = self._extract_attribute_section_request(query)
        if attribute_request.get('subject'):
            return attribute_request.get('heading') or attribute_request['subject']

        if not any(marker in query_norm for marker in ('noi dung', 'toan bo', 'day du', 'muc', 'phan', 'bang', 'danh sach', 'section', 'chuong')):
            return ''

        heading = ''
        for marker in ('noi dung', 'bang', 'danh sach', 'muc', 'phan', 'section', 'chuong'):
            marker_text = f' {marker} '
            if marker_text in f' {query_norm} ':
                heading = query_norm.split(marker, 1)[1]
                break
        if not heading:
            heading = query_norm

        heading = re.sub(
            r'\b(toi|minh|muon|can|xem|lay|trich|in|ra|toan bo|day du|chi tiet|noi dung|cua|ve|phan|muc|bang|danh sach)\b',
            ' ',
            heading,
        )
        heading = re.sub(r'\s+', ' ', heading).strip(' .:-')
        return heading if len(heading) >= 8 else ''

    def _extract_requested_table_number(self, query: str) -> str:
        """Return the table number when the user asks for an exact Bảng/Table N."""
        query_norm = self._normalize_query_text(query)
        if not query_norm:
            return ''
        match = re.search(r'\b(?:bang|table)\s*(\d{1,3})\b', query_norm)
        return match.group(1) if match else ''

    def _is_specific_image_query(self, query: str) -> bool:
        """True when the user asks for a particular figure/image such as "Hinh 2"."""
        query_norm = self._normalize_query_text(query)
        if not query_norm:
            return False
        return bool(re.search(r'\b(?:hinh|figure|image|anh)\s*\d+\b', query_norm))

    def _requested_image_limit(self, query: str, default_specific: Optional[int] = 1) -> Optional[int]:
        """Return requested image count. None means no explicit cap/all images."""
        query_norm = self._normalize_query_text(query)
        if not query_norm:
            return default_specific

        if any(marker in query_norm for marker in ('tat ca', 'toan bo', 'liet ke', 'danh sach', 'all images', 'all image')):
            return None

        digit_match = re.search(r'\b(\d{1,3})\s*(?:anh|hinh|hinh anh|image|images|photo|photos)\b', query_norm)
        if digit_match:
            return max(1, min(100, int(digit_match.group(1))))

        word_counts = {
            'mot': 1,
            'hai': 2,
            'ba': 3,
            'bon': 4,
            'tu': 4,
            'nam': 5,
            'sau': 6,
            'bay': 7,
            'tam': 8,
            'chin': 9,
            'muoi': 10,
        }
        word_match = re.search(r'\b(mot|hai|ba|bon|tu|nam|sau|bay|tam|chin|muoi)\s*(?:anh|hinh|hinh anh|image|images|photo|photos)\b', query_norm)
        if word_match:
            return word_counts.get(word_match.group(1), default_specific)

        return default_specific if self._is_specific_image_query(query) else None

    def _retrieve_assets_for_exact_image(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        max_assets: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Attach image assets near an exact figure-caption chunk."""
        if not candidates or not self._is_specific_image_query(query):
            return []

        chunk_ids = [c.get('chunk_id') for c in candidates if c.get('chunk_id')]
        document_ids = list({str(c.get('document_id')) for c in candidates if c.get('document_id')})
        pages = list({c.get('page') for c in candidates if c.get('page')})
        if not document_ids or (not chunk_ids and not pages):
            return []

        heading_norm = self._extract_requested_heading(query)
        figure_match = re.search(r'\b(?:hinh|figure|image|anh)\s*(\d+)\b', self._normalize_query_text(query))
        figure_token = f"hinh {figure_match.group(1)}" if figure_match else ''
        requested_figure_number = figure_match.group(1) if figure_match else ''
        requested_limit = max_assets if max_assets is not None else self._requested_image_limit(query, default_specific=1)

        try:
            from django.db.models import Q

            DocumentAsset = apps.get_model('documents', 'DocumentAsset')
            DocumentChunk = apps.get_model('documents', 'DocumentChunk')
            filters = Q(document_id__in=document_ids, is_deleted=False)
            location_filter = Q()
            if chunk_ids:
                location_filter |= Q(chunk_id__in=chunk_ids)
            if pages:
                location_filter |= Q(page_number__in=pages)
            if location_filter:
                filters &= location_filter

            assets = list(
                DocumentAsset.objects.select_related('chunk')
                .filter(filters)
                .order_by('page_number', 'created_at')[: (max(requested_limit * 3, 12) if requested_limit else 100)]
            )

            selected_asset = None
            if requested_figure_number and len(assets) > 1:
                page_numbers = [page for page in pages if page]
                page_figure_numbers: Dict[int, List[str]] = {}
                chunk_rows = (
                    DocumentChunk.objects.filter(
                        document_id__in=document_ids,
                        page_number__in=page_numbers,
                        node_type='detail',
                        is_deleted=False,
                    )
                    .order_by('page_number', 'chunk_index')
                    .values('page_number', 'content')
                )
                for row in chunk_rows:
                    page_number = row.get('page_number')
                    if not page_number:
                        continue
                    numbers = page_figure_numbers.setdefault(int(page_number), [])
                    for number in re.findall(r'\bhinh\s*(\d+)\b', self._normalize_query_text(row.get('content') or '')):
                        if number not in numbers:
                            numbers.append(number)

                for page_number in page_numbers:
                    page_assets = [a for a in assets if int(a.page_number or 0) == int(page_number)]
                    figures_on_page = page_figure_numbers.get(int(page_number), [])
                    if requested_figure_number not in figures_on_page or not page_assets:
                        continue

                    page_assets.sort(
                        key=lambda asset: float((asset.position_in_document or {}).get('y') or 0.0)
                    )
                    if len(figures_on_page) > 1 and len(page_assets) > 1:
                        figure_idx = figures_on_page.index(requested_figure_number)
                        asset_idx = round(figure_idx * (len(page_assets) - 1) / (len(figures_on_page) - 1))
                    else:
                        asset_idx = 0
                    selected_asset = page_assets[max(0, min(asset_idx, len(page_assets) - 1))]
                    break

                if selected_asset and requested_limit == 1:
                    assets = [selected_asset]

            scored_assets: List[Tuple[float, Any]] = []
            selected_asset_id = str(selected_asset.id) if selected_asset else ''
            selected_asset_y = (
                float((selected_asset.position_in_document or {}).get('y') or 0.0)
                if selected_asset else None
            )
            for asset in assets:
                linked_text = ''
                try:
                    linked_text = asset.chunk.content if asset.chunk_id and asset.chunk else ''
                except Exception:
                    linked_text = ''
                combined_norm = self._normalize_query_text(
                    ' '.join([
                        asset.caption or '',
                        asset.ocr_text or '',
                        asset.context_text or '',
                        linked_text or '',
                    ])
                )

                score = 0.55
                if figure_token and figure_token in combined_norm:
                    score += 0.35
                if heading_norm and heading_norm in combined_norm:
                    score += 0.25
                if asset.chunk_id and str(asset.chunk_id) in {str(cid) for cid in chunk_ids}:
                    score += 0.2
                if selected_asset_id and str(asset.id) == selected_asset_id:
                    score += 0.4
                scored_assets.append((min(1.25, score), asset))

            scored_assets.sort(
                key=lambda item: (
                    item[0],
                    -abs(float((item[1].position_in_document or {}).get('y') or 0.0) - selected_asset_y)
                    if selected_asset_y is not None else 0.0,
                    (float(item[1].image_width or 0.0) * float(item[1].image_height or 0.0)),
                ),
                reverse=True,
            )

            result = []
            seen = set()
            for score, asset in scored_assets:
                if str(asset.id) in seen:
                    continue
                seen.add(str(asset.id))
                result.append({
                    'chunk_id': '',
                    'document_id': str(asset.document_id),
                    'score': score,
                    'source': 'asset',
                    'snippet': (asset.caption or '')[:300],
                    'asset_id': str(asset.id),
                    'asset_caption': asset.caption or '',
                    'asset_image_path': asset.image_path,
                    'asset_page_number': asset.page_number,
                    'asset_sheet_name': asset.sheet_name,
                    'asset_anchor_cell': asset.anchor_cell,
                    'asset_paragraph_index': asset.paragraph_index,
                    'asset_position_in_document': asset.position_in_document or {},
                    'asset_context_text': '',
                    'asset_ocr_text': asset.ocr_text or '',
                    'asset_linked_chunk_text': (asset.chunk.content or '') if asset.chunk_id and asset.chunk else '',
                    '_asset_text_score': score,
                    '_exact_image_asset': True,
                })
                if requested_limit is not None and len(result) >= requested_limit:
                    break
            return result
        except Exception as e:
            logger.warning(f"[_retrieve_assets_for_exact_image] failed: {e}")
            return []

    def _trim_section_text(self, text: str, heading_norm: str, is_first: bool) -> str:
        """Trim a section chunk to the requested heading and stop before obvious next sections."""
        if not text:
            return ''

        result = text
        if is_first and heading_norm:
            norm_chars = []
            original_positions = []
            for idx, char in enumerate(text):
                if char.isspace():
                    normalized_char = ' '
                else:
                    decomposed = unicodedata.normalize('NFD', char.lower())
                    normalized_char = ''.join(
                        ch for ch in decomposed
                        if unicodedata.category(ch) != 'Mn'
                    )
                    normalized_char = normalized_char.replace('đ', 'd').replace('Đ', 'd')
                    normalized_char = re.sub(r'[^\w\s]+', ' ', normalized_char)
                for out_char in normalized_char:
                    norm_chars.append(out_char)
                    original_positions.append(idx)
            text_norm = ''.join(norm_chars)
            pattern = r'\s+'.join(re.escape(part) for part in heading_norm.split())
            match = re.search(pattern, text_norm)
            if match:
                result = text[original_positions[match.start()]:]
            else:
                fuzzy_start = self._find_fuzzy_heading_original_start(text, heading_norm)
                if fuzzy_start is not None:
                    result = text[fuzzy_start:]

        stop_patterns = [
            r'\n\s*TÀI LIỆU THAM KHẢO\b',
            r'\n\s*TAI LIEU THAM KHAO\b',
            r'\n\s*PHỤ LỤC\b',
            r'\n\s*PHU LUC\b',
            r'\s+Chỉ Số Đánh Giá\b',
            r'\s+Chi So Danh Gia\b',
            r'\s+Thành phần hệ thống\b',
            r'\s+Thanh phan he thong\b',
            r'\s+Phương Pháp\b',
            r'\s+Phuong Phap\b',
        ]
        for pattern in stop_patterns:
            match = re.search(pattern, result, flags=re.IGNORECASE)
            if match:
                result = result[:match.start()]
                break
        return result.strip()

    def _heading_terms(self, heading_norm: str) -> Tuple[set, set, set]:
        """Return important, attribute, and subject terms for fuzzy section matching."""
        tokens = [
            token for token in re.findall(r'\w+', heading_norm or '')
            if len(token) >= 3
        ]
        attribute_terms = {
            'chuc', 'nang', 'nhiem', 'quyen', 'han', 'trach',
            'vai', 'tro', 'chuc', 'trach',
        }
        stop_terms = {
            'noi', 'dung', 'cua', 'cho', 've', 'cac', 'nhung',
            'xem', 'lay', 'trich', 'toi', 'minh',
        }
        important = {token for token in tokens if token not in stop_terms}
        attrs = {token for token in important if token in attribute_terms or token == 'vu'}
        subject = important - attrs
        return important, attrs, subject

    def _fuzzy_heading_line_score(self, line_norm: str, heading_norm: str) -> int:
        """Score attribute-style headings when exact substring matching is too brittle."""
        important, attrs, subject = self._heading_terms(heading_norm)
        if len(important) < 4 or not attrs or len(subject) < 2:
            return 0

        line_terms = set(re.findall(r'\w+', line_norm or ''))
        attr_hits = len(attrs & line_terms)
        subject_hits = len(subject & line_terms)
        has_attribute_phrase = any(
            phrase in line_norm
            for phrase in ('chuc nang', 'nhiem vu', 'quyen han', 'trach nhiem', 'vai tro')
        )
        if attr_hits < 2 and not has_attribute_phrase:
            return 0
        if subject_hits < min(2, len(subject)):
            return 0

        score = (attr_hits * 3) + (subject_hits * 2)
        if re.match(r'^\s*(?:dieu|article)\s+\d+', line_norm) or re.match(r'^\s*\d+(?:\.\d+)*\.?\s+', line_norm):
            score += 6
        first_attr_positions = [
            pos for pos in (
                line_norm.find('chuc nang'),
                line_norm.find('nhiem vu'),
                line_norm.find('quyen han'),
                line_norm.find('trach nhiem'),
                line_norm.find('vai tro'),
            )
            if pos >= 0
        ]
        if first_attr_positions:
            attr_pos = min(first_attr_positions)
            if attr_pos <= 40:
                score += 5
            elif attr_pos <= 100:
                score += 2
        if 'truong phong' in line_norm:
            score -= 4
        if 'thuc hien cac chuc nang nhiem vu theo su phan cong' in line_norm:
            score -= 5
        return max(0, score)

    def _find_fuzzy_heading_original_start(self, text: str, heading_norm: str) -> Optional[int]:
        """Find the original offset of a fuzzy-matched heading line."""
        best: Optional[Tuple[int, int]] = None
        offset = 0
        for raw_line in (text or '').splitlines(keepends=True):
            line_norm = self._normalize_query_text(raw_line)
            score = self._fuzzy_heading_line_score(line_norm, heading_norm)
            if score and (best is None or score > best[0]):
                best = (score, offset)
            offset += len(raw_line)
        if best and best[0] >= 12:
            return best[1]
        return None

    def _subject_terms(self, subject: str) -> set:
        """Extract meaningful subject terms from a normalized section subject."""
        stop_terms = {
            'va', 'cua', 've', 'cho', 'cac', 'nhung', 'noi', 'dung',
            'muc', 'phan', 'chuong', 'dieu', 'section', 'article',
        }
        return {
            token for token in re.findall(r'\w+', subject or '')
            if len(token) >= 2 and token not in stop_terms
        }

    def _subject_match_score(self, text_norm: str, subject_terms: set) -> int:
        """Score how well normalized text matches a requested subject."""
        if not text_norm or not subject_terms:
            return 0
        text_terms = set(re.findall(r'\w+', text_norm))
        hits = len(subject_terms & text_terms)
        required = max(1, min(len(subject_terms), (len(subject_terms) * 2 + 2) // 3))
        if hits < required:
            return 0
        return hits * 3

    def _attribute_terms(self, attributes: str) -> set:
        """Extract terms that describe the requested attribute/section type."""
        return {
            token for token in re.findall(r'\w+', attributes or '')
            if len(token) >= 2
        }

    def _segment_starts_like_heading(self, segment_norm: str) -> bool:
        """Detect generic section-like starts without assuming document domain."""
        return bool(
            re.match(r'^\s*(?:dieu|article|section|muc|phan|chuong|chapter)\s+\d+', segment_norm or '')
            or re.match(r'^\s*\d+(?:\.\d+)*[.)]?\s+\S+', segment_norm or '')
        )

    def _looks_like_short_heading(self, segment: str, segment_norm: str) -> bool:
        """Generic short heading detector for OCR/PDF text."""
        clean = re.sub(r'\s+', ' ', segment or '').strip()
        if not clean:
            return False
        if self._segment_starts_like_heading(segment_norm):
            return True
        if len(clean) > 140:
            return False
        if clean.endswith(('.', ';', ',')):
            return False
        letters = [ch for ch in clean if ch.isalpha()]
        uppercase_ratio = (
            sum(1 for ch in letters if ch.upper() == ch and ch.lower() != ch) / max(1, len(letters))
            if letters else 0.0
        )
        return uppercase_ratio >= 0.65 or clean.istitle()

    def _attribute_heading_line_score(
        self,
        segment: str,
        line_norm: str,
        attribute_terms: set,
        subject_terms: set,
        subject_anchor_score: int = 0,
    ) -> int:
        """Score a generic heading/section candidate for the requested attribute."""
        if not line_norm:
            return 0
        line_terms = set(re.findall(r'\w+', line_norm))
        attr_hits = len(attribute_terms & line_terms)
        if attribute_terms and attr_hits < max(1, min(len(attribute_terms), 2)):
            return 0

        heading_like = self._looks_like_short_heading(segment, line_norm)
        if not heading_like:
            return 0
        if re.search(r'\bthuc hien\s+(?:cac\s+)?(?:chuc nang|nhiem vu|quyen han|trach nhiem)\b', line_norm):
            return 0
        if re.search(r'\btheo su phan cong\b', line_norm):
            return 0

        subject_score = self._subject_match_score(line_norm, subject_terms)
        if not subject_score and not subject_anchor_score:
            return 0

        score = attr_hits * 5 + subject_score + min(12, subject_anchor_score)
        if self._segment_starts_like_heading(line_norm):
            score += 10
        if subject_score:
            score += 4
        return max(0, score)

    def _subject_anchor_line_score(self, segment: str, segment_norm: str, subject_terms: set) -> int:
        """Score generic headings that introduce the requested subject."""
        subject_score = self._subject_match_score(segment_norm, subject_terms)
        if not subject_score:
            return 0
        if not self._looks_like_short_heading(segment, segment_norm):
            return 0
        heading_bonus = 6 if self._segment_starts_like_heading(segment_norm) else 3
        return subject_score + heading_bonus

    def _find_attribute_heading_in_row(
        self,
        row_text: str,
        attribute_terms: set,
        subject_terms: set,
        subject_anchor_score: int = 0,
    ) -> Tuple[int, int, str]:
        """Return best attribute heading line as (score, offset, line)."""
        best = (0, 0, '')
        offset = 0
        for raw_line in (row_text or '').splitlines(keepends=True):
            segments = re.split(
                r'(?=\b(?:Điều|Article)\s+\d+(?:\.\d+)*\.?\s+|\b\d+(?:\.\d+)*[.)]\s+)',
                raw_line,
                flags=re.IGNORECASE,
            )
            segment_offset = 0
            for segment in segments:
                if not segment:
                    continue
                line_norm = self._normalize_query_text(segment)
                score = self._attribute_heading_line_score(
                    segment,
                    line_norm,
                    attribute_terms,
                    subject_terms,
                    subject_anchor_score=subject_anchor_score,
                )
                if score > best[0]:
                    best = (score, offset + segment_offset, segment)
                segment_offset += len(segment)
            offset += len(raw_line)
        return best

    def _starts_new_numbered_section(self, text: str) -> bool:
        """Detect the next section heading when collecting contiguous chunks."""
        return bool(re.match(r'^\s*\d+(?:\.\d+)*\.\s+\S+', text or ''))

    def _first_numbered_section_id(self, text: str) -> str:
        """Return the first section number from a chunk, e.g. '3', '3.1', or 'Dieu 29'."""
        for raw_line in (text or '').splitlines():
            raw_line = raw_line or ''
            raw_stripped = raw_line.strip()
            if not raw_stripped:
                continue

            numbered_match = re.match(r'^\s*(\d+(?:\.\d+)*)[.)]\s+\S+', raw_line)
            if numbered_match:
                return numbered_match.group(1)

            line_norm = unicodedata.normalize('NFD', raw_line.lower())
            line_norm = ''.join(
                ch for ch in line_norm
                if unicodedata.category(ch) != 'Mn'
            )
            line_norm = (
                line_norm
                .replace('đ', 'd').replace('Đ', 'D')
                .replace('Ä‘', 'd').replace('Ä', 'd')
            )
            line_norm = re.sub(r'\s+', ' ', line_norm).strip()

            article_match = re.match(r'^(?:dieu|article)\s+(\d+(?:\.\d+)*)\b', line_norm)
            if article_match:
                return article_match.group(1)
        return ''

    def _is_child_section_id(self, current_id: str, candidate_id: str) -> bool:
        """True if candidate section belongs under current section."""
        if not current_id or not candidate_id:
            return False
        return candidate_id == current_id or candidate_id.startswith(f"{current_id}.")

    def _starts_new_outside_section(self, text: str, current_section_id: str) -> bool:
        """Detect a new numbered section outside the requested section subtree."""
        section_id = self._first_numbered_section_id(text)
        if not section_id:
            return False
        if not current_section_id:
            return True
        return not self._is_child_section_id(current_section_id, section_id)

    def _trim_to_section_scope(self, text: str, current_section_id: str) -> str:
        """Trim text before the first numbered section outside current_section_id."""
        if not text or not current_section_id:
            return text or ''

        kept = []
        for line in text.splitlines():
            section_id = self._first_numbered_section_id(line)
            if section_id and not self._is_child_section_id(current_section_id, section_id):
                break
            kept.append(line)
        return '\n'.join(kept).strip()

    def _has_heading_line(self, text: str, heading_norm: str) -> bool:
        """Return true when the requested heading appears as a standalone section heading."""
        for raw_line in (text or '').splitlines():
            line_norm = self._normalize_query_text(raw_line)
            if not line_norm or heading_norm not in line_norm:
                if self._fuzzy_heading_line_score(line_norm, heading_norm) >= 12:
                    return True
                continue
            prefix = line_norm.split(heading_norm, 1)[0].strip()
            suffix = line_norm.split(heading_norm, 1)[1].strip()
            if suffix and not re.match(r'^\d+$', suffix):
                continue
            if not prefix:
                return True
            if re.match(r'^\d+(?:\.\d+)*\.?\s*(?:cac|nhung|phan)?$', prefix):
                return True
        return False

    def _heading_section_id(self, text: str, heading_norm: str) -> str:
        """Return section number for the heading line that matched heading_norm."""
        lines = (text or '').splitlines()
        for raw_line in lines:
            line_norm = self._normalize_query_text(raw_line)
            fuzzy_match = bool(line_norm and self._fuzzy_heading_line_score(line_norm, heading_norm) >= 12)
            if not line_norm or (heading_norm not in line_norm and not fuzzy_match):
                continue
            if heading_norm in line_norm:
                prefix = line_norm.split(heading_norm, 1)[0].strip()
                match = re.match(r'^(\d+(?:\.\d+)*)\.?\s*(?:cac|nhung|phan)?$', prefix)
                if match:
                    return match.group(1)
            local_section = self._first_numbered_section_id(raw_line)
            if local_section:
                return local_section

        if heading_norm and heading_norm in self._normalize_query_text(text or ''):
            return self._first_numbered_section_id(text)
        return ''

    def _looks_like_toc_chunk(self, row: Dict[str, Any]) -> bool:
        """Detect table-of-contents/list-of-tables chunks before exact-heading extraction."""
        text = row.get('content') or ''
        text_norm = self._normalize_query_text(text)
        metadata = row.get('metadata') or {}
        if metadata.get('is_toc') or metadata.get('layout_role') == 'toc':
            return True
        if any(marker in text_norm for marker in ('muc luc', 'danh sach bang', 'danh sach hinh anh')):
            return True

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if any(re.search(r'\.\.\.\s*\d+$', line) for line in lines[:20]):
            return True
        if len(lines) < 2:
            return False

        toc_like = 0
        for line in lines[:20]:
            if re.search(r'\.\.\.\s*\d+$', line) or re.search(r'^(?:\d+(?:\.\d+)*|bảng\s+\d+|hình\s+\d+)\b.+\s\d+$', line, flags=re.IGNORECASE):
                toc_like += 1
        return toc_like >= 2 and (toc_like / max(1, min(len(lines), 20))) >= 0.35

    def _find_exact_heading_start_pos(self, rows: List[Dict[str, Any]], heading_norm: str) -> Optional[int]:
        """Find the real section start, preferring content over TOC occurrences."""
        matches = [
            idx
            for idx, row in enumerate(rows)
            if (
                heading_norm in self._normalize_query_text(row.get('content') or '')
                or self._fuzzy_heading_line_score(self._normalize_query_text(row.get('content') or ''), heading_norm) >= 12
            )
        ]
        if not matches:
            return None

        scored_matches = []
        for idx in matches:
            row = rows[idx]
            text = row.get('content') or ''
            text_norm = self._normalize_query_text(text)
            score = 0
            if self._looks_like_toc_chunk(row):
                score -= 10
            else:
                score += 3

            if self._has_heading_line(text, heading_norm):
                score += 4

            fuzzy_score = 0
            for raw_line in (text or '').splitlines():
                fuzzy_score = max(
                    fuzzy_score,
                    self._fuzzy_heading_line_score(self._normalize_query_text(raw_line), heading_norm),
                )
            if fuzzy_score:
                score += min(10, fuzzy_score)

            heading_pos = text_norm.find(heading_norm)
            heading_tail = text_norm[heading_pos + len(heading_norm):] if heading_pos >= 0 else ''
            if len(heading_tail.strip()) > 80:
                score += 2
            if len(heading_tail.strip()) > 20 and not re.match(r'^\s*(?:\.+\s*)?\d+\b', heading_tail):
                score += 1

            block_type = (row.get('metadata') or {}).get('block_type')
            if block_type in ('paragraph', 'mixed', 'table'):
                score += 1
            elif block_type in ('list', 'title'):
                score -= 1

            heading_path = (row.get('metadata') or {}).get('heading_path') or []
            if isinstance(heading_path, (list, tuple)):
                heading_path_text = ' '.join(str(item) for item in heading_path if item)
            else:
                heading_path_text = str(heading_path)
            if heading_norm in self._normalize_query_text(heading_path_text):
                score += 2

            if idx + 1 < len(rows):
                next_row = rows[idx + 1]
                next_text = next_row.get('content') or ''
                same_doc = str(next_row.get('document_id')) == str(row.get('document_id'))
                adjacent = int(next_row.get('chunk_index') or 0) - int(row.get('chunk_index') or 0) == 1
                if (
                    same_doc
                    and adjacent
                    and len(next_text.strip()) > 80
                    and not self._looks_like_toc_chunk(next_row)
                    and not self._starts_new_outside_section(next_text, self._heading_section_id(text, heading_norm))
                ):
                    score += 1
            scored_matches.append((score, idx))

        scored_matches.sort(key=lambda item: (item[0], item[1]), reverse=True)
        best_score, best_idx = scored_matches[0]
        if best_score <= -5:
            return matches[0]
        return best_idx

    def _retrieve_exact_heading_section_candidates(
        self,
        query: str,
        resolved_doc_ids: List[str],
        max_chunks: int = 6,
    ) -> List[Dict[str, Any]]:
        """Fetch continuous chunks for an explicitly requested heading."""
        heading_norm = self._extract_requested_heading(query)
        if not heading_norm or not resolved_doc_ids:
            return []

        try:
            DocumentChunk = apps.get_model('documents', 'DocumentChunk')
            rows = list(
                DocumentChunk.objects.filter(
                    document_id__in=resolved_doc_ids,
                    node_type='detail',
                    is_deleted=False,
                )
                .order_by('document_id', 'chunk_index')
                .values('id', 'document_id', 'content', 'page_number', 'chunk_index', 'metadata')
            )
            start_pos = self._find_exact_heading_start_pos(rows, heading_norm)
            if start_pos is None:
                return []

            start_text = rows[start_pos].get('content') or ''
            current_section_id = self._heading_section_id(start_text, heading_norm) or self._first_numbered_section_id(start_text)
            start_doc_id = str(rows[start_pos].get('document_id'))
            start_page = rows[start_pos].get('page_number')
            section_rows = rows[start_pos:start_pos + max_chunks]
            candidates = []
            for offset, row in enumerate(section_rows):
                row_text = row.get('content') or ''
                if offset > 0:
                    if current_section_id:
                        if self._starts_new_outside_section(row_text, current_section_id):
                            break
                    else:
                        # Non-numbered headings, especially table titles in
                        # converted Office/PDF text, are often followed by
                        # numbered cell fragments like author lists. Keep the
                        # contiguous page instead of treating "1." as a new
                        # section immediately.
                        if str(row.get('document_id')) != start_doc_id:
                            break
                        if start_page and row.get('page_number') and row.get('page_number') != start_page:
                            break
                snippet = self._trim_section_text(row.get('content') or '', heading_norm, offset == 0)
                snippet = self._trim_to_section_scope(snippet, current_section_id)
                if not snippet:
                    continue
                candidates.append({
                    'chunk_id': str(row['id']),
                    'document_id': str(row['document_id']),
                    'score': 1.5 - (offset * 0.03),
                    'source': 'exact_heading',
                    'snippet': snippet,
                    'page': row.get('page_number'),
                    'chunk_index': row.get('chunk_index'),
                    'metadata': row.get('metadata') or {},
                    '_exact_heading': heading_norm,
                })
                if offset > 0 and len(snippet) < len(row.get('content') or ''):
                    break
            return candidates
        except Exception as e:
            logger.warning(f"[_retrieve_exact_heading_section_candidates] failed: {e}")
            return []

    def _retrieve_attribute_section_candidates(
        self,
        query: str,
        resolved_doc_ids: List[str],
        max_chunks: int = 6,
    ) -> List[Dict[str, Any]]:
        """Fetch a requested attribute section using subject/heading structure."""
        attribute_request = self._extract_attribute_section_request(query)
        subject = attribute_request.get('subject') or ''
        attributes = attribute_request.get('attributes') or ''
        subject_terms = self._subject_terms(subject)
        attribute_terms = self._attribute_terms(attributes)
        if not subject_terms or not attribute_terms or not resolved_doc_ids:
            return []

        try:
            DocumentChunk = apps.get_model('documents', 'DocumentChunk')
            rows = list(
                DocumentChunk.objects.filter(
                    document_id__in=resolved_doc_ids,
                    node_type='detail',
                    is_deleted=False,
                )
                .order_by('document_id', 'chunk_index')
                .values('id', 'document_id', 'content', 'page_number', 'chunk_index', 'metadata')
            )

            direct_matches: List[Tuple[int, int, int, str]] = []
            subject_anchors: List[Tuple[int, int]] = []
            for idx, row in enumerate(rows):
                row_text = row.get('content') or ''
                score, offset, line = self._find_attribute_heading_in_row(
                    row_text,
                    attribute_terms,
                    subject_terms,
                )
                if score:
                    direct_matches.append((score, idx, offset, line))

                offset_cursor = 0
                for raw_line in row_text.splitlines(keepends=True):
                    segments = re.split(
                        r'(?=\b(?:Điều|Article|Section|Mục|Phần|Chương|Chapter)\s+\d+(?:\.\d+)*\.?\s+|\b\d+(?:\.\d+)*[.)]\s+)',
                        raw_line,
                        flags=re.IGNORECASE,
                    )
                    segment_offset = 0
                    for segment in segments:
                        if segment:
                            segment_norm = self._normalize_query_text(segment)
                            anchor_score = self._subject_anchor_line_score(
                                segment,
                                segment_norm,
                                subject_terms,
                            )
                            if anchor_score:
                                subject_anchors.append((anchor_score, idx))
                        segment_offset += len(segment)
                    offset_cursor += len(raw_line)

                heading_path = (row.get('metadata') or {}).get('heading_path') or []
                if heading_path:
                    heading_text = (
                        ' '.join(str(item) for item in heading_path if item)
                        if isinstance(heading_path, (list, tuple))
                        else str(heading_path)
                    )
                    heading_norm = self._normalize_query_text(heading_text)
                    anchor_score = self._subject_match_score(heading_norm, subject_terms)
                    if anchor_score:
                        subject_anchors.append((anchor_score + 4, idx))

            best_match: Optional[Tuple[int, int, int, str]] = None
            if direct_matches:
                direct_matches.sort(key=lambda item: (item[0], -item[1]), reverse=True)
                best_match = direct_matches[0]

            for subject_score, anchor_idx in subject_anchors:
                scan_end = min(len(rows), anchor_idx + max(max_chunks * 2, 10))
                for idx in range(anchor_idx, scan_end):
                    row_text = rows[idx].get('content') or ''
                    score, offset, line = self._find_attribute_heading_in_row(
                        row_text,
                        attribute_terms,
                        subject_terms,
                        subject_anchor_score=subject_score,
                    )
                    if not score:
                        continue
                    distance_penalty = max(0, idx - anchor_idx)
                    total_score = score + min(8, subject_score) - distance_penalty
                    if best_match is None or total_score > best_match[0]:
                        best_match = (total_score, idx, offset, line)

            if best_match:
                # Prefer direct headings with both subject and attribute when
                # their score is close to anchor-derived matches.
                strong_direct = [
                    item for item in direct_matches
                    if self._subject_match_score(
                        self._normalize_query_text(item[3]),
                        subject_terms,
                    )
                ]
                if strong_direct:
                    strong_direct.sort(key=lambda item: (item[0], -item[1]), reverse=True)
                    if strong_direct[0][0] >= best_match[0] - 5:
                        best_match = strong_direct[0]

            if not best_match:
                return []

            _score, start_pos, start_offset, heading_line = best_match
            start_row = rows[start_pos]
            start_text = start_row.get('content') or ''
            current_section_id = (
                self._first_numbered_section_id(heading_line)
                or self._first_numbered_section_id(start_text[start_offset:])
            )
            candidates = []
            for offset, row in enumerate(rows[start_pos:start_pos + max_chunks]):
                row_text = row.get('content') or ''
                if offset > 0 and current_section_id:
                    if self._starts_new_outside_section(row_text, current_section_id):
                        break

                snippet = row_text[start_offset:] if offset == 0 else row_text
                snippet = self._trim_to_section_scope(snippet, current_section_id)
                if not snippet:
                    continue
                candidates.append({
                    'chunk_id': str(row['id']),
                    'document_id': str(row['document_id']),
                    'score': 2.0 - (offset * 0.03),
                    'source': 'attribute_section',
                    'snippet': snippet,
                    'page': row.get('page_number'),
                    'chunk_index': row.get('chunk_index'),
                    'metadata': row.get('metadata') or {},
                    '_attribute_subject': subject,
                    '_attribute_heading': self._normalize_query_text(heading_line),
                })
                if offset > 0 and len(snippet) < len(row_text):
                    break

            return candidates
        except Exception as e:
            logger.warning(f"[_retrieve_attribute_section_candidates] failed: {e}")
            return []

    def _retrieve_exact_table_candidates(
        self,
        query: str,
        resolved_doc_ids: List[str],
    ) -> List[Dict[str, Any]]:
        """Fetch the exact table requested as "Bảng N" before semantic retrieval."""
        table_number = self._extract_requested_table_number(query)
        if not table_number or not resolved_doc_ids:
            return []

        heading_norm = self._extract_requested_heading(query)
        try:
            DocumentChunk = apps.get_model('documents', 'DocumentChunk')
            rows = list(
                DocumentChunk.objects.filter(
                    document_id__in=resolved_doc_ids,
                    node_type='detail',
                    is_deleted=False,
                )
                .order_by('document_id', 'chunk_index')
                .values('id', 'document_id', 'content', 'page_number', 'chunk_index', 'metadata')
            )

            table_pattern = re.compile(rf'\b(?:bang|table)\s*{re.escape(table_number)}\b')
            scored_matches = []
            for idx, row in enumerate(rows):
                row_text = row.get('content') or ''
                row_norm = self._normalize_query_text(row_text)
                if not table_pattern.search(row_norm):
                    continue

                metadata = row.get('metadata') or {}
                score = 5
                if self._looks_like_toc_chunk(row):
                    score -= 8
                else:
                    score += 4

                if re.search(rf'(^|\n)\s*(?:bang|table)\s*{re.escape(table_number)}\b', row_norm):
                    score += 3
                if metadata.get('block_type') == 'table' or 'table' in (metadata.get('block_types') or []):
                    score += 2
                if heading_norm:
                    if heading_norm in row_norm:
                        score += 5
                    else:
                        score += min(4, self._term_overlap_score(row_text, heading_norm))
                if 'stt' in row_norm and ('truong du lieu' in row_norm or 'mo ta' in row_norm):
                    score += 2

                scored_matches.append((score, idx))

            if not scored_matches:
                return []

            scored_matches.sort(key=lambda item: (item[0], item[1]), reverse=True)
            best_score, best_idx = scored_matches[0]
            if best_score <= 0:
                return []

            row = rows[best_idx]
            snippet = (row.get('content') or '').strip()
            if not snippet:
                return []

            return [{
                'chunk_id': str(row['id']),
                'document_id': str(row['document_id']),
                'score': 2.0,
                'source': 'exact_table',
                'snippet': snippet,
                'page': row.get('page_number'),
                'chunk_index': row.get('chunk_index'),
                'metadata': row.get('metadata') or {},
                '_exact_table_number': table_number,
            }]
        except Exception as e:
            logger.warning(f"[_retrieve_exact_table_candidates] failed: {e}")
            return []

    def _markdown_table_from_rows(self, rows: List[List[Any]], reference_text: str = '') -> str:
        """Convert extracted table cells to markdown without changing cell content."""
        cleaned_rows: List[List[str]] = []
        for row in rows or []:
            cells = [
                re.sub(r'\s+', ' ', str(cell or '').replace('|', '/')).strip()
                for cell in (row or [])
            ]
            if any(cells):
                cleaned_rows.append(cells)

        if not cleaned_rows:
            return ''

        cleaned_rows = self._repair_table_identifier_cells(cleaned_rows, reference_text)
        max_cols = max(len(row) for row in cleaned_rows)
        normalized_rows = [row + [''] * (max_cols - len(row)) for row in cleaned_rows]

        first_row = normalized_rows[0]
        first_row_is_data = bool(first_row and re.match(r'^\s*\d+\s*$', first_row[0] or ''))
        if first_row_is_data:
            headers = [f"Cột {index}" for index in range(1, max_cols + 1)]
            data_rows = normalized_rows
        else:
            headers = first_row
            data_rows = normalized_rows[1:]

        table_lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        table_lines.extend("| " + " | ".join(row) + " |" for row in data_rows)
        return "\n".join(table_lines)

    def _repair_table_identifier_cells(
        self,
        rows: List[List[str]],
        reference_text: str = '',
    ) -> List[List[str]]:
        """Repair OCR/PDF table cells like "absence id _" using identifiers in the chunk text."""
        if not rows or not reference_text:
            return rows

        reference_identifiers: Dict[str, str] = {}
        for match in re.finditer(r'(?m)^\s*([A-Za-z][A-Za-z0-9_]{2,})\b', reference_text):
            identifier = match.group(1).strip()
            key = re.sub(r'[^a-z0-9]+', '', identifier.lower())
            if key:
                reference_identifiers.setdefault(key, identifier)

        if not reference_identifiers:
            return rows

        repaired: List[List[str]] = []
        for row_index, row in enumerate(rows):
            repaired_row = list(row)
            if row_index > 0 and repaired_row:
                cell_key = re.sub(r'[^a-z0-9]+', '', repaired_row[0].lower())
                if cell_key in reference_identifiers:
                    repaired_row[0] = reference_identifiers[cell_key]
            repaired.append(repaired_row)
        return repaired

    def _try_extract_pdf_table_markdown(self, candidate: Dict[str, Any], snippet: str) -> str:
        """Use PyMuPDF table detection for exact PDF/Office-preview table requests when available."""
        document_id = candidate.get('document_id')
        page = candidate.get('page')
        if not document_id or not page:
            return ''

        try:
            Document = apps.get_model('documents', 'Document')
            doc = Document.objects.filter(id=document_id, is_deleted=False).first()
            if not doc:
                return ''

            file_type = (getattr(doc, 'file_type', '') or getattr(doc, 'mime_type', '') or '').lower()
            storage_path = getattr(doc, 'storage_path', '') or ''
            pdf_path = storage_path if ('pdf' in file_type or storage_path.lower().endswith('.pdf')) else ''
            if not pdf_path:
                metadata = candidate.get('metadata') or {}
                preview_path = ((metadata.get('spreadsheet') or {}).get('preview_pdf_path') or '').strip()
                if preview_path.lower().endswith('.pdf'):
                    pdf_path = preview_path
            if not pdf_path:
                return ''

            import fitz  # PyMuPDF
            import io
            from contextlib import redirect_stderr, redirect_stdout

            with fitz.open(pdf_path) as pdf:
                page_index = int(page) - 1
                if page_index < 0 or page_index >= pdf.page_count:
                    return ''
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    table_finder = pdf[page_index].find_tables()
                tables = getattr(table_finder, 'tables', []) or []
                if not tables:
                    return ''

                snippet_norm = self._normalize_query_text(snippet)
                snippet_terms = {
                    term for term in re.split(r'\W+', snippet_norm)
                    if len(term) >= 2
                }

                best_rows: List[List[Any]] = []
                best_score = 0
                for table in tables:
                    rows = table.extract() or []
                    table_text = ' '.join(
                        str(cell or '')
                        for row in rows
                        for cell in (row or [])
                    )
                    table_norm = self._normalize_query_text(table_text)
                    if not table_norm:
                        continue
                    table_terms = {
                        term for term in re.split(r'\W+', table_norm)
                        if len(term) >= 2
                    }
                    overlap = len(snippet_terms & table_terms)
                    coverage = overlap / max(1, min(len(snippet_terms), len(table_terms)))
                    exact_fragments = sum(
                        1 for fragment in re.findall(r'\b[\w@./-]{4,}\b', table_norm)
                        if fragment in snippet_norm
                    )
                    score = overlap + int(coverage * 20) + exact_fragments
                    if score > best_score:
                        best_score = score
                        best_rows = rows

                if not best_rows or best_score < 5:
                    return ''
                return self._markdown_table_from_rows(best_rows, reference_text=snippet)
        except Exception as e:
            logger.debug(f"[_try_extract_pdf_table_markdown] failed: {e}")
            return ''

    def _format_exact_table_snippet(self, snippet: str, candidate: Optional[Dict[str, Any]] = None) -> str:
        """Render exact table evidence without inventing columns or cell boundaries."""
        text = (snippet or '').replace('\r\n', '\n').replace('\r', '\n').strip()
        if not text:
            return ''

        lines = [line.rstrip() for line in text.split('\n') if line.strip()]
        title = lines[0] if lines else ''

        has_markdown_table = any(line.strip().startswith('|') and line.strip().endswith('|') for line in lines)
        has_markdown_separator = any(re.match(r'^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$', line.strip()) for line in lines)
        if has_markdown_table:
            if has_markdown_separator:
                return text
            if len(lines) >= 2 and all(line.strip().startswith('|') for line in lines[:2]):
                header_cols = lines[0].strip().strip('|').split('|')
                separator = '| ' + ' | '.join('---' for _ in header_cols) + ' |'
                return '\n'.join([lines[0], separator, *lines[1:]])
            return text

        extracted_table = self._try_extract_pdf_table_markdown(candidate or {}, text)
        if extracted_table:
            return (title + "\n\n" if title and not title.startswith('|') else "") + extracted_table

        body = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ''
        if title and body:
            return f"{title}\n\n```text\n{body}\n```"
        return f"```text\n{text}\n```"

    def _build_exact_table_answer(self, candidates: List[Dict[str, Any]]) -> str:
        """Create a deterministic answer for exact Bảng/Table N requests."""
        exact_candidate = next((c for c in candidates if c.get('source') == 'exact_table'), None)
        if not exact_candidate:
            return ''

        snippet = (
            exact_candidate.get('citation_excerpt')
            or exact_candidate.get('snippet')
            or ''
        ).strip()
        if not snippet:
            return ''

        title = (
            exact_candidate.get('document_title')
            or exact_candidate.get('title')
            or exact_candidate.get('document_name')
            or 'Tài liệu'
        )
        source_label = self._build_source_label(
            title=title,
            page=exact_candidate.get('page'),
            citation_id=exact_candidate.get('citation_id') or 1,
        )
        return f"{self._format_exact_table_snippet(snippet, exact_candidate)}\n\n{source_label}"

    def _candidate_content_signature(self, candidate: Dict[str, Any]) -> str:
        """Create a stable signature for near-duplicate chunk content."""
        text = (
            candidate.get('citation_excerpt')
            or candidate.get('snippet')
            or candidate.get('content')
            or ''
        )
        normalized = self._normalize_query_text(text)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        if len(normalized) < 25:
            return ''
        tokens = [token for token in re.findall(r'\w+', normalized) if len(token) > 2]
        if len(tokens) > 40:
            tokens = tokens[:40]
        return ' '.join(tokens)

    def _looks_like_front_matter_candidate(self, candidate: Dict[str, Any]) -> bool:
        """Detect TOC/front-matter chunks so they can be downranked or skipped."""
        metadata = candidate.get('metadata') or {}
        if metadata.get('is_toc') or metadata.get('layout_role') == 'toc':
            return True

        text = candidate.get('snippet') or candidate.get('citation_excerpt') or candidate.get('content') or ''
        snippet = self._normalize_query_text(text)
        if any(marker in snippet for marker in ('muc luc', 'danh sach bang', 'danh sach hinh anh', 'table of contents', 'contents page')):
            return True

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if any(re.search(r'\.\.\.\s*\d+$', line) for line in lines[:20]):
            return True
        if len(lines) < 2:
            return False
        toc_like = 0
        for line in lines[:20]:
            if re.search(r'\.\.\.\s*\d+$', line) or re.search(r'^(?:\d+(?:\.\d+)*|bảng\s+\d+|hình\s+\d+)\b.+\s\d+$', line, flags=re.IGNORECASE):
                toc_like += 1
        return toc_like >= 2 and (toc_like / max(1, min(len(lines), 20))) >= 0.35

    def _filter_front_matter_candidates(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Keep TOC/front-matter only when the user is explicitly asking for it."""
        if not candidates:
            return candidates

        query_norm = self._normalize_query_text(query)
        asks_toc = any(marker in query_norm for marker in ('muc luc', 'table of contents', 'contents', 'index'))
        if asks_toc:
            return candidates

        return [candidate for candidate in candidates if not self._looks_like_front_matter_candidate(candidate)]

    def _is_better_candidate(self, existing: Dict[str, Any], candidate: Dict[str, Any]) -> bool:
        """Prefer body content over front-matter and higher-scoring evidence."""
        existing_score = float(existing.get('score', 0.0) or 0.0)
        candidate_score = float(candidate.get('score', 0.0) or 0.0)
        if candidate_score > existing_score + 0.03:
            return True

        existing_body = not self._looks_like_front_matter_candidate(existing)
        candidate_body = not self._looks_like_front_matter_candidate(candidate)
        if candidate_body and not existing_body:
            return True

        existing_len = len((existing.get('snippet') or existing.get('citation_excerpt') or ''))
        candidate_len = len((candidate.get('snippet') or candidate.get('citation_excerpt') or ''))
        if candidate_len > existing_len and candidate_score >= existing_score - 0.02:
            return True

        return False

    def _deduplicate_candidates_by_content(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove near-duplicate chunks so the final context covers more unique content."""
        if not candidates:
            return []

        asset_candidates = [c for c in candidates if c.get('source') == 'asset']
        chunk_candidates = [c for c in candidates if c.get('source') != 'asset']
        grouped: Dict[str, Dict[str, Any]] = {}

        for candidate in chunk_candidates:
            signature = self._candidate_content_signature(candidate)
            if not signature:
                signature = f"__fallback__:{candidate.get('chunk_id') or id(candidate)}"

            existing = grouped.get(signature)
            if existing is None or self._is_better_candidate(existing, candidate):
                grouped[signature] = candidate

        deduped_chunks = sorted(
            grouped.values(),
            key=lambda item: float(item.get('score', 0.0) or 0.0),
            reverse=True,
        )
        return deduped_chunks + asset_candidates

    def _stitch_sequential_chunks(self, candidates):
        """Merge sequential chunks from same doc into continuous blocks for LLM."""
        if not candidates or len(candidates) <= 1:
            return candidates
        assets = [c for c in candidates if c.get('source') == 'asset']
        chunks = [c for c in candidates if c.get('source') != 'asset']
        if not chunks:
            return assets
        by_doc = {}
        for c in chunks:
            doc_id = str(c.get('document_id', '__unknown__'))
            by_doc.setdefault(doc_id, []).append(c)
        stitched = []
        for _doc_id, doc_chunks in by_doc.items():
            doc_chunks.sort(key=lambda x: int(x.get('chunk_index') or 0))
            group = []
            for c in doc_chunks:
                if not group:
                    group.append(c)
                    continue
                last_idx = int(group[-1].get('chunk_index') or 0)
                curr_idx = int(c.get('chunk_index') or 0)
                if curr_idx - last_idx <= 1:
                    group.append(c)
                else:
                    stitched.append(self._merge_stitch_group(group))
                    group = [c]
            if group:
                stitched.append(self._merge_stitch_group(group))
        stitched.sort(key=lambda x: float(x.get('score', 0) or 0), reverse=True)
        return stitched + assets

    def _merge_stitch_group(self, group):
        """Merge sequential chunks into one block."""
        if len(group) == 1:
            return group[0]
        merged = group[0].copy()
        snippets = [c.get('snippet') or c.get('citation_excerpt') or '' for c in group]
        merged['snippet'] = '\n\n'.join(s for s in snippets if s)
        merged['citation_excerpt'] = merged['snippet']
        merged['score'] = float(max(float(c.get('score', 0) or 0) for c in group))
        pages = [c.get('page') for c in group if c.get('page')]
        merged['page'] = min(pages) if pages else None
        merged['_stitched_from'] = len(group)
        return merged

    def _self_rag_relevance_check(self, query: str, candidates, threshold: float = 0.3) -> Dict[str, Any]:
        """Self-RAG: use LLM to score each chunk's relevance. Re-retrieve if too few pass.

        Returns dict with 'passed' (bool), 'avg_score' (float), 'low_relevance_ids' (list).
        If < 40% of candidates are relevant, triggers re-retrieval request.
        """
        if not getattr(settings, 'RAG_SELF_RAG_RELEVANCE_CHECK_ENABLED', True):
            return {'passed': True, 'avg_score': 0.5, 'low_relevance_ids': []}

        if not candidates or not self.llama:
            return {'passed': True, 'avg_score': 0.5, 'low_relevance_ids': []}

        # Score top 8 candidates
        top_n = candidates[:8]
        snippets = [(c.get('snippet') or c.get('citation_excerpt') or '')[:300] for c in top_n]

        prompt = (
            "Danh gia do lien quan cua moi doan van duoi day voi cau hoi. "
            "Cham diem tu 1 (khong lien quan) den 5 (rat lien quan). "
            "TRA VE CHI CAC CON SO, MOI SO TREN 1 DONG.\n\n"
            f"Cau hoi: {query}\n\n"
        )
        for i, snip in enumerate(snippets, 1):
            prompt += f"Doan {i}: {snip}\n\n"
        prompt += "Diem (1-5):"

        try:
            response = self.llama.complete(prompt=prompt, max_tokens=40, temperature=0.1)
            scores = []
            for line in (response or '').strip().split('\n'):
                try:
                    s = int(line.strip())
                    scores.append(s / 5.0)  # normalize to 0-1
                except ValueError:
                    continue

            if not scores:
                return {'passed': True, 'avg_score': 0.5, 'low_relevance_ids': []}

            avg = sum(scores) / len(scores)
            low_ids = [
                candidates[i].get('chunk_id', '')
                for i, s in enumerate(scores)
                if i < len(candidates) and s < threshold
            ]
            passed = (len(scores) - len(low_ids)) / max(1, len(scores)) >= 0.4

            if not passed:
                logger.warning(
                    f"[SELF_RAG] Low relevance: {len(low_ids)}/{len(scores)} below {threshold} "
                    f"avg={avg:.2f}. Triggering re-retrieval."
                )
            return {'passed': passed, 'avg_score': round(avg, 3), 'low_relevance_ids': low_ids}
        except Exception as e:
            logger.debug(f"[SELF_RAG] Check failed: {e}")
            return {'passed': True, 'avg_score': 0.5, 'low_relevance_ids': []}

    def _feedback_log_grounding(self, query: str, grounding_result: Dict[str, Any]):
        """Feedback loop: log grounding scores for future weight tuning.

        Stores per-query grounding stats. Over time, these can be used to
        adjust semantic/lexical/base weights automatically.
        """
        if not hasattr(self, '_feedback_buffer'):
            self._feedback_buffer: List[Dict[str, Any]] = []

        self._feedback_buffer.append({
            'query': query[:120],
            'grounded': grounding_result.get('grounded', True),
            'avg_similarity': grounding_result.get('avg_similarity', 1.0),
            'ungrounded_count': len(grounding_result.get('ungrounded_claims', [])),
        })

        # Keep last 100 entries
        if len(self._feedback_buffer) > 100:
            self._feedback_buffer = self._feedback_buffer[-100:]

        # Compute running stats
        total = len(self._feedback_buffer)
        grounded_count = sum(1 for e in self._feedback_buffer if e['grounded'])
        avg_sim = sum(e['avg_similarity'] for e in self._feedback_buffer) / max(1, total)

        logger.debug(
            f"[FEEDBACK] {grounded_count}/{total} grounded ({100*grounded_count/max(1,total):.0f}%) "
            f"avg_similarity={avg_sim:.3f}"
        )

    def _verify_answer_grounding(self, answer_text, candidates, threshold=0.45):
        """Post-generation check: verify each claim has supporting evidence via embedding similarity."""
        import math
        if not answer_text or not candidates:
            return {'grounded': True, 'ungrounded_claims': [], 'avg_similarity': 1.0}
        claims = [s.strip() for s in __import__('re').split(r'(?<=[.!?。])\s+', answer_text) if len(s.strip()) > 20]
        if not claims:
            return {'grounded': True, 'ungrounded_claims': [], 'avg_similarity': 1.0}
        chunk_texts = [c.get('snippet') or c.get('citation_excerpt') or '' for c in candidates[:10]]
        chunk_texts = [t for t in chunk_texts if t]
        if not chunk_texts:
            return {'grounded': True, 'ungrounded_claims': [], 'avg_similarity': 1.0}
        try:
            claim_embs = [self.embedding.create_embedding(cl) for cl in claims]
            chunk_embs = [self.embedding.create_embedding(ct) for ct in chunk_texts]
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"[GROUNDING] Embedding failed: {e}")
            return {'grounded': True, 'ungrounded_claims': [], 'avg_similarity': 1.0}
        sims = []
        ungrounded = []
        for i, ce in enumerate(claim_embs):
            if not ce:
                continue
            max_sim = 0.0
            for che in chunk_embs:
                if not che:
                    continue
                dot = sum(a*b for a, b in zip(ce, che))
                na = math.sqrt(sum(a*a for a in ce))
                nb = math.sqrt(sum(b*b for b in che))
                sim = dot/(na*nb) if na and nb else 0.0
                max_sim = max(max_sim, sim)
            sims.append(max_sim)
            if max_sim < threshold:
                ungrounded.append({'claim': claims[i][:200], 'similarity': round(max_sim, 3)})
        avg_sim = sum(sims)/len(sims) if sims else 1.0
        grounded = len(ungrounded) == 0
        if not grounded:
            import logging
            logging.getLogger(__name__).warning(f"[GROUNDING] {len(ungrounded)}/{len(claims)} ungrounded avg={avg_sim:.3f}")
        return {'grounded': grounded, 'ungrounded_claims': ungrounded, 'avg_similarity': round(avg_sim, 3)}

    def _verify_answer_grounding_v2(self, answer_text, candidates, threshold=0.45):
        """Verify citation coverage, exact facts and semantic support."""
        import math

        empty_result = {
            'grounded': True,
            'grounding_score': 1.0,
            'ungrounded_claims': [],
            'avg_similarity': 1.0,
            'citation_coverage': 1.0,
            'exact_unsupported_claims': [],
        }
        if not answer_text or not candidates:
            return empty_result

        claims = self._extract_answer_claims(answer_text)
        if not claims:
            return empty_result

        chunk_texts = [c.get('snippet') or c.get('citation_excerpt') or '' for c in candidates[:10]]
        chunk_texts = [t for t in chunk_texts if t]
        if not chunk_texts:
            return empty_result

        claim_attributions = self._build_fact_attribution(answer_text, candidates)
        cited_claims = [item for item in claim_attributions if item.get('citation_numbers')]
        citation_coverage = len(cited_claims) / max(1, len(claims))

        candidates_by_citation = {
            int(c.get('citation_id')): c
            for c in candidates
            if str(c.get('citation_id') or '').isdigit()
        }
        exact_unsupported = []
        for claim in claims:
            clean_claim = self._remove_citation_markup(claim)
            critical_facts = self._extract_critical_facts(clean_claim)
            if not critical_facts:
                continue
            cited_numbers = self._extract_referenced_citation_numbers(claim)
            evidence_candidates = [
                candidates_by_citation[num]
                for num in cited_numbers
                if num in candidates_by_citation
            ] or candidates[:10]
            supported = any(
                self._critical_facts_supported(
                    c.get('citation_excerpt') or c.get('snippet') or '',
                    clean_claim,
                )
                for c in evidence_candidates
            )
            if not supported:
                exact_unsupported.append({
                    'claim': clean_claim[:200],
                    'missing_facts': critical_facts[:12],
                })

        try:
            claim_embs = [self.embedding.create_embedding(cl) for cl in claims]
            chunk_embs = [self.embedding.create_embedding(ct) for ct in chunk_texts]
        except Exception as e:
            logger.warning(f"[GROUNDING] Embedding failed: {e}")
            grounded = not exact_unsupported and citation_coverage >= 0.65
            return {
                'grounded': grounded,
                'grounding_score': round(citation_coverage if grounded else min(citation_coverage, 0.49), 3),
                'ungrounded_claims': exact_unsupported,
                'avg_similarity': 1.0,
                'citation_coverage': round(citation_coverage, 3),
                'exact_unsupported_claims': exact_unsupported,
                'claims': claim_attributions,
            }

        sims = []
        ungrounded = []
        for i, ce in enumerate(claim_embs):
            if not ce:
                continue
            max_sim = 0.0
            for che in chunk_embs:
                if not che:
                    continue
                dot = sum(a * b for a, b in zip(ce, che))
                na = math.sqrt(sum(a * a for a in ce))
                nb = math.sqrt(sum(b * b for b in che))
                sim = dot / (na * nb) if na and nb else 0.0
                max_sim = max(max_sim, sim)
            sims.append(max_sim)
            if max_sim < threshold:
                ungrounded.append({'claim': claims[i][:200], 'similarity': round(max_sim, 3)})

        avg_sim = sum(sims) / len(sims) if sims else 1.0
        coverage_ok = citation_coverage >= 0.65
        grounded = len(ungrounded) == 0 and not exact_unsupported and coverage_ok
        grounding_score = min(avg_sim, citation_coverage if coverage_ok else citation_coverage * 0.8)
        if not grounded:
            logger.warning(
                f"[GROUNDING] semantic={len(ungrounded)}/{len(claims)} "
                f"exact={len(exact_unsupported)} citation_coverage={citation_coverage:.3f} avg={avg_sim:.3f}"
            )
        return {
            'grounded': grounded,
            'grounding_score': round(grounding_score, 3),
            'ungrounded_claims': ungrounded + exact_unsupported,
            'avg_similarity': round(avg_sim, 3),
            'citation_coverage': round(citation_coverage, 3),
            'exact_unsupported_claims': exact_unsupported,
            'claims': claim_attributions,
        }

    def _extract_answer_claims(self, answer_text: str) -> List[str]:
        """Split an answer into compact claim units for attribution checks."""
        cleaned = self._strip_trailing_source_lines(answer_text or '')
        claims = []
        for block in re.split(r'\n+', cleaned):
            block = block.strip()
            if not block:
                continue
            if re.match(r'^\s*(?:[-+*]|\d+\.)\s+', block):
                claims.append(block)
                continue
            claims.extend(
                part.strip()
                for part in re.split(r'(?<=[.!?])\s+', block)
                if len(part.strip()) > 20
            )
        return claims

    def _build_fact_attribution(self, answer_text: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Map each answer claim to the best supporting citation candidate."""
        claims = self._extract_answer_claims(answer_text)
        if not claims:
            return []

        by_citation = {
            int(c.get('citation_id')): c
            for c in candidates
            if str(c.get('citation_id') or '').isdigit()
        }
        attributions = []
        for index, claim in enumerate(claims, start=1):
            clean_claim = self._remove_citation_markup(claim)
            citation_numbers = sorted(self._extract_referenced_citation_numbers(claim))
            candidate_pool = [
                by_citation[number]
                for number in citation_numbers
                if number in by_citation
            ] or candidates[:10]

            best_candidate = None
            best_score = -1.0
            best_quality: Dict[str, Any] = {}
            for candidate in candidate_pool:
                quality = self._citation_quality_metrics(candidate, clean_claim, answer_text)
                score = quality['grounding_score'] + quality['overlap_score'] + (0.25 if not quality['missing_facts'] else 0)
                if score > best_score:
                    best_score = score
                    best_candidate = candidate
                    best_quality = quality

            grounded = bool(
                best_candidate
                and best_quality
                and best_quality.get('grounding_score', 0) >= 0.45
                and not best_quality.get('missing_facts')
            )
            attributions.append({
                'claim_index': index,
                'claim': clean_claim[:500],
                'citation_numbers': citation_numbers,
                'best_citation': best_candidate.get('citation_id') if best_candidate else None,
                'document_id': str(best_candidate.get('document_id')) if best_candidate and best_candidate.get('document_id') else '',
                'chunk_id': str(best_candidate.get('chunk_id')) if best_candidate and best_candidate.get('chunk_id') else '',
                'page': best_candidate.get('page') if best_candidate else None,
                'grounded': grounded,
                'grounding_score': best_quality.get('grounding_score', 0.0),
                'confidence': best_quality.get('confidence', 0.0),
                'matched_facts': best_quality.get('matched_facts', []),
                'missing_facts': best_quality.get('missing_facts', []),
            })

        return attributions

    def _revise_answer_for_grounding(
        self,
        query: str,
        answer_text: str,
        context_str: str,
        grounding: Dict[str, Any],
    ) -> str:
        """Ask the model to rewrite an ungrounded answer using only provided evidence."""
        if not context_str or not getattr(settings, 'RAG_GROUNDING_REVISION_ENABLED', True):
            return answer_text

        issues = grounding.get('ungrounded_claims') or grounding.get('exact_unsupported_claims') or []
        issue_lines = []
        for issue in issues[:8]:
            claim = issue.get('claim', '') if isinstance(issue, dict) else str(issue)
            missing = issue.get('missing_facts', []) if isinstance(issue, dict) else []
            suffix = f" | missing facts: {', '.join(map(str, missing[:8]))}" if missing else ''
            issue_lines.append(f"- {claim[:240]}{suffix}")

        revision_prompt = (
            "CAU HOI CAN TRA LOI:\n"
            f"{query}\n\n"
            "CAU TRA LOI BAN DAU CO DAU HIEU THIEU CAN CU HOAC TRICH DAN KHONG DU:\n"
            f"{answer_text}\n\n"
            "CAC VAN DE CAN SUA:\n"
            + ("\n".join(issue_lines) if issue_lines else "- Citation coverage/grounding thap")
            + "\n\n"
            f"{context_str}\n\n"
            "Hay viet lai cau tra loi bang tieng Viet co dau, ngan gon va dung tai lieu. "
            "Chi giu cac thong tin co trong NGUON, moi y quan trong phai co citation [n]. "
            "Neu tai lieu khong du thong tin, noi ro phan nao khong thay trong tai lieu. "
            "Khong them kien thuc ben ngoai."
        )

        try:
            revised = self.llama.chat_complete(
                messages=[{'role': 'user', 'content': revision_prompt}],
                system_prompt=self.RAG_SYSTEM_PROMPT,
                max_tokens=getattr(settings, 'RAG_GROUNDING_REVISION_MAX_TOKENS', 768),
                temperature=0.1,
            )
            revised = (revised or '').strip()
            return revised if revised else answer_text
        except Exception as e:
            logger.warning(f"[GROUNDING] Answer revision failed: {e}")
            return answer_text

    def _append_grounding_warning(self, answer_text: str, grounding: Dict[str, Any]) -> str:
        """Make weak grounding visible to the end user, not only metadata."""
        if not getattr(settings, 'RAG_GROUNDING_VISIBLE_WARNING_ENABLED', True):
            grounding['warning_visible'] = False
            return answer_text
        if grounding.get('grounded', True):
            grounding['warning_visible'] = False
            return answer_text
        if 'chưa đủ bằng chứng trực tiếp' in (answer_text or '').lower():
            grounding['warning_visible'] = True
            return answer_text

        grounding['warning_visible'] = True
        warning = (
            "\n\nLưu ý: Một số ý trong câu trả lời chưa đủ bằng chứng trực tiếp "
            "trong tài liệu. Vui lòng kiểm tra phần nguồn/citation; các claim thiếu "
            "căn cứ đã được đánh dấu trong metadata."
        )
        return f"{(answer_text or '').rstrip()}{warning}"

    def _ensure_visible_citation_marker(
        self,
        answer_text: str,
        citations: List[Dict[str, Any]],
    ) -> str:
        """Ensure the UI has at least one inline marker to attach a citation popup."""
        if not citations or self._extract_referenced_citation_numbers(answer_text):
            return answer_text

        first_citation = next(
            (citation for citation in citations if not any(str(key).startswith('_') for key in citation.keys())),
            None,
        )
        if not first_citation:
            return answer_text

        number = first_citation.get('number') or 1
        return f"{(answer_text or '').rstrip()} [{number}]"

    def _finalize_rag_answer(
        self,
        query: str,
        answer_text: str,
        context_str: str,
        candidates: List[Dict[str, Any]],
        allow_revision: bool = True,
    ) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
        """Build citations and revise the answer once when grounding fails."""
        if not candidates:
            return answer_text, [], {
                'grounded': True,
                'grounding_score': 1.0,
                'citation_coverage': 1.0,
                'claims': [],
            }

        grounding = self._verify_answer_grounding_v2(answer_text, candidates)
        final_answer = answer_text
        revised = False
        if allow_revision and not grounding.get('grounded', True):
            revised_answer = self._revise_answer_for_grounding(query, answer_text, context_str, grounding)
            if revised_answer and revised_answer != answer_text:
                revised = True
                final_answer = revised_answer
                grounding = self._verify_answer_grounding_v2(final_answer, candidates)

        citations = self._build_citation_payload(candidates, final_answer, query)
        final_answer = self._ensure_visible_citation_marker(final_answer, citations)
        grounding['revised'] = revised
        final_answer = self._append_grounding_warning(final_answer, grounding)
        citations.append({'_grounding': grounding})
        citations.append({'_fact_attribution': grounding.get('claims', [])})
        self._feedback_log_grounding(query, grounding)
        return final_answer, citations, grounding

    def _is_list_style_query(self, query: str) -> bool:
        """Detect questions that need comprehensive extraction, not a short fact."""
        q = self._normalize_query_text(query)
        if not q:
            return False

        comprehensive_patterns = [
            r'\b(cac|nhung)\b',
            r'\b(bao gom|gom|gom nhung gi)\b',
            r'\b(liet ke|ke ra|neu|trinh bay)\b',
            r'\b(day du|chi tiet|tat ca|toan bo)\b',
            r'\b(la gi|nhu the nao)\b',
            r'\b(dac diem|dac trung|thanh phan|noi dung|nguyen tac|yeu cau)\b',
            r'\b(chuc nang|nhiem vu|quyen han|trach nhiem|vai tro|chuc trach)\b.*\b(cua|cho|ve)\b',
            r'\b(cua|cho|ve)\b.*\b(chuc nang|nhiem vu|quyen han|trach nhiem|vai tro|chuc trach)\b',
            r'^\s*\d+\s*[/.)-]\s*',
        ]
        return (
            any(re.search(pattern, q) for pattern in comprehensive_patterns)
            or self._is_internal_document_query(query)
        )

    def _is_internal_document_query(self, query: str) -> bool:
        """Detect common internal-document terms that usually require broad evidence."""
        q = self._normalize_query_text(query)
        if not q:
            return False
        internal_terms = (
            'quy dinh', 'quy che', 'noi quy', 'dieu khoan', 'chinh sach',
            'quy trinh', 'thu tuc', 'bieu mau', 'mau', 'phieu', 'bien ban',
            'quyet dinh', 'thong bao', 'luong', 'thuong', 'phu cap',
            'khau tru', 'thuc linh', 'kpi', 'phuc loi', 'nang luong',
            'tang luong', 'bang luong', 'thong ke', 'so lieu', 'bao cao',
            'dinh muc', 'ma tran', 'trach nhiem', 'quyen han',
        )
        return any(term in q for term in internal_terms)

    def _is_internal_table_query(self, query: str) -> bool:
        """Detect salary/KPI/statistical/table requests that should preserve rows and columns."""
        q = self._normalize_query_text(query)
        if not q:
            return False
        table_patterns = (
            r'\bbang\s+(?:luong|kpi|thong tin|du lieu|so lieu)\b',
            r'\b(?:kpi|thong ke|so lieu|du lieu|ma tran)\b',
            r'\b(?:cot|column)\b',
            r'\b(?:hang|dong|row)\s+\d+\b',
            r'\b(?:hang|dong|row)\b.*\b(?:bang|excel|du lieu|so lieu)\b',
            r'\b(?:luong co ban|phu cap|khau tru|thuc linh)\b',
        )
        return any(re.search(pattern, q) for pattern in table_patterns)

    def _is_internal_procedure_query(self, query: str) -> bool:
        """Detect internal procedure/process requests."""
        q = self._normalize_query_text(query)
        if not q:
            return False
        return any(term in q for term in ('quy trinh', 'cac buoc', 'tung buoc', 'trinh tu', 'thu tuc', 'luu do', 'cach tinh'))

    def _is_section_content_query(self, query: str) -> bool:
        """True when the user asks to view/extract the content of a named heading."""
        q = self._normalize_query_text(query)
        if not q:
            return False
        if self._extract_attribute_section_request(query).get('subject'):
            return True
        if not self._extract_requested_heading(query):
            return False
        section_markers = (
            'xem',
            'lay',
            'trich',
            'noi dung',
            'toan bo',
            'day du',
            'chi tiet',
            'muc',
            'phan',
            'section',
            'chuong',
        )
        return any(marker in q for marker in section_markers)

    def _is_image_query(self, query: str) -> bool:
        """Detect if user asks to LIST ALL images. If they describe a SPECIFIC one, we return False to let RAG rank it."""
        q = self._normalize_query_text(query)
        if not q:
            return False
        
        # Keywords that imply "Show me everything"
        list_all_keywords = ['tat ca', 'liet ke', 'cac', 'nhung', 'toan bo', 'list', 'all']
        image_keywords = ['hinh anh', 'anh', 'minh chung', 'asset', 'hinh']
        
        has_list_intent = any(kw in q for kw in list_all_keywords)
        has_image = any(kw in q for kw in image_keywords)
        
        # Only force-show if they want to see "all" or "list" images.
        # If they just say "Show me the chart image", has_list_intent will be False, 
        # and we let the vector search + AI citations do their job to pick the RIGHT one.
        return has_list_intent and has_image

    def _get_effective_query_intent(self, query: str):
        """Return intent/config after applying local comprehensive-query heuristics."""
        intent, config = self._get_query_intent(query)
        from services.retrieval.query_intent import QueryIntent

        classifier = self._get_intent_classifier()
        if self._is_internal_table_query(query):
            return QueryIntent.TABLE, classifier.get_retrieval_config(QueryIntent.TABLE)
        if self._is_internal_procedure_query(query):
            return QueryIntent.PROCEDURAL, classifier.get_retrieval_config(QueryIntent.PROCEDURAL)
        if not self._is_list_style_query(query):
            return intent, config

        if intent in (QueryIntent.FACTUAL, QueryIntent.DEFINITIONAL):
            return QueryIntent.LIST, classifier.get_retrieval_config(QueryIntent.LIST)
        return intent, config

    def _get_forced_intent_value(self, query: str) -> str:
        """Value passed to QueryRouter so routing and context sizing agree."""
        try:
            intent, _config = self._get_effective_query_intent(query)
            return getattr(intent, 'value', str(intent))
        except Exception:
            return ''

    def _get_rag_top_k(self, query: str, default_top_k: int) -> int:
        """Intent-driven top_k: use QueryIntentClassifier for adaptive depth."""
        if self._is_section_content_query(query):
            base_top_k = int(getattr(settings, 'RAG_RETRIEVAL_TOP_K', default_top_k))
            return int(getattr(settings, 'RAG_RETRIEVAL_TOP_K_SECTION', max(base_top_k, 12)))
        try:
            _intent, config = self._get_effective_query_intent(query)
            return config.top_k
        except Exception:
            pass
        base_top_k = int(getattr(settings, 'RAG_RETRIEVAL_TOP_K', default_top_k))
        list_top_k = int(getattr(settings, 'RAG_RETRIEVAL_TOP_K_LIST', max(base_top_k, 12)))
        return list_top_k if self._is_list_style_query(query) else base_top_k

    def _get_rag_max_tokens(self, query: str) -> int:
        """Intent-driven max_tokens: LIST queries get up to 2048 tokens to prevent truncation."""
        if self._is_section_content_query(query):
            context_window = int(getattr(settings, 'LLM_CONTEXT_WINDOW', 4096))
            default_tokens = 2048 if context_window >= 6144 else 1536
            return int(getattr(settings, 'RAG_LLM_MAX_TOKENS_SECTION', default_tokens))
        try:
            _intent, config = self._get_effective_query_intent(query)
            from services.retrieval.query_intent import QueryIntent
            if _intent == QueryIntent.LIST:
                return int(getattr(settings, 'RAG_LLM_MAX_TOKENS_LIST', 2048))
            elif _intent == QueryIntent.TABLE:
                return int(getattr(settings, 'RAG_LLM_MAX_TOKENS_TABLE', 2048))
            elif _intent in (QueryIntent.ANALYTICAL, QueryIntent.COMPARATIVE):
                return int(getattr(settings, 'RAG_LLM_MAX_TOKENS_ANALYTICAL', 1536))
            elif _intent == QueryIntent.PROCEDURAL:
                return int(getattr(settings, 'RAG_LLM_MAX_TOKENS_PROCEDURAL', 1024))
            else:
                return int(getattr(settings, 'RAG_LLM_MAX_TOKENS', 768))
        except Exception:
            pass
        base_tokens = int(getattr(settings, 'RAG_LLM_MAX_TOKENS', 384))
        list_tokens = int(getattr(settings, 'RAG_LLM_MAX_TOKENS_LIST', max(base_tokens, 1024)))
        return list_tokens if self._is_list_style_query(query) else base_tokens

    def _get_context_snippet_chars(self, query: str) -> int:
        """Intent-driven snippet_chars: use QueryIntentClassifier. LIST gets 3000 chars to hold full tables."""
        if self._is_section_content_query(query):
            list_chars = int(getattr(settings, 'RAG_CONTEXT_SNIPPET_CHARS_LIST', 3000))
            return int(getattr(settings, 'RAG_CONTEXT_SNIPPET_CHARS_SECTION', max(list_chars, 5000)))
        try:
            _intent, config = self._get_effective_query_intent(query)
            snippet_chars = int(config.snippet_chars)
            if self._is_internal_table_query(query):
                return max(
                    snippet_chars,
                    int(getattr(settings, 'RAG_CONTEXT_SNIPPET_CHARS_INTERNAL_TABLE', 5000)),
                )
            if self._is_internal_document_query(query):
                return max(
                    snippet_chars,
                    int(getattr(settings, 'RAG_CONTEXT_SNIPPET_CHARS_INTERNAL', 3500)),
                )
            return snippet_chars
        except Exception:
            pass
        base_chars = int(getattr(settings, 'RAG_CONTEXT_SNIPPET_CHARS', 1400))
        list_chars = int(getattr(settings, 'RAG_CONTEXT_SNIPPET_CHARS_LIST', max(base_chars, 3000)))
        return list_chars if self._is_list_style_query(query) else base_chars

    def _estimate_tokens(self, text: str) -> int:
        """Conservative token estimate used before sending prompt to llama.cpp."""
        chars_per_token = float(getattr(settings, 'RAG_CONTEXT_CHARS_PER_TOKEN', 3.2))
        chars_per_token = max(1.0, chars_per_token)
        return int((len(text or '') / chars_per_token) + 1)

    def _get_context_token_budget(self, query: str) -> int:
        """Compute safe input-context budget from the real llama context window."""
        context_window = int(getattr(settings, 'LLM_CONTEXT_WINDOW', 4096))
        answer_budget = self._get_rag_max_tokens(query)
        reserved = int(getattr(settings, 'RAG_PROMPT_RESERVED_TOKENS', 650))
        available = context_window - answer_budget - reserved
        # Keep a useful lower bound, but never let context consume the full window.
        max_context_tokens = max(512, int(context_window * 0.65))
        return max(256, min(available, max_context_tokens))

    def _get_context_max_chars(self, query: str) -> int:
        """Cap total RAG context so neighbor expansion stays inside the LLM window."""
        base_chars = int(getattr(settings, 'RAG_CONTEXT_MAX_CHARS', 5000))
        list_chars = int(getattr(settings, 'RAG_CONTEXT_MAX_CHARS_LIST', max(base_chars, 7000)))
        if self._is_section_content_query(query):
            configured_chars = int(getattr(settings, 'RAG_CONTEXT_MAX_CHARS_SECTION', max(list_chars, 12000)))
        elif self._is_internal_table_query(query):
            configured_chars = int(getattr(settings, 'RAG_CONTEXT_MAX_CHARS_INTERNAL_TABLE', max(list_chars, 12000)))
        elif self._is_internal_document_query(query):
            configured_chars = int(getattr(settings, 'RAG_CONTEXT_MAX_CHARS_INTERNAL', max(list_chars, 10000)))
        else:
            configured_chars = list_chars if self._is_list_style_query(query) else base_chars
        token_budget = self._get_context_token_budget(query)
        chars_per_token = float(getattr(settings, 'RAG_CONTEXT_CHARS_PER_TOKEN', 3.2))
        token_safe_chars = int(token_budget * max(1.0, chars_per_token))
        return max(1200, min(configured_chars, token_safe_chars))

    def _get_neighbor_window(self, query: str) -> Tuple[int, int, int]:
        """Intent-driven neighbor window for context expansion."""
        if self._is_section_content_query(query):
            before = int(getattr(settings, 'RAG_CONTEXT_NEIGHBOR_BEFORE_SECTION', 1))
            after = int(getattr(settings, 'RAG_CONTEXT_NEIGHBOR_AFTER_SECTION', 8))
            max_chunks = int(getattr(settings, 'RAG_CONTEXT_MAX_CHUNKS_SECTION', 24))
            return max(0, before), max(0, after), max(1, max_chunks)
        try:
            _intent, config = self._get_effective_query_intent(query)
            return config.neighbor_before, config.neighbor_after, config.max_context_chunks
        except Exception:
            pass
        if not self._is_list_style_query(query):
            return 0, 0, int(getattr(settings, 'RAG_CONTEXT_MAX_CHUNKS', 8))

        before = int(getattr(settings, 'RAG_CONTEXT_NEIGHBOR_BEFORE_LIST', 1))
        after = int(getattr(settings, 'RAG_CONTEXT_NEIGHBOR_AFTER_LIST', 3))
        max_chunks = int(getattr(settings, 'RAG_CONTEXT_MAX_CHUNKS_LIST', 18))
        return max(0, before), max(0, after), max(1, max_chunks)

    def _expand_candidates_with_neighbors(
        self,
        candidates: List[Dict[str, Any]],
        query: str,
    ) -> List[Dict[str, Any]]:
        """
        Add adjacent chunks for comprehensive questions.

        Retrieval often hits the first chunk of a section, while the remaining
        bullets live in the next chunks/pages. Expanding by document order keeps
        the behavior generic for any document without hardcoded domain keywords.
        """
        if not candidates:
            return []

        before, after, max_chunks = self._get_neighbor_window(query)
        chunk_ids_needed = [c.get('chunk_id') for c in candidates if c.get('chunk_id')]
        if not chunk_ids_needed:
            return candidates[:max_chunks]

        try:
            DocumentChunk = apps.get_model('documents', 'DocumentChunk')
            base_chunks = DocumentChunk.objects.filter(
                id__in=chunk_ids_needed,
                is_deleted=False,
            ).values('id', 'document_id', 'content', 'page_number', 'chunk_index', 'node_type', 'metadata')
            base_chunk_map = {str(chunk['id']): chunk for chunk in base_chunks}

            hydrated: List[Dict[str, Any]] = []
            seen = set()

            def add_candidate(source_candidate: Dict[str, Any], chunk: Dict[str, Any], source_suffix: str = ''):
                chunk_id = str(chunk['id'])
                if chunk_id in seen or len(hydrated) >= max_chunks:
                    return
                seen.add(chunk_id)
                item = source_candidate.copy()
                item['chunk_id'] = chunk_id
                item['document_id'] = str(chunk['document_id'])
                item['snippet'] = chunk.get('content') or source_candidate.get('snippet') or ''
                item['page'] = chunk.get('page_number') or source_candidate.get('page')
                item['chunk_index'] = chunk.get('chunk_index')
                item['metadata'] = chunk.get('metadata') or source_candidate.get('metadata') or {}
                if source_suffix:
                    item['source'] = f"{source_candidate.get('source', 'retrieval')}_{source_suffix}"
                    item['score'] = float(source_candidate.get('score', 0.0) or 0.0) * 0.92
                    item['anchor_chunk_id'] = source_candidate.get('chunk_id')
                hydrated.append(item)

            for candidate in candidates:
                base_chunk = base_chunk_map.get(str(candidate.get('chunk_id')))
                if not base_chunk:
                    if str(candidate.get('chunk_id')) not in seen and len(hydrated) < max_chunks:
                        seen.add(str(candidate.get('chunk_id')))
                        hydrated.append(candidate)
                    continue

                if before or after:
                    start_index = int(base_chunk.get('chunk_index') or 0) - before
                    end_index = int(base_chunk.get('chunk_index') or 0) + after
                    neighbor_chunks = DocumentChunk.objects.filter(
                        document_id=base_chunk['document_id'],
                        node_type='detail',
                        is_deleted=False,
                        chunk_index__gte=start_index,
                        chunk_index__lte=end_index,
                    ).order_by('chunk_index').values(
                        'id', 'document_id', 'content', 'page_number', 'chunk_index', 'node_type', 'metadata'
                    )
                    for neighbor in neighbor_chunks:
                        suffix = '' if str(neighbor['id']) == str(base_chunk['id']) else 'neighbor'
                        add_candidate(candidate, neighbor, suffix)
                        if len(hydrated) >= max_chunks:
                            break
                else:
                    add_candidate(candidate, base_chunk)

                if len(hydrated) >= max_chunks:
                    break

            return hydrated or candidates[:max_chunks]
        except Exception as e:
            logger.warning(f"[_expand_candidates_with_neighbors] Khong the mo rong context: {e}")
            return candidates[:max_chunks]

    def _metadata_value(self, metadata: Dict[str, Any], *keys: str) -> Any:
        """Return the first available value from chunk metadata."""
        if not isinstance(metadata, dict):
            return None
        for key in keys:
            value = metadata.get(key)
            if value is not None and value != '':
                return value
        return None

    def _extract_referenced_citation_numbers(self, text: str) -> set:
        """Find source chips that the model actually used in the final answer."""
        numbers = set()
        if not text:
            return numbers
            
        # 1. Standard format: [1], [2]
        for match in re.finditer(r'\[(\d{1,3})\]', text):
            numbers.add(int(match.group(1)))
            
        # 2. Source label format: [Nguon: abc.docx] 2 or [Nguon: abc.docx] 2.
        for match in re.finditer(r'\]\s*(\d{1,3})(?:[.\s]|$)', text):
            numbers.add(int(match.group(1)))
            
        return numbers

    def _extract_source_references(self, text: str) -> List[Dict[str, Any]]:
        """Extract long source labels from the final answer."""
        references: List[Dict[str, Any]] = []
        pattern = re.compile(
            r'\[(?:Ngu[^\]:]*|Source):\s*([^\]]+?)\]\s*\[(\d{1,3})\]',
            re.IGNORECASE,
        )
        for match in pattern.finditer(text or ''):
            source_text = match.group(1).strip()
            number = int(match.group(2))
            page_match = re.search(r'\btrang\s*(\d+)\b', source_text, re.IGNORECASE)
            title = re.split(r',\s*trang\s*\d+\b', source_text, maxsplit=1, flags=re.IGNORECASE)[0].strip()
            references.append({
                'number': number,
                'title': title,
                'page': int(page_match.group(1)) if page_match else None,
            })
        return references

    def _extract_answer_context_for_citation(self, text: str, citation_id: Any) -> str:
        """Return the sentence/paragraph that the model attached to a citation chip."""
        if citation_id is None:
            return ''

        citation_text = re.escape(str(citation_id))
        pattern = re.compile(
            rf'(?:\[(?:Ngu[^\]:]*|Source):[^\]]+\]\s*)?\[{citation_text}\]',
            re.IGNORECASE,
        )
        match = pattern.search(text or '')
        if not match:
            return ''

        before = (text or '')[:match.start()]
        before = re.sub(r'\[(?:Ngu[^\]:]*|Source):[^\]]+\]\s*$', ' ', before, flags=re.IGNORECASE)
        before = self._strip_trailing_source_lines(before)

        paragraph_parts = [part.strip() for part in re.split(r'\n\s*\n', before) if part.strip()]
        paragraph = paragraph_parts[-1] if paragraph_parts else before
        lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
        if len(lines) > 1:
            selected: List[str] = []
            for line in reversed(lines):
                selected.insert(0, line)
                selected_text = "\n".join(selected)
                if line.endswith(':') or len(selected) >= 5 or len(selected_text) >= 520:
                    break
            return "\n".join(selected).strip()

        sentences = [item.group(0).strip() for item in re.finditer(r'[^.!?\n]+[.!?]?', paragraph) if item.group(0).strip()]
        context = sentences[-1] if sentences else paragraph
        return context[-520:].strip()

    def _strip_trailing_source_lines(self, text: str) -> str:
        """Remove citation-only source lines before extracting answer context."""
        lines = (text or '').replace('\r\n', '\n').replace('\r', '\n').split('\n')
        source_line_pattern = re.compile(
            r'^\s*\[(?:Ngu[^\]:]*|Source):[^\]]+\](?:\s*\[\d{1,3}\])?\s*$',
            re.IGNORECASE,
        )
        source_tail_pattern = re.compile(r'\btrang\s*\d+\]?\s*\[\d{1,3}\]\s*$', re.IGNORECASE)

        while lines and not lines[-1].strip():
            lines.pop()

        while lines:
            tail = lines[-1].strip()
            if not source_line_pattern.search(tail) and not source_tail_pattern.search(tail):
                break

            lines.pop()
            while lines and not lines[-1].strip():
                lines.pop()

        return '\n'.join(lines).strip()

    def _extract_critical_facts(self, text: str) -> List[str]:
        """Extract facts that must appear in evidence if present in the cited answer sentence."""
        if not text:
            return []

        facts: List[str] = []
        patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b',
            r'https?://[^\s\])]+',
            r'\b\d+(?:[.,]\d+)?\s*(?:%|vnd|usd|eur|kg|g|km|m|cm|mm|gb|mb|kb|ngay|thang|nam|gio|phut|lan|diem|trieu|ty)(?=\s|$|[.,;:)\]])',
            r'\b(?:19|20)\d{2}\b',
            r'\b\d+(?:[.,]\d+)?\b',
        ]
        for pattern in patterns:
            facts.extend(match.group(0).strip() for match in re.finditer(pattern, text))

        normalized_facts = []
        seen = set()
        for fact in facts:
            normalized = self._normalize_query_text(fact)
            if normalized and normalized not in seen:
                normalized_facts.append(normalized)
                seen.add(normalized)
        return normalized_facts

    def _critical_facts_supported(self, evidence_text: str, answer_context: str) -> bool:
        """Reject a citation when the answer sentence contains exact facts absent from the chunk."""
        critical_facts = self._extract_critical_facts(answer_context)
        if not critical_facts:
            return True

        evidence_norm = self._normalize_query_text(evidence_text or '')
        return all(fact in evidence_norm for fact in critical_facts)

    def _critical_fact_coverage(self, evidence_text: str, answer_context: str) -> Dict[str, Any]:
        """Measure exact support for numbers, dates, URLs and similar facts."""
        facts = self._extract_critical_facts(answer_context)
        if not facts:
            return {
                'score': 1.0,
                'facts': [],
                'matched_facts': [],
                'missing_facts': [],
            }

        evidence_norm = self._normalize_query_text(evidence_text or '')
        matched = [fact for fact in facts if fact in evidence_norm]
        missing = [fact for fact in facts if fact not in evidence_norm]
        score = len(matched) / max(1, len(facts))
        return {
            'score': round(score, 3),
            'facts': facts,
            'matched_facts': matched,
            'missing_facts': missing,
        }

    def _citation_quality_metrics(
        self,
        candidate: Dict[str, Any],
        answer_context: str,
        answer_text: str,
    ) -> Dict[str, Any]:
        """Score how strongly a citation supports the exact answer sentence."""
        evidence = candidate.get('citation_excerpt') or candidate.get('snippet') or ''
        reference = answer_context or self._remove_citation_markup(answer_text or '')
        evidence_terms = {
            term for term in re.split(r'\W+', self._normalize_query_text(evidence))
            if len(term) >= 4
        }
        reference_terms = {
            term for term in re.split(r'\W+', self._normalize_query_text(reference))
            if len(term) >= 4
        }
        overlap_count = len(evidence_terms & reference_terms)
        overlap_score = overlap_count / max(1, min(len(evidence_terms), len(reference_terms)))

        raw_score = float(candidate.get('score', 0.0) or 0.0)
        retrieval_score = max(0.0, min(1.0, raw_score if raw_score <= 1.0 else raw_score / (raw_score + 1.0)))
        fact_coverage = self._critical_fact_coverage(evidence, answer_context)
        grounding_score = (0.55 * overlap_score) + (0.45 * float(fact_coverage['score']))
        confidence = (0.45 * retrieval_score) + (0.40 * grounding_score) + (0.15 if answer_context else 0.0)

        return {
            'confidence': round(max(0.0, min(1.0, confidence)), 3),
            'grounding_score': round(max(0.0, min(1.0, grounding_score)), 3),
            'overlap_score': round(max(0.0, min(1.0, overlap_score)), 3),
            'retrieval_score': round(retrieval_score, 3),
            'matched_facts': fact_coverage['matched_facts'],
            'missing_facts': fact_coverage['missing_facts'],
            'critical_facts': fact_coverage['facts'],
        }

    def _build_source_label(
        self,
        title: str,
        page: Any = None,
        line_start: Any = None,
        line_end: Any = None,
        citation_id: Any = None,
    ) -> str:
        """Build a user-visible source label without exposing technical chunk indexes as paragraphs."""
        parts = [f"Nguồn: {title}"]
        if page:
            parts.append(f"trang {page}")
        if line_start:
            line_text = f"dòng {line_start}"
            if line_end and line_end != line_start:
                line_text += f"-{line_end}"
            parts.append(line_text)
        label = f"[{', '.join(parts)}]"
        return f"{label} [{citation_id}]" if citation_id is not None else label

    def _candidate_answer_overlap(self, candidate: Dict[str, Any], answer_text: str) -> int:
        """Score how much a candidate snippet overlaps with the final answer."""
        snippet = self._normalize_query_text(candidate.get('citation_excerpt') or candidate.get('snippet') or '')
        answer = self._normalize_query_text(self._remove_citation_markup(answer_text or ''))
        if not snippet or not answer:
            return 0
        snippet_terms = {term for term in re.split(r'\W+', snippet) if len(term) >= 4}
        answer_terms = {term for term in re.split(r'\W+', answer) if len(term) >= 4}
        return len(snippet_terms & answer_terms)

    def _remove_citation_markup(self, text: str) -> str:
        """Remove source labels from answer text before matching evidence excerpts."""
        without_long_sources = re.sub(r'\[(?:Ngu[^\]:]*|Source):[^\]]+\]\s*\[\d{1,3}\]', ' ', text or '', flags=re.IGNORECASE)
        return re.sub(r'\[\d{1,3}\]', ' ', without_long_sources)

    def _clean_asset_caption(self, caption: str) -> str:
        """Remove prompt scaffolding that may leak from old VL captions."""
        text = re.sub(r'\s+', ' ', caption or '').strip()
        if not text:
            return ''

        replacements = [
            (r'^\s*\d+\.\s*Loại ảnh\s*:\s*', ''),
            (r'\b\d+\.\s*Mô tả nội dung\s*THỰC TẾ\s*:\s*', ''),
            (r'\b\d+\.\s*Chú ý hướng chữ\s*:\s*', ' '),
            (r'\b\d+\.\s*Tuyệt đối không bịa đặt[^.?!]*(?:[.?!]|$)', ' '),
            (r'\bCHỈ TRẢ VỀ[^.?!]*(?:[.?!]|$)', ' '),
        ]
        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        text = re.sub(r'\s+', ' ', text).strip(' -:;,.')
        return text

    def _term_overlap_score(self, text: str, reference_text: str) -> int:
        text_norm = self._normalize_query_text(text or '')
        ref_norm = self._normalize_query_text(reference_text or '')
        if not text_norm or not ref_norm:
            return 0
        text_terms = {term for term in re.split(r'\W+', text_norm) if len(term) >= 4}
        ref_terms = {term for term in re.split(r'\W+', ref_norm) if len(term) >= 4}
        return len(text_terms & ref_terms)

    def _split_heading_sections(self, text: str) -> List[str]:
        """Split chunk text into question/heading sections when the document has numbered headings."""
        if not text:
            return []

        heading_pattern = re.compile(
            r'(?m)^\s*(?:[-–—]\s*)?(?:Câu\s*)?\d+\s*[/.)-]\s+.+(?:\?|:)\s*$',
            re.IGNORECASE,
        )
        matches = list(heading_pattern.finditer(text))
        if not matches:
            return []

        sections = []
        for index, match in enumerate(matches):
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            section = text[start:end].strip()
            if section:
                sections.append(section)
        return sections

    def _split_evidence_units(self, text: str) -> List[str]:
        """Split a section into display-sized evidence lines/sentences."""
        if not text:
            return []

        units: List[str] = []
        for block in re.split(r'\n+', text):
            block = block.strip()
            if not block:
                continue
            if re.match(r'^\s*(?:[-+*•]|[-–—]\s*)', block):
                units.append(block)
                continue
            parts = re.split(r'(?<=[.!?。])\s+', block)
            units.extend(part.strip() for part in parts if part.strip())
        return units

    def _trim_citation_excerpt(self, snippet: str, answer_text: str, max_chars: int = 900) -> str:
        """
        Build a short citation excerpt for UI display only.

        Retrieval still uses full chunks; this trims the popup evidence to the
        section/sentences most related to the final answer and avoids bleeding
        into the next numbered question.
        """
        snippet = (snippet or '').strip()
        if not snippet:
            return ''
        if len(snippet) <= max_chars:
            return snippet

        reference_text = self._remove_citation_markup(answer_text or '')
        sections = self._split_heading_sections(snippet)
        if sections:
            best_section = max(
                sections,
                key=lambda section: self._term_overlap_score(section, reference_text),
            )
            if self._term_overlap_score(best_section, reference_text) > 0:
                snippet = best_section.strip()

        if len(snippet) <= max_chars:
            return snippet

        units = self._split_evidence_units(snippet)
        if not units:
            return snippet[:max_chars].strip()

        heading_units = [
            unit for unit in units[:2]
            if re.match(r'^\s*(?:[-–—]\s*)?(?:Câu\s*)?\d+\s*[/.)-]\s+.+(?:\?|:)\s*$', unit, re.IGNORECASE)
        ]
        scored_units = [
            (index, unit, self._term_overlap_score(unit, reference_text))
            for index, unit in enumerate(units)
        ]
        relevant = [(index, unit) for index, unit, score in scored_units if score > 0]
        if not relevant:
            return snippet[:max_chars].strip()

        selected_indexes = set()
        for unit in heading_units:
            selected_indexes.add(units.index(unit))

        for index, _unit in sorted(relevant, key=lambda item: item[0]):
            selected_indexes.add(index)
            candidate_text = "\n".join(units[i] for i in sorted(selected_indexes))
            if len(candidate_text) >= max_chars:
                break

        excerpt_parts = []
        for index in sorted(selected_indexes):
            next_text = "\n".join(excerpt_parts + [units[index]])
            if len(next_text) > max_chars and excerpt_parts:
                break
            excerpt_parts.append(units[index])

        return "\n".join(excerpt_parts).strip() or snippet[:max_chars].strip()

    def _build_citation_payload(
        self,
        candidates: List[Dict[str, Any]],
        answer_text: str = '',
        query: str = '',
    ) -> List[Dict[str, Any]]:
        """Convert retrieved chunks into frontend-ready source cards."""
        citations: List[Dict[str, Any]] = []
        seen = set()
        referenced_numbers = self._extract_referenced_citation_numbers(answer_text)
        source_references = self._extract_source_references(answer_text)
        source_reference_map = {ref['number']: ref for ref in source_references}
        doc_name_map: Dict[str, str] = {}
        doc_file_type_map: Dict[str, str] = {}
        missing_doc_ids = list({
            str(candidate.get('document_id'))
            for candidate in candidates
            if candidate.get('document_id')
            and not (candidate.get('document_title') or candidate.get('title') or candidate.get('document_name'))
        })
        if missing_doc_ids:
            try:
                Document = apps.get_model('documents', 'Document')
                docs = Document.objects.filter(id__in=missing_doc_ids, is_deleted=False).values('id', 'original_name', 'filename', 'file_type')
                doc_name_map = {
                    str(doc['id']): doc.get('original_name') or doc.get('filename') or f"Tai lieu {doc['id']}"
                    for doc in docs
                }
                doc_file_type_map = {
                    str(doc['id']): doc.get('file_type') or ''
                    for doc in docs
                }
            except Exception as e:
                logger.warning(f"[_build_citation_payload] Khong the hydrate document names: {e}")

        for candidate in candidates:
            # ── Asset citations ──────────────────────────────
            if candidate.get('source') == 'asset':
                asset_id = candidate.get('asset_id', '')
                doc_id = candidate.get('document_id', '')
                citation_id = candidate.get('citation_id')
                clean_caption = self._clean_asset_caption(candidate.get('asset_caption', ''))
                
                # SMART FILTER: Only include asset if it's referenced in the answer
                # OR if the user question explicitly asks for images/proofs.
                is_explicit_request = self._is_specific_image_query(query) or self._is_image_query(query)
                
                if answer_text and citation_id:
                    try:
                        numeric_id = int(citation_id)
                        # 1. Trích xuất danh sách số được nhắc tới (Chỉ dùng trong phạm vi hàm này)
                        referenced_numbers = self._extract_referenced_citation_numbers(answer_text)
                        is_referenced = numeric_id in referenced_numbers
                        
                        # 2. Điểm số tương đồng (Dựa trên mô tả ảnh từ Qwen 2.5)
                        score = float(candidate.get('score', 0) or 0)
                        
                        # LOGIC SIẾT CHẶT:
                        # - Nếu được AI trích dẫn đích danh ([1], [2]...): LUÔN HIỆN
                        if is_referenced:
                            pass # Tiếp tục xử lý
                        else:
                            # - Nếu KHÔNG được trích dẫn: 
                            #   + Chỉ hiện nếu là yêu cầu xem ảnh ĐÍCH DANH và điểm số phải cao (> 0.85)
                            #   + Hoặc điểm số phải CỰC CAO (> 0.95) để tránh hiện nhầm icon.
                            if not (is_explicit_request and score >= 0.45):
                                continue
                    except (ValueError, TypeError):
                        pass

                key = ('asset', str(asset_id))
                if key in seen or not asset_id:
                    continue
                seen.add(key)
                citations.append({
                    'id': str(asset_id),
                    'number': int(citation_id) if str(citation_id).isdigit() else (len(citations) + 1),
                    'title': clean_caption[:100] or 'Hình ảnh trong tài liệu',
                    'source_label': '',
                    'description': clean_caption[:900],
                    'excerpt': clean_caption[:900],
                    'document_id': str(doc_id),
                    'chunk_id': '',
                    'asset_id': asset_id,
                    'asset_caption': clean_caption,
                    'asset_image_path': candidate.get('asset_image_path', ''),
                    'asset_page_number': candidate.get('asset_page_number'),
                    'asset_sheet_name': candidate.get('asset_sheet_name'),
                    'asset_anchor_cell': candidate.get('asset_anchor_cell'),
                    'asset_paragraph_index': candidate.get('asset_paragraph_index'),
                    'asset_position_in_document': candidate.get('asset_position_in_document') or {},
                    'asset_context_text': candidate.get('asset_context_text') or '',
                    'page': candidate.get('asset_page_number'),
                    'type': 'asset',
                    'source': 'asset',
                    'document_title': doc_name_map.get(str(doc_id)),
                    'document_file_type': doc_file_type_map.get(str(doc_id)) or candidate.get('document_file_type'),
                    'score': round(float(candidate.get('score', 0) or 0), 3),
                    'confidence': round(float(candidate.get('score', 0) or 0), 3),
                    'grounding_score': round(float(candidate.get('score', 0) or 0), 3),
                    'matched_facts': [],
                    'missing_facts': [],
                    'asset': {
                        'id': asset_id,
                        'image_url': '/api/v1/assets/' + asset_id + '/image',
                        'thumbnail_url': '/api/v1/assets/' + asset_id + '/thumbnail',
                        'caption': clean_caption,
                        'page_number': candidate.get('asset_page_number'),
                        'sheet_name': candidate.get('asset_sheet_name'),
                        'anchor_cell': candidate.get('asset_anchor_cell'),
                        'paragraph_index': candidate.get('asset_paragraph_index'),
                        'position_in_document': candidate.get('asset_position_in_document') or {},
                        'context_text': candidate.get('asset_context_text') or '',
                    },
                })

                continue

            chunk_id = candidate.get('chunk_id')
            document_id = candidate.get('document_id')
            if not chunk_id or not document_id:
                continue

            citation_id = candidate.get('citation_id')
            if answer_text and citation_id is None:
                continue
            citation_id = citation_id or len(citations) + 1
            if referenced_numbers:
                try:
                    numeric_citation_id = int(citation_id)
                except (TypeError, ValueError):
                    numeric_citation_id = None
                if numeric_citation_id not in referenced_numbers:
                    continue

            answer_context = self._extract_answer_context_for_citation(answer_text, citation_id)

            metadata = candidate.get('metadata') or {}
            title = (
                candidate.get('document_title')
                or candidate.get('title')
                or candidate.get('document_name')
                or doc_name_map.get(str(document_id))
                or 'Tai lieu'
            )
            page = candidate.get('page')
            ref = source_reference_map.get(int(citation_id)) if str(citation_id).isdigit() else None
            if ref and ref.get('page'):
                replacement_candidates = [
                    item for item in candidates
                    if item.get('document_id') == document_id
                    and item.get('page') is not None
                    and int(item.get('page')) == int(ref['page'])
                ]
                fact_supported_candidates = [
                    item for item in replacement_candidates
                    if self._critical_facts_supported(
                        item.get('citation_excerpt') or item.get('snippet') or '',
                        answer_context,
                    )
                ]
                replacement = max(
                    fact_supported_candidates or replacement_candidates,
                    key=lambda item: self._term_overlap_score(
                        item.get('citation_excerpt') or item.get('snippet') or '',
                        answer_context or answer_text,
                    ),
                    default=None,
                )
                current_overlap = self._term_overlap_score(
                    candidate.get('citation_excerpt') or candidate.get('snippet') or '',
                    answer_context or answer_text,
                )
                replacement_overlap = self._term_overlap_score(
                    replacement.get('citation_excerpt') or replacement.get('snippet') or '',
                    answer_context or answer_text,
                ) if replacement else 0
                should_replace = (
                    replacement
                    and (
                        not page
                        or int(page) != int(ref['page'])
                        or replacement_overlap > current_overlap
                        or not self._critical_facts_supported(
                            candidate.get('citation_excerpt') or candidate.get('snippet') or '',
                            answer_context,
                        )
                    )
                )
                if should_replace:
                    candidate = replacement
                    chunk_id = candidate.get('chunk_id')
                    metadata = candidate.get('metadata') or {}
                    page = candidate.get('page')
                    title = (
                        candidate.get('document_title')
                        or candidate.get('title')
                        or candidate.get('document_name')
                        or doc_name_map.get(str(document_id))
                        or title
                    )

            key = (str(document_id), str(chunk_id), str(citation_id))
            if key in seen:
                continue
            seen.add(key)

            chunk_index = candidate.get('chunk_index')
            start_char = self._metadata_value(metadata, 'start_char', 'char_start')
            end_char = self._metadata_value(metadata, 'end_char', 'char_end')
            line_start = self._metadata_value(metadata, 'row_start', 'line_start', 'start_line')
            line_end = self._metadata_value(metadata, 'row_end', 'line_end', 'end_line')
            raw_excerpt = (candidate.get('citation_excerpt') or candidate.get('snippet') or '').strip()

            if answer_context and not self._critical_facts_supported(raw_excerpt, answer_context):
                logger.warning(
                    "[_build_citation_payload] Skip citation %s because critical facts are absent from evidence",
                    citation_id,
                )
                continue

            excerpt = self._trim_citation_excerpt(raw_excerpt, answer_text)
            source_label = self._build_source_label(
                title=title,
                page=page,
                line_start=line_start,
                line_end=line_end,
                citation_id=citation_id,
            )
            quality = self._citation_quality_metrics(candidate, answer_context, answer_text)

            citations.append({
                'id': f"{document_id}:{chunk_id}",
                'number': int(citation_id) if str(citation_id).isdigit() else citation_id,
                'title': title,
                'source_label': source_label,
                'description': excerpt[:900],
                'excerpt': excerpt[:1800],
                'answer_context': answer_context,
                'document_id': str(document_id),
                'chunk_id': str(chunk_id),
                'page': page,
                'chunk_index': chunk_index,
                'line_start': line_start,
                'line_end': line_end,
                'start_char': start_char,
                'end_char': end_char,
                'type': candidate.get('document_type') or 'document',
                'source': candidate.get('source', ''),
                'score': round(float(candidate.get('score', 0) or 0), 3),
                'confidence': quality['confidence'],
                'grounding_score': quality['grounding_score'],
                'overlap_score': quality['overlap_score'],
                'retrieval_score': quality['retrieval_score'],
                'critical_facts': quality['critical_facts'],
                'matched_facts': quality['matched_facts'],
                'missing_facts': quality['missing_facts'],
                'url': f"/documents/{document_id}/download",
            })

        return citations

    # =========================================================================
    # HELPERS - Resolve document IDs from DB conversation attachments
    # =========================================================================

    def _resolve_document_ids(
        self,
        user_id: int,
        conversation_id,
        document_ids: List[str],
        folder_ids: List[str],
    ) -> List[str]:
        """
        Trả về danh sách document IDs cuối cùng để giới hạn RAG search.

        Ưu tiên:
        1. Dùng document_ids truyền trực tiếp từ request (nhanh nhất)
        2. Expand folder_ids → document_ids
        3. Nếu cả 2 đều rỗng → đọc từ ConversationAttachedDocument trong DB
        
        Returns:
            List[str] of document IDs, rỗng nếu không có đính kèm nào.
        """
        final_ids: List[str] = list(document_ids or [])

        # Expand folder_ids → document_ids
        if folder_ids:
            try:
                Document = apps.get_model('documents', 'Document')
                docs_in_folders = Document.objects.filter(
                    folder_id__in=folder_ids,
                    is_deleted=False,
                ).values_list('id', flat=True)
                final_ids.extend([str(d) for d in docs_in_folders])
            except Exception as e:
                logger.warning(f"[_resolve_document_ids] Lỗi expand folder_ids: {e}")

        # Fallback: đọc từ DB (khi user đính kèm từ trước)
        if not final_ids and conversation_id:
            try:
                ConversationAttachedDocument = apps.get_model('operations', 'ConversationAttachedDocument')
                attached_ids = ConversationAttachedDocument.objects.filter(
                    conversation_id=conversation_id,
                    is_deleted=False,
                    document__isnull=False,
                    document__is_deleted=False,
                ).values_list('document_id', flat=True)
                final_ids.extend([str(d) for d in attached_ids])

                # Expand folders đã đính kèm trong DB
                ConversationAttachedFolder = apps.get_model('operations', 'ConversationAttachedFolder')
                attached_folder_ids = ConversationAttachedFolder.objects.filter(
                    conversation_id=conversation_id,
                    is_deleted=False,
                    folder__isnull=False,
                    folder__is_deleted=False,
                ).values_list('folder_id', flat=True)

                if attached_folder_ids:
                    Document = apps.get_model('documents', 'Document')
                    docs_in_attached_folders = Document.objects.filter(
                        folder_id__in=list(attached_folder_ids),
                        is_deleted=False,
                    ).values_list('id', flat=True)
                    final_ids.extend([str(d) for d in docs_in_attached_folders])

            except Exception as e:
                logger.warning(f"[_resolve_document_ids] Lỗi đọc DB attachments: {e}")
        
        # FINAL FALLBACK: if nothing is explicitly attached, use accessible
        # system documents/folders so document chat still produces real
        # citations instead of falling back to plain LLM output.
        if not final_ids and user_id and getattr(settings, 'AUTO_USE_ACCESSIBLE_ATTACHMENTS', True):
            logger.info(
                f"[_resolve_document_ids] No explicit attachments, fetching accessible documents/folders for user {user_id}"
            )
            try:
                attachments = self.chat_attachment_service.get_accessible_attachments(user_id)

                accessible_doc_ids = [
                    str(doc.get('id'))
                    for doc in attachments.get('documents', [])
                    if doc.get('id')
                ]
                accessible_folder_ids = [
                    str(folder.get('id'))
                    for folder in attachments.get('folders', [])
                    if folder.get('id')
                ]

                final_ids.extend(accessible_doc_ids)

                if accessible_folder_ids:
                    Document = apps.get_model('documents', 'Document')
                    docs_in_accessible_folders = Document.objects.filter(
                        folder_id__in=accessible_folder_ids,
                        is_deleted=False,
                    ).values_list('id', flat=True)
                    final_ids.extend([str(d) for d in docs_in_accessible_folders])

                if final_ids:
                    logger.debug(
                        f"[_resolve_document_ids] Resolved {len(final_ids)} document IDs from accessible system documents/folders"
                    )
            except Exception as e:
                logger.error(f"[_resolve_document_ids] Lỗi khi lấy danh sách tài liệu/folder truy cập: {e}")

        # Deduplicate, giữ thứ tự
        seen = set()
        unique_ids = []
        for d in final_ids:
            if d not in seen:
                seen.add(d)
                unique_ids.append(d)

        return unique_ids

    # =========================================================================
    # RETRIEVAL - Build context from documents via Hybrid Search
    # =========================================================================

    def _retrieve_context(
        self,
        query: str,
        resolved_doc_ids: List[str],
        explicit_doc_ids: List[str] = None,
        folder_ids: List[str] = None,
        conversation_history: List[Dict[str, Any]] = None,
        top_k: int = 4,  # Fix E: Giam tu 5 -> 4 de nhanh hon, it noise hon
        snippet_chars: int = 900,
        rag_mode: str = 'fast',
        current_page: int = None,
    ) -> Tuple[str, List[Dict]]:
        """
        Thực hiện Hybrid RAG search (BM25 + Vector) → rerank → build context string.

        Args:
            query: Câu hỏi của người dùng.
            resolved_doc_ids: Danh sách document IDs đã được resolve.
            top_k: Số lượng chunks muốn lấy.

        Returns:
            Tuple (context_string, candidates_list)
            - context_string: Text sẵn sàng chèn vào prompt LLM (có header + citations).
            - candidates_list: Raw list candidates để lưu vào metadata nếu cần.
        """
        t_context_start = time.monotonic()
        if not resolved_doc_ids:
            return '', []

        try:
            t_route_start = time.monotonic()
            exact_table_candidates = self._retrieve_exact_table_candidates(query, resolved_doc_ids)
            attribute_section_candidates: List[Dict[str, Any]] = []
            if not exact_table_candidates:
                attribute_section_candidates = self._retrieve_attribute_section_candidates(
                    query,
                    resolved_doc_ids,
                    max_chunks=int(getattr(settings, 'RAG_ATTRIBUTE_SECTION_MAX_CHUNKS', 16)),
                )
            exact_heading_candidates: List[Dict[str, Any]] = []
            if not exact_table_candidates and not attribute_section_candidates:
                exact_heading_candidates = self._retrieve_exact_heading_section_candidates(
                    query,
                    resolved_doc_ids,
                    max_chunks=int(getattr(settings, 'RAG_EXACT_HEADING_MAX_CHUNKS', 16)),
                )
            if exact_table_candidates:
                snippet_chars = max(
                    snippet_chars,
                    int(getattr(settings, 'RAG_EXACT_TABLE_SNIPPET_CHARS', 5000)),
                )
                candidates = exact_table_candidates
                t_route_done = (time.monotonic() - t_route_start) * 1000
            elif attribute_section_candidates:
                snippet_chars = max(
                    snippet_chars,
                    int(getattr(settings, 'RAG_ATTRIBUTE_SECTION_SNIPPET_CHARS', 5000)),
                )
                candidates = attribute_section_candidates
                t_route_done = (time.monotonic() - t_route_start) * 1000
            elif exact_heading_candidates:
                snippet_chars = max(
                    snippet_chars,
                    int(getattr(settings, 'RAG_EXACT_HEADING_SNIPPET_CHARS', 5000)),
                )
                exact_image_assets = self._retrieve_assets_for_exact_image(query, exact_heading_candidates)
                candidates = exact_heading_candidates + exact_image_assets
                t_route_done = (time.monotonic() - t_route_start) * 1000
            else:
                router = self._get_router()

                # Truyền document_ids vào user_context để HybridRetriever / RAPTOR biết giới hạn
                user_context = {
                    'document_ids': resolved_doc_ids,
                    'explicit_document_ids': explicit_doc_ids or [],
                    'folder_ids': folder_ids or [],
                    'rag_mode': rag_mode or 'fast',
                    'forced_intent': self._get_forced_intent_value(query),
                }
                if current_page:
                    user_context['current_page'] = current_page

                # QueryRouter: quyết định dùng RAPTOR hay Hybrid, rồi rerank
                candidates = router.route(
                    query=query,
                    user_context=user_context,
                    top_k=top_k,
                    conversation_history=conversation_history,
                )
                t_route_done = (time.monotonic() - t_route_start) * 1000

            if not candidates:
                logger.debug("[_retrieve_context] Không tìm thấy chunks phù hợp")
                return '', []

            candidates = self._filter_front_matter_candidates(query, candidates)
            is_spreadsheet_retrieval = any(
                c.get('source') == 'spreadsheet'
                or (c.get('metadata') or {}).get('spreadsheet_intent')
                for c in candidates
            )

            # Lấy thông tin tên tài liệu để gắn citation (batch query, tránh N+1)
            # Retrieval payloads only carry short previews. Fetch the selected
            # chunks before prompt building so key facts are not truncated.
            t_chunk_fetch_start = time.monotonic()
            # Separate assets from chunks before neighbor expansion
            asset_candidates_ctx = [c for c in candidates if c.get('source') == 'asset']
            chunk_candidates_ctx = [c for c in candidates if c.get('source') != 'asset']
            if exact_table_candidates:
                chunk_candidates_ctx = exact_table_candidates
            elif attribute_section_candidates:
                chunk_candidates_ctx = attribute_section_candidates
            elif exact_heading_candidates:
                chunk_candidates_ctx = exact_heading_candidates
            elif not is_spreadsheet_retrieval:
                chunk_candidates_ctx = self._expand_candidates_with_neighbors(chunk_candidates_ctx, query)
            candidates = self._deduplicate_candidates_by_content(chunk_candidates_ctx + asset_candidates_ctx)
            # Context stitching: merge sequential chunks into continuous blocks
            if not is_spreadsheet_retrieval:
                candidates = self._stitch_sequential_chunks(candidates)
            # Self-RAG: relevance check, re-retrieve if too few relevant
            relevance = {'passed': True} if (is_spreadsheet_retrieval or exact_table_candidates or attribute_section_candidates or exact_heading_candidates) else self._self_rag_relevance_check(query, candidates)
            if not exact_table_candidates and not attribute_section_candidates and not exact_heading_candidates and not is_spreadsheet_retrieval and not relevance['passed'] and len(resolved_doc_ids) > 0:
                logger.info("[SELF_RAG] Re-retrieving with expanded strategy...")
                try:
                    router = self._get_router()
                    re_user_context = {
                        'document_ids': resolved_doc_ids,
                        'rag_mode': rag_mode or 'fast',
                        'forced_intent': self._get_forced_intent_value(query),
                    }
                    if current_page:
                        re_user_context['current_page'] = current_page
                    re_candidates = router.route(
                        query=query,
                        user_context=re_user_context,
                        top_k=max(8, top_k * 2),
                        conversation_history=conversation_history,
                    )
                    if re_candidates:
                        re_assets = [c for c in re_candidates if c.get('source') == 'asset']
                        re_chunks = [c for c in re_candidates if c.get('source') != 'asset']
                        candidates = self._deduplicate_candidates_by_content(re_chunks + re_assets)
                        candidates = self._stitch_sequential_chunks(candidates)
                        candidates = self._filter_front_matter_candidates(query, candidates)
                        logger.info(f"[SELF_RAG] Re-retrieved {len(candidates)} candidates")
                except Exception as e:
                    logger.warning(f"[SELF_RAG] Re-retrieval failed: {e}")
            t_chunk_fetch_done = (time.monotonic() - t_chunk_fetch_start) * 1000

            t_doc_fetch_start = time.monotonic()
            doc_ids_needed = list({c.get('document_id') for c in candidates if c.get('document_id')})
            doc_name_map: Dict[str, str] = {}
            doc_type_map: Dict[str, str] = {}
            if doc_ids_needed:
                try:
                    Document = apps.get_model('documents', 'Document')
                    docs = Document.objects.filter(id__in=doc_ids_needed, is_deleted=False).values(
                        'id', 'original_name', 'filename', 'file_type', 'mime_type'
                    )
                    for doc in docs:
                        name = doc.get('original_name') or doc.get('filename') or f"doc_{doc['id']}"
                        doc_name_map[str(doc['id'])] = name
                        doc_type_map[str(doc['id'])] = doc.get('file_type') or doc.get('mime_type') or 'document'
                except Exception as e:
                    logger.warning(f"[_retrieve_context] Không thể lấy tên tài liệu: {e}")
            t_doc_fetch_done = (time.monotonic() - t_doc_fetch_start) * 1000

            # Build context string với số thứ tự để LLM trích dẫn dễ hơn
            t_ctx_build_start = time.monotonic()
            context_parts = []
            max_context_chars = self._get_context_max_chars(query)
            max_context_tokens = self._get_context_token_budget(query)
            is_image_intent = self._is_image_query(query)
            asset_token_reserve = int(max_context_tokens * 0.35) if is_image_intent else 0
            asset_char_reserve = int(max_context_chars * 0.35) if is_image_intent else 0
            chunk_token_limit = max(256, max_context_tokens - asset_token_reserve)
            chunk_char_limit = max(1200, max_context_chars - asset_char_reserve)
            context_chars_used = 0
            context_tokens_used = 0
            for i, c in enumerate(candidates, start=1):
                if c.get('source') == 'asset':
                    continue

                doc_id = c.get('document_id', '')
                doc_name = doc_name_map.get(str(doc_id), f'Tài liệu #{i}')
                page = c.get('page')
                chunk_index = c.get('chunk_index')
                metadata = c.get('metadata') or {}
                line_start = self._metadata_value(metadata, 'row_start', 'line_start', 'start_line')
                line_end = self._metadata_value(metadata, 'row_end', 'line_end', 'end_line')
                snippet = (c.get('snippet') or '').strip()[:snippet_chars]
                if snippet:
                    remaining_chars = chunk_char_limit - context_chars_used
                    if remaining_chars <= 0:
                        break
                    snippet = snippet[:remaining_chars]
                    c['citation_id'] = i
                    c['document_title'] = doc_name
                    c['document_type'] = doc_type_map.get(str(doc_id), 'document')
                    c['citation_excerpt'] = snippet
                    page_info = f"Trang: {page}\n" if page else ""
                    line_info = f"Dong: {line_start}-{line_end}\n" if line_start and line_end and line_end != line_start else (f"Dong: {line_start}\n" if line_start else "")
                    chunk_info = f"Doan/Chunk: {chunk_index}\n" if chunk_index is not None else ""
                    heading_path = metadata.get('heading_path') or []
                    heading_info = ""
                    if heading_path:
                        if isinstance(heading_path, (list, tuple)):
                            heading_info = f"Muc: {' > '.join(str(h) for h in heading_path if h)}\n"
                        else:
                            heading_info = f"Muc: {heading_path}\n"
                    source_label = self._build_source_label(
                        title=doc_name,
                        page=page,
                        line_start=line_start,
                        line_end=line_end,
                        citation_id=i,
                    )
                    header = (
                        f"--- NGUON [{i}] ---\n"
                        f"Tai lieu: {doc_name}\n"
                        f"{page_info}"
                        f"{heading_info}"
                        f"{line_info}"
                        f"{chunk_info}"
                        f"Cach trich dan bat buoc: {source_label}\n"
                        "Doan trich:\n"
                    )
                    part_tokens = self._estimate_tokens(header + snippet)
                    remaining_tokens = chunk_token_limit - context_tokens_used
                    if remaining_tokens <= 0:
                        break
                    if part_tokens > remaining_tokens:
                        chars_per_token = float(getattr(settings, 'RAG_CONTEXT_CHARS_PER_TOKEN', 3.2))
                        snippet = snippet[:max(0, int(remaining_tokens * max(1.0, chars_per_token)) - len(header))]
                        part_tokens = self._estimate_tokens(header + snippet)
                        if part_tokens > remaining_tokens:
                            overflow_chars = int((part_tokens - remaining_tokens) * max(1.0, chars_per_token)) + 16
                            snippet = snippet[:max(0, len(snippet) - overflow_chars)]
                            part_tokens = self._estimate_tokens(header + snippet)
                    if part_tokens > remaining_tokens:
                        break
                    if not snippet.strip():
                        break
                    context_parts.append(
                        f"{header}{snippet}"
                    )
                    context_chars_used += len(snippet)
                    context_tokens_used += part_tokens

            # ── Add asset captions to context ────────────────
            asset_parts = []
            for i, c in enumerate(candidates, start=1):
                if c.get('source') == 'asset' and c.get('asset_caption'):
                    # Assign citation_id to asset so LLM can reference it
                    c['citation_id'] = i
                    cap = self._clean_asset_caption(c['asset_caption'])[:220]
                    loc = ''
                    if c.get('asset_sheet_name'):
                        loc += f"Sheet {c['asset_sheet_name']}"
                    if c.get('asset_anchor_cell'):
                        loc += f" cell {c['asset_anchor_cell']}"
                    if c.get('asset_page_number'):
                        loc += f" trang {c['asset_page_number']}"
                    
                    source_label = self._build_source_label(
                        title=doc_name_map.get(str(c.get('document_id')), 'Hinh anh'),
                        page=c.get('asset_page_number'),
                        citation_id=i
                    )
                    
                    prefix = f"--- HINH ANH [{i}] ---\n"
                    if loc:
                        prefix += f"Vi tri: {loc.strip()}\n"
                    prefix += f"Cach trich dan: {source_label}\n"

                    details = [f"{prefix}Mo ta: {cap}"]
                    context_text = (c.get('asset_context_text') or '').strip()
                    if context_text:
                        details.append(f"Ngu canh gan anh: {context_text[:260]}")
                    linked_chunk_text = (c.get('asset_linked_chunk_text') or '').strip()
                    if linked_chunk_text:
                        details.append(f"Doan tai lieu gan nhat: {linked_chunk_text[:320]}")
                    ocr_text = (c.get('asset_ocr_text') or '').strip()
                    if ocr_text:
                        details.append(f"Chu/OCR trong anh: {ocr_text[:260]}")

                    asset_text = "\n".join(details)
                    remaining_tokens = max_context_tokens - context_tokens_used
                    remaining_chars = max_context_chars - context_chars_used
                    if remaining_tokens <= 0 or remaining_chars <= 0:
                        break

                    asset_token_estimate = self._estimate_tokens(asset_text)
                    if asset_token_estimate > remaining_tokens or len(asset_text) > remaining_chars:
                        trimmed_details = [f"{prefix}Mo ta: {cap}"]
                        for label, text, limit in (
                            ("Ngu canh gan anh", context_text, 120),
                            ("Doan tai lieu gan nhat", linked_chunk_text, 180),
                            ("Chu/OCR trong anh", ocr_text, 120),
                        ):
                            if not text:
                                continue
                            candidate_text = "\n".join(trimmed_details + [f"{label}: {text[:limit]}"])
                            if self._estimate_tokens(candidate_text) <= remaining_tokens and len(candidate_text) <= remaining_chars:
                                trimmed_details.append(f"{label}: {text[:limit]}")
                        asset_text = "\n".join(trimmed_details)
                        asset_token_estimate = self._estimate_tokens(asset_text)

                    if asset_token_estimate > remaining_tokens or len(asset_text) > remaining_chars:
                        continue

                    asset_parts.append(asset_text)
                    context_tokens_used += asset_token_estimate
                    context_chars_used += len(asset_text)

            if asset_parts:
                asset_context = "=== THONG TIN HINH ANH TRONG TAI LIEU (CHI TRICH DAN KHI THUC SU LIEN QUAN) ===\n" + "\n\n".join(asset_parts) + "\n=== HET HINH ANH ==="
                context_parts.append(asset_context)

            if not context_parts:
                return '', candidates

            full_context = (
                "=== NOI DUNG TAI LIEU THAM KHAO (CHI DUOC DUNG THONG TIN NAY) ===\n"
                + "\n\n".join(context_parts) +
                "\n=== HET TAI LIEU ==="
            )
            t_ctx_build_done = (time.monotonic() - t_ctx_build_start) * 1000
            t_context_total = (time.monotonic() - t_context_start) * 1000

            logger.info(
                f"[CONTEXT_PROFILE] "
                f"query='{query[:40]}...' "
                f"chunks={len(candidates)} docs={len(doc_name_map)} "
                f"context_chars={context_chars_used}/{max_context_chars} "
                f"context_tokens~={context_tokens_used}/{max_context_tokens} | "
                f"timing: route={t_route_done:.1f}ms, "
                f"chunk_fetch={t_chunk_fetch_done:.1f}ms, "
                f"doc_fetch={t_doc_fetch_done:.1f}ms, "
                f"ctx_build={t_ctx_build_done:.1f}ms, "
                f"total={t_context_total:.1f}ms"
            )
            logger.debug(
                f"[_retrieve_context] {len(candidates)} chunks từ {len(doc_name_map)} tài liệu "
                f"(top score: {candidates[0].get('score', 0):.3f})"
            )
            return full_context, candidates

        except Exception as e:
            logger.error(f"[_retrieve_context] Lỗi retrieval: {e}", exc_info=True)
            return '', []

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def ask(
        self, 
        user_id: int, 
        query: str, 
        conversation_id: int = None,
        filters: Dict = None,
        rag_mode: str = 'fast',
    ) -> Tuple[str, Any]:
        """
        Thực hiện hỏi đáp trực tiếp (Direct Q&A) với hỗ trợ tài liệu nếu có.
        """
        try:
            # 1. Quản lý Conversation
            if conversation_id:
                conversation = self.conversation_repo.get_conversation_by_id(conversation_id, account_id=user_id)
                if not conversation:
                    raise BusinessLogicError(f"Conversation {conversation_id} not found")
            else:
                conversation = self.conversation_repo.create_conversation(account_id=user_id, title=query[:50])

            # 2. Lưu tin nhắn User
            user_message = self.message_repo.create_user_message(
                conversation_id=conversation.id,
                account_id=user_id,
                content=query
            )

            # P2#9: Unified retrieval - use same pipeline as ask_stream()
            # Thay vi search_similar truc tiep, dung _retrieve_context
            # de di qua QueryRouter -> HybridRetriever -> Reranker
            resolved_ids = self._resolve_document_ids(
                user_id=user_id,
                conversation_id=conversation.id,
                document_ids=(filters or {}).get('document_ids') or [],
                folder_ids=(filters or {}).get('folder_ids') or [],
            )
            rag_mode = (filters or {}).get('rag_mode') or rag_mode or 'fast'
            current_page = (filters or {}).get('current_page') or (filters or {}).get('currentPage')

            # 4. Lấy lịch sử
            messages_for_llm = self.message_repo.get_message_history(conversation.id, as_dicts=True)
            if len(messages_for_llm) > 6:
                messages_for_llm = messages_for_llm[-6:]
            
            context_str, rag_candidates = self._retrieve_context(
                query=query,
                resolved_doc_ids=resolved_ids,
                explicit_doc_ids=(filters or {}).get('document_ids') or [],
                folder_ids=(filters or {}).get('folder_ids') or [],
                conversation_history=messages_for_llm,
                top_k=self._get_rag_top_k(query, default_top_k=3),
                snippet_chars=self._get_context_snippet_chars(query),
                rag_mode=rag_mode,
                current_page=current_page,
            )

            exact_table_answer = self._build_exact_table_answer(rag_candidates)
            if exact_table_answer:
                bot_response_text, citations, _grounding = self._finalize_rag_answer(
                    query=query,
                    answer_text=exact_table_answer,
                    context_str=context_str,
                    candidates=rag_candidates,
                    allow_revision=False,
                )
                bot_message = self.message_repo.create_bot_message(
                    conversation_id=conversation.id,
                    content=bot_response_text,
                    metadata=citations,
                )
                return bot_response_text, bot_message

            # 5. Đính kèm tài liệu vào câu hỏi nếu có
            # P2#9: Unified context injection (same as ask_stream)
            if context_str:
                last_msg = messages_for_llm[-1].copy()
                last_msg['content'] = (
                    f"CAU HOI CAN TRA LOI:\n{query}\n\n"
                    f"{context_str}"
                )
                messages_for_llm = [last_msg]

            # 6. Gọi LLM
            use_rag = bool(context_str)
            system_prompt = self.RAG_SYSTEM_PROMPT if use_rag else ''
            bot_response_text = self.llama.chat_complete(
                messages=messages_for_llm,
                system_prompt=system_prompt,
                max_tokens=self._get_rag_max_tokens(query) if use_rag else None,
                temperature=getattr(settings, 'RAG_LLM_TEMPERATURE', 0.2) if use_rag else None,
            )

            # 7. Lưu tin nhắn Bot
            bot_response_text, citations, _grounding = self._finalize_rag_answer(
                query=query,
                answer_text=bot_response_text,
                context_str=context_str,
                candidates=rag_candidates,
            )

            bot_message = self.message_repo.create_bot_message(
                conversation_id=conversation.id,
                content=bot_response_text,
                metadata=citations
            )

            return bot_response_text, bot_message

        except Exception as e:
            logger.error(f"Error in Chat: {str(e)}", exc_info=True)
            raise LLMServiceError(f"Lỗi kết nối LLM: {str(e)}")

    def ask_stream(
        self,
        user_id: int,
        query: str,
        conversation_id: int = None,
        document_ids: List[str] = None,
        folder_ids: List[str] = None,
        rag_mode: str = 'fast',
        current_page: int = None,
    ) -> Generator[str, None, None]:
        """
        Chat STREAM với Model — hỗ trợ RAG khi có tài liệu đính kèm.

        Pipeline:
          1. Quản lý Conversation (get/create)
          2. Lưu user message vào DB
          3. Resolve document_ids (từ request hoặc DB fallback)
          4. [NẾU có tài liệu] Hybrid Search → Rerank → Build context
          5. Build messages cho LLM (có/không có context)
          6. Stream từ LLM (yield từng chunk)
          7. Lưu bot response vào DB sau khi hoàn tất

        Args:
            user_id: ID của user đang chat.
            query: Câu hỏi / tin nhắn của user.
            conversation_id: ID cuộc trò chuyện (None → tạo mới).
            document_ids: List ID tài liệu để giới hạn RAG search (từ frontend).
            folder_ids: List ID thư mục để expand thành document_ids.

        Yields:
            str: Từng text chunk từ LLM.
        """
        import time
        t0 = time.monotonic()

        try:
            # ── BƯỚC 1: Quản lý Conversation ─────────────────────────────────
            if conversation_id:
                conversation = self.conversation_repo.get_conversation_by_id(conversation_id, account_id=user_id)
                if not conversation:
                    logger.warning(f"Conversation {conversation_id} not found, creating new one")
                    conversation = self.conversation_repo.create_conversation(account_id=user_id, title=query[:50])
            else:
                conversation = self.conversation_repo.create_conversation(account_id=user_id, title=query[:50])

            t1 = time.monotonic()
            logger.debug(f"[ask_stream] step1 conversation ready: {(t1-t0)*1000:.1f}ms")

            # ── BƯỚC 2: Lưu tin nhắn User ─────────────────────────────────────
            self.message_repo.create_user_message(
                conversation_id=conversation.id,
                account_id=user_id,
                content=query
            )

            t2 = time.monotonic()
            logger.debug(f"[ask_stream] step2 user_message saved: {(t2-t1)*1000:.1f}ms")

            # ── BƯỚC 3: Lấy lịch sử tin nhắn ─────────────────────────────────
            messages_for_llm = self.message_repo.get_message_history(conversation.id, as_dicts=True)
            if len(messages_for_llm) > 10:
                messages_for_llm = messages_for_llm[-10:]

            t3 = time.monotonic()
            logger.debug(
                f"[ask_stream] step3 history loaded ({len(messages_for_llm)} msgs): {(t3-t2)*1000:.1f}ms"
            )

            # ── BƯỚC 4: Resolve document IDs & RAG Retrieval ──────────────────
            yield {'status': 'Đang chuẩn bị phạm vi tìm kiếm...'}
            resolved_ids = self._resolve_document_ids(
                user_id=user_id,
                conversation_id=conversation.id,
                document_ids=document_ids or [],
                folder_ids=folder_ids or [],
            )

            t4 = time.monotonic()
            logger.debug(
                f"[ask_stream] step4 resolved {len(resolved_ids)} doc IDs: {(t4-t3)*1000:.1f}ms"
            )

            context_str = ''
            rag_candidates = []
            has_rag_scope = bool(resolved_ids)

            if has_rag_scope:
                yield {'status': 'Đang tìm kiếm thông tin trong tài liệu...'}
                context_str, rag_candidates = self._retrieve_context(
                    query=query,
                    resolved_doc_ids=resolved_ids,
                    explicit_doc_ids=document_ids or [],
                    folder_ids=folder_ids or [],
                    conversation_history=messages_for_llm,
                    top_k=self._get_rag_top_k(query, default_top_k=4),
                    snippet_chars=self._get_context_snippet_chars(query),
                    rag_mode=rag_mode,
                    current_page=current_page,
                )
                t5 = time.monotonic()
                logger.debug(
                    f"[ask_stream] step5 RAG retrieved {len(rag_candidates)} chunks: {(t5-t4)*1000:.1f}ms"
                )
                logger.info(
                    f"[ask_stream] 🔍 RAG ACTIVE — {len(resolved_ids)} docs, "
                    f"{len(rag_candidates)} chunks retrieved"
                )
                yield {'status': 'Đang tổng hợp câu trả lời...'}
            else:
                logger.debug("[ask_stream] ℹ️ RAG INACTIVE — không có tài liệu đính kèm, chat thuần")
                yield {'status': 'Đang tạo câu trả lời...'}

            # ── BƯỚC 5: Build prompt cho LLM ──────────────────────────────────
            # Chèn context vào tin nhắn CUỐI của user (không thay đổi lịch sử cũ)
            exact_table_answer = self._build_exact_table_answer(rag_candidates)
            if exact_table_answer:
                full_response, citations, _grounding = self._finalize_rag_answer(
                    query=query,
                    answer_text=exact_table_answer,
                    context_str=context_str,
                    candidates=rag_candidates,
                    allow_revision=False,
                )
                yield full_response
                yield {'citations': citations}
                self.message_repo.create_bot_message(
                    conversation_id=conversation.id,
                    content=full_response,
                    metadata=citations,
                )
                logger.debug(
                    f"Saved deterministic exact-table answer for conversation {conversation.id} "
                    f"({len(citations)} citations)"
                )
                return

            if context_str and messages_for_llm:
                last_msg = messages_for_llm[-1].copy()
                last_msg['content'] = (
                    f"CAU HOI CAN TRA LOI:\n{query}\n\n"
                    f"{context_str}"
                )
                messages_with_context = [last_msg]
            else:
                messages_with_context = messages_for_llm

            use_rag = bool(context_str)
            system_prompt = self.RAG_SYSTEM_PROMPT if use_rag else ''

            t_pre_llm = time.monotonic()
            logger.debug(
                f"[ask_stream] total pre-LLM overhead: {(t_pre_llm-t0)*1000:.1f}ms "
                f"(RAG={'ON' if use_rag else 'OFF'})"
            )

            # ── BƯỚC 6: Stream LLM ────────────────────────────────────────────
            full_response = ''
            first_chunk = True
            citations = []
            verify_before_emit = use_rag and (
                str(rag_mode or '').lower() == 'deep'
                or getattr(settings, 'RAG_STREAM_VERIFY_BEFORE_EMIT', False)
            )
            try:
                for chunk in self.llama.chat_complete_stream(
                    messages=messages_with_context,
                    system_prompt=system_prompt,
                    max_tokens=self._get_rag_max_tokens(query) if use_rag else None,
                    temperature=getattr(settings, 'RAG_LLM_TEMPERATURE', 0.2) if use_rag else None,
                ):
                    if first_chunk:
                        logger.debug(
                            f"[ask_stream] first chunk received: "
                            f"{(time.monotonic()-t_pre_llm)*1000:.1f}ms after LLM call"
                        )
                        first_chunk = False
                    full_response += chunk
                    if not verify_before_emit:
                        yield chunk


                # Sau khi stream text hoan tat, gui citation data qua SSE
                # de frontend hien thi popup nguon tham khao ngay trong phien chat.
                if full_response and rag_candidates:
                    try:
                        full_response, citations, grounding = self._finalize_rag_answer(
                            query=query,
                            answer_text=full_response,
                            context_str=context_str,
                            candidates=rag_candidates,
                            allow_revision=verify_before_emit,
                        )
                        if verify_before_emit:
                            yield full_response
                        yield {'citations': citations}
                    except Exception as cite_err:
                        logger.error(f"[ask_stream] Citation build failed: {cite_err}", exc_info=True)
                        # Fallback: yield basic citations without advanced logic
                        fallback = []
                        for i, c in enumerate(rag_candidates[:5], 1):
                            fallback.append({
                                'id': str(c.get('chunk_id', i)),
                                'number': i,
                                'title': c.get('document_title', 'Tai lieu'),
                                'excerpt': (c.get('snippet') or '')[:300],
                                'source': c.get('source', ''),
                            })
                        yield {'citations': fallback}
                elif full_response and verify_before_emit:
                    yield full_response

            finally:
                # ── BƯỚC 7: Lưu kết quả vào DB (LUÔN chạy kể cả khi client ngắt kết nối) ──
                if full_response:
                    try:
                        # Build citations nếu chưa có (client ngắt kết nối giữa stream)
                        if not citations:
                            try:
                                citations = self._build_citation_payload(rag_candidates, full_response, query)
                            except Exception:
                                citations = []

                        self.message_repo.create_bot_message(
                            conversation_id=conversation.id,
                            content=full_response,
                            metadata=citations
                        )
                        logger.debug(
                            f"✅ Đã lưu tin nhắn Bot vào DB cho conversation {conversation.id} "
                            f"(RAG={'ON' if use_rag else 'OFF'}, {len(citations)} citations)"
                        )
                    except Exception as save_err:
                        logger.error(f"❌ Lỗi khi lưu tin nhắn Bot: {save_err}")

        except Exception as e:
            logger.error(f"Stream error: {str(e)}", exc_info=True)
            yield f"Lỗi hệ thống: {str(e)}"

    def get_conversation_history(self, conversation_id: int, user_id: int) -> List[Any]:
        """
        Lấy toàn bộ lịch sử trò truyện
        
        ✅ CORRECT: Uses MessageRepository (not ORM)
        """
        # Verify permission
        conversation = self.conversation_repo.get_conversation_by_id(conversation_id, user_id)
        if not conversation:
            raise BusinessLogicError("Conversation not found or access denied")
        
        # ✅ CORRECT: Get messages via repository
        return self.message_repo.get_conversation_messages(conversation_id)
