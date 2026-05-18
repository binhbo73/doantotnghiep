"""
DocumentUploadService
=====================
Handles the full upload pipeline:
  1. Validate file (size, type)
  2. Determine scope/department/folder correctly
  3. Save file to disk
  4. Create Document record (status='pending')
  5. Parse text (PDF/DOCX/TXT/MD)
  6. Chunk text → DocumentChunk rows
  7. Embed each chunk → Qdrant + DocumentEmbedding rows
  8. Update Document status → 'completed' or 'failed'
  9. Audit log

SCOPING RULES (quan trọng):
----------------------------
Case A: folder_id != None AND folder.department != None
    → doc.folder = folder, doc.department = folder.department, doc.access_scope = folder.access_scope

Case B: folder_id != None AND folder.department == None   (folder thuộc công ty)
    → doc.folder = folder, doc.department = None, doc.access_scope = 'company'

Case C: folder_id == None AND department_id != None       (chỉ thuộc phòng ban, không có folder)
    → doc.folder = None, doc.department = department_id, doc.access_scope = 'department'

Case D: folder_id == None AND department_id == None       (toàn công ty)
    → doc.folder = None, doc.department = None, doc.access_scope = 'company'

Người dùng được phép truyền access_scope='department' cùng department_id để override Case D về Case C.
"""

import logging
import os
import hashlib
import uuid
from typing import Optional, List
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from django.core.files.uploadedfile import UploadedFile
from django.apps import apps

from apps.documents.models import Document
from services.ai.embedding_client import EmbeddingClient
from core.exceptions import (
    ValidationError,
    FileSizeExceededError,
    DocumentProcessingError,
)
from repositories.document_repository import DocumentRepository
from repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class DocumentUploadService:
    """
    Service chuyên biệt cho việc upload tài liệu nội bộ.

    Flow:
      upload() → _validate_file() → _resolve_scope() → _save_file()
              → _create_document() → _process_document()
              → [parse → chunk → embed → update_status]
    """

    MAX_FILE_SIZE_MB = 100
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
        'text/plain',
        'text/markdown',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
        'application/vnd.ms-excel',  # .xls
    }
    UPLOAD_ROOT = 'uploads'

    def __init__(self):
        self.document_repo = DocumentRepository()
        self.user_repo = UserRepository()

    # =========================================================================
    # PUBLIC ENTRY POINT
    # =========================================================================

    def upload(
        self,
        file: UploadedFile,
        user_id: int,
        folder_id: Optional[str] = None,
        department_id: Optional[str] = None,
        access_scope: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        run_processing: bool = True,
    ) -> 'Document':
        """
        Upload tài liệu nội bộ và trigger indexing pipeline.

        Args:
            file            : Django UploadedFile (multipart)
            user_id         : ID tài khoản upload
            folder_id       : UUID folder (optional). Nếu có → scope tự động theo folder.
            department_id   : UUID phòng ban (optional). Dùng khi không có folder.
            access_scope    : 'personal' | 'department' | 'company'. Override tự động nếu cần.
            description     : Mô tả tài liệu
            tags            : Danh sách tên tag
            run_processing  : Nếu True → parse + chunk + embed ngay (synchronous).
                              Nếu False → chỉ lưu file + record, xử lý sau.

        Returns:
            Document instance (status='completed' hoặc 'failed')

        Raises:
            FileSizeExceededError, ValidationError, DocumentProcessingError
        """
        # 1. Validate file
        file_content, file_mime = self._validate_file(file)

        # 2. Resolve scope (folder / department / company)
        resolved = self._resolve_scope(folder_id, department_id, access_scope)

        # 3. Save file bytes to disk
        storage_path, hashed_name = self._save_file(file_content, file.name, user_id)

        # 4. Create Document record (status='pending')
        with transaction.atomic():
            document = self._create_document(
                file=file,
                file_content=file_content,
                file_mime=file_mime,
                hashed_name=hashed_name,
                storage_path=storage_path,
                user_id=user_id,
                resolved=resolved,
                description=description,
                tags=tags or [],
            )

        logger.info(
            f"[Upload] Document {document.id} created – "
            f"folder={resolved['folder_id']}, dept={resolved['department_id']}, "
            f"scope={resolved['access_scope']}"
        )

        # 5. Process (parse → chunk → embed)
        if run_processing:
            import threading
            from django.db import connection

            def background_process(doc, path):
                try:
                    self._process_document(doc, path)
                finally:
                    # Đảm bảo đóng connection trong thread riêng để tránh leak hoặc lỗi
                    connection.close()

            thread = threading.Thread(
                target=background_process,
                args=(document, storage_path),
                name=f"DocProcess-{document.id}"
            )
            thread.daemon = True  # Luôn chạy ngầm
            thread.start()
            logger.info(f"[Upload] Started background processing for {document.id}")

        return document

    # =========================================================================
    # STEP 1 – Validate file
    # =========================================================================

    def _validate_file(self, file: UploadedFile):
        """Kiểm tra kích thước và MIME type, đọc nội dung 1 lần."""
        # Validate size
        size_mb = file.size / (1024 * 1024)
        if size_mb > self.MAX_FILE_SIZE_MB:
            raise FileSizeExceededError(
                f"File '{file.name}' ({size_mb:.1f}MB) vượt giới hạn {self.MAX_FILE_SIZE_MB}MB"
            )

        # Detect MIME type from upload or filename extension
        mime = file.content_type or ''
        if not mime or mime == 'application/octet-stream':
            import mimetypes
            guessed_mime, _ = mimetypes.guess_type(file.name)
            mime = guessed_mime or mime or 'application/octet-stream'

        if mime not in self.ALLOWED_MIME_TYPES:
            _, ext = os.path.splitext(file.name.lower())
            extension_map = {
                '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                '.xls': 'application/vnd.ms-excel',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.doc': 'application/msword',
                '.txt': 'text/plain',
                '.md': 'text/markdown',
                '.pdf': 'application/pdf',
            }
            mime = extension_map.get(ext, mime)

        if mime not in self.ALLOWED_MIME_TYPES:
            raise ValidationError(
                f"Loại file '{mime}' không được hỗ trợ. "
                f"Chấp nhận: {', '.join(sorted(self.ALLOWED_MIME_TYPES))}"
            )

        # Read content once
        content = file.read()
        file.seek(0)
        return content, mime

    def _normalize_file_type(self, file_name: str, mime_type: str) -> str:
        """Normalize file type to extension-based labels for UI and metadata."""
        ext = os.path.splitext(file_name)[1].lower()
        if ext == '.md':
            return 'markdown'
        if ext == '.txt':
            return 'txt'
        if ext == '.docx':
            return 'docx'
        if ext == '.doc':
            return 'doc'
        if ext == '.pdf':
            return 'pdf'
        if ext == '.xlsx':
            return 'xlsx'
        if ext == '.xls':
            return 'xls'

        mime_map = {
            'application/pdf': 'pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'application/msword': 'doc',
            'text/plain': 'txt',
            'text/markdown': 'markdown',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
            'application/vnd.ms-excel': 'xls',
        }
        return mime_map.get(mime_type, ext.lstrip('.') or 'bin')

    # =========================================================================
    # STEP 2 – Resolve scope
    # =========================================================================

    def _resolve_scope(
        self,
        folder_id: Optional[str],
        department_id: Optional[str],
        access_scope: Optional[str],
    ) -> dict:
        """
        Xác định (folder_id, department_id, access_scope) theo logic nghiệp vụ.
        
        VALIDATION RULES (Direction 2 - linh hoạt theo document):
        - Nếu folder.access_scope = personal → document access_scope PHẢI = personal
        - Nếu folder.access_scope = department → document access_scope chỉ có thể là department/personal
        - Nếu folder.access_scope = company → document có thể là company/department/personal
        - department scope luôn cần department_id hiệu lực

        CASE A: Có folder personal
            → chỉ cho phép personal
        CASE B: Có folder department
            → department: kế thừa department của folder
            → personal: department = None
            → company: reject
        CASE C: Có folder company
            → tôn trọng access_scope request của document
        CASE D: Không có folder
            → giữ logic theo access_scope + department_id request
        """
        Folder = apps.get_model('documents', 'Folder')

        # Scope mặc định theo request đầu vào
        requested_scope = access_scope or ('department' if department_id else 'company')

        if folder_id:
            # Validate folder tồn tại
            try:
                folder = Folder.objects.select_related('department').get(
                    pk=folder_id, is_deleted=False
                )
            except Folder.DoesNotExist:
                raise ValidationError(f"Folder {folder_id} không tồn tại")

            # CASE A: folder personal -> chỉ personal
            if folder.access_scope == 'personal':
                if requested_scope != 'personal':
                    raise ValidationError(
                        f"Document trong personal folder phải có access_scope='personal', "
                        f"không được '{requested_scope}'"
                    )

                return {
                    'folder_id': str(folder.id),
                    'department_id': None,
                    'access_scope': 'personal',
                }

            # CASE B: folder department -> company bị chặn
            if folder.access_scope == 'department':
                if requested_scope == 'company':
                    raise ValidationError(
                        "Tài liệu trong department folder không thể là company-wide"
                    )

                # personal doc trong department folder -> vẫn personal
                if requested_scope == 'personal':
                    return {
                        'folder_id': str(folder.id),
                        'department_id': None,
                        'access_scope': 'personal',
                    }

                # department doc trong department folder -> kế thừa department của folder
                return {
                    'folder_id': str(folder.id),
                    'department_id': str(folder.department_id) if folder.department_id else None,
                    'access_scope': 'department',
                }

            # CASE C: folder company -> document scope linh hoạt theo request
            if requested_scope == 'department':
                if not department_id:
                    raise ValidationError("Tài liệu department-scoped phải có department_id")
                return {
                    'folder_id': str(folder.id),
                    'department_id': str(department_id),
                    'access_scope': 'department',
                }

            if requested_scope == 'personal':
                return {
                    'folder_id': str(folder.id),
                    'department_id': None,
                    'access_scope': 'personal',
                }

            return {
                'folder_id': str(folder.id),
                'department_id': None,
                'access_scope': 'company',
            }
        else:
            # CASE D: không có folder -> theo request
            if requested_scope == 'department':
                if not department_id:
                    raise ValidationError("Tài liệu department-scoped phải có department_id")
                return {
                    'folder_id': None,
                    'department_id': str(department_id),
                    'access_scope': 'department',
                }

            if requested_scope == 'personal':
                return {
                    'folder_id': None,
                    'department_id': None,
                    'access_scope': 'personal',
                }

            return {
                'folder_id': None,
                'department_id': None,
                'access_scope': 'company',
            }

    # =========================================================================
    # STEP 3 – Save file to disk
    # =========================================================================

    def _save_file(self, content: bytes, original_name: str, user_id: int):
        """Lưu nội dung file vào uploads/{user_id}/{md5}{ext}."""
        import os as _os
        file_hash = hashlib.md5(content).hexdigest()
        ext = _os.path.splitext(original_name)[1].lower()
        hashed_name = f"{file_hash}{ext}"

        storage_dir = _os.path.join(self.UPLOAD_ROOT, str(user_id))
        _os.makedirs(storage_dir, exist_ok=True)

        storage_path = _os.path.join(storage_dir, hashed_name)
        if not _os.path.exists(storage_path):
            with open(storage_path, 'wb') as f:
                f.write(content)
            logger.debug(f"File saved: {storage_path}")
        else:
            logger.debug(f"File already exists (same hash): {storage_path}")

        return storage_path, hashed_name

    # =========================================================================
    # STEP 4 – Create Document record
    # =========================================================================

    def _create_document(
        self,
        file: UploadedFile,
        file_content: bytes,
        file_mime: str,
        hashed_name: str,
        storage_path: str,
        user_id: int,
        resolved: dict,
        description: Optional[str],
        tags: List[str],
    ) -> 'Document':
        """Tạo Document record trong PostgreSQL với status='pending'."""
        import os as _os
        ext = _os.path.splitext(file.name)[1].lstrip('.').lower() or 'bin'

        normalized_type = self._normalize_file_type(file.name, file_mime)

        document = self.document_repo.create(
            original_name=file.name,
            filename=hashed_name,
            storage_path=storage_path,
            file_type=normalized_type,
            file_size=len(file_content),
            mime_type=file_mime,
            uploader_id=user_id,
            department_id=resolved['department_id'],
            folder_id=resolved['folder_id'],
            access_scope=resolved['access_scope'],
            embedding_model=getattr(settings, 'EMBEDDING_MODEL', 'bge-m3'),
            status='pending',
            metadata={
                'description': description or '',
                'original_ext': ext,
                'embedding_model': getattr(settings, 'EMBEDDING_MODEL', 'bge-m3'),
            },
        )

        # Thêm tags nếu có
        if tags:
            self._add_tags(document, [t.strip() for t in tags if t.strip()])

        return document

    def _add_tags(self, document, tag_names: List[str]):
        """Tạo hoặc lấy Tag và gắn vào document."""
        Tag = apps.get_model('documents', 'Tag')
        for name in tag_names:
            tag, _ = Tag.objects.get_or_create(
                name=name.lower(),
                defaults={'name': name},
            )
            document.tags.add(tag)

    # =========================================================================
    # STEP 5 – Full processing pipeline: parse → chunk → embed
    # =========================================================================

    def _process_document(self, document, storage_path: str):
        """Simplified processing: delegate to DocumentIngestPipeline.

        The pipeline will perform parse → chunk → embed → persist and
        return a PipelineContext we can use to update the Document row.
        """
        import time
        start_time = time.time()

        # Mark processing
        self._update_status(document, 'processing')

        try:
            from services.pipeline.orchestrator import DocumentIngestPipeline

            pipeline = DocumentIngestPipeline()
            metadata = {
                'source_name': document.original_name,
                'file_type': document.file_type,
                'uploader_id': str(document.uploader_id or ''),
                'embedding_model': getattr(settings, 'EMBEDDING_MODEL', document.embedding_model or ''),
            }

            success, context = pipeline.execute(
                file_path=storage_path,
                user_id=str(document.uploader_id or ''),
                document_id=str(document.id),
                metadata=metadata,
            )

            # Update document based on pipeline result
            if success:
                try:
                    document.refresh_from_db()
                    document.status = 'completed'
                    document.metadata = document.metadata or {}
                    for key, value in context.metadata.items():
                        if isinstance(value, (str, int, float, bool, list, dict)) or value is None:
                            document.metadata[key] = value
                    document.metadata.update({
                        'chunk_count': len(context.chunks),
                        'processed_at': time.time(),
                        'pipeline_metrics_ms': context.total_time_ms(),
                    })
                    document.save(update_fields=['status', 'metadata'])
                    logger.info(f"[Upload] Document {document.id} processed by pipeline: {len(context.chunks)} chunks")
                except Exception as e:
                    logger.error(f"[Upload] Failed to update document after pipeline success: {e}")
            else:
                err_msg = '; '.join([e.get('error', '') for e in context.errors]) or 'Unknown pipeline error'
                logger.error(f"[Upload] Pipeline failed for document {document.id}: {err_msg}")
                self._update_status(document, 'failed', error=err_msg)

        except Exception as e:
            logger.exception(f"[Upload] Pipeline execution error for document {document.id}: {e}")
            self._update_status(document, 'failed', error=str(e))


    # =========================================================================
    # HELPERS
    # =========================================================================

    def _update_status(self, document, status: str, error: str = None):
        """Cập nhật trạng thái xử lý của document."""
        document.status = status
        if error:
            document.metadata['processing_error'] = error
        document.save(update_fields=['status', 'metadata'])
