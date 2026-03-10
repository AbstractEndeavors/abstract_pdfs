from .imports import *
from .pdf_utils import pdf_tools, pdf_to_text
from .pipeline import SliceManager

class AbstractPDFManager:
    """
    Central manager for PDF ingestion, deduplication, splitting, OCR conversion, and slice-aware text extraction.
    
    Layers:
      1️⃣ Basic utilities (hashing, splitting, per-page image conversion)
      2️⃣ Directory-oriented bulk conversion (`pdf_to_text_in_folders`)
      3️⃣ Slice-aware column detection via SliceManager
      4️⃣ Manifest-driven persistence

    Example:
        mgr = AbstractPDFManager("/mnt/24T/media/docs/sample.pdf")
        mgr.run_basic_extraction()
        mgr.run_slice_analysis(engine='paddle')
    """

    def __init__(self, pdf_path: str, out_root: Optional[str] = None, engines: Union[str, List[str]] = 'paddle'):
        self.pdf_path = get_pdf_path(pdf_path)
        if not self.pdf_path:
            raise FileNotFoundError(f"❌ Could not locate valid PDF in {pdf_path}")
        self.file_parts = get_file_parts(self.pdf_path)
        self.pdf_dir = self.file_parts.get("dirname")
        
        self.filename = self.file_parts.get("filename")
        self.dirname = self.file_parts.get("dirname")
        self.out_root = out_root or os.path.join(self.dirname, f"{self.filename}_output")
        mkdirs(self.out_root)

        self.engines = make_list(engines)
        self.manifest = load_manifest(pdf_dir=self.pdf_dir)
        logger.info(f"📁 Initialized AbstractPDFManager for {self.filename}")

    # ------------------------------------------------------------
    # ✅ 1. Basic Splitting & Conversion
    # ------------------------------------------------------------
    def split_pdf(self) -> List[str]:
        """Split PDF into individual pages (stored in out_root/pdf_pages)."""
        pdf_pages_dir = os.path.join(self.out_root, "pdf_pages")
        mkdirs(pdf_pages_dir)
        pages = pdf_to_text.split_pdf(self.pdf_path, pdf_pages_dir, self.filename)
        logger.info(f"📄 Split {self.filename} into {len(pages)} pages")
        return pages

    def convert_to_images(self, pdf_pages: Optional[List[str]] = None) -> List[str]:
        """Convert PDF pages into images."""
        pdf_pages = pdf_pages or self.split_pdf()
        images_dir = os.path.join(self.out_root, "images")
        mkdirs(images_dir)

        img_paths = []
        for pdf_page in pdf_pages:
            try:
                images = convert_from_path(pdf_page)
                if not images:
                    continue
                out_path = os.path.join(images_dir, Path(pdf_page).stem + ".png")
                images[0].save(out_path, "PNG")
                img_paths.append(out_path)
            except Exception as e:
                logger.error(f"❌ Error converting {pdf_page} to image: {e}")
        logger.info(f"🖼️ Converted {len(img_paths)} page(s) to PNGs")
        return img_paths

    # ------------------------------------------------------------
    # ✅ 2. Text Extraction (image_to_text)
    # ------------------------------------------------------------
    def extract_text(self, img_paths: Optional[List[str]] = None) -> List[str]:
        """Extract text from images using base OCR."""
        img_paths = img_paths or self.convert_to_images()
        text_dir = os.path.join(self.out_root, "text")
        mkdirs(text_dir)

        extracted = []
        for img in img_paths:
            try:
                txt = image_to_text(img)
                txt_path = os.path.join(text_dir, Path(img).stem + ".txt")
                write_to_file(txt_path, txt)
                extracted.append(txt_path)
            except Exception as e:
                logger.error(f"❌ Error extracting text from {img}: {e}")
        logger.info(f"✍️ Extracted text from {len(extracted)} images")
        return extracted

    # ------------------------------------------------------------
    # ✅ 3. Full Batch (deduplication + per-folder extraction)
    # ------------------------------------------------------------
    def run_batch_extraction(self, src_dir: str = None, dest_dir: str = None):
        """Run deduplication and full OCR extraction across a directory tree."""
        src_dir = src_dir or self.pdf_dir
        dest_dir = dest_dir or os.path.join(self.out_root, "pdf_convert")
        pdf_to_text.pdf_to_text_in_folders(src_dir, dest_dir)
        logger.info(f"📚 Completed batch extraction for {src_dir}")

    # ------------------------------------------------------------
    # ✅ 4. Slice-aware Column OCR
    # ------------------------------------------------------------
    def run_slice_analysis(self, engine: str = "paddle"):
        """Run full SliceManager pipeline for a single or multiple engines."""
        try:
            slicer = SliceManager(pdf_path=self.pdf_path, out_root=self.out_root, engines=engine)
            slicer.process_pdf()
            logger.info(f"🏁 Slice analysis complete for {self.filename} [{engine}]")
        except Exception as e:
            logger.error(f"❌ Slice analysis failed for {self.filename}: {e}")

    # ------------------------------------------------------------
    # ✅ 5. Manifest Handling
    # ------------------------------------------------------------
    def save_manifest(self, override=False):
        """Write manifest updates to disk."""
        save_manifest_data(data=self.manifest, pdf_dir=self.pdf_dir, override=override)
        logger.info(f"🧾 Manifest saved at {self.pdf_dir}")

    # ------------------------------------------------------------
    # ✅ 6. Orchestrated High-Level Runner
    # ------------------------------------------------------------
    def run_basic_extraction(self):
        """Split → Convert → Extract text"""
        pages = self.split_pdf()
        imgs = self.convert_to_images(pages)
        self.extract_text(imgs)
        logger.info(f"✅ Completed base extraction for {self.filename}")

    def run_full_pipeline(self, include_slice=True):
        """Perform entire pipeline, optionally including SliceManager OCR."""
        self.run_basic_extraction()
        if include_slice:
            for engine in self.engines:
                self.run_slice_analysis(engine)
        self.save_manifest()
        logger.info(f"🚀 Full pipeline completed for {self.filename}")
