import io
import qrcode
from vision.analyzer import inspect_image

# Create a sample QR code
qr = qrcode.make("https://example.com/verify-account")

# Convert QR code into image bytes
buffer = io.BytesIO()
qr.save(buffer, format="PNG")
image_bytes = buffer.getvalue()

# Run visual inspection
results = inspect_image(image_bytes)

print("QR CODE TEST RESULTS:")
for result in results:
    print("-", result)