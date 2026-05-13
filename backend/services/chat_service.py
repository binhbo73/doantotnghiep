"""
Chat Service - Bộ điều phối (Orchestrator) hệ thống RAG.
Quy trình: 
1. Nhận yêu cầu của User
2. Lấy lịch sử chat via MessageRepository
3. Tìm kiếm kiến thức liên quan từ Vector DB (Qdrant)
4. Xây dựng Prompt tổng hợp
5. Gọi LLM (LlamaClient) 
6. Lưu tin nhắn vào Database via MessageRepository

Pattern:
    ✅ CORRECT: Service → ConversationRepository/MessageRepository → ORM
    ❌ NEVER: Service → Conversation.objects.*, Message.objects.* directly
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from django.apps import apps
from django.utils import timezone
from core.exceptions import BusinessLogicError, LLMServiceError
from services.ai.llama_client import LlamaClient
from services.ai.embedding_client import EmbeddingClient
from services.ai.qdrant_client import QdrantClient
from repositories.conversation_repository import ConversationRepository
from repositories.message_repository import MessageRepository

logger = logging.getLogger(__name__)


class ChatService:
    """
    RAG Chat Orchestrator - Trái tim của hệ thống hỏi đáp tri thức
    
    ✅ CORRECT DATA FLOW:
    View → ChatService → ConversationRepository/MessageRepository → ORM → Models
    """
    
    SYSTEM_PROMPT = """Bạn là trợ lý ảo AI thông minh, hỗ trợ người dùng giải đáp các thắc mắc.
    Nếu có 'Nội dung tham khảo' bên dưới, hãy ưu tiên sử dụng nó để trả lời và trích dẫn nguồn (ví dụ: '[Nguồn: Tên tài liệu.pdf]').
    Nếu nội dung tham khảo không chứa thông tin cần thiết hoặc không có tài liệu liên quan, bạn hãy sử dụng kiến thức tổng quát của mình để trả lời người dùng một cách chính xác và hữu ích nhất.
    Luôn duy trì thái độ chuyên nghiệp, lịch sự và hỗ trợ.
    """

    def __init__(self):
        """Khởi tạo với các repository và client AI"""
        self.llama = LlamaClient()
        self.embedding = EmbeddingClient()
        self.qdrant = QdrantClient()
        # ✅ CORRECT: Use repositories instead of ORM direct
        self.conversation_repo = ConversationRepository()
        self.message_repo = MessageRepository()

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
                    raise ValidationError(f"Conversation {conversation_id} not found")
            else:
                conversation = self.conversation_repo.create_conversation(account_id=user_id, title=query[:50])

            # 2. Lưu tin nhắn User
            user_message = self.message_repo.create_user_message(
                conversation_id=conversation.id,
                account_id=user_id,
                content=query
            )

            # 3. Lấy ngữ cảnh (Chỉ dùng nếu tìm thấy kết quả tốt)
            query_vector = self.embedding.create_embedding(query)
            search_results = self.qdrant.search_similar(embedding=query_vector, limit=3, score_threshold=0.7)
            
            context_texts = [res[2].get('text_preview', '') for res in search_results]
            source_docs = list(set([res[2].get('document_id') for res in search_results if res[2].get('document_id')]))
            
            # 4. Lấy lịch sử
            messages_for_llm = self.message_repo.get_message_history(conversation.id, as_dicts=True)
            if len(messages_for_llm) > 6:
                messages_for_llm = messages_for_llm[-6:]

            # 5. Đính kèm tài liệu vào câu hỏi nếu có
            if context_texts:
                context_str = "\n".join(context_texts)
                messages_for_llm[-1]["content"] += f"\n\n[Tài liệu tham khảo nội bộ]:\n{context_str}"

            # 6. Gọi LLM trực tiếp (Giống như chat trực tiếp ở port 11435)
            bot_response_text = self.llama.chat_complete(
                messages=messages_for_llm,
                system_prompt="" # Xóa hoàn toàn ràng buộc hệ thống
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
        filters: Dict = None
    ):
        """
        Chat STREAM với Model (Không RAG, Không Prompt ràng buộc)
        
        Pipeline:
          1. Quản lý Conversation (get/create)
          2. Lưu user message vào DB
          3. Lấy lịch sử messages
          4. Stream từ LLM
          5. Lưu bot response vào DB
        """
        import time
        t0 = time.monotonic()

        try:
            # 1. Quản lý Conversation & Tin nhắn User
            if conversation_id:
                conversation = self.conversation_repo.get_conversation_by_id(conversation_id, account_id=user_id)
                if not conversation:
                    logger.warning(f"Conversation {conversation_id} not found, creating new one")
                    conversation = self.conversation_repo.create_conversation(account_id=user_id, title=query[:50])
            else:
                conversation = self.conversation_repo.create_conversation(account_id=user_id, title=query[:50])

            t1 = time.monotonic()
            logger.debug(f"[ask_stream] step1 conversation ready: {(t1-t0)*1000:.1f}ms")

            self.message_repo.create_user_message(
                conversation_id=conversation.id,
                account_id=user_id,
                content=query
            )

            t2 = time.monotonic()
            logger.debug(f"[ask_stream] step2 user_message saved: {(t2-t1)*1000:.1f}ms")

            # 2. Lấy lịch sử tin nhắn (Chỉ lấy tin nhắn gốc của user và bot)
            messages_for_llm = self.message_repo.get_message_history(conversation.id, as_dicts=True)
            if len(messages_for_llm) > 10:
                messages_for_llm = messages_for_llm[-10:]

            t3 = time.monotonic()
            logger.debug(f"[ask_stream] step3 history loaded ({len(messages_for_llm)} msgs): {(t3-t2)*1000:.1f}ms")
            logger.debug(f"[ask_stream] total pre-LLM overhead: {(t3-t0)*1000:.1f}ms")

            full_response = ""
            first_chunk = True
            try:
                # 3. Stream kết quả trực tiếp từ LLM
                for chunk in self.llama.chat_complete_stream(
                    messages=messages_for_llm
                ):
                    if first_chunk:
                        logger.debug(f"[ask_stream] first chunk received: {(time.monotonic()-t3)*1000:.1f}ms after LLM call")
                        first_chunk = False
                    full_response += chunk
                    yield chunk
            finally:
                # 4. LUÔN LUÔN lưu kết quả vào DB (ngảy cả khi client ngắt kết nối)
                if full_response:
                    try:
                        self.message_repo.create_bot_message(
                            conversation_id=conversation.id,
                            content=full_response,
                            metadata={'direct_chat': True, 'streaming': True}
                        )
                        logger.debug(f"✅ Đã lưu tin nhắn Bot vào DB cho conversation {conversation.id}")
                    except Exception as save_err:
                        logger.error(f"❌ Lỗi khi lưu tin nhắn Bot: {str(save_err)}")

        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
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
