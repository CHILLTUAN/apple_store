IF OBJECT_ID(N'dbo.StoreSettings', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.StoreSettings (
        setting_key NVARCHAR(100) NOT NULL PRIMARY KEY,
        setting_value INT NOT NULL
    );
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM dbo.StoreSettings
    WHERE setting_key = N'homepage_products_per_category'
)
BEGIN
    INSERT INTO dbo.StoreSettings (setting_key, setting_value)
    VALUES (N'homepage_products_per_category', 4);
END;
GO
