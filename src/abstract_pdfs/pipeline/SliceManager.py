from .imports import *

# ---------------------------------------------------------------------------
# Path helpers — one place, used by both standalone functions and SliceManager
# ---------------------------------------------------------------------------

def get_image_file_path(i: int, pdf_path: str, base_dir: str = None) -> str:
    file_parts = get_file_parts(pdf_path)
    base_dir   = base_dir or file_parts.get("dirname")
    filename   = file_parts.get("filename")
    page_str   = f"page_{i:03d}"
    return os.path.join(base_dir, "thumbnails", page_str, f"{filename}_{page_str}.png")


def get_image_text_path(i: int, pdf_path: str, base_dir: str = None) -> str:
    file_parts = get_file_parts(pdf_path)
    base_dir   = base_dir or file_parts.get("dirname")
    filename   = file_parts.get("filename")
    page_str   = f"page_{i:03d}"
    return os.path.join(base_dir, "text", f"{filename}_{page_str}.txt")


# ---------------------------------------------------------------------------
# Completeness report — pure read, no side effects
# ---------------------------------------------------------------------------

PageReport = Dict[str, bool]   # file_key -> exists

def check_all_files(pdf_path: str, base_dir: str = None) -> Dict[int, PageReport]:
    """
    For every page in the PDF return a dict describing which expected output
    files exist on disk. Makes no changes.

    Return shape:
        {
            1: {"thumbnail": True,  "text": False},
            2: {"thumbnail": True,  "text": True},
            ...
        }
    """
    reader  = get_pdf_reader(pdf_path)
    n_pages = len(reader.pages)
    report: Dict[int, PageReport] = {}

    for i in range(1, n_pages + 1):
        report[i] = {
            "thumbnail": os.path.isfile(get_image_file_path(i, pdf_path, base_dir)),
            "text":      os.path.isfile(get_image_text_path(i, pdf_path, base_dir)),
        }

    return report


def is_complete(report: Dict[int, PageReport]) -> bool:
    return all(all(v.values()) for v in report.values())


def missing_pages(report: Dict[int, PageReport]) -> List[int]:
    """Return page numbers where any expected file is absent."""
    return [i for i, checks in report.items() if not all(checks.values())]


# ---------------------------------------------------------------------------
# PDF reader helper
# ---------------------------------------------------------------------------

def get_pdf_reader(file_path: str) -> PyPDF2.PdfReader:
    return PyPDF2.PdfReader(file_path)


# ---------------------------------------------------------------------------
# PageResult — typed return value for process_page
# Replaces the ad-hoc {"left": {"raw": {"text": None}, ...}} dict.
# Consumers read .full_clean directly rather than navigating nested dicts.
# ---------------------------------------------------------------------------

class PageResult:
    """
    Holds OCR output for one page.

    is_two_column: False means the page was treated as a single block;
                   left_* holds the full text, right_* is empty.
    """
    __slots__ = (
        "page_num", "is_two_column",
        "left_raw", "left_clean",
        "right_raw", "right_clean",
    )

    def __init__(
        self,
        page_num:     int,
        is_two_column: bool = False,
        left_raw:     str = "",
        left_clean:   str = "",
        right_raw:    str = "",
        right_clean:  str = "",
    ):
        self.page_num      = page_num
        self.is_two_column = is_two_column
        self.left_raw      = left_raw
        self.left_clean    = left_clean
        self.right_raw     = right_raw
        self.right_clean   = right_clean

    @property
    def full_clean(self) -> str:
        parts = [p for p in (self.left_clean, self.right_clean) if p]
        return "\n".join(parts)

    @property
    def full_raw(self) -> str:
        parts = [p for p in (self.left_raw, self.right_raw) if p]
        return "\n".join(parts)

    def to_dict(self) -> dict:
        """Serialise to the legacy nested dict shape so existing consumers don't break."""
        return {
            "page":         self.page_num,
            "is_two_column": self.is_two_column,
            "left":  {"raw": {"text": self.left_raw},  "clean": {"text": self.left_clean}},
            "right": {"raw": {"text": self.right_raw}, "clean": {"text": self.right_clean}},
        }


# ---------------------------------------------------------------------------
# Slice Manager
# ---------------------------------------------------------------------------

class SliceManager:
    """Column-aware OCR processor."""

    def __init__(
        self,
        pdf_path:         str,
        out_root:         Optional[str] = None,
        engines                         = "paddle",
        engine_directory: bool          = False,
        visualize:        bool          = None,
        root_url                         = None,
        media_root                       = None,
        pdfs_public_url                  = None,
    ):
        self.root_url        = root_url        or ROOT_URL
        self.media_root      = media_root      or MEDIA_ROOT_DIR
        self.pdfs_public_url = pdfs_public_url or PDFS_ROOT_DIR

        self.file_parts = ensure_pdf_directory(pdf_path, out_root)
        self.pdf_path   = self.file_parts.get("file_path")
        self.base_dir   = self.file_parts.get("dirname")
        self.filename   = self.file_parts.get("filename")
        self.visualize  = visualize
        self.imgs       = []
        self.info_data  = {}

        # FIX (BUG-006): make_list normalises "paddle", "paddle,tesseract",
        # ["paddle"], and ["paddle", "tesseract"] to a clean list.
        self.engines          = make_list(engines)
        self.engine_directory = engine_directory or len(self.engines) > 1

        self.reader    = get_pdf_reader(self.pdf_path)
        self.pdf_pages = self.reader.pages

        # Directory tree
        self.images  = make_dir(self.base_dir, "thumbnails")
        self.text    = make_dir(self.base_dir, "text")
        self.pre     = make_dir(self.base_dir, "preprocessed")
        self.pages   = make_dir(self.pre, "pages")
        self.pre_txt = make_dir(self.pre, "txt")
        self.pre_img = make_dir(self.pre, "img")
        self.cols    = make_dir(self.pre_img, "cols")

        # Per-engine directory map
        self.engine_dirs: Dict[str, Dict] = {}
        for engine in self.engines:
            root = make_dir(self.base_dir, engine) if self.engine_directory else self.base_dir
            self.engine_dirs[engine] = {
                "root":        root,
                "clean_tx":    self.text,
                "pre_img":     make_dir(self.pre_img, "pre"),
                "raw_tx":      make_dir(self.pre_txt, "raw"),
                "pre_txt":     make_dir(self.pre_txt, "pre"),
                "pre_cln":     make_dir(self.pre_txt, "cln"),
                "final_raw":   os.path.join(self.text, f"{self.filename}_{engine}_FULL.txt"),
                "final_clean": os.path.join(self.text, f"{self.filename}_{engine}_FULL_cleaned.txt"),
            }

    # ---------------------------------------------------------
    # Completeness
    # ---------------------------------------------------------

    def get_completeness_report(self) -> Dict[int, PageReport]:
        return check_all_files(self.pdf_path, self.base_dir)

    # FIX (BUG-007 + BUG-003): ensure_complete no longer processes pages itself.
    # It returns the set of page numbers that still need work so the caller
    # (process_pdf_for_engine) can decide whether to run them and capture results.
    def incomplete_pages(self, engine: str) -> List[int]:
        """
        Return page numbers that are missing any expected output file.
        Pure read — no processing. Caller decides what to do with the list.
        """
        report = self.get_completeness_report()
        gaps   = missing_pages(report)
        if gaps:
            logger.info(f"[{engine}] {len(gaps)} incomplete page(s): {gaps}")
        else:
            logger.info(f"[{engine}] all pages complete")
        return gaps

    # ---------------------------------------------------------
    # Page image extraction (no intermediate PDF file)
    # ---------------------------------------------------------

    def extract_page_image(self, page, page_num: int) -> Optional[str]:
        page_str = f"page_{page_num:03d}"
        page_dir = make_dir(self.images, page_str)
        img_path = os.path.join(page_dir, f"{self.filename}_{page_str}.png")

        if os.path.exists(img_path):
            return img_path

        try:
            import io
            from pdf2image import convert_from_bytes

            buf = io.BytesIO()
            writer = PyPDF2.PdfWriter()
            writer.add_page(page)
            writer.write(buf)

            images = convert_from_bytes(buf.getvalue())
            if not images:
                logger.warning(f"No image rendered for page {page_num:03d}")
                return None

            images[0].save(img_path, "PNG")
            return img_path

        except Exception as e:
            logger.error(f"Page extraction failed on {page_num:03d}: {e}")
            return None

    # ---------------------------------------------------------
    # Single-column OCR
    # ---------------------------------------------------------

    def process_single_column(
        self,
        img_path:   str,
        page_num:   int,
        engine:     str,
        side_label: str = "",
    ) -> Tuple[str, str]:
        from abstract_pdfs import write_to_file, read_from_file
        from abstract_ocr.ocr_utils.preprocess import preprocess_image
        from abstract_ocr.ocr_utils.layered_ocr import layered_ocr_img
        from abstract_ocr import clean_text
        import cv2

        dirs     = self.engine_dirs[engine]
        suffix   = f"_{side_label}" if side_label else ""
        txt_name = f"{self.filename}_page_{page_num:03d}{suffix}.txt"
        txt_path = os.path.join(dirs["raw_tx"],   txt_name)
        cln_path = os.path.join(dirs["clean_tx"], txt_name)
        proc_img = os.path.join(dirs["pre_img"],  f"page_{page_num:03d}{suffix}.png")

        if os.path.isfile(txt_path) and os.path.isfile(cln_path):
            return read_from_file(txt_path), read_from_file(cln_path)

        preprocess_image(img_path, proc_img)
        image_array = cv2.imread(proc_img)
        df  = layered_ocr_img(image_array, engine=engine)
        txt = "\n".join(df["text"].tolist())
        write_to_file(contents=txt, file_path=txt_path)

        cln = clean_text(txt)
        write_to_file(contents=cln, file_path=cln_path)

        logger.info(f"[{engine}] OCR complete — page {page_num:03d}{suffix}")
        return txt, cln

    # ---------------------------------------------------------
    # Per-page processing
    # ---------------------------------------------------------

    def process_page(self, page, page_num: int, engine: str) -> PageResult:
        """
        Process one page. Returns a PageResult.

        FIX (BUG-004): validate_reading_order return value is now captured.
        If the page is determined to be single-column, we skip slicing and run
        OCR on the full page image rather than splitting it at the midpoint.

        FIX (BUG-005): slice_columns receives the pre-existing column image dict
        (left_img / right_img paths if they exist) rather than a bare {}.
        """
        from abstract_ocr.ocr_utils.column_utils import (
            detect_columns, validate_reading_order, slice_columns,
        )
        from abstract_pdfs import write_to_file

        empty = PageResult(page_num=page_num)

        try:
            img_path = self.extract_page_image(page, page_num)
            if not img_path:
                return empty

            divider, _meta = detect_columns(img_path)

            # FIX (BUG-004): capture the column verdict
            is_two_column: bool = validate_reading_order(
                img_path, divider, visualize=self.visualize
            )

            full_cln_txt_path = os.path.join(
                self.text, f"{self.filename}_page_{page_num:03d}.txt"
            )

            # ── Single-column path ────────────────────────────────────────────
            # Treat the full page as "left" so full_clean is the complete text.
            if not is_two_column:
                logger.debug(f"page {page_num:03d} — single-column, no split")
                txt, cln = self.process_single_column(img_path, page_num, engine)
                write_to_file(contents=cln, file_path=full_cln_txt_path)
                return PageResult(
                    page_num=page_num,
                    is_two_column=False,
                    left_raw=txt,
                    left_clean=cln,
                )

            # ── Two-column path ───────────────────────────────────────────────
            left_img  = os.path.join(
                self.cols, f"{self.filename}_page_{page_num:03d}_left.png"
            )
            right_img = os.path.join(
                self.cols, f"{self.filename}_page_{page_num:03d}_right.png"
            )

            # FIX (BUG-005): pass existing column images as pre-computed hints
            # so slice_columns can skip re-slicing if they already exist.
            existing_columns: dict = {}
            if os.path.exists(left_img):
                existing_columns["left"]  = {"image": {"path": left_img}}
            if os.path.exists(right_img):
                existing_columns["right"] = {"image": {"path": right_img}}

            columns = (
                existing_columns
                if len(existing_columns) == 2
                else slice_columns(img_path, divider, self.cols, existing_columns)
            )

            left_raw = left_clean = right_raw = right_clean = ""
            full_parts: List[str] = []

            for side, var_raw, var_clean in (
                ("left",  "left_raw",  "left_clean"),
                ("right", "right_raw", "right_clean"),
            ):
                side_path = columns.get(side, {}).get("image", {}).get("path")
                if not side_path:
                    logger.warning(
                        f"[{engine}] page {page_num:03d} — no image for side '{side}'"
                    )
                    continue
                txt, cln = self.process_single_column(side_path, page_num, engine, side)
                if side == "left":
                    left_raw, left_clean = txt, cln
                else:
                    right_raw, right_clean = txt, cln
                if cln:
                    full_parts.append(cln)

            write_to_file(
                contents="\n".join(full_parts), file_path=full_cln_txt_path
            )
            return PageResult(
                page_num=page_num,
                is_two_column=True,
                left_raw=left_raw,
                left_clean=left_clean,
                right_raw=right_raw,
                right_clean=right_clean,
            )

        except Exception as e:
            logger.error(f"[{engine}] page {page_num:03d} failed: {e}")
            traceback.print_exc()
            return empty

    # ---------------------------------------------------------
    # Per-engine PDF processing
    # ---------------------------------------------------------

    def process_pdf_for_engine(self, engine: str) -> None:
        """
        Process all pages for one engine.

        FIX (BUG-007 + BUG-001 + BUG-002 + BUG-003):
        The previous implementation had three interacting flaws:
          1. ensure_complete processed all missing pages, then the main loop
             processed them again → double work on first run.
          2. When LEFT+RIGHT cache files existed, info_data["pages"] was set to []
             and the method returned early → info_data always empty on cache hit.
          3. Pages repaired by ensure_complete never appeared in info_data["pages"].

        New flow:
          1. Determine which pages still need processing (incomplete_pages — pure read).
          2. Reconstruct info_data["pages"] from disk for already-complete pages.
          3. Process only the incomplete pages, appending to info_data["pages"].
          4. Cache check (LEFT+RIGHT files) now happens AFTER info_data is built,
             and only skips the final write-out, not the info_data population.
        """
        from abstract_pdfs import write_to_file, read_from_file

        logger.info(f"[{engine}] starting — {self.filename}")

        dirs    = self.engine_dirs[engine]
        partial = f"{self.filename}_{engine}"
        left_path  = os.path.join(dirs["raw_tx"], f"{partial}_LEFT.txt")
        right_path = os.path.join(dirs["raw_tx"], f"{partial}_RIGHT.txt")

        self.info_data["dirs"]    = dirs
        self.info_data["partial"] = partial
        self.info_data["texts"]   = {"left": left_path, "right": right_path}

        # Build page index: what's already on disk vs what still needs work
        needs_processing: set[int] = set(self.incomplete_pages(engine))
        page_results: Dict[int, PageResult] = {}

        # Reconstruct already-complete pages from disk so info_data is always full
        for i, page in enumerate(self.pdf_pages, start=1):
            if i in needs_processing:
                continue
            page_str  = f"page_{i:03d}"
            page_tag  = f"{self.filename}_{page_str}"
            # Prefer the clean full-page text if it exists
            full_path = os.path.join(self.text, f"{page_tag}.txt")
            full_text = ""
            if os.path.isfile(full_path):
                full_text = read_from_file(full_path)
            page_results[i] = PageResult(
                page_num=i,
                left_clean=full_text,
            )

        # Process only incomplete pages (no double-work)
        all_left:  List[str] = []
        all_right: List[str] = []

        for i, page in enumerate(self.pdf_pages, start=1):
            if i not in needs_processing:
                continue
            logger.info(f"[{engine}] processing page {i:03d}")
            result = self.process_page(page, i, engine)
            page_results[i] = result

        # Combine in page order for the aggregate left/right files
        for i in sorted(page_results):
            r = page_results[i]
            if r.left_raw:
                all_left.append(r.left_raw)
            if r.right_raw:
                all_right.append(r.right_raw)

        # Write aggregate files only if there's new content
        if not os.path.isfile(left_path) or needs_processing:
            write_to_file(contents="\n\n".join(all_left),  file_path=left_path)
            write_to_file(contents="\n\n".join(all_right), file_path=right_path)
        else:
            logger.info(f"[{engine}] aggregate files already current — skipping write")

        # info_data["pages"] is always a complete ordered list of PageResult dicts
        self.info_data["pages"] = [
            page_results[i].to_dict() for i in sorted(page_results)
        ]

        logger.info(
            f"[{engine}] complete — {len(page_results)} pages "
            f"({len(needs_processing)} newly processed)"
        )

    # ---------------------------------------------------------
    # Multi-engine entry point
    # ---------------------------------------------------------

    def process_pdf(self, manifest: bool = True) -> Dict:
        logger.info(f"Starting OCR pipeline — {self.filename}")

        for engine in self.engines:
            self.process_pdf_for_engine(engine)

        if manifest:
            # FIX: use keyword args so signature changes don't silently reorder
            from abstract_pdfs.abstract_scaffold.src.generators import generate_pdf_manifest
            generate_pdf_manifest(
                pdf_path=self.pdf_path,
                text_root=self.text,
                thumb_root=self.images,
                base_url=self.root_url,
                media_root=self.media_root,
                pdfs_public_url=self.pdfs_public_url,
            )

        logger.info("OCR pipeline complete")
        return self.file_parts
