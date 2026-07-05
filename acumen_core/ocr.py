"""
ocr.py - OCR and image extraction helpers for scanned PDFs and figures.
Optional: requires tesseract-ocr, poppler-utils, PyMuPDF, Pillow, pdf2image.
"""

import io

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from PIL import Image
    import pytesseract
except Exception:
    Image = None
    pytesseract = None

try:
    from pdf2image import convert_from_path
except Exception:
    convert_from_path = None


def extract_embedded_images(pdf_path):
    """Extract embedded images from PDF using PyMuPDF."""
    if not fitz:
        return []
    images = []
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)
            for img_idx, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                width = base_image["width"]
                height = base_image["height"]
                if width < 50 or height < 50:
                    continue
                if not Image:
                    continue
                pil_image = Image.open(io.BytesIO(image_bytes))
                images.append({
                    "page_num": page_num + 1,
                    "image_index": img_idx,
                    "pil_image": pil_image,
                    "width": width,
                    "height": height,
                })
        doc.close()
    except Exception:
        pass
    return images


def ocr_pil_image(image):
    """Run pytesseract OCR on a PIL Image, return cleaned text."""
    if not pytesseract or not image:
        return ""
    try:
        gray = image.convert("L")
        text = pytesseract.image_to_string(gray)
        return text.strip()
    except Exception:
        return ""


def describe_image_via_gemini(image):
    """Send image to Gemini Vision for rich description of flowcharts/figures."""
    if not image:
        return ""
    from acumen_core.llm import call_gemini_vision
    prompt = (
        "This is a medical figure or flowchart from a clinical paper. "
        "Transcribe ALL visible text exactly as written. "
        "Then describe the structure: arrows, relationships, decision nodes, "
        "and clinical pathways shown. Be precise and complete."
    )
    return call_gemini_vision(image, prompt)


def fallback_page_ocr(pdf_path):
    """Convert PDF pages to images and OCR each page (scanned PDF fallback)."""
    if not convert_from_path or not pytesseract:
        return ""
    texts = []
    try:
        pages = convert_from_path(pdf_path, dpi=300)
        for page_num, page_image in enumerate(pages, 1):
            text = ocr_pil_image(page_image)
            if text:
                texts.append(f"[Page {page_num}]\n{text}")
    except Exception as e:
        print(f"  Page-level OCR failed: {e}")
    return "\n\n".join(texts)


def extract_figure_text(pdf_path):
    """Extract embedded images, transcribe via OCR or Gemini Vision."""
    images = extract_embedded_images(pdf_path)
    if not images:
        return ""

    figure_texts = []
    for img_info in images:
        page_num = img_info["page_num"]
        pil_image = img_info["pil_image"]
        area = img_info["width"] * img_info["height"]

        if area >= 150000:
            description = describe_image_via_gemini(pil_image)
            if description:
                figure_texts.append(f"[Figure/Flowchart from page {page_num}]\n{description}")
        else:
            text = ocr_pil_image(pil_image)
            if text:
                figure_texts.append(f"[Figure text from page {page_num}]\n{text}")

    return "\n\n".join(figure_texts)
