from ..imports import *
from abstract_apis import *
from abstract_react.meta_utils.apis.metadata import *
def is_image(path):
    file_parts = get_file_parts(path)
    ext = file_parts.get('ext')
    if ext in IMAGE_EXTS:
        return True
    return False
def analyze_page(pdf_dir,page_index):
    data={"text":get_text(pdf_dir,page_index),
    "scope":f"page:{page_index}",
    "summary_preset":"brief",         # one page ≠ article-length
    "keyword_preset":"seo"}
    return postRequest('https://clownworld.biz/hugpy/analyze/text',data=data)
def refine_keywords(text, preset="seo"):
    data={"text":text,"preset":preset}
    return postRequest('https://clownworld.biz/hugpy/keybert/refine_keywords',data=data)
def summarize(text, preset="article"):
    data={"text":text,"preset":preset}
    return postRequest('https://clownworld.biz/hugpy/summarizer/summarize',data=data)

def get_pdf_dir(pdf_dir):
    if os.path.isfile(pdf_dir):
        pdf_dir = os.path.dirname(pdf_dir)
    return pdf_dir
def get_page_num(num):
    num = str(num)
    return '000'[:-len(num)]+num
def get_page_num_str(num):
    page_num = get_page_num(num)
    
    return f"page_{page_num}"
def get_thumbnails_dir(pdf_dir):
    pdf_dir = get_pdf_dir(pdf_dir)
    return os.path.join(pdf_dir,'thumbnails')
def get_thumbnail_dir(pdf_dir,i):
    thumbnails_dir = get_thumbnails_dir(pdf_dir)
    page_num_str = get_page_num_str(i)
    return os.path.join(thumbnails_dir,page_num_str)
def get_thumbnail(pdf_dir,i):
    thumbnail_dir = get_thumbnail_dir(pdf_dir,i)
    image_list = [os.path.join(thumbnail_dir,item) for item in os.listdir(thumbnail_dir) if is_image(item)]
    return image_list[0] if image_list else None
def get_texts_dir(pdf_dir):
    pdf_dir = get_pdf_dir(pdf_dir)
    return os.path.join(pdf_dir,'text')
def get_all_text_paths(pdf_dir):
    texts_dir = get_texts_dir(pdf_dir)  
    return [os.path.join(texts_dir,item) for item in os.listdir(texts_dir) if "left" not in item and "right" not in item and item.endswith(f".txt")]
def get_all_texts(pdf_dir):
    text_paths = get_all_text_paths(pdf_dir)
    text_paths.sort()
    return [read_from_file(text_path) for text_path in text_paths]

def get_full_text(pdf_dir):
    texts = get_all_texts(pdf_dir)
    return '\n'.join(texts)
def get_full_text_summary(pdf_dir):
    all_text = get_full_text(pdf_dir)
    return summarize(text, preset="article")
def get_full_text_keywords(pdf_dir):
    text = get_full_text(pdf_dir)
    return refine_keywords(text, preset="seo")
def get_text_path(pdf_dir,i):
    texts_dir = get_texts_dir(pdf_dir)
    page_num_str = get_page_num_str(i)
    text_list = [os.path.join(texts_dir,item) for item in os.listdir(texts_dir) if "left" not in item and "right" not in item and item.endswith(f"{page_num_str}.txt")]
    text_list.sort()
    return text_list[i-1] if text_list else None
def get_text(pdf_dir,i):
    text_path = get_text_path(pdf_dir,i)
    return read_from_file(text_path)
def get_text_summary(pdf_dir,i):
    text = get_text(pdf_dir,i)
    return summarize(text, preset="article")
def get_text_keywords(pdf_dir,i):
    text = get_text(pdf_dir,i)
    return refine_keywords(text, preset="seo")

def path_to_url(path,media_root,site_root):
    return path.replace(media_root,site_root)
def url_to_path(url,media_root,site_root):
    return path.replace(site_root,media_root)
def path_to_url_info(path,media_root,site_root):
    dirname = os.path.dirname(path)       
    return path_to_url(dirname,media_root,site_root)
def convert_paths_to_urls(data,media_root,site_root):
    base_url = base_url or site_root
    return data.replace(media_root,base_url)
def slice_pdf(pdf_path,media_root,site_root):
    out_root = os.path.dirname(pdf_path)
    asset = SliceManager(
        pdf_path=pdf_path,
        out_root=out_root,
        engines="paddle",
        engine_directory= False,
        visualize= None,
        root_url=site_root,
        media_root=media_root,
        pdfs_public_url=PDFS_PUBLIC_URL
        )
    return asset
def create_bread_crumbs(path,media_root,site_root):
    path_parts = str(path).replace(media_root,'').split('/thumbnails/')[0].split('/text/')[0].split('/')
    parts = [part for part in path_parts if part]
    path_init = site_root
    breadCrumbs = f'<nav class="breadcrumb"> › <a href="{path_init}">Home</a>'
    main = parts[-1]
    parts = parts[:-1]
    for part in parts:
        path_init = f"{path_init}/{part}"
        a_comp = f'<a href="{path_init}/">{part}</a>'
        breadCrumbs = f"{breadCrumbs} › {a_comp}"
    breadCrumbs = f"{breadCrumbs} › <span>{main}</span></nav>"
    return breadCrumbs

def get_page_data(i,pdf_path,media_root=None,site_root=None):
    page_data = {}
    page_num_str = get_page_num_str(i)
    thumbnail_page_path = get_thumbnail(pdf_path,i)
    basename = os.path.basename(pdf_path)
    title,ext = os.path.splitext(basename)
    
    page_dir = os.path.dirname(thumbnail_page_path)
    json_path = os.path.join(page_dir, "info.json")
    thumbnail_page_url = path_to_url(thumbnail_page_path,media_root,site_root)
    thumbnail_html_url = path_to_url_info(thumbnail_page_path,media_root,site_root)
    text_page_path = get_text_path(pdf_path,i)
    text_page_url = path_to_url(text_page_path,media_root,site_root)
    text_page_text = read_from_file(text_page_path)
    analyze_result = analyze_page(pdf_path, i)
    text_summary = analyze_result.get("summary")          # short paragraph
    keywords = analyze_result.get("keywords",{}).get("primary") # keywords relevant to that page
    domain = site_root.split('://')[1]
    site_name = '.'.join(domain.split('.')[:-1])
    json_data={}
    if os.path.isfile(json_path):
        json_data = safe_load_from_json(json_path)

    page_title = f"{title} | {page_num_str} | {thumbnail_html_url}"
    page_data["title"] = json_data.get('title',page_title)
    page_data['href'] = thumbnail_html_url
    page_data['share_url'] = thumbnail_html_url
    page_data['thumbnail_link'] = thumbnail_page_url
    page_data['domain']=[domain]
    page_data['variants']=[site_root]
    page_data['text'] = text_page_text
    page_data['description'] = json_data.get('description',text_summary)
    page_data['keywords'] = json_data.get('keywords',keywords)
    page_data['creator'] = site_name
    page_data['author'] = f'@{site_name}'
    page_data['site'] = site_root
    page_data['site_name'] = site_name
    page_data['keywords_str']= ','.join(page_data['keywords'])
    
    meta = get_meta_info(info=page_data)
    page_data["page_url"] = thumbnail_html_url
    
    page_data["alt"] = json_data.get('alt',page_data['title'])
    page_data["caption"] = json_data.get('caption',text_summary)
    page_data["schema"] = meta.get("og", {})
    page_data["schema"]['site_name'] = domain
    page_data["social_meta"] = meta.get("twitter", {})
    page_data["other"] = meta.get("other")
    page_data['meta']= meta
    return page_data

def build_meta_tags(meta: dict, image_url: str, title: str, text: str = "",path=None,media_root=None,site_root=None):
    
    meta['variants'] = [site_root]
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

    breadcrumbs = create_bread_crumbs(path,media_root,site_root) if path else ""
    description = meta.get("description", "")
    keywords    = meta.get("keywords", "")
    canonical   = meta.get("canonical", image_url)
    meta_tags = generate_meta_tags(meta, base_url=site_root, json_path=None)

    tags_html = ""
    for t in (art.get("tag") or []):
        tags_html += f'<span class="card-tag">{t}</span>'
    return  f"""  <meta charset="{other.get('charset', 'UTF-8')}">
  <meta name="viewport" content="{other.get('viewport', 'width=device-width,initial-scale=1')}">
  <meta name="theme-color" content="{other.get('theme_color', '#FFFFFF')}">
  <meta name="color-scheme" content="{other.get('color_scheme', 'light')}">
  {meta_tags}"""
def get_meta_tags(page_num,pdf_path,media_root,site_root):
    meta = get_page_data(page_num,pdf_path,media_root=media_root,site_root=site_root)
    return build_meta_tags(meta=meta, image_url=meta.get("thumbnail_link"), title=meta.get("title"), text=meta.get('description'),path=pdf_path,media_root=media_root,site_root=site_root)
def build_image_html():
    page_data = get_page_data(page_num,pdf_path,media_root=media_root,site_root=site_root)
    meta = build_meta_tags(meta=meta, image_url=meta.get("thumbnail_link"), title=meta.get("title"), text=meta.get('description'),path=pdf_path,media_root=media_root,site_root=site_root)

    
    write_atomic(
        json_path,
        json.dumps(page_data, indent=2, ensure_ascii=False),
    )

    # HTML — one per thumbnail image
    html = build_image_html(page_data, thumbnail_page_url, page_data['title'],text_page_text,thumbnail_page_path)
    
