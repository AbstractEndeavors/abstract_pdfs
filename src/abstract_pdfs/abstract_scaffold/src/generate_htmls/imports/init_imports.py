
from ...imports import *
import argparse, json, sys, re,os
from pathlib import Path
from typing import Optional
from abstract_utilities import *
SITE_ROOT  = "https://thedailydialectics.com"
IMAGE_EXTS = [".webp", ".jpg", ".jpeg", ".png", ".gif"]

SKIP_DIRS = {
    "text", "pages", "images", "thumbnails", "pdf_pages",
    "preprocessed_images", "preprocessed_text",
    "node_modules", ".git", "__pycache__",
}
