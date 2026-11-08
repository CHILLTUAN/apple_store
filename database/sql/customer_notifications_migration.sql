IF OBJECT_ID(N'dbo.CustomerNotifications', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.CustomerNotifications (
        notification_id BIGINT IDENTITY(1, 1) PRIMARY KEY,
        user_id INT NOT NULL,
        order_id INT NOT NULL,
        notification_type NVARCHAR(30) NOT NULL,
        title NVARCHAR(120) NOT NULL,
        message NVARCHAR(500) NOT NULL,
        is_read BIT NOT NULL
            CONSTRAINT DF_CustomerNotifications_is_read DEFAULT 0,
        created_at DATETIME NOT NULL
            CONSTRAINT DF_CustomerNotifications_created_at DEFAULT GETDATE(),
        CONSTRAINT FK_CustomerNotifications_Users
            FOREIGN KEY (user_id) REFERENCES dbo.Users(user_id)
            ON DELETE CASCADE
    );
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_CustomerNotifications_user_unread_created'
        AND object_id = OBJECT_ID(N'dbo.CustomerNotifications')
)
BEGIN
    CREATE INDEX IX_CustomerNotifications_user_unread_created
        ON dbo.CustomerNotifications(user_id, is_read, created_at DESC);
END;
GO
