import io
from PIL import Image, ImageDraw
from vision.analyzer import analyze_screenshot


def test_analyze_screenshot():
    # Create a sample screenshot
    image = Image.new("RGB", (700, 120), "white")
    draw = ImageDraw.Draw(image)

    draw.text(
        (20, 35),
        "Your bank account will be blocked today",
        fill="black"
    )

    # Convert image into bytes
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    # Run the complete screenshot analyzer
    result = analyze_screenshot(image_bytes)

    # Check the result
    assert result.source == "screenshot"
    assert isinstance(result.signals, list)

    print("\nSCREENSHOT ANALYSIS RESULT:")
    print(result)