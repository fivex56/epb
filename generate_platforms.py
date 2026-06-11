"""
Generate static platform pages: /platforms/[id].html
Reads result.json, creates one HTML file per platform with embedded data.
"""
import json
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
PLATFORMS_DIR = BASE / "platforms"
RESULT_JSON = BASE / "result.json"

FEATURES = [
    ("api", "API"), ("telegram", "Telegram"), ("marketplace", "Marketplace"),
    ("autotopup", "Auto-topup"), ("usdt_trx", "USDT-TRX"), ("dapp", "dApp"),
    ("referral", "Referral"), ("staking", "Staking"), ("bandwidth", "Bandwidth"),
]

PLATFORM_FEATURES = {
    "apitrx": ["api","autotopup"], "brutus": ["marketplace","dapp"],
    "catfee": ["autotopup"], "energyfather": ["api","referral"],
    "ergon": ["dapp","staking"], "feee": ["api","referral","usdt_trx"],
    "feesaver": ["telegram","referral","autotopup"], "itrx": ["api","referral"],
    "justlend_dao": ["dapp","staking"], "mefree": ["api"],
    "netts": [], "refee": ["telegram","referral"],
    "renttron": [], "tofee": ["dapp"],
    "tr_energy": ["referral"], "tronex": ["api","telegram","referral"],
    "tronify": ["api","referral"], "tronmax": ["marketplace","api","referral"],
    "tronsave": ["staking"], "tronzap": ["referral"],
}

LOGOS = {
    "apitrx": "apitrx", "catfee": "catfee", "energyfather": "energyfather",
    "itrx": "itrx", "netts": "netts", "renttron": "RentTron",
    "tr_energy": "tr_energy", "tronex": "zapper", "tronzap": "zapper",
    "tronify": "f4c1c86b-91b6-421f-aa58-6b3023a028e8",
    "feesaver": "8bca1d9a-755c-4240-9701-0147518798b8",
    "mefree": "00711338-9ced-4140-bd06-d4980d78ba4c", "feee": "Frame 4",
}

TERMS = ["15m", "1h", "1d", "3d", "10d"]

HEADER_TOP = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>"""

HEADER_MID = """ — TRON Energy Review | Energy Price Board</title>
<meta name="robots" content="index,follow"/>
<link rel="canonical" href="https://energypriceboard.tech/platforms/"""

HEADER_END = """.html"/>
<meta property="og:title" content="{name} — TRON Energy Review"/>
<meta property="og:description" content="{og_desc}"/>
<meta property="og:url" content="https://energypriceboard.tech/platforms/{pid}.html"/>
<meta property="og:type" content="website"/><meta property="og:site_name" content="Energy Price Board"/>
<meta property="og:image" content="https://energypriceboard.tech/logos/epb_preview.webp"/>
<meta name="twitter:card" content="summary_large_image"/><meta name="twitter:site" content="@energypricebrd"/>
<meta name="twitter:title" content="{name} — TRON Energy Review"/>
<meta name="twitter:description" content="{og_desc}"/>
<meta name="twitter:image" content="https://energypriceboard.tech/logos/epb_preview.webp"/>
<link rel="icon" type="image/svg+xml" href="/favicon.svg"/><link rel="shortcut icon" href="/favicon.ico"/>
<meta name="google-site-verification" content="jXzvaa8jMF6f2N4VpfT0rfmwYdbFz553pV99v41m6uY"/>
<meta name="yandex-verification" content="45316677b3bc5338"/>
<script type="text/javascript">(function(m,e,t,r,i,k,a){{m[i]=m[i]||function(){{(m[i].a=m[i].a||[]).push(arguments)}};m[i].l=1*new Date();for(var j=0;j<document.scripts.length;j++){{if(document.scripts[j].src===r){{return;}}}}k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)}})(window,document,'script','https://mc.yandex.ru/metrika/tag.js?id=109720065','ym');ym(109720065,'init',{{ssr:true,webvisor:true,clickmap:true,ecommerce:"dataLayer",referrer:document.referrer,url:location.href,accurateTrackBounce:true,trackLinks:true}});</script>
<noscript><div><img src="https://mc.yandex.ru/watch/109720065" style="position:absolute;left:-9999px" alt=""/></div></noscript>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-CQ2WTT1T10"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-CQ2WTT1T10');</script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="preconnect" href="https://mc.yandex.ru"><link rel="preconnect" href="https://www.googletagmanager.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
<noscript><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet"></noscript>
"""

CSS = """<style>*,*::before,*::after{box-sizing:border-box}:root{--bg-dark:#0B0F19;--card-dark:#181E2C;--ink-white:#FFFFFF;--ink-secondary:#8A94A6;--ink-primary-light:#0F172A;--ink-secondary-light:#374151;--blue:#2F6BFA;--green:#16a34a;--line-dark:rgba(255,255,255,.08);--font:'Inter','Golos Text','SF Pro Display',-apple-system,sans-serif}html{height:100%}body{margin:0;min-height:100%;background:var(--bg-dark);color:var(--ink-white);font:400 15px/1.65 var(--font);-webkit-font-smoothing:antialiased}.container{max-width:900px;margin:0 auto;padding:0 32px}@media(max-width:768px){.container{padding:0 20px}}.nav{display:flex;align-items:center;justify-content:space-between;padding:20px 0;border-bottom:1px solid var(--line-dark);margin-bottom:32px}.nav-brand{font-size:19px;font-weight:800;letter-spacing:-.4px;text-decoration:none;color:var(--ink-white)}.nav-brand em{font-style:normal;color:var(--blue)}.nav-links{display:flex;gap:4px}.nav-links a{text-decoration:none;color:var(--ink-secondary);padding:7px 14px;border-radius:8px;font-size:13px;font-weight:500;transition:.2s}.nav-links a:hover{color:var(--ink-white);background:rgba(255,255,255,.06)}.breadcrumb{font-size:12px;color:var(--ink-secondary);margin-bottom:20px}.breadcrumb a{color:var(--ink-secondary);text-decoration:none}.breadcrumb a:hover{color:var(--blue)}h1{font-size:32px;font-weight:900;letter-spacing:-0.02em;margin:0 0 4px}.subtitle{color:var(--ink-secondary);font-size:14px;margin-bottom:24px}.prices-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:16px 0}@media(max-width:500px){.prices-grid{grid-template-columns:1fr}}.price-box{background:var(--card-dark);border:1px solid var(--line-dark);border-radius:10px;padding:14px 16px;text-align:center}.price-box .amount{font-size:11px;font-weight:700;color:var(--ink-secondary);text-transform:uppercase;letter-spacing:.4px;margin-bottom:4px}.price-box .value{font-size:24px;font-weight:800;color:var(--ink-white)}.price-box .best{color:var(--green)}.info-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;margin:16px 0}.info-item{background:var(--card-dark);border:1px solid var(--line-dark);border-radius:8px;padding:12px 14px}.info-item .il{font-size:10px;font-weight:700;color:var(--ink-secondary);text-transform:uppercase;letter-spacing:.4px;margin-bottom:2px}.info-item .iv{font-size:14px;font-weight:600}.info-item .iv.yes{color:var(--green)}.info-item .iv.no{color:rgba(255,255,255,.3)}.features-chips{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0}.f-chip{padding:4px 12px;border-radius:100px;font-size:11px;font-weight:600}.f-chip.has{background:rgba(34,197,94,.1);color:var(--green)}.f-chip.no{background:rgba(255,255,255,.04);color:var(--ink-secondary)}.cta-btn{display:inline-block;padding:12px 28px;border-radius:10px;font-weight:700;text-decoration:none;font-family:var(--font);font-size:14px;margin-top:16px;margin-right:8px}.cta-primary{background:var(--blue);color:#fff}.cta-primary:hover{background:#1a5ae6}.cta-secondary{background:rgba(255,255,255,.06);color:var(--ink-white);border:1px solid rgba(255,255,255,.15)}h2{font-size:20px;font-weight:700;margin:32px 0 10px}table{width:100%;border-collapse:collapse;font-size:14px}td{padding:6px 0;border-bottom:1px solid var(--line-dark)}.footer{border-top:1px solid var(--line-dark);padding:32px 0;margin-top:48px;display:flex;justify-content:space-between;align-items:center;font-size:13px;color:var(--ink-secondary);flex-wrap:wrap;gap:12px}.footer a{color:var(--ink-secondary);text-decoration:none}@media(max-width:768px){h1{font-size:24px}.nav{flex-direction:column;gap:12px;align-items:flex-start}.nav-links{flex-wrap:wrap}}</style>
"""

BODY_TOP = """</head>
<body>
<main><div class="container">
<nav class="nav" aria-label="Main navigation"><a href="/" class="nav-brand">Energy<em>Board</em></a><div class="nav-links"><a href="/">Board</a><a href="/compare.html">Compare</a><a href="/history.html">History</a><a href="/blog.html">Blog</a></div></nav>
<div class="breadcrumb"><a href="/">Home</a> / <a href="/compare.html">Compare</a> / <span>{name}</span></div>
<h1>{name} <span style="font-size:14px;color:{best_color};font-weight:600;vertical-align:middle">{best_badge}</span></h1>
<p class="subtitle">TRON energy rental platform — {desc_prices}</p>
<div class="prices-grid">
<div class="price-box"><div class="amount">65k · 1 Hour</div><div class="value{best_class}">{p65} TRX</div></div>
<div class="price-box"><div class="amount">130k · 1 Hour</div><div class="value">{p130} TRX</div></div>
</div>
<a class="cta-btn cta-primary" href="{ref_url}" target="_blank" rel="nofollow noopener">{cta_text}</a>
<a class="cta-btn cta-secondary" href="/compare.html">Compare All Platforms</a>
<h2>Features</h2><div class="features-chips">{feat_chips}</div>
<div class="info-grid">
<div class="info-item"><div class="il">API Access</div><div class="iv{api_cls}">{api_val}</div></div>
<div class="info-item"><div class="il">Telegram Bot</div><div class="iv{tg_cls}">{tg_val}</div></div>
<div class="info-item"><div class="il">Referral Program</div><div class="iv{ref_cls}">{ref_val}</div></div>
<div class="info-item"><div class="il">Minimum Order</div><div class="iv">{min_order}</div></div>
</div>
<h2>All Prices</h2><table>{price_rows}</table>
<p style="margin-top:16px;color:var(--ink-secondary);font-size:13px">Last updated: {ts}</p>
"""

BODY_BOTTOM = """</div></main>
<footer class="footer"><div class="container" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;width:100%"><span>© 2026 Energy Price Board</span><span><a href="/">Board</a> · <a href="/compare.html">Compare</a> · <a href="/blog.html">Blog</a></span></div></footer>
</body>
</html>"""

SCHEMA = """<script type="application/ld+json">{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"Energy Price Board","item":"https://energypriceboard.tech/"},{"@type":"ListItem","position":2,"name":"Compare","item":"https://energypriceboard.tech/compare.html"},{"@type":"ListItem","position":3,"name":"{name}"}]}</script>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Product","name":"{name} — TRON Energy Rental","description":"{og_desc}","url":"{ref_url}","offers":{"@type":"AggregateOffer","lowPrice":"{p65}","highPrice":"{p130}","priceCurrency":"TRX"}}</script>
"""

def fmt(n):
    if isinstance(n, (int, float)) and n > 0:
        return f"{n:.2f}"
    return "--"

def generate():
    data = json.loads(RESULT_JSON.read_text())
    platforms = data["platforms"] or []
    PLATFORMS_DIR.mkdir(exist_ok=True)

    # Find cheapest 65k for best badge
    with65 = [p for p in platforms if isinstance(p.get("65k_1h_price"), (int, float))]
    with65.sort(key=lambda p: p["65k_1h_price"])
    cheapest_price = with65[0]["65k_1h_price"] if with65 else None

    for p in platforms:
        pid = p["platform_id"]
        name = p.get("platform_name", pid)
        p65 = p.get("65k_1h_price")
        p130 = p.get("130k_1h_price")
        p65ok = isinstance(p65, (int, float))
        p130ok = isinstance(p130, (int, float))
        ref_url = p.get("referral_url") or p.get("url") or "/"
        has_ref = p.get("has_referral") and p.get("referral_url")
        ts = p.get("ts", "")
        if ts:
            ts = ts[:19].replace("T", " ")

        # Best price?
        is_best = p65ok and cheapest_price is not None and p65 == cheapest_price
        best_color = "var(--green)" if is_best else "var(--ink-secondary)"
        best_badge = "★ Best Price" if is_best else ""
        best_class = " best" if is_best else ""

        # Features
        pfeats = PLATFORM_FEATURES.get(pid, [])
        feat_chips = ""
        for fid, flabel in FEATURES:
            has = fid in pfeats
            feat_chips += f'<span class="f-chip{" has" if has else " no"}">{flabel}</span>'

        # Prices table
        price_rows = ""
        for t in TERMS:
            v65 = p.get(f"65k_{t}_price")
            v130 = p.get(f"130k_{t}_price")
            if isinstance(v65, (int, float)):
                price_rows += f'<tr><td>65k · {t}</td><td style="font-weight:700;color:var(--ink-white)">{fmt(v65)} TRX</td></tr>'
            if isinstance(v130, (int, float)):
                price_rows += f'<tr><td>130k · {t}</td><td style="font-weight:700;color:var(--ink-white)">{fmt(v130)} TRX</td></tr>'

        # Meta
        og_desc = f"Live {name} energy rental prices. 65k from {fmt(p65)} TRX, 130k from {fmt(p130)} TRX. Features, API availability, and real-time comparison."

        # CTA
        cta_text = "🎁 Rent Energy (Referral)" if has_ref else f"Visit {name}"
        desc_prices = f"live 65k/1h prices from {fmt(p65)} TRX"

        # Features info
        api_val = "✓ Yes" if "api" in pfeats else "--"
        api_cls = " yes" if "api" in pfeats else " no"
        tg_val = "✓ Yes" if "telegram" in pfeats else "--"
        tg_cls = " yes" if "telegram" in pfeats else " no"
        ref_val = "✓ Yes" if "referral" in pfeats else "--"
        ref_cls = " yes" if "referral" in pfeats else " no"
        min_order = p.get("minimum_order_energy") if p.get("minimum_order_energy") and p.get("minimum_order_energy") != "N/A" else "No limit"

        html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{name} — TRON Energy Review | Energy Price Board</title>
<meta name="description" content="{og_desc}"/>
<meta name="robots" content="index,follow"/>
<link rel="canonical" href="https://energypriceboard.tech/platforms/{pid}.html"/>
<meta property="og:title" content="{name} — TRON Energy Review"/>
<meta property="og:description" content="{og_desc}"/>
<meta property="og:url" content="https://energypriceboard.tech/platforms/{pid}.html"/>
<meta property="og:type" content="website"/><meta property="og:site_name" content="Energy Price Board"/>
<meta property="og:image" content="https://energypriceboard.tech/logos/epb_preview.webp"/>
<meta name="twitter:card" content="summary_large_image"/><meta name="twitter:site" content="@energypricebrd"/>
<meta name="twitter:title" content="{name} — TRON Energy Review"/>
<meta name="twitter:description" content="{og_desc}"/>
<meta name="twitter:image" content="https://energypriceboard.tech/logos/epb_preview.webp"/>
<link rel="icon" type="image/svg+xml" href="/favicon.svg"/><link rel="shortcut icon" href="/favicon.ico"/>
<meta name="google-site-verification" content="jXzvaa8jMF6f2N4VpfT0rfmwYdbFz553pV99v41m6uY"/>
<meta name="yandex-verification" content="45316677b3bc5338"/>
<script type="text/javascript">(function(m,e,t,r,i,k,a){{m[i]=m[i]||function(){{(m[i].a=m[i].a||[]).push(arguments)}};m[i].l=1*new Date();for(var j=0;j<document.scripts.length;j++){{if(document.scripts[j].src===r){{return;}}}}k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)}})(window,document,'script','https://mc.yandex.ru/metrika/tag.js?id=109720065','ym');ym(109720065,'init',{{ssr:true,webvisor:true,clickmap:true,ecommerce:"dataLayer",referrer:document.referrer,url:location.href,accurateTrackBounce:true,trackLinks:true}});</script>
<noscript><div><img src="https://mc.yandex.ru/watch/109720065" style="position:absolute;left:-9999px" alt=""/></div></noscript>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-CQ2WTT1T10"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-CQ2WTT1T10');</script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="preconnect" href="https://mc.yandex.ru"><link rel="preconnect" href="https://www.googletagmanager.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
<noscript><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet"></noscript>
{CSS}
</head>
<body>
<main><div class="container">
<nav class="nav" aria-label="Main navigation"><a href="/" class="nav-brand">Energy<em>Board</em></a><div class="nav-links"><a href="/">Board</a><a href="/compare.html">Compare</a><a href="/history.html">History</a><a href="/blog.html">Blog</a></div></nav>
<div class="breadcrumb"><a href="/">Home</a> / <a href="/compare.html">Compare</a> / <span>{name}</span></div>
<h1>{name} <span style="font-size:14px;color:{best_color};font-weight:600;vertical-align:middle">{best_badge}</span></h1>
<p class="subtitle">TRON energy rental platform — {desc_prices}</p>
<div class="prices-grid">
<div class="price-box"><div class="amount">65k · 1 Hour</div><div class="value{best_class}">{fmt(p65)} TRX</div></div>
<div class="price-box"><div class="amount">130k · 1 Hour</div><div class="value">{fmt(p130)} TRX</div></div>
</div>
<a class="cta-btn cta-primary" href="{ref_url}" target="_blank" rel="nofollow noopener">{cta_text}</a>
<a class="cta-btn cta-secondary" href="/compare.html">Compare All Platforms</a>
<h2>Features</h2><div class="features-chips">{feat_chips}</div>
<div class="info-grid">
<div class="info-item"><div class="il">API Access</div><div class="iv{api_cls}">{api_val}</div></div>
<div class="info-item"><div class="il">Telegram Bot</div><div class="iv{tg_cls}">{tg_val}</div></div>
<div class="info-item"><div class="il">Referral Program</div><div class="iv{ref_cls}">{ref_val}</div></div>
<div class="info-item"><div class="il">Minimum Order</div><div class="iv">{min_order}</div></div>
</div>
<h2>All Prices</h2><table>{price_rows}</table>
<p style="margin-top:16px;color:var(--ink-secondary);font-size:13px">Last updated: {ts}</p>
</div></main>
<footer class="footer"><div class="container" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;width:100%"><span>© 2026 Energy Price Board</span><span><a href="/">Board</a> · <a href="/compare.html">Compare</a> · <a href="/blog.html">Blog</a></span></div></footer>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{{"@type":"ListItem","position":1,"name":"Energy Price Board","item":"https://energypriceboard.tech/"}},{{"@type":"ListItem","position":2,"name":"Compare","item":"https://energypriceboard.tech/compare.html"}},{{"@type":"ListItem","position":3,"name":"{name}"}}]}}</script>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Product","name":"{name} — TRON Energy Rental","description":"{og_desc}","url":"{ref_url}","offers":{{"@type":"AggregateOffer","lowPrice":"{fmt(p65)}","highPrice":"{fmt(p130)}","priceCurrency":"TRX"}}}}</script>
</body>
</html>"""

        out_path = PLATFORMS_DIR / f"{pid}.html"
        out_path.write_text(html, encoding="utf-8")
        print(f"  {pid}.html — {name}")

    print(f"\nDone! {len(platforms)} platform pages in {PLATFORMS_DIR}/")


if __name__ == "__main__":
    generate()
