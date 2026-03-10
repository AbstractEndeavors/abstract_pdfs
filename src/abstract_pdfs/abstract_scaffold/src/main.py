from .cli import abstract_scaffold_build_parser
from .handlers import cmd_image,cmd_pdf,cmd_page
def abstract_scaffold_main() -> int:
    parser = abstract_scaffold_build_parser()
    args   = parser.parse_args()

    # ── Validate shared required args ─────────────────────────────────────────
    if not args.base_url:
        print("ERROR: --base-url is required (or set BASE_URL / NEXT_PUBLIC_API_BASE env var)",
              file=sys.stderr)
        return 1

    cmd = args.command

    if cmd in ("image", "pdf") and not args.media_root:
        print("ERROR: --media-root is required for image/pdf commands (or set MEDIA_ROOT / PUBLIC_ROOT)",
              file=sys.stderr)
        return 1

    if cmd == "image":  return cmd_image(args)
    if cmd == "pdf":    return cmd_pdf(args)
    if cmd == "page":   return cmd_page(args)

    parser.print_help()
    return 1
