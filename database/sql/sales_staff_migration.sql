IF COL_LENGTH(N'dbo.Orders', N'stock_committed') IS NULL
BEGIN
    ALTER TABLE dbo.Orders
    ADD stock_committed BIT NOT NULL
        CONSTRAINT DF_Orders_stock_committed DEFAULT 1;
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM dbo.Users
    WHERE username = 'SALESTAFF'
)
BEGIN
    INSERT INTO dbo.Users (
        full_name, email, username, password_hash, role, is_active
    )
    VALUES (
        N'Nhân viên bán hàng',
        'SALESTAFF@apple-store.local',
        'SALESTAFF',
        'scrypt:32768:8:1$TRNV7R62qWsR1vg4$7febf097a85b570f674a09be04a822aee3ce719bacbccf136394816fc089a380aca01b4e31248f12319ecfcec06667fc41b557eb9c20414424aad646bbd4e519',
        2,
        1
    );
END;
GO
