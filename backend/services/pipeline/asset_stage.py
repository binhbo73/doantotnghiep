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
        ASSET_OCR_ENGINE = 'tesseract'
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
        self.ocr_engine = getattr(settings, 'ASSET_OCR_ENGINE', 'tesseract')
        self.ocr_languages = getattr(settings, 'ASSET_OCR_LANGUAGES', 'vie+eng')
        self.paddleocr_lang = getattr(settings, 'ASSET_PADDLEOCR_LANG', 'vi')
        self.vl_caption_enabled = getattr(settings, 'ASSET_VL_CAPTION_ENABLED', True)
        self.embed_captions = getattr(settings, 'ASSET_EMBED_CAPTIONS', True)
        self.max_images = getattr(settings, 'ASSET_MAX_IMAGES_PER_DOC', 50)
        self.min_image_bytes = getattr(settings, 'ASSET_MIN_IMAGE_SIZE_BYTES', 1024)
        self.max_image_width = getattr(settings, 'ASSET_IMAGE_MAX_WIDTH', 2000)
        self._paddle_ocr = None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Thực thi asset extraction + OCR + VL caption."""
        t_start = time.monotonic()
        context.metadata['asset_status'] = 'processing'
        context.metadata['asset_ready'] = False
        context.metadata['asset_started_at'] = timezone.now().isoformat()

        if not getattr(settings, 'ASSET_PIPELINE_ENABLED', True):
            self.logger.info("Asset pipeline disabled (ASSET_PIPELINE_ENABLED=False)")
            context.metadata['asset_status'] = 'not_required'
            context.metadata['asset_reason'] = 'disabled'
            context.metadata['asset_count'] = 0
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
            elif context.text_content:
                full_text = context.text_content
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
                context.metadata['asset_status'] = 'not_required'
                context.metadata['asset_reason'] = f'unsupported_file_type:{file_ext or "unknown"}'
                return context

            extract_func = ext_map[file_ext][1]
            raw_assets = extract_func(file_path, full_text)
            if file_ext in {'.doc', '.docx'} and raw_assets:
                self._enrich_docx_assets_with_pages(raw_assets, file_path, pa_text)

            if not raw_assets:
                self.logger.info(f"No assets found in {os.path.basename(file_path)}")
                context.metadata['asset_count'] = 0
                context.metadata['asset_status'] = 'not_required'
                context.metadata['asset_reason'] = 'no_assets_found'
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
            context.metadata['asset_status'] = 'ready'
            context.metadata['asset_ready'] = True
            context.metadata['asset_ready_at'] = timezone.now().isoformat()
            context.metadata['asset_pipeline_ms'] = total_ms
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
            context.metadata['asset_status'] = 'failed'
            context.metadata['asset_ready'] = False
            context.metadata['asset_failed_at'] = timezone.now().isoformat()
            return context

    # ═══════════════════════════════════════════════════════════════
    # OCR
    # ═══════════════════════════════════════════════════════════════

    def _enrich_docx_assets_with_pages(self, raw_assets: List[Dict[str, Any]], file_path: str, page_aware_text) -> None:
        """Map DOCX inline images to the same PDF-preview pages used by chunks."""
        if not page_aware_text or not hasattr(page_aware_text, 'get_page_at_position'):
            return

        try:
            self._enrich_docx_assets_with_pdf_image_pages(raw_assets, file_path, page_aware_text)

            paragraph_offsets = self._get_docx_paragraph_offsets(file_path)
            text_length = len(getattr(page_aware_text, 'text', '') or '')

            for asset_index, raw in enumerate(raw_assets):
                if raw.get('page_number'):
                    continue

                para_idx = raw.get('paragraph_index')
                if para_idx is None:
                    para_idx = (raw.get('position') or {}).get('paragraph_index')

                char_pos = None
                if isinstance(para_idx, int) and paragraph_offsets:
                    safe_idx = max(0, min(para_idx, len(paragraph_offsets) - 1))
                    char_pos = paragraph_offsets[safe_idx]
                elif text_length > 0:
                    char_pos = int((asset_index / max(1, len(raw_assets))) * text_length)

                if char_pos is None:
                    continue

                page_number = page_aware_text.get_page_at_position(char_pos)
                raw['page_number'] = page_number
                raw_position = raw.setdefault('position', {})
                raw_position['page_number'] = page_number
                raw_position['char_pos'] = char_pos

                self.logger.info(
                    f"[ASSET] DOCX asset {asset_index} paragraph={para_idx} "
                    f"mapped_to_page={page_number} char={char_pos}"
                )
        except Exception as e:
            self.logger.warning(f"Failed to enrich DOCX assets with page numbers: {e}")

    def _enrich_docx_assets_with_pdf_image_pages(
        self,
        raw_assets: List[Dict[str, Any]],
        file_path: str,
        page_aware_text,
    ) -> int:
        """Find the page where each DOCX image is actually rendered in the PDF preview."""
        try:
            import fitz
            from PIL import Image
            from io import BytesIO
            from services.document.office_preview import convert_office_to_pdf
        except Exception as e:
            self.logger.debug(f"PDF image page mapping unavailable: {e}")
            return 0

        def image_hash(image_data: bytes, size: int = 16) -> Optional[str]:
            try:
                image = Image.open(BytesIO(image_data)).convert('L').resize((size, size))
                values = list(image.getdata())
                average = sum(values) / len(values)
                return ''.join('1' if value >= average else '0' for value in values)
            except Exception:
                return None

        def hash_distance(left: Optional[str], right: Optional[str]) -> int:
            if not left or not right or len(left) != len(right):
                return 999
            return sum(a != b for a, b in zip(left, right))

        try:
            preview_pdf = convert_office_to_pdf(file_path)
            pdf = fitz.open(preview_pdf)
            paragraph_offsets = self._get_docx_paragraph_offsets(file_path)

            candidates = []
            for page_index in range(pdf.page_count):
                page = pdf[page_index]
                for image_info in page.get_images(full=True):
                    xref = image_info[0]
                    rects = page.get_image_rects(xref)
                    if not rects:
                        continue

                    extracted = pdf.extract_image(xref)
                    image_data = extracted.get('image') or b''
                    digest = image_hash(image_data)
                    if not digest:
                        continue

                    for rect in rects:
                        candidates.append({
                            'page_number': page_index + 1,
                            'page_width': page.rect.width,
                            'page_height': page.rect.height,
                            'xref': xref,
                            'hash': digest,
                            'rect': rect,
                            'used': False,
                        })

            if not candidates:
                return 0

            mapped = 0
            for asset_index, raw in enumerate(raw_assets):
                if raw.get('page_number'):
                    continue

                digest = image_hash(raw.get('image_data', b''))
                if not digest:
                    continue

                para_idx = raw.get('paragraph_index')
                if para_idx is None:
                    para_idx = (raw.get('position') or {}).get('paragraph_index')

                fallback_page = None
                if isinstance(para_idx, int) and paragraph_offsets:
                    safe_idx = max(0, min(para_idx, len(paragraph_offsets) - 1))
                    fallback_page = page_aware_text.get_page_at_position(paragraph_offsets[safe_idx])

                best_candidate = None
                best_score = None
                best_distance = None
                for candidate in candidates:
                    if candidate['used']:
                        continue
                    distance = hash_distance(digest, candidate['hash'])
                    if distance > 32:
                        continue

                    page_penalty = abs(candidate['page_number'] - fallback_page) if fallback_page else 0
                    score = (distance * 10) + page_penalty
                    if best_score is None or score < best_score:
                        best_candidate = candidate
                        best_score = score
                        best_distance = distance

                if not best_candidate:
                    continue

                best_candidate['used'] = True
                rect = best_candidate['rect']
                page_number = best_candidate['page_number']
                raw['page_number'] = page_number
                raw_position = raw.setdefault('position', {})
                raw_position['page_number'] = page_number
                raw_position['page_source'] = 'pdf_image_match'
                raw_position['pdf_xref'] = best_candidate['xref']
                raw_position['pdf_bbox'] = [
                    round(rect.x0, 2),
                    round(rect.y0, 2),
                    round(rect.x1, 2),
                    round(rect.y1, 2),
                ]
                raw_position['pdf_page_width'] = round(best_candidate['page_width'], 2)
                raw_position['pdf_page_height'] = round(best_candidate['page_height'], 2)
                mapped += 1

                self.logger.info(
                    f"[ASSET] DOCX asset {asset_index} paragraph={para_idx} "
                    f"matched_pdf_page={page_number} hash_distance={best_distance}"
                )

            return mapped
        except Exception as e:
            self.logger.warning(f"Failed to map DOCX assets from PDF preview images: {e}")
            return 0

    def _get_docx_paragraph_offsets(self, file_path: str) -> List[int]:
        try:
            from docx import Document

            doc = Document(file_path)
            offsets = []
            cursor = 0
            for paragraph in doc.paragraphs:
                offsets.append(cursor)
                cursor += len(paragraph.text or '') + 1
            return offsets
        except Exception as e:
            self.logger.warning(f"Failed to read DOCX paragraph offsets: {e}")
            return []

    def _run_ocr(self, image_data: bytes) -> tuple:
        """Run the configured OCR engine and return (text, confidence)."""
        engine = (self.ocr_engine or 'tesseract').lower()
        if engine == 'tesseract':
            return self._run_tesseract_ocr(image_data)
        return self._run_paddleocr(image_data)

    def _get_paddleocr_client(self):
        """Lazy-load PaddleOCR once per asset pipeline run."""
        if self._paddle_ocr is not None:
            return self._paddle_ocr

        from paddleocr import PaddleOCR

        lang = (self.paddleocr_lang or '').strip() or self._map_paddleocr_lang(self.ocr_languages)
        try:
            self._paddle_ocr = PaddleOCR(
                lang=lang,
                use_textline_orientation=True,
            )
        except TypeError:
            self._paddle_ocr = PaddleOCR(
                lang=lang,
                use_angle_cls=True,
            )
        return self._paddle_ocr

    @staticmethod
    def _map_paddleocr_lang(languages: str) -> str:
        normalized = (languages or '').lower()
        if 'vie' in normalized or 'vi' in normalized:
            return 'vi'
        if 'eng' in normalized or 'en' in normalized:
            return 'en'
        return 'vi'

    def _run_paddleocr(self, image_data: bytes) -> tuple:
        """Run PaddleOCR and keep visual rows for table-like images."""
        try:
            import numpy as np
            from PIL import Image

            img = Image.open(io.BytesIO(image_data)).convert('RGB')
            image_array = np.array(img)
            ocr = self._get_paddleocr_client()

            try:
                raw_result = ocr.ocr(image_array, cls=True)
            except TypeError:
                raw_result = ocr.ocr(image_array)
            except AttributeError:
                raw_result = ocr.predict(image_array)

            entries = self._parse_paddleocr_result(raw_result)
            if not entries:
                return '', 0.0

            ocr_text = self._format_ocr_entries_as_reading_order(entries)
            avg_conf = sum(item['confidence'] for item in entries) / len(entries)
            return ocr_text.strip(), round(avg_conf * 100, 1)

        except ImportError:
            self.logger.warning("paddleocr/paddlepaddle not installed. OCR skipped.")
            return '', 0.0
        except Exception as e:
            self.logger.warning(f"PaddleOCR failed: {e}")
            return '', 0.0

    def _parse_paddleocr_result(self, raw_result) -> List[Dict[str, Any]]:
        """Normalize PaddleOCR 2.x/3.x outputs to positioned text boxes."""
        entries: List[Dict[str, Any]] = []

        def add_entry(box, text, confidence):
            text = str(text or '').strip()
            if not text:
                return
            points = []
            try:
                if hasattr(box, 'tolist'):
                    box = box.tolist()
                if (
                    isinstance(box, (list, tuple))
                    and len(box) == 4
                    and all(isinstance(value, (int, float)) for value in box)
                ):
                    x1, y1, x2, y2 = [float(value) for value in box]
                    box = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
                for point in box or []:
                    points.append((float(point[0]), float(point[1])))
            except Exception:
                points = []
            if not points:
                points = [(0.0, 0.0)]
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            entries.append({
                'text': text,
                'confidence': float(confidence or 0.0),
                'x': min(xs),
                'y': min(ys),
                'height': max(1.0, max(ys) - min(ys)),
            })

        def parse_old_item(item):
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                return
            box = item[0]
            payload = item[1]
            if isinstance(payload, (list, tuple)) and payload:
                text = payload[0]
                confidence = payload[1] if len(payload) > 1 else 0.0
                add_entry(box, text, confidence)

        if isinstance(raw_result, list):
            for page in raw_result:
                if hasattr(page, 'to_dict'):
                    page = page.to_dict()
                elif hasattr(page, 'json'):
                    try:
                        page = page.json
                    except Exception:
                        pass
                if isinstance(page, dict):
                    self._parse_paddleocr_dict(page, add_entry)
                elif isinstance(page, list):
                    if page and isinstance(page[0], (list, tuple)) and len(page[0]) >= 2 and isinstance(page[0][1], (list, tuple)):
                        for item in page:
                            parse_old_item(item)
                    else:
                        parse_old_item(page)
        elif isinstance(raw_result, dict):
            self._parse_paddleocr_dict(raw_result, add_entry)
        elif hasattr(raw_result, 'to_dict'):
            self._parse_paddleocr_dict(raw_result.to_dict(), add_entry)

        return entries

    def _parse_paddleocr_dict(self, result: Dict[str, Any], add_entry) -> None:
        """Parse common PaddleOCR 3.x dict result fields."""
        texts = result.get('rec_texts') or result.get('texts') or []
        scores = result.get('rec_scores') or result.get('scores') or []
        boxes = result.get('rec_boxes') or result.get('dt_polys') or result.get('boxes') or []
        for idx, text in enumerate(texts):
            box = boxes[idx] if idx < len(boxes) else None
            confidence = scores[idx] if idx < len(scores) else 0.0
            add_entry(box, text, confidence)

    def _format_ocr_entries_as_reading_order(self, entries: List[Dict[str, Any]]) -> str:
        """Group OCR boxes into rows so tables remain readable/searchable."""
        ordered = sorted(entries, key=lambda item: (item['y'], item['x']))
        rows: List[List[Dict[str, Any]]] = []
        for item in ordered:
            matched_row = None
            for row in rows:
                row_y = sum(cell['y'] for cell in row) / len(row)
                row_height = max(cell['height'] for cell in row)
                if abs(item['y'] - row_y) <= max(8.0, row_height * 0.7):
                    matched_row = row
                    break
            if matched_row is None:
                rows.append([item])
            else:
                matched_row.append(item)

        formatted_rows = []
        for row in rows:
            cells = sorted(row, key=lambda item: item['x'])
            formatted_rows.append(' | '.join(cell['text'] for cell in cells if cell['text']))
        return '\n'.join(line for line in formatted_rows if line)

    def _run_tesseract_ocr(self, image_data: bytes) -> tuple:
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

    def _build_asset_embedding_text(self, asset) -> str:
        """Build searchable text for an asset embedding."""
        parts = []
        if asset.caption:
            parts.append(f"Mo ta anh: {asset.caption}")
        if asset.ocr_text:
            parts.append(f"OCR trong anh: {asset.ocr_text[:1500]}")
        if asset.context_text:
            parts.append(f"Ngu canh gan anh: {asset.context_text[:2000]}")
        try:
            if asset.chunk_id and asset.chunk and asset.chunk.content:
                parts.append(f"Noi dung doan lien ket: {asset.chunk.content[:2500]}")
        except Exception:
            pass
        if asset.page_number:
            parts.append(f"Trang: {asset.page_number}")
        if asset.paragraph_index is not None:
            parts.append(f"Paragraph: {asset.paragraph_index}")
        return "\n".join(p for p in parts if p).strip() or (asset.caption or "")

    def _embed_asset_caption(self, asset) -> None:
        """Embed caption asset vào Qdrant collection document_assets."""
        try:
            from services.ai.embedding_client import EmbeddingClient
            from services.ai.qdrant_client import QdrantClient

            embedding_client = EmbeddingClient()
            qdrant_client = QdrantClient()

            embedding_text = self._build_asset_embedding_text(asset)
            caption_embedding = embedding_client.create_embedding(embedding_text)
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
