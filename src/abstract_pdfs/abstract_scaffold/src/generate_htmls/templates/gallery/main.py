CARD_IMG = """\
        <a class="card" href="{href}">
          <img src="{img_url}" alt="{alt}" loading="lazy">
          <div class="card-body">
            <span class="card-title">{title}</span>
            {desc_html}
          </div>
        </a>"""

CARD_NO_IMG = """\
        <a class="card" href="{href}">
          <div class="card-body">
            <span class="card-title">{title}</span>
            {desc_html}
          </div>
        </a>"""

GALLERY_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{page_title} | thedailydialectics</title>
  <link rel="canonical" href="{canonical_url}">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: system-ui, sans-serif; background: #0d0d0d; color: #e0e0e0; padding: 2rem 1rem; }}
    nav.breadcrumb {{ font-size: .8rem; color: #888; margin-bottom: 2rem; }}
    nav.breadcrumb a {{ color: #aaa; text-decoration: none; }}
    nav.breadcrumb a:hover {{ color: #fff; }}
    h1 {{ font-size: 1.6rem; margin-bottom: 1.5rem; color: #f0f0f0; text-transform: capitalize; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem; max-width: 1200px; }}
    .card {{ background: #1a1a1a; border-radius: 8px; overflow: hidden; text-decoration: none;
             color: #e0e0e0; transition: transform .2s, box-shadow .2s; display: flex; flex-direction: column; }}
    .card:hover {{ transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,.4); }}
    .card img {{ width: 100%; height: 140px; object-fit: cover; display: block; flex-shrink: 0; }}
    .card-body {{ padding: .6rem .75rem; display: flex; flex-direction: column; gap: .35rem; flex: 1; }}
    .card-title {{ font-size: .85rem; color: #ccc; text-transform: capitalize; font-weight: 600; }}
    .card-desc {{ font-size: .75rem; color: #777; line-height: 1.45;
                  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
                  overflow: hidden; }}
    .card-tags {{ display: flex; flex-wrap: wrap; gap: .2rem; margin-top: auto; padding-top: .3rem; }}
    .card-tag {{ background: #222; border: 1px solid #2e2e2e; border-radius: 3px;
                  padding: .1rem .35rem; font-size: .65rem; color: #666; }}
  </style>
</head>
<body>
  <nav class="breadcrumb">{breadcrumbs}</nav>
  <h1>{heading}</h1>
  <div class="grid">
{cards}
  </div>
</body>
</html>"""
