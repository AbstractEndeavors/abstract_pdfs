from .imports import *
# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def abstract_scaffold_build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="scaffold_media",
        description="Generate info.json / manifest.json / variables.json / content.md for TDD media.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--base-url",    default=os.environ.get("BASE_URL", os.environ.get("NEXT_PUBLIC_API_BASE", "")),
                        help="Site base URL. Env: BASE_URL or NEXT_PUBLIC_API_BASE")
    shared.add_argument("--media-root", "--public-root", "--public",
                        dest="media_root",
                        default=os.environ.get("MEDIA_ROOT", os.environ.get("PUBLIC_ROOT", "")),
                        help="Volume root that maps to / for URL paths (e.g. /srv/media/ba). "
                             "Env: MEDIA_ROOT or PUBLIC_ROOT")
    shared.add_argument("--write",       action="store_true",
                        help="Actually write files (default: dry-run, prints only)")
    shared.add_argument("--overwrite",   action="store_true",
                        help="Overwrite existing files")

    sub = root.add_subparsers(dest="command", required=True)

    # ── image ────────────────────────────────────────────────────────────────
    p_img = sub.add_parser("image", parents=[shared],
                           help="Generate info.json for one image or a directory of images")
    p_img.add_argument("--input", required=True,
                       help="Path to an image file or a directory to walk recursively")

    # ── pdf ──────────────────────────────────────────────────────────────────
    p_pdf = sub.add_parser("pdf", parents=[shared],
                           help="Generate {base}_manifest.json for one PDF or a directory of PDFs")
    p_pdf.add_argument("--input", required=True,
                       help="Path to a PDF file or directory")

    # ── page ─────────────────────────────────────────────────────────────────
    p_page = sub.add_parser("page", parents=[shared],
                             help="Scaffold variables.json + content.md for a new page")
    p_page.add_argument("--pages-root", default=os.environ.get("PAGES_ROOT", ""),
                        help="Root content directory. Env: PAGES_ROOT")
    p_page.add_argument("--section",  required=True, help="Section name, e.g. 'cannabis'")
    p_page.add_argument("--slug",     required=True, help="Page slug, e.g. 'rick-simpson-oil'")
    p_page.add_argument("--title",    required=True, help="Page title")
    p_page.add_argument("--description", required=True, help="Page description / meta description")
    p_page.add_argument("--thumbnail",   required=True,
                        help="Thumbnail dir relative to public/, e.g. 'imgs/cannabis/cannabis-oil-and-leaves'")
    p_page.add_argument("--keywords",    default="", help="Comma-separated keywords")
    p_page.add_argument("--content-file", default="", help="Override content_file path")
    p_pipe = sub.add_parser("pipeline", parents=[shared],
                            help="Full run: manifest PDFs, info images, generate indexes")
    p_pipe.add_argument("--input", required=True, help="Root directory to process")
    p_pipe.add_argument("--site-root", default=None, dest="site_root")
    p_pipe.add_argument("--no-recurse", action="store_true", dest="no_recurse")
    p_pipe.add_argument("--dry-run", action="store_true", dest="dry_run")
    return root
