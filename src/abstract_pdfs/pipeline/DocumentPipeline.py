from .imports import *
from .document_rename    import rename_collection
from .SliceManager       import SliceManager


class DocumentPipeline:

    def __init__(self,
                 pdf_path: str,
                 base_dir=None,
                 out_root=None,
                 engines=None,
                 engine_directory=None,
                 visualize=None,
                 root_url=None,
                 media_root=None,
                 pdfs_public_url=None
                 ):
        self.file_parts = normalize_pdf_path(pdf_path)
        self.pdf_path   = self.file_parts.get("file_path")
        self.base_dir   = self.file_parts.get("dirname")
        self.out_root = out_root or self.base_dir
        self.engines    = engines or ["layout_ocr"]
        self.engine_directory = engine_directory or False,
        self.visualize= visualize,
        self.root_url= root_url,
        self.media_root= media_root,
        self.pdfs_public_url= pdfs_public_url
    def run(self) -> Path:
        print("📂 normalised directory:", self.base_dir)

        # OCR
        slice_mgr = SliceManager(
            pdf_path=self.pdf_path,
            out_root=self.out_root,
            engines=self.engines,
            engine_directory=self.engine_directory,
            visualize=self.visualize,
            root_url=self.root_url,
            media_root=self.media_root,
            pdfs_public_url=self.pdfs_public_url
            )
        self.file_parts = slice_mgr.process_pdf(self.engines)
        self.pdf_path   = self.file_parts.get("file_path")
        self.base_dir   = self.file_parts.get("dirname")
        self.dirbase    = self.file_parts.get("dirbase")

        # Integrity check (was commented out — re-enabled)
        validate_collection(self.pdf_path)

        # Slug rename
        slug    = slugify(self.dirbase)
        new_dir = rename_collection(self.base_dir, slug)

        print("📦 renamed collection:", new_dir)
        return new_dir
