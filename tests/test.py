from imports import PDFWorkspaceResolver
from abstract_utilities import get_files_and_dirs
pdf_dir = "/srv/staging/pdfs/education/chemistry/rndm/Nitration of Acetanilide"
resolver = PDFWorkspaceResolver()
_, pdf_files = get_files_and_dirs(pdf_dir, allowed_exts=[".pdf"])

for path in pdf_files:
    input(path)
    ws = resolver.resolve(path, write_manifest=True)
    input(ws)
