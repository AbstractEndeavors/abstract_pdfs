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

from abstract_utilities import get_file_parts, get_files_and_dirs, MIME_TYPES


# ------------------------------------------------------------------
# Schema
# ------------------------------------------------------------------

@dataclass
class PDFWorkspace:
    """Resolved PDF workspace — every path is relative to pdf_dir."""

    pdf_dir: Path                          # absolute anchor (not serialised)
    pdf_path: PurePosixPath                # relative
    text_dir: PurePosixPath                # relative
    thumbnails_dir: PurePosixPath          # relative

    thumbnails: List[PurePosixPath] = field(default_factory=list)
    texts: List[PurePosixPath] = field(default_factory=list)
    infos: List[PurePosixPath] = field(default_factory=list)
    htmls: List[PurePosixPath] = field(default_factory=list)
    manifest_path: PurePosixPath = PurePosixPath("manifest.json")

    # ---- path helpers ------------------------------------------------

    def absolute(self, rel: PurePosixPath) -> Path:
        """Resolve a workspace-relative path back to the filesystem."""
        return self.pdf_dir / rel

    def exists(self, rel: PurePosixPath) -> bool:
        return self.absolute(rel).exists()

    # ---- manifest ----------------------------------------------------

    def compile_manifest(self) -> Dict[str, Any]:
        """
        Build a manifest dict from current workspace state.

        Only includes artifacts that actually exist on disk —
        the manifest is a snapshot of truth, not a wish list.
        """
        def _existing(paths: List[PurePosixPath]) -> List[str]:
            return [str(p) for p in paths if self.exists(p)]

        manifest: Dict[str, Any] = {
            "schema_version": 1,
            "compiled_at": datetime.now(timezone.utc).isoformat(),
            "pdf": str(self.pdf_path) if self.exists(self.pdf_path) else None,
            "text_dir": str(self.text_dir) if self.exists(self.text_dir) else None,
            "thumbnails_dir": str(self.thumbnails_dir) if self.exists(self.thumbnails_dir) else None,
            "texts": _existing(self.texts),
            "thumbnails": _existing(self.thumbnails),
            "infos": _existing(self.infos),
            "htmls": _existing(self.htmls),
            "page_count": len(_existing(self.texts)),
        }
        return manifest

    def write_manifest(self) -> PurePosixPath:
        """Compile and write manifest.json into the workspace root."""
        manifest = self.compile_manifest()
        dest = self.absolute(self.manifest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        with open(dest, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)

        return self.manifest_path

    def read_manifest(self) -> Optional[Dict[str, Any]]:
        """Load the existing manifest, or None if it doesn't exist."""
        abs_path = self.absolute(self.manifest_path)
        if not abs_path.is_file():
            return None
        with open(abs_path, "r", encoding="utf-8") as fh:
            return json.load(fh)


# ------------------------------------------------------------------
# Resolver
# ------------------------------------------------------------------

_IMAGE_EXTS: List[str] = list(MIME_TYPES.get("image", {}).keys())
_TEXT_EXCLUDE_STEMS = {"left", "right"}


class PDFWorkspaceResolver:
    """
    Resolves a raw path into a PDFWorkspace with relative paths
    and an optional manifest write.

    Usage:
        resolver = PDFWorkspaceResolver()
        ws = resolver.resolve("/data/report.pdf")
        ws.write_manifest()
    """

    def resolve(
        self,
        path: str | os.PathLike,
        *,
        write_manifest: bool = False,
    ) -> Optional[PDFWorkspace]:
        """
        Resolve *path* to a PDFWorkspace.

        If write_manifest is True, compiles and writes manifest.json
        as part of resolution.  Returns None if the path doesn't
        point to a valid PDF or its parent directory.
        """
        pdf_abs = self._ensure_dir_layout(Path(path))
        if pdf_abs is None:
            return None

        pdf_dir = pdf_abs.parent

        ws = PDFWorkspace(
            pdf_dir=pdf_dir,
            pdf_path=PurePosixPath(pdf_abs.name),
            text_dir=PurePosixPath("text"),
            thumbnails_dir=PurePosixPath("thumbnails"),
        )
        self._scan(ws)

        if write_manifest:
            ws.write_manifest()

        return ws

    # -- directory layout ------------------------------------------

    @staticmethod
    def _ensure_dir_layout(path: Path) -> Optional[Path]:
        """
        If *path* is a bare PDF sitting next to siblings, move it
        into its own directory.  If *path* is already a directory,
        look for the matching PDF inside it.

        Returns the canonical absolute pdf_path, or None.
        """
        if path.is_file() and path.suffix == ".pdf":
            if path.parent.name != path.stem:
                target_dir = path.parent / path.stem
                target_dir.mkdir(parents=True, exist_ok=True)
                target = target_dir / path.name
                shutil.move(str(path), str(target))
                return target
            return path

        if path.is_dir():
            candidate = path / f"{path.name}.pdf"
            if candidate.is_file():
                return candidate

        return None

    # -- catalog ---------------------------------------------------

    def _scan(self, ws: PDFWorkspace) -> None:
        ws.thumbnails = self._scan_dir(
            ws, ws.thumbnails_dir, allowed_exts=_IMAGE_EXTS,
        )
        ws.texts = sorted(
            p for p in self._scan_dir(ws, ws.text_dir, allowed_exts=[".txt"])
            if not _is_side_channel_text(p)
        )
        ws.infos = [
            p for p in self._scan_dir(ws, ws.thumbnails_dir, allowed_exts=[".json"])
            if str(p).endswith("info.json")
        ]
        ws.htmls = self._scan_htmls(ws)

    @staticmethod
    def _scan_dir(
        ws: PDFWorkspace,
        rel_dir: PurePosixPath,
        *,
        allowed_exts: List[str],
    ) -> List[PurePosixPath]:
        """Scan a subdirectory and return workspace-relative paths."""
        abs_dir = ws.absolute(rel_dir)
        if not abs_dir.is_dir():
            return []

        _, files = get_files_and_dirs(str(abs_dir), allowed_exts=allowed_exts)
        return [
            _to_relative(ws.pdf_dir, Path(f))
            for f in files
        ]

    @staticmethod
    def _scan_htmls(ws: PDFWorkspace) -> List[PurePosixPath]:
        found: List[PurePosixPath] = []

        root_index = PurePosixPath("index.html")
        if ws.exists(root_index):
            found.append(root_index)

        thumb_abs = ws.absolute(ws.thumbnails_dir)
        if thumb_abs.is_dir():
            _, files = get_files_and_dirs(str(thumb_abs), allowed_exts=[".html"])
            found.extend(
                _to_relative(ws.pdf_dir, Path(f))
                for f in files
                if f.endswith("index.html")
            )
        return found


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _to_relative(root: Path, absolute: Path) -> PurePosixPath:
    """Convert an absolute path to a POSIX-relative path from *root*."""
    return PurePosixPath(absolute.resolve().relative_to(root.resolve()))


def _is_side_channel_text(path: PurePosixPath) -> bool:
    name_lower = path.stem.lower()
    if any(stem in name_lower for stem in _TEXT_EXCLUDE_STEMS):
        return True
    if path.name.endswith("clean.txt"):
        return True
    return False
