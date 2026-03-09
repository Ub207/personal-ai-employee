#!/usr/bin/env node
/**
 * social-mcp-server.js — Gold Tier MCP Server
 * ============================================
 * Model Context Protocol server for social media posting.
 * Supports Twitter/X (API v2), Facebook Pages, and Instagram Business.
 *
 * Usage:
 *   node social-mcp-server.js
 *
 * Configuration (env vars):
 *   TWITTER_BEARER_TOKEN, TWITTER_API_KEY, TWITTER_API_SECRET
 *   TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
 *   FB_PAGE_ID, FB_ACCESS_TOKEN
 *   IG_ACCOUNT_ID  (Instagram Business Account ID linked to FB page)
 *   DRY_RUN=true
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import dotenv from "dotenv";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import fs from "fs";
import crypto from "crypto";

// ── Bootstrap ─────────────────────────────────────────────────────────────────
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const vaultPath = join(__dirname, "..");
dotenv.config({ path: join(vaultPath, ".env") });

// ── Configuration ─────────────────────────────────────────────────────────────
const DRY_RUN = process.env.DRY_RUN === "true";

// Twitter
const TWITTER_API_KEY = process.env.TWITTER_API_KEY || "";
const TWITTER_API_SECRET = process.env.TWITTER_API_SECRET || "";
const TWITTER_ACCESS_TOKEN = process.env.TWITTER_ACCESS_TOKEN || "";
const TWITTER_ACCESS_SECRET = process.env.TWITTER_ACCESS_SECRET || "";
const TWITTER_BEARER_TOKEN = process.env.TWITTER_BEARER_TOKEN || "";

// Facebook / Instagram (Graph API)
const FB_PAGE_ID = process.env.FB_PAGE_ID || "";
const FB_ACCESS_TOKEN = process.env.FB_ACCESS_TOKEN || "";
const IG_ACCOUNT_ID = process.env.IG_ACCOUNT_ID || "";

const LOGS_DIR = join(vaultPath, "Logs");
const LOG_FILE = join(LOGS_DIR, "social_actions.json");

if (!fs.existsSync(LOGS_DIR)) {
  fs.mkdirSync(LOGS_DIR, { recursive: true });
}

// ── Audit Logging ─────────────────────────────────────────────────────────────

function logAction(entry) {
  let log = [];
  if (fs.existsSync(LOG_FILE)) {
    try {
      log = JSON.parse(fs.readFileSync(LOG_FILE, "utf-8"));
    } catch {
      log = [];
    }
  }
  log.push({ timestamp: new Date().toISOString(), ...entry });
  if (log.length > 2000) log = log.slice(-2000);
  fs.writeFileSync(LOG_FILE, JSON.stringify(log, null, 2), "utf-8");
}

// ── Twitter OAuth 1.0a Helpers ────────────────────────────────────────────────

/**
 * Generate OAuth 1.0a Authorization header for Twitter API v2 write operations.
 * The Twitter v2 API requires OAuth 1.0a User Context for posting tweets.
 */
function buildOAuth1Header(method, url, params = {}) {
  const oauthParams = {
    oauth_consumer_key: TWITTER_API_KEY,
    oauth_nonce: crypto.randomBytes(16).toString("hex"),
    oauth_signature_method: "HMAC-SHA1",
    oauth_timestamp: Math.floor(Date.now() / 1000).toString(),
    oauth_token: TWITTER_ACCESS_TOKEN,
    oauth_version: "1.0",
  };

  const allParams = { ...params, ...oauthParams };
  const sortedKeys = Object.keys(allParams).sort();
  const paramString = sortedKeys
    .map((k) => `${encodeURIComponent(k)}=${encodeURIComponent(allParams[k])}`)
    .join("&");

  const signatureBase = [
    method.toUpperCase(),
    encodeURIComponent(url),
    encodeURIComponent(paramString),
  ].join("&");

  const signingKey = `${encodeURIComponent(TWITTER_API_SECRET)}&${encodeURIComponent(TWITTER_ACCESS_SECRET)}`;
  const signature = crypto
    .createHmac("sha1", signingKey)
    .update(signatureBase)
    .digest("base64");

  oauthParams.oauth_signature = signature;

  const authHeader =
    "OAuth " +
    Object.keys(oauthParams)
      .sort()
      .map((k) => `${encodeURIComponent(k)}="${encodeURIComponent(oauthParams[k])}"`)
      .join(", ");

  return authHeader;
}

/**
 * Post a tweet using Twitter API v2 with OAuth 1.0a.
 */
async function twitterPostTweet(text, replyToId = null) {
  const url = "https://api.twitter.com/2/tweets";
  const body = { text };
  if (replyToId) body.reply = { in_reply_to_tweet_id: replyToId };

  const authHeader = buildOAuth1Header("POST", url, {});

  const response = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: authHeader,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  const data = await response.json();
  if (!response.ok || data.errors) {
    const errMsg = data.errors?.[0]?.message || data.detail || JSON.stringify(data);
    throw new Error(`Twitter API error: ${errMsg}`);
  }

  return data.data;
}

// ── Facebook Graph API Helpers ────────────────────────────────────────────────

const FB_GRAPH_BASE = "https://graph.facebook.com/v19.0";

async function fbApiPost(endpoint, params) {
  const url = `${FB_GRAPH_BASE}${endpoint}`;
  const body = { ...params, access_token: FB_ACCESS_TOKEN };

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await response.json();
  if (data.error) {
    throw new Error(`Facebook API error: ${data.error.message} (code ${data.error.code})`);
  }
  return data;
}

async function fbApiGet(endpoint, params = {}) {
  const qs = new URLSearchParams({ ...params, access_token: FB_ACCESS_TOKEN }).toString();
  const url = `${FB_GRAPH_BASE}${endpoint}?${qs}`;

  const response = await fetch(url);
  const data = await response.json();
  if (data.error) {
    throw new Error(`Facebook API error: ${data.error.message} (code ${data.error.code})`);
  }
  return data;
}

// ── MCP Server ────────────────────────────────────────────────────────────────

const server = new McpServer({
  name: "social-mcp",
  version: "1.0.0",
  description: "Social media posting for AI Employee (Twitter/X, Facebook, Instagram)",
});

// ── Tool: post_to_twitter ─────────────────────────────────────────────────────

server.tool(
  "post_to_twitter",
  "Post a tweet to Twitter/X using API v2 with OAuth 1.0a. Supports threads and replies.",
  {
    text: z
      .string()
      .max(280)
      .describe("Tweet text (max 280 characters)"),
    reply_to_tweet_id: z
      .string()
      .optional()
      .describe("Tweet ID to reply to (for threads)"),
  },
  async ({ text, reply_to_tweet_id }) => {
    try {
      if (DRY_RUN) {
        const result = { dry_run: true, message: `DRY_RUN: Would post tweet: "${text}"`, chars: text.length };
        logAction({ platform: "twitter", tool: "post_to_twitter", text: text.substring(0, 100), result: "dry_run" });
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      if (!TWITTER_API_KEY || !TWITTER_ACCESS_TOKEN) {
        throw new Error("Twitter credentials not configured. Set TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET.");
      }

      const tweet = await twitterPostTweet(text, reply_to_tweet_id || null);

      const result = {
        success: true,
        platform: "twitter",
        tweet_id: tweet.id,
        text: tweet.text,
        url: `https://twitter.com/i/web/status/${tweet.id}`,
      };

      logAction({ platform: "twitter", tool: "post_to_twitter", tweet_id: tweet.id, result: "success" });

      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    } catch (error) {
      logAction({ platform: "twitter", tool: "post_to_twitter", result: "error", error: error.message });
      return {
        content: [{ type: "text", text: `Error posting to Twitter: ${error.message}` }],
        isError: true,
      };
    }
  }
);

// ── Tool: post_to_facebook ────────────────────────────────────────────────────

server.tool(
  "post_to_facebook",
  "Post a message to a Facebook Page via the Graph API.",
  {
    message: z.string().describe("Post message/caption"),
    link: z.string().url().optional().describe("URL to attach to the post"),
    published: z
      .boolean()
      .optional()
      .default(true)
      .describe("Publish immediately (true) or save as draft (false)"),
  },
  async ({ message, link, published }) => {
    try {
      if (DRY_RUN) {
        const result = { dry_run: true, message: `DRY_RUN: Would post to Facebook Page ${FB_PAGE_ID}`, preview: message.substring(0, 100) };
        logAction({ platform: "facebook", tool: "post_to_facebook", result: "dry_run" });
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      if (!FB_PAGE_ID || !FB_ACCESS_TOKEN) {
        throw new Error("Facebook credentials not configured. Set FB_PAGE_ID and FB_ACCESS_TOKEN.");
      }

      const params = { message, published };
      if (link) params.link = link;

      const data = await fbApiPost(`/${FB_PAGE_ID}/feed`, params);

      const result = {
        success: true,
        platform: "facebook",
        post_id: data.id,
        page_id: FB_PAGE_ID,
        message_preview: message.substring(0, 100),
      };

      logAction({ platform: "facebook", tool: "post_to_facebook", post_id: data.id, result: "success" });

      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    } catch (error) {
      logAction({ platform: "facebook", tool: "post_to_facebook", result: "error", error: error.message });
      return {
        content: [{ type: "text", text: `Error posting to Facebook: ${error.message}` }],
        isError: true,
      };
    }
  }
);

// ── Tool: post_to_instagram ───────────────────────────────────────────────────

server.tool(
  "post_to_instagram",
  "Post an image with caption to Instagram Business Account via the Graph API. Requires a public image URL.",
  {
    caption: z.string().describe("Post caption"),
    image_url: z
      .string()
      .url()
      .describe("Publicly accessible image URL (JPEG or PNG)"),
  },
  async ({ caption, image_url }) => {
    try {
      if (DRY_RUN) {
        const result = { dry_run: true, message: `DRY_RUN: Would post to Instagram account ${IG_ACCOUNT_ID}`, caption: caption.substring(0, 100) };
        logAction({ platform: "instagram", tool: "post_to_instagram", result: "dry_run" });
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      if (!IG_ACCOUNT_ID || !FB_ACCESS_TOKEN) {
        throw new Error("Instagram credentials not configured. Set IG_ACCOUNT_ID and FB_ACCESS_TOKEN.");
      }

      // Step 1: Create media container
      const containerData = await fbApiPost(`/${IG_ACCOUNT_ID}/media`, {
        image_url,
        caption,
      });

      if (!containerData.id) {
        throw new Error("Failed to create Instagram media container.");
      }

      const containerId = containerData.id;

      // Step 2: Poll until container is FINISHED
      let containerReady = false;
      let attempts = 0;
      while (!containerReady && attempts < 10) {
        await new Promise((r) => setTimeout(r, 2000));
        const statusData = await fbApiGet(`/${containerId}`, { fields: "status_code" });
        if (statusData.status_code === "FINISHED") {
          containerReady = true;
        } else if (statusData.status_code === "ERROR") {
          throw new Error("Instagram media container failed with ERROR status.");
        }
        attempts++;
      }

      if (!containerReady) {
        throw new Error("Instagram media container timed out — try again later.");
      }

      // Step 3: Publish the container
      const publishData = await fbApiPost(`/${IG_ACCOUNT_ID}/media_publish`, {
        creation_id: containerId,
      });

      const result = {
        success: true,
        platform: "instagram",
        media_id: publishData.id,
        account_id: IG_ACCOUNT_ID,
        caption_preview: caption.substring(0, 100),
        image_url,
      };

      logAction({ platform: "instagram", tool: "post_to_instagram", media_id: publishData.id, result: "success" });

      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    } catch (error) {
      logAction({ platform: "instagram", tool: "post_to_instagram", result: "error", error: error.message });
      return {
        content: [{ type: "text", text: `Error posting to Instagram: ${error.message}` }],
        isError: true,
      };
    }
  }
);

// ── Tool: get_social_summary ──────────────────────────────────────────────────

server.tool(
  "get_social_summary",
  "Get summary of recent social media activity from the audit log and optionally live platform stats.",
  {
    days: z.number().optional().default(7).describe("Number of days to look back"),
    include_live_stats: z
      .boolean()
      .optional()
      .default(false)
      .describe("Fetch live follower counts from platforms (requires valid credentials)"),
  },
  async ({ days, include_live_stats }) => {
    try {
      const since = new Date(Date.now() - days * 24 * 60 * 60 * 1000);

      // Read local action log
      let log = [];
      if (fs.existsSync(LOG_FILE)) {
        try {
          const raw = JSON.parse(fs.readFileSync(LOG_FILE, "utf-8"));
          log = raw.filter((e) => new Date(e.timestamp) >= since);
        } catch {
          log = [];
        }
      }

      const platformStats = { twitter: 0, facebook: 0, instagram: 0, errors: 0 };
      for (const entry of log) {
        if (entry.result === "error") {
          platformStats.errors++;
        } else if (entry.platform === "twitter") {
          platformStats.twitter++;
        } else if (entry.platform === "facebook") {
          platformStats.facebook++;
        } else if (entry.platform === "instagram") {
          platformStats.instagram++;
        }
      }

      const result = {
        period_days: days,
        since: since.toISOString(),
        post_counts: platformStats,
        total_posts: platformStats.twitter + platformStats.facebook + platformStats.instagram,
        recent_actions: log.slice(-10).map((e) => ({
          timestamp: e.timestamp,
          platform: e.platform,
          tool: e.tool,
          result: e.result,
          id: e.tweet_id || e.post_id || e.media_id || null,
        })),
      };

      // Optionally fetch live stats
      if (include_live_stats && !DRY_RUN) {
        const liveStats = {};

        // Twitter: get authenticated user info
        if (TWITTER_BEARER_TOKEN) {
          try {
            const twitterResp = await fetch("https://api.twitter.com/2/users/me?user.fields=public_metrics", {
              headers: { Authorization: `Bearer ${TWITTER_BEARER_TOKEN}` },
            });
            const twitterData = await twitterResp.json();
            if (twitterData.data) {
              liveStats.twitter = {
                username: twitterData.data.username,
                followers: twitterData.data.public_metrics?.followers_count,
                tweets: twitterData.data.public_metrics?.tweet_count,
              };
            }
          } catch (e) {
            liveStats.twitter = { error: e.message };
          }
        }

        // Facebook: get page fan count
        if (FB_PAGE_ID && FB_ACCESS_TOKEN) {
          try {
            const fbData = await fbApiGet(`/${FB_PAGE_ID}`, { fields: "name,fan_count,followers_count" });
            liveStats.facebook = {
              page_name: fbData.name,
              fans: fbData.fan_count,
              followers: fbData.followers_count,
            };
          } catch (e) {
            liveStats.facebook = { error: e.message };
          }
        }

        // Instagram: get account info
        if (IG_ACCOUNT_ID && FB_ACCESS_TOKEN) {
          try {
            const igData = await fbApiGet(`/${IG_ACCOUNT_ID}`, { fields: "username,followers_count,media_count" });
            liveStats.instagram = {
              username: igData.username,
              followers: igData.followers_count,
              media_count: igData.media_count,
            };
          } catch (e) {
            liveStats.instagram = { error: e.message };
          }
        }

        result.live_platform_stats = liveStats;
      }

      logAction({ tool: "get_social_summary", result: "success", days });

      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    } catch (error) {
      logAction({ tool: "get_social_summary", result: "error", error: error.message });
      return {
        content: [{ type: "text", text: `Error getting social summary: ${error.message}` }],
        isError: true,
      };
    }
  }
);

// ── Start Server ──────────────────────────────────────────────────────────────

async function main() {
  console.error("Starting Social MCP Server...");
  console.error(`Twitter configured: ${Boolean(TWITTER_API_KEY)}`);
  console.error(`Facebook configured: ${Boolean(FB_PAGE_ID && FB_ACCESS_TOKEN)}`);
  console.error(`Instagram configured: ${Boolean(IG_ACCOUNT_ID)}`);
  console.error(`Dry Run: ${DRY_RUN}`);

  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error("Social MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error starting Social MCP Server:", error);
  process.exit(1);
});
