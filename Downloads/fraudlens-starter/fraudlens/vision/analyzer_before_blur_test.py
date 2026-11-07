
import io
import cv2
import numpy as np

from PIL import Image
from common.schema import AnalysisResult
from nlp.analyzer import analyze_text


def extract_text(image_bytes: bytes) -> str:
    try:
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        )

        image = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(image)

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
        elif sharpness < 80:
            signals.append("Screenshot may be blurry")

        detector = cv2.QRCodeDetector()
        qr_text, points, _ = detector.detectAndDecode(image_array)

        if points is not None:
            signals.append("QR code detected in screenshot")

            if qr_text:
                signals.append("QR code contains an encoded destination")

        return signals

    except Exception as e:
        print(f"Image inspection error: {e}")
        return ["Image quality inspection unavailable"]


def analyze_screenshot(image_bytes: bytes) -> AnalysisResult:
    text = extract_text(image_bytes)
    visual_signals = inspect_image(image_bytes)

    if not text.strip():
        return AnalysisResult(
            source="screenshot",
            signals=visual_signals + ["No text extracted by OCR"],
            explanation=(
                "No readable text was extracted. "
                "Image quality and QR-code checks were performed "
                "where possible."
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
                result.explanation
                + " Visual inspection: "
                + (
                    ", ".join(visual_signals)
                    if visual_signals
                    else "No additional visual indicators detected."
                )
            )
        }
    )
