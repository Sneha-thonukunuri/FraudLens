"""MEMBER 2 owns this file.
Currently: OCR (if pytesseract + Tesseract installed) -> Member 1's text analyzer.
TODO (Week 2): send the image to a multimodal LLM for visual cues (fake logos,
spoofed layouts, QR codes) and merge with the OCR-text result."""
import io
from common.schema import AnalysisResult
from nlp.analyzer import analyze_text


def extract_text(image_bytes: bytes) -> str:
    try:
        from PIL import Image
        import pytesseract
        return pytesseract.image_to_string(Image.open(io.BytesIO(image_bytes)))
    except Exception:
        return ""


def analyze_screenshot(image_bytes: bytes) -> AnalysisResult:
    text = extract_text(image_bytes)
    if not text.strip():
        return AnalysisResult(source="screenshot",
                              explanation="[MOCK] No text extracted (OCR unavailable or empty image).")
    r = analyze_text(text)
    return r.model_copy(update={"source": "screenshot",
                                "signals": r.signals + ["text extracted via OCR"]})
