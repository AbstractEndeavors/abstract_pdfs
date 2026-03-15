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
# Failure registry — disk-backed, survives restarts
# ---------------------------------------------------------------------------

class PageFailure(TypedDict):
    page:      int
    strategy:  str        # last strategy attempted
    error:     str        # exception message
    timestamp: str        # ISO-8601


class FailureRegistry:
    """
    Tracks pages that failed all extraction strategies so the repair loop
    doesn't retry them every invocation.

    Backed by a JSON file next to the output tree.  Keyed by page number.
    """

    def __init__(self, base_dir: str):
        self._path = os.path.join(base_dir, "failures.json")
        self._data: Dict[str, PageFailure] = self._load()

    # -- persistence --

    def _load(self) -> Dict[str, PageFailure]:
        if not os.path.isfile(self._path):
            return {}
        try:
            with open(self._path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _flush(self) -> None:
        tmp = self._path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self._data, f, indent=2)
        os.replace(tmp, self._path)

    # -- public API --

    def record(self, page: int, strategy: str, error: Exception) -> None:
        self._data[str(page)] = PageFailure(
            page=page,
            strategy=strategy,
            error=str(error),
            timestamp=datetime.utcnow().isoformat(),
        )
        self._flush()

    def is_failed(self, page: int) -> bool:
        return str(page) in self._data

    def failed_pages(self) -> List[int]:
        return sorted(int(k) for k in self._data)

    def clear_page(self, page: int) -> None:
        self._data.pop(str(page), None)
        self._flush()

    def clear_all(self) -> None:
        self._data.clear()
        self._flush()

    def summary(self) -> Dict[str, PageFailure]:
        return dict(self._data)


# ---------------------------------------------------------------------------
# Image extraction strategies — explicit ordered fallback chain
# ---------------------------------------------------------------------------

def _extract_via_pdf2image_direct(
    pdf_path: str, page_num: int, img_path: str
) -> Optional[str]:
    """
    Render page image directly from the source PDF via pdf2image/Poppler.
    Bypasses PyPDF2's object graph entirely — no recursion risk.
    """
    from pdf2image import convert_from_path

    images = convert_from_path(
        pdf_path,
        first_page=page_num,
        last_page=page_num,
        dpi=200,
    )
    if not images:
        return None

    images[0].save(img_path, "PNG")
    return img_path


def _extract_via_pymupdf(
    pdf_path: str, page_num: int, img_path: str
) -> Optional[str]:
    """
    Render via PyMuPDF (fitz).  Independent PDF parser — handles files
    that choke both PyPDF2 and Poppler.
    """
    import fitz

    doc  = fitz.open(pdf_path)
    page = doc[page_num - 1]             # 0-indexed
    pix  = page.get_pixmap(dpi=200)
    pix.save(img_path)
    doc.close()
    return img_path


def _extract_via_pypdf2_buffer(
    page, page_num: int, img_path: str
) -> Optional[str]:
    """
    Original strategy: serialize single page via PyPDF2 writer, render
    with pdf2image.  Kept as last resort — known to hit recursion depth
    errors on certain PDFs.
    """
    import io
    from pdf2image import convert_from_bytes

    buf    = io.BytesIO()
    writer = PyPDF2.PdfWriter()
    writer.add_page(page)
    writer.write(buf)

    images = convert_from_bytes(buf.getvalue())
    if not images:
        return None

    images[0].save(img_path, "PNG")
    return img_path


# Registry of strategies in attempted order.
# Each entry: (name, callable, requires_page_object)
#   - name:                  logged on failure / stored in failure registry
#   - callable:              the extractor function
#   - requires_page_object:  True → pass (page, page_num, img_path)
#                            False → pass (pdf_path, page_num, img_path)

ImageStrategy = Tuple[str, Callable, bool]

DEFAULT_IMAGE_STRATEGIES: List[ImageStrategy] = [
    ("pdf2image_direct", _extract_via_pdf2image_direct, False),
    ("pymupdf",          _extract_via_pymupdf,          False),
    ("pypdf2_buffer",    _extract_via_pypdf2_buffer,    True),
]


def extract_page_image_with_fallbacks(
    pdf_path:   str,
    page,                           # PyPDF2 page object (only used by legacy strategy)
    page_num:   int,
    img_path:   str,
    strategies: List[ImageStrategy] = None,
    failures:   FailureRegistry     = None,
) -> Optional[str]:
    """
    Walk the strategy chain.  Return path on first success, None if all fail.
    Records terminal failure in the registry when every strategy is exhausted.
    """
    if os.path.exists(img_path):
        return img_path

    strategies = strategies or DEFAULT_IMAGE_STRATEGIES
    last_error: Optional[Exception] = None
    last_name:  str = ""

    for name, fn, needs_page in strategies:
        try:
            if needs_page:
                result = fn(page, page_num, img_path)
            else:
                result = fn(pdf_path, page_num, img_path)

            if result:
                logger.info(f"[{name}] page {page_num:03d} — image extracted")
                return result

        except Exception as exc:
            last_error = exc
            last_name  = name
            logger.warning(f"[{name}] page {page_num:03d} failed: {exc}")
            continue

    # Every strategy exhausted — record permanent failure.
    if failures is not None and last_error is not None:
        failures.record(page_num, last_name, last_error)

    logger.error(f"All image strategies exhausted for page {page_num:03d}")
    return None


# ---------------------------------------------------------------------------
# Completeness report — pure read, no side effects
# ---------------------------------------------------------------------------

PageReport = Dict[str, bool]   # file_key -> exists

def check_all_files(pdf_path: str, base_dir: str = None) -> Dict[int, PageReport]:
    reader   = get_pdf_reader(pdf_path)
    n_pages  = len(reader.pages)
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
    return [i for i, checks in report.items() if not all(checks.values())]


def repairable_pages(
    report:   Dict[int, PageReport],
    failures: FailureRegistry,
) -> List[int]:
    """Pages that are incomplete AND not permanently failed."""
    return [
        i for i, checks in report.items()
        if not all(checks.values()) and not failures.is_failed(i)
    ]


# ---------------------------------------------------------------------------
# PDF reader helper
# ---------------------------------------------------------------------------

def get_pdf_reader(file_path: str) -> PyPDF2.PdfReader:
    return PyPDF2.PdfReader(file_path)


# ---------------------------------------------------------------------------
# Slice Manager
# ---------------------------------------------------------------------------

class SliceManager:
    """Column-aware OCR processor."""

    def __init__(
        self,
        pdf_path:         str,
        out_root:         Optional[str] = None,
        engines                         = "layout_ocr",
        engine_directory: bool          = False,
        visualize:        bool          = None,
        root_url                        = None,
        media_root                      = None,
        pdfs_public_url                 = None,
        image_strategies: List[ImageStrategy] = None,
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

        self.engines          = make_list(engines)
        self.engine_directory = engine_directory or len(self.engines) > 1

        self.reader    = get_pdf_reader(self.pdf_path)
        self.pdf_pages = self.reader.pages

        # Failure registry — shared across engines, persisted to disk
        self.failures = FailureRegistry(self.base_dir)

        # Image extraction fallback chain (caller can override)
        self.image_strategies = image_strategies or DEFAULT_IMAGE_STRATEGIES

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
    # Paddle engine adapter
    # ---------------------------------------------------------

    def _engine_paddle(self, img_path: str, page_num: int, side_label: str):
        return self.process_single_column(
            img_path,
            page_num,
            "paddle",
            side_label,
        )

    # ---------------------------------------------------------
    # Layout OCR engine adapter
    # ---------------------------------------------------------

    def _engine_layout(self, img_path: str, page_num: int, side_label: str):
        from abstract_ocr.layout_ocr.pipeline import run_on_image
        from abstract_ocr.layout_ocr.schemas import PipelineConfig
        from abstract_ocr import clean_text
        from abstract_pdfs import write_to_file

        config = PipelineConfig()
        report = run_on_image(img_path, config=config)

        raw_text = report.result.raw_text
        clean    = clean_text(raw_text)

        txt_name   = f"{self.filename}_page_{page_num:03d}.txt"
        raw_path   = os.path.join(self.text, txt_name)
        clean_path = os.path.join(self.text, f"{self.filename}_page_{page_num:03d}_clean.txt")

        write_to_file(contents=raw_text, file_path=raw_path)
        write_to_file(contents=clean,    file_path=clean_path)

        logger.info(f"[layout_ocr] OCR complete — page {page_num:03d}")
        return raw_text, clean

    # ---------------------------------------------------------
    # Engine dispatch
    # ---------------------------------------------------------

    _ENGINE_MAP = {
        "paddle":     "_engine_paddle",
        "layout_ocr": "_engine_layout",
    }

    def _run_engine(self, img_path: str, page_num: int, engine: str, side_label: str = ""):
        method_name = self._ENGINE_MAP.get(engine)
        if method_name is None:
            raise ValueError(f"Unknown OCR engine: {engine}")
        return getattr(self, method_name)(img_path, page_num, side_label)

    # ---------------------------------------------------------
    # Page image extraction — fallback chain
    # ---------------------------------------------------------

    def extract_page_image(self, page, page_num: int) -> Optional[str]:
        page_str = f"page_{page_num:03d}"
        page_dir = make_dir(self.images, page_str)
        img_path = os.path.join(page_dir, f"{self.filename}_{page_str}.png")

        return extract_page_image_with_fallbacks(
            pdf_path=self.pdf_path,
            page=page,
            page_num=page_num,
            img_path=img_path,
            strategies=self.image_strategies,
            failures=self.failures,
        )

    # ---------------------------------------------------------
    # Completeness
    # ---------------------------------------------------------

    def get_completeness_report(self) -> Dict[int, PageReport]:
        return check_all_files(self.pdf_path, self.base_dir)

    def ensure_complete(self, engine: str) -> None:
        """
        Re-process pages that are missing outputs AND have not permanently
        failed.  Deterministic failures are recorded in the failure
        registry and skipped on subsequent invocations.
        """
        report = self.get_completeness_report()

        if is_complete(report):
            logger.info(f"[{engine}] all pages complete — nothing to repair")
            return

        to_repair = repairable_pages(report, self.failures)
        skipped   = self.failures.failed_pages()

        if skipped:
            logger.info(
                f"[{engine}] skipping {len(skipped)} permanently failed page(s)"
            )

        if not to_repair:
            logger.info(f"[{engine}] no repairable pages remaining")
            return

        logger.info(f"[{engine}] repairing {len(to_repair)} incomplete page(s): {to_repair}")

        for i in to_repair:
            page = self.pdf_pages[i - 1]
            logger.info(f"[{engine}] re-processing page {i:03d}")
            self.process_page(page, i, engine)

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
        txt_path = os.path.join(dirs["raw_tx"],  txt_name)
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
    # Process page
    # ---------------------------------------------------------

    def process_page(self, page, page_num: int, engine: str) -> Dict:
        from abstract_ocr.ocr_utils.column_utils import (
            detect_columns,
            validate_reading_order,
            slice_columns,
        )

        result = {
            "left":  {"raw": {"text": None}, "clean": {"text": None}},
            "right": {"raw": {"text": None}, "clean": {"text": None}},
        }

        img_path = self.extract_page_image(page, page_num)

        if not img_path:
            # extract_page_image already recorded the failure — bail cleanly.
            return result

        try:
            # Layout OCR runs on full page (no column slicing)
            if engine == "layout_ocr":
                txt, cln = self._run_engine(img_path, page_num, engine)
                result["left"]["raw"]["text"]   = txt
                result["left"]["clean"]["text"] = cln
                return result

            # Standard column OCR engines
            divider, _ = detect_columns(img_path)

            validate_reading_order(
                img_path,
                divider,
                visualize=self.visualize,
            )

            left_img  = os.path.join(self.cols, f"{self.filename}_page_{page_num:03d}_left.png")
            right_img = os.path.join(self.cols, f"{self.filename}_page_{page_num:03d}_right.png")

            if os.path.exists(left_img) and os.path.exists(right_img):
                columns = {
                    "left":  {"image": {"path": left_img}},
                    "right": {"image": {"path": right_img}},
                }
            else:
                columns = slice_columns(img_path, divider, self.cols, {})

            for side in ("left", "right"):
                side_path = columns.get(side, {}).get("image", {}).get("path")
                if not side_path:
                    continue
                txt, cln = self._run_engine(side_path, page_num, engine, side)
                result[side]["raw"]["text"]   = txt
                result[side]["clean"]["text"] = cln

        except Exception as e:
            logger.error(f"[{engine}] page {page_num:03d} failed: {e}")
            traceback.print_exc()

        return result

    # ---------------------------------------------------------
    # Per-engine PDF processing
    # ---------------------------------------------------------

    def process_pdf_for_engine(self, engine: str) -> None:
        from abstract_pdfs import write_to_file

        logger.info(f"[{engine}] starting OCR — {self.filename}")

        # Repair incomplete pages (skips permanently failed ones).
        self.ensure_complete(engine)

        dirs       = self.engine_dirs[engine]
        partial    = f"{self.filename}_{engine}"
        left_path  = os.path.join(dirs["raw_tx"], f"{partial}_LEFT.txt")
        right_path = os.path.join(dirs["raw_tx"], f"{partial}_RIGHT.txt")

        self.info_data["dirs"]    = dirs
        self.info_data["partial"] = partial
        self.info_data["texts"]   = {"left": left_path, "right": right_path}
        self.info_data["pages"]   = []

        if os.path.isfile(left_path) and os.path.isfile(right_path):
            logger.info(f"[{engine}] cached — skipping OCR")
            return

        all_left:  List[str] = []
        all_right: List[str] = []

        for i, page in enumerate(self.pdf_pages, start=1):
            # Skip pages we know cannot be processed.
            if self.failures.is_failed(i):
                continue

            res = self.process_page(page, i, engine)

            if res["left"]["raw"]["text"]:
                all_left.append(res["left"]["raw"]["text"])
            if res["right"]["raw"]["text"]:
                all_right.append(res["right"]["raw"]["text"])

            self.info_data["pages"].append({"page": i, "res": res})

        write_to_file(contents="\n\n".join(all_left),  file_path=left_path)
        write_to_file(contents="\n\n".join(all_right), file_path=right_path)

        failed = self.failures.failed_pages()
        if failed:
            logger.warning(
                f"[{engine}] OCR complete with {len(failed)} permanently "
                f"failed page(s): {failed}"
            )
        else:
            logger.info(f"[{engine}] OCR complete")

    # ---------------------------------------------------------
    # Multi-engine entry point
    # ---------------------------------------------------------

    def process_pdf(self, manifest: bool = True) -> Dict:
        logger.info(f"Starting OCR pipeline — {self.filename}")

        for engine in self.engines:
            self.process_pdf_for_engine(engine)

        if manifest:
            generate_pdf_manifest(
                self.pdf_path,
                self.text,
                self.images,
                self.root_url,
                self.media_root,
                self.pdfs_public_url,
            )

        failed = self.failures.failed_pages()
        if failed:
            logger.warning(
                f"OCR pipeline complete — {len(failed)} page(s) permanently "
                f"failed (see {self.failures._path})"
            )
        else:
            logger.info("OCR pipeline complete")

        return self.file_parts
