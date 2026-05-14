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
import time
from typing import List, Dict, Any, Optional, Tuple, Generator
from django.apps import apps
from django.conf import settings
from django.utils import timezone
from core.exceptions import BusinessLogicError, LLMServiceError
from services.ai.llama_client import LlamaClient
from services.ai.embedding_client import EmbeddingClient
from services.ai.qdrant_client import QdrantClient
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

    # Fix B: RAG prompt cuc manh - bat buoc CHI dung tai lieu, cam suy dien
    RAG_SYSTEM_PROMPT = """BAN LA TRO LY TRA LOI DUA TREN TAI LIEU DUOC CUNG CAP.

QUY TAC BAT BUOC:
1. CHI tra loi dua vao NOI DUNG TAI LIEU THAM KHAO ben duoi.
2. TUYET DOI KHONG dung kien thuc ben ngoai hoac suy doan.
3. Tra loi DUNG Y DINH CAU HOI HIEN TAI; bo qua cac doan lien quan nhung tra loi cho cau hoi khac.
4. Neu cau hoi hoi "tai sao/vi sao/ly do", uu tien cac doan co "ly do", "vi", "do", "nguyen nhan", "buoc phai".
5. KHONG tra loi "khong co thong tin" neu bat ky doan nao da tra loi truc tiep cau hoi.
6. NEU tai lieu thuc su khong chua thong tin, hay tra loi: "Tai lieu khong co thong tin nay."
7. Trich dan nguon cu the: [Nguon: ten_file, trang X] cho moi y.
8. Tra loi NGAN GON, dung y chinh, khong dai dong.
9. NEU cau hoi la dang liet ke/"gom nhung gi"/"dac trung", phai liet ke DAY DU cac y co trong tai lieu tham khao, khong rut gon mat y.

NEU BAN DUNG KIEN THUC NGOAI TAI LIEU, CAU TRA LOI SAI.
TAT CA THONG TIN PHAI DEN TU TAI LIEU DUOC CUNG CAP."""

    def __init__(self):
        """Khởi tạo với các repository và client AI"""
        self.llama = LlamaClient()
        self.embedding = EmbeddingClient()
        self.qdrant = QdrantClient()
        # ✅ CORRECT: Use repositories instead of ORM direct
        self.conversation_repo = ConversationRepository()
        self.message_repo = MessageRepository()
        self.document_repo = DocumentRepository()
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

    def _is_list_style_query(self, query: str) -> bool:
        """Detect queries that expect comprehensive bullet/list answers."""
        q = (query or '').lower()
        list_markers = [
            'đặc trưng', 'dac trung', 'bao gồm', 'bao gom', 'gồm', 'gom',
            'liệt kê', 'liet ke', 'nêu', 'neu', 'những gì', 'nhung gi',
            'các', 'cac', 'kể', 'ke', 'list',
        ]
        return any(marker in q for marker in list_markers)

    def _get_rag_top_k(self, query: str, default_top_k: int) -> int:
        """Increase retrieval depth for list-style questions to reduce missing points."""
        base_top_k = int(getattr(settings, 'RAG_RETRIEVAL_TOP_K', default_top_k))
        list_top_k = int(getattr(settings, 'RAG_RETRIEVAL_TOP_K_LIST', max(base_top_k, 8)))
        return list_top_k if self._is_list_style_query(query) else base_top_k

    def _get_rag_max_tokens(self, query: str) -> int:
        """Allow longer output for list-style questions so answers are not truncated."""
        base_tokens = int(getattr(settings, 'RAG_LLM_MAX_TOKENS', 384))
        list_tokens = int(getattr(settings, 'RAG_LLM_MAX_TOKENS_LIST', max(base_tokens, 768)))
        return list_tokens if self._is_list_style_query(query) else base_tokens

    def _get_context_snippet_chars(self, query: str) -> int:
        """Allow larger per-chunk context for list-style questions."""
        base_chars = int(getattr(settings, 'RAG_CONTEXT_SNIPPET_CHARS', 1400))
        list_chars = int(getattr(settings, 'RAG_CONTEXT_SNIPPET_CHARS_LIST', max(base_chars, 2200)))
        return list_chars if self._is_list_style_query(query) else base_chars

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
        # -> Tự động tìm kiếm trong TẤT CẢ tài liệu mà user có quyền truy cập.
        if not final_ids and user_id:
            logger.info(f"[_resolve_document_ids] No explicit attachments, fetching accessible documents via repository for user {user_id}")
            try:
                # Sử dụng chính logic mà giao diện "Đính kèm hệ thống" đang dùng
                accessible_qs = self.document_repo.get_accessible_documents(user_id)
                accessible_ids = list(accessible_qs.values_list('id', flat=True))
                final_ids.extend([str(i) for i in accessible_ids])
                
                if final_ids:
                    logger.debug(f"[_resolve_document_ids] Resolved {len(final_ids)} documents from Scope-based permissions")
            except Exception as e:
                logger.error(f"[_resolve_document_ids] Lỗi khi lấy danh sách tài liệu truy cập: {e}")

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
            try:
                DocumentChunk = apps.get_model('documents', 'DocumentChunk')
                chunk_ids_needed = [c.get('chunk_id') for c in candidates if c.get('chunk_id')]
                chunks = DocumentChunk.objects.filter(
                    id__in=chunk_ids_needed,
                    is_deleted=False,
                ).values('id', 'document_id', 'content', 'page_number')
                chunk_map = {str(chunk['id']): chunk for chunk in chunks}
                for candidate in candidates:
                    chunk = chunk_map.get(str(candidate.get('chunk_id')))
                    if not chunk:
                        continue
                    candidate['document_id'] = str(chunk['document_id'])
                    candidate['snippet'] = chunk.get('content') or candidate.get('snippet') or ''
                    candidate['page'] = chunk.get('page_number') or candidate.get('page')
            except Exception as e:
                logger.warning(f"[_retrieve_context] Khong the hydrate chunks: {e}")
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
            for i, c in enumerate(candidates, start=1):
                doc_id = c.get('document_id', '')
                doc_name = doc_name_map.get(str(doc_id), f'Tài liệu #{i}')
                page = c.get('page')
                page_info = f", trang {page}" if page else ''
                snippet = (c.get('snippet') or '').strip()[:snippet_chars]
                if snippet:
                    context_parts.append(
                        f"--- TAI LIEU {i}: {doc_name}{page_info} ---\n{snippet}"
                    )

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
                f"chunks={len(candidates)} docs={len(doc_name_map)} | "
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
                last_msg['content'] = f"{query}\n\n{context_str}"
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
