# Skill: Social Post

## Purpose
Post content across multiple social media platforms (Twitter/X, Facebook, Instagram)
using the social MCP server. Reads pending posts from `/Posts/Pending/`, posts them,
logs results, and updates the dashboard.

## Trigger
Run this skill when:
- The user asks to post something to social media
- There are files in `/Posts/Pending/` awaiting publication
- A scheduled social post time has arrived
- After creating a weekly briefing or completing a milestone worth sharing

## Steps

1. **Read `Company_Handbook.md`** — check social media guidelines, tone of voice,
   and any platform-specific rules or banned content.

2. **Check `/Posts/Pending/`** for pending post files:
   - Each file should have frontmatter with `platforms`, `content`, `image_url` (optional)
   - If no pending posts, check if the user has provided ad-hoc content to post

3. **For each pending post**, read the frontmatter and content:
   - `platforms`: comma-separated list (`twitter,facebook,instagram`)
   - `content`: the post text
   - `image_url`: (optional) publicly accessible image for Instagram
   - `scheduled_for`: (optional) only post if this datetime has passed

4. **Post to each platform** using the social MCP server tools:
   - **Twitter/X**: use `post_to_twitter` (max 280 chars; truncate or summarize if needed)
   - **Facebook**: use `post_to_facebook` (full content, optionally with link)
   - **Instagram**: use `post_to_instagram` (requires image_url; captions can be longer)
   - Log each result (success or failure) before moving to the next platform

5. **Handle failures gracefully**:
   - If one platform fails, continue with others (do not abort the whole batch)
   - Write a note at the bottom of the post file recording which platforms succeeded/failed
   - If all platforms fail, move the file to `/Posts/Failed/` with error details

6. **Move completed post files**:
   - Success (all platforms posted): move to `/Posts/Done/`
   - Partial success: move to `/Posts/Done/` with failure notes in the file
   - Total failure: move to `/Posts/Failed/`

7. **Update `Dashboard.md`**:
   - Add a row to Recent Activity for each successful post
   - Note the platforms and timestamp

8. **Report back** a summary:
   - How many posts were published
   - Which platforms succeeded/failed
   - Any content that exceeded character limits

## Post File Format

Posts in `/Posts/Pending/` should use this frontmatter format:

```markdown
---
type: social_post
platforms: twitter,facebook,instagram
image_url: https://example.com/image.jpg
scheduled_for: 2026-03-10T09:00:00Z
status: pending
---

Your post content goes here.

For Twitter, keep this under 280 characters or I'll truncate it to the first sentence.

#hashtag1 #hashtag2
```

## Platform-Specific Notes

### Twitter/X
- Hard limit: 280 characters
- If content is longer, truncate at last complete word before 277 chars and add "…"
- Do NOT post the image_url as part of the text (it wastes character space)
- Use `reply_to_tweet_id` for thread continuation

### Facebook
- No character limit for organic posts
- Can include a `link` parameter (URL preview will be generated)
- Works best with a strong opening line (first 2 lines shown before "See More")

### Instagram
- Requires a public `image_url` (JPEG or PNG)
- Cannot post text-only to Instagram; skip gracefully if no image_url
- Caption can be long but first 125 chars show without "more" truncation
- Hashtags go at the end of the caption

## Example Output
```
Social Post Results:
  ✅ Twitter: "This week we launched our new AI Employee system! It's already..."
     → https://twitter.com/i/web/status/1234567890
  ✅ Facebook: Posted to page (ID: 123456789_987654321)
  ✅ Instagram: Media published (ID: 17854360227135492)

Moved to /Posts/Done/social_2026-03-10_product_launch.md

Dashboard updated. 3 platform posts logged.
```
