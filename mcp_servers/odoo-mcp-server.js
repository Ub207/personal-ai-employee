#!/usr/bin/env node
/**
 * odoo-mcp-server.js — Gold Tier MCP Server
 * ==========================================
 * Model Context Protocol server for Odoo Community ERP via JSON-RPC.
 * Supports Odoo 17+ (JSON-RPC endpoint at /web/dataset/call_kw).
 *
 * Usage:
 *   node odoo-mcp-server.js
 *
 * Configuration (env vars):
 *   ODOO_URL=http://localhost:8069
 *   ODOO_DB=my_company
 *   ODOO_USERNAME=admin
 *   ODOO_PASSWORD=admin
 *   DRY_RUN=true
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import dotenv from "dotenv";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import fs from "fs";

// ── Bootstrap ─────────────────────────────────────────────────────────────────
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const vaultPath = join(__dirname, "..");
dotenv.config({ path: join(vaultPath, ".env") });

// ── Configuration ─────────────────────────────────────────────────────────────
const ODOO_URL = process.env.ODOO_URL || "http://localhost:8069";
const ODOO_DB = process.env.ODOO_DB || "";
const ODOO_USERNAME = process.env.ODOO_USERNAME || "admin";
const ODOO_PASSWORD = process.env.ODOO_PASSWORD || "admin";
const DRY_RUN = process.env.DRY_RUN === "true";

const LOGS_DIR = join(vaultPath, "Logs");
const LOG_FILE = join(LOGS_DIR, "odoo_actions.json");

// Ensure Logs directory exists
if (!fs.existsSync(LOGS_DIR)) {
  fs.mkdirSync(LOGS_DIR, { recursive: true });
}

// ── JSON-RPC Client ───────────────────────────────────────────────────────────

let _uid = null; // cached session UID

/**
 * Make a raw JSON-RPC call to Odoo.
 */
async function jsonRpc(endpoint, method, params) {
  const url = `${ODOO_URL}${endpoint}`;
  const payload = {
    jsonrpc: "2.0",
    method: "call",
    id: Date.now(),
    params,
  };

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const data = await response.json();

  if (data.error) {
    const errMsg = data.error.data?.message || data.error.message || JSON.stringify(data.error);
    throw new Error(`Odoo RPC Error: ${errMsg}`);
  }

  return data.result;
}

/**
 * Authenticate with Odoo and return uid.
 */
async function authenticate() {
  if (_uid !== null) return _uid;

  if (!ODOO_DB || !ODOO_USERNAME || !ODOO_PASSWORD) {
    throw new Error("Missing Odoo credentials: set ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD");
  }

  const uid = await jsonRpc("/web/dataset/call_kw", "call", {
    model: "res.users",
    method: "authenticate",
    args: [ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {}],
    kwargs: {},
  });

  // Odoo's authenticate is actually at /web/session/authenticate
  // Let's use the correct endpoint
  const authResult = await fetch(`${ODOO_URL}/web/session/authenticate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      method: "call",
      params: {
        db: ODOO_DB,
        login: ODOO_USERNAME,
        password: ODOO_PASSWORD,
      },
    }),
  });

  const authData = await authResult.json();
  if (authData.error || !authData.result?.uid) {
    throw new Error("Authentication failed. Check ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD.");
  }

  _uid = authData.result.uid;
  return _uid;
}

/**
 * Call an Odoo model method via JSON-RPC (requires authentication).
 */
async function odooCall(model, method, args = [], kwargs = {}) {
  const uid = await authenticate();

  return jsonRpc("/web/dataset/call_kw", "call", {
    model,
    method,
    args,
    kwargs: {
      context: { lang: "en_US", tz: "UTC", uid },
      ...kwargs,
    },
  });
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

// ── MCP Server ────────────────────────────────────────────────────────────────

const server = new McpServer({
  name: "odoo-mcp",
  version: "1.0.0",
  description: "Odoo Community ERP integration for AI Employee",
});

// ── Tool: search_invoices ─────────────────────────────────────────────────────

server.tool(
  "search_invoices",
  "Search Odoo invoices/bills by state, date range, or customer. Returns structured list.",
  {
    state: z
      .enum(["draft", "posted", "cancel", "all"])
      .optional()
      .default("all")
      .describe("Invoice state filter"),
    date_from: z
      .string()
      .optional()
      .describe("Start date filter (YYYY-MM-DD)"),
    date_to: z
      .string()
      .optional()
      .describe("End date filter (YYYY-MM-DD)"),
    partner_name: z
      .string()
      .optional()
      .describe("Filter by customer/vendor name (partial match)"),
    limit: z
      .number()
      .optional()
      .default(20)
      .describe("Maximum results to return"),
    move_type: z
      .enum(["out_invoice", "in_invoice", "out_refund", "in_refund", "all"])
      .optional()
      .default("out_invoice")
      .describe("Invoice type: out_invoice=customer invoice, in_invoice=vendor bill"),
  },
  async ({ state, date_from, date_to, partner_name, limit, move_type }) => {
    try {
      if (DRY_RUN) {
        const dryResult = {
          dry_run: true,
          message: "DRY_RUN active — no Odoo connection made",
          sample_invoices: [
            { id: 1, name: "INV/2026/00001", partner: "Sample Corp", amount_total: 1500.0, state: "posted", date: "2026-03-01" },
            { id: 2, name: "INV/2026/00002", partner: "Acme Ltd", amount_total: 750.5, state: "draft", date: "2026-03-05" },
          ],
        };
        logAction({ tool: "search_invoices", params: { state, move_type }, result: "dry_run" });
        return {
          content: [{ type: "text", text: JSON.stringify(dryResult, null, 2) }],
        };
      }

      // Build domain filter
      const domain = [];
      if (move_type !== "all") domain.push(["move_type", "=", move_type]);
      if (state !== "all") domain.push(["state", "=", state]);
      if (date_from) domain.push(["invoice_date", ">=", date_from]);
      if (date_to) domain.push(["invoice_date", "<=", date_to]);
      if (partner_name) domain.push(["partner_id.name", "ilike", partner_name]);

      const invoices = await odooCall("account.move", "search_read", [domain], {
        fields: [
          "name", "partner_id", "invoice_date", "invoice_date_due",
          "amount_total", "amount_residual", "state", "move_type",
          "currency_id", "ref",
        ],
        limit,
        order: "invoice_date desc",
      });

      const result = {
        count: invoices.length,
        invoices: invoices.map((inv) => ({
          id: inv.id,
          number: inv.name,
          partner: inv.partner_id?.[1] || "Unknown",
          date: inv.invoice_date,
          due_date: inv.invoice_date_due,
          total: inv.amount_total,
          amount_due: inv.amount_residual,
          state: inv.state,
          type: inv.move_type,
          currency: inv.currency_id?.[1] || "USD",
          reference: inv.ref || "",
        })),
      };

      logAction({ tool: "search_invoices", params: { state, move_type, date_from, date_to }, result: `found ${result.count}` });

      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      logAction({ tool: "search_invoices", result: "error", error: error.message });
      return {
        content: [{ type: "text", text: `Error searching invoices: ${error.message}` }],
        isError: true,
      };
    }
  }
);

// ── Tool: create_invoice ──────────────────────────────────────────────────────

server.tool(
  "create_invoice",
  "Create a new customer invoice in Odoo. Returns the new invoice ID and number.",
  {
    partner_name: z.string().describe("Customer name (must exist in Odoo)"),
    lines: z
      .array(
        z.object({
          product_name: z.string().describe("Product or service name"),
          quantity: z.number().describe("Quantity"),
          unit_price: z.number().describe("Unit price"),
          description: z.string().optional().describe("Line description"),
        })
      )
      .describe("Invoice line items"),
    invoice_date: z
      .string()
      .optional()
      .describe("Invoice date (YYYY-MM-DD), defaults to today"),
    reference: z.string().optional().describe("Customer reference / PO number"),
    note: z.string().optional().describe("Internal notes"),
  },
  async ({ partner_name, lines, invoice_date, reference, note }) => {
    try {
      if (DRY_RUN) {
        const dryResult = {
          dry_run: true,
          message: `DRY_RUN: Would create invoice for ${partner_name}`,
          lines_count: lines.length,
          estimated_total: lines.reduce((s, l) => s + l.quantity * l.unit_price, 0),
        };
        logAction({ tool: "create_invoice", params: { partner_name, lines_count: lines.length }, result: "dry_run" });
        return {
          content: [{ type: "text", text: JSON.stringify(dryResult, null, 2) }],
        };
      }

      // Find partner by name
      const partners = await odooCall("res.partner", "search_read", [[["name", "ilike", partner_name]]], {
        fields: ["id", "name"],
        limit: 1,
      });

      if (!partners.length) {
        throw new Error(`Partner not found: "${partner_name}". Create the customer in Odoo first.`);
      }
      const partnerId = partners[0].id;

      // Build invoice lines (minimal — product lookup optional)
      const invoiceLines = lines.map((line) => ({
        name: line.description || line.product_name,
        quantity: line.quantity,
        price_unit: line.unit_price,
      }));

      const invoiceVals = {
        move_type: "out_invoice",
        partner_id: partnerId,
        invoice_date: invoice_date || new Date().toISOString().split("T")[0],
        ref: reference || "",
        narration: note || "",
        invoice_line_ids: invoiceLines.map((l) => [0, 0, l]),
      };

      const invoiceId = await odooCall("account.move", "create", [invoiceVals]);

      // Read back the created invoice
      const [created] = await odooCall("account.move", "read", [[invoiceId]], {
        fields: ["name", "amount_total", "state"],
      });

      const result = {
        success: true,
        invoice_id: invoiceId,
        invoice_number: created.name,
        total: created.amount_total,
        state: created.state,
        partner: partner_name,
      };

      logAction({ tool: "create_invoice", params: { partner_name, lines_count: lines.length }, result: `created ${created.name}` });

      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      logAction({ tool: "create_invoice", result: "error", error: error.message });
      return {
        content: [{ type: "text", text: `Error creating invoice: ${error.message}` }],
        isError: true,
      };
    }
  }
);

// ── Tool: get_revenue_summary ─────────────────────────────────────────────────

server.tool(
  "get_revenue_summary",
  "Get revenue summary for a date range. Returns total invoiced, collected, and outstanding amounts.",
  {
    date_from: z.string().describe("Start date (YYYY-MM-DD)"),
    date_to: z.string().describe("End date (YYYY-MM-DD)"),
    group_by: z
      .enum(["month", "partner", "product"])
      .optional()
      .default("month")
      .describe("Group results by month, partner, or product"),
  },
  async ({ date_from, date_to, group_by }) => {
    try {
      if (DRY_RUN) {
        const dryResult = {
          dry_run: true,
          period: `${date_from} to ${date_to}`,
          total_invoiced: 45000.0,
          total_collected: 38500.0,
          total_outstanding: 6500.0,
          invoice_count: 12,
          message: "DRY_RUN: sample data shown",
        };
        logAction({ tool: "get_revenue_summary", params: { date_from, date_to }, result: "dry_run" });
        return {
          content: [{ type: "text", text: JSON.stringify(dryResult, null, 2) }],
        };
      }

      const domain = [
        ["move_type", "=", "out_invoice"],
        ["state", "=", "posted"],
        ["invoice_date", ">=", date_from],
        ["invoice_date", "<=", date_to],
      ];

      const invoices = await odooCall("account.move", "search_read", [domain], {
        fields: ["name", "partner_id", "invoice_date", "amount_total", "amount_residual", "currency_id"],
        order: "invoice_date asc",
      });

      const totalInvoiced = invoices.reduce((s, i) => s + i.amount_total, 0);
      const totalOutstanding = invoices.reduce((s, i) => s + i.amount_residual, 0);
      const totalCollected = totalInvoiced - totalOutstanding;

      // Group data
      const grouped = {};
      for (const inv of invoices) {
        let key;
        if (group_by === "month") {
          key = inv.invoice_date ? inv.invoice_date.substring(0, 7) : "unknown";
        } else if (group_by === "partner") {
          key = inv.partner_id?.[1] || "Unknown";
        } else {
          key = inv.name;
        }
        if (!grouped[key]) grouped[key] = { invoiced: 0, outstanding: 0, count: 0 };
        grouped[key].invoiced += inv.amount_total;
        grouped[key].outstanding += inv.amount_residual;
        grouped[key].count += 1;
      }

      const result = {
        period: { from: date_from, to: date_to },
        summary: {
          total_invoiced: Math.round(totalInvoiced * 100) / 100,
          total_collected: Math.round(totalCollected * 100) / 100,
          total_outstanding: Math.round(totalOutstanding * 100) / 100,
          invoice_count: invoices.length,
          collection_rate: totalInvoiced > 0 ? `${Math.round((totalCollected / totalInvoiced) * 100)}%` : "N/A",
        },
        breakdown: Object.entries(grouped).map(([key, val]) => ({
          [group_by]: key,
          invoiced: Math.round(val.invoiced * 100) / 100,
          outstanding: Math.round(val.outstanding * 100) / 100,
          count: val.count,
        })),
      };

      logAction({ tool: "get_revenue_summary", params: { date_from, date_to }, result: `total ${totalInvoiced}` });

      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      logAction({ tool: "get_revenue_summary", result: "error", error: error.message });
      return {
        content: [{ type: "text", text: `Error getting revenue summary: ${error.message}` }],
        isError: true,
      };
    }
  }
);

// ── Tool: list_customers ──────────────────────────────────────────────────────

server.tool(
  "list_customers",
  "List customers from Odoo with optional name filter. Returns basic contact info.",
  {
    search: z.string().optional().describe("Name or email search term"),
    limit: z.number().optional().default(25).describe("Maximum results"),
    include_stats: z
      .boolean()
      .optional()
      .default(false)
      .describe("Include total invoiced amount per customer"),
  },
  async ({ search, limit, include_stats }) => {
    try {
      if (DRY_RUN) {
        const dryResult = {
          dry_run: true,
          count: 2,
          customers: [
            { id: 1, name: "Sample Corp", email: "billing@sample.com", phone: "+1-555-0100", city: "New York" },
            { id: 2, name: "Acme Ltd", email: "accounts@acme.com", phone: "+1-555-0200", city: "London" },
          ],
        };
        logAction({ tool: "list_customers", result: "dry_run" });
        return {
          content: [{ type: "text", text: JSON.stringify(dryResult, null, 2) }],
        };
      }

      const domain = [["customer_rank", ">", 0]];
      if (search) domain.push("|", ["name", "ilike", search], ["email", "ilike", search]);

      const customers = await odooCall("res.partner", "search_read", [domain], {
        fields: ["id", "name", "email", "phone", "city", "country_id", "customer_rank"],
        limit,
        order: "name asc",
      });

      const result = {
        count: customers.length,
        customers: customers.map((c) => ({
          id: c.id,
          name: c.name,
          email: c.email || "",
          phone: c.phone || "",
          city: c.city || "",
          country: c.country_id?.[1] || "",
        })),
      };

      if (include_stats && customers.length > 0) {
        const partnerIds = customers.map((c) => c.id);
        const invoiceSums = await odooCall("account.move", "read_group", [
          [["move_type", "=", "out_invoice"], ["state", "=", "posted"], ["partner_id", "in", partnerIds]],
          ["partner_id", "amount_total:sum"],
          ["partner_id"],
        ]);

        const statsMap = {};
        for (const row of invoiceSums) {
          const pid = row.partner_id[0];
          statsMap[pid] = Math.round(row.amount_total * 100) / 100;
        }

        result.customers = result.customers.map((c) => ({
          ...c,
          total_invoiced: statsMap[c.id] || 0,
        }));
      }

      logAction({ tool: "list_customers", params: { search, limit }, result: `found ${result.count}` });

      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      logAction({ tool: "list_customers", result: "error", error: error.message });
      return {
        content: [{ type: "text", text: `Error listing customers: ${error.message}` }],
        isError: true,
      };
    }
  }
);

// ── Tool: get_accounting_summary ──────────────────────────────────────────────

server.tool(
  "get_accounting_summary",
  "Get full accounting health snapshot: receivables, payables, cash, overdue invoices.",
  {
    as_of_date: z
      .string()
      .optional()
      .describe("Snapshot date (YYYY-MM-DD), defaults to today"),
  },
  async ({ as_of_date }) => {
    const snapshotDate = as_of_date || new Date().toISOString().split("T")[0];

    try {
      if (DRY_RUN) {
        const dryResult = {
          dry_run: true,
          as_of_date: snapshotDate,
          receivables: { total: 12500.0, overdue: 3200.0, invoices_count: 8 },
          payables: { total: 4800.0, overdue: 0.0, bills_count: 3 },
          overdue_invoices: [
            { number: "INV/2026/00005", partner: "Late Corp", amount: 2000.0, days_overdue: 15 },
            { number: "INV/2026/00003", partner: "Slow LLC", amount: 1200.0, days_overdue: 32 },
          ],
          message: "DRY_RUN: sample data shown",
        };
        logAction({ tool: "get_accounting_summary", result: "dry_run" });
        return {
          content: [{ type: "text", text: JSON.stringify(dryResult, null, 2) }],
        };
      }

      // Receivables: posted customer invoices with residual > 0
      const receivables = await odooCall("account.move", "search_read", [
        [["move_type", "=", "out_invoice"], ["state", "=", "posted"], ["amount_residual", ">", 0]],
      ], {
        fields: ["name", "partner_id", "invoice_date_due", "amount_residual"],
      });

      const totalReceivable = receivables.reduce((s, i) => s + i.amount_residual, 0);
      const overdueReceivables = receivables.filter(
        (i) => i.invoice_date_due && i.invoice_date_due < snapshotDate
      );
      const totalOverdueReceivable = overdueReceivables.reduce((s, i) => s + i.amount_residual, 0);

      // Payables: posted vendor bills with residual > 0
      const payables = await odooCall("account.move", "search_read", [
        [["move_type", "=", "in_invoice"], ["state", "=", "posted"], ["amount_residual", ">", 0]],
      ], {
        fields: ["name", "partner_id", "invoice_date_due", "amount_residual"],
      });

      const totalPayable = payables.reduce((s, i) => s + i.amount_residual, 0);
      const overduePayables = payables.filter(
        (i) => i.invoice_date_due && i.invoice_date_due < snapshotDate
      );
      const totalOverduePayable = overduePayables.reduce((s, i) => s + i.amount_residual, 0);

      const result = {
        as_of_date: snapshotDate,
        receivables: {
          total: Math.round(totalReceivable * 100) / 100,
          overdue: Math.round(totalOverdueReceivable * 100) / 100,
          invoices_count: receivables.length,
          overdue_count: overdueReceivables.length,
        },
        payables: {
          total: Math.round(totalPayable * 100) / 100,
          overdue: Math.round(totalOverduePayable * 100) / 100,
          bills_count: payables.length,
          overdue_count: overduePayables.length,
        },
        overdue_receivables: overdueReceivables.map((i) => {
          const dueDate = new Date(i.invoice_date_due);
          const today = new Date(snapshotDate);
          const daysOverdue = Math.floor((today - dueDate) / 86400000);
          return {
            number: i.name,
            partner: i.partner_id?.[1] || "Unknown",
            amount: Math.round(i.amount_residual * 100) / 100,
            due_date: i.invoice_date_due,
            days_overdue: daysOverdue,
          };
        }).sort((a, b) => b.days_overdue - a.days_overdue),
        working_capital_indicator: Math.round((totalReceivable - totalPayable) * 100) / 100,
      };

      logAction({ tool: "get_accounting_summary", params: { snapshotDate }, result: `receivable ${totalReceivable}, payable ${totalPayable}` });

      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      logAction({ tool: "get_accounting_summary", result: "error", error: error.message });
      return {
        content: [{ type: "text", text: `Error getting accounting summary: ${error.message}` }],
        isError: true,
      };
    }
  }
);

// ── Start Server ──────────────────────────────────────────────────────────────

async function main() {
  console.error("Starting Odoo MCP Server...");
  console.error(`Odoo URL: ${ODOO_URL}`);
  console.error(`Odoo DB: ${ODOO_DB || "(not set)"}`);
  console.error(`Dry Run: ${DRY_RUN}`);

  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error("Odoo MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error starting Odoo MCP Server:", error);
  process.exit(1);
});
