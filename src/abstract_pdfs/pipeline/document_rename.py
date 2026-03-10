from .imports import *
def _detect_page_number(name: str):
    m = PAGE_RE.search(name)
    return int(m.group(1)) if m else None


def _zero_page(num: int, width: int = 3) -> str:
    return f"page_{str(num).zfill(width)}"


def _safe_move(src: Path, dst: Path) -> None:
    if src == dst:
        return
    if dst.exists():
        raise RuntimeError(f"Rename collision — destination exists: {dst}")
    shutil.move(str(src), str(dst))


def rename_collection(directory: str, slug: str) -> Path:
    """
    Rename every file inside a processed-PDF directory to carry `slug` as prefix,
    then rename the directory itself.

    Conventions:
      - PDF        → {slug}.pdf
      - Images     → {slug}_{page_NNN}{ext}   (zero-padded to 3 digits)
      - Text files → {slug}_{page_NNN}{ext}
      - Files with no page number in their name are left untouched.

    Returns the new directory path.
    """
    directory = Path(directory)
    parent    = directory.parent
    new_dir   = parent / slug

    if new_dir.exists():
        raise RuntimeError(f"Target directory already exists: {new_dir}")

    pdf_file    = None
    image_files = []
    text_files  = []

    for root, _, files in directory.walk() if hasattr(directory, "walk") else _os_walk(directory):
        for f in files:
            p   = Path(root) / f
            ext = p.suffix.lower()
            if ext in PDF_EXTS:
                pdf_file = p
            elif ext in IMAGE_EXTS:
                image_files.append(p)
            elif ext in TEXT_EXTS:
                text_files.append(p)

    if not pdf_file:
        raise RuntimeError(f"No PDF found in: {directory}")

    # PDF
    _safe_move(pdf_file, pdf_file.with_name(f"{slug}.pdf"))

    # Images
    for img in sorted(image_files):
        page = _detect_page_number(img.name)
        if page is None:
            continue
        _safe_move(img, img.with_name(f"{slug}_{_zero_page(page)}{img.suffix}"))

    # Text
    for txt in sorted(text_files):
        page = _detect_page_number(txt.name)
        if page is None:
            continue
        _safe_move(txt, txt.with_name(f"{slug}_{_zero_page(page)}{txt.suffix}"))

    # Directory last
    _safe_move(directory, new_dir)
    return new_dir


# ---------------------------------------------------------------------------
# compat shim for Python < 3.12 (Path.walk not available)
# ---------------------------------------------------------------------------
import os as _os

def _os_walk(directory: Path):
    for root, dirs, files in _os.walk(directory):
        yield root, dirs, files
