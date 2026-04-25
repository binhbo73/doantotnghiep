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
from django.utils import timezone
from django.core.files.uploadedfile import UploadedFile
from django.apps import apps

from apps.documents.models import Document
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

        # Detect MIME type
        mime = file.content_type or ''
        if not mime:
            import mimetypes
            mime, _ = mimetypes.guess_type(file.name)
            mime = mime or 'application/octet-stream'

        if mime not in self.ALLOWED_MIME_TYPES:
            raise ValidationError(
                f"Loại file '{mime}' không được hỗ trợ. "
                f"Chấp nhận: {', '.join(sorted(self.ALLOWED_MIME_TYPES))}"
            )

        # Read content once
        content = file.read()
        file.seek(0)
        return content, mime

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

        CASE A: Có folder thuộc phòng ban
            → scope = folder.access_scope, department = folder.department
        CASE B: Có folder nhưng folder thuộc công ty (không có dept)
            → scope = 'company', department = None
        CASE C: Không có folder, có phòng ban
            → scope = 'department', department = department_id
        CASE D: Không có folder, không có phòng ban
            → scope = 'company', department = None
        """
        Folder = apps.get_model('documents', 'Folder')

        if folder_id:
            # Validate folder tồn tại
            try:
                folder = Folder.objects.select_related('department').get(
                    pk=folder_id, is_deleted=False
                )
            except Folder.DoesNotExist:
                raise ValidationError(f"Folder {folder_id} không tồn tại")

            if folder.department_id:
                # CASE A: folder thuộc phòng ban
                return {
                    'folder_id': str(folder.id),
                    'department_id': str(folder.department_id),
                    'access_scope': folder.access_scope,  # kế thừa từ folder
                }
            else:
                # CASE B: folder thuộc công ty (không có dept)
                return {
                    'folder_id': str(folder.id),
                    'department_id': None,
                    'access_scope': 'company',
                }
        else:
            if department_id:
                # CASE C: chỉ thuộc phòng ban, không có folder
                return {
                    'folder_id': None,
                    'department_id': str(department_id),
                    'access_scope': access_scope or 'department',
                }
            else:
                # CASE D: toàn công ty
                return {
                    'folder_id': None,
                    'department_id': None,
                    'access_scope': access_scope or 'company',
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

        document = self.document_repo.create(
            original_name=file.name,
            filename=hashed_name,
            storage_path=storage_path,
            file_type=file_mime,
            file_size=len(file_content),
            mime_type=file_mime,
            uploader_id=user_id,
            department_id=resolved['department_id'],
            folder_id=resolved['folder_id'],
            access_scope=resolved['access_scope'],
            status='pending',
            metadata={
                'description': description or '',
                'original_ext': ext,
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
        """
        Pipeline hoàn chỉnh:
          Parse text → Chunk + Embed (via DocumentChunker)
        Cập nhật document.status = 'completed' | 'failed'.
        """
        doc_id = str(document.id)

        # Đánh dấu đang xử lý
        self._update_status(document, 'processing')

        try:
            # ── 5a. Parse text ────────────────────────────────────────────────
            from services.document.parser import DocumentParser
            parser = DocumentParser()
            try:
                # Pass the mime type stored in DB because storage_path might lack extension
                text, parse_meta = parser.parse_file(storage_path, file_type=document.file_type)
            except DocumentProcessingError as e:
                logger.error(f"[Upload] Parse failed for {doc_id}: {e}")
                self._update_status(document, 'failed', error=str(e))
                return

            if not text or not text.strip():
                logger.warning(f"[Upload] Empty text after parsing {doc_id}")
                self._update_status(document, 'failed', error='Không trích xuất được nội dung')
                return

            # ── 5b. Khởi tạo AI clients ──────────────────────────────────────
            try:
                from services.ai.llama_client import LlamaClient
                from services.ai.qdrant_client import QdrantClient
                llama = LlamaClient()
                qdrant = QdrantClient()
            except Exception as e:
                logger.error(f"[Upload] AI client init failed: {e}")
                self._update_status(document, 'failed', error=f"AI Service error: {str(e)}")
                return

            # ── 5c. Chunk & Embed ─────────────────────────────────────────────
            from services.document.chunker import DocumentChunker
            chunker = DocumentChunker()

            # Persist runtime chunking strategy for observability/tuning
            document.chunking_strategy = chunker.strategy_name
            document.save(update_fields=['chunking_strategy'])
            
            # chunk_and_embed handles: chunking, embedding, DB saving, Qdrant saving, and linking
            try:
                with transaction.atomic():
                    processed_chunks = chunker.chunk_and_embed(
                        text=text,
                        document_id=doc_id,
                        llama_client=llama,
                        qdrant_client=qdrant,
                        metadata={
                            'file_type': document.file_type,
                            'page_count': parse_meta.get('pages', 0),
                            'word_count': parse_meta.get('word_count', 0),
                            'source_name': document.original_name,
                        },
                    )
            except Exception as e:
                logger.error(f"[Upload] Chunk & Embed failed for {doc_id}: {e}")
                self._update_status(document, 'failed', error=f"Processing error: {str(e)}")
                return

            # ── 5d. Cập nhật Document status ──────────────────────────────────
            if processed_chunks:
                document.status = 'completed'
                document.chunking_strategy = chunker.strategy_name
                document.metadata.update({
                    'chunk_count': len(processed_chunks),
                    'word_count': parse_meta.get('word_count', 0),
                    'page_count': parse_meta.get('pages', 0),
                    'processed_at': timezone.now().isoformat(),
                })
                document.save(update_fields=['status', 'metadata'])
                logger.info(
                    f"[Upload] Document {doc_id} processed successfully: "
                    f"{len(processed_chunks)} chunks embedded"
                )
            else:
                self._update_status(document, 'failed', error='Không tạo được chunk hoặc embedding nào')

        except Exception as e:
            logger.error(f"[Upload] Unexpected error processing {doc_id}: {e}", exc_info=True)
            self._update_status(document, 'failed', error=str(e))

        except Exception as e:
            logger.error(f"[Upload] Unexpected error processing {doc_id}: {e}", exc_info=True)
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
