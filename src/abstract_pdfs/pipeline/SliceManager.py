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
    files exist on disk.  Makes no changes.

    Return shape:
        {
            1: {"thumbnail": True,  "text": False},
            2: {"thumbnail": True,  "text": True},
            ...
        }
    """
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
    """Return page numbers where any expected file is absent."""
    return [i for i, checks in report.items() if not all(checks.values())]


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

        self.engines          = make_list(engines)
        self.engine_directory = engine_directory or len(self.engines) > 1

        self.reader    = get_pdf_reader(self.pdf_path)
        self.pdf_pages = self.reader.pages

        # Directory tree
        self.images = make_dir(self.base_dir, "thumbnails")
        self.text   = make_dir(self.base_dir, "text")
        self.pre    = make_dir(self.base_dir, "preprocessed")
        self.pages  = make_dir(self.pre, "pages")
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
        """
        Return per-page existence checks for every expected output file.
        Delegates to the standalone check_all_files so the logic lives in
        one place and can be called without a SliceManager instance.
        """
        return check_all_files(self.pdf_path, self.base_dir)

    def ensure_complete(self, engine: str) -> None:
        """
        Check every page for missing outputs and re-process only those pages.
        Called at the start of process_pdf_for_engine so partial runs are
        automatically repaired on the next invocation.
        """
        report = self.get_completeness_report()

        if is_complete(report):
            logger.info(f"[{engine}] all pages complete — nothing to repair")
            return

        gaps = missing_pages(report)
        logger.info(f"[{engine}] repairing {len(gaps)} incomplete page(s): {gaps}")

        for i in gaps:
            page = self.pdf_pages[i - 1]   # pages is 0-indexed
            logger.info(f"[{engine}] re-processing page {i:03d}")
            self.process_page(page, i, engine)

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
        img_path:  str,
        page_num:  int,
        engine:    str,
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

        # BUG FIX: removed `input(cln_path)` debug call
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

    def process_page(self, page, page_num: int, engine: str) -> Dict:
        from abstract_ocr.ocr_utils.column_utils import (
            detect_columns, validate_reading_order, slice_columns,
        )

        result = {
            "left":  {"raw": {"text": None}, "clean": {"text": None}},
            "right": {"raw": {"text": None}, "clean": {"text": None}},
        }

        try:
            img_path = self.extract_page_image(page, page_num)
            if not img_path:
                return result

            divider, _ = detect_columns(img_path)
            validate_reading_order(img_path, divider, visualize=self.visualize)
            full_cln_txt_path = os.path.join(self.text, f"{self.filename}_page_{page_num:03d}.txt")
            full_cln_txt = []
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
                txt, cln = self.process_single_column(side_path, page_num, engine, side)
                result[side]["raw"]["text"]   = txt
                result[side]["clean"]["text"] = cln
                full_cln_txt.append(cln)
            write_to_file(contents='\n'.join(full_cln_txt),file_path=full_cln_txt_path)
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

        # Repair any pages from a previous incomplete run before doing anything else.
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

        all_left  = []
        all_right = []

        for i, page in enumerate(self.pdf_pages, start=1):
            res = self.process_page(page, i, engine)

            if res["left"]["raw"]["text"]:
                all_left.append(res["left"]["raw"]["text"])
            if res["right"]["raw"]["text"]:
                all_right.append(res["right"]["raw"]["text"])

            self.info_data["pages"].append({"page": i, "res": res})

        write_to_file(contents="\n\n".join(all_left),  file_path=left_path)
        write_to_file(contents="\n\n".join(all_right), file_path=right_path)

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

        logger.info("OCR pipeline complete")
        return self.file_parts
