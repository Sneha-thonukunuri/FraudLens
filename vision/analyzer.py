
import io
import os
import cv2
import numpy as np

from PIL import Image, ImageFilter, ImageOps
from common.schema import AnalysisResult
from nlp.analyzer import analyze_text
from dotenv import load_dotenv
from google import genai
from google.genai import types
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

WINDOWS_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def _configure_tesseract(pytesseract) -> None:
    """Use TESSERACT_CMD from the environment if set, else the default Windows
    install path if it exists, else rely on `tesseract` being on PATH."""
    cmd = os.environ.get("TESSERACT_CMD")
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd
    elif os.path.exists(WINDOWS_TESSERACT):
        pytesseract.pytesseract.tesseract_cmd = WINDOWS_TESSERACT


def extract_text(image_bytes: bytes) -> str:
    try:
        import pytesseract

        _configure_tesseract(pytesseract)

        # Open screenshot
        image = Image.open(io.BytesIO(image_bytes))

        # Convert to grayscale
        image = image.convert("L")

        # Increase image size
        image = image.resize(
            (image.width * 2, image.height * 2)
        )

        # Improve contrast
        image = ImageOps.autocontrast(image)

        # Improve sharpness
        image = image.filter(
            ImageFilter.SHARPEN
        )

        # Extract text using OCR
        extracted_text = pytesseract.image_to_string(
            image,
            config="--oem 3 --psm 6"
        )

        return extracted_text.strip()

    except Exception as e:
        print(f"OCR error: {e}")
        return ""


def inspect_image(image_bytes: bytes) -> list:
    signals = []

    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_array = np.array(image)

        height, width = image_array.shape[:2]

        if width < 400 or height < 300:
            signals.append("Low-resolution screenshot")

        gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
        sharpness = cv2.Laplacian(
            gray, cv2.CV_64F
        ).var()

        contrast = gray.std()
        if contrast < 5:
            signals.append("Screenshot has very low visual detail")
        if sharpness < 80:
            signals.append("Screenshot may be blurry")

        detector = cv2.QRCodeDetector()
        qr_text, points, _ = detector.detectAndDecode(image_array)

        if points is not None and len(points) > 0:
            signals.append("QR code detected in screenshot")

            if qr_text:
                signals.append("QR code contains encoded content")

            if qr_text.startswith(("http://", "https://")):
                signals.append("QR code contains a URL")

        return signals

    except Exception as e:
        print(f"Image inspection error: {e}")
        return ["Image quality inspection unavailable"]

def analyze_image_with_gemini(image_bytes: bytes) -> str:
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image_format = image.format.lower()

        mime_type = {
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp"
        }.get(image_format, "image/png")

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type
                ),
                """
                Analyze this screenshot for possible fraud.

                Look for:
                1. Fake or suspicious logos.
                2. Impersonation of banks or companies.
                3. Fake website or payment layouts.
                4. Suspicious QR codes.
                5. Visual signs of phishing.

                Explain the visual evidence you find.
                Do not assume an image is fraudulent without evidence.
                """
            ]
        )
        
        return response.text or "Gemini returned no analysis."

    except Exception as e:
        print(f"Gemini image analysis error: {e}")
        return "Gemini image analysis unavailable."
def analyze_screenshot(image_bytes: bytes) -> AnalysisResult:
    text = extract_text(image_bytes)
    visual_signals = inspect_image(image_bytes)
    
    gemini_analysis = analyze_image_with_gemini(image_bytes)
    if not text.strip():
        return AnalysisResult(
            source="screenshot",
            signals=visual_signals + ["No text extracted by OCR"],
           explanation=(
                "No readable text was extracted. "
                "Image quality and QR-code checks were performed "
                "where possible. "
                "Gemini visual analysis: " + gemini_analysis
            )
        )

    result = analyze_text(text)

    return result.model_copy(
        update={
            "source": "screenshot",
            "signals": (
                result.signals
                + ["Text extracted via OCR"]
                + visual_signals
            ),
            "explanation": (
                result.explanation + " Gemini visual analysis: " + gemini_analysis
                + " Visual inspection: "
                + (
                    ", ".join(visual_signals)
                    if visual_signals
                    else "No additional visual indicators detected."
                )
            )
        }
    )
