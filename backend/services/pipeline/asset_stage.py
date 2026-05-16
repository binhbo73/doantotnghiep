"""
Asset Pipeline Stage - OCR + VL Caption + Embed
================================================

Flow:
1. Gọi AssetExtractor để extract ảnh từ file
2. Lưu ảnh vào media/document_assets/{doc_id}/
3. Chạy Tesseract OCR trên từng ảnh
4. Gọi Qwen2.5-VL tạo caption (vision model thật)
5. Lưu DocumentAsset vào DB
6. Embed caption vào Qdrant collection document_assets
"""

import os
import io
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from django.conf import settings
from django.utils import timezone

from .base import PipelineStage, PipelineContext, StageExecutionError

logger = logging.getLogger(__name__)


class AssetPipelineStage(PipelineStage):
    """
    Trích xuất ảnh → OCR → VL Caption → Lưu DB → Embed.

    Cấu hình (settings.py):
        ASSET_PIPELINE_ENABLED = True
        ASSET_OCR_ENABLED = True
        ASSET_OCR_LANGUAGES = 'vie+eng'
        ASSET_VL_CAPTION_ENABLED = True
        ASSET_EMBED_CAPTIONS = True
        ASSET_MAX_IMAGES_PER_DOC = 50
        ASSET_MIN_IMAGE_SIZE_BYTES = 1024
        ASSET_IMAGE_MAX_WIDTH = 2000
    """

    STAGE_NAME = "asset_extraction"

    def __init__(self, name: str = None):
        super().__init__(name=name or self.STAGE_NAME)
        self.ocr_enabled = getattr(settings, 'ASSET_OCR_ENABLED', True)
        self.ocr_languages = getattr(settings, 'ASSET_OCR_LANGUAGES', 'vie+eng')
        self.vl_caption_enabled = getattr(settings, 'ASSET_VL_CAPTION_ENABLED', True)
        self.embed_captions = getattr(settings, 'ASSET_EMBED_CAPTIONS', True)
        self.max_images = getattr(settings, 'ASSET_MAX_IMAGES_PER_DOC', 50)
        self.min_image_bytes = getattr(settings, 'ASSET_MIN_IMAGE_SIZE_BYTES', 1024)
        self.max_image_width = getattr(settings, 'ASSET_IMAGE_MAX_WIDTH', 2000)

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Thực thi asset extraction + OCR + VL caption."""
        t_start = time.monotonic()

        if not getattr(settings, 'ASSET_PIPELINE_ENABLED', True):
            self.logger.info("Asset pipeline disabled (ASSET_PIPELINE_ENABLED=False)")
            return context

        try:
            file_path = context.file_path
            document_id = context.document_id
            file_ext = (context.metadata.get('file_extension', '') or '').lower()

            # Lấy full text từ page_aware_text nếu có
            full_text = ''
            pa_text = context.metadata.get('page_aware_text')
            if pa_text and hasattr(pa_text, 'text'):
                full_text = pa_text.text
            elif context.metadata.get('text_content'):
                full_text = context.metadata['text_content']

            # ── Bước 1: Extract ảnh từ file ──────────────────
            from services.document.asset_extractor import AssetExtractor

            extractor = AssetExtractor()

            ext_map = {
                '.pdf': ('pdf', extractor.extract_from_pdf),
                '.docx': ('docx', extractor.extract_from_docx),
                '.doc': ('docx', extractor.extract_from_docx),
                '.xlsx': ('xlsx', extractor.extract_from_xlsx),
                '.xls': ('xlsx', extractor.extract_from_xlsx),
            }

            if file_ext not in ext_map:
                self.logger.info(f"Asset extraction not supported for {file_ext}")
                context.metadata['asset_count'] = 0
                return context

            extract_func = ext_map[file_ext][1]
            raw_assets = extract_func(file_path, full_text)

            if not raw_assets:
                self.logger.info(f"No assets found in {os.path.basename(file_path)}")
                context.metadata['asset_count'] = 0
                return context

            # Giới hạn số lượng
            raw_assets = raw_assets[:self.max_images]
            self.logger.info(
                f"[ASSET] Extracted {len(raw_assets)} raw assets from {os.path.basename(file_path)}"
            )

            # ── Bước 2: Khởi tạo VL caption client (nếu cần) ──
            vl_client = None
            if self.vl_caption_enabled:
                try:
                    from services.ai.vl_caption_client import VLCaptionClient
                    vl_client = VLCaptionClient()
                    if not vl_client.is_available():
                        self.logger.warning(
                            "VL model not available, falling back to rule-based caption"
                        )
                        vl_client = None
                except Exception as e:
                    self.logger.warning(f"Failed to init VL client: {e}")

            # ── Bước 3: Xử lý từng asset ─────────────────────
            from django.apps import apps
            DocumentAsset = apps.get_model('documents', 'DocumentAsset')
            DocumentChunk = apps.get_model('documents', 'DocumentChunk')

            asset_count = 0
            ocr_success = 0
            caption_success = 0

            for idx, raw in enumerate(raw_assets):
                try:
                    # Bỏ qua ảnh quá nhỏ
                    if len(raw.get('image_data', b'')) < self.min_image_bytes:
                        continue

                    # ── Resize nếu quá lớn ──
                    image_data = raw['image_data']
                    width = raw.get('width', 0)
                    height = raw.get('height', 0)

                    if width > self.max_image_width:
                        image_data, width, height = self._resize_image(image_data, self.max_image_width)

                    # ── Lưu ảnh ──
                    image_path = extractor.save_asset_image(document_id, raw, idx)

                    # Cập nhật file đã resize nếu có
                    if width <= self.max_image_width:
                        full_image_path = os.path.join(
                            extractor.media_root, str(document_id),
                            os.path.basename(image_path)
                        )
                        with open(full_image_path, 'wb') as f:
                            f.write(image_data)

                    # ── OCR ──
                    ocr_text = ''
                    ocr_confidence = 0.0
                    if self.ocr_enabled:
                        ocr_text, ocr_confidence = self._run_ocr(image_data)
                        if ocr_text:
                            ocr_success += 1

                    # ── VL Caption ──
                    caption = ''
                    caption_raw = ''
                    caption_model = 'rule-based'

                    if vl_client and image_data:
                        location_hint = vl_client._build_location_hint(raw)
                        caption_raw = vl_client.generate_caption(
                            image_data=image_data,
                            image_format=raw.get('image_format', 'png'),
                            context_text=raw.get('context_text', ''),
                            location_hint=location_hint,
                            language='vi',
                        )
                        if caption_raw:
                            caption = caption_raw
                            caption_model = getattr(settings, 'VL_MODEL_NAME', 'qwen25-vl-3b')
                            caption_success += 1

                    # Fallback: rule-based caption nếu VL không available
                    if not caption:
                        caption = self._generate_rule_based_caption(raw, ocr_text)

                    # ── Tìm chunk gần nhất ──
                    chunk = None
                    if raw.get('page_number'):
                        chunk = DocumentChunk.objects.filter(
                            document_id=document_id,
                            page_number=raw['page_number'],
                            is_deleted=False,
                        ).first()

                    # ── Lưu DocumentAsset ──
                    status = 'captioned' if caption else ('ocr_done' if ocr_text else 'extracted')

                    asset = DocumentAsset.objects.create(
                        document_id=document_id,
                        chunk=chunk,
                        asset_type=raw.get('asset_type', 'other'),
                        page_number=raw.get('page_number'),
                        sheet_name=raw.get('sheet_name'),
                        anchor_cell=raw.get('anchor_cell'),
                        anchor_row=raw.get('anchor_row'),
                        paragraph_index=raw.get('paragraph_index'),
                        position_in_document=raw.get('position', {}),
                        image_path=image_path,
                        image_format=raw.get('image_format', 'png'),
                        image_width=width,
                        image_height=height,
                        image_size_bytes=len(image_data),
                        ocr_text=ocr_text[:5000] if ocr_text else None,
                        ocr_confidence=round(ocr_confidence, 1) if ocr_confidence else None,
                        ocr_language=self.ocr_languages,
                        caption=caption[:2000] if caption else None,
                        caption_model=caption_model,
                        caption_raw_response=caption_raw[:2000] if caption_raw else None,
                        context_text=(raw.get('context_text', '') or '')[:3000],
                        context_range={
                            'start_char': raw.get('position', {}).get('x', 0),
                            'end_char': raw.get('position', {}).get('x', 0) + raw.get('position', {}).get('width', 0),
                        },
                        processing_status=status,
                        processed_at=timezone.now(),
                    )

                    # ── Embed caption vào Qdrant ──
                    if self.embed_captions and caption:
                        self._embed_asset_caption(asset)

                    asset_count += 1

                    self.logger.debug(
                        f"Asset {idx}: type={asset.asset_type}, page={asset.page_number}, "
                        f"cell={asset.anchor_cell}, ocr={len(ocr_text)}B, caption={len(caption)}B"
                    )

                except Exception as e:
                    self.logger.warning(f"Failed to process asset {idx}: {e}")
                    continue

            # ── Ghi metadata vào context ──
            context.metadata['asset_count'] = asset_count
            context.metadata['asset_ocr_success'] = ocr_success
            context.metadata['asset_caption_success'] = caption_success
            context.metadata['asset_vl_enabled'] = vl_client is not None
            context.metadata['asset_extracted_at'] = datetime.now().isoformat()

            total_ms = (time.monotonic() - t_start) * 1000
            self.logger.info(
                f"[ASSET] stage=complete document={document_id} "
                f"assets={asset_count}/{len(raw_assets)} ocr={ocr_success} caption={caption_success} "
                f"vl={vl_client is not None} time={total_ms:.0f}ms"
            )

            return context

        except Exception as e:
            self.logger.error(f"Asset pipeline failed: {e}", exc_info=True)
            context.metadata['asset_error'] = str(e)[:500]
            context.metadata['asset_count'] = 0
            return context

    # ═══════════════════════════════════════════════════════════════
    # OCR
    # ═══════════════════════════════════════════════════════════════

    def _run_ocr(self, image_data: bytes) -> tuple:
        """Chạy Tesseract OCR, trả về (text, confidence)."""
        try:
            import pytesseract
            from PIL import Image

            img = Image.open(io.BytesIO(image_data))

            # Convert grayscale
            if img.mode not in ('L', 'LA'):
                img = img.convert('L')

            custom_config = r'--oem 3 --psm 6'
            ocr_data = pytesseract.image_to_data(
                img,
                lang=self.ocr_languages,
                config=custom_config,
                output_type=pytesseract.Output.DICT,
            )

            ocr_text = ' '.join(w for w in ocr_data['text'] if w.strip())
            confidences = [c for c in ocr_data['conf'] if c > 0]
            avg_conf = sum(confidences) / len(confidences) if confidences else 0

            return ocr_text.strip(), round(avg_conf, 1)

        except ImportError:
            self.logger.warning("pytesseract not installed. OCR skipped.")
            return '', 0.0
        except Exception as e:
            self.logger.warning(f"OCR failed: {e}")
            return '', 0.0

    # ═══════════════════════════════════════════════════════════════
    # RULE-BASED CAPTION (fallback khi VL không available)
    # ═══════════════════════════════════════════════════════════════

    def _generate_rule_based_caption(self, asset: Dict[str, Any], ocr_text: str) -> str:
        """Fallback caption khi VL model không sẵn sàng."""
        parts = []

        # Loại asset
        type_labels = {
            'pdf_embedded': 'Ảnh nhúng trong PDF',
            'pdf_page_render': 'Trang quét PDF',
            'docx_inline': 'Ảnh trong DOCX',
            'docx_header': 'Ảnh header DOCX',
            'xlsx_image': 'Ảnh trong Excel',
            'xls_image': 'Ảnh trong Excel',
        }
        type_label = type_labels.get(asset.get('asset_type', ''), 'Ảnh')

        # Vị trí
        location_parts = []
        if asset.get('sheet_name'):
            location_parts.append(f"Sheet {asset['sheet_name']}")
        if asset.get('anchor_cell'):
            location_parts.append(f"cell {asset['anchor_cell']}")
        if asset.get('anchor_row'):
            location_parts.append(f"dòng {asset['anchor_row']}")
        if asset.get('page_number'):
            location_parts.append(f"trang {asset['page_number']}")
        if asset.get('paragraph_index') is not None:
            location_parts.append(f"đoạn {asset['paragraph_index'] + 1}")

        location_str = ', '.join(location_parts) if location_parts else 'tài liệu'
        caption = f"{type_label} tại {location_str}."

        # OCR
        if ocr_text:
            ocr_preview = ocr_text[:200].replace('\n', ' ')
            caption += f" OCR: {ocr_preview}."

        # Context
        ctx = (asset.get('context_text', '') or '')[:200].replace('\n', ' ')
        if ctx:
            caption += f" Ngữ cảnh: {ctx}."

        return caption

    # ═══════════════════════════════════════════════════════════════
    # EMBED
    # ═══════════════════════════════════════════════════════════════

    def _embed_asset_caption(self, asset) -> None:
        """Embed caption asset vào Qdrant collection document_assets."""
        try:
            from services.ai.embedding_client import EmbeddingClient
            from services.ai.qdrant_client import QdrantClient

            embedding_client = EmbeddingClient()
            qdrant_client = QdrantClient()

            caption_embedding = embedding_client.create_embedding(asset.caption)
            if not caption_embedding:
                return

            vector_id = qdrant_client.add_asset_embedding(
                embedding=caption_embedding,
                asset_id=str(asset.id),
                document_id=str(asset.document_id),
                chunk_id=str(asset.chunk_id) if asset.chunk_id else None,
                caption=asset.caption,
                page_number=asset.page_number,
                sheet_name=asset.sheet_name,
                anchor_cell=asset.anchor_cell,
                image_path=asset.image_path,
            )

            asset.caption_embedding_id = vector_id
            asset.embedding_model = getattr(settings, 'EMBEDDING_MODEL', 'bge-m3')
            asset.embedding_dimension = len(caption_embedding)
            asset.processing_status = 'embedded'
            asset.save(update_fields=[
                'caption_embedding_id', 'embedding_model',
                'embedding_dimension', 'processing_status',
            ])

            self.logger.debug(f"Asset {asset.id} embedded: vector={vector_id}")

        except Exception as e:
            self.logger.warning(f"Failed to embed asset {asset.id}: {e}")

    # ═══════════════════════════════════════════════════════════════
    # IMAGE UTILS
    # ═══════════════════════════════════════════════════════════════

    def _resize_image(self, image_data: bytes, max_width: int) -> tuple:
        """Resize ảnh giữ tỉ lệ nếu width > max_width."""
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(image_data))
            w, h = img.size

            if w <= max_width:
                return image_data, w, h

            ratio = max_width / w
            new_size = (max_width, int(h * ratio))
            img_resized = img.resize(new_size, Image.LANCZOS)

            output = io.BytesIO()
            fmt = img.format or 'PNG'
            img_resized.save(output, format=fmt)
            return output.getvalue(), new_size[0], new_size[1]

        except Exception as e:
            self.logger.warning(f"Image resize failed: {e}")
            return image_data, 0, 0

    def can_skip(self, context: PipelineContext) -> bool:
        """Skip nếu pipeline bị tắt hoặc không có file."""
        if not getattr(settings, 'ASSET_PIPELINE_ENABLED', True):
            return True
        if not context.file_path or not os.path.exists(context.file_path):
            return True
        return False
