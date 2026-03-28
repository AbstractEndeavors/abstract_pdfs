from .init_imports import *
from .urls import *


def humanize(name):
    return name.replace("-", " ").replace("_", " ").title()


def clean_text(s, max_len=160):
    """Collapse whitespace and trim to max_len."""
    if isinstance(s, list):
        s = str(",".join(s))
    s = re.sub(r'\s+', ' ', s).strip()
    if len(s) > max_len:
        s = s[:max_len].rsplit(' ', 1)[0] + '…'
    return s


def child_dirs(directory):
    entries = []
    try:
        for name in sorted(os.listdir(directory)):
            full = os.path.join(directory, name)
            if os.path.isdir(full) and name not in SKIP_DIRS and not name.startswith("."):
                entries.append(full)
    except OSError:
        pass
    return entries


def load_manifest(directory):
    dirname = os.path.basename(directory)
    for name in [f"{dirname}_manifest.json", "manifest.json"]:
        p = os.path.join(directory, name)
        if not os.path.exists(p):
            continue
        try:
            with open(p, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, list) and data:
                return data
        except (json.JSONDecodeError, OSError) as e:
            print(f"[warn] bad manifest {p}: {e}")
    return None


def first_real_image_url(directory, media_root, site_root):
    for root, _, files in os.walk(directory):
        for f in sorted(files):
            _, ext = os.path.splitext(f)
            if ext.lower() in IMAGE_EXTS:
                full = os.path.join(root, f)
                if os.path.isfile(full):
                    try:
                        return path_to_url(full, media_root, site_root)
                    except ValueError:
                        continue
    return None


def breadcrumbs(base_url):
    path_part = base_url.rstrip("/").replace(SITE_ROOT, "").lstrip("/")
    segments = [s for s in path_part.split("/") if s]
    crumbs = [f'<a href="{SITE_ROOT}">Home</a>']
    acc = SITE_ROOT
    for i, seg in enumerate(segments):
        acc += f"/{seg}"
        if i < len(segments) - 1:
            crumbs.append(f'<a href="{acc}/">{humanize(seg)}</a>')
        else:
            crumbs.append(f"<span>{seg}</span>")
    return " › ".join(crumbs)


def extract_description(manifest):
    """
    Pull the best available description from a manifest.
    Priority: longdesc (OCR text) → caption → keywords_str
    """
    first = manifest[0]
    raw = (
        first.get("longdesc")
        or first.get("caption")
        or first.get("keywords_str", "").replace(",", " ")
        or ""
    )
    return clean_text(raw, 160)


def extract_keywords(manifest, limit=8):
    """Aggregate keywords across all pages, deduplicated, capped at limit."""
    seen = set()
    out = []
    for entry in manifest:
        for kw in entry.get("keywords_str", "").split(","):
            kw = kw.strip()
            kl = kw.lower()
            if kw and kl not in seen and len(kl) > 2:
                seen.add(kl)
                out.append(kw)
                if len(out) >= limit:
                    return out
    return out
