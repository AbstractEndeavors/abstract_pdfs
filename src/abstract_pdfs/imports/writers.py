from .init_imports import *
# ─────────────────────────────────────────────────────────────────────────────
# Writer
# ─────────────────────────────────────────────────────────────────────────────

def write_json(path: Path, data: dict | list, dry_run: bool, overwrite: bool) -> str:
    """
    Write JSON to path. Returns a status string for logging.

    dry_run:   print what would happen, don't write
    overwrite: allow replacing existing files
    """
    if isinstance(path,str):
        path = Path(path)
    if path.exists() and not overwrite:
        return f"  SKIP (exists, use --overwrite): {path}"

    content = json.dumps(data, indent=2, ensure_ascii=False)

    if dry_run:
        return f"  DRY-RUN would write ({len(content)} bytes): {path}"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"  WROTE: {path}"


def write_text(path: Path, content: str, dry_run: bool, overwrite: bool) -> str:
    if isinstance(path,str):
        path = Path(path)
    if path.exists() and not overwrite:
        return f"  SKIP (exists, use --overwrite): {path}"
    if dry_run:
        return f"  DRY-RUN would write ({len(content)} bytes): {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"  WROTE: {path}"
