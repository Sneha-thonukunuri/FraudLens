
import io
from PIL import Image, ImageDraw
from vision.analyzer import inspect_image


def test_normal_screenshot():
    # Create a normal-quality screenshot
    image = Image.new("RGB", (800, 600), "white")
    draw = ImageDraw.Draw(image)
    draw.text((100, 100), "Your account statement is ready", fill="black")

    # Convert image into bytes
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    # Run visual inspection
    results = inspect_image(image_bytes)

    # Verify the inspection works
    assert isinstance(results, list)
    assert "Screenshot may be blurry" not in results
