
import io
from PIL import Image, ImageDraw
from vision.analyzer import inspect_image

# Create a normal-quality screenshot
image = Image.new("RGB", (800, 600), "white")
draw = ImageDraw.Draw(image)
from PIL import ImageFont

font = ImageFont.truetype("arial.ttf", 32)

draw.text(
    (100, 200),
    "Your account statement is ready",
    fill="black",
    font=font
)

# Crop the image
width, height = image.size
image = image.crop((
    100,
    150,
    750,
    350
))
image.save("vision/cropped_screenshot.png")
print("Cropped image saved successfully!")
print("Original image size:", width, height)
print("Cropped image size:", image.size)

# Convert image into bytes
buffer = io.BytesIO()
image.save(buffer, format="PNG")
image_bytes = buffer.getvalue()

# Run visual inspection
results = inspect_image(image_bytes)

print("CROPPED SCREENSHOT TEST RESULTS:")
for result in results:
    print("-", result)
from vision.analyzer import extract_text

cropped_text = extract_text(image_bytes)

print("OCR TEXT FROM CROPPED IMAGE:")
print(cropped_text)