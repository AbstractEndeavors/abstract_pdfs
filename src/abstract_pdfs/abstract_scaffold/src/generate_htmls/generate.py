from .templates import (
    build_viewer_page,
    GALLERY_PAGE,
)
from .imports import (
    child_dirs,
    humanize,
    load_manifest,
    breadcrumbs,
)
from .gallery import cards_from_subdirs, render_cards
import os

def generate_index(directory, base_url, media_root, site_root, dry_run=False,pdf_path=None):
    manifest = load_manifest(directory)
    
    if manifest:
        html = build_viewer_page(directory, base_url, manifest, media_root, site_root,pdf_path=pdf_path)
        label = f"viewer ({len(manifest)} pages)"
    else:
        children = child_dirs(directory)
        if not children:
            return False
        cards = cards_from_subdirs(children, base_url, media_root, site_root)
        html = GALLERY_PAGE.format(
            page_title=humanize(os.path.basename(directory)),
            canonical_url=base_url.rstrip("/") + "/",
            breadcrumbs=breadcrumbs(base_url),
            heading=os.path.basename(directory),
            cards=render_cards(cards),
        )
        label = f"gallery ({len(cards)} cards)"

    out = os.path.join(directory, "index.html")
    if dry_run:
        print(f"[dry-run] {out}  [{label}]")
    else:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(html)
        print(f"wrote {out}  [{label}]")
    return True


def run(root, base_url, media_root, site_root, recurse=True, dry_run=False,pdf_path=None):
    generate_index(root, base_url, media_root, site_root, dry_run=dry_run,pdf_path=pdf_path)
    if recurse:
        for child in child_dirs(root):
            child_name = os.path.basename(child)
            run(
                child,
                f"{base_url.rstrip('/')}/{child_name}",
                media_root,
                site_root,
                recurse=True,
                dry_run=dry_run,
            )
