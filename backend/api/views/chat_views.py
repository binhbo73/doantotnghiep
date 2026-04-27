"""
Chat Views - REST API endpoints for RAG chat system.

Features:
1. Conversation Management (Create, List, Retrieve, Update)
2. Message Management (Send message, List messages)
3. Human Feedback (Rate AI responses)
4. Chat History

Endpoints:
- POST /api/v1/chat/conversations - Create conversation
- GET /api/v1/chat/conversations - List user's conversations
- GET /api/v1/chat/conversations/{id} - Get conversation details
- POST /api/v1/chat/messages - Send message (triggers RAG pipeline)
- GET /api/v1/chat/conversations/{id}/messages - Get messages in conversation
- POST /api/v1/chat/messages/{id}/feedback - Rate AI response
"""
import logging
from typing import Optional
from uuid import UUID

from django.utils import timezone
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from apps.operations.models import (
    Conversation, Message, HumanFeedback,
    ConversationAttachedDocument, ConversationAttachedFolder
)
from apps.documents.models import Document, Folder
from repositories.conversation_repository import ConversationRepository
from repositories.message_repository import MessageRepository

from api.views.base import BaseViewSet
from api.serializers.base import ResponseBuilder
from api.serializers.chat_serializers import (
    ConversationSimpleSerializer,
    ConversationDetailSerializer,
    ConversationCreateSerializer,
    MessageSimpleSerializer,
    MessageDetailSerializer,
    MessageCreateSerializer,
    MessageListQuerySerializer,
    HumanFeedbackCreateSerializer,
    HumanFeedbackSerializer,
    ConversationHistorySerializer,
)
from core.exceptions import BusinessLogicError, ValidationError

logger = logging.getLogger(__name__)


# ============================================================
# PAGINATION
# ============================================================

class ChatPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500


# ============================================================
# CONVERSATION VIEWS
# ============================================================

class ConversationListCreateView(BaseViewSet):
    """
    GET /api/v1/chat/conversations - List user's conversations (paginated)
    POST /api/v1/chat/conversations - Create new conversation
    """
    permission_classes = [IsAuthenticated]
    pagination_class = ChatPagination
    
    def get_queryset(self):
        """Get conversations for current user"""
        user = self.request.user
        return Conversation.objects.filter(
            account=user,
            is_deleted=False
        ).order_by('-updated_at')
    
    def list(self, request: Request) -> Response:
        """
        List all conversations for authenticated user.
        
        Query Parameters:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 50, max: 500)
        - search: Search in conversation title
        """
        queryset = self.get_queryset()
        
        # Debug logging
        current_user = request.user
        logger.info(f"📋 Fetching conversations for user: {current_user.id} ({current_user.username})")
        logger.info(f"📊 Total conversations found: {queryset.count()}")
        
        # Search filter
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(summary__icontains=search)
            )
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ConversationSimpleSerializer(page, many=True)
            logger.info(f"✅ Returning paginated response: {len(serializer.data)} conversations")
            return Response(
                ResponseBuilder.paginated(
                    items=serializer.data,
                    page=self.paginator.page.number,
                    page_size=self.paginator.page.paginator.per_page,
                    total_items=self.paginator.page.paginator.count,
                    message="Conversations retrieved successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        serializer = ConversationSimpleSerializer(queryset, many=True)
        return self.success_response(
            data=serializer.data,
            message="Conversations retrieved successfully"
        )
    
    def create(self, request: Request) -> Response:
        """
        Create new conversation.
        
        Request Body:
        {
            "title": "Optional title",
            "document_ids": [uuid, uuid],
            "folder_ids": [uuid, uuid]
        }
        """
        try:
            serializer = ConversationCreateSerializer(
                data=request.data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            conversation = serializer.save()
            
            logger.info(f"Conversation {conversation.id} created by user {request.user.id}")
            
            return self.success_response(
                data=ConversationDetailSerializer(conversation).data,
                message="Conversation created successfully",
                status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}", exc_info=True)
            return self.error_response(
                message=f"Failed to create conversation: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST
            )


class ConversationDetailView(BaseViewSet):
    """
    GET /api/v1/chat/conversations/{id} - Get conversation details
    PUT /api/v1/chat/conversations/{id} - Update conversation
    DELETE /api/v1/chat/conversations/{id} - Delete conversation
    """
    permission_classes = [IsAuthenticated]
    
    def get_object(self, conversation_id: UUID) -> Optional[Conversation]:
        """Get conversation and verify ownership"""
        try:
            conversation = Conversation.objects.get(
                id=conversation_id,
                account=self.request.user,
                is_deleted=False
            )
            return conversation
        except Conversation.DoesNotExist:
            return None
    
    def retrieve(self, request: Request, conversation_id: str) -> Response:
        """Get conversation details with message history"""
        try:
            conversation = self.get_object(UUID(conversation_id))
            
            if not conversation:
                return self.error_response(
                    message="Conversation not found or access denied",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            serializer = ConversationDetailSerializer(conversation)
            return self.success_response(
                data=serializer.data,
                message="Conversation retrieved successfully"
            )
        except ValueError:
            return self.error_response(
                message="Invalid conversation ID format",
                status_code=status.HTTP_400_BAD_REQUEST
            )
    
    def update(self, request: Request, conversation_id: str) -> Response:
        """Update conversation title/summary"""
        try:
            conversation = self.get_object(UUID(conversation_id))
            
            if not conversation:
                return self.error_response(
                    message="Conversation not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Update allowed fields
            if 'title' in request.data:
                conversation.title = request.data['title']
            if 'summary' in request.data:
                conversation.summary = request.data['summary']
            
            conversation.save()
            logger.info(f"Conversation {conversation_id} updated by user {request.user.id}")
            
            return self.success_response(
                data=ConversationDetailSerializer(conversation).data,
                message="Conversation updated successfully"
            )
        except ValueError:
            return self.error_response(
                message="Invalid conversation ID format",
                status_code=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request: Request, conversation_id: str) -> Response:
        """Soft delete conversation"""
        try:
            conversation = self.get_object(UUID(conversation_id))
            
            if not conversation:
                return self.error_response(
                    message="Conversation not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Soft delete
            conversation.is_deleted = True
            conversation.save()
            
            logger.info(f"Conversation {conversation_id} deleted by user {request.user.id}")
            
            return self.success_response(
                message="Conversation deleted successfully",
                status_code=status.HTTP_204_NO_CONTENT
            )
        except ValueError:
            return self.error_response(
                message="Invalid conversation ID format",
                status_code=status.HTTP_400_BAD_REQUEST
            )


# ============================================================
# MESSAGE VIEWS
# ============================================================

class MessageSendView(BaseViewSet):
    """
    POST /api/v1/chat/messages - Send message to AI (triggers RAG pipeline)
    
    This is the main endpoint for user queries.
    It integrates with ChatService to handle:
    1. Save user message
    2. Vector search in Qdrant
    3. LLM inference
    4. Save AI response
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'], url_path='stream')
    def stream(self, request: Request) -> Response:
        """
        Gửi tin nhắn và nhận kết quả dạng STREAMING (Trả về từng chữ).
        Giống hệt giao diện llama-server ở port 11435.
        """
        from django.http import StreamingHttpResponse
        from services.chat_service import ChatService
        import json

        content = request.data.get('content')
        conversation_id = request.data.get('conversation_id')
        
        if not content:
            return self.error_response("Nội dung không được để trống", status.HTTP_400_BAD_REQUEST)

        chat_service = ChatService()

        def stream_generator():
            try:
                # Trả về data dạng SSE (Server-Sent Events)
                for chunk in chat_service.ask_stream(
                    user_id=request.user.id,
                    query=content,
                    conversation_id=conversation_id
                ):
                    # Format data để frontend dễ xử lý
                    yield f"data: {json.dumps({'text': chunk})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingHttpResponse(
            stream_generator(),
            content_type='text/event-stream'
        )

    def create(self, request: Request) -> Response:
        """
        Send message to AI assistant.
        
        Request Body:
        {
            "conversation_id": "uuid",
            "content": "Your question here",
            "document_ids": [optional uuids],
            "folder_ids": [optional uuids]
        }
        
        Response includes:
        - AI response message
        - Source documents cited
        - Tokens used
        """
        try:
            serializer = MessageCreateSerializer(
                data=request.data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            bot_message = serializer.save()
            
            logger.info(f"User {request.user.id} sent message in conversation")
            
            return self.success_response(
                data=MessageDetailSerializer(bot_message).data,
                message="Message processed successfully",
                status_code=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return self.error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return self.error_response(
                message=f"Failed to process message: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MessageListView(BaseViewSet):
    """
    GET /api/v1/chat/conversations/{conversation_id}/messages - List messages in conversation
    
    Supports pagination and filtering by role.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = ChatPagination
    
    def get_conversation(self, conversation_id: UUID) -> Optional[Conversation]:
        """Get conversation and verify ownership"""
        try:
            return Conversation.objects.get(
                id=conversation_id,
                account=self.request.user,
                is_deleted=False
            )
        except Conversation.DoesNotExist:
            return None
    
    def list(self, request: Request, conversation_id: str) -> Response:
        """
        Get messages from a conversation.
        
        Query Parameters:
        - role: Filter by message role (user, assistant, system)
        - page: Page number
        - page_size: Items per page
        """
        try:
            conversation = self.get_conversation(UUID(conversation_id))
            
            if not conversation:
                return self.error_response(
                    message="Conversation not found or access denied",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Get messages
            queryset = Message.objects.filter(
                conversation=conversation,
                is_deleted=False
            ).order_by('created_at')
            
            # Filter by role
            role = request.query_params.get('role')
            if role in ['user', 'assistant', 'system']:
                queryset = queryset.filter(role=role)
            
            # Pagination
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = MessageDetailSerializer(page, many=True)
                return Response(
                    ResponseBuilder.paginated(
                        items=serializer.data,
                        page=self.paginator.page.number,
                        page_size=self.paginator.page.paginator.per_page,
                        total_items=self.paginator.page.paginator.count,
                        message="Messages retrieved successfully"
                    ),
                    status=status.HTTP_200_OK
                )
            
            serializer = MessageDetailSerializer(queryset, many=True)
            return self.success_response(
                data=serializer.data,
                message="Messages retrieved successfully"
            )
        except ValueError:
            return self.error_response(
                message="Invalid conversation ID format",
                status_code=status.HTTP_400_BAD_REQUEST
            )


class MessageDetailView(BaseViewSet):
    """
    GET /api/v1/chat/messages/{id} - Get message details
    """
    permission_classes = [IsAuthenticated]
    
    def retrieve(self, request: Request, message_id: str) -> Response:
        """Get message details"""
        try:
            message = Message.objects.get(
                id=UUID(message_id),
                is_deleted=False,
                conversation__account=request.user
            )
            
            serializer = MessageDetailSerializer(message)
            return self.success_response(
                data=serializer.data,
                message="Message retrieved successfully"
            )
        except Message.DoesNotExist:
            return self.error_response(
                message="Message not found or access denied",
                status_code=status.HTTP_404_NOT_FOUND
            )
        except ValueError:
            return self.error_response(
                message="Invalid message ID format",
                status_code=status.HTTP_400_BAD_REQUEST
            )


# ============================================================
# FEEDBACK VIEWS
# ============================================================

class MessageFeedbackView(BaseViewSet):
    """
    POST /api/v1/chat/messages/{id}/feedback - Rate AI response (upvote/downvote)
    GET /api/v1/chat/messages/{id}/feedback - Get feedback on message
    """
    permission_classes = [IsAuthenticated]
    
    def create(self, request: Request, message_id: str) -> Response:
        """
        Submit feedback on AI response.
        
        Request Body:
        {
            "rating": "upvote" or "downvote",
            "comment": "Optional feedback text"
        }
        """
        try:
            # Add message_id to request data
            data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
            data['message_id'] = message_id
            
            serializer = HumanFeedbackCreateSerializer(
                data=data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            feedback = serializer.save()
            
            logger.info(f"Feedback recorded by user {request.user.id} on message {message_id}")
            
            return self.success_response(
                data=HumanFeedbackSerializer(feedback).data,
                message="Feedback recorded successfully",
                status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Error recording feedback: {str(e)}", exc_info=True)
            return self.error_response(
                message=f"Failed to record feedback: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST
            )
    
    def retrieve(self, request: Request, message_id: str) -> Response:
        """Get all feedback on a message"""
        try:
            feedbacks = HumanFeedback.objects.filter(
                message_id=UUID(message_id),
                is_deleted=False,
                message__conversation__account=request.user
            )
            
            serializer = HumanFeedbackSerializer(feedbacks, many=True)
            return self.success_response(
                data=serializer.data,
                message="Feedback retrieved successfully"
            )
        except ValueError:
            return self.error_response(
                message="Invalid message ID format",
                status_code=status.HTTP_400_BAD_REQUEST
            )
