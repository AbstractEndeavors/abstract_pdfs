# handlers.py
from .imports import *
from .generators import (
    generate_image_info,
    generate_page_variables,
    generate_pdf_manifest,
)
def get_dict(obj):
    if not isinstance(obj,dict):
        try:
            obj = obj.to_dict()
        except Exception as e:
            logger.info(f"ERROR in generators.py via {obj}: {e}")
    return obj

def cmd_image(input_path, *, base_url, media_root, write=False, overwrite=False):
    input_path = os.path.abspath(input_path)
    media_root = os.path.abspath(media_root)

    targets = []

    if os.path.isfile(input_path):
        _, ext = os.path.splitext(input_path)
        if ext.lower() in IMAGE_EXTENSIONS:
            targets.append(input_path)
        else:
            print(f"ERROR: {input_path} is not a recognised image file.", file=sys.stderr)
            return 1
    elif os.path.isdir(input_path):
        for root, _, files in os.walk(input_path):
            for f in files:
                _, ext = os.path.splitext(f)
                if ext.lower() in IMAGE_EXTENSIONS:
                    targets.append(os.path.join(root, f))
        if not targets:
            print(f"WARNING: No image files found under {input_path}")
            return 0
    else:
        print(f"ERROR: {input_path} does not exist.", file=sys.stderr)
        return 1

    print(f"Processing {len(targets)} image(s)...")
    for img_path in sorted(targets):
        info = generate_image_info(img_path, base_url, media_root)
        out = os.path.join(os.path.dirname(img_path), "info.json")
        msg = write_json(out, get_dict(info), dry_run=not write, overwrite=overwrite)
        print(msg)

    return 0


def cmd_pdf(pdf_path, *, base_url, media_root, write=False, overwrite=False):
    input_path = os.path.abspath(pdf_path)
    media_root = os.path.abspath(media_root)

    if not os.path.exists(pdf_path):
        print(f"ERROR: {pdf_path} does not exist.", file=sys.stderr)
        return 1

    targets = []
    if os.path.isfile(pdf_path):
        if input_path.lower().endswith(".pdf"):
            targets.append(pdf_path)
        else:
            print(f"ERROR: {input_path} is not a PDF.", file=sys.stderr)
            return 1
    elif os.path.isdir(pdf_path):
        for root, _, files in os.walk(pdf_path):
            for f in files:
                if f.lower().endswith(".pdf"):
                    targets.append(os.path.join(root, f))

    print(f"Processing {len(targets)} PDF(s)...")
    for p in sorted(targets):
        name = os.path.basename(p)
        stem = os.path.splitext(name)[0]
        print(f"\n  {name}")
        entries = generate_pdf_manifest(p, base_url=base_url, media_root=media_root)
        out = os.path.join(os.path.dirname(p), f"{stem}_manifest.json")
        msg = write_json(out, [get_dict(e) for e in entries],
                         dry_run=not write, overwrite=overwrite)
        print(f"  → {len(entries)} pages")
        print(msg)

    return 0


def cmd_page(*, section, slug, title, description, thumbnail,
             base_url, pages_root, keywords="", content_file="",
             write=False, overwrite=False):
    pages_root = os.path.abspath(pages_root)
    page_dir = os.path.join(pages_root, section, slug)

    variables = generate_page_variables(
        section=section,
        slug=slug,
        title=title,
        description=description,
        thumbnail=thumbnail,
        base_url=base_url,
        keywords=keywords,
        content_file=content_file,
    )

    vars_path = os.path.join(page_dir, "variables.json")
    msg = write_json(vars_path, get_dict(variables), dry_run=not write, overwrite=overwrite)
    print(msg)

    content_md = f"# {title}\n\n{description}\n\n<!-- Add page content here -->\n"
    md_path = os.path.join(page_dir, "content.md")
    msg = write_text(md_path, content_md, dry_run=not write, overwrite=overwrite)
    print(msg)

    return 0
