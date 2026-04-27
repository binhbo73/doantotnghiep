"""
Chat WebSocket Consumer - Real-time bidirectional communication for chat.

Features:
1. Real-time message delivery
2. User presence/typing indicators
3. Conversation updates
4. Connection management

Usage:
- ws://localhost:8000/ws/chat/{conversation_id}/?token={auth_token}

Installation Required:
- pip install django-channels channels-redis
- Configure in settings.py:
  INSTALLED_APPS += ['daphne', 'channels']
  ASGI_APPLICATION = 'config.asgi.application'
  CHANNEL_LAYERS = {
      'default': {
          'BACKEND': 'channels_redis.core.RedisChannelLayer',
          'CONFIG': {"hosts": [('127.0.0.1', 6379)]},
      }
  }
"""
import json
import logging
from typing import Dict, Any, Optional
from uuid import UUID

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from apps.operations.models import Conversation, Message
from apps.users.models import Account
from repositories.conversation_repository import ConversationRepository
from repositories.message_repository import MessageRepository

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat.
    
    Connects to: ws://host/ws/chat/{conversation_id}/?token={auth_token}
    
    Message Types:
    - message: New message from user
    - typing: User is typing indicator
    - presence: User online/offline
    - history: Request chat history
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        # Get conversation ID and auth token from URL
        self.conversation_id = self.scope['url_route']['kwargs'].get('conversation_id')
        self.user = None
        
        try:
            # Authenticate user from JWT token in query string
            query_string = self.scope.get('query_string', b'').decode()
            token_str = self._extract_token_from_query(query_string)
            
            if not token_str:
                await self.close()
                logger.warning("WebSocket connection attempted without token")
                return
            
            # Validate token and get user
            self.user = await self._get_user_from_token(token_str)
            if not self.user:
                await self.close()
                logger.warning("Invalid token in WebSocket connection")
                return
            
            # Verify conversation ownership
            conversation = await self._get_conversation(self.conversation_id, self.user.id)
            if not conversation:
                await self.close()
                logger.warning(f"User {self.user.id} attempted to access unauthorized conversation {self.conversation_id}")
                return
            
            self.conversation = conversation
            self.room_group_name = f'chat_{self.conversation_id}'
            
            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            await self.accept()
            logger.info(f"User {self.user.id} connected to conversation {self.conversation_id}")
            
            # Notify others that user is online
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_presence',
                    'user_id': str(self.user.id),
                    'username': self.user.username,
                    'status': 'online',
                    'timestamp': timezone.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error in WebSocket connect: {str(e)}", exc_info=True)
            await self.close()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        try:
            if hasattr(self, 'room_group_name') and self.user:
                # Notify others that user is offline
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'user_presence',
                        'user_id': str(self.user.id),
                        'username': self.user.username,
                        'status': 'offline',
                        'timestamp': timezone.now().isoformat()
                    }
                )
                
                # Leave room group
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
                
                logger.info(f"User {self.user.id} disconnected from conversation {self.conversation_id}")
        except Exception as e:
            logger.error(f"Error in WebSocket disconnect: {str(e)}", exc_info=True)
    
    async def receive(self, text_data):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'message')
            
            if message_type == 'message':
                await self._handle_message(data)
            elif message_type == 'typing':
                await self._handle_typing(data)
            elif message_type == 'history':
                await self._handle_history_request(data)
            else:
                logger.warning(f"Unknown message type: {message_type}")
        
        except json.JSONDecodeError:
            await self.send(json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {str(e)}", exc_info=True)
            await self.send(json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    # ============================================================
    # MESSAGE HANDLERS
    # ============================================================
    
    async def _handle_message(self, data: Dict[str, Any]):
        """Handle incoming chat message"""
        content = data.get('content', '').strip()
        
        if not content:
            await self.send(json.dumps({
                'type': 'error',
                'message': 'Message content cannot be empty'
            }))
            return
        
        try:
            # Save user message to database
            user_message = await self._save_user_message(content)
            
            # Broadcast to group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_id': str(user_message.id),
                    'role': 'user',
                    'username': self.user.username,
                    'full_name': f"{self.user.first_name} {self.user.last_name}".strip(),
                    'content': content,
                    'created_at': user_message.created_at.isoformat(),
                    'status': 'sent'
                }
            )
            
            # For RAG chat: get AI response
            await self._get_ai_response(content)
            
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
            await self.send(json.dumps({
                'type': 'error',
                'message': f"Failed to process message: {str(e)}"
            }))
    
    async def _handle_typing(self, data: Dict[str, Any]):
        """Handle typing indicator"""
        is_typing = data.get('is_typing', False)
        
        # Broadcast typing status
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_typing',
                'user_id': str(self.user.id),
                'username': self.user.username,
                'is_typing': is_typing,
                'timestamp': timezone.now().isoformat()
            }
        )
    
    async def _handle_history_request(self, data: Dict[str, Any]):
        """Handle request for chat history"""
        limit = min(data.get('limit', 50), 100)
        offset = data.get('offset', 0)
        
        messages = await self._get_conversation_messages(limit, offset)
        
        await self.send(json.dumps({
            'type': 'history',
            'messages': messages,
            'total': len(messages)
        }))
    
    # ============================================================
    # GROUP MESSAGE HANDLERS (receive from channel layer)
    # ============================================================
    
    async def chat_message(self, event):
        """Receive chat_message from group"""
        await self.send(json.dumps(event))
    
    async def user_typing(self, event):
        """Receive user_typing from group"""
        await self.send(json.dumps(event))
    
    async def user_presence(self, event):
        """Receive user_presence from group"""
        await self.send(json.dumps(event))
    
    async def ai_response(self, event):
        """Receive AI response from group"""
        await self.send(json.dumps(event))
    
    # ============================================================
    # DATABASE OPERATIONS (sync_to_async)
    # ============================================================
    
    @database_sync_to_async
    def _get_user_from_token(self, token_str: str) -> Optional[Account]:
        """Validate JWT token and return user"""
        try:
            token = AccessToken(token_str)
            user_id = token['user_id']
            return Account.objects.get(id=user_id, is_active=True)
        except Exception as e:
            logger.warning(f"Token validation failed: {str(e)}")
            return None
    
    @database_sync_to_async
    def _get_conversation(self, conversation_id: str, user_id: UUID) -> Optional[Conversation]:
        """Get conversation and verify ownership"""
        try:
            conversation = Conversation.objects.get(
                id=UUID(conversation_id),
                account_id=user_id,  # Owner only
                is_deleted=False
            )
            return conversation
        except (Conversation.DoesNotExist, ValueError):
            return None
    
    @database_sync_to_async
    def _save_user_message(self, content: str) -> Message:
        """Save user message to database"""
        message = Message.objects.create(
            conversation_id=self.conversation.id,
            account=self.user,
            role='user',
            content=content
        )
        return message
    
    @database_sync_to_async
    def _get_conversation_messages(self, limit: int, offset: int):
        """Get conversation history"""
        messages = Message.objects.filter(
            conversation_id=self.conversation.id,
            is_deleted=False
        ).order_by('-created_at')[offset:offset + limit]
        
        result = []
        for msg in reversed(list(messages)):
            result.append({
                'id': str(msg.id),
                'role': msg.role,
                'username': msg.account.username if msg.account else 'AI',
                'content': msg.content,
                'created_at': msg.created_at.isoformat(),
            })
        return result
    
    async def _get_ai_response(self, content: str):
        """Get AI response asynchronously"""
        from services.chat_service import ChatService
        
        try:
            # Run in thread pool to avoid blocking
            loop = __import__('asyncio').get_event_loop()
            chat_service = ChatService()
            
            ai_response, bot_message = await loop.run_in_executor(
                None,
                lambda: chat_service.ask(
                    user_id=self.user.id,
                    query=content,
                    conversation_id=self.conversation.id
                )
            )
            
            # Broadcast AI response to group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'ai_response',
                    'message_id': str(bot_message.id),
                    'role': 'assistant',
                    'username': 'AI Assistant',
                    'content': ai_response,
                    'created_at': bot_message.created_at.isoformat(),
                    'citations': bot_message.citations,
                    'status': 'complete'
                }
            )
        except Exception as e:
            logger.error(f"Error getting AI response: {str(e)}", exc_info=True)
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'error',
                    'message': f"AI service error: {str(e)}"
                }
            )
    
    # ============================================================
    # UTILITY METHODS
    # ============================================================
    
    def _extract_token_from_query(self, query_string: str) -> Optional[str]:
        """Extract JWT token from query string"""
        for param in query_string.split('&'):
            if param.startswith('token='):
                return param.split('=', 1)[1]
        return None
