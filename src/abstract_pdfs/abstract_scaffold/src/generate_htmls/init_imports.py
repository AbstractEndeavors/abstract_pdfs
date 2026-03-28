from __future__ import annotations
import argparse, json, os, sys, re
from typing import Optional

SITE_ROOT  = "https://thedailydialectics.com"
IMAGE_EXTS = [".webp", ".jpg", ".jpeg", ".png", ".gif"]

SKIP_DIRS = {
    "text", "pages", "images", "thumbnails", "pdf_pages",
    "preprocessed_images", "preprocessed_text",
    "node_modules", ".git", "__pycache__",
}
