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
    RAG_SYSTEM_PROMPT = """BAN LA TRO LY RAG TRA LOI DUY NHAT DUA TREN TAI LIEU DUOC CUNG CAP.

NGUYEN TAC BAT BUOC:
1. Chi dung "NOI DUNG TAI LIEU THAM KHAO" de tra loi. Khong dung kien thuc ben ngoai, khong suy doan.
2. Tra loi dung cau hoi hien tai. Bo qua doan tham khao khong tra loi truc tiep cau hoi.
3. Neu tai lieu khong du thong tin de tra loi, noi ro: "Tai lieu khong co thong tin nay." Neu chi thieu mot phan, tra loi phan co bang chung va noi phan nao khong thay trong tai lieu.
4. Moi y quan trong phai co trich dan: [Nguon: ten_file, trang X]. Neu khong co trang, dung vi tri/chunk co trong nguon.

CACH LAM VIEC:
1. Tu xac dinh kieu cau hoi:
   - dinh nghia/giai thich: tra loi ro khai niem va cac y giai thich co trong tai lieu.
   - liet ke/gom nhung gi/cac/nhung/day du/chi tiet: phai trich xuat day du tat ca muc chinh, muc con, dau gach, so thu tu lien quan.
   - so sanh: neu diem giong, khac, tieu chi so sanh co trong tai lieu thi trinh bay theo bang hoac bullet.
   - quy trinh/cac buoc: giu dung thu tu buoc trong tai lieu.
   - so lieu/bang bieu: chep dung so, don vi, dieu kien, moc thoi gian; khong lam tron neu tai lieu khong lam tron.
   - cau hoi tai sao/ly do/nguyen nhan: chi neu cac ly do/nguyen nhan duoc tai lieu neu truc tiep.
2. Khi cau hoi yeu cau day du:
   - Doc tat ca doan tham khao lien quan, ke ca doan/trang/chunk lien tiep.
   - Giu cau truc tai lieu: muc chinh -> y con -> chi tiet.
   - Khong rut gon mat y con, vi du, ngoai le, dieu kien, dau (+/-) neu chung tra loi truc tiep cau hoi.
3. Khi cau hoi khong yeu cau day du, tra loi ngan gon, dung trong tam, van phai co trich dan.
4. Neu cac doan tai lieu mau thuan nhau, neu ca hai thong tin va trich dan tung nguon; khong tu chon mot ben neu tai lieu khong cho biet.
5. Khong viet loi dan dai, khong nhac lai quy tac, khong noi ve qua trinh suy luan noi bo."""

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

    def _normalize_query_text(self, text: str) -> str:
        """Lowercase Vietnamese text and remove accents for intent checks."""
        normalized = unicodedata.normalize('NFD', text or '')
        without_marks = ''.join(
            ch for ch in normalized
            if unicodedata.category(ch) != 'Mn'
        )
        return re.sub(r'\s+', ' ', without_marks.lower()).strip()

    def _is_list_style_query(self, query: str) -> bool:
        """Detect questions that need comprehensive extraction, not a short fact."""
        q = self._normalize_query_text(query)
        if not q:
            return False

        comprehensive_patterns = [
            r'\b(cac|nhung)\b',
            r'\b(bao gom|gom|gom nhung gi)\b',
            r'\b(liet ke|ke ra|neu|trinh bay)\b',
            r'\b(day du|chi tiet|tat ca)\b',
            r'\b(la gi|nhu the nao)\b',
            r'\b(dac diem|dac trung|thanh phan|noi dung|nguyen tac|yeu cau)\b',
            r'^\s*\d+\s*[/.)-]\s*',
        ]
        return any(re.search(pattern, q) for pattern in comprehensive_patterns)

    def _get_rag_top_k(self, query: str, default_top_k: int) -> int:
        """Increase retrieval depth for list-style questions to reduce missing points."""
        base_top_k = int(getattr(settings, 'RAG_RETRIEVAL_TOP_K', default_top_k))
        list_top_k = int(getattr(settings, 'RAG_RETRIEVAL_TOP_K_LIST', max(base_top_k, 12)))
        return list_top_k if self._is_list_style_query(query) else base_top_k

    def _get_rag_max_tokens(self, query: str) -> int:
        """Allow longer output for list-style questions so answers are not truncated."""
        base_tokens = int(getattr(settings, 'RAG_LLM_MAX_TOKENS', 384))
        list_tokens = int(getattr(settings, 'RAG_LLM_MAX_TOKENS_LIST', max(base_tokens, 1024)))
        return list_tokens if self._is_list_style_query(query) else base_tokens

    def _get_context_snippet_chars(self, query: str) -> int:
        """Allow larger per-chunk context for list-style questions."""
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
        configured_chars = list_chars if self._is_list_style_query(query) else base_chars
        token_budget = self._get_context_token_budget(query)
        chars_per_token = float(getattr(settings, 'RAG_CONTEXT_CHARS_PER_TOKEN', 3.2))
        token_safe_chars = int(token_budget * max(1.0, chars_per_token))
        return max(1200, min(configured_chars, token_safe_chars))

    def _get_neighbor_window(self, query: str) -> Tuple[int, int, int]:
        """Return before/after/max chunks for context expansion."""
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
            ).values('id', 'document_id', 'content', 'page_number', 'chunk_index', 'node_type')
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
                        'id', 'document_id', 'content', 'page_number', 'chunk_index', 'node_type'
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
        
        # FINAL FALLBACK: Nếu vẫn không có IDs nào (không truyền từ request, không có trong DB)
        # -> Tự động tìm kiếm trong toàn bộ tài liệu và folder mà user có quyền truy cập.
        if not final_ids and user_id:
            logger.info(
                f"[_resolve_document_ids] No explicit attachments, fetching accessible documents/folders for user {user_id}"
            )
            try:
                # Sử dụng đúng logic mà giao diện "Đính kèm từ hệ thống" đang dùng.
                # Bao gồm cả tài liệu trực tiếp và tài liệu nằm trong folder user được phép truy cập.
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
                        f"[_resolve_document_ids] Resolved {len(final_ids)} document IDs from accessible documents/folders"
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
        top_k: int = 4,  # Fix E: Giam tu 5 -> 4 de nhanh hon, it noise hon
        snippet_chars: int = 900,
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
            router = self._get_router()

            # Truyền document_ids vào user_context để HybridRetriever / RAPTOR biết giới hạn
            user_context = {'document_ids': resolved_doc_ids}

            # QueryRouter: quyết định dùng RAPTOR hay Hybrid, rồi rerank
            candidates = router.route(
                query=query,
                user_context=user_context,
                top_k=top_k,
            )
            t_route_done = (time.monotonic() - t_route_start) * 1000

            if not candidates:
                logger.debug("[_retrieve_context] Không tìm thấy chunks phù hợp")
                return '', []

            # Lấy thông tin tên tài liệu để gắn citation (batch query, tránh N+1)
            # Retrieval payloads only carry short previews. Fetch the selected
            # chunks before prompt building so key facts are not truncated.
            t_chunk_fetch_start = time.monotonic()
            candidates = self._expand_candidates_with_neighbors(candidates, query)
            t_chunk_fetch_done = (time.monotonic() - t_chunk_fetch_start) * 1000

            t_doc_fetch_start = time.monotonic()
            doc_ids_needed = list({c.get('document_id') for c in candidates if c.get('document_id')})
            doc_name_map: Dict[str, str] = {}
            if doc_ids_needed:
                try:
                    Document = apps.get_model('documents', 'Document')
                    docs = Document.objects.filter(id__in=doc_ids_needed, is_deleted=False).values('id', 'original_name', 'filename')
                    for doc in docs:
                        name = doc.get('original_name') or doc.get('filename') or f"doc_{doc['id']}"
                        doc_name_map[str(doc['id'])] = name
                except Exception as e:
                    logger.warning(f"[_retrieve_context] Không thể lấy tên tài liệu: {e}")
            t_doc_fetch_done = (time.monotonic() - t_doc_fetch_start) * 1000

            # Build context string với số thứ tự để LLM trích dẫn dễ hơn
            t_ctx_build_start = time.monotonic()
            context_parts = []
            max_context_chars = self._get_context_max_chars(query)
            max_context_tokens = self._get_context_token_budget(query)
            context_chars_used = 0
            context_tokens_used = 0
            for i, c in enumerate(candidates, start=1):
                doc_id = c.get('document_id', '')
                doc_name = doc_name_map.get(str(doc_id), f'Tài liệu #{i}')
                page = c.get('page')
                page_info = f", trang {page}" if page else ''
                snippet = (c.get('snippet') or '').strip()[:snippet_chars]
                if snippet:
                    remaining_chars = max_context_chars - context_chars_used
                    if remaining_chars <= 0:
                        break
                    snippet = snippet[:remaining_chars]
                    header = f"--- TAI LIEU {i}: {doc_name}{page_info} ---\n"
                    part_tokens = self._estimate_tokens(header + snippet)
                    remaining_tokens = max_context_tokens - context_tokens_used
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

            if not context_parts:
                return '', candidates

            context_str = "\n\n".join(context_parts)
            full_context = (
                "=== NOI DUNG TAI LIEU THAM KHAO (CHI DUOC DUNG THONG TIN NAY) ===\n"
                + context_str +
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
        filters: Dict = None
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
                document_ids=[],
                folder_ids=[],
            )
            
            context_str, rag_candidates = self._retrieve_context(
                query=query,
                resolved_doc_ids=resolved_ids,
                top_k=self._get_rag_top_k(query, default_top_k=3),
                snippet_chars=self._get_context_snippet_chars(query),
            )
            
            context_texts = [context_str] if context_str else []
            source_docs = list(set([
                c.get('document_id') for c in rag_candidates if c.get('document_id')
            ]))
            
            # 4. Lấy lịch sử
            messages_for_llm = self.message_repo.get_message_history(conversation.id, as_dicts=True)
            if len(messages_for_llm) > 6:
                messages_for_llm = messages_for_llm[-6:]

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
            bot_message = self.message_repo.create_bot_message(
                conversation_id=conversation.id,
                content=bot_response_text,
                metadata={'sources': source_docs}
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
            use_rag = bool(resolved_ids)

            if use_rag:
                yield {'status': 'Đang tìm kiếm thông tin trong tài liệu...'}
                context_str, rag_candidates = self._retrieve_context(
                    query=query,
                    resolved_doc_ids=resolved_ids,
                    top_k=self._get_rag_top_k(query, default_top_k=4),
                    snippet_chars=self._get_context_snippet_chars(query),
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
            if context_str and messages_for_llm:
                last_msg = messages_for_llm[-1].copy()
                last_msg['content'] = (
                    f"CAU HOI CAN TRA LOI:\n{query}\n\n"
                    f"{context_str}"
                )
                messages_with_context = [last_msg]
            else:
                messages_with_context = messages_for_llm

            system_prompt = self.RAG_SYSTEM_PROMPT if use_rag else ''

            t_pre_llm = time.monotonic()
            logger.debug(
                f"[ask_stream] total pre-LLM overhead: {(t_pre_llm-t0)*1000:.1f}ms "
                f"(RAG={'ON' if use_rag else 'OFF'})"
            )

            # ── BƯỚC 6: Stream LLM ────────────────────────────────────────────
            full_response = ''
            first_chunk = True
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
                    yield chunk

            finally:
                # ── BƯỚC 7: Lưu kết quả vào DB (LUÔN chạy kể cả khi client ngắt kết nối) ──
                if full_response:
                    try:
                        # Lưu citations vào metadata để frontend hiển thị
                        citations = []
                        for c in rag_candidates:
                            if c.get('document_id'):
                                citations.append({
                                    'document_id': c.get('document_id'),
                                    'chunk_id': c.get('chunk_id'),
                                    'score': round(float(c.get('score', 0)), 3),
                                    'source': c.get('source', ''),
                                    'page': c.get('page'),
                                })

                        self.message_repo.create_bot_message(
                            conversation_id=conversation.id,
                            content=full_response,
                            metadata={
                                'direct_chat': not use_rag,
                                'streaming': True,
                                'rag_active': use_rag,
                                'document_ids': resolved_ids,
                                'citations': citations,
                            }
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
