-- =====================================================================
-- DEMO DATA — 2 days of sales (bills + items + payments + stock levels)
-- Run this in the Supabase SQL Editor.
-- It is idempotent: re-running it cleans up the previous DEMO rows first.
-- After running, restart the bot and press the buttons to see this data.
-- =====================================================================

-- ------------------ 0. CLEANUP previous demo (safe, DEMO-scoped) -------
delete from payments
 where bill_id in (select id from bills where bill_number like 'DEMO-%');

delete from bill_items
 where bill_id in (select id from bills where bill_number like 'DEMO-%');

delete from stock_movements
 where reference_type = 'demo';

delete from bills
 where bill_number like 'DEMO-%';

delete from bill_sessions bs
 where not exists (select 1 from bills b where b.session_id = bs.id);

-- ------------------ 1. BILL SESSIONS + BILLS --------------------------
-- telegram_id 111111111 is a placeholder for the demo owner.
-- (The /New Bill button creates its own open session per real user.)
with
s1 as (
  insert into bill_sessions (telegram_id, status, created_at)
  values (111111111, 'finalized', now() - interval '2 days' + interval '1 hour')
  returning id
),
s2 as (
  insert into bill_sessions (telegram_id, status, created_at)
  values (111111111, 'finalized', now() - interval '2 days' + interval '9 hours')
  returning id
),
s3 as (
  insert into bill_sessions (telegram_id, status, created_at)
  values (111111111, 'finalized', now() - interval '1 day' + interval '1 hour')
  returning id
),
s4 as (
  insert into bill_sessions (telegram_id, status, created_at)
  values (111111111, 'finalized', now() - interval '1 day' + interval '9 hours')
  returning id
),
b1 as (
  insert into bills (bill_number, session_id, status, subtotal, discount,
                     taxable_total, gst_amount, total, payment_method,
                     amount_paid, balance_due, finalized_at, created_at)
  select 'DEMO-DAY1-0001', id, 'finalized', 680.00, 0, 680.00, 34.00, 714.00,
         'cash', 714.00, 0,
         now() - interval '2 days' + interval '1 hour',
         now() - interval '2 days' + interval '1 hour'
    from s1
  returning id
),
b2 as (
  insert into bills (bill_number, session_id, status, subtotal, discount,
                     taxable_total, gst_amount, total, payment_method,
                     amount_paid, balance_due, finalized_at, created_at)
  select 'DEMO-DAY1-0002', id, 'finalized', 1025.00, 0, 1025.00, 36.25, 1061.25,
         'upi', 1061.25, 0,
         now() - interval '2 days' + interval '9 hours',
         now() - interval '2 days' + interval '9 hours'
    from s2
  returning id
),
b3 as (
  insert into bills (bill_number, session_id, status, subtotal, discount,
                     taxable_total, gst_amount, total, payment_method,
                     amount_paid, balance_due, finalized_at, created_at)
  select 'DEMO-DAY2-0001', id, 'finalized', 592.00, 0, 592.00, 34.16, 626.16,
         'cash', 626.16, 0,
         now() - interval '1 day' + interval '1 hour',
         now() - interval '1 day' + interval '1 hour'
    from s3
  returning id
),
b4 as (
  insert into bills (bill_number, session_id, status, subtotal, discount,
                     taxable_total, gst_amount, total, payment_method,
                     amount_paid, balance_due, finalized_at, created_at)
  select 'DEMO-DAY2-0002', id, 'finalized', 1213.00, 0, 1213.00, 150.35, 1363.35,
         'card', 1363.35, 0,
         now() - interval '1 day' + interval '9 hours',
         now() - interval '1 day' + interval '9 hours'
    from s4
  returning id
)
-- ------------------ 2. BILL ITEMS --------------------------------------
insert into bill_items
    (bill_id, product_id, product_name, unit, quantity, price, gst_rate,
     gst_amount, line_total)
select b.id, p.id, p.name, p.unit, t.qty, t.price, t.gst,
       round((t.qty * t.price * t.gst / 100.0)::numeric, 2),
       round((t.qty * t.price)::numeric, 2)
  from (values
    -- Bill DEMO-DAY1-0001  (Aashirvaad Atta x2 @265/5%, Tata Salt x5 @30/5%)
    ('DEMO-DAY1-0001', 'ATT001', 2, 265, 5),
    ('DEMO-DAY1-0001', 'SAL001', 5, 30, 5),
    -- Bill DEMO-DAY1-0002  (Basmati x1 @475/5%, Toor Dal x2 @150/0%, Sunflower Oil x2 @125/5%)
    ('DEMO-DAY1-0002', 'RIC001', 1, 475, 5),
    ('DEMO-DAY1-0002', 'DAL001', 2, 150, 0),
    ('DEMO-DAY1-0002', 'OIL001', 2, 125, 5),
    -- Bill DEMO-DAY2-0001  (Maggi x12 @14/12%, Sugar x3 @48/0%, Parle-G x4 @70/5%)
    ('DEMO-DAY2-0001', 'MAG001', 12, 14, 12),
    ('DEMO-DAY2-0001', 'SUG001', 3, 48, 0),
    ('DEMO-DAY2-0001', 'BIS001', 4, 70, 5),
    -- Bill DEMO-DAY2-0002  (Milk x6 @58/5%, Bru Coffee x1 @175/5%, Dairy Milk x10 @45/18%, Bisleri x12 @20/18%)
    ('DEMO-DAY2-0002', 'MIL001', 6, 58, 5),
    ('DEMO-DAY2-0002', 'COF001', 1, 175, 5),
    ('DEMO-DAY2-0002', 'CHO001', 10, 45, 18),
    ('DEMO-DAY2-0002', 'WAT001', 12, 20, 18)
  ) as t(bill_number, sku, qty, price, gst)
  join bills b  on b.bill_number = t.bill_number
  join products p on p.sku = t.sku;

-- ------------------ 3. PAYMENTS (feeds money_received) -----------------
insert into payments (bill_id, amount, method, payment_type, created_at)
select b.id, b.total, b.payment_method, 'sale', b.finalized_at
  from bills b where b.bill_number in
  ('DEMO-DAY1-0001', 'DEMO-DAY1-0002', 'DEMO-DAY2-0001', 'DEMO-DAY2-0002');

-- ------------------ 4. STOCK LEVELS (remaining after sales) ------------
-- Sold qty is deducted from the seed. Re-running just SETS the same values,
-- so this stays consistent.
update products set quantity = t.qty
  from (values
    ('ATT001', 23), ('SAL001', 35), ('RIC001', 17), ('DAL001', 33),
    ('OIL001', 28), ('MAG001', 38), ('SUG001', 57), ('BIS001', 31),
    ('MIL001', 29), ('COF001', 14), ('CHO001', 15), ('WAT001', 28)
  ) as t(sku, qty)
  where products.sku = t.sku;

-- A few items pushed below reorder / out of stock to demo the Low Stock
-- and Stock Health buttons.
update products set quantity = 0, reorder_level = 3 where sku = 'GHE001';   -- AMUL GHEE 1L  → OUT OF STOCK
update products set quantity = 4, reorder_level = 5 where sku = 'SOAP002';  -- DOVE SOAP     → LOW
update products set quantity = 2, reorder_level = 5 where sku = 'SHAM001';  -- CLINIC PLUS   → LOW

-- ------------------ 5. STOCK MOVEMENTS (audit trail) -------------------
-- Reconstruct a SALE movement for every demo line item. previous_quantity
-- approximates the stock before this bill (current + qty sold on the bill).
insert into stock_movements
    (product_id, movement_type, quantity, previous_quantity, new_quantity,
     reference_type, reference_id, created_at)
select bi.product_id, 'SALE', bi.quantity,
       p.quantity + bi.quantity,          -- before this demo bill
       p.quantity,                        -- remaining now
       'bill', bi.bill_id, b.finalized_at
  from bill_items bi
  join bills b    on b.id = bi.bill_id
  join products p on p.id = bi.product_id
 where b.bill_number like 'DEMO-%';

-- =====================================================================
-- 6. VERIFY — expected results for the bot buttons
-- =====================================================================
-- select * from sales_summary(7);            -- total_sales 3764.76, gst 254.76, 4 bills
-- select * from daily_sales(7);              -- per-day totals for the last 2-3 days
-- select * from sold_items(1);               -- yesterday's sold items
-- select * from money_received(1);           -- yesterday's payments by method
-- select * from payment_breakdown(7);        -- cash 1340.16 / upi 1061.25 / card 1363.35
-- select * from low_stock(50);               -- Ghee(0/3), Dove(4/5), Clinic Plus(2/5) + any seeds already low
-- select * from stock_health();              -- total 30, low/out for Ghee/Dove/Clinic Plus
-- select bill_number, total, gst_amount, payment_method, finalized_at from bills
--   where bill_number like 'DEMO-%' order by finalized_at;  -- the 4 demo bills