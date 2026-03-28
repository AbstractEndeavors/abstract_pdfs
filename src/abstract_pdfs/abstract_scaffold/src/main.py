# main.py
from .cli import abstract_scaffold_build_parser
from .handlers import cmd_image, cmd_pdf, cmd_page

def abstract_scaffold_main(argv=None):
    parser = abstract_scaffold_build_parser()
    args = parser.parse_args(argv)

    if not args.base_url:
        print("ERROR: --base-url required", file=sys.stderr)
        return 1

    if args.command == "image":
        if not args.media_root:
            print("ERROR: --media-root required", file=sys.stderr)
            return 1
        return cmd_image(args.input, base_url=args.base_url,
                         media_root=args.media_root, write=args.write,
                         overwrite=args.overwrite)

    if args.command == "pdf":
        if not args.media_root:
            print("ERROR: --media-root required", file=sys.stderr)
            return 1
        return cmd_pdf(args.input, base_url=args.base_url,
                       media_root=args.media_root, write=args.write,
                       overwrite=args.overwrite)

    if args.command == "page":
        return cmd_page(section=args.section, slug=args.slug,
                        title=args.title, description=args.description,
                        thumbnail=args.thumbnail, base_url=args.base_url,
                        pages_root=args.pages_root, keywords=args.keywords,
                        content_file=args.content_file, write=args.write,
                        overwrite=args.overwrite)
    # main.py — add the dispatch
    if args.command == "pipeline":
        if not args.media_root:
            print("ERROR: --media-root required", file=sys.stderr)
            return 1
        return cmd_pipeline(args.input, base_url=args.base_url,
                            media_root=args.media_root, site_root=args.site_root,
                            recurse=not args.no_recurse, write=args.write,
                            overwrite=args.overwrite, dry_run=args.dry_run)
    parser.print_help()
    return 1
