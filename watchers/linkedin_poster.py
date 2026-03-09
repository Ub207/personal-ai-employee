"""
linkedin_poster.py — Silver Tier Auto-Poster
=============================================
Automatically posts business updates to LinkedIn to generate sales.
Supports draft mode (requires approval) and auto-post mode.

Uses Playwright for browser automation of LinkedIn.

Usage:
    python linkedin_poster.py [--vault-path PATH] [--draft] [--dry-run]

Requirements:
    pip install playwright
    playwright install chromium

Setup:
    1. Install: pip install playwright && playwright install chromium
    2. First run: Login to LinkedIn manually when browser opens
    3. Session saved to: ~/.linkedin_session/

Content Sources:
    - /Vault/Posts/Pending/ — Markdown files with post content
    - Auto-generates from /Vault/Done/ achievements
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("LinkedInPoster")

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_VAULT = Path(__file__).resolve().parent.parent  # D:/bronze_tier

SESSION_PATH = Path.home() / ".linkedin_session"
POSTS_PENDING = DEFAULT_VAULT / "Posts" / "Pending"
POSTS_PUBLISHED = DEFAULT_VAULT / "Posts" / "Published"

DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
DRAFT_MODE = True  # Default to draft mode for safety


# ── Poster Class ──────────────────────────────────────────────────────────────
class LinkedInPoster:
    """Posts business updates to LinkedIn automatically."""

    def __init__(self, vault_path: Path, draft_mode: bool = True, dry_run: bool = False):
        self.vault = vault_path
        self.draft_mode = draft_mode
        self.dry_run = dry_run
        self.session_path = SESSION_PATH

        # Ensure folders exist
        POSTS_PENDING.mkdir(parents=True, exist_ok=True)
        POSTS_PUBLISHED.mkdir(parents=True, exist_ok=True)
        self.session_path.mkdir(parents=True, exist_ok=True)

    def get_pending_posts(self) -> list[Path]:
        """Get list of pending post files."""
        if not POSTS_PENDING.exists():
            return []
        return sorted(POSTS_PENDING.glob("*.md"))

    def read_post_content(self, file_path: Path) -> dict:
        """Parse markdown post file with frontmatter."""
        content = file_path.read_text(encoding="utf-8")

        # Extract frontmatter
        frontmatter = {}
        body = content

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                fm_text = parts[1].strip()
                body = parts[2].strip()
                for line in fm_text.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        frontmatter[key.strip()] = value.strip()

        return {
            "frontmatter": frontmatter,
            "content": body,
            "file_path": file_path,
            "title": frontmatter.get("title", file_path.stem),
            "hashtags": frontmatter.get("hashtags", "").split(",") if frontmatter.get("hashtags") else [],
        }

    def generate_post_from_achievements(self) -> list[dict]:
        """Auto-generate posts from completed tasks in /Done."""
        done_folder = self.vault / "Done"
        if not done_folder.exists():
            return []

        posts = []
        recent_files = sorted(done_folder.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)[:5]

        for file in recent_files:
            content = file.read_text(encoding="utf-8")
            # Extract first 200 chars as achievement summary
            first_line = content.split("\n")[0].replace("#", "").strip()

            post_content = f"""🎉 Just completed: {first_line}

This is part of our ongoing commitment to delivering excellence.

#Achievement #Business #Progress"""

            posts.append({
                "frontmatter": {"title": f"Achievement: {first_line[:50]}"},
                "content": post_content,
                "file_path": file,
                "hashtags": ["Achievement", "Business", "Progress"],
                "auto_generated": True,
            })

        return posts

    def create_post_file(self, content: str, title: str) -> Path:
        """Create a pending post file."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        safe_title = title.replace(" ", "_").replace("/", "_")[:50]
        post_file = POSTS_PENDING / f"POST_{timestamp}_{safe_title}.md"

        post_content = f"""---
title: {title}
created: {datetime.now().isoformat()}
status: pending
type: business_update
hashtags: Business,Update,Growth
---

{content}
"""
        post_file.write_text(post_content, encoding="utf-8")
        return post_file

    def publish_post(self, post_data: dict) -> bool:
        """Publish a post to LinkedIn using Playwright."""
        if self.dry_run:
            log.info(f"[DRY RUN] Would publish post: {post_data['title']}")
            log.info(f"[DRY RUN] Content preview:\n{post_data['content'][:200]}...")
            return True

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    str(self.session_path),
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                    ],
                )

                page = browser.pages[0] if browser.pages else browser.new_page()

                # Navigate to LinkedIn
                page.goto("https://www.linkedin.com/feed/", timeout=60000)

                try:
                    # Wait for feed to load
                    page.wait_for_selector('[data-id="share-box-start"]', timeout=30000)
                except PlaywrightTimeout:
                    log.warning("LinkedIn feed not loaded. May need manual login.")
                    browser.close()
                    return False

                # Click on "Start a post"
                try:
                    start_post = page.query_selector('[data-id="share-box-start"]')
                    if start_post:
                        start_post.click()
                        page.wait_for_timeout(2000)
                    else:
                        # Alternative selector
                        page.click('div[role="button"]', timeout=5000)
                        page.wait_for_timeout(2000)
                except Exception as e:
                    log.debug(f"Could not find post button: {e}")

                # Find and fill the post text area
                try:
                    # LinkedIn's editor element
                    editor = page.query_selector('div[contenteditable="true"][role="textbox"]')
                    if editor:
                        editor.fill(post_data["content"][:3000])  # LinkedIn limit
                        page.wait_for_timeout(1000)

                        if self.draft_mode:
                            log.info("Draft mode: Post content entered but not submitted.")
                            # Don't click post button in draft mode
                        else:
                            # Click Post button
                            post_button = page.query_selector('button[aria-label*="Post"]')
                            if post_button:
                                post_button.click()
                                page.wait_for_timeout(3000)
                                log.info("Post published successfully!")
                            else:
                                log.warning("Could not find Post button.")

                        browser.close()
                        return True
                    else:
                        log.warning("Could not find post editor.")
                        browser.close()
                        return False

                except Exception as e:
                    log.error(f"Error filling post content: {e}")
                    browser.close()
                    return False

        except Exception as e:
            log.error(f"Playwright error: {e}")
            return False

    def move_to_published(self, file_path: Path, success: bool):
        """Move post file to Published folder after posting."""
        if success:
            dest = POSTS_PUBLISHED / file_path.name
            file_path.rename(dest)
            log.info(f"Post moved to Published: {dest.name}")
        else:
            log.warning(f"Post failed, keeping in Pending: {file_path.name}")

    def update_dashboard(self, post_title: str, status: str):
        """Update Dashboard.md with post activity."""
        dashboard = self.vault / "Dashboard.md"
        if not dashboard.exists():
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        log_line = f"| {timestamp} | LinkedIn post | {post_title[:40]}... | {status} |\n"

        text = dashboard.read_text(encoding="utf-8")
        lines = text.split("\n")

        for i, line in enumerate(lines):
            if line.startswith("| 2026-03-09") or line.startswith("| 2026-03-04"):
                lines.insert(i, log_line)
                break
        else:
            lines.append(log_line)

        dashboard.write_text("\n".join(lines), encoding="utf-8")

    def run(self, auto_generate: bool = False):
        """Main posting workflow."""
        log.info("=" * 60)
        log.info("  AI Employee — LinkedIn Auto-Poster  (Silver Tier)")
        log.info("=" * 60)
        log.info(f"  Vault        : {self.vault}")
        log.info(f"  Draft mode   : {self.draft_mode}")
        log.info(f"  Dry run      : {self.dry_run}")
        log.info(f"  Session path : {self.session_path}")
        log.info("=" * 60)

        posts_to_publish = []

        # Get pending posts
        pending = self.get_pending_posts()
        if pending:
            log.info(f"Found {len(pending)} pending post(s).")
            for post_file in pending:
                post_data = self.read_post_content(post_file)
                posts_to_publish.append({**post_data, "file_path": post_file})

        # Auto-generate from achievements if enabled
        if auto_generate:
            log.info("Auto-generating posts from recent achievements...")
            auto_posts = self.generate_post_from_achievements()
            for post in auto_posts:
                # Save as pending first
                new_file = self.create_post_file(post["content"], post["frontmatter"].get("title", "Achievement"))
                log.info(f"Created auto-post: {new_file.name}")

        # Publish posts
        for post_data in posts_to_publish:
            log.info(f"Publishing: {post_data['title']}")
            success = self.publish_post(post_data)
            self.move_to_published(post_data["file_path"], success)
            self.update_dashboard(
                post_data["title"],
                "✅ Published" if success else "❌ Failed",
            )

        log.info("LinkedIn posting complete.")


# ── Runner ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Silver Tier LinkedIn Auto-Poster — publishes business updates."
    )
    parser.add_argument(
        "--vault-path",
        default=str(DEFAULT_VAULT),
        help=f"Path to Obsidian vault (default: {DEFAULT_VAULT})",
    )
    parser.add_argument(
        "--draft",
        action="store_true",
        default=DRAFT_MODE,
        help="Draft mode: prepare post but don't publish (default: True).",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-generate posts from /Done achievements.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=DRY_RUN,
        help="Log actions without posting (safe for testing).",
    )
    args = parser.parse_args()

    vault = Path(args.vault_path).resolve()

    if not vault.exists():
        log.error(f"Vault path does not exist: {vault}")
        sys.exit(1)

    poster = LinkedInPoster(
        vault_path=vault,
        draft_mode=args.draft,
        dry_run=args.dry_run,
    )
    poster.run(auto_generate=args.auto)


if __name__ == "__main__":
    main()
