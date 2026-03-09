#!/usr/bin/env node
/**
 * email-mcp-server.js — Silver Tier MCP Server
 * ==============================================
 * Model Context Protocol server for sending emails via SMTP.
 * Integrates with Claude Code for email actions.
 *
 * Usage:
 *   node email-mcp-server.js
 *
 * Configuration:
 *   Set environment variables:
 *   - SMTP_HOST=smtp.gmail.com
 *   - SMTP_PORT=587
 *   - SMTP_USER=your.email@gmail.com
 *   - SMTP_PASS=your-app-password
 *   - DRY_RUN=true (optional, for testing)
 *
 * Install:
 *   npm install @modelcontextprotocol/sdk nodemailer
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import nodemailer from "nodemailer";
import dotenv from "dotenv";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import fs from "fs";

// Load environment variables from .env file in vault root
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const vaultPath = join(__dirname, "..");
dotenv.config({ path: join(vaultPath, ".env") });

// ── Configuration ────────────────────────────────────────────────────────────
const SMTP_HOST = process.env.SMTP_HOST || "smtp.gmail.com";
const SMTP_PORT = parseInt(process.env.SMTP_PORT || "587");
const SMTP_USER = process.env.SMTP_USER || "";
const SMTP_PASS = process.env.SMTP_PASS || "";
const DRY_RUN = process.env.DRY_RUN === "true";

// ── Email Transporter ────────────────────────────────────────────────────────
const transporter = nodemailer.createTransport({
  host: SMTP_HOST,
  port: SMTP_PORT,
  secure: SMTP_PORT === 465, // true for 465, false for other ports
  auth: {
    user: SMTP_USER,
    pass: SMTP_PASS,
  },
});

// Verify connection configuration
transporter.verify((error, success) => {
  if (error) {
    console.error("SMTP connection failed:", error.message);
    console.error("Email MCP will run in limited mode.");
  } else {
    console.log("SMTP connection successful. Ready to send emails.");
  }
});

// ── MCP Server Setup ─────────────────────────────────────────────────────────
const server = new McpServer({
  name: "email-mcp",
  version: "1.0.0",
  description: "Email sending capabilities for AI Employee",
});

// ── Tools ────────────────────────────────────────────────────────────────────

/**
 * Send an email
 */
server.tool(
  "send_email",
  "Send an email via SMTP. Requires approval for new contacts or bulk sends.",
  {
    to: z.string().email().describe("Recipient email address"),
    subject: z.string().describe("Email subject"),
    body: z.string().describe("Email body (plain text or HTML)"),
    from_name: z.string().optional().describe("Sender name (optional)"),
    cc: z.string().optional().describe("CC recipients (comma-separated)"),
    bcc: z.string().optional().describe("BCC recipients (comma-separated)"),
    attachment_path: z.string().optional().describe("Path to attachment file"),
    is_html: z.boolean().optional().default(false).describe("Whether body is HTML"),
  },
  async ({
    to,
    subject,
    body,
    from_name,
    cc,
    bcc,
    attachment_path,
    is_html,
  }) => {
    const timestamp = new Date().toISOString();

    // Check credentials
    if (!SMTP_USER || !SMTP_PASS) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Email not sent: SMTP credentials not configured. Set SMTP_USER and SMTP_PASS environment variables.`,
          },
        ],
        isError: true,
      };
    }

    // Dry run mode
    if (DRY_RUN) {
      return {
        content: [
          {
            type: "text",
            text: `📧 [DRY RUN] Email would be sent:\n- To: ${to}\n- Subject: ${subject}\n- From: ${from_name || SMTP_USER}\n- Body preview: ${body.substring(0, 200)}...`,
          },
        ],
      };
    }

    try {
      // Build email options
      const mailOptions = {
        from: from_name ? `${from_name} <${SMTP_USER}>` : SMTP_USER,
        to,
        subject,
        text: is_html ? undefined : body,
        html: is_html ? body : undefined,
        cc: cc ? cc.split(",").map((s) => s.trim()) : undefined,
        bcc: bcc ? bcc.split(",").map((s) => s.trim()) : undefined,
      };

      // Add attachment if provided
      if (attachment_path && fs.existsSync(attachment_path)) {
        mailOptions.attachments = [
          {
            filename: attachment_path.split(/[\\/]/).pop(),
            path: attachment_path,
          },
        ];
      }

      // Send email
      const info = await transporter.sendMail(mailOptions);

      // Log the action
      logEmailAction({
        timestamp,
        action_type: "email_send",
        to,
        subject,
        result: "success",
        message_id: info.messageId,
      });

      return {
        content: [
          {
            type: "text",
            text: `✅ Email sent successfully!\n- To: ${to}\n- Subject: ${subject}\n- Message ID: ${info.messageId}\n- Response: ${info.response}`,
          },
        ],
      };
    } catch (error) {
      const errorMsg = error.message || "Unknown error";

      // Log the failure
      logEmailAction({
        timestamp,
        action_type: "email_send",
        to,
        subject,
        result: "failed",
        error: errorMsg,
      });

      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to send email: ${errorMsg}`,
          },
        ],
        isError: true,
      };
    }
  }
);

/**
 * Draft an email (doesn't send, just prepares)
 */
server.tool(
  "draft_email",
  "Create a draft email file in /Pending_Approval for review before sending.",
  {
    to: z.string().email().describe("Recipient email address"),
    subject: z.string().describe("Email subject"),
    body: z.string().describe("Email body"),
    from_name: z.string().optional().describe("Sender name (optional)"),
    is_html: z.boolean().optional().default(false).describe("Whether body is HTML"),
  },
  async ({ to, subject, body, from_name, is_html }) => {
    const timestamp = new Date().toISOString();
    const timestampFile = new Date().toISOString().replace(/[:.]/g, "-");
    const safeSubject = subject.replace(/[^a-zA-Z0-9]/g, "_").substring(0, 50);

    const draftContent = `---
type: email_draft
to: ${to}
subject: ${subject}
from_name: ${from_name || "AI Employee"}
created: ${timestamp}
status: pending_approval
is_html: ${is_html}
---

# Email Draft — Requires Approval

**To:** ${to}
**Subject:** ${subject}
**From:** ${from_name || SMTP_USER}

---

${body}

---

## To Approve
Move this file to /Approved folder to send.

## To Reject
Move this file to /Rejected folder or add comments below.

## Notes
*(Human reviewer — add comments here)*
`;

    const draftsFolder = join(vaultPath, "Pending_Approval");
    if (!fs.existsSync(draftsFolder)) {
      fs.mkdirSync(draftsFolder, { recursive: true });
    }

    const draftFile = join(
      draftsFolder,
      `EMAIL_DRAFT_${timestampFile}_${safeSubject}.md`
    );

    try {
      fs.writeFileSync(draftFile, draftContent, "utf-8");

      return {
        content: [
          {
            type: "text",
            text: `📝 Email draft created: ${draftFile}\n\nMove this file to /Approved to send, or /Rejected to discard.`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to create draft: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }
);

/**
 * List recent emails from log
 */
server.tool(
  "list_sent_emails",
  "List recently sent emails from the audit log.",
  {
    limit: z.number().optional().default(10).describe("Number of emails to list"),
  },
  async ({ limit }) => {
    const logFile = join(vaultPath, "Logs", "email_actions.json");

    if (!fs.existsSync(logFile)) {
      return {
        content: [
          {
            type: "text",
            text: "📭 No email history found. No emails have been sent yet.",
          },
        ],
      };
    }

    try {
      const logData = JSON.parse(fs.readFileSync(logFile, "utf-8"));
      const recent = logData.slice(-limit).reverse();

      const formatted = recent
        .map(
          (entry) =>
            `[${new Date(entry.timestamp).toLocaleString()}] ${entry.action_type} to ${entry.to} — ${entry.result}`
        )
        .join("\n");

      return {
        content: [
          {
            type: "text",
            text: `📧 Recent Email Actions (last ${limit}):\n\n${formatted}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Error reading log: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// ── Helper Functions ─────────────────────────────────────────────────────────

/**
 * Log email actions for audit trail
 */
function logEmailAction(entry) {
  const logFile = join(vaultPath, "Logs", "email_actions.json");
  const logsFolder = join(vaultPath, "Logs");

  if (!fs.existsSync(logsFolder)) {
    fs.mkdirSync(logsFolder, { recursive: true });
  }

  let logData = [];
  if (fs.existsSync(logFile)) {
    try {
      logData = JSON.parse(fs.readFileSync(logFile, "utf-8"));
    } catch {
      logData = [];
    }
  }

  logData.push(entry);

  // Keep only last 1000 entries
  if (logData.length > 1000) {
    logData = logData.slice(-1000);
  }

  fs.writeFileSync(logFile, JSON.stringify(logData, null, 2), "utf-8");
}

// ── Start Server ─────────────────────────────────────────────────────────────

async function main() {
  console.error("Starting Email MCP Server...");
  console.error(`SMTP Host: ${SMTP_HOST}`);
  console.error(`Dry Run: ${DRY_RUN}`);

  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error("Email MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error starting Email MCP Server:", error);
  process.exit(1);
});
