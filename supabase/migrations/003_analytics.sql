-- =====================================================================
-- SuperMarket Ops Agent — Analytics RPC Functions
-- Read-model helpers. These compute the numbers; the AI only interprets.
-- Run after 002_rpc.sql
-- =====================================================================

-- Daily sales totals (last N days, finalized bills).
create or replace function daily_sales(p_days int default 7)
returns table (day date, total numeric, gst numeric, bill_count bigint)
language sql
as $$
  select
      created_at::date as day,
      sum(total) as total,
      sum(gst_amount) as gst,
      count(*) as bill_count
  from bills
  where status = 'finalized'
    and created_at >= now() - (p_days || ' days')::interval
  group by created_at::date
  order by day asc;
$$;

-- Sales summary for a window.
create or replace function sales_summary(p_days int default 7)
returns table (total_sales numeric, gst_collected numeric, bill_count bigint)
language sql
as $$
  select
      coalesce(sum(total), 0) as total_sales,
      coalesce(sum(gst_amount), 0) as gst_collected,
      count(*) as bill_count
  from bills
  where status = 'finalized'
    and created_at >= now() - (p_days || ' days')::interval;
$$;

-- Top products by revenue in a window.
create or replace function top_products(p_days int default 7, p_limit int default 10)
returns table (product_name text, units_sold numeric, revenue numeric)
language sql
as $$
  select
      bi.product_name,
      sum(bi.quantity) as units_sold,
      sum(bi.line_total) as revenue
  from bill_items bi
  join bills b on b.id = bi.bill_id
  where b.status = 'finalized'
    and b.created_at >= now() - (p_days || ' days')::interval
  group by bi.product_name
  order by revenue desc
  limit p_limit;
$$;

-- Payment method breakdown.
create or replace function payment_breakdown(p_days int default 7)
returns table (method text, total numeric, count bigint)
language sql
as $$
  select
      coalesce(b.payment_method, 'unknown'),
      sum(b.total),
      count(*)
  from bills b
  where b.status = 'finalized'
    and b.created_at >= now() - (p_days || ' days')::interval
  group by b.payment_method
  order by 2 desc;
$$;

-- Low stock items.
create or replace function low_stock(p_limit int default 20)
returns table (id bigint, name text, quantity numeric, reorder_level numeric)
language sql
as $$
  select p.id, p.name, p.quantity, p.reorder_level
  from products p
  where p.quantity <= p.reorder_level
  order by (p.quantity / nullif(p.reorder_level, 0)) asc
  limit p_limit;
$$;

-- Stock health snapshot.
create or replace function stock_health()
returns table (total_skus bigint, low_stock_skus bigint, out_of_stock_skus bigint)
language sql
as $$
  select
      count(*) as total_skus,
      count(*) filter (where quantity <= reorder_level) as low_stock_skus,
      count(*) filter (where quantity <= 0) as out_of_stock_skus
  from products;
$$;

-- Every product sold in a window (units + revenue). Used for "Today's Sales".
create or replace function sold_items(p_days int default 1)
returns table (product_name text, units_sold numeric, revenue numeric)
language sql
as $$
  select
      bi.product_name,
      sum(bi.quantity) as units_sold,
      sum(bi.line_total) as revenue
  from bill_items bi
  join bills b on b.id = bi.bill_id
  where b.status = 'finalized'
    and b.finalized_at >= now() - (p_days || ' days')::interval
  group by bi.product_name
  order by revenue desc;
$$;

-- Money actually received in a window (bill payments + khata settlements).
create or replace function money_received(p_days int default 1)
returns table (source text, method text, amount numeric)
language sql
as $$
  select
      'sale'::text as source,
      method,
      amount
  from payments
  where payment_type = 'sale'
    and created_at >= now() - (p_days || ' days')::interval
  union all
  select
      'khata_settlement'::text as source,
      method,
      amount
  from payments
  where payment_type = 'khata_settlement'
    and created_at >= now() - (p_days || ' days')::interval;
$$;