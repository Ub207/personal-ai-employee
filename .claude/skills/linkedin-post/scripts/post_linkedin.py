#!/usr/bin/env python3
"""
post_linkedin.py — linkedin-post skill script
Posts to LinkedIn using Playwright browser automation.
Usage: python post_linkedin.py --content "Your post text here"
"""

import os
import sys
import argparse
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
except ImportError:
    pass

LINKEDIN_EMAIL    = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")
DRY_RUN           = os.getenv("DRY_RUN", "true").lower() == "true"


def post_to_linkedin(content: str) -> bool:
    if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
        print("ERROR: LINKEDIN_EMAIL or LINKEDIN_PASSWORD not set in .env")
        return False

    if DRY_RUN:
        print(f"[DRY RUN] Would post to LinkedIn:")
        print(f"  Content: {content[:120]}...")
        return True

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Login
        page.goto("https://www.linkedin.com/login")
        page.fill("#username", LINKEDIN_EMAIL)
        page.fill("#password", LINKEDIN_PASSWORD)
        page.click('[type=submit]')
        page.wait_for_url("**/feed/**", timeout=15000)

        # Open post dialog
        page.click('.share-box-feed-entry__trigger')
        page.wait_for_selector('.ql-editor', timeout=10000)
        page.fill('.ql-editor', content)

        # Submit
        page.click('button[data-control-name="share.post"]')
        page.wait_for_timeout(3000)

        browser.close()

    print(f"LinkedIn post published successfully.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--content", required=True, help="Post content text")
    args = parser.parse_args()

    success = post_to_linkedin(args.content)
    sys.exit(0 if success else 1)
