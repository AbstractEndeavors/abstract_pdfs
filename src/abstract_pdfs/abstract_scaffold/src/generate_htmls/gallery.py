from .imports import *
from .templates.gallery import CARD_IMG, CARD_NO_IMG


def cards_from_subdirs(children, base_url, media_root, site_root):
    cards = []
    for child in children:
        img_url = None
        child_name = os.path.basename(child)
        alt = child_name
        title = humanize(child_name)
        desc = ""
        tags = []

        # info.json (imgs-style)
        info = os.path.join(child, "info.json")
        if os.path.exists(info):
            try:
                with open(info, "r", encoding="utf-8") as fh:
                    meta = json.load(fh)
                raw = meta.get("schema", {}).get("url") or meta.get("social_meta", {}).get("og:image")
                img_url = verified_url(raw, media_root, site_root)
                alt = meta.get("alt") or alt
                title = meta.get("title") or title
                desc = clean_text(meta.get("longdesc") or meta.get("caption") or "", 140)
            except (json.JSONDecodeError, OSError):
                pass

        # manifest (pdfs-style)
        if not img_url or not desc:
            m = load_manifest(child)
            if m:
                raw = m[0].get("social_meta", {}).get("og:image")
                if not img_url:
                    img_url = verified_url(raw, media_root, site_root)
                if not desc:
                    desc = extract_description(m)
                tags = extract_keywords(m, 4)

        # filesystem fallback image
        if not img_url:
            img_url = first_real_image_url(child, media_root, site_root)

        # Build desc + tags HTML fragments
        desc_html = f'<span class="card-desc">{desc}</span>' if desc else ""
        if tags:
            tags_inner = "".join(f'<span class="card-tag">{t}</span>' for t in tags)
            desc_html += f'<div class="card-tags">{tags_inner}</div>'

        cards.append({
            "img_url": img_url,
            "alt": alt,
            "title": title,
            "href": f"{base_url.rstrip('/')}/{child_name}/",
            "desc_html": desc_html,
        })
    return cards


def render_cards(cards):
    return "\n".join(
        CARD_IMG.format(**c) if c.get("img_url") else CARD_NO_IMG.format(**c)
        for c in cards
    )
