"""Exercise the public image renderer after Pillow security updates."""
from io import BytesIO
from PIL import Image
from routes_trading import _render_share_png


def test_share_image_renders_candles_with_current_pillow():
    result = _render_share_png({'engine': 'Test Strategy', 'direction': 'BUY', 'expiration': 30,
        'confidence': 0.6, 'strategyVersion': 'test', 'triggerPos': 1,
        'candles': [{'open': 1.0, 'high': 1.2, 'low': 0.9, 'close': 1.1},
                    {'open': 1.1, 'high': 1.3, 'low': 1.0, 'close': 1.2}]})
    with Image.open(BytesIO(result)) as image:
        assert image.format == 'PNG'
        assert image.size == (1200, 630)
        image.verify()
