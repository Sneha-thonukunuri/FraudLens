
import io
from PIL import Image, ImageDraw, ImageFilter
from vision.analyzer import inspect_image


def test_blurry_screenshot():
    # Create a screenshot with text
    image = Image.new("RGB", (800, 600), "white")
    draw = ImageDraw.Draw(image)
    draw.text((100, 100), "Your bank account will be blocked today", fill="black")

    # Make the screenshot blurry
    image = image.filter(ImageFilter.GaussianBlur(radius=5))

    # Convert image into bytes
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    # Run visual inspection
    results = inspect_image(image_bytes)

    # Verify blur is detected
    assert isinstance(results, list)
    assert "Screenshot may be blurry" in results
