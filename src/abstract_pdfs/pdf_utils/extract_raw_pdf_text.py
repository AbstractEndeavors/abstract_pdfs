# pdf_pre_ocr_extractor.py

import pdfplumber
from PyPDF2 import PdfReader


# -------------------------
# QUALITY SCORING
# -------------------------
def score_text_quality(text: str) -> float:
    if not text:
        return 0.0

    length = len(text.strip())
    if length == 0:
        return 0.0

    alpha_ratio = sum(c.isalpha() for c in text) / length
    printable_ratio = sum(c.isprintable() for c in text) / length

    words = text.split()
    avg_word_len = (
        sum(len(w) for w in words) / len(words)
        if words else 0
    )

    score = 0
    score += min(alpha_ratio * 2, 1.0)
    score += printable_ratio
    score += min(avg_word_len / 6, 1.0)

    return score / 3


# -------------------------
# CLEANING
# -------------------------
def normalize_text(text: str) -> str:
    if not text:
        return ""

    # normalize whitespace
    text = text.replace("\x00", "")
    text = "\n".join(line.strip() for line in text.splitlines())

    return text


# -------------------------
# EXTRACTION METHODS
# -------------------------
def extract_with_pdfplumber(pdf_path: str):
    pages = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            try:
                text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
            except Exception:
                text = ""

            text = normalize_text(text)
            score = score_text_quality(text)

            pages.append({
                "page_index": i,
                "text": text,
                "score": score,
                "method": "pdfplumber"
            })

    return pages


def extract_with_pypdf2(pdf_path: str):
    reader = PdfReader(pdf_path)
    pages = []

    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""

        text = normalize_text(text)
        score = score_text_quality(text)

        pages.append({
            "page_index": i,
            "text": text,
            "score": score,
            "method": "pypdf2"
        })

    return pages


# -------------------------
# MERGE STRATEGY
# -------------------------
def merge_page_results(pages_a, pages_b):
    merged = []

    for i in range(max(len(pages_a), len(pages_b))):
        pa = pages_a[i] if i < len(pages_a) else None
        pb = pages_b[i] if i < len(pages_b) else None

        if pa and pb:
            best = pa if pa["score"] >= pb["score"] else pb
        else:
            best = pa or pb

        merged.append(best)

    return merged


# -------------------------
# MAIN PIPELINE
# -------------------------
def extract_pdf_pre_ocr(pdf_path: str, page_threshold=0.5, doc_threshold=0.6):
    # dual extraction
    pages_plumber = extract_with_pdfplumber(pdf_path)
    pages_pypdf2 = extract_with_pypdf2(pdf_path)

    merged_pages = merge_page_results(pages_plumber, pages_pypdf2)

    # compute document score
    scores = [p["score"] for p in merged_pages if p["text"].strip()]
    doc_score = sum(scores) / len(scores) if scores else 0

    # determine OCR needs
    ocr_pages = [
        p["page_index"]
        for p in merged_pages
        if p["score"] < page_threshold
    ]

    requires_full_ocr = doc_score < doc_threshold

    return {
        "pages": merged_pages,
        "doc_score": doc_score,
        "ocr_pages": ocr_pages,
        "requires_full_ocr": requires_full_ocr
    }
