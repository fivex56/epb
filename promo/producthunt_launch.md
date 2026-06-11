# Product Hunt Launch — Energy Price Board

## Tagline
Real-time TRON energy rental comparison across 20 platforms — find the cheapest deal in seconds

## Description
I got tired of opening 10 tabs every time I needed TRON energy for a USDT transfer. Prices change hourly and the spread between cheapest and most expensive platform is 3-5x. So I built a price board.

What it does:
- Tracks 20 TRON energy rental platforms in real time
- Shows live prices for 65k and 130k energy (15min to 10 day durations)
- Energy calculator: pick amount + duration → top 3 cheapest
- Feature filters: API, Telegram bot, Auto-topup, Marketplace, Referral, etc.
- Price history heatmap with color-coded drops
- Platform comparison matrix — all prices in one table

Tech: Python scrapers (Playwright + raw API), nginx, Chart.js, vanilla JS. Open source at github.com/fivex56/epb.

Why: A USDT TRC20 transfer burns ~14 TRX directly. With rented energy at 2.3 TRX — that's 84% savings. For a bot doing 50 transfers/day, that's $700/month saved. This board finds you the cheapest option every time.

Feedback welcome! What features would you add?

## First comment (post right after launching)
Hey Product Hunt! I built this because the TRON energy rental market is genuinely wild — 20 platforms, no central price discovery, and prices that change hourly. Some platforms charge 2.3 TRX, others 9.5 TRX for the exact same thing.

The stack: Python + Playwright scrapers run every 2 minutes, nginx serves static HTML with embedded JSON for SEO, and Chart.js handles the analytics. Everything is vanilla JS — no framework overhead.

It's free, no ads, no affiliate links (some platforms have referral programs but I mark those clearly). Open source at github.com/fivex56/epb.

Would love feedback on:
- What other platforms should I add?
- What features would make this a daily tool for you?
- Should I add a Telegram bot that alerts on price drops?

Ask me anything about TRON energy or building scrapers for 20 different platforms!

## Screenshots to upload
1. Main page with hero + stats + calculator
2. Compare tab with matrix table
3. Price history heatmap

## Launch timing
- Tuesday or Wednesday, 12:01 AM PST (Product Hunt resets at midnight)
- This gives a full 24h of visibility
