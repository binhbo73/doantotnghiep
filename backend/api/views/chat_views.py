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
    ConversationAttachmentSerializer,
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


class ConversationAttachmentView(BaseViewSet):
    """
    GET /api/v1/chat/conversations/{id}/attachments - List attachments
    POST /api/v1/chat/conversations/{id}/attachments - Attach documents/folders
    DELETE /api/v1/chat/conversations/{id}/attachments - Detach documents/folders
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, conversation_id: UUID) -> Optional[Conversation]:
        try:
            return Conversation.objects.get(
                id=conversation_id,
                account=self.request.user,
                is_deleted=False,
            )
        except Conversation.DoesNotExist:
            return None

    def _restore_or_create_document_attachment(self, conversation, document):
        attachment, created = ConversationAttachedDocument.objects.get_or_create(
            conversation=conversation,
            document=document,
        )
        if not created and attachment.is_deleted:
            attachment.is_deleted = False
            attachment.deleted_at = None
            attachment.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])

    def _restore_or_create_folder_attachment(self, conversation, folder):
        attachment, created = ConversationAttachedFolder.objects.get_or_create(
            conversation=conversation,
            folder=folder,
        )
        if not created and attachment.is_deleted:
            attachment.is_deleted = False
            attachment.deleted_at = None
            attachment.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])

    def _soft_delete_document_attachment(self, conversation, document_id):
        ConversationAttachedDocument.objects.filter(
            conversation=conversation,
            document_id=document_id,
            is_deleted=False,
        ).update(is_deleted=True, deleted_at=timezone.now())

    def _soft_delete_folder_attachment(self, conversation, folder_id):
        ConversationAttachedFolder.objects.filter(
            conversation=conversation,
            folder_id=folder_id,
            is_deleted=False,
        ).update(is_deleted=True, deleted_at=timezone.now())

    def retrieve(self, request: Request, conversation_id: str) -> Response:
        try:
            conversation = self.get_object(UUID(conversation_id))
            if not conversation:
                return self.error_response(
                    message="Conversation not found or access denied",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            serializer = ConversationDetailSerializer(conversation)
            return self.success_response(
                data={
                    'conversation_id': str(conversation.id),
                    'attached_documents': serializer.data['attached_documents'],
                    'attached_folders': serializer.data['attached_folders'],
                },
                message="Conversation attachments retrieved successfully",
            )
        except ValueError:
            return self.error_response(
                message="Invalid conversation ID format",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    def create(self, request: Request, conversation_id: str) -> Response:
        try:
            conversation = self.get_object(UUID(conversation_id))
            if not conversation:
                return self.error_response(
                    message="Conversation not found or access denied",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            serializer = ConversationAttachmentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            for document_id in serializer.validated_data.get('document_ids', []):
                try:
                    document = Document.objects.get(id=document_id, is_deleted=False)
                except Document.DoesNotExist:
                    continue
                self._restore_or_create_document_attachment(conversation, document)

            for folder_id in serializer.validated_data.get('folder_ids', []):
                try:
                    folder = Folder.objects.get(id=folder_id, is_deleted=False)
                except Folder.DoesNotExist:
                    continue
                self._restore_or_create_folder_attachment(conversation, folder)

            conversation.refresh_from_db()
            return self.success_response(
                data=ConversationDetailSerializer(conversation).data,
                message="Conversation attachments updated successfully",
                status_code=status.HTTP_200_OK,
            )
        except ValueError:
            return self.error_response(
                message="Invalid conversation ID format",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Error updating conversation attachments: {str(e)}", exc_info=True)
            return self.error_response(
                message=f"Failed to update conversation attachments: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request: Request, conversation_id: str) -> Response:
        try:
            conversation = self.get_object(UUID(conversation_id))
            if not conversation:
                return self.error_response(
                    message="Conversation not found or access denied",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            serializer = ConversationAttachmentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            for document_id in serializer.validated_data.get('document_ids', []):
                self._soft_delete_document_attachment(conversation, document_id)

            for folder_id in serializer.validated_data.get('folder_ids', []):
                self._soft_delete_folder_attachment(conversation, folder_id)

            conversation.refresh_from_db()
            return self.success_response(
                data=ConversationDetailSerializer(conversation).data,
                message="Conversation attachments removed successfully",
                status_code=status.HTTP_200_OK,
            )
        except ValueError:
            return self.error_response(
                message="Invalid conversation ID format",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Error removing conversation attachments: {str(e)}", exc_info=True)
            return self.error_response(
                message=f"Failed to remove conversation attachments: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST,
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
    POST /api/v1/chat/messages/{id}/feedback - Rate AI response (1-5 stars)
    GET /api/v1/chat/messages/{id}/feedback - Get feedback on message
    DELETE /api/v1/chat/messages/{id}/feedback - Delete own feedback
    
    Features:
    - Only allow feedback on assistant messages
    - Verify message belongs to user's conversation
    - Soft-delete recovery for deleted feedback
    - Audit logging for compliance
    - Unique constraint: one feedback per user per message
    """
    permission_classes = [IsAuthenticated]
    
    def create(self, request: Request, message_id: str) -> Response:
        """
        Submit feedback on AI response.
        
        Request Body:
        {
            "rating": "1" to "5",
            "comment": "Optional feedback text (max 1000 chars)"
        }
        
        Responses:
        - 201: Feedback created
        - 200: Feedback updated (if already had feedback)
        - 400: Invalid input or validation error
        - 401: Unauthorized
        - 404: Message not found or no permission
        """
        try:
            message_id_uuid = UUID(message_id)
        except ValueError:
            return self.error_response(
                message="Invalid message ID format",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
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
            
            # Get action from context
            feedback_action = self.context_data.get('feedback_action', 'SUBMIT') if hasattr(self, 'context_data') else 'SUBMIT'
            created = serializer.context.get('feedback_created', True)
            
            # Log to audit trail
            try:
                from apps.operations.models import AuditLog
                AuditLog.log_action(
                    account=request.user,
                    action='FEEDBACK',
                    description=f"{'Created' if created else 'Updated'} feedback ({feedback.rating}) on message {message_id}",
                    resource_id=message_id_uuid,
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
            except Exception as audit_error:
                logger.warning(f"Failed to log audit: {audit_error}")
            
            logger.info(
                f"Feedback {'created' if created else 'updated'} by user {request.user.id} "
                f"on message {message_id}: {feedback.rating}"
            )
            
            return self.success_response(
                data=HumanFeedbackSerializer(feedback).data,
                message=f"Feedback {'recorded' if created else 'updated'} successfully",
                status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK
            )
        
        except serializers.ValidationError as e:
            error_detail = e.detail
            if isinstance(error_detail, dict):
                error_msg = str(list(error_detail.values())[0][0]) if error_detail else "Validation error"
            else:
                error_msg = str(error_detail[0]) if isinstance(error_detail, list) else str(error_detail)
            
            return self.error_response(
                message=error_msg,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error recording feedback: {str(e)}", exc_info=True)
            return self.error_response(
                message=f"Failed to record feedback: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST
            )
    
    def retrieve(self, request: Request, message_id: str) -> Response:
        """
        Get all feedback on a message.
        
        Only returns feedback for messages in user's conversations.
        Only shows non-deleted feedback.
        
        Query Parameters:
        - rating: Filter by rating (1-5 stars) - optional
        """
        try:
            message_id_uuid = UUID(message_id)
        except ValueError:
            return self.error_response(
                message="Invalid message ID format",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Verify message exists and belongs to user
            message = Message.objects.get(
                id=message_id_uuid,
                is_deleted=False,
                conversation__account=request.user
            )
            
            # Get feedbacks on this message
            feedbacks = HumanFeedback.objects.filter(
                message=message,
                is_deleted=False
            ).select_related('account')
            
            # Optional: filter by rating
            rating_filter = request.query_params.get('rating')
            if rating_filter in ['1', '2', '3', '4', '5']:
                feedbacks = feedbacks.filter(rating=rating_filter)
            
            # Serialize and return
            serializer = HumanFeedbackSerializer(feedbacks, many=True)
            
            # Add summary stats
            total_count = feedbacks.count()
            counts = {}
            total_score = 0
            for i in range(1, 6):
                c = feedbacks.filter(rating=str(i)).count()
                counts[f'star_{i}'] = c
                total_score += (c * i)
            
            stats = {
                'total': total_count,
                'average_rating': round(total_score / total_count, 1) if total_count > 0 else 0,
                'counts': counts
            }
            
            return self.success_response(
                data={
                    'message_id': str(message_id_uuid),
                    'stats': stats,
                    'feedbacks': serializer.data
                },
                message="Feedback retrieved successfully"
            )
        
        except Message.DoesNotExist:
            return self.error_response(
                message="Message not found or you don't have permission to view feedback",
                status_code=status.HTTP_404_NOT_FOUND
            )
    
    def destroy(self, request: Request, message_id: str) -> Response:
        """
        Delete own feedback on a message (soft delete).
        
        Can only delete feedback that user created.
        Performs soft delete for audit trail.
        """
        try:
            message_id_uuid = UUID(message_id)
        except ValueError:
            return self.error_response(
                message="Invalid message ID format",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Verify message exists and belongs to user
            message = Message.objects.get(
                id=message_id_uuid,
                is_deleted=False,
                conversation__account=request.user
            )
            
            # Get user's feedback on this message
            feedback = HumanFeedback.objects.get(
                message=message,
                account=request.user,
                is_deleted=False
            )
            
            # Soft delete
            feedback.is_deleted = True
            feedback.deleted_at = timezone.now()
            feedback.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
            
            # Log audit
            try:
                from apps.operations.models import AuditLog
                AuditLog.log_action(
                    account=request.user,
                    action='DELETE',
                    description=f"Deleted feedback on message {message_id}",
                    resource_id=message_id_uuid,
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
            except Exception as audit_error:
                logger.warning(f"Failed to log audit: {audit_error}")
            
            logger.info(f"Feedback deleted by user {request.user.id} on message {message_id}")
            
            return self.success_response(
                message="Feedback deleted successfully",
                status_code=status.HTTP_204_NO_CONTENT
            )
        
        except HumanFeedback.DoesNotExist:
            return self.error_response(
                message="You haven't provided feedback on this message",
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Message.DoesNotExist:
            return self.error_response(
                message="Message not found or you don't have permission",
                status_code=status.HTTP_404_NOT_FOUND
            )
    
    @staticmethod
    def get_client_ip(request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
