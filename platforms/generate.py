#!/usr/bin/env python3
"""Generate SEO platform pages from result.json"""
import json, os

with open('../result.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

platforms = data['platforms']

TEMPLATE = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{name} — TRON Energy Rental Prices | Energy Price Board</title>
<meta name="description" content="{name} TRON energy rental prices. Compare 65k and 130k energy rates for 1 hour rental. {extra_desc}"/>
<meta name="robots" content="index,follow"/>
<link rel="canonical" href="https://energypriceboard.tech/platforms/{slug}.html"/>
<meta property="og:title" content="{name} — Energy Price Board"/>
<meta property="og:description" content="{name} TRON energy rental prices and tariff details."/>
<meta property="og:url" content="https://energypriceboard.tech/platforms/{slug}.html"/>
<meta property="og:type" content="website"/>
<!-- Yandex.Metrika -->
<script type="text/javascript">
(function(m,e,t,r,i,k,a){{m[i]=m[i]||function(){{(m[i].a=m[i].a||[]).push(arguments)}};m[i].l=1*new Date();for(var j=0;j<document.scripts.length;j++){{if(document.scripts[j].src===r){{return;}}}}k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)}})(window,document,'script','https://mc.yandex.ru/metrika/tag.js?id=109720065','ym');
ym(109720065,'init',{{ssr:true,webvisor:true,clickmap:true,ecommerce:"dataLayer",referrer:document.referrer,url:location.href,accurateTrackBounce:true,trackLinks:true}});
</script>
<noscript><div><img src="https://mc.yandex.ru/watch/109720065" style="position:absolute;left:-9999px" alt=""/></div></noscript>
<!-- /Yandex.Metrika -->
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-CQ2WTT1T10"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-CQ2WTT1T10');</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box}}
:root{{
  --bg-dark:#0B0F19;--card-dark:#181E2C;--ink-white:#FFFFFF;
  --ink-secondary:#8A94A6;--blue:#2F6BFA;--purple:#5936FA;
  --line-dark:rgba(255,255,255,.08);--radius-card:20px;
  --font:'Inter','Golos Text','SF Pro Display',-apple-system,sans-serif;
}}
html{{height:100%}}
body{{
  margin:0;min-height:100%;background:var(--bg-dark);color:var(--ink-white);
  font:400 15px/1.6 var(--font);-webkit-font-smoothing:antialiased;
}}
.container{{max-width:960px;margin:0 auto;padding:0 24px}}
.nav{{
  display:flex;align-items:center;justify-content:space-between;
  padding:22px 0;border-bottom:1px solid var(--line-dark);margin-bottom:40px;
}}
.nav-brand{{font-size:21px;font-weight:800;letter-spacing:-.4px;text-decoration:none;color:var(--ink-white)}}
.nav-brand em{{font-style:normal;color:var(--blue)}}
.nav-links{{display:flex;gap:4px}}
.nav-links a{{
  text-decoration:none;color:var(--ink-secondary);padding:8px 16px;
  border-radius:8px;font-size:14px;font-weight:500;transition:.2s;
}}
.nav-links a:hover{{color:var(--ink-white);background:rgba(255,255,255,.06)}}
h1{{font-size:36px;font-weight:900;letter-spacing:-0.02em;margin:0 0 8px}}
h1 span{{background:linear-gradient(135deg,#FFFFFF 40%,var(--blue) 90%);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.subtitle{{font-size:16px;color:var(--ink-secondary);margin-bottom:36px}}
.card{{
  background:var(--card-dark);border:1px solid var(--line-dark);border-radius:var(--radius-card);
  padding:32px;margin-bottom:24px;
}}
.card h2{{font-size:22px;font-weight:800;margin:0 0 20px;color:var(--ink-white)}}
.tbl{{width:100%;border-collapse:collapse;font-size:14px}}
.tbl th{{
  text-align:left;padding:10px 14px;color:var(--ink-secondary);
  font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.5px;
  border-bottom:1px solid var(--line-dark);
}}
.tbl td{{
  padding:10px 14px;border-bottom:1px solid rgba(255,255,255,.03);
  font-variant-numeric:tabular-nums;
}}
.tbl td.price{{font-weight:800;color:var(--ink-white)}}
.tbl td.na{{color:#5A5E68}}
.btn{{
  display:inline-flex;align-items:center;gap:8px;padding:14px 28px;
  border-radius:12px;font-size:15px;font-weight:700;text-decoration:none;
  transition:all .2s;font-family:var(--font);
  background:var(--blue);color:#fff;border:none;cursor:pointer;
}}
.btn:hover{{background:#1a5ae6;transform:translateY(-1px)}}
.btn-outline{{
  background:transparent;border:1px solid rgba(255,255,255,.15);color:var(--ink-white);
}}
.btn-outline:hover{{background:rgba(255,255,255,.06)}}
.cta-row{{display:flex;gap:12px;flex-wrap:wrap;margin-top:8px}}
.disclaimer{{
  font-size:12px;color:var(--ink-secondary);padding:20px 0 40px;line-height:1.7;
}}
.footer{{
  border-top:1px solid var(--line-dark);padding:28px 0 36px;
  display:flex;flex-wrap:wrap;justify-content:space-between;gap:24px;
}}
.footer a{{color:var(--ink-secondary);text-decoration:none;font-size:13px;transition:.12s}}
.footer a:hover{{color:var(--blue)}}
@media(max-width:768px){{
  .nav{{flex-direction:column;gap:12px;align-items:flex-start}}
  h1{{font-size:26px}}
  .card{{padding:20px}}
}}
</style>
</head>
<body>
<div class="container">
  <nav class="nav">
    <a href="/" class="nav-brand">Energy<em>Board</em></a>
    <div class="nav-links">
      <a href="/">Board</a>
      <a href="/explorer.html">Explorer</a>
      <a href="/history.html">History</a>
      <a href="/blog.html">Blog</a>
    </div>
  </nav>

  <h1><span>{name}</span></h1>
  <p class="subtitle">TRON energy rental platform — current tariffs &amp; prices</p>

  <div class="card">
    <h2>Platform Info</h2>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:14px">
      <div><span style="color:var(--ink-secondary)">Website:</span> {website_html}</div>
      {ref_info}
      {capacity_html}
      {limits_html}
    </div>
    {cta_html}
  </div>

  <div class="card">
    <h2>Energy Rental Prices (65k Energy)</h2>
    <table class="tbl">
      <tr><th>Duration</th><th>Price (TRX)</th></tr>
      {rows_65k}
    </table>
  </div>

  <div class="card">
    <h2>Energy Rental Prices (130k Energy)</h2>
    <table class="tbl">
      <tr><th>Duration</th><th>Price (TRX)</th></tr>
      {rows_130k}
    </table>
  </div>

  <p class="disclaimer">
    ⚠️ <strong>Disclaimer:</strong> All price data is collected from publicly available open sources.
    Prices are updated periodically but may not reflect real-time changes. Always verify on the official platform
    before making a purchase. Energy Price Board is not affiliated with {name} and does not guarantee
    the accuracy of the displayed information. Some links may contain referral codes.
  </p>

  <footer class="footer">
    <div><span style="font-size:11px;color:var(--ink-secondary)">© 2026 Energy Price Board</span></div>
    <div>
      <a href="/terms.txt">Terms</a> · <a href="/privacy.txt">Privacy</a> · <a href="/disclaimer.txt">Disclaimer</a>
    </div>
  </footer>
</div>
</body>
</html>
'''

TERMS = ['15m','1h','1d','3d','10d']

for p in platforms:
    pid = p['platform_id']
    name = p['platform_name'] or pid
    slug = pid
    url = p.get('url','')
    ref = p.get('referral_url','')
    has_ref = p.get('has_referral', False)

    # Website link: use ref if available, otherwise direct url
    website_url = ref if has_ref else url
    website_html = '<a href="{}" target="_blank" rel="nofollow noopener" style="color:var(--blue);text-decoration:none;font-weight:600">{}</a>'.format(website_url, website_url) if website_url else '<span style="color:var(--ink-secondary)">Not available</span>'

    ref_info = ''
    if has_ref and ref:
        ref_info = '<div><span style="color:var(--ink-secondary)">Referral deal:</span> <span style="color:#7CEE7C;font-weight:700">✓ Active</span></div>'

    capacity = p.get('platform_max_energy', 'N/A')
    capacity_html = ''
    if capacity and capacity != 'N/A':
        cap_str = '{:.1f}M'.format(capacity/1e6) if capacity >= 1e6 else '{:.0f}k'.format(capacity/1e3)
        capacity_html = '<div><span style="color:var(--ink-secondary)">Total capacity:</span> <span style="color:var(--ink-white)">{}</span></div>'.format(cap_str)

    limits_html = ''
    min_e = p.get('minimum_order_energy', 'N/A')
    max_e = p.get('maximum_order_energy', 'N/A')
    if min_e and min_e != 'N/A':
        limits_html += '<div><span style="color:var(--ink-secondary)">Min order:</span> <span style="color:var(--ink-white)">{:,}</span></div>'.format(min_e)
    if max_e and max_e != 'N/A':
        max_str = '{:.0f}M'.format(max_e/1e6) if max_e >= 1e6 else '{:,}'.format(max_e)
        limits_html += '<div><span style="color:var(--ink-secondary)">Max order:</span> <span style="color:var(--ink-white)">{}</span></div>'.format(max_str)

    cta_html = ''
    if has_ref and ref:
        cta_html = '<div class="cta-row"><a class="btn" href="{}" target="_blank" rel="nofollow noopener">Rent Energy on {}</a><a class="btn btn-outline" href="/">← Back to Price Board</a></div>'.format(ref, name)
    elif url:
        cta_html = '<div class="cta-row"><a class="btn" href="{}" target="_blank" rel="nofollow">Visit {}</a><a class="btn btn-outline" href="/">← Back to Price Board</a></div>'.format(url, name)
    else:
        cta_html = '<div class="cta-row"><a class="btn btn-outline" href="/">← Back to Price Board</a></div>'

    # Build price rows
    rows_65k = ''
    any_65k = False
    for t in TERMS:
        key = '65k_{}_price'.format(t)
        val = p.get(key, 'N/A')
        if isinstance(val, (int, float)):
            rows_65k += '<tr><td>{} hour</td><td class="price">{:.4f} TRX</td></tr>\n'.format(t, val)
            any_65k = True
        else:
            rows_65k += '<tr><td>{}</td><td class="na">N/A</td></tr>\n'.format(t)
    if not any_65k:
        rows_65k = '<tr><td colspan="2" style="color:var(--ink-secondary);text-align:center;padding:20px">No price data available for 65k energy</td></tr>'

    rows_130k = ''
    any_130k = False
    for t in TERMS:
        key = '130k_{}_price'.format(t)
        val = p.get(key, 'N/A')
        if isinstance(val, (int, float)):
            rows_130k += '<tr><td>{} hour</td><td class="price">{:.4f} TRX</td></tr>\n'.format(t, val)
            any_130k = True
        else:
            rows_130k += '<tr><td>{}</td><td class="na">N/A</td></tr>\n'.format(t)
    if not any_130k:
        rows_130k = '<tr><td colspan="2" style="color:var(--ink-secondary);text-align:center;padding:20px">No price data available for 130k energy</td></tr>'

    extra_desc = 'All available tariffs and current rates.' if (any_65k or any_130k) else 'Check availability and rates.'

    html = TEMPLATE.format(
        name=name, slug=slug,
        website_html=website_html, ref_info=ref_info,
        capacity_html=capacity_html, limits_html=limits_html,
        cta_html=cta_html, rows_65k=rows_65k, rows_130k=rows_130k,
        extra_desc=extra_desc
    )

    path = os.path.join('.', '{}.html'.format(slug))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print('Generated: {}'.format(path))

print('\nDone! {} pages created.'.format(len(platforms)))
