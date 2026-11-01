USE APPLESTORE_SCHEMA_TEST
/*
    Apple Store - Seed Data
    Nạp dữ liệu mẫu cho:
    - Categories: 6 bản ghi
    - Products: 8 bản ghi
    - ProductImages: 16 bản ghi

    Chọn đúng database thử nghiệm trong SSMS trước khi chạy.
*/

-- =========================================
-- 1. CATEGORIES
-- =========================================
SET IDENTITY_INSERT dbo.Categories ON;

INSERT INTO dbo.Categories
    (category_id, category_name, is_active, created_at, slug, image_url)
VALUES
    (1, N'Mac',       1, '2026-10-22T12:55:18.097', 'mac',       N'images/categories/mac.png'),
    (2, N'iPad',      1, '2026-10-22T12:55:18.097', 'ipad',      N'images/categories/ipad.png'),
    (3, N'iPhone',    1, '2026-10-22T12:55:18.097', 'iphone',    N'images/categories/iphone.png'),
    (4, N'Watch',     1, '2026-10-22T12:55:18.097', 'watch',     N'images/categories/watch.png'),
    (5, N'Airpods',   1, '2026-10-22T12:55:18.097', 'airpods',   N'images/categories/airpods.png'),
    (6, N'Phụ kiện',  1, '2026-10-22T12:55:18.097', 'phu-kien',  N'images/categories/phu_kien.png');

SET IDENTITY_INSERT dbo.Categories OFF;
GO

-- =========================================
-- 2. PRODUCTS
-- =========================================
SET IDENTITY_INSERT dbo.Products ON;


-- =========================================
-- 2. PRODUCTS
-- Cấu hình: RAM 32GB, sạc 35W
-- ROM: 512GB cho product_id 1-4
--      1TB   cho product_id 5-8
-- =========================================
SET IDENTITY_INSERT dbo.Products ON;

INSERT INTO dbo.Products
    (product_id, category_id, product_name, color,
     description, price, stock_quantity, is_active, created_at,
     ram, rom, charger_power)
VALUES
    (1, 1, N'MacBook Air 13 inch M5 32GB', N'Ánh Sao',
     N'RAM 32GB, SSD 512GB, sạc 35W',
     45490000.00, 0, 1, '2026-10-22T13:54:44.787',
     '32GB', '512GB', '35W'),

    (2, 1, N'MacBook Air 13 inch M5 32GB', N'Bạc',
     N'RAM 32GB, SSD 512GB, sạc 35W',
     45490000.00, 0, 1, '2026-10-22T13:54:44.787',
     '32GB', '512GB', '35W'),

    (3, 1, N'MacBook Air 13 inch M5 32GB', N'Đêm Xanh Thẳm',
     N'RAM 32GB, SSD 512GB, sạc 35W',
     45490000.00, 0, 1, '2026-10-22T13:54:44.787',
     '32GB', '512GB', '35W'),

    (4, 1, N'MacBook Air 13 inch M5 32GB', N'Xanh Da Trời',
     N'RAM 32GB, SSD 512GB, sạc 35W',
     45490000.00, 0, 1, '2026-10-22T13:54:44.787',
     '32GB', '512GB', '35W'),

    (5, 1, N'MacBook Air 13 inch M5 32GB', N'Ánh Sao',
     N'RAM 32GB, SSD 1TB, sạc 35W',
     53290000.00, 0, 1, '2026-10-22T13:54:44.787',
     '32GB', '1TB', '35W'),

    (6, 1, N'MacBook Air 13 inch M5 32GB', N'Bạc',
     N'RAM 32GB, SSD 1TB, sạc 35W',
     53290000.00, 0, 1, '2026-10-22T13:54:44.787',
     '32GB', '1TB', '35W'),

    (7, 1, N'MacBook Air 13 inch M5 32GB', N'Đêm Xanh Thẳm',
     N'RAM 32GB, SSD 1TB, sạc 35W',
     53290000.00, 0, 1, '2026-10-22T13:54:44.787',
     '32GB', '1TB', '35W'),

    (8, 1, N'MacBook Air 13 inch M5 32GB', N'Xanh Da Trời',
     N'RAM 32GB, SSD 1TB, sạc 35W',
     53290000.00, 0, 1, '2026-10-22T13:54:44.787',
     '32GB', '1TB', '35W'),

    -- Sample iPad catalog entries; the category image is a temporary placeholder.
    (9, 2, N'iPad Pro 11 inch', N'Đen',
     N'Dữ liệu mẫu iPad Pro 11 inch',
     29990000.00, 0, 1, '2026-10-23T13:54:44.787',
     NULL, '256GB', NULL),

    (10, 2, N'iPad Pro 13 inch', N'Đen',
     N'Dữ liệu mẫu iPad Pro 13 inch',
     37990000.00, 0, 1, '2026-10-23T13:54:44.787',
     NULL, '256GB', NULL),

    (11, 2, N'iPad Air 11 inch', N'Xanh',
     N'Dữ liệu mẫu iPad Air 11 inch',
     19990000.00, 0, 1, '2026-10-23T13:54:44.787',
     NULL, '128GB', NULL),

    (12, 2, N'iPad Air 13 inch', N'Xanh',
     N'Dữ liệu mẫu iPad Air 13 inch',
     26990000.00, 0, 1, '2026-10-23T13:54:44.787',
     NULL, '128GB', NULL),

    -- Sample iPhone catalog entries; the category image is a temporary placeholder.
    (13, 3, N'iPhone 17', N'Đen',
     N'Dữ liệu mẫu iPhone 17',
     24990000.00, 0, 1, '2026-10-24T13:54:44.787',
     NULL, '256GB', NULL),

    (14, 3, N'iPhone Air', N'Trắng',
     N'Dữ liệu mẫu iPhone Air',
     31990000.00, 0, 1, '2026-10-24T13:54:44.787',
     NULL, '256GB', NULL),

    (15, 3, N'iPhone 17 Pro', N'Cam Vũ Trụ',
     N'Dữ liệu mẫu iPhone 17 Pro',
     34990000.00, 0, 1, '2026-10-24T13:54:44.787',
     NULL, '256GB', NULL),

    (16, 3, N'iPhone 17 Pro Max', N'Xanh Đậm',
     N'Dữ liệu mẫu iPhone 17 Pro Max',
     37990000.00, 0, 1, '2026-10-24T13:54:44.787',
     NULL, '256GB', NULL),

    -- Sample Watch catalog entries; the category image is a temporary placeholder.
    (17, 4, N'Apple Watch Series 11 42mm', N'Đen',
     N'Dữ liệu mẫu Apple Watch Series 11 42mm',
     10990000.00, 0, 1, '2026-10-24T13:54:44.787',
     NULL, NULL, NULL),

    (18, 4, N'Apple Watch Series 11 46mm', N'Bạc',
     N'Dữ liệu mẫu Apple Watch Series 11 46mm',
     11990000.00, 0, 1, '2026-10-24T13:54:44.787',
     NULL, NULL, NULL),

    (19, 4, N'Apple Watch SE 3 40mm', N'Đen',
     N'Dữ liệu mẫu Apple Watch SE 3 40mm',
     6490000.00, 0, 1, '2026-10-24T13:54:44.787',
     NULL, NULL, NULL),

    (20, 4, N'Apple Watch Ultra 3 49mm', N'Titan Tự Nhiên',
     N'Dữ liệu mẫu Apple Watch Ultra 3 49mm',
     22990000.00, 0, 1, '2026-10-24T13:54:44.787',
     NULL, NULL, NULL),

    -- Sample AirPods catalog entries; the category image is a temporary placeholder.
    (21, 5, N'AirPods 4', N'Trắng',
     N'Dữ liệu mẫu AirPods 4',
     3490000.00, 0, 1, '2026-10-24T13:54:44.787',
     NULL, NULL, NULL),

    (22, 5, N'AirPods 4 chống ồn chủ động', N'Trắng',
     N'Dữ liệu mẫu AirPods 4 chống ồn chủ động',
     4990000.00, 0, 1, '2026-10-24T13:54:44.787',
     NULL, NULL, NULL),

    (23, 5, N'AirPods Pro 3', N'Trắng',
     N'Dữ liệu mẫu AirPods Pro 3',
     6490000.00, 0, 1, '2026-10-24T13:54:44.787',
     NULL, NULL, NULL),

    (24, 5, N'AirPods Max USB-C', N'Đêm Xanh Thẳm',
     N'Dữ liệu mẫu AirPods Max USB-C',
     13990000.00, 0, 1, '2026-10-24T13:54:44.787',
     NULL, NULL, NULL),

    -- Sample accessories; the category image is a temporary placeholder.
    (25, 6, N'Cáp sạc USB-C 60W', N'Trắng',
     N'Dữ liệu mẫu cáp sạc USB-C 60W',
     590000.00, 0, 1, '2026-10-24T13:54:44.787',
     NULL, NULL, '60W'),

    (26, 6, N'Củ sạc USB-C 20W', N'Trắng',
     N'Dữ liệu mẫu củ sạc USB-C 20W',
     490000.00, 0, 1, '2026-10-24T13:54:44.787',
     NULL, NULL, '20W'),

    (27, 6, N'Củ sạc USB-C kép 35W', N'Trắng',
     N'Dữ liệu mẫu củ sạc USB-C kép 35W',
     1490000.00, 0, 1, '2026-10-24T13:54:44.787',
     NULL, NULL, '35W'),

    (28, 6, N'Bộ sạc MagSafe', N'Trắng',
     N'Dữ liệu mẫu bộ sạc MagSafe',
     1190000.00, 0, 1, '2026-10-24T13:54:44.787',
     NULL, NULL, NULL);

SET IDENTITY_INSERT dbo.Products OFF;
GO

-- =========================================
-- 3. PRODUCT IMAGES
-- =========================================
SET IDENTITY_INSERT dbo.ProductImages ON;

INSERT INTO dbo.ProductImages
    (image_id, product_id, image_url, is_primary, created_at)
VALUES
    (1,  1, 'images/products/macbook_air_13inch_m5_32gb_starlight1.png', 1, '2026-10-22T15:19:28.947'),
    (2,  5, 'images/products/macbook_air_13inch_m5_32gb_starlight1.png', 1, '2026-10-22T15:19:28.947'),
    (3,  1, 'images/products/macbook_air_13inch_m5_32gb_starlight2.png', 0, '2026-10-22T15:19:28.947'),
    (4,  5, 'images/products/macbook_air_13inch_m5_32gb_starlight2.png', 0, '2026-10-22T15:19:28.947'),

    (5,  2, 'images/products/macbook_air_13inch_m5_32gb_silver1.png', 1, '2026-10-22T15:19:28.947'),
    (6,  6, 'images/products/macbook_air_13inch_m5_32gb_silver1.png', 1, '2026-10-22T15:19:28.947'),
    (7,  2, 'images/products/macbook_air_13inch_m5_32gb_silver2.png', 0, '2026-10-22T15:19:28.947'),
    (8,  6, 'images/products/macbook_air_13inch_m5_32gb_silver2.png', 0, '2026-10-22T15:19:28.947'),

    (9,  3, 'images/products/macbook_air_13inch_m5_32gb_midnight1.png', 1, '2026-10-22T15:19:28.947'),
    (10, 7, 'images/products/macbook_air_13inch_m5_32gb_midnight1.png', 1, '2026-10-22T15:19:28.947'),
    (11, 3, 'images/products/macbook_air_13inch_m5_32gb_midnight2.png', 0, '2026-10-22T15:19:28.947'),
    (12, 7, 'images/products/macbook_air_13inch_m5_32gb_midnight2.png', 0, '2026-10-22T15:19:28.947'),

    (13, 4, 'images/products/macbook_air_13inch_m5_32gb_skyblue1.png', 1, '2026-10-22T15:19:28.947'),
    (14, 8, 'images/products/macbook_air_13inch_m5_32gb_skyblue1.png', 1, '2026-10-22T15:19:28.947'),
    (15, 4, 'images/products/macbook_air_13inch_m5_32gb_skyblue2.png', 0, '2026-10-22T15:19:28.947'),
    (16, 8, 'images/products/macbook_air_13inch_m5_32gb_skyblue2.png', 0, '2026-10-22T15:19:28.947'),
    --Model Ipad
    (17, 9, 'images/categories/ipad.png', 1, '2026-10-23T15:19:28.947'),
    (18, 10, 'images/categories/ipad.png', 1, '2026-10-23T15:19:28.947'),
    (19, 11, 'images/categories/ipad.png', 1, '2026-10-23T15:19:28.947'),
    (20, 12, 'images/categories/ipad.png', 1, '2026-10-23T15:19:28.947'),
    -- Sample product images use category placeholders until product photos are added.
    (21, 13, 'images/categories/iphone.png', 1, '2026-10-24T15:19:28.947'),
    (22, 14, 'images/categories/iphone.png', 1, '2026-10-24T15:19:28.947'),
    (23, 15, 'images/categories/iphone.png', 1, '2026-10-24T15:19:28.947'),
    (24, 16, 'images/categories/iphone.png', 1, '2026-10-24T15:19:28.947'),

    (25, 17, 'images/categories/watch.png', 1, '2026-10-24T15:19:28.947'),
    (26, 18, 'images/categories/watch.png', 1, '2026-10-24T15:19:28.947'),
    (27, 19, 'images/categories/watch.png', 1, '2026-10-24T15:19:28.947'),
    (28, 20, 'images/categories/watch.png', 1, '2026-10-24T15:19:28.947'),

    (29, 21, 'images/categories/airpods.png', 1, '2026-10-24T15:19:28.947'),
    (30, 22, 'images/categories/airpods.png', 1, '2026-10-24T15:19:28.947'),
    (31, 23, 'images/categories/airpods.png', 1, '2026-10-24T15:19:28.947'),
    (32, 24, 'images/categories/airpods.png', 1, '2026-10-24T15:19:28.947'),

    (33, 25, 'images/categories/phu_kien.png', 1, '2026-10-24T15:19:28.947'),
    (34, 26, 'images/categories/phu_kien.png', 1, '2026-10-24T15:19:28.947'),
    (35, 27, 'images/categories/phu_kien.png', 1, '2026-10-24T15:19:28.947'),
    (36, 28, 'images/categories/phu_kien.png', 1, '2026-10-24T15:19:28.947');

SET IDENTITY_INSERT dbo.ProductImages OFF;
GO


SELECT COUNT(*) AS CategoryCount FROM dbo.Categories;
SELECT COUNT(*) AS ProductCount FROM dbo.Products;
SELECT COUNT(*) AS ProductImageCount FROM dbo.ProductImages;


-- 1. Kiểm tra số lượng dữ liệu
SELECT 'Categories' AS table_name, COUNT(*) AS total
FROM dbo.Categories
UNION ALL
SELECT 'Products', COUNT(*) FROM dbo.Products
UNION ALL
SELECT 'ProductImages', COUNT(*) FROM dbo.ProductImages
UNION ALL
SELECT 'Users', COUNT(*) FROM dbo.Users
UNION ALL
SELECT 'Orders', COUNT(*) FROM dbo.Orders
UNION ALL
SELECT 'OrderDetails', COUNT(*) FROM dbo.OrderDetails;
GO

-- 2. Kiểm tra khóa ngoại sản phẩm
SELECT p.product_id, p.product_name, c.category_name
FROM dbo.Products AS p
JOIN dbo.Categories AS c
    ON p.category_id = c.category_id;
GO
