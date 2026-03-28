"""
generate_index_html.py  (v5)

Two kinds of output:

1. PDF VIEWER page  — for leaf dirs that have a manifest
2. GALLERY INDEX page — for branch dirs, cards now include description snippet

Usage
-----
    python generate_index_html.py \
        --root       /srv/media/thedailydialectics/pdfs \
        --base-url   https://thedailydialectics.com/pdfs \
        --media-root /srv/media/thedailydialectics/pdfs

    python generate_index_html.py \
        --root       /srv/media/thedailydialectics/imgs \
        --base-url   https://thedailydialectics.com/imgs \
        --media-root /srv/media/thedailydialectics/imgs \
        --site-root  https://thedailydialectics.com/imgs

    python generate_index_html.py \
        --root /srv/media/thedailydialectics/pdfs/wipow/a197278 \
        --base-url https://thedailydialectics.com/pdfs/wipow/a197278 \
        --media-root /srv/media/thedailydialectics/pdfs \
        --no-recurse --dry-run
"""
from .imports import *
from .generate import run


def generate_index_html(root, *, base_url, media_root, site_root=None,
                        recurse=True, dry_run=False,pdf_path=None):
    root = os.path.abspath(root)
    media_root = os.path.abspath(media_root)
    site_root = (site_root or base_url).rstrip("/")

    if not os.path.isdir(root):
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        return 1

    run(root, base_url, media_root, site_root,
        recurse=recurse, dry_run=dry_run)
    return 0


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--root",        required=True)
    p.add_argument("--base-url",    required=True,  dest="base_url")
    p.add_argument("--media-root",  required=True,  dest="media_root")
    p.add_argument("--site-root",   default=None,   dest="site_root")
    p.add_argument("--no-recurse",  action="store_true", dest="no_recurse")
    p.add_argument("--dry-run",     action="store_true", dest="dry_run")
    args = p.parse_args(argv)

    return generate_index_html(
        args.root,
        base_url=args.base_url,
        media_root=args.media_root,
        site_root=args.site_root,
        recurse=not args.no_recurse,
        dry_run=args.dry_run,
    )
