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
                "Bạn là chuyên gia phân tích thị giác. Hãy thực hiện các bước sau nhưng CHỈ TRẢ VỀ nội dung mô tả, không lặp lại các yêu cầu của tôi:\n"
                "1. Xác định loại ảnh: Văn bản/giấy tờ, biểu đồ/giao diện, hay ảnh chụp thực tế?\n"
                "2. Mô tả nội dung THỰC TẾ: \n"
                "   - Nếu là giấy tờ: Đọc tên, ngày tháng, tiêu đề và các thông tin định danh.\n"
                "   - Nếu là biểu đồ/giao diện: Mô tả các thành phần và chức năng chính.\n"
                "   - Nếu là ảnh chụp: Mô tả chủ thể, hành động và bối cảnh.\n"
                "3. Chú ý hướng chữ: Đọc theo đúng chiều của chữ trong ảnh.\n"
                "Lưu ý: Không thêm lời dẫn, không lặp lại yêu cầu. Chỉ trả về kết quả mô tả sạch."
            )
        else:
            prompt = (
                "You are a visual analysis expert. Look closely at this image and describe what you SEE with your own eyes.\n\n"
                "IMPORTANT REQUIREMENTS:\n"
                "1. Only describe the ACTUAL content in the image (people, objects, stamps, text on the image).\n"
                "2. The image might be rotated; try to read text in the correct orientation.\n"
                "3. DO NOT hallucinate content based on surrounding text if the image doesn't show it.\n"
                "4. If you see a red stamp, a person's name, or a document type (certificate, degree), state it clearly.\n"
                "5. Keep it concise (3-4 sentences).\n"
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
