
import io
import qrcode

from vision.analyzer import inspect_image


def test_qr_code_detection():
    # Create a sample QR code containing a URL
    qr = qrcode.make("https://example.com")
    
    # Convert QR image into bytes
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    # Run screenshot inspection
    results = inspect_image(image_bytes)

    # Check QR detection
    assert "QR code detected in screenshot" in results
    assert "QR code contains encoded content" in results
    assert "QR code contains a URL" in results

    print("QR CODE TEST PASSED!")
    print(results)
