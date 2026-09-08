-- =====================================================================
-- SuperMarket Ops Agent — Supabase Schema
-- Source of truth: PostgreSQL
-- Run this in Supabase SQL Editor (or apply via migrations).
-- =====================================================================

-- ---------- Extensions ----------
create extension if not exists "pgcrypto";

-- =====================================================================
-- CATEGORIES
-- =====================================================================
create table if not exists categories (
    id          bigint generated always as identity primary key,
    name        text not null unique,
    created_at  timestamptz not null default now()
);

-- =====================================================================
-- PRODUCTS
-- =====================================================================
create table if not exists products (
    id             bigint generated always as identity primary key,
    sku            text not null unique,
    name           text not null,
    category_id    bigint references categories(id) on delete set null,
    unit           text not null default 'piece',       -- piece, kg, packet, litre, dozen, box
    is_loose       boolean not null default false,
    cost_price     numeric(12,2) not null default 0,
    selling_price  numeric(12,2) not null default 0,
    mrp            numeric(12,2),
    quantity       numeric(12,3) not null default 0,
    reorder_level  numeric(12,3) not null default 0,
    hsn_code       text,
    gst_rate       numeric(5,2) not null default 0,     -- 0, 5, 12, 18, 28
    created_at     timestamptz not null default now(),
    updated_at     timestamptz not null default now()
);

create index if not exists idx_products_name  on products (name);
create index if not exists idx_products_cat   on products (category_id);
create index if not exists idx_products_sku   on products (sku);

-- =====================================================================
-- STOCK MOVEMENTS  (audit trail)
-- =====================================================================
create table if not exists stock_movements (
    id                bigint generated always as identity primary key,
    product_id        bigint not null references products(id) on delete cascade,
    movement_type     text not null,   -- STOCK_IN, SALE, ADJUSTMENT, RETURN
    quantity          numeric(12,3) not null,
    previous_quantity numeric(12,3) not null,
    new_quantity      numeric(12,3) not null,
    unit_cost         numeric(12,2),
    reference_type    text,            -- bill, stock_receipt, adjustment
    reference_id      bigint,
    created_at        timestamptz not null default now()
);

create index if not exists idx_stock_movements_product on stock_movements (product_id);
create index if not exists idx_stock_movements_ref     on stock_movements (reference_type, reference_id);

-- =====================================================================
-- CUSTOMERS  (khata)
-- =====================================================================
create table if not exists customers (
    id         bigint generated always as identity primary key,
    name       text not null,
    phone      text,
    created_at timestamptz not null default now()
);

create index if not exists idx_customers_name on customers (name);

-- =====================================================================
-- BILLS + BILL SESSIONS (multi-turn draft -> finalize)
-- =====================================================================
create table if not exists bill_sessions (
    id           bigint generated always as identity primary key,
    telegram_id  bigint not null,
    status       text not null default 'open',   -- open, finalized, cancelled
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now()
);

create unique index if not exists idx_bill_session_open
    on bill_sessions (telegram_id)
    where status = 'open';

-- Bill number sequence (DB-assigned, concurrency-safe)
create sequence if not exists bills_number_seq;

create table if not exists bills (
    id                bigint generated always as identity primary key,
    bill_number       text not null unique
                      default ('INV-' || to_char(now(), 'YYYYMMDD') || '-' || lpad(nextval('bills_number_seq')::text, 4, '0')),
    session_id        bigint references bill_sessions(id) on delete set null,
    customer_id       bigint references customers(id) on delete set null,
    status            text not null default 'draft',   -- draft, finalized, void
    subtotal          numeric(12,2) not null default 0,
    discount          numeric(12,2) not null default 0,
    taxable_total     numeric(12,2) not null default 0,
    gst_amount        numeric(12,2) not null default 0,
    total             numeric(12,2) not null default 0,
    payment_method    text,                            -- cash, upi, card, credit
    amount_paid       numeric(12,2) not null default 0,
    balance_due       numeric(12,2) not null default 0,
    finalized_at      timestamptz,
    created_at        timestamptz not null default now()
);

create index if not exists idx_bills_status     on bills (status);
create index if not exists idx_bills_created    on bills (created_at);
create index if not exists idx_bills_customer   on bills (customer_id);

create table if not exists bill_items (
    id            bigint generated always as identity primary key,
    bill_id       bigint not null references bills(id) on delete cascade,
    product_id    bigint not null references products(id),
    product_name  text not null,
    unit          text not null default 'piece',
    quantity      numeric(12,3) not null,
    price         numeric(12,2) not null,          -- unit selling price
    gst_rate      numeric(5,2) not null default 0,
    gst_amount    numeric(12,2) not null default 0,
    line_total    numeric(12,2) not null
);

create index if not exists idx_bill_items_bill on bill_items (bill_id);

-- =====================================================================
-- PAYMENTS
-- =====================================================================
create table if not exists payments (
    id              bigint generated always as identity primary key,
    bill_id         bigint references bills(id) on delete set null,
    customer_id     bigint references customers(id) on delete set null,
    amount          numeric(12,2) not null,
    method          text not null,        -- cash, upi, card, credit
    payment_type    text not null default 'sale',  -- sale, khata_settlement
    created_at      timestamptz not null default now()
);

create index if not exists idx_payments_bill     on payments (bill_id);
create index if not exists idx_payments_customer on payments (customer_id);

-- =====================================================================
-- KHATA TRANSACTIONS  (credit ledger)
-- =====================================================================
create table if not exists khata_transactions (
    id              bigint generated always as identity primary key,
    customer_id     bigint not null references customers(id) on delete cascade,
    transaction_type text not null,       -- credit (sale on credit), payment
    amount          numeric(12,2) not null,
    bill_id         bigint references bills(id) on delete set null,
    note            text,
    created_at      timestamptz not null default now()
);

create index if not exists idx_khata_customer on khata_transactions (customer_id);

-- =====================================================================
-- PREFERENCES  (persistent memory)
-- =====================================================================
create table if not exists preferences (
    telegram_id  bigint not null,
    key          text not null,
    value        text not null,
    updated_at   timestamptz not null default now(),
    primary key (telegram_id, key)
);

-- =====================================================================
-- IDEMPOTENCY KEYS  (guard against duplicate operations)
-- =====================================================================
create table if not exists idempotency_keys (
    id           bigint generated always as identity primary key,
    telegram_id  bigint not null,
    idem_key     text not null,
    operation    text not null,
    payload      jsonb,
    result       jsonb,
    created_at   timestamptz not null default now(),
    unique (telegram_id, idem_key)
);

-- =====================================================================
-- updated_at trigger helper
-- =====================================================================
create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end $$;

drop trigger if exists trg_products_updated on products;
create trigger trg_products_updated
    before update on products
    for each row execute function set_updated_at();

drop trigger if exists trg_bills_updated on bills;
create trigger trg_bills_updated
    before update on bills
    for each row execute function set_updated_at();

drop trigger if exists trg_bill_sessions_updated on bill_sessions;
create trigger trg_bill_sessions_updated
    before update on bill_sessions
    for each row execute function set_updated_at();
