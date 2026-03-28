from .init_imports import *
def url_to_path(
    url: str,
    media_root: Path,
    site_root: str
    ) -> Optional[Path]:
    if not url or site_root not in url:
        return None
    rel = url.replace(site_root, "").lstrip("/")
    return safe_join_path(media_root,rel)


def path_to_url(
    path: Path,
    media_root: Path,
    site_root: str
    ) -> str:
    return f"{site_root}/{safe_rel_path(path,media_root)}"


def find_correct_path(
    broken: Path,
    media_root: Path
    ) -> Optional[Path]:
    target = broken.name
    if not target:
        return None
    matches = list(media_root.rglob(target))
    if len(matches) == 1:
        return matches[0]
    parent_name = broken.parent.name
    for m in matches:
        if m.parent.name == parent_name:
            return m
    return None


def verified_url(
    url: str,
    media_root: Path,
    site_root: str
    ) -> Optional[str]:
    if not url:
        return None
    expected = url_to_path(url, media_root, site_root)
    if expected is None:
        return url
    if os.path.exists(expected):
        return url
    correct = find_correct_path(expected, media_root)
    return path_to_url(correct, media_root, site_root) if correct else None

