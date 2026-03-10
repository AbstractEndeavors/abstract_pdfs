from .imports import *
def find_closest_pdf(directory: str) -> Optional[str]:
    """
    Locate the most likely PDF inside a directory tree.

    Preference:
      1. PDF whose stem matches the directory name.
      2. Shallowest PDF found.
    """
    directory = os.path.abspath(directory)
    target    = os.path.basename(directory).lower().replace(" ", "_")

    closest_pdf   = None
    closest_depth = float("inf")

    for root, _, files in os.walk(directory):
        depth = root[len(directory):].count(os.sep)
        for pdf in (f for f in files if f.lower().endswith(".pdf")):
            base = os.path.splitext(pdf)[0].lower().replace(" ", "_")
            if base == target:
                return os.path.join(root, pdf)
            if depth < closest_depth:
                closest_depth = depth
                closest_pdf   = os.path.join(root, pdf)

    return closest_pdf


# ---------------------------------------------------------
# Directory Normalization
# ---------------------------------------------------------

def ensure_pdf_directory(
    pdf_item: str,
    out_root: Optional[str] = None,
) -> Dict:
    """
    Guarantee that a PDF lives inside a directory with the same stem.
    Returns a file_parts dict for the canonical PDF location.
    """
    # If given a directory, hunt for the PDF inside it.
    if os.path.isdir(pdf_item):
        found = find_closest_pdf(pdf_item)
        if not found:
            raise RuntimeError(f"No PDF found in directory: {pdf_item}")
        return get_file_parts(found)

    # BUG FIX: removed three `input(...)` debug calls that were left in.
    # BUG FIX: removed duplicate normalize_pdf_path — called once, used consistently.
    file_parts = normalize_pdf_path(pdf_item)
    pdf_item   = file_parts.get("file_path")
    ext        = file_parts.get("ext")

    if not pdf_item or not os.path.isfile(pdf_item) or ext != ".pdf":
        raise RuntimeError(f"Invalid PDF path: {pdf_item}")

    dirname  = file_parts.get("dirname")
    basename = file_parts.get("basename")
    base_dir = out_root or dirname

    os.makedirs(base_dir, exist_ok=True)

    new_pdf = os.path.join(base_dir, os.path.basename(pdf_item))
    if pdf_item != new_pdf:
        shutil.copy(pdf_item, new_pdf)

    return get_file_parts(new_pdf)


def normalize_pdf_path(pdf_path):
    """
    Ensure the PDF lives inside a directory of the same name.

    If dirname == filename (already co-located):
        e.g. /docs/foo/foo.pdf  →  return as-is
    Otherwise:
        create /dirname/filename/ and move the PDF there.
    """
    file_parts = get_file_parts(pdf_path)
    dirname  = file_parts.get("dirname")
    name     = file_parts.get("filename")   # stem, no ext
    dirbase  = file_parts.get("dirbase")    # last segment of dirname
    basename = file_parts.get("basename")   # filename + ext

    # Already inside a same-name directory — nothing to do.
    if dirbase == name:
        pdf_path = os.path.join(dirname, f"{dirbase}.pdf")
        return get_file_parts(pdf_path)

    # Move into a new sibling directory named after the file.
    target_dir = os.path.join(dirname, name)
    new_pdf    = os.path.join(target_dir, basename)

    if not os.path.isdir(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    # BUG FIX: was `shutil.move(str(pdf), ...)` — `pdf` undefined.
    shutil.move(str(pdf_path), str(new_pdf))

    return get_file_parts(str(new_pdf))
