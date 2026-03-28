from .init_imports import *


def url_to_path(url, media_root, site_root):
    if not url or site_root not in url:
        return None
    rel = url.replace(site_root, "").lstrip("/")
    return os.path.join(media_root, rel)


def path_to_url(path, media_root, site_root):
    rel = os.path.relpath(path, media_root).replace(os.sep, "/")
    return f"{site_root}/{rel}"


def find_correct_path(broken, media_root):
    target = os.path.basename(broken)
    if not target:
        return None
    matches = []
    for root, _, files in os.walk(media_root):
        if target in files:
            matches.append(os.path.join(root, target))
    if len(matches) == 1:
        return matches[0]
    parent_name = os.path.basename(os.path.dirname(broken))
    for m in matches:
        if os.path.basename(os.path.dirname(m)) == parent_name:
            return m
    return None


def verified_url(url, media_root, site_root):
    if not url:
        return None
    expected = url_to_path(url, media_root, site_root)
    if expected is None:
        return url
    if os.path.exists(expected):
        return url
    correct = find_correct_path(expected, media_root)
    return path_to_url(correct, media_root, site_root) if correct else None
