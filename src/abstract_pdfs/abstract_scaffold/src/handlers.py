from .imports import *
from .generators import (
    generate_image_info,
    generate_page_variables,
    generate_pdf_manifest
    )
# ─────────────────────────────────────────────────────────────────────────────
# Subcommand handlers
# ─────────────────────────────────────────────────────────────────────────────

def cmd_image(args: argparse.Namespace) -> int:
    input_path  = Path(args.input).resolve()
    media_root  = Path(args.media_root).resolve()
    base_url    = args.base_url

    targets: list[Path] = []

    if input_path.is_file():
        if input_path.suffix.lower() in IMAGE_EXTENSIONS:
            targets.append(input_path)
        else:
            print(f"ERROR: {input_path} is not a recognised image file.", file=sys.stderr)
            return 1
    elif input_path.is_dir():
        for ext in IMAGE_EXTENSIONS:
            targets.extend(input_path.rglob(f"*{ext}"))
        if not targets:
            print(f"WARNING: No image files found under {input_path}")
            return 0
    else:
        print(f"ERROR: {input_path} does not exist.", file=sys.stderr)
        return 1

    print(f"Processing {len(targets)} image(s)...")
    for img_path in sorted(targets):
        info  = generate_image_info(img_path, base_url, media_root)
        out   = img_path.parent / "info.json"
        msg   = write_json(out, info.to_dict(), dry_run=not args.write, overwrite=args.overwrite)
        print(msg)

    return 0


def cmd_pdf(args: argparse.Namespace) -> int:
    pdf_path   = Path(args.input).resolve()
    media_root = Path(args.media_root).resolve()
    base_url   = args.base_url

    if not pdf_path.exists():
        print(f"ERROR: {pdf_path} does not exist.", file=sys.stderr)
        return 1

    targets: list[Path] = []
    if pdf_path.is_file():
        if pdf_path.suffix.lower() == PDF_EXTENSION:
            targets.append(pdf_path)
        else:
            print(f"ERROR: {pdf_path} is not a PDF.", file=sys.stderr)
            return 1
    elif pdf_path.is_dir():
        targets.extend(pdf_path.rglob("*.pdf"))

    print(f"Processing {len(targets)} PDF(s)...")
    for p in sorted(targets):
        print(f"\n  {p.name}")
        entries  = generate_pdf_manifest(p, base_url, media_root)
        out      = p.parent / f"{p.stem}_manifest.json"
        msg      = write_json(out, [e.to_dict() for e in entries],
                              dry_run=not args.write, overwrite=args.overwrite)
        print(f"  → {len(entries)} pages")
        print(msg)

    return 0


def cmd_page(args: argparse.Namespace) -> int:
    pages_root = Path(args.pages_root).resolve()
    base_url   = args.base_url
    section    = args.section
    slug       = args.slug

    page_dir = pages_root / section / slug

    variables = generate_page_variables(
        section     = section,
        slug        = slug,
        title       = args.title,
        description = args.description,
        thumbnail   = args.thumbnail,
        base_url    = base_url,
        keywords    = args.keywords or "",
        content_file= args.content_file or "",
    )

    # variables.json
    vars_path = page_dir / "variables.json"
    msg = write_json(vars_path, variables.to_dict(), dry_run=not args.write, overwrite=args.overwrite)
    print(msg)

    # content.md — starter template
    content_md = f"# {args.title}\n\n{args.description}\n\n<!-- Add page content here -->\n"
    md_path    = page_dir / "content.md"
    msg = write_text(md_path, content_md, dry_run=not args.write, overwrite=args.overwrite)
    print(msg)

    return 0
