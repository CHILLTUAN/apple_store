IF COL_LENGTH(N'dbo.OrderDetails', N'engraving_text') IS NULL
BEGIN
    ALTER TABLE dbo.OrderDetails
    ADD engraving_text NVARCHAR(30) NULL;
END;
GO

IF EXISTS (
    SELECT 1
    FROM sys.columns
    WHERE object_id = OBJECT_ID(N'dbo.Orders')
      AND name = N'note'
      AND max_length <> -1
)
BEGIN
    ALTER TABLE dbo.Orders
    ALTER COLUMN note NVARCHAR(MAX) NULL;
END;
GO
