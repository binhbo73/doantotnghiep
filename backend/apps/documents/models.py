from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from apps.users.models import Account, Department
from core.models import BaseModel
import uuid


class Folder(BaseModel):
    """
    Document folder (hierarchical tree structure).
    Folders can have subfolders and documents.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="Folder name")
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subfolders',
        help_text="Parent folder (hierarchical structure)"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='folders',
        help_text="Associated department"
    )
    access_scope = models.CharField(
        max_length=50,
        default='company',
        choices=[('personal', 'Personal'), ('department', 'Department'), ('company', 'Company')],
        help_text="Access scope (personal, department, company)"
    )
    description = models.TextField(max_length=1000, null=True, blank=True, help_text="Folder description")
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional metadata")
    created_by = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_folders',
        help_text="User who created this folder"
    )

    class Meta:
        db_table = "folders"
        verbose_name = "Folder"
        verbose_name_plural = "Folders"
        indexes = [
            models.Index(fields=['parent_id']),
            models.Index(fields=['department_id']),
            models.Index(fields=['created_by_id']),
            models.Index(fields=['name']),
            models.Index(fields=['is_deleted']),
        ]

    def __str__(self):
        return self.name


class Tag(BaseModel):
    """
    Tags for categorizing and organizing documents.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="Tag name")
    color = models.CharField(max_length=10, default="#000000", help_text="Hex color code")
    description = models.TextField(max_length=500, null=True, blank=True, help_text="Tag description")
    created_by = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tags',
        help_text="User who created this tag"
    )

    class Meta:
        db_table = "tags"
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

    def __str__(self):
        return self.name


class Document(BaseModel):
    """
    Core document model for RAG system.
    Supports hierarchical chunking, versioning, and permission management.
    25 fields total including new fields for hierarchical RAG and version control.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255, help_text="Stored filename")
    original_name = models.CharField(max_length=255, help_text="Original filename from upload")
    storage_path = models.TextField(help_text="Full path in storage (S3, local, etc.)")
    file_type = models.CharField(max_length=255, help_text="File type (pdf, docx, txt, markdown)")
    file_size = models.BigIntegerField(default=0, help_text="File size in bytes")
    mime_type = models.CharField(max_length=255, null=True, blank=True, help_text="MIME type")
    uploader = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents',
        help_text="User who uploaded this document"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        help_text="Associated department"
    )
    folder = models.ForeignKey(
        Folder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        help_text="Folder containing this document"
    )
    access_scope = models.CharField(
        max_length=50,
        default='company',
        choices=[('personal', 'Personal'), ('department', 'Department'), ('company', 'Company')],
        help_text="Access scope (personal, department, company)"
    )
    is_public = models.BooleanField(default=False, help_text="Is publicly accessible?")
    tags = models.ManyToManyField(Tag, blank=True, related_name='documents', help_text="Associated tags")
    doc_language = models.CharField(max_length=10, default='vi', help_text="Document language (vi, en, etc.)")
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional metadata")
    version = models.IntegerField(default=1, help_text="Version number (for updates)")
    embedding_model = models.CharField(
        max_length=100,
        default="mistral-embed",
        help_text="Embedding model used"
    )
    chunking_strategy = models.CharField(
        max_length=100,
        default="recursive_character_1000_200",
        help_text="Chunking strategy (e.g., recursive_character_1000_200)"
    )
    s3_url = models.URLField(
        max_length=1000,
        null=True,
        blank=True,
        help_text="S3 URL for direct access"
    )
    status = models.CharField(
        max_length=50,
        default='pending',
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        help_text="Processing status"
    )
    version_lock = models.IntegerField(
        default=1,
        help_text="Version lock for optimistic concurrency control"
    )
    has_hierarchical_chunks = models.BooleanField(
        default=False,
        help_text="Does this document have hierarchical chunks (parent-child)?"
    )

    class Meta:
        db_table = "documents"
        verbose_name = "Document"
        verbose_name_plural = "Documents"
        indexes = [
            models.Index(fields=['uploader_id']),
            models.Index(fields=['department_id', 'is_deleted']),
            models.Index(fields=['folder_id', 'is_deleted']),
            models.Index(fields=['status', 'is_deleted']),
            models.Index(fields=['created_at'], name='idx_documents_created_at'),
            models.Index(fields=['is_deleted']),
        ]

    def __str__(self):
        return self.original_name


class DocumentChunk(BaseModel):
    """
    Document chunks for RAG (Retrieval-Augmented Generation).
    Supports hierarchical chunks (parent-child structure).
    Tracks vector IDs for Qdrant synchronization.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='chunks',
        help_text="Parent document"
    )
    parent_node = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='child_nodes',
        help_text="Parent chunk (hierarchical structure)"
    )
    prev_chunk = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='next_chunk_ref',
        help_text="Previous chunk in sequence"
    )
    next_chunk = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prev_chunk_ref',
        help_text="Next chunk in sequence"
    )
    node_type = models.CharField(
        max_length=50,
        default='detail',
        choices=[('summary', 'Summary'), ('detail', 'Detail'), ('section', 'Section')],
        help_text="Chunk type (summary, detail, section)"
    )
    vector_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="ID in Qdrant vector database"
    )
    content = models.TextField(help_text="Chunk content text")
    summary = models.TextField(null=True, blank=True, help_text="AI-generated summary")
    page_number = models.IntegerField(default=1, help_text="Page number in source document")
    chunk_index = models.IntegerField(default=0, help_text="Sequential index of chunk")
    token_count = models.IntegerField(default=0, help_text="Token count (for cost calculation)")
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata (position, heading, etc.)"
    )
    search_vector = SearchVectorField(null=True, blank=True, verbose_name="FTS Search Vector")

    class Meta:
        db_table = "document_chunks"
        verbose_name = "Document Chunk"
        verbose_name_plural = "Document Chunks"
        indexes = [
            models.Index(fields=['document_id']),
            models.Index(fields=['parent_node_id']),
            models.Index(fields=['vector_id']),
            models.Index(fields=['page_number']),
            models.Index(fields=['prev_chunk_id'], name='idx_chunk_prev'),
            models.Index(fields=['next_chunk_id'], name='idx_chunk_next'),
            models.Index(fields=['is_deleted']),
            GinIndex(fields=['search_vector'], name='docchunk_search_vec_gin'),
        ]

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.document.original_name}"


class DocumentPermission(BaseModel):
    """
    Document-level permissions with permission precedence.
    Supports role-based and account-specific permissions.
    Implements permission precedence: inherit, override, deny.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='permissions',
        help_text="Document being permission-controlled"
    )
    subject_type = models.CharField(
        max_length=50,
        choices=[('role', 'Role'), ('account', 'Account')],
        help_text="Type of subject (role or account)"
    )
    subject_id = models.CharField(
        max_length=255,
        help_text="ID of role (UUID) or account (BIGINT)"
    )
    permission = models.CharField(
        max_length=50,
        default='read',
        choices=[('read', 'Read'), ('write', 'Write'), ('delete', 'Delete')],
        help_text="Permission level (read, write, delete)"
    )
    permission_precedence = models.CharField(
        max_length=50,
        default='inherit',
        choices=[('inherit', 'Inherit'), ('override', 'Override'), ('deny', 'Deny')],
        help_text="Permission precedence (inherit from folder, override, or deny)"
    )
    is_active = models.BooleanField(default=True, help_text="Is this permission active?")
    granted_by = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='document_permissions_granted',
        help_text="User who granted this permission"
    )

    class Meta:
        db_table = "document_permissions"
        verbose_name = "Document Permission"
        verbose_name_plural = "Document Permissions"
        unique_together = [['document', 'subject_type', 'subject_id']]
        indexes = [
            models.Index(fields=['document_id']),
            models.Index(fields=['subject_type', 'subject_id']),
            models.Index(fields=['permission_precedence']),
            models.Index(fields=['is_deleted']),
        ]

    def __str__(self):
        return f"{self.document.original_name} → {self.subject_type}:{self.subject_id}"

    @property
    def resolved_subject(self):
        """Resolves the CharField subject_id to an actual Account or Role instance."""
        try:
            if self.subject_type == 'role':
                from apps.users.models import Role
                return Role.objects.get(pk=self.subject_id)
            elif self.subject_type == 'account':
                from apps.users.models import Account
                return Account.objects.get(pk=self.subject_id)
        except Exception:
            return None
        return None


class FolderPermission(BaseModel):
    """
    Folder-level permissions.
    Folders can inherit permissions to contained documents.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    folder = models.ForeignKey(
        Folder,
        on_delete=models.CASCADE,
        related_name='permissions',
        help_text="Folder being permission-controlled"
    )
    subject_type = models.CharField(
        max_length=50,
        choices=[('role', 'Role'), ('account', 'Account')],
        help_text="Type of subject (role or account)"
    )
    subject_id = models.CharField(
        max_length=255,
        help_text="ID of role (UUID) or account (BIGINT)"
    )
    permission = models.CharField(
        max_length=50,
        default='read',
        choices=[('read', 'Read'), ('write', 'Write'), ('delete', 'Delete')],
        help_text="Permission level (read, write, delete)"
    )
    is_active = models.BooleanField(default=True, help_text="Is this permission active?")
    granted_by = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='folder_permissions_granted',
        help_text="User who granted this permission"
    )

    class Meta:
        db_table = "folder_permissions"
        verbose_name = "Folder Permission"
        verbose_name_plural = "Folder Permissions"
        unique_together = [['folder', 'subject_type', 'subject_id']]
        indexes = [
            models.Index(fields=['folder_id']),
            models.Index(fields=['subject_type', 'subject_id']),
            models.Index(fields=['is_deleted']),
        ]

    def __str__(self):
        return f"{self.folder.name} → {self.subject_type}:{self.subject_id}"

    @property
    def resolved_subject(self):
        """Resolves the CharField subject_id to an actual Account or Role instance."""
        try:
            if self.subject_type == 'role':
                from apps.users.models import Role
                return Role.objects.get(pk=self.subject_id)
            elif self.subject_type == 'account':
                from apps.users.models import Account
                return Account.objects.get(pk=self.subject_id)
        except Exception:
            return None
        return None


class DocumentEmbedding(BaseModel):
    """
    Document embeddings (vector representations).
    Stores embedding vectors for document chunks (for RAG similarity search).
    
    Có thể lưu vector ở:
    1. Database này (nếu model nhỏ, dùng pgvector)
    2. Qdrant vector database (mặc định cho production)
    
    Table này tracks metadata + vector_id reference tới Qdrant.
    
    Inherits from BaseModel: automatic soft delete + timestamps + SoftDeleteManager
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chunk = models.ForeignKey(
        DocumentChunk,
        on_delete=models.CASCADE,
        related_name='embeddings',
        help_text="Chunk being embedded"
    )
    embedding_model = models.CharField(
        max_length=100,
        default="Q wen3-4B-Instruct-2507-Q4_K_M",
        help_text="Model used for embedding"
    )
    embedding_dimension = models.IntegerField(
        default=1536,
        help_text="Vector dimension"
    )
    # Store embedding locally (optional - using pgvector if enabled)
    # In production, vectors are typically stored in Qdrant, not here
    embedding_vector = models.TextField(
        null=True,
        blank=True,
        help_text="Vector as JSON (optional - usually in Qdrant)"
    )
    qdrant_vector_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
        help_text="Vector ID in Qdrant database"
    )
    qdrant_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Similarity score from last Qdrant search"
    )
    embedding_computed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "document_embeddings"
        verbose_name = "Document Embedding"
        verbose_name_plural = "Document Embeddings"
        indexes = [
            models.Index(fields=['chunk_id']),
            models.Index(fields=['qdrant_vector_id']),
            models.Index(fields=['embedding_model']),
            models.Index(fields=['created_at']),
        ]
        unique_together = [['chunk', 'embedding_model']]
    
    def __str__(self):
        return f"Embedding for chunk {self.chunk.chunk_index}"


class DocumentAsset(BaseModel):
    """
    Ảnh / embedded object trích xuất từ tài liệu (PDF, DOCX, XLSX).

    Mỗi asset chứa:
    - Ảnh gốc (lưu file)
    - Kết quả OCR từ Tesseract (text trong ảnh)
    - Caption từ Qwen2.5-VL (mô tả ảnh bằng vision model)
    - Vector embedding của caption (lưu trong Qdrant collection document_assets)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ── Liên kết ────────────────────────────────────────────
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='assets',
        help_text="Tài liệu cha chứa asset này"
    )
    chunk = models.ForeignKey(
        DocumentChunk,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assets',
        help_text="DocumentChunk gần nhất chứa asset"
    )

    # ── Loại asset ──────────────────────────────────────────
    asset_type = models.CharField(
        max_length=50,
        choices=[
            ('pdf_embedded', 'PDF Embedded Image'),
            ('pdf_page_render', 'PDF Page Render'),
            ('docx_inline', 'DOCX Inline Image'),
            ('docx_header', 'DOCX Header Image'),
            ('xlsx_image', 'XLSX Embedded Image'),
            ('xls_image', 'XLS Embedded Image'),
            ('other', 'Other'),
        ],
        help_text="Loại asset (nguồn gốc)"
    )

    # ── Định vị trong tài liệu ─────────────────────────────
    page_number = models.IntegerField(null=True, blank=True, help_text="Số trang (PDF) hoặc sheet index (Excel)")
    sheet_name = models.CharField(max_length=255, null=True, blank=True, help_text="Tên sheet (Excel)")
    anchor_cell = models.CharField(max_length=20, null=True, blank=True, help_text="Ô anchor Excel: G9, F8")
    anchor_row = models.IntegerField(null=True, blank=True, help_text="Số dòng anchor trong Excel")
    paragraph_index = models.IntegerField(null=True, blank=True, help_text="Thứ tự paragraph trong DOCX")
    position_in_document = models.JSONField(default=dict, blank=True, help_text="{x, y, width, height} trên trang")

    # ── File ảnh ───────────────────────────────────────────
    image_path = models.TextField(help_text="Đường dẫn: media/document_assets/{doc_id}/...")
    image_format = models.CharField(max_length=10, default='png', help_text="png, jpg, webp")
    image_width = models.IntegerField(null=True, blank=True, help_text="Chiều rộng pixels")
    image_height = models.IntegerField(null=True, blank=True, help_text="Chiều cao pixels")
    image_size_bytes = models.IntegerField(default=0, help_text="Kích thước file bytes")

    # ── OCR ────────────────────────────────────────────────
    ocr_text = models.TextField(null=True, blank=True, help_text="Kết quả OCR từ Tesseract")
    ocr_confidence = models.FloatField(null=True, blank=True, help_text="Độ tin cậy OCR trung bình (0-100)")
    ocr_language = models.CharField(max_length=20, default='vie', help_text="vie, eng, vie+eng")

    # ── Caption (VL model) ─────────────────────────────────
    caption = models.TextField(null=True, blank=True, help_text="Caption từ Qwen2.5-VL: mô tả nội dung ảnh")
    caption_model = models.CharField(max_length=100, default='qwen25-vl-3b', help_text="Model tạo caption")
    caption_raw_response = models.TextField(null=True, blank=True, help_text="Response gốc từ VL model")

    # ── Context xung quanh ảnh ─────────────────────────────
    context_text = models.TextField(null=True, blank=True, help_text="Text xung quanh ảnh (paragraph/sheet/row)")
    context_range = models.JSONField(default=dict, blank=True, help_text="{start_char, end_char}")

    # ── Embedding ──────────────────────────────────────────
    caption_embedding_id = models.CharField(max_length=255, null=True, blank=True, help_text="Vector ID trong Qdrant (collection: document_assets)")
    embedding_model = models.CharField(max_length=100, default='bge-m3', help_text="Model embed caption")
    embedding_dimension = models.IntegerField(default=1024, help_text="Số chiều vector embedding")

    # ── Trạng thái xử lý ──────────────────────────────────
    processing_status = models.CharField(
        max_length=50, default='pending',
        choices=[
            ('pending', 'Pending'),
            ('extracted', 'Extracted'),
            ('ocr_done', 'OCR Done'),
            ('captioned', 'Captioned'),
            ('embedded', 'Embedded'),
            ('failed', 'Failed'),
        ],
        help_text="Trạng thái xử lý asset"
    )
    processing_error = models.TextField(null=True, blank=True, help_text="Lỗi nếu failed")
    processed_at = models.DateTimeField(null=True, blank=True, help_text="Thời điểm xử lý xong")

    class Meta:
        db_table = "document_assets"
        verbose_name = "Document Asset"
        verbose_name_plural = "Document Assets"
        indexes = [
            models.Index(fields=['document_id']),
            models.Index(fields=['chunk_id']),
            models.Index(fields=['asset_type']),
            models.Index(fields=['processing_status']),
            models.Index(fields=['page_number']),
            models.Index(fields=['sheet_name', 'anchor_cell']),
            models.Index(fields=['caption_embedding_id']),
            models.Index(fields=['is_deleted']),
        ]
        ordering = ['page_number', 'paragraph_index']

    def __str__(self):
        location = (
            f"Sheet={self.sheet_name}, Cell={self.anchor_cell}"
            if self.sheet_name
            else f"Page={self.page_number}"
        )
        return f"Asset {self.asset_type} at {location} of {self.document.original_name}"
