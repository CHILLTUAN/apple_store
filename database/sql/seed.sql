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
     '32GB', '1TB', '35W');

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
    (16, 8, 'images/products/macbook_air_13inch_m5_32gb_skyblue2.png', 0, '2026-10-22T15:19:28.947');

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
