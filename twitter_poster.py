"""
Twitter/X Auto-Poster for Energy Price Board
Posts 1 tweet/day at random working hours.
Run with --loop to post continuously on schedule.
"""
import os
import re
import json
import time
import random
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

import requests

# === CONFIG ===
BASE_DIR = Path(__file__).parent
POSTS_FILE = BASE_DIR / "promo" / "twitter_posts.md"
POSTED_TRACKER = BASE_DIR / "posted_tweets.json"
API_URL = "https://api.twitter.com/2/tweets"
DRY_RUN = os.environ.get("TWITTER_DRY_RUN", "0") == "1"

# Skip these platforms until a certain date (YYYY-MM-DD)
SKIP_UNTIL = {
    "TronMax": "2026-06-17",
}


def load_dotenv():
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    val = val.strip().strip('"').strip("'")
                    if key not in os.environ:
                        os.environ[key] = val


def refresh_access_token():
    """Use refresh token to get a new OAuth 2.0 access token."""
    client_id = os.environ.get("TWITTER_CLIENT_ID", "")
    refresh_token = os.environ.get("TWITTER_REFRESH_TOKEN", "")
    if not client_id or not refresh_token:
        raise ValueError("Missing TWITTER_CLIENT_ID or TWITTER_REFRESH_TOKEN")

    resp = requests.post(
        "https://api.twitter.com/2/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if resp.status_code == 200:
        data = resp.json()
        new_token = data["access_token"]
        new_refresh = data.get("refresh_token", refresh_token)
        os.environ["TWITTER_ACCESS_TOKEN"] = new_token
        os.environ["TWITTER_REFRESH_TOKEN"] = new_refresh
        print("[auth] Token refreshed")
        return new_token
    else:
        raise ValueError(f"Token refresh failed: {resp.status_code} {resp.text}")


def get_auth():
    """OAuth 2.0 Bearer token auth."""
    token = os.environ.get("TWITTER_ACCESS_TOKEN", "")
    if not token:
        raise ValueError("Missing TWITTER_ACCESS_TOKEN")
    return {"Authorization": f"Bearer {token}"}


def parse_posts():
    """Parse twitter_posts.md into list of tweets."""
    text = POSTS_FILE.read_text(encoding="utf-8")

    posts = []

    # Find all ## @handle - Platform sections
    # The dash could be em-dash, en-dash, or regular dash
    section_pattern = re.compile(
        r'^## (@\w+)\s+[-–—]\s+(.+?)$\n(.*?)(?=^## |\Z)',
        re.MULTILINE | re.DOTALL
    )

    for match in section_pattern.finditer(text):
        handle = match.group(1).strip().lstrip("@")
        platform_name = match.group(2).strip()
        section_content = match.group(3).strip()

        # Skip "General posts" header
        if handle.lower() == "general" or "general posts" in platform_name.lower():
            continue

        # Parse individual posts: **Post N (...)**
        post_blocks = re.split(r"\n\*\*Post \d+[^*]*\*\*\n", section_content)

        for block in post_blocks:
            block = block.strip()
            if not block:
                continue
            # Join lines, skip empty ones and title lines
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            # Remove "**Post N (...):**" title if present
            lines = [l for l in lines if not l.startswith("**Post")]
            tweet_text = " ".join(lines)

            if tweet_text and len(tweet_text) > 10:
                posts.append({
                    "handle": handle,
                    "platform": platform_name,
                    "text": tweet_text,
                    "hash": hashlib.md5(tweet_text.encode()).hexdigest()[:12],
                })

    # Parse "General posts" section (no handle)
    general_match = re.search(r'^## General posts.*?\n(.*)',
                              text, re.MULTILINE | re.DOTALL)
    if general_match:
        general_text = general_match.group(1).strip()
        general_blocks = re.split(r"\n\*\*Post \d+[^*]*\*\*\n", general_text)
        for block in general_blocks:
            block = block.strip()
            if not block:
                continue
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            tweet_text = " ".join(lines)
            if tweet_text and len(tweet_text) > 10:
                posts.append({
                    "handle": None,
                    "platform": "General",
                    "text": tweet_text,
                    "hash": hashlib.md5(tweet_text.encode()).hexdigest()[:12],
                })

    return posts


def load_tracker():
    if POSTED_TRACKER.exists():
        return json.loads(POSTED_TRACKER.read_text())
    return {"posted": [], "last_platform": None}


def save_tracker(tracker):
    POSTED_TRACKER.write_text(json.dumps(tracker, indent=2, ensure_ascii=False))


def should_skip(post):
    platform = post["platform"]
    if platform in SKIP_UNTIL:
        until = datetime.strptime(SKIP_UNTIL[platform], "%Y-%m-%d")
        if datetime.now() < until:
            return True
    return False


def pick_next_post(posts, tracker):
    posted_hashes = set(tracker["posted"])
    available = [p for p in posts if p["hash"] not in posted_hashes]
    available = [p for p in available if not should_skip(p)]

    if not available:
        print("[!] All posts tweeted. Resetting...")
        tracker["posted"] = []
        available = [p for p in posts if not should_skip(p)]

    last_plat = tracker.get("last_platform")
    others = [p for p in available if p["platform"] != last_plat]
    if others:
        available = others

    return random.choice(available)


def post_tweet(text: str) -> dict:
    headers = {"Authorization": f"Bearer {os.environ.get('TWITTER_ACCESS_TOKEN', '')}",
               "Content-Type": "application/json"}
    resp = requests.post(API_URL, json={"text": text}, headers=headers, timeout=30)

    if resp.status_code == 201:
        data = resp.json()
        tid = data["data"]["id"]
        print(f"[OK] Posted! ID: {tid}")
        safe = text[:120].encode('ascii', errors='replace').decode()
        print(f"     {safe}...")
        return {"id": tid, "status": "posted"}
    elif resp.status_code == 401:
        # Token expired — refresh and retry once
        print("[auth] Token expired, refreshing...")
        refresh_access_token()
        headers["Authorization"] = f"Bearer {os.environ['TWITTER_ACCESS_TOKEN']}"
        resp = requests.post(API_URL, json={"text": text}, headers=headers, timeout=30)
        if resp.status_code == 201:
            data = resp.json()
            print(f"[OK] Posted! ID: {data['data']['id']}")
            return {"id": data["data"]["id"], "status": "posted"}
        else:
            print(f"[FAIL] HTTP {resp.status_code}: {resp.text[:300]}")
            return {"id": None, "status": "failed", "error": resp.text}
    else:
        print(f"[FAIL] HTTP {resp.status_code}: {resp.text[:300]}")
        return {"id": None, "status": "failed", "error": resp.text}


def schedule_next_run():
    now = datetime.now()
    rand_hour = random.randint(9, 20)
    rand_min = random.randint(0, 59)
    target = now.replace(hour=rand_hour, minute=rand_min, second=0, microsecond=0)

    if target <= now:
        target += timedelta(days=1)
        rand_hour = random.randint(9, 20)
        rand_min = random.randint(0, 59)
        target = target.replace(hour=rand_hour, minute=rand_min)

    delay = (target - now).total_seconds()
    print(f"[next] Scheduled: {target.strftime('%Y-%m-%d %H:%M')} "
          f"(in {delay/3600:.1f}h)")
    return delay


def main():
    print(f"=== @energypricebrd Poster === {datetime.now():%Y-%m-%d %H:%M:%S}")

    posts = parse_posts()
    print(f"[+] {len(posts)} tweets loaded")

    tracker = load_tracker()
    remaining = len(posts) - len(tracker["posted"])
    print(f"[+] Posted: {len(tracker['posted'])}, remaining: {remaining}")

    skipped = [p for p in posts if should_skip(p)]
    for s in skipped:
        until = SKIP_UNTIL.get(s["platform"], "?")
        print(f"[skip] {s['platform']} until {until}")

    chosen = pick_next_post(posts, tracker)
    tag = f"@{chosen['handle']}" if chosen.get("handle") else "(general)"
    print(f"[>] [{chosen['platform']}] {tag}")
    safe_text = chosen['text'][:140].encode('ascii', errors='replace').decode()
    print(f"    {safe_text}")

    if DRY_RUN:
        print("[dry] Not posting")
        return

    result = post_tweet(chosen["text"])
    if result["status"] == "posted":
        tracker["posted"].append(chosen["hash"])
        tracker["last_platform"] = chosen["platform"]
        save_tracker(tracker)
        print(f"[save] {len(tracker['posted'])}/{len(posts)} posted")
    else:
        print("[!] Failed, retry next run")


if __name__ == "__main__":
    load_dotenv()

    if len(os.sys.argv) > 1 and os.sys.argv[1] == "--loop":
        while True:
            try:
                main()
            except Exception as e:
                print(f"[!!] {e}")
            delay = schedule_next_run()
            print(f"[sleep] {delay/3600:.1f}h...")
            time.sleep(delay)
    else:
        main()
