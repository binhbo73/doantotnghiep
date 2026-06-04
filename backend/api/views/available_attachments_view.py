"""
Available Attachments View - API Endpoint for Chat Attachment Selection
========================================================================

Endpoint: GET /api/v1/chat/available-attachments

Returns all documents and folders that the current user can access for 
attaching to conversations, based on:
1. access_scope (personal/department/company)
2. backend permission codes
3. DocumentPermission entries
4. FolderPermission entries

Response format:
{
    "success": true,
    "data": {
        "documents": [...],
        "folders": [...],
        "pagination": {...}
    }
}
"""

from rest_framework.views import APIView
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from core.constants import PermissionCodes
from core.permissions.drf_permissions import IsAuthenticatedUser, user_has_permission
from api.serializers.base import ResponseBuilder
from api.serializers.chat_attachment_serializers import AvailableAttachmentsSerializer
from services.chat_attachment_service import ChatAttachmentService
import logging

logger = logging.getLogger(__name__)


class AvailableAttachmentsView(APIView):
    """
    API Endpoint: GET /api/v1/chat/available-attachments
    
    Returns documents and folders accessible by current user for chat attachments.
    
    Permissions checked:
    - access_scope: personal (owner only), department (same dept), company (all)
    - DocumentPermission table: explicit account/role permissions
    - FolderPermission table: explicit account/role permissions
    - chat_read permission before exposing selectable attachments
    """
    permission_classes = [IsAuthenticatedUser]
    
    def get(self, request: Request) -> Response:
        """
        Get available documents and folders for current user.
        
        Query Parameters: None
        
        Returns:
        {
            "success": true,
            "data": {
                "documents": [...accessible documents...],
                "folders": [...accessible folders...],
                "pagination": {
                    "total_documents": N,
                    "total_folders": M
                }
            }
        }
        """
        try:
            if not user_has_permission(request.user, PermissionCodes.CHAT_READ):
                return Response(
                    ResponseBuilder.error(
                        message=f"You need {PermissionCodes.CHAT_READ} permission",
                        status_code=status.HTTP_403_FORBIDDEN,
                    ),
                    status=status.HTTP_403_FORBIDDEN,
                )

            user_id = request.user.id
            logger.info(f"📎 Fetching available attachments for user: {user_id}")
            
            # Use Service layer for business logic
            service = ChatAttachmentService()
            attachments_data = service.get_accessible_attachments(user_id)
            
            # Serialize response
            serializer = AvailableAttachmentsSerializer(attachments_data)
            
            return Response(
                ResponseBuilder.success(
                    data=serializer.data,
                    message="Available attachments retrieved successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.error(f"Error getting available attachments: {str(e)}", exc_info=True)
            return Response(
                ResponseBuilder.error(
                    message=f"Failed to get available attachments: {str(e)}",
                    status_code=500
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
