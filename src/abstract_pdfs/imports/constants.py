from .init_imports import MIME_TYPES,get_env_value,eatOuter,re
def eatSlash(string):
    try:
        string = eatOuter(string,['/'])
    except Exception as e:
        logger.info(f"{e}")
    return string
IMAGE_EXTS = list(MIME_TYPES.get('image').keys())
PDF_EXTENSION    = ".pdf"
TEXT_EXTS   = {".txt"}
PDF_EXTS    = {".pdf"}
ENV_PATH = get_env_value("ABSTRACT_MEDIA_SCAFFOLD_ENV_PATH")
CREATOR_NAME = get_env_value("ABSTRACT_MEDIA_SCAFFOLD_CREATOR_NAME",path=ENV_PATH) or 'thedailydialectics'
CONTENT_TYPE = get_env_value("ABSTRACT_MEDIA_SCAFFOLD_CONTENT_TYPE",path=ENV_PATH) or 'educational'
ATTRIBUTION=f"Created by {CREATOR_NAME} for {CONTENT_TYPE} purposes"

ROOT_URL_ = get_env_value("ABSTRACT_MEDIA_SCAFFOLD_ROOT_URL",path=ENV_PATH)
ROOT_URL = eatSlash(ROOT_URL_)
PDFS_PUBLIC_URL = get_env_value("ABSTRACT_MEDIA_PDFS_PUBLIC_URL",path=ENV_PATH) or f"{ROOT_URL}/pdfs"
IMGS_PUBLIC_URL = get_env_value("ABSTRACT_MEDIA_IMGS_PUBLIC_URL",path=ENV_PATH) or f"{ROOT_URL}/imgs"


ROOT_DIR_ = get_env_value("ABSTRACT_SCAFFOLD_ROOT_DIR",path=ENV_PATH)
ROOT_DIR = eatSlash(ROOT_DIR_)
MEDIA_ROOT_DIR = get_env_value("ABSTRACT_MEDIA_SCAFFOLD_MEDIA_ROOT_DIR",path=ENV_PATH) or f"{ROOT_DIR}/media"
PDFS_ROOT_DIR = get_env_value("ABSTRACT_MEDIA_SCAFFOLD_PDFS_ROOT_DIR",path=ENV_PATH) or f"{MEDIA_ROOT_DIR}/pdfs"
IMGS_ROOT_DIR = get_env_value("ABSTRACT_MEDIA_SCAFFOLD_IMGS_ROOT_DIR",path=ENV_PATH) or f"{MEDIA_ROOT_DIR}/imgs"
PAGE_RE     = re.compile(r"page[_\-]?(\d+)", re.IGNORECASE)

