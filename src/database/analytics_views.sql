-- ============================================================================
-- ANALYTICS SQL VIEWS
-- Enterprise-grade analytics views for VendorVault POS System
-- Version: 2.0.0 | Created: January 2026
-- ============================================================================

-- Drop existing views if they exist
DROP VIEW IF EXISTS views_sales_daily;
DROP VIEW IF EXISTS views_inventory_health;
DROP VIEW IF EXISTS views_profitability;
DROP VIEW IF EXISTS views_supplier_performance;

-- ============================================================================
-- 1. SALES DAILY VIEW
-- Aggregates daily sales metrics from bill table
-- ============================================================================
CREATE VIEW views_sales_daily AS
SELECT 
    date(b.date) as sale_date,
    COUNT(*) as bill_count,
    COALESCE(SUM(b.total), 0) as total_sales,
    COALESCE(SUM(b.subtotal), 0) as subtotal,
    COALESCE(SUM(b.tax_amount), 0) as total_tax,
    COALESCE(SUM(b.discount), 0) as total_discount,
    COALESCE(AVG(b.total), 0) as avg_order_value,
    COALESCE(SUM(b.cgst_amount), 0) as total_cgst,
    COALESCE(SUM(b.sgst_amount), 0) as total_sgst
FROM bill b
GROUP BY date(b.date)
ORDER BY sale_date DESC;

-- ============================================================================
-- 2. INVENTORY HEALTH VIEW
-- Stock status per variant with health indicators
-- ============================================================================
CREATE VIEW views_inventory_health AS
SELECT 
    pv.variant_id,
    p.product_id,
    p.product_name,
    pv.variant_name,
    pv.sku,
    pv.barcode,
    pt.type_name as product_type,
    pt.product_type_id,
    b.brand_name,
    b.brand_id,
    COALESCE(i.stock_quantity, 0) as stock_quantity,
    COALESCE(i.reorder_level, 10) as reorder_level,
    i.expiry_date,
    i.batch_number,
    COALESCE(pv.mrp, 0) as mrp,
    COALESCE(pv.cost_price, 0) as cost_price,
    COALESCE(i.stock_quantity, 0) * COALESCE(pv.cost_price, 0) as stock_value,
    COALESCE(i.stock_quantity, 0) * COALESCE(pv.mrp, 0) as stock_mrp_value,
    (COALESCE(pv.mrp, 0) - COALESCE(pv.cost_price, 0)) as margin_per_unit,
    CASE 
        WHEN i.expiry_date IS NOT NULL AND i.expiry_date < date('now') THEN 'EXPIRED'
        WHEN COALESCE(i.stock_quantity, 0) <= 0 THEN 'OUT_OF_STOCK'
        WHEN COALESCE(i.stock_quantity, 0) <= COALESCE(i.reorder_level, 10) THEN 'LOW'
        WHEN COALESCE(i.stock_quantity, 0) > COALESCE(i.reorder_level, 10) * 5 THEN 'OVERSTOCK'
        ELSE 'OK'
    END as stock_status,
    CASE 
        WHEN i.expiry_date IS NOT NULL AND i.expiry_date < date('now', '+30 days') 
             AND i.expiry_date >= date('now') THEN 1
        ELSE 0
    END as expiring_soon
FROM product_variants pv
JOIN products p ON pv.product_id = p.product_id
JOIN brands b ON p.brand_id = b.brand_id
JOIN product_types pt ON p.product_type_id = pt.product_type_id
LEFT JOIN inventory i ON pv.variant_id = i.variant_id
WHERE p.is_active = 1 AND pv.is_active = 1;

-- ============================================================================
-- 3. PROFITABILITY VIEW
-- Profit analysis per product variant
-- ============================================================================
CREATE VIEW views_profitability AS
SELECT 
    p.product_id,
    p.product_name,
    p.product_code,
    pv.variant_id,
    pv.variant_name,
    pv.sku,
    pt.type_name as product_type,
    b.brand_name,
    COALESCE(pv.mrp, 0) as mrp,
    COALESCE(pv.cost_price, 0) as cost_price,
    (COALESCE(pv.mrp, 0) - COALESCE(pv.cost_price, 0)) as gross_profit_per_unit,
    CASE 
        WHEN COALESCE(pv.mrp, 0) > 0 
        THEN ROUND(((pv.mrp - COALESCE(pv.cost_price, 0)) / pv.mrp) * 100, 2)
        ELSE 0 
    END as margin_percent,
    COALESCE(i.stock_quantity, 0) as current_stock,
    COALESCE(i.stock_quantity, 0) * (COALESCE(pv.mrp, 0) - COALESCE(pv.cost_price, 0)) as potential_profit
FROM products p
JOIN product_variants pv ON p.product_id = pv.product_id
JOIN brands b ON p.brand_id = b.brand_id
JOIN product_types pt ON p.product_type_id = pt.product_type_id
LEFT JOIN inventory i ON pv.variant_id = i.variant_id
WHERE p.is_active = 1 AND pv.is_active = 1;

-- ============================================================================
-- 4. SUPPLIER PERFORMANCE VIEW
-- Supplier metrics and product associations
-- ============================================================================
CREATE VIEW views_supplier_performance AS
SELECT 
    s.supplier_id,
    s.supplier_name,
    s.contact_person,
    s.phone,
    s.email,
    s.gst_number,
    COALESCE(s.rating, 0) as rating,
    s.is_active,
    COUNT(DISTINCT ps.product_id) as product_count,
    COALESCE(AVG(ps.unit_cost), 0) as avg_unit_cost,
    COALESCE(AVG(ps.lead_time_days), 0) as avg_lead_time,
    COALESCE(MIN(ps.lead_time_days), 0) as min_lead_time,
    COALESCE(MAX(ps.lead_time_days), 0) as max_lead_time,
    COALESCE(SUM(ps.minimum_order_qty), 0) as total_moq,
    COUNT(CASE WHEN ps.is_preferred = 1 THEN 1 END) as preferred_product_count
FROM suppliers s
LEFT JOIN product_suppliers ps ON s.supplier_id = ps.supplier_id
WHERE s.is_active = 1
GROUP BY s.supplier_id, s.supplier_name, s.contact_person, s.phone, 
         s.email, s.gst_number, s.rating, s.is_active;

-- ============================================================================
-- 5. SALES BY PRODUCT TYPE VIEW
-- Sales aggregated by product category
-- ============================================================================
CREATE VIEW views_sales_by_type AS
SELECT 
    pt.product_type_id,
    pt.type_name,
    pt.hsn_code,
    COUNT(DISTINCT p.product_id) as product_count,
    COUNT(DISTINCT pv.variant_id) as variant_count,
    COALESCE(SUM(i.stock_quantity), 0) as total_stock,
    COALESCE(SUM(i.stock_quantity * pv.cost_price), 0) as total_stock_value
FROM product_types pt
LEFT JOIN products p ON pt.product_type_id = p.product_type_id AND p.is_active = 1
LEFT JOIN product_variants pv ON p.product_id = pv.product_id AND pv.is_active = 1
LEFT JOIN inventory i ON pv.variant_id = i.variant_id
WHERE pt.is_active = 1
GROUP BY pt.product_type_id, pt.type_name, pt.hsn_code
ORDER BY pt.display_order, pt.type_name;

-- ============================================================================
-- 6. SALES BY BRAND VIEW
-- Sales aggregated by brand
-- ============================================================================
CREATE VIEW views_sales_by_brand AS
SELECT 
    b.brand_id,
    b.brand_name,
    b.description,
    COUNT(DISTINCT p.product_id) as product_count,
    COUNT(DISTINCT pv.variant_id) as variant_count,
    COALESCE(SUM(i.stock_quantity), 0) as total_stock,
    COALESCE(SUM(i.stock_quantity * pv.cost_price), 0) as total_stock_value
FROM brands b
LEFT JOIN products p ON b.brand_id = p.brand_id AND p.is_active = 1
LEFT JOIN product_variants pv ON p.product_id = pv.product_id AND pv.is_active = 1
LEFT JOIN inventory i ON pv.variant_id = i.variant_id
WHERE b.is_active = 1
GROUP BY b.brand_id, b.brand_name, b.description
ORDER BY b.brand_name;
