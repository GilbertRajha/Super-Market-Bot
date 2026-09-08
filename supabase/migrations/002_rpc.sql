-- =====================================================================
-- SuperMarket Ops Agent — RPC Functions
-- Critical, concurrency-safe operations run inside single PostgreSQL
-- transactions. Keeps business rules close to the data.
-- Run after 001_schema.sql.
-- =====================================================================

-- =====================================================================
-- receive_stock_rpc
-- Add stock to a product inside a transaction and record a movement.
-- =====================================================================
create or replace function receive_stock_rpc(
    p_product_id bigint,
    p_qty numeric,
    p_unit_cost numeric,
    p_reference text default 'stock_receipt'
)
returns jsonb
language plpgsql
as $$
declare
    v_prev numeric;
    v_new  numeric;
begin
    -- row lock to prevent concurrent writes
    select quantity into v_prev
      from products
     where id = p_product_id
       for update;

    if not found then
        raise exception 'product not found: %', p_product_id;
    end if;

    v_new := v_prev + p_qty;

    update products
       set quantity = v_new,
           cost_price = coalesce(p_unit_cost, cost_price)
     where id = p_product_id;

    insert into stock_movements
        (product_id, movement_type, quantity, previous_quantity, new_quantity, unit_cost, reference_type, reference_id)
    values
        (p_product_id, 'STOCK_IN', p_qty, v_prev, v_new, p_unit_cost, p_reference, null);

    return jsonb_build_object(
        'product_id', p_product_id,
        'previous_quantity', v_prev,
        'new_quantity', v_new
    );
end $$;

-- =====================================================================
-- finalize_bill_rpc
-- The heart of the system. In ONE transaction:
--   * validates stock for every item
--   * validates amounts
--   * decrements stock
--   * records stock movements
--   * marks bill finalized
--   * records payment
--   * records khata credit if payment_method = 'credit'
-- Any failure rolls back everything.
--
-- p_items: jsonb array of {product_id, quantity}
-- p_paid: amount actually paid now
-- =====================================================================
create or replace function finalize_bill_rpc(
    p_bill_id bigint,
    p_items jsonb,
    p_paid numeric,
    p_payment_method text
)
returns jsonb
language plpgsql
as $$
declare
    v_bill             bills%rowtype;
    v_subtotal         numeric := 0;
    v_taxable          numeric := 0;
    v_gst              numeric := 0;
    v_total            numeric := 0;
    v_item             jsonb;
    v_product          products%rowtype;
    v_qty              numeric;
    v_line_total       numeric;
    v_balance_due      numeric;
    v_payment          numeric;
    v_price            numeric;
    v_gst_rate         numeric;
    v_discount         numeric;
    v_factor           numeric;
begin
    -- lock the bill
    select * into v_bill from bills where id = p_bill_id for update;
    if not found then
        raise exception 'bill not found: %', p_bill_id;
    end if;
    if v_bill.status = 'finalized' then
        raise exception 'bill already finalized';
    end if;

    -- Items must be non-empty
    if jsonb_array_length(p_items) = 0 then
        raise exception 'bill has no items';
    end if;

    v_discount := coalesce(v_bill.discount, 0);

    -- Delete any existing bill_items then re-insert with fresh validation
    delete from bill_items where bill_id = p_bill_id;

    -- Actually compute items based on products (server-side truth). A whole-bill
    -- discount is apportioned proportionally across lines BEFORE GST, so GST is
    -- always computed on the discounted value (GST-correct).
    for v_item in select * from jsonb_array_elements(p_items)
    loop
        v_qty := (v_item->>'quantity')::numeric;
        if v_qty <= 0 then
            raise exception 'quantity must be positive';
        end if;

        select * into v_product
          from products
         where id = (v_item->>'product_id')::bigint
           for update;

        if not found then
            raise exception 'product not found';
        end if;

        if v_product.quantity < v_qty then
            raise exception 'insufficient stock for %: have %, need %',
                v_product.name, v_product.quantity, v_qty;
        end if;

        v_price    := v_product.selling_price;
        v_gst_rate := v_product.gst_rate;
        v_line_total := round((v_price * v_qty)::numeric, 2);

        v_subtotal := v_subtotal + v_line_total;
        v_taxable  := v_taxable + v_line_total;

        insert into bill_items
            (bill_id, product_id, product_name, unit, quantity, price,
             gst_rate, gst_amount, line_total)
        values
            (p_bill_id, v_product.id, v_product.name, v_product.unit, v_qty,
             v_price, v_gst_rate, 0, v_line_total);

        -- decrement stock
        update products
           set quantity = quantity - v_qty
         where id = v_product.id;

        -- audit movement
        insert into stock_movements
            (product_id, movement_type, quantity, previous_quantity, new_quantity,
             unit_cost, reference_type, reference_id)
        values
            (v_product.id, 'SALE', -v_qty, v_product.quantity,
             v_product.quantity - v_qty, v_product.cost_price, 'bill', p_bill_id);
    end loop;

    -- Apportion discount across lines and compute GST on discounted values,
    -- then fill in each line's gst_amount accordingly.
    v_factor := 1.0;
    if v_discount > 0 and v_subtotal > 0 then
        v_factor := 1.0 - (v_discount / v_subtotal);
    end if;

    update bill_items
       set gst_amount = round((line_total * v_factor * gst_rate / 100.0)::numeric, 2)
     where bill_id = p_bill_id;

    select coalesce(sum(gst_amount), 0) into v_gst from bill_items where bill_id = p_bill_id;
    v_subtotal := round(v_subtotal * v_factor, 2);
    v_taxable  := v_subtotal;
    v_total    := round((v_subtotal + v_gst)::numeric, 2);

    v_payment := least(coalesce(p_paid, 0), v_total);
    v_balance_due := v_total - v_payment;

    if p_payment_method = 'credit' then
        -- full amount goes to khata as balance due
        v_payment := 0;
        v_balance_due := v_total;
    end if;

    update bills
       set status        = 'finalized',
           subtotal      = v_subtotal,
           taxable_total = v_taxable,
           gst_amount    = v_gst,
           total         = v_total,
           payment_method= p_payment_method,
           amount_paid   = v_payment,
           balance_due   = v_balance_due,
           finalized_at  = now()
     where id = p_bill_id;

    -- payments
    if v_payment > 0 then
        insert into payments (bill_id, customer_id, amount, method, payment_type)
        values (p_bill_id, v_bill.customer_id, v_payment, p_payment_method, 'sale');
    end if;

    -- khata ledger for credit sales
    if p_payment_method = 'credit' and v_bill.customer_id is not null then
        insert into khata_transactions (customer_id, transaction_type, amount, bill_id, note)
        values (v_bill.customer_id, 'credit', v_total, p_bill_id, 'sale on credit');
    end if;

    -- close the session
    update bill_sessions
       set status = 'finalized'
     where id = v_bill.session_id;

    return jsonb_build_object(
        'bill_id', p_bill_id,
        'bill_number', (select bill_number from bills where id = p_bill_id),
        'subtotal', v_subtotal,
        'gst_amount', v_gst,
        'total', v_total,
        'amount_paid', v_payment,
        'balance_due', v_balance_due,
        'status', 'finalized'
    );
end $$;

-- =====================================================================
-- record_khata_payment_rpc
-- Record a payment against a customer's credit balance.
-- =====================================================================
create or replace function record_khata_payment_rpc(
    p_customer_id bigint,
    p_amount numeric,
    p_method text default 'cash'
)
returns jsonb
language plpgsql
as $$
declare
    v_balance numeric;
begin
    if p_amount <= 0 then
        raise exception 'payment amount must be positive';
    end if;

    select coalesce(sum(case
        when transaction_type = 'credit' then amount
        when transaction_type = 'payment' then -amount
        else 0 end), 0) into v_balance
      from khata_transactions
     where customer_id = p_customer_id;

    if v_balance < p_amount then
        raise exception 'payment exceeds outstanding balance (balance: %)', v_balance;
    end if;

    insert into khata_transactions (customer_id, transaction_type, amount, note)
    values (p_customer_id, 'payment', p_amount, 'settlement ' || p_method);

    insert into payments (customer_id, amount, method, payment_type)
    values (p_customer_id, p_amount, p_method, 'khata_settlement');

    return jsonb_build_object(
        'customer_id', p_customer_id,
        'new_balance', v_balance - p_amount
    );
end $$;

-- =====================================================================
-- get_khata_balance_rpc
-- =====================================================================
create or replace function get_khata_balance_rpc(p_customer_id bigint)
returns jsonb
language plpgsql
as $$
declare
    v_balance numeric;
begin
    select coalesce(sum(case
        when transaction_type = 'credit' then amount
        when transaction_type = 'payment' then -amount
        else 0 end), 0) into v_balance
      from khata_transactions
     where customer_id = p_customer_id;

    return jsonb_build_object('customer_id', p_customer_id, 'balance', v_balance);
end $$;
