"""KAOS chart-image security and structured-output contract tests."""
import json
from io import BytesIO
import pytest
from PIL import Image
from kaos_chart_image import (
    sanitize_chart_image, validate_chart_result, extract_response_json,
    MAX_UPLOAD,
)

def image_bytes(fmt="PNG", size=(600,400)):
    picture=Image.new("RGB",size,"white")
    out=BytesIO()
    picture.save(out,format=fmt)
    return out.getvalue()

def test_png_accepted_and_metadata_not_preserved():
    raw=image_bytes()
    clean,mime=sanitize_chart_image(raw,"image/png")
    assert mime=="image/png"
    with Image.open(BytesIO(clean)) as img:
        assert img.size==(600,400)
        assert img.info=={}

def test_jpeg_converted_to_png():
    clean,mime=sanitize_chart_image(image_bytes("JPEG"),"image/jpeg")
    assert clean[:8]==b"\x89PNG\r\n\x1a\n"
    assert mime=="image/png"

def test_bad_content_rejected():
    with pytest.raises(ValueError):
        sanitize_chart_image(b"not an image","image/png")
    with pytest.raises(ValueError):
        sanitize_chart_image(image_bytes(),"image/jpeg")
    with pytest.raises(ValueError):
        sanitize_chart_image(image_bytes(),"text/plain")
    with pytest.raises(ValueError):
        sanitize_chart_image(b"x"*(MAX_UPLOAD+1),"image/png")

def test_tiny_chart_rejected():
    with pytest.raises(ValueError):
        sanitize_chart_image(image_bytes(size=(100,100)),"image/png")

def valid_result():
    return {
        "directional_bias":"INSUFFICIENT_DATA",
        "visible_timeframe":"unknown","visible_symbol":"unknown",
        "trend":"no readable candles","visible_patterns":[],
        "support_levels":[],"resistance_levels":[],
        "bullish_scenario":"Insufficient evidence",
        "bearish_scenario":"Insufficient evidence",
        "invalidation":"Cannot be determined",
        "limitations":["Static screenshot"],"needs_live_data_verification":True,
    }

def test_model_output_requires_exact_schema():
    correct=valid_result()
    assert validate_chart_result(correct)==correct
    with pytest.raises(ValueError):
        validate_chart_result({**correct,"order":"BUY"})
    with pytest.raises(ValueError):
        validate_chart_result({**correct,"directional_bias":"BUY"})
    with pytest.raises(ValueError):
        validate_chart_result({**correct,"visible_patterns":[1]})

def test_response_extraction():
    data={"output":[{"type":"message","content":[
        {"type":"output_text","text":json.dumps(valid_result())}
    ]}]}
    assert extract_response_json(data)["directional_bias"]=="INSUFFICIENT_DATA"
    with pytest.raises(ValueError):
        extract_response_json({"output":[]})
