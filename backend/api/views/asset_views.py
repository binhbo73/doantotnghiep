"""
Asset Views - API Endpoints for Document Assets (OCR + VL Caption Pipeline)

Endpoints:
1. GET /api/v1/documents/{doc_id}/assets  - List assets
2. GET /api/v1/assets/{asset_id}           - Asset detail
3. GET /api/v1/assets/{asset_id}/image     - Original asset image
4. GET /api/v1/assets/{asset_id}/thumbnail - Thumbnail image
"""

import logging
import mimetypes
import os
from io import BytesIO

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import FileResponse, HttpResponse
from django.conf import settings

from core.permissions.drf_permissions import IsAuthenticatedUser
from core.utils.response_builder import ResponseBuilder
from core.exceptions import NotFoundError, PermissionDeniedError

logger = logging.getLogger(__name__)


class DocumentAssetsListView(APIView):
    """GET /api/v1/documents/{doc_id}/assets - List all assets of a document."""

    permission_classes = [IsAuthenticatedUser]

    def get(self, request, doc_id):
        try:
            from core.permissions import get_permission_manager
            perm_manager = get_permission_manager()
            if not perm_manager.check_document_access(request.user.id, doc_id, action='read'):
                raise PermissionDeniedError(f"No read permission on document {doc_id}")

            from apps.documents.models import DocumentAsset
            from api.serializers.document_serializers import DocumentAssetSerializer

            assets = DocumentAsset.objects.filter(
                document_id=doc_id, is_deleted=False
            ).order_by('page_number', 'paragraph_index')

            logger.info(f"[DocumentAssetsListView] Document {doc_id}: Found {assets.count()} assets (not deleted)")
            for asset in assets:
                logger.info(f"  - Asset {asset.id}: type={asset.asset_type}, page={asset.page_number}, sheet={asset.sheet_name}, anchor={asset.anchor_cell}, status={asset.processing_status}")

            serializer = DocumentAssetSerializer(assets, many=True)
            return Response(
                ResponseBuilder.success(data=serializer.data),
                status=status.HTTP_200_OK,
            )

        except PermissionDeniedError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=403),
                status=status.HTTP_403_FORBIDDEN,
            )
        except Exception as e:
            logger.error(f"Error listing assets: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to list assets", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DocumentAssetDetailView(APIView):
    """GET /api/v1/assets/{asset_id} - Get asset detail."""

    permission_classes = [IsAuthenticatedUser]

    def get(self, request, asset_id):
        try:
            from apps.documents.models import DocumentAsset
            from api.serializers.document_serializers import DocumentAssetSerializer
            from core.permissions import get_permission_manager

            asset = DocumentAsset.objects.get(id=asset_id, is_deleted=False)
            perm_manager = get_permission_manager()
            if not perm_manager.check_document_access(
                request.user.id, str(asset.document_id), action='read'
            ):
                raise PermissionDeniedError("No read permission on asset's document")

            serializer = DocumentAssetSerializer(asset)
            return Response(
                ResponseBuilder.success(data=serializer.data),
                status=status.HTTP_200_OK,
            )

        except DocumentAsset.DoesNotExist:
            return Response(
                ResponseBuilder.error(f"Asset {asset_id} not found", status_code=404),
                status=status.HTTP_404_NOT_FOUND,
            )
        except PermissionDeniedError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=403),
                status=status.HTTP_403_FORBIDDEN,
            )
        except Exception as e:
            logger.error(f"Error getting asset: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to get asset", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DocumentAssetImageView(APIView):
    """GET /api/v1/assets/{asset_id}/image - Get original asset image."""

    permission_classes = [IsAuthenticatedUser]

    def get(self, request, asset_id):
        try:
            from apps.documents.models import DocumentAsset
            from core.permissions import get_permission_manager

            try:
                asset = DocumentAsset.objects.get(id=asset_id, is_deleted=False)
            except DocumentAsset.DoesNotExist:
                # SELF-HEALING: If asset not found, it might be stale (deleted and recreated).
                # Try to find a replacement by matching sheet_name and anchor_cell of the deleted asset.
                stale_asset = DocumentAsset.objects.filter(id=asset_id).first()
                if not stale_asset:
                    raise DocumentAsset.DoesNotExist()
                
                # Try to find a new asset in the same location
                asset = DocumentAsset.objects.filter(
                    document_id=stale_asset.document_id,
                    sheet_name=stale_asset.sheet_name,
                    anchor_cell=stale_asset.anchor_cell,
                    is_deleted=False
                ).first()
                
                if not asset:
                    raise DocumentAsset.DoesNotExist()
                
                logger.info(f"[DocumentAssetImageView] HEALED: Stale ID {asset_id} replaced by new ID {asset.id} at {asset.sheet_name} {asset.anchor_cell}")

            perm_manager = get_permission_manager()
            if not perm_manager.check_document_access(
                request.user.id, str(asset.document_id), action='read'
            ):
                raise PermissionDeniedError("No read permission")

            image_full_path = os.path.join(settings.MEDIA_ROOT, asset.image_path)
            logger.info(f"[DocumentAssetImageView] asset_id={asset.id}, image_path={asset.image_path}, full_path={image_full_path}")
            exists = os.path.exists(image_full_path)
            logger.info(f"[DocumentAssetImageView] image exists={exists}")
            if not exists:
                raise NotFoundError(f"Image file not found: {asset.image_path}")

            content_type = mimetypes.guess_type(image_full_path)[0] or f'image/{asset.image_format or "png"}'
            return FileResponse(
                open(image_full_path, 'rb'),
                content_type=content_type,
                as_attachment=False,
                filename=os.path.basename(image_full_path),
            )

        except DocumentAsset.DoesNotExist:
            return Response(
                ResponseBuilder.error(f"Asset {asset_id} not found", status_code=404),
                status=status.HTTP_404_NOT_FOUND,
            )
        except PermissionDeniedError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=403),
                status=status.HTTP_403_FORBIDDEN,
            )
        except NotFoundError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error serving asset image: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to get asset image", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DocumentAssetThumbnailView(APIView):
    """GET /api/v1/assets/{asset_id}/thumbnail - Get thumbnail image (300px max)."""

    permission_classes = [IsAuthenticatedUser]

    def get(self, request, asset_id):
        try:
            from PIL import Image
            from apps.documents.models import DocumentAsset
            from core.permissions import get_permission_manager

            try:
                asset = DocumentAsset.objects.get(id=asset_id, is_deleted=False)
            except DocumentAsset.DoesNotExist:
                # SELF-HEALING: Same logic as ImageView
                stale_asset = DocumentAsset.objects.filter(id=asset_id).first()
                if not stale_asset:
                    raise DocumentAsset.DoesNotExist()
                
                asset = DocumentAsset.objects.filter(
                    document_id=stale_asset.document_id,
                    sheet_name=stale_asset.sheet_name,
                    anchor_cell=stale_asset.anchor_cell,
                    is_deleted=False
                ).first()
                
                if not asset:
                    raise DocumentAsset.DoesNotExist()

            perm_manager = get_permission_manager()
            if not perm_manager.check_document_access(
                request.user.id, str(asset.document_id), action='read'
            ):
                raise PermissionDeniedError("No read permission")

            image_full_path = os.path.join(settings.MEDIA_ROOT, asset.image_path)
            logger.info(f"[DocumentAssetThumbnailView] asset_id={asset.id}, image_path={asset.image_path}, full_path={image_full_path}")
            exists = os.path.exists(image_full_path)
            logger.info(f"[DocumentAssetThumbnailView] image exists={exists}")
            if not exists:
                raise NotFoundError(f"Image file not found: {asset.image_path}")

            img = Image.open(image_full_path)
            img.thumbnail((300, 300), Image.LANCZOS)

            output = BytesIO()
            fmt = img.format or 'PNG'
            img.save(output, format=fmt)
            output.seek(0)

            content_type = f'image/{fmt.lower()}'
            return HttpResponse(output.read(), content_type=content_type)

        except DocumentAsset.DoesNotExist:
            return Response(
                ResponseBuilder.error(f"Asset {asset_id} not found", status_code=404),
                status=status.HTTP_404_NOT_FOUND,
            )
        except PermissionDeniedError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=403),
                status=status.HTTP_403_FORBIDDEN,
            )
        except NotFoundError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to generate thumbnail", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
