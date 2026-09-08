# Supermarket Ops Agent

A Telegram-first, AI-agent supermarket operations assistant built for the
assignment. Telegram is the **entire product**; there is no separate web app.

## Architecture pillars

```
Telegram → Model Router (provider fallback) → Agent (tool calling)
          → Tools (validated inputs) → Services → Supabase (RPC transactions)
          → Artifacts (PDF invoice, PPTX report)
```

- **Supabase / PostgreSQL is the source of truth** — products, stock, bills,
  khata, payments, preferences, idempotency keys, audit trail.
- **AI layer is multi-model with fallbacks** — the application references
  *roles* (agent / fast / analysis / vision), never hard-coded model names.
- **AI never touches the database.** It calls tools; tools validate inputs and
  delegate to services; critical writes go through **PostgreSQL RPCs**
  (`finalize_bill_rpc`, `receive_stock_rpc`, `record_khata_payment_rpc`) which
  run inside single transactions with row locks.

## Setup

1. Create a Supabase project and run the SQL files in order from
   `supabase/migrations/` (`001_schema.sql`, `002_rpc.sql`, `003_analytics.sql`)
   plus `supabase/seed.sql` for the 30 products.
2. Copy `.env.example` to `.env` and fill in:
   - `TELEGRAM_BOT_TOKEN` — from BotFather
   - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — from Supabase dashboard
   - at least one of `OPENROUTER_API_KEY` / `GEMINI_API_KEY`
   - the model role variables (`PRIMARY_MODEL`, `FALLBACK_MODEL`, `FAST_MODEL`,
     `ANALYSIS_MODEL`) with whichever free models you have access to
3. Install dependencies and run:

```bash
pip install -r requirements.txt
python -m app.main
```

## Key flows

| Flow | Path |
| ---- | ---- |
| Check stock | `"how much sugar is left?"` → search_products → get_stock |
| Multi-turn bill | create_bill → add_bill_item ×n → calculate_bill → user confirms → finalize_bill (RPC: lock stock, decrement, GST, payment, audit) |
| Receive stock | `receive_stock` → RPC inside transaction |
| Khata | create_customer → record_credit_payment → get_credit_balance |
| Invoice PDF | `generate_invoice_pdf` → artifact sent via Telegram |
| Weekly report | analytics tools → analysis model writes insights → PPTX (charts via matplotlib) |
| Memory | `set_preference` / `get_preference`, e.g. default payment method |

## Safety properties

- **No overselling** — `finalize_bill_rpc` locks each product row and checks
  stock inside the transaction; any shortage aborts everything.
- **Idempotency** — billing finalization is guarded by an `idempotency_keys`
  table (unique per user + key). Duplicate finalize requests return the cached
  result instead of double-decrementing.
- **Concurrency** — every critical multi-step write is one PostgreSQL RPC /
  transaction, never a sequence of client-side updates.
- **Audit** — every stock change records a `stock_movements` row
  (previous → new).
=======
# Super-Market-Bot
A Telegram-first AI supermarket ops assistant. It manages bills (draft → GST → finalize), inventory with low-stock alerts, khata (credit) ledger, and daily/weekly analytics — all driven by natural language or quick buttons. Data lives in Supabase with atomic RPC transactions, and it generates invoice PDFs and PPTX reports with AI insights.

