"""Private KAOS chart screenshot inspection. No execution or forecast authority.

The upload is decoded, stripped of metadata, resized and converted to a safe
raster before being sent to the configured vision provider. The result only
describes visible evidence. Images are never persisted by this module.
"""
from io import BytesIO
import json
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD = 4 * 1024 * 1024
MAX_PIXELS = 16_000_000
MAX_SIDE = 2048
ALLOWED_FORMATS = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
DIRECTIONS = {"BULLISH", "BEARISH", "NEUTRAL", "INSUFFICIENT_DATA"}

SCHEMA = {
    "type": "object",
    "properties": {
        "directional_bias": {"type": "string", "enum": sorted(DIRECTIONS)},
        "visible_timeframe": {"type": "string"},
        "visible_symbol": {"type": "string"},
        "trend": {"type": "string"},
        "visible_patterns": {"type": "array", "items": {"type": "string"}},
        "support_levels": {"type": "array", "items": {"type": "string"}},
        "resistance_levels": {"type": "array", "items": {"type": "string"}},
        "bullish_scenario": {"type": "string"},
        "bearish_scenario": {"type": "string"},
        "invalidation": {"type": "string"},
        "limitations": {"type": "array", "items": {"type": "string"}},
        "needs_live_data_verification": {"type": "boolean"},
    },
    "required": [
        "directional_bias","visible_timeframe","visible_symbol","trend",
        "visible_patterns","support_levels","resistance_levels",
        "bullish_scenario","bearish_scenario","invalidation","limitations",
        "needs_live_data_verification"
    ],
    "additionalProperties": False,
}


def sanitize_chart_image(data, content_type):
    if not isinstance(data, bytes) or not 1 <= len(data) <= MAX_UPLOAD:
        raise ValueError("Upload must be between 1 byte and 4 MB")
    if content_type not in ALLOWED_FORMATS.values():
        raise ValueError("Only PNG, JPEG and WebP screenshots are supported")
    try:
        with Image.open(BytesIO(data)) as source:
            if source.format not in ALLOWED_FORMATS:
                raise ValueError("Unsupported image encoding")
            if ALLOWED_FORMATS[source.format] != content_type:
                raise ValueError("Image MIME type does not match the image")
            if source.width < 200 or source.height < 150:
                raise ValueError("Chart screenshot is too small")
            if source.width * source.height > MAX_PIXELS:
                raise ValueError("Chart screenshot exceeds pixel limits")
            source.load()
            corrected = ImageOps.exif_transpose(source)
            corrected.thumbnail((MAX_SIDE, MAX_SIDE))
            # New raster object drops metadata and unknown chunks/EXIF/ICC.
            canvas = Image.new("RGB", corrected.size, "white")
            if corrected.mode in ("RGBA", "LA"):
                rgba = corrected.convert("RGBA")
                canvas.paste(rgba, mask=rgba.getchannel("A"))
            else:
                canvas.paste(corrected.convert("RGB"))
            out = BytesIO()
            canvas.save(out, format="PNG", optimize=True)
            return out.getvalue(), "image/png"
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Image could not be safely decoded") from exc


def validate_chart_result(value):
    if not isinstance(value, dict) or set(value) != set(SCHEMA["required"]):
        raise ValueError("Unexpected vision response format")
    if value["directional_bias"] not in DIRECTIONS:
        raise ValueError("Invalid visual assessment")
    for key in ("visible_timeframe","visible_symbol","trend","bullish_scenario",
                "bearish_scenario","invalidation"):
        if not isinstance(value[key], str) or len(value[key]) > 1500:
            raise ValueError("Invalid chart text field")
    for key in ("visible_patterns","support_levels","resistance_levels","limitations"):
        arr = value[key]
        if not isinstance(arr, list) or len(arr) > 20 or any(
            not isinstance(t, str) or len(t) > 240 for t in arr
        ):
            raise ValueError("Invalid chart evidence list")
    if type(value["needs_live_data_verification"]) is not bool:
        raise ValueError("Invalid verification status")
    return value


def extract_response_json(payload):
    for message in payload.get("output", []):
        if message.get("type") != "message":
            continue
        for item in message.get("content", []):
            if item.get("type") == "output_text":
                return validate_chart_result(json.loads(item["text"]))
    raise ValueError("Vision model did not return analysis")
