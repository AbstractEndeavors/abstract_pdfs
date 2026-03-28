from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any
from abstract_utilities import *
from typing import *
from PIL import Image
from abstract_ocr import *
from pdf2image import convert_from_path
import os, shutil, hashlib, re, logging, PyPDF2,traceback,unicodedata,argparse,json,sys
from abstract_utilities import (
    mkdirs as make_dir,
    get_ext,
    is_file,
    make_list,
    get_logFile,
    get_directory,
    get_base_name,
    get_file_name,
    write_to_file,
    get_file_parts
    )

logger = get_logFile("abstract_pdf", level=logging.INFO)
try:
    from PIL import Image as PILImage
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import fitz  # PyMuPDF — for PDF page rendering + text extraction
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False
