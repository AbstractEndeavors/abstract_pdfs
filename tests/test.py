from imports import *
from abstract_utilities import get_files_and_dirs

_DISPATCH = {
    "image": lambda args: scaffold_image(args.input, base_url=args.base_url,
                media_root=args.media_root, write=args.write, overwrite=args.overwrite),
    "pdf":   lambda args: scaffold_pdf(args.input, base_url=args.base_url,
                media_root=args.media_root, write=args.write, overwrite=args.overwrite),
    "page":  lambda args: scaffold_page(pages_root=args.pages_root, section=args.section,
                slug=args.slug, title=args.title, description=args.description,
                thumbnail=args.thumbnail, keywords=args.keywords,
                content_file=args.content_file, base_url=args.base_url,
                media_root=args.media_root, write=args.write, overwrite=args.overwrite),
}

def main(argv=None):
    parser = abstract_scaffold_build_parser()
    args = parser.parse_args(argv)
    return _DISPATCH[args.command](args)


pdf_path = "/srv/media/thedailydialectics/pdfs/FIOA/41707059074637/41707059074637.pdf"
BASE_URL='https://thedailydialectics.com'
MEDIA_ROOT='/srv/media/thedailydialectics'
PDFS_PUBLIC_URL=f"{BASE_URL}/pdfs"
data = {
    "pdf_path":pdf_path,
    "base_url":BASE_URL,
    "media_root":MEDIA_ROOT,
    "overwrite":True,
    "write":True
    }
cmd_pdf(**data)
##
##input(abstract_scaffold_main(data))
result = generate_pdf_manifest(**data)
input(result)
