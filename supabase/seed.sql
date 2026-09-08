-- =====================================================================
-- SuperMarket Ops Agent — Seed Data (30 products)
-- Run after 002_rpc.sql
-- =====================================================================

-- Categories
insert into categories (name) values
    ('Flour'),
    ('Staples'),
    ('Rice'),
    ('Pulses'),
    ('Cooking Oil'),
    ('Beverages'),
    ('Dairy'),
    ('Instant Food'),
    ('Biscuits'),
    ('Chocolates'),
    ('Snacks'),
    ('Personal Care'),
    ('Cleaning'),
    ('Fresh Produce')
on conflict (name) do nothing;

-- Products
-- (sku, name, category, unit, is_loose, cost, sell, mrp, qty, reorder, hsn, gst)
insert into products
    (sku, name, category_id, unit, is_loose, cost_price, selling_price, mrp,
     quantity, reorder_level, hsn_code, gst_rate)
select * from (values
    ('ATT001', 'Aashirvaad Atta 5kg', (select id from categories where name='Flour'), 'packet', false, 220, 265, 265, 25, 5, '00000000', 5),
    ('SAL001', 'Tata Salt 1kg', (select id from categories where name='Staples'), 'packet', false, 22, 30, 30, 40, 10, '00000000', 5),
    ('RIC001', 'India Gate Basmati Rice 5kg', (select id from categories where name='Rice'), 'packet', false, 390, 475, 475, 18, 5, '00000000', 5),
    ('RIC002', 'Loose Rice', (select id from categories where name='Rice'), 'kg', true, 42, 50, 50, 75, 20, '00000000', 0),
    ('DAL001', 'Toor Dal', (select id from categories where name='Pulses'), 'kg', true, 125, 150, 150, 35, 10, '00000000', 0),
    ('DAL002', 'Moong Dal', (select id from categories where name='Pulses'), 'kg', true, 105, 130, 130, 30, 8, '00000000', 0),
    ('SUG001', 'Loose Sugar', (select id from categories where name='Staples'), 'kg', true, 40, 48, 48, 60, 15, '00000000', 0),
    ('OIL001', 'Fortune Sunflower Oil 1L', (select id from categories where name='Cooking Oil'), 'litre', true, 105, 125, 125, 30, 8, '00000000', 5),
    ('OIL002', 'Fortune Groundnut Oil 1L', (select id from categories where name='Cooking Oil'), 'litre', true, 135, 160, 160, 20, 6, '00000000', 5),
    ('TEA001', 'Tata Tea 250g', (select id from categories where name='Beverages'), 'packet', false, 110, 135, 135, 22, 6, '00000000', 5),
    ('COF001', 'Bru Instant Coffee 100g', (select id from categories where name='Beverages'), 'packet', false, 145, 175, 175, 15, 5, '00000000', 5),
    ('MIL001', 'Amul Taaza Milk 1L', (select id from categories where name='Dairy'), 'litre', true, 50, 58, 58, 35, 10, '00000000', 5),
    ('BUT001', 'Amul Butter 100g', (select id from categories where name='Dairy'), 'packet', false, 52, 62, 62, 20, 6, '00000000', 12),
    ('GHE001', 'Amul Ghee 1L', (select id from categories where name='Dairy'), 'litre', true, 520, 610, 610, 10, 3, '00000000', 12),
    ('MAG001', 'Maggi 70g', (select id from categories where name='Instant Food'), 'packet', false, 11, 14, 14, 50, 15, '00000000', 12),
    ('BIS001', 'Parle-G 800g', (select id from categories where name='Biscuits'), 'packet', false, 55, 70, 70, 35, 10, '00000000', 5),
    ('BIS002', 'Britannia Good Day 200g', (select id from categories where name='Biscuits'), 'packet', false, 30, 40, 40, 28, 8, '00000000', 18),
    ('CHO001', 'Dairy Milk 40g', (select id from categories where name='Chocolates'), 'piece', false, 35, 45, 45, 25, 8, '00000000', 18),
    ('SNK001', 'Lays Classic Salted 50g', (select id from categories where name='Snacks'), 'packet', false, 17, 20, 20, 40, 12, '00000000', 12),
    ('NOO001', 'Yippee Noodles 70g', (select id from categories where name='Instant Food'), 'packet', false, 11, 15, 15, 35, 10, '00000000', 12),
    ('SOAP001', 'Lux Soap 100g', (select id from categories where name='Personal Care'), 'piece', false, 28, 38, 38, 25, 7, '00000000', 18),
    ('SOAP002', 'Dove Soap 100g', (select id from categories where name='Personal Care'), 'piece', false, 45, 55, 55, 18, 5, '00000000', 18),
    ('SHAM001', 'Clinic Plus Shampoo 175ml', (select id from categories where name='Personal Care'), 'ml', false, 75, 95, 95, 15, 5, '00000000', 18),
    ('DETER001', 'Surf Excel Matic 1kg', (select id from categories where name='Cleaning'), 'packet', false, 145, 180, 180, 20, 6, '00000000', 18),
    ('DISH001', 'Vim Dishwash Bar 200g', (select id from categories where name='Cleaning'), 'piece', false, 18, 25, 25, 30, 8, '00000000', 18),
    ('TOIL001', 'Colgate Toothpaste 200g', (select id from categories where name='Personal Care'), 'piece', false, 85, 110, 110, 22, 6, '00000000', 18),
    ('VEG001', 'Fresh Potato', (select id from categories where name='Fresh Produce'), 'kg', true, 28, 35, 35, 50, 15, '00000000', 0),
    ('VEG002', 'Fresh Onion', (select id from categories where name='Fresh Produce'), 'kg', true, 30, 40, 40, 45, 15, '00000000', 0),
    ('FRU001', 'Fresh Banana', (select id from categories where name='Fresh Produce'), 'dozen', true, 35, 50, 50, 20, 6, '00000000', 0),
    ('WAT001', 'Bisleri Water 1L', (select id from categories where name='Beverages'), 'litre', true, 15, 20, 20, 40, 10, '00000000', 18)
) as t(sku, name, category_id, unit, is_loose, cost_price, selling_price, mrp,
       quantity, reorder_level, hsn_code, gst_rate)
on conflict (sku) do update set
    name = EXCLUDED.name,
    category_id = EXCLUDED.category_id,
    unit = EXCLUDED.unit,
    is_loose = EXCLUDED.is_loose,
    cost_price = EXCLUDED.cost_price,
    selling_price = EXCLUDED.selling_price,
    mrp = EXCLUDED.mrp,
    quantity = EXCLUDED.quantity,
    reorder_level = EXCLUDED.reorder_level,
    gst_rate = EXCLUDED.gst_rate;
