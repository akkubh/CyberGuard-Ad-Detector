"""
ocr_module.py
─────────────
Extracts text from images (WhatsApp forwards, Facebook ad screenshots,
SMS screenshots) using Tesseract OCR with Indian language support.

Install requirements:
  pip install pytesseract pillow opencv-python-headless
  
Install Tesseract engine:
  Ubuntu/Debian: sudo apt-get install tesseract-ocr tesseract-ocr-hin tesseract-ocr-tam
  Windows:       https://github.com/UB-Mannheim/tesseract/wiki
  Mac:           brew install tesseract tesseract-lang

TECHNICAL NOTE:
Tesseract is an open-source OCR engine originally developed by HP and now
maintained by Google. The 'hin' language pack adds Hindi/Devanagari support,
which is critical for Indian scam content that mixes Hindi and English.
We preprocess images (grayscale → denoise → threshold) before OCR to
dramatically improve accuracy on low-quality WhatsApp screenshots.
"""

import base64
import io
import re
from pathlib import Path

try:
    import pytesseract
    from PIL import Image, ImageFilter, ImageEnhance
    import cv2
    import numpy as np
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def preprocess_image(img: "Image.Image") -> "Image.Image":
    """
    Preprocess image for better OCR accuracy.
    WhatsApp screenshots are often low-res, compressed, and have coloured
    backgrounds — preprocessing normalises them.

    Steps:
      1. Convert to grayscale (removes colour noise)
      2. Increase contrast (makes text pop against background)
      3. Denoise (removes WhatsApp compression artifacts)
      4. Threshold (converts to pure black/white — Tesseract works best on B/W)
    """
    # Convert PIL to OpenCV format
    img_array = np.array(img.convert("RGB"))
    gray      = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

    # Denoise
    denoised  = cv2.fastNlMeansDenoising(gray, h=10)

    # Adaptive threshold — handles uneven lighting
    thresh    = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

    # Scale up small images (Tesseract works better on larger text)
    h, w = thresh.shape
    if w < 800:
        scale  = 800 / w
        thresh = cv2.resize(thresh, (int(w * scale), int(h * scale)),
                            interpolation=cv2.INTER_CUBIC)

    return Image.fromarray(thresh)


def extract_text_from_image(image_data: str | bytes, languages: str = "eng+hin") -> dict:
    """
    Extract text from an image using Tesseract OCR.

    Args:
        image_data: Base64-encoded image string OR raw bytes
        languages:  Tesseract language codes. 'eng+hin' = English + Hindi.
                    Add 'tam' for Tamil, 'tel' for Telugu, etc.

    Returns:
        dict with 'text', 'confidence', 'success', 'error'
    """
    if not OCR_AVAILABLE:
        return {
            "text":       "",
            "confidence": 0,
            "success":    False,
            "error":      "OCR not available. Install: pip install pytesseract pillow opencv-python-headless",
        }

    try:
        # Decode base64 if needed
        if isinstance(image_data, str):
            # Strip data URI prefix if present (data:image/jpeg;base64,...)
            if "," in image_data:
                image_data = image_data.split(",", 1)[1]
            raw_bytes = base64.b64decode(image_data)
        else:
            raw_bytes = image_data

        img = Image.open(io.BytesIO(raw_bytes))

        # Preprocess
        processed = preprocess_image(img)

        # OCR config: PSM 6 = assume uniform block of text (best for ad text)
        config = f"--psm 6 --oem 3 -l {languages}"
        data   = pytesseract.image_to_data(
            processed, config=config,
            output_type=pytesseract.Output.DICT
        )

        # Filter by confidence and join
        words      = [
            data["text"][i]
            for i in range(len(data["text"]))
            if int(data["conf"][i]) > 40 and data["text"][i].strip()
        ]
        text       = " ".join(words).strip()
        confidence = sum(
            int(c) for c in data["conf"] if int(c) > 0
        ) / max(1, sum(1 for c in data["conf"] if int(c) > 0))

        return {
            "text":       text,
            "confidence": round(confidence, 1),
            "success":    bool(text),
            "error":      None,
            "word_count": len(words),
        }

    except Exception as e:
        return {
            "text":       "",
            "confidence": 0,
            "success":    False,
            "error":      str(e),
        }


def extract_text_from_file(file_path: str | Path) -> dict:
    """Convenience wrapper for file paths."""
    with open(file_path, "rb") as f:
        return extract_text_from_image(f.read())
