"""
PDF workspace resolver.

Given a path to a PDF (file or its parent directory), resolves the
canonical directory layout, catalogs every artifact, and compiles
a manifest.json as the single source of truth.

Layout convention:
    <name>/
        <name>.pdf
        manifest.json
        index.html
        text/
            000.txt  001.txt  ...
        thumbnails/
            000.png  000_info.json  index.html  ...

All paths stored and serialised as POSIX-relative from the workspace
root (pdf_dir), so the manifest is portable across machines.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional

from abstract_utilities import get_file_parts, get_files_and_dirs, MIME_TYPES,get_pathlib_path,get_str_path


# ------------------------------------------------------------------
# Path helpers
# ------------------------------------------------------------------

def _to_posix(path):
    """Normalize a path to forward slashes for portable serialization."""
    return path.replace(os.sep, "/")


def _to_relative(root, absolute):
    """Return a POSIX-relative path from root to absolute."""
    rel = os.path.relpath(os.path.realpath(absolute), os.path.realpath(root))
    return _to_posix(rel)


def _is_side_channel_text(rel_path):
    stem = os.path.splitext(os.path.basename(rel_path))[0].lower()
    if any(s in stem for s in _TEXT_EXCLUDE_STEMS):
        return True
    if rel_path.endswith("clean.txt"):
        return True
    return False


_IMAGE_EXTS = list(MIME_TYPES.get("image", {}).keys())
_TEXT_EXCLUDE_STEMS = {"left", "right"}


# ------------------------------------------------------------------
# Schema
# ------------------------------------------------------------------

@dataclass
class PDFWorkspace:
    """Resolved PDF workspace — every stored path is relative to pdf_dir."""

    pdf_dir: str                                    # absolute anchor (not serialised)
    pdf_path: str                                   # relative
    text_dir: str                                   # relative
    thumbnails_dir: str                             # relative

    thumbnails: List[str] = field(default_factory=list)
    texts: List[str] = field(default_factory=list)
    infos: List[str] = field(default_factory=list)
    htmls: List[str] = field(default_factory=list)
    manifest_path: str = "manifest.json"

    # ---- path helpers ------------------------------------------------

    def absolute(self, rel):
        """Resolve a workspace-relative path back to the filesystem."""
        return os.path.join(self.pdf_dir, rel)

    def exists(self, rel):
        return os.path.exists(self.absolute(rel))

    # ---- manifest ----------------------------------------------------

    def compile_manifest(self):
        """
        Build a manifest dict from current workspace state.

        Only includes artifacts that actually exist on disk —
        the manifest is a snapshot of truth, not a wish list.
        """
        def _existing(paths):
            return [p for p in paths if self.exists(p)]

        return {
            "schema_version": 1,
            "compiled_at": datetime.now(timezone.utc).isoformat(),
            "pdf": self.pdf_path if self.exists(self.pdf_path) else None,
            "text_dir": self.text_dir if self.exists(self.text_dir) else None,
            "thumbnails_dir": self.thumbnails_dir if self.exists(self.thumbnails_dir) else None,
            "texts": _existing(self.texts),
            "thumbnails": _existing(self.thumbnails),
            "infos": _existing(self.infos),
            "htmls": _existing(self.htmls),
            "page_count": len(_existing(self.texts)),
        }

    def write_manifest(self):
        """Compile and write manifest.json into the workspace root."""
        manifest = self.compile_manifest()
        dest = self.absolute(self.manifest_path)
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)

        with open(dest, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)

        return self.manifest_path

    def read_manifest(self):
        """Load the existing manifest, or None if it doesn't exist."""
        abs_path = self.absolute(self.manifest_path)
        if not os.path.isfile(abs_path):
            return None
        with open(abs_path, "r", encoding="utf-8") as fh:
            return json.load(fh)


# ------------------------------------------------------------------
# Resolver
# ------------------------------------------------------------------

class PDFWorkspaceResolver:
    """
    Resolves a raw path into a PDFWorkspace with relative paths
    and an optional manifest write.

    Usage:
        resolver = PDFWorkspaceResolver()
        ws = resolver.resolve("/data/report.pdf")
        ws.write_manifest()
    """

    def resolve(self, path, *, write_manifest=False):
        """
        Resolve *path* to a PDFWorkspace.

        Returns None if the path doesn't point to a valid PDF
        or its parent directory.
        """
        pdf_abs = self._ensure_dir_layout(path)
        if pdf_abs is None:
            return None

        pdf_dir = os.path.dirname(pdf_abs)

        ws = PDFWorkspace(
            pdf_dir=pdf_dir,
            pdf_path=_to_posix(os.path.basename(pdf_abs)),
            text_dir="text",
            thumbnails_dir="thumbnails",
        )
        self._scan(ws)

        if write_manifest:
            ws.write_manifest()

        return ws

    # -- directory layout ------------------------------------------

    @staticmethod
    def _ensure_dir_layout(path):
        """
        If *path* is a bare PDF sitting next to siblings, move it
        into its own directory.  If *path* is already a directory,
        look for the matching PDF inside it.

        Returns the canonical absolute pdf_path, or None.
        """
        if os.path.isfile(path) and path.endswith(".pdf"):
            parent = os.path.dirname(path)
            stem = os.path.splitext(os.path.basename(path))[0]

            if os.path.basename(parent) != stem:
                target_dir = os.path.join(parent, stem)
                os.makedirs(target_dir, exist_ok=True)
                target = os.path.join(target_dir, os.path.basename(path))
                shutil.move(path, target)
                return target
            return path

        if os.path.isdir(path):
            dirname = os.path.basename(path)
            candidate = os.path.join(path, f"{dirname}.pdf")
            if os.path.isfile(candidate):
                return candidate

        return None

    # -- catalog ---------------------------------------------------

    def _scan(self, ws):
        ws.thumbnails = self._scan_dir(ws, ws.thumbnails_dir, allowed_exts=_IMAGE_EXTS)
        ws.texts = sorted(
            p for p in self._scan_dir(ws, ws.text_dir, allowed_exts=[".txt"])
            if not _is_side_channel_text(p)
        )
        ws.infos = [
            p for p in self._scan_dir(ws, ws.thumbnails_dir, allowed_exts=[".json"])
            if p.endswith("info.json")
        ]
        ws.htmls = self._scan_htmls(ws)

    @staticmethod
    def _scan_dir(ws, rel_dir, *, allowed_exts):
        """Scan a subdirectory and return workspace-relative paths."""
        abs_dir = ws.absolute(rel_dir)
        if not os.path.isdir(abs_dir):
            return []

        _, files = get_files_and_dirs(abs_dir, allowed_exts=allowed_exts)
        return [_to_relative(ws.pdf_dir, f) for f in files]

    @staticmethod
    def _scan_htmls(ws):
        found = []

        root_index = "index.html"
        if ws.exists(root_index):
            found.append(root_index)

        thumb_abs = ws.absolute(ws.thumbnails_dir)
        if os.path.isdir(thumb_abs):
            _, files = get_files_and_dirs(thumb_abs, allowed_exts=[".html"])
            found.extend(
                _to_relative(ws.pdf_dir, f)
                for f in files
                if f.endswith("index.html")
            )
        return found
