"""
This file is deprecated.
Group chat member management has been removed to simplify the API.
The system now focuses on RAG Chat (User ↔ AI) only.
"""


logger = logging.getLogger(__name__)


class ConversationMemberView(BaseViewSet):
    """
    Manage members in group conversations.
    
    Endpoints:
    - POST /api/v1/chat/conversations/{id}/members
    - GET /api/v1/chat/conversations/{id}/members
    - DELETE /api/v1/chat/conversations/{id}/members/{member_id}
    """
    permission_classes = [IsAuthenticated]
    
    def create(self, request: Request, conversation_id: str) -> Response:
        """
        Add member to group conversation.
        
        Request:
        {
            "account_id": "uuid",
            "role": "member" or "admin"
        }
        """
        try:
            # Verify conversation exists and is group chat
            try:
                conversation = Conversation.objects.get(
                    id=UUID(conversation_id),
                    is_deleted=False
                )
            except Conversation.DoesNotExist:
                return self.error_response(
                    message="Conversation not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            if conversation.type != 'group':
                return self.error_response(
                    message="Can only add members to group conversations",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Verify requester is admin
            try:
                member_record = ConversationMember.objects.get(
                    conversation=conversation,
                    account=request.user,
                    is_deleted=False
                )
                if member_record.role != 'admin':
                    return self.error_response(
                        message="Only admins can add members",
                        status_code=status.HTTP_403_FORBIDDEN
                    )
            except ConversationMember.DoesNotExist:
                return self.error_response(
                    message="You are not a member of this conversation",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            # Add member
            data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
            data['conversation_id'] = conversation_id
            
            serializer = ConversationMemberCreateSerializer(
                data=data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            member = serializer.save()
            
            logger.info(f"Member {data['account_id']} added to conversation {conversation_id}")
            
            return self.success_response(
                data=ConversationMemberSerializer(member).data,
                message="Member added successfully",
                status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Error adding member: {str(e)}", exc_info=True)
            return self.error_response(
                message=f"Failed to add member: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST
            )
    
    def list(self, request: Request, conversation_id: str) -> Response:
        """List all members in group conversation"""
        try:
            # Verify conversation exists
            try:
                conversation = Conversation.objects.get(
                    id=UUID(conversation_id),
                    is_deleted=False
                )
            except Conversation.DoesNotExist:
                return self.error_response(
                    message="Conversation not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Verify user is member (for both RAG and group)
            if conversation.type == 'group':
                try:
                    ConversationMember.objects.get(
                        conversation=conversation,
                        account=request.user,
                        is_deleted=False
                    )
                except ConversationMember.DoesNotExist:
                    return self.error_response(
                        message="You are not a member of this conversation",
                        status_code=status.HTTP_403_FORBIDDEN
                    )
            elif conversation.account != request.user:
                return self.error_response(
                    message="Access denied",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            # List members
            members = ConversationMember.objects.filter(
                conversation=conversation,
                is_deleted=False
            ).order_by('created_at')
            
            serializer = ConversationMemberSerializer(members, many=True)
            return self.success_response(
                data=serializer.data,
                message="Members retrieved successfully"
            )
        except Exception as e:
            logger.error(f"Error listing members: {str(e)}", exc_info=True)
            return self.error_response(
                message=f"Failed to list members: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request: Request, conversation_id: str, member_id: str) -> Response:
        """Remove member from group conversation (admins only)"""
        try:
            # Verify conversation exists
            try:
                conversation = Conversation.objects.get(
                    id=UUID(conversation_id),
                    is_deleted=False
                )
            except Conversation.DoesNotExist:
                return self.error_response(
                    message="Conversation not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Verify requester is admin
            try:
                requester_member = ConversationMember.objects.get(
                    conversation=conversation,
                    account=request.user,
                    is_deleted=False
                )
                if requester_member.role != 'admin':
                    return self.error_response(
                        message="Only admins can remove members",
                        status_code=status.HTTP_403_FORBIDDEN
                    )
            except ConversationMember.DoesNotExist:
                return self.error_response(
                    message="You are not a member of this conversation",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            # Get member to remove
            try:
                member_to_remove = ConversationMember.objects.get(
                    id=UUID(member_id),
                    conversation=conversation,
                    is_deleted=False
                )
            except ConversationMember.DoesNotExist:
                return self.error_response(
                    message="Member not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Soft delete member
            member_to_remove.is_deleted = True
            member_to_remove.save()
            
            logger.info(f"Member {member_to_remove.account.username} removed from conversation {conversation_id}")
            
            return self.success_response(
                data={},
                message="Member removed successfully",
                status_code=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            logger.error(f"Error removing member: {str(e)}", exc_info=True)
            return self.error_response(
                message=f"Failed to remove member: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST
            )
