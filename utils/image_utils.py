# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Image utility functions for processing and converting images
"""

import base64
import io
from fractions import Fraction
from PIL import Image

from utils.log_config import get_logger

logger = get_logger("ImageUtils")


IMAGE_SIZE_PRESET_MAP = {
    "1:1": {"1K": "1280x1280", "2K": "2048x2048", "4K": "2880x2880"},
    "2:3": {"1K": "848x1280", "2K": "1360x2048", "4K": "2336x3520"},
    "3:2": {"1K": "1280x848", "2K": "2048x1360", "4K": "3520x2336"},
    "3:4": {"1K": "960x1280", "2K": "1536x2048", "4K": "2480x3312"},
    "4:3": {"1K": "1280x960", "2K": "2048x1536", "4K": "3312x2480"},
    "4:5": {"1K": "1024x1280", "2K": "1632x2048", "4K": "2560x3216"},
    "5:4": {"1K": "1280x1024", "2K": "2048x1632", "4K": "3216x2560"},
    "9:16": {"1K": "720x1280", "2K": "1152x2048", "4K": "2160x3840"},
    "16:9": {"1K": "1280x720", "2K": "2048x1152", "4K": "3840x2160"},
    "21:9": {"1K": "1280x544", "2K": "2048x864", "4K": "3840x1632"},
}


def detect_image_mime_from_bytes(image_bytes: bytes) -> str:
    """
    Detect MIME type from raw image bytes using file signatures.

    Args:
        image_bytes: Raw image bytes.

    Returns:
        MIME type string, defaults to image/jpeg when unknown.
    """
    if not image_bytes or len(image_bytes) < 12:
        return "image/jpeg"

    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    if image_bytes.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"

    return "image/jpeg"


def detect_image_mime_from_b64(image_b64_str: str) -> str:
    """
    Detect MIME type from base64 encoded image content.

    Args:
        image_b64_str: Base64 image string (without data URL prefix).

    Returns:
        MIME type string, defaults to image/jpeg when unknown.
    """
    try:
        raw_bytes = base64.b64decode(image_b64_str)
    except Exception:
        return "image/jpeg"
    return detect_image_mime_from_bytes(raw_bytes)


def normalize_gemini_image_size(image_size: str, default_size: str = "1K") -> str:
    """
    Normalize Gemini image size value to supported enum: 1K/2K/4K.

    Args:
        image_size: Input image size string.
        default_size: Fallback when input is invalid.

    Returns:
        Normalized image size string.
    """
    normalized = (image_size or "").strip().upper()
    if normalized in {"1K", "2K", "4K"}:
        return normalized
    return default_size


def normalize_gemini_media_resolution(
    image_size: str,
    default_resolution: str = "MEDIA_RESOLUTION_MEDIUM",
) -> str:
    """
    Map a coarse image size hint to the MediaResolution enum names used by
    current google-genai releases.
    """
    normalized = normalize_gemini_image_size(
        image_size,
        default_size="2K" if default_resolution == "MEDIA_RESOLUTION_MEDIUM" else "1K",
    )
    mapping = {
        "1K": "MEDIA_RESOLUTION_LOW",
        "2K": "MEDIA_RESOLUTION_MEDIUM",
        "4K": "MEDIA_RESOLUTION_HIGH",
    }
    return mapping.get(normalized, default_resolution)


def normalize_aspect_ratio(aspect_ratio: str, default_ratio: str = "16:9") -> str:
    """Normalize an aspect ratio string while preserving supported custom ratios."""
    raw_value = str(aspect_ratio or "").strip()
    if ":" not in raw_value:
        return default_ratio
    left, right = raw_value.split(":", 1)
    try:
        width_ratio = int(left.strip())
        height_ratio = int(right.strip())
    except ValueError:
        return default_ratio
    if width_ratio <= 0 or height_ratio <= 0:
        return default_ratio
    if max(width_ratio, height_ratio) / min(width_ratio, height_ratio) > 3:
        return default_ratio
    reduced = Fraction(width_ratio, height_ratio)
    return f"{reduced.numerator}:{reduced.denominator}"


def openai_image_size_from_controls(
    aspect_ratio: str,
    image_resolution: str,
    *,
    default_size: str = "1536x1024",
) -> str:
    """
    Convert UI aspect-ratio and resolution controls to OpenAI Images `size`.

    GPT image models receive concrete pixel dimensions instead of separate
    aspect-ratio/image-size parameters. Returned values obey the documented
    GPT-Image-2 bounds: dimensions are multiples of 16, the longest side is at
    most 3840 px, aspect ratio is at most 3:1, and total pixels stay under
    8,294,400.
    """
    normalized_resolution = str(image_resolution or "").strip().upper()
    raw_ratio = str(aspect_ratio or "").strip()
    mapped_size = IMAGE_SIZE_PRESET_MAP.get(raw_ratio, {}).get(normalized_resolution)
    if mapped_size:
        return mapped_size

    normalized_ratio = normalize_aspect_ratio(aspect_ratio, default_ratio="3:2")
    mapped_size = IMAGE_SIZE_PRESET_MAP.get(normalized_ratio, {}).get(normalized_resolution)
    if mapped_size:
        return mapped_size

    width_ratio, height_ratio = (int(part) for part in normalized_ratio.split(":", 1))

    if normalized_resolution == "4K":
        target_long_edge = 3840
    elif normalized_resolution == "2K":
        target_long_edge = 2048
    elif normalized_resolution == "1K":
        target_long_edge = 1024
    else:
        return default_size

    def _dims_for_long_edge(long_edge: int) -> tuple[int, int]:
        if width_ratio >= height_ratio:
            width = long_edge
            height = round(long_edge * height_ratio / width_ratio)
        else:
            height = long_edge
            width = round(long_edge * width_ratio / height_ratio)
        width = max(16, round(width / 16) * 16)
        height = max(16, round(height / 16) * 16)
        return width, height

    width, height = _dims_for_long_edge(target_long_edge)

    max_pixels = 8_294_400
    min_pixels = 655_360

    while width * height < min_pixels and max(width, height) < 3840:
        target_long_edge = min(3840, target_long_edge + 16)
        width, height = _dims_for_long_edge(target_long_edge)

    while width * height > max_pixels and target_long_edge > 16:
        target_long_edge = max(16, target_long_edge - 16)
        width, height = _dims_for_long_edge(target_long_edge)

    return f"{width}x{height}"


def build_gemini_image_prompt(prompt_text: str, aspect_ratio: str, image_size: str) -> str:
    """
    Append rendering hints directly into the prompt for SDK versions that no
    longer expose ImageConfig.
    """
    return (
        f"{prompt_text}\n\n"
        "Additional rendering requirements:\n"
        f"- Aspect ratio: {aspect_ratio}\n"
        f"- Output resolution preference: {normalize_gemini_image_size(image_size, default_size='2K')}\n"
        "- Return only the rendered image.\n"
    )


def convert_png_b64_to_jpg_b64(png_b64_str: str) -> str:
    """
    Convert a PNG base64 string to a JPG base64 string.
    
    Args:
        png_b64_str: Base64 encoded PNG image string
        
    Returns:
        Base64 encoded JPG image string, or None if conversion fails
    """
    try:
        if not png_b64_str or len(png_b64_str) < 10:
            logger.warning(f"⚠️  base64 字符串无效（过短）: {png_b64_str[:50] if png_b64_str else 'None'}")
            return None
            
        img = Image.open(io.BytesIO(base64.b64decode(png_b64_str))).convert("RGB")
        out_io = io.BytesIO()
        img.save(out_io, format="JPEG", quality=95)
        return base64.b64encode(out_io.getvalue()).decode("utf-8")
    except Exception as e:
        logger.error(f"❌ 图片转换失败: {e}")
        logger.debug(f"   输入预览: {png_b64_str[:100] if png_b64_str else 'None'}")
        return None
