from typing import Any, Dict, Optional


def perform_ocr(data: bytes) -> Optional[Dict[str, Any]]:
    """Attempt simple OCR on the given image bytes.

    Returns a dictionary of extracted text if OCR libraries are available.
    """
    try:
        import pytesseract
        from PIL import Image
        import io
    except Exception:
        return None

    try:
        image = Image.open(io.BytesIO(data))
        text = pytesseract.image_to_string(image)
        return {"text": text}
    except Exception:
        return None
