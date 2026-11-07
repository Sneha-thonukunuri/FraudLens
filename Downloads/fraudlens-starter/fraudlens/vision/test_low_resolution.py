
import io
from PIL import Image, ImageDraw, ImageFont
from vision.analyzer import inspect_image, extract_text

# Create a normal-quality screenshot
image = Image.new("RGB", (800, 600), "white")
draw = ImageDraw.Draw(image)

font = ImageFont.truetype("arial.ttf", 32)

draw.text(
    (100, 250),
    "Your account statement is ready",
    fill="black",
    font=font
)

# Reduce the image resolution
image = image.resize((200, 150), Image.Resampling.LANCZOS)

# Save the low-resolution screenshot
image.save("vision/low_resolution_screenshot.png")

# Convert image into bytes
buffer = io.BytesIO()
image.save(buffer, format="PNG")
image_bytes = buffer.getvalue()

# Run visual inspection
results = inspect_image(image_bytes)

print("LOW-RESOLUTION TEST RESULTS:")
for result in results:
    print("-", result)

# Run OCR
extracted_text = extract_text(image_bytes)

print("OCR TEXT FROM LOW-RESOLUTION IMAGE:")
print(extracted_text)
assert "Low-resolution screenshot" in results
assert "Your account statement is ready" in extracted_text

print("LOW-RESOLUTION TEST PASSED!")