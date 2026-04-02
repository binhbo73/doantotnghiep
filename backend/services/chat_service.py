"""
Chat Service - Bộ điều phối (Orchestrator) hệ thống RAG.
Quy trình: 
1. Nhận yêu cầu của User
2. Lấy lịch sử chat
3. Tìm kiếm kiến thức liên quan từ Vector DB (Qdrant)
4. Xây dựng Prompt tổng hợp
5. Gọi LLM (LlamaClient) 
6. Lưu tin nhắn vào Database
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from django.apps import apps
from django.utils import timezone
from core.exceptions import BusinessLogicError, LLMServiceError
from services.ai.llama_client import LlamaClient
from services.ai.qdrant_client import QdrantClient

logger = logging.getLogger(__name__)


class ChatService:
    """
    RAG Chat Orchestrator - Trái tim của hệ thống hỏi đáp tri thức
    """
    
    SYSTEM_PROMPT = """Bạn là trợ lý ảo AI thông minh, hỗ trợ người dùng dựa trên KIẾN THỨC NỘI BỘ được cung cấp.
    HÃY TUÂN THỦ CÁC QUY TẮC SAU:
    1. Chỉ trả lời dựa trên phần 'Nội dung tham khảo' bên dưới. 
    2. Nếu không có thông tin trong nội dung tham khảo, hãy nói: 'Xin lỗi, tôi không tìm thấy thông tin này trong tài liệu hệ thống'.
    3. Trình bày rõ ràng, súc tích, chuyên nghiệp.
    4. Trích dẫn tên tài liệu nếu có (ví dụ: '[Nguồn: Báo cáo năm 2023.pdf]').
    """

    def __init__(self):
        """Khởi tạo với các client AI"""
        self.llama = LlamaClient()
        self.qdrant = QdrantClient()
        # Models
        self.Conversation = apps.get_model('operations', 'Conversation')
        self.Message = apps.get_model('operations', 'Message')
        self.Document = apps.get_model('documents', 'Document')

    def ask(
        self, 
        user_id: int, 
        query: str, 
        conversation_id: int = None,
        filters: Dict = None
    ) -> Tuple[str, Any]:
        """
        Thực hiện chu trình RAG hoàn chỉnh (Hỏi đáp trên tài liệu)
        
        Args:
            user_id: ID người hỏi
            query: Câu hỏi của người dùng
            conversation_id: ID cuộc hội thoại (nếu có)
            filters: Các điều kiện lọc tài liệu (theo department, folder...)
            
        Returns:
            (phiên_bản_text_trả_lời, đối_tượng_tin_nhắn_bot)
        """
        try:
            # 1. Quản lý Conversation
            if conversation_id:
                conversation = self.Conversation.objects.get(pk=conversation_id, account_id=user_id)
            else:
                # Tạo cuộc hội thoại mới nếu chưa có
                conversation = self.Conversation.objects.create(
                    account_id=user_id,
                    title=query[:50] + "..."
                )

            # 2. Lưu tin nhắn của Người dùng
            user_message = self.Message.objects.create(
                conversation=conversation,
                account_id=user_id,
                role='user',
                content=query
            )

            # 3. Retrieval - Tìm kiếm kiến thức liên quan (Vector Search)
            # a. Tạo embedding cho câu hỏi
            query_vector = self.llama.create_embedding(query)
            
            # b. Tìm kiếm top K đoạn văn bản trong Qdrant
            search_results = self.qdrant.search_similar(
                embedding=query_vector,
                limit=5,
                score_threshold=0.7,
                filter_payload=filters  # Lọc theo quyền truy cập của User
            )
            
            # c. Trích xuất text từ các kết quả tìm thấy
            context_texts = []
            source_docs = set()
            for vector_id, score, payload in search_results:
                text = payload.get('text_preview', '[Thông tin không xác định]')
                doc_id = payload.get('document_id')
                if doc_id:
                    source_docs.add(doc_id)
                context_texts.append(f"- {text}")
            
            context_str = "\n".join(context_texts) if context_texts else "Không tìm thấy tài liệu liên quan."

            # 4. Lấy lịch sử chat (3 tin nhắn gần nhất) để giữ ngữ cảnh
            history = self.Message.objects.filter(
                conversation=conversation
            ).order_by('-created_at')[:4]
            
            messages_for_llm = []
            for msg in reversed(history):
                messages_for_llm.append({"role": msg.role, "content": msg.content})

            # 5. Xây dựng Final Prompt (Augmentation)
            full_prompt = f"Dựa trên các thông tin sau để trả lời người dùng:\n\nNỘI DUNG THAM KHẢO:\n{context_str}\n\nCÂU HỎI: {query}"
            
            # Thay thế câu hỏi mới nhất bằng prompt có chứa context
            if messages_for_llm:
                messages_for_llm[-1]["content"] = full_prompt
            else:
                messages_for_llm = [{"role": "user", "content": full_prompt}]

            # 6. Gọi LLM để sinh câu trả lời (Generation)
            bot_response_text = self.llama.chat_complete(
                messages=messages_for_llm,
                system_prompt=self.SYSTEM_PROMPT
            )

            # 7. Lưu câu trả lời của Bot và metadata nguồn dẫn
            bot_message = self.Message.objects.create(
                conversation=conversation,
                account_id=None,  # Hệ thống
                role='assistant',
                content=bot_response_text,
                metadata={
                    'sources': list(source_docs),
                    'total_context_chunks': len(context_texts)
                }
            )

            return bot_response_text, bot_message

        except Exception as e:
            logger.error(f"Error in RAG process: {str(e)}", exc_info=True)
            raise LLMServiceError(f"Hệ thống RAG gặp sự cố: {str(e)}")

    def get_conversation_history(self, conversation_id: int, user_id: int) -> List[Any]:
        """Lấy toàn bộ lịch sử trò truyện"""
        history = self.Message.objects.filter(
            conversation_id=conversation_id,
            conversation__account_id=user_id
        ).order_by('created_at')
        return list(history)
