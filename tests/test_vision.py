"""Vision analyzer tests. Images are generated in memory (no font files, no disk writes)."""
import io
import shutil

import pytest
from PIL import Image, ImageDraw, ImageFilter

from vision.analyzer import analyze_screenshot, inspect_image

needs_tesseract = pytest.mark.skipif(
    shutil.which("tesseract") is None, reason="Tesseract binary not installed")


def _png(image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _text_image(size=(800, 600), text="Your account statement is ready"):
    img = Image.new("RGB", size, "white")
    ImageDraw.Draw(img).text((100, 100), text, fill="black")
    return img


def test_normal_screenshot_not_flagged_blurry():
    results = inspect_image(_png(_text_image()))
    assert "Screenshot may be blurry" not in results


def test_blurry_screenshot_flagged():
    img = _text_image(text="Your bank account will be blocked today")
    results = inspect_image(_png(img.filter(ImageFilter.GaussianBlur(radius=5))))
    assert "Screenshot may be blurry" in results


def test_low_resolution_flagged():
    img = _text_image().resize((200, 150), Image.Resampling.LANCZOS)
    assert "Low-resolution screenshot" in inspect_image(_png(img))


def test_cropped_image_still_inspected():
    img = _text_image().crop((100, 50, 750, 250))
    assert isinstance(inspect_image(_png(img)), list)


def test_qr_code_with_url_detected():
    qrcode = pytest.importorskip("qrcode")
    qr = qrcode.make("https://example.com/verify-account")
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    results = inspect_image(buf.getvalue())
    assert "QR code detected in screenshot" in results
    assert "QR code contains encoded content" in results
    assert "QR code contains a URL" in results


def test_garbage_bytes_do_not_crash():
    r = analyze_screenshot(b"not an image")
    assert r.source == "screenshot"
    assert r.score == 0.0


@needs_tesseract
def test_ocr_text_reaches_text_analyzer():
    img = Image.new("RGB", (900, 200), "white")
    ImageDraw.Draw(img).text((20, 80), "Your bank account will be blocked today", fill="black")
    r = analyze_screenshot(_png(img))
    assert r.source == "screenshot"
    assert "Text extracted via OCR" in r.signals
