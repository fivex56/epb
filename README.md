# ⚡ Energy Price Board — TRON Energy Rental Comparison

Live price comparison of **20+ TRON energy rental platforms**. Find the cheapest 65k/130k energy for 1-hour rental. Instant.

<p align="center">
  <strong>🌐 <a href="https://energypriceboard.tech">energypriceboard.tech</a></strong>
</p>

## How It Works

```
Scraper fleet (20 platforms) → aggregate.py → fill_prices.py → result.json → upload → live site
                                    ↓
                              history_7d.json (time-series)
                              history_30d.json
```

### Scrapers
- **12 Playwright** (headless Chrome): FeeSaver, CatFee, NETTS, RentTron, Tofee, Brutus, Ergon, etc.
- **6 REST API**: iTRX, Feee.io, Tronex Energy, Tronify, MeFree, TR Energy
- **2 dApp interaction**: Brutus (types amount, clicks duration, reads SUN), TronMax (marketplace SUN rates via API)
- **1 generic fallback**: scans page text for TRX prices

### Data Pipeline
- `epb_runner.py` orchestrates the full cycle: scrape all → aggregate → fill missing → ingest history → upload
- `fill_prices.py` fills N/A slots using market median ratios: 130k ≈ 2× 65k, 1d ≈ 1.67× 1h, 3d = 1d×3, 10d = 1d×10
- Atomic upload via WinSCP with `.tmp` rename

## Pages

| Page | Description |
|------|-------------|
| `index.html` | Main board — hero stats, dashboard, energy calculator, all platforms grid |
| `explorer.html` | Price matrix with per-column min highlighting |
| `history.html` | Heatmap, rankings, historical charts, price change tracking |
| `blog.html` | 4 technical articles about TRON energy |
| `platforms/*.html` | 19 SEO pages for individual platforms |

## Architecture

```
Energy_sbor/
├── *_scraper.py          # Individual platform scrapers (Playwright / API)
├── base_scraper.py        # Base class
├── base_playwright_scraper.py  # Playwright base with generic fallback
├── aggregate.py           # Collects all *_prices.json → result.json
├── fill_prices.py         # Fills N/A prices from market ratios
├── epb_runner.py          # Orchestrator — continuous loop
├── epb_ingest.py          # Time-series ingestion → history_*.json
├── generate_logos.py      # Platform logo generator
├── index.html             # Main page
├── explorer.html          # Price matrix explorer
├── history.html           # Historical trends & analytics
├── blog.html              # Technical blog
├── platforms/             # SEO platform pages
├── logos/                 # Platform logo images
├── start_background.bat   # Windows startup script
├── run_upload.bat         # WinSCP upload trigger
└── run_once.bat           # One-off scrape cycle
```

## Price Calculation

All platforms use **SUN** (internal TRON unit). Conversion:
```
price TRX = energy_amount × SUN_rate / 1_000_000
```

Where available, scrapers read actual SUN rates from API or DOM. Otherwise fallback scans page for TRX numbers.

## Stack

- **Scraping**: Playwright (headless Chromium), Python `requests`
- **Frontend**: Vanilla JS + CSS Grid, Inter font, Chart.js
- **Server**: Static HTML + JSON on shared hosting (nginx)
- **Analytics**: Yandex.Metrika + Google Analytics
- **Deploy**: WinSCP FTPES with atomic `.tmp` rename

## Running Locally

```bash
# Single scraper
python catfee_scraper.py

# Full cycle once
python epb_runner.py --once

# Continuous mode (every N minutes)
python epb_runner.py --continuous --timeout 5 --wait 2

# Windows background
start_background.bat
```

## Environment Variables

Some scrapers use API keys. Set these env vars (or hardcode for local use):
```
ITRX_API_KEY=your_key
ITRX_API_SECRET=your_secret
TRONEX_API_KEY=your_key
```

## License

MIT — do whatever you want. Energy should be cheap for everyone.

---

Built by Energy Price Board team · [Telegram](https://t.me/energypriceboard) · [X/Twitter](https://x.com/epbfish) · [team@energypriceboard.tech](mailto:team@energypriceboard.tech)
