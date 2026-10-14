BEGIN;

TRUNCATE TABLE
    reviews,
    shipments,
    payments,
    order_items,
    orders,
    inventory,
    products,
    categories,
    addresses,
    customers
RESTART IDENTITY CASCADE;

INSERT INTO customers (customer_id, first_name, last_name, email, phone, created_at) VALUES
    (1, 'Amara', 'Okafor', 'amara.okafor@nexacart.example', '+2348015550101', '2026-09-02 09:15:00'),
    (2, 'Tunde', 'Adebayo', 'tunde.adebayo@nexacart.example', '+2348015550102', '2026-09-03 10:30:00'),
    (3, 'Zainab', 'Bello', 'zainab.bello@nexacart.example', '+2348015550103', '2026-09-04 13:45:00'),
    (4, 'Chinedu', 'Eze', 'chinedu.eze@nexacart.example', '+2348015550104', '2026-09-05 08:20:00'),
    (5, 'Mariam', 'Usman', 'mariam.usman@nexacart.example', '+2348015550105', '2026-09-06 15:10:00'),
    (6, 'Ifeoma', 'Nwosu', 'ifeoma.nwosu@nexacart.example', '+2348015550106', '2026-09-07 11:05:00');

INSERT INTO addresses (address_id, customer_id, street, city, state, country) VALUES
    (1, 1, '12 Admiralty Way', 'Lekki', 'Lagos', 'Nigeria'),
    (2, 1, '8 Allen Avenue', 'Ikeja', 'Lagos', 'Nigeria'),
    (3, 2, '45 Ring Road', 'Ibadan', 'Oyo', 'Nigeria'),
    (4, 3, '19 Tafawa Balewa Road', 'Kano', 'Kano', 'Nigeria'),
    (5, 3, '7 Wuse Market Road', 'Wuse', 'FCT', 'Nigeria'),
    (6, 4, '28 Okigwe Road', 'Owerri', 'Imo', 'Nigeria'),
    (7, 5, '5 Zoo Road', 'Kaduna', 'Kaduna', 'Nigeria'),
    (8, 6, '33 Aba Road', 'Port Harcourt', 'Rivers', 'Nigeria'),
    (9, 6, '14 Independence Layout', 'Enugu', 'Enugu', 'Nigeria');

INSERT INTO categories (category_id, name, description) VALUES
    (1, 'Electronics', 'Phones, computers, accessories and personal devices.'),
    (2, 'Fashion', 'Clothing, bags and everyday fashion accessories.'),
    (3, 'Home and Kitchen', 'Household appliances, cookware and home essentials.'),
    (4, 'Beauty and Grooming', 'Personal care, skincare and grooming products.'),
    (5, 'Groceries', 'Packaged food, cooking supplies and snacks.'),
    (6, 'Books and Stationery', 'Educational books, notes and planning materials.');

INSERT INTO products (product_id, category_id, name, description, price, is_active, created_at) VALUES
    (1, 1, 'NexaOne Smartphone', 'Android smartphone with 128GB storage.', 380000.00, TRUE, '2026-09-08 09:00:00'),
    (2, 1, 'ClearSound Wireless Earbuds', 'Bluetooth earbuds with charging case.', 42000.00, TRUE, '2026-09-08 09:10:00'),
    (3, 1, 'LiteBook 14 Laptop', 'Lightweight laptop for study and office work.', 620000.00, TRUE, '2026-09-08 09:20:00'),
    (4, 1, 'FastCharge Power Bank', '20000mAh portable charger.', 18500.00, TRUE, '2026-09-08 09:30:00'),
    (5, 2, 'Classic Cotton T-Shirt', 'Plain cotton round-neck shirt.', 8500.00, TRUE, '2026-09-08 10:00:00'),
    (6, 2, 'Leather Sandals', 'Handmade leather sandals.', 22000.00, TRUE, '2026-09-08 10:10:00'),
    (7, 2, 'Ankara Tote Bag', 'Patterned fabric tote bag.', 15000.00, TRUE, '2026-09-08 10:20:00'),
    (8, 3, 'KitchenPro Blender', 'Multi-speed blender for home kitchens.', 39000.00, TRUE, '2026-09-08 11:00:00'),
    (9, 3, 'Non-stick Cookware Set', 'Five-piece non-stick cooking pot set.', 76000.00, TRUE, '2026-09-08 11:10:00'),
    (10, 3, 'LED Desk Lamp', 'Adjustable rechargeable desk lamp.', 14500.00, TRUE, '2026-09-08 11:20:00'),
    (11, 4, 'Shea Butter Lotion', 'Moisturising lotion with shea butter.', 6500.00, TRUE, '2026-09-08 12:00:00'),
    (12, 4, 'Beard Grooming Kit', 'Comb, oil and trimming scissors.', 12500.00, TRUE, '2026-09-08 12:10:00'),
    (13, 5, 'Premium Rice 10kg', 'Parboiled rice packaged in 10kg bag.', 32000.00, TRUE, '2026-09-08 13:00:00'),
    (14, 5, 'Groundnut Oil 5L', 'Cooking oil in sealed 5L container.', 15500.00, TRUE, '2026-09-08 13:10:00'),
    (15, 5, 'Spicy Plantain Chips', 'Crunchy plantain chips snack pack.', 2500.00, TRUE, '2026-09-08 13:20:00'),
    (16, 6, 'Database Systems Textbook', 'Introductory database systems reference text.', 28500.00, TRUE, '2026-09-08 14:00:00'),
    (17, 6, 'Software Architecture Notes', 'Printed study notes for software design.', 18000.00, TRUE, '2026-09-08 14:10:00'),
    (18, 6, 'Project Planner Journal', 'Undated journal for project planning.', 5500.00, TRUE, '2026-09-08 14:20:00');

INSERT INTO inventory (inventory_id, product_id, quantity_in_stock, reorder_level, updated_at) VALUES
    (1, 1, 25, 5, '2026-09-10 09:00:00'),
    (2, 2, 80, 15, '2026-09-10 09:05:00'),
    (3, 3, 12, 3, '2026-09-10 09:10:00'),
    (4, 4, 140, 20, '2026-09-10 09:15:00'),
    (5, 5, 200, 30, '2026-09-10 10:00:00'),
    (6, 6, 45, 8, '2026-09-10 10:05:00'),
    (7, 7, 60, 10, '2026-09-10 10:10:00'),
    (8, 8, 32, 6, '2026-09-10 11:00:00'),
    (9, 9, 18, 4, '2026-09-10 11:05:00'),
    (10, 10, 75, 12, '2026-09-10 11:10:00'),
    (11, 11, 160, 25, '2026-09-10 12:00:00'),
    (12, 12, 70, 10, '2026-09-10 12:05:00'),
    (13, 13, 95, 15, '2026-09-10 13:00:00'),
    (14, 14, 88, 12, '2026-09-10 13:05:00'),
    (15, 15, 300, 50, '2026-09-10 13:10:00'),
    (16, 16, 40, 8, '2026-09-10 14:00:00'),
    (17, 17, 55, 10, '2026-09-10 14:05:00'),
    (18, 18, 120, 20, '2026-09-10 14:10:00');

INSERT INTO orders (order_id, customer_id, shipping_address_id, total_amount, status, created_at) VALUES
    (1, 1, 1, 464000.00, 'confirmed', '2026-09-12 09:35:00'),
    (2, 2, 3, 78500.00, 'delivered', '2026-09-12 11:15:00'),
    (3, 3, 5, 620000.00, 'processing', '2026-09-13 10:40:00'),
    (4, 4, 6, 56000.00, 'shipped', '2026-09-13 14:05:00'),
    (5, 5, 7, 47500.00, 'confirmed', '2026-09-14 08:25:00'),
    (6, 6, 8, 50500.00, 'delivered', '2026-09-14 15:30:00'),
    (7, 1, 2, 59500.00, 'pending', '2026-09-15 12:45:00'),
    (8, 3, 4, 102500.00, 'cancelled', '2026-09-15 16:20:00');

INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price) VALUES
    (1, 1, 1, 1, 380000.00),
    (2, 1, 2, 2, 42000.00),
    (3, 2, 9, 1, 76000.00),
    (4, 2, 15, 1, 2500.00),
    (5, 3, 3, 1, 620000.00),
    (6, 4, 8, 1, 39000.00),
    (7, 4, 10, 1, 14500.00),
    (8, 4, 15, 1, 2500.00),
    (9, 5, 13, 1, 32000.00),
    (10, 5, 14, 1, 15500.00),
    (11, 6, 16, 1, 28500.00),
    (12, 6, 6, 1, 22000.00),
    (13, 7, 12, 1, 12500.00),
    (14, 7, 11, 3, 6500.00),
    (15, 7, 7, 1, 15000.00),
    (16, 7, 15, 5, 2500.00),
    (17, 8, 2, 2, 42000.00),
    (18, 8, 4, 1, 18500.00);

INSERT INTO payments (payment_id, order_id, amount, payment_method, payment_status, transaction_reference, paid_at) VALUES
    (1, 1, 464000.00, 'card', 'successful', 'NCX-PAY-20260912-001', '2026-09-12 09:38:00'),
    (2, 2, 78500.00, 'bank_transfer', 'failed', 'NCX-PAY-20260912-002A', '2026-09-12 11:18:00'),
    (3, 2, 78500.00, 'bank_transfer', 'successful', 'NCX-PAY-20260912-002B', '2026-09-12 11:25:00'),
    (4, 3, 620000.00, 'card', 'pending', 'NCX-PAY-20260913-003', NULL),
    (5, 4, 56000.00, 'wallet', 'successful', 'NCX-PAY-20260913-004', '2026-09-13 14:07:00'),
    (6, 5, 47500.00, 'card', 'successful', 'NCX-PAY-20260914-005', '2026-09-14 08:28:00'),
    (7, 6, 50500.00, 'bank_transfer', 'successful', 'NCX-PAY-20260914-006', '2026-09-14 15:34:00'),
    (8, 7, 59500.00, 'wallet', 'pending', 'NCX-PAY-20260915-007', NULL),
    (9, 8, 102500.00, 'card', 'failed', 'NCX-PAY-20260915-008', '2026-09-15 16:23:00');

INSERT INTO shipments (shipment_id, order_id, tracking_number, status, shipped_at, delivered_at) VALUES
    (1, 1, 'NCX-SHP-20260912-001', 'pending', NULL, NULL),
    (2, 2, 'NCX-SHP-20260912-002', 'delivered', '2026-09-12 17:00:00', '2026-09-14 10:30:00'),
    (3, 4, 'NCX-SHP-20260913-004', 'shipped', '2026-09-14 09:10:00', NULL),
    (4, 6, 'NCX-SHP-20260914-006', 'delivered', '2026-09-15 08:45:00', '2026-09-16 13:20:00');

INSERT INTO reviews (review_id, customer_id, product_id, rating, comment, created_at) VALUES
    (1, 1, 1, 4, 'The phone is fast and the battery lasts through a busy day.', '2026-09-18 09:00:00'),
    (2, 1, 2, 5, 'Clear audio and easy pairing with my phone.', '2026-09-18 09:10:00'),
    (3, 2, 9, 5, 'The cookware set arrived well packaged and works well.', '2026-09-18 11:30:00'),
    (4, 3, 3, 4, 'Good performance for school work and project documentation.', '2026-09-19 10:00:00'),
    (5, 4, 8, 4, 'The blender is powerful enough for daily kitchen use.', '2026-09-19 12:15:00'),
    (6, 5, 13, 5, 'Good rice quality and the package size is convenient.', '2026-09-20 08:45:00'),
    (7, 6, 16, 4, 'Useful textbook for understanding database design concepts.', '2026-09-20 14:20:00');

SELECT setval(pg_get_serial_sequence('customers', 'customer_id'), (SELECT MAX(customer_id) FROM customers));
SELECT setval(pg_get_serial_sequence('addresses', 'address_id'), (SELECT MAX(address_id) FROM addresses));
SELECT setval(pg_get_serial_sequence('categories', 'category_id'), (SELECT MAX(category_id) FROM categories));
SELECT setval(pg_get_serial_sequence('products', 'product_id'), (SELECT MAX(product_id) FROM products));
SELECT setval(pg_get_serial_sequence('inventory', 'inventory_id'), (SELECT MAX(inventory_id) FROM inventory));
SELECT setval(pg_get_serial_sequence('orders', 'order_id'), (SELECT MAX(order_id) FROM orders));
SELECT setval(pg_get_serial_sequence('order_items', 'order_item_id'), (SELECT MAX(order_item_id) FROM order_items));
SELECT setval(pg_get_serial_sequence('payments', 'payment_id'), (SELECT MAX(payment_id) FROM payments));
SELECT setval(pg_get_serial_sequence('shipments', 'shipment_id'), (SELECT MAX(shipment_id) FROM shipments));
SELECT setval(pg_get_serial_sequence('reviews', 'review_id'), (SELECT MAX(review_id) FROM reviews));

COMMIT;
