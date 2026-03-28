from .imports import *
from abstract_react.meta_utils.apis.metadata import *
def create_bread_crumbs(path):
    path_parts = path.replace(MEDIA_ROOT,'').split('/thumbnails/')[0].split('/text/')[0].split('/')
    parts = [part for part in path_parts if part]
    path_init = 'https://thedailydialectics.com'
    breadCrumbs = f'<nav class="breadcrumb"> › <a href="{path_init}">Home</a>'
    main = parts[-1]
    parts = parts[:-1]
    for part in parts:
        path_init = f"{path_init}/{part}"
        a_comp = f'<a href="{path_init}/">{part}</a>'
        breadCrumbs = f"{breadCrumbs} › {a_comp}"
    breadCrumbs = f"{breadCrumbs} › <span>{main}</span></nav>"
    return breadCrumbs

def get_page_data(page_num,pdf_path):
    page_data = {}
    page_num_str = get_page_num_str(page_num)
    thumbnail_page_path = get_thumbnail(pdf_path,i)
    page_dir = os.path.dirname(thumbnail_page_path)
    json_path = os.path.join(page_dir, "info.json")
    thumbnail_page_url = path_to_url(thumbnail_page_path)
    thumbnail_html_url = path_to_url_info(thumbnail_page_path)
    text_page_path = get_text(pdf_path,i)
    text_page_url = path_to_url(text_page_path)
    text_page_text = read_from_file(text_page_path)
    analyze_result = analyze_page(pdf_dir, i)
    text_summary = analyze_result.summary          # short paragraph
    keywords = analyze_result.keywords.primary # keywords relevant to that page

    json_data={}
    if os.path.isfile(json_path):
        json_data = safe_load_from_json(json_path)
    
    page_title = f"{title} | {page_num_str} | {thumbnail_html_url}"
    page_data["title"] = json_data.get('title',page_title)
    page_data['href'] = thumbnail_html_url
    page_data['share_url'] = thumbnail_html_url
    page_data['thumbnail_link'] = thumbnail_page_url
    page_data['domain']=['thedailydialectics.com']
    page_data['variants']=['https://thedailydialectics.com']
    page_data['text'] = text_page_text
    page_data['description'] = json_data.get('description',text_summary)
    page_data['keywords'] = json_data.get('keywords',keywords)
    page_data['creator'] = 'thedailydialectics'
    page_data['author'] = '@thedailydialectics'
    page_data['site'] = 'https://thedailydialectics.com'
    page_data['site_name'] = 'thedailydialectics'
    page_data['keywords_str']= ','.join(page_data['keywords'])
    
    meta = get_meta_info(info=page_data)
    page_data["page_url"] = thumbnail_html_url
    
    page_data["alt"] = json_data.get('alt',page_data['title'])
    page_data["caption"] = json_data.get('caption',text_summary)
    page_data["schema"] = meta.get("og", {})
    page_data["schema"]['site_name'] = "thedailydialectics.com"
    page_data["social_meta"] = meta.get("twitter", {})
    page_data["other"] = meta.get("other")
    page_data['meta']= meta
    return page_data

def build_meta_tags(meta: dict, image_url: str, title: str, text: str = "",path=None):
    
    meta['variants'] = ['https://thedailydialectics.com']
    og    = meta.get("og", {})
    tw    = meta.get("twitter", {})
    other = meta.get("other", {})
    art   = og.get("article", {})
    description   = meta.get("description", {})
    domain = tw.get("domain", "")

    domain = tw.get("domain", "")
    if isinstance(domain, list):
        domain = domain[0] if domain else ""

    tag_metas = "".join(
        f'  <meta property="article:tag" content="{t}">\n'
        for t in (art.get("tag") or [])
    )
    article_metas = "".join(
        f'  <meta property="article:{k}" content="{v}">\n'
        for k, v in art.items()
        if k != "tag" and v
    )
    other_metas = "".join(
        f'  <meta name="{k}" content="{v}">\n'
        for k, v in other.items()
        if v and k not in ("alternate", "geo", "hreflang") and not isinstance(v, dict)
    )

    breadcrumbs = create_bread_crumbs(path) if path else ""
    description = meta.get("description", "")
    keywords    = meta.get("keywords", "")
    canonical   = meta.get("canonical", image_url)
    meta_tags = generate_meta_tags(meta, base_url='https://thedailydialectics.com', json_path=None)

    tags_html = ""
    for t in (art.get("tag") or []):
        tags_html += f'<span class="card-tag">{t}</span>'
    return  f"""  <meta charset="{other.get('charset', 'UTF-8')}">
  <meta name="viewport" content="{other.get('viewport', 'width=device-width,initial-scale=1')}">
  <meta name="theme-color" content="{other.get('theme_color', '#FFFFFF')}">
  <meta name="color-scheme" content="{other.get('color_scheme', 'light')}">
  {meta_tags}"""
def get_meta_tags(page_num,pdf_path):
    meta = get_page_data(page_num,pdf_path)
    return build_meta_tags(meta=meta, image_url=meta.get("thumbnail_link"), title=meta.get("title"), text=meta.get('description'),path=pdf_path)
