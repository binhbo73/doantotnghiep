"""
VL Caption Client - Gọi Qwen2.5-VL qua llama.cpp multimodal API
=================================================================

Sử dụng llama.cpp server với mmproj để chạy Qwen2.5-VL-3B.
API endpoint: http://llama-vl-server:8081/v1/chat/completions

Định dạng multimodal message của llama.cpp:
{
    "role": "user",
    "content": [
        {"type": "text", "text": "Mô tả ảnh này"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
    ]
}
"""

import base64
import logging
import time
import requests
from typing import List, Dict, Optional, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class VLCaptionClient:
    """
    Client gọi Qwen2.5-VL-3B qua llama.cpp multimodal API để tạo caption cho ảnh.

    Cấu hình (settings.py):
        VL_MODEL_BASE_URL = "http://llama-vl-server:8081/v1"
        VL_MODEL_NAME = "Qwen2.5-VL-3B-Instruct"
        VL_MODEL_TIMEOUT = 120
        VL_MODEL_MAX_TOKENS = 256
        VL_MODEL_TEMPERATURE = 0.3
    """

    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        timeout: int = None,
        max_tokens: int = None,
        temperature: float = None,
    ):
        self.base_url = base_url or getattr(settings, 'VL_MODEL_BASE_URL', 'http://llama-vl-server:8081/v1')
        self.model = model or getattr(settings, 'VL_MODEL_NAME', 'Qwen2.5-VL-3B-Instruct')
        self.timeout = timeout or getattr(settings, 'VL_MODEL_TIMEOUT', 120)
        self.max_tokens = max_tokens or getattr(settings, 'VL_MODEL_MAX_TOKENS', 256)
        self.temperature = temperature or getattr(settings, 'VL_MODEL_TEMPERATURE', 0.3)
        self._available = None  # cache health check

    def is_available(self) -> bool:
        """Kiểm tra VL model server có sẵn sàng không."""
        if self._available is not None:
            return self._available
        try:
            resp = requests.get(f"{self.base_url}/models", timeout=5)
            self._available = resp.status_code == 200
        except Exception:
            self._available = False
        return self._available

    def generate_caption(
        self,
        image_data: bytes,
        image_format: str = 'png',
        context_text: str = '',
        location_hint: str = '',
        language: str = 'vi',
    ) -> Optional[str]:
        """
        Gửi ảnh tới Qwen2.5-VL để tạo caption mô tả nội dung ảnh.

        Args:
            image_data: Bytes của ảnh
            image_format: 'png', 'jpg', ...
            context_text: Text xung quanh ảnh trong tài liệu
            location_hint: Gợi ý vị trí (vd: "Sheet Biểu mẫu, cell G9")
            language: Ngôn ngữ caption ('vi' hoặc 'en')

        Returns:
            Caption text hoặc None nếu thất bại
        """
        if not self.is_available():
            logger.warning("VL model server not available, skipping caption generation")
            return None

        # ── Encode ảnh base64 ──
        mime_type = f"image/{image_format}"
        if image_format == 'jpg':
            mime_type = 'image/jpeg'
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        data_uri = f"data:{mime_type};base64,{image_b64}"

        # ── Tạo prompt ──
        prompt = self._build_prompt(context_text, location_hint, language)

        # ── Tạo message multimodal ──
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            }
        ]

        # ── Gọi API ──
        try:
            t_start = time.monotonic()

            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "stream": False,
                },
                timeout=self.timeout,
            )

            elapsed_ms = (time.monotonic() - t_start) * 1000

            if resp.status_code == 200:
                result = resp.json()
                if "choices" in result and len(result["choices"]) > 0:
                    caption = result["choices"][0]["message"]["content"].strip()
                    logger.info(
                        f"VL caption generated: {len(caption)} chars, time={elapsed_ms:.0f}ms"
                    )
                    return caption
                else:
                    logger.warning(f"VL API returned no choices: {result}")
                    return None
            else:
                logger.warning(
                    f"VL API error {resp.status_code}: {resp.text[:300]}"
                )
                return None

        except requests.Timeout:
            logger.error(f"VL model timeout after {self.timeout}s")
            return None
        except Exception as e:
            logger.error(f"VL caption generation failed: {e}")
            return None

    def _build_prompt(
        self, context_text: str, location_hint: str, language: str
    ) -> str:
        """Tạo prompt cho VL model, ưu tiên thị giác hơn ngữ cảnh."""

        if language == 'vi':
            prompt = (
               "Bạn là hệ thống tạo caption ảnh cho RAG. Hãy quan sát kỹ ảnh và mô tả chính xác những gì thực sự nhìn thấy.\n"
                "Chỉ trả về một đoạn mô tả hoàn chỉnh bằng tiếng Việt có dấu. Không đánh số, không dùng tiêu đề, không bullet, không lặp lại yêu cầu.\n\n"
                "Nội dung cần mô tả:\n"
                "- Loại ảnh nếu nhận ra: ảnh chụp, giấy tờ/văn bản, bảng biểu, biểu đồ, giao diện phần mềm, sơ đồ, logo, chữ viết tay, hoặc ảnh minh họa.\n"
                "- Nội dung chính: đối tượng, bố cục, hành động, trạng thái, quan hệ giữa các thành phần.\n"
                "- Chữ/số/ký hiệu đọc được: tiêu đề, nhãn, tên riêng, ngày tháng, số liệu, nút bấm, cột/hàng, con dấu.\n"
                "- Với bảng/biểu đồ/giao diện: nêu tên thành phần, nhãn chính, dữ liệu nổi bật và chức năng nếu nhìn thấy rõ.\n"
                "- Với giấy tờ: nêu loại giấy tờ, tiêu đề, tên người/tổ chức, ngày tháng, mã số, chữ ký hoặc con dấu nếu đọc được.\n"
                "- Nếu ảnh bị mờ, xoay, cắt mất, hoặc chữ không đọc rõ, hãy nói rõ phần nào không đọc rõ thay vì đoán.\n"
                "- Không bịa thông tin không có trong ảnh. Không dùng ngữ cảnh bên ngoài để thay thế nội dung thị giác.\n\n"
                "Độ dài: 2-4 câu, đủ chi tiết để người dùng tìm lại ảnh bằng từ khóa."
            )
        else:
            prompt = (
             "You are the image caption generation system for RAG. Please observe the image carefully and accurately describe what you actually see."
            "Return only a complete description in Vietnamese with diacritics. No numbering, no titles, no bullet points, and no repetition of requests."
            "Content to describe:"
            "- Image type if recognized: photograph, document/text, table, chart, software interface, diagram, logo, handwriting, or illustration."
            "- Main content: object, layout, action, state, relationship between components."
            "- Readable letters/numbers/symbols: title, label, proper name, date, data, button, column/row, seal."
            "- For tables/charts/interfaces: state the component name, main label, prominent data, and function if clearly visible."
            "- For documents: state the type of document, Title, name of person/organization, date, code number, signature or seal if legible."
            "- If the image is blurry, rotated, cropped, or the text is illegible, specify which parts are unclear instead of guessing."
            "- Do not fabricate information not present in the image. Do not use external context to replace visual content."
            "Length: 2-4 sentences, detailed enough for users to find the image using keywords."
            )

        # ── Thêm context như một gợi ý phụ, không phải nguồn chính ──
        if location_hint:
            prompt += f"\nVị trí đính kèm: {location_hint}."

        if context_text:
            context_short = context_text[:300].replace('\n', ' ')
            prompt += (
                f"\nGợi ý ngữ cảnh (CHỈ DÙNG THAM KHẢO): {context_short}\n"
                "Nếu nội dung ảnh khác với gợi ý ngữ cảnh này, hãy TIN VÀO MẮT MÌNH."
            )

        return prompt

    def generate_batch_captions(
        self,
        assets: List[Dict[str, Any]],
        max_batch: int = 10,
    ) -> List[Optional[str]]:
        """
        Tạo caption cho nhiều ảnh (xử lý tuần tự, không song song vì VL model nặng).

        Args:
            assets: List[dict] asset data từ AssetExtractor
            max_batch: Số lượng tối đa

        Returns:
            List[str | None] caption theo thứ tự assets
        """
        captions = []
        for idx, asset in enumerate(assets[:max_batch]):
            caption = self.generate_caption(
                image_data=asset.get('image_data', b''),
                image_format=asset.get('image_format', 'png'),
                context_text=asset.get('context_text', ''),
                location_hint=self._build_location_hint(asset),
            )
            captions.append(caption)

            # Delay nhẹ giữa các request để tránh quá tải
            if idx < len(assets[:max_batch]) - 1:
                time.sleep(0.5)

        return captions

    @staticmethod
    def _build_location_hint(asset: Dict[str, Any]) -> str:
        """Tạo mô tả vị trí ngắn gọn cho ảnh."""
        parts = []
        if asset.get('sheet_name'):
            parts.append(f"Sheet {asset['sheet_name']}")
        if asset.get('anchor_cell'):
            parts.append(f"ô {asset['anchor_cell']}")
        if asset.get('page_number'):
            parts.append(f"trang {asset['page_number']}")
        if asset.get('paragraph_index') is not None:
            parts.append(f"đoạn {asset['paragraph_index'] + 1}")
        return ', '.join(parts) if parts else 'tài liệu'
