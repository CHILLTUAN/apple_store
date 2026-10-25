CREATE TABLE Users (
    user_id INT IDENTITY(1, 1) PRIMARY KEY,
    full_name NVARCHAR(100) NOT NULL,
    phone VARCHAR(15),
    email VARCHAR(100) UNIQUE,
    address NVARCHAR(255),
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role TINYINT NOT NULL DEFAULT 3,
    is_active BIT DEFAULT 1,
    created_at DATETIME DEFAULT GETDATE()
)
GO

CREATE TABLE Categories (
    category_id INT IDENTITY(1, 1) PRIMARY KEY,
    category_name NVARCHAR(100) NOT NULL,
    is_active BIT DEFAULT 1,
    created_at DATETIME DEFAULT GETDATE(),
    slug VARCHAR(100) NOT NULL UNIQUE,
    image_url NVARCHAR(255) NULL
)
GO



CREATE TABLE Products (
    product_id INT IDENTITY(1, 1) PRIMARY KEY,
    category_id INT NOT NULL,
    product_name NVARCHAR(200) NOT NULL,
    color NVARCHAR(50),
    description NVARCHAR(MAX),
    price DECIMAL(18, 2) NOT NULL,
    stock_quantity INT NOT NULL DEFAULT 0,
    is_active BIT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT GETDATE(),
    ram VARCHAR(20),
    rom VARCHAR(20),
    charger_power VARCHAR(20),

    FOREIGN KEY (category_id)
        REFERENCES Categories(category_id)
);
GO

CREATE TABLE ProductImages (
    image_id INT IDENTITY(1, 1) PRIMARY KEY,
    product_id INT NOT NULL,
    image_url VARCHAR(255) NOT NULL,
    is_primary BIT DEFAULT 0,
    created_at DATETIME DEFAULT GETDATE(),

    FOREIGN KEY (product_id)
        REFERENCES Products(product_id)
)
GO

CREATE TABLE Orders (
    order_id INT IDENTITY(1, 1) PRIMARY KEY,
    user_id INT NOT NULL,
    order_date DATETIME DEFAULT GETDATE(),
    total_amount DECIMAL(18, 2) NOT NULL,
    payment_method NVARCHAR(50),
    payment_status NVARCHAR(50) DEFAULT N'Chưa thanh toán',
    shipping_address NVARCHAR(255) NOT NULL,
    shipping_fee DECIMAL(18, 2) DEFAULT 0,
    order_status NVARCHAR(50) DEFAULT N'Chờ duyệt',
    note NVARCHAR(255),

    FOREIGN KEY (user_id)
        REFERENCES Users(user_id)
)
GO

CREATE TABLE OrderDetails (
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(18, 2) NOT NULL,

    PRIMARY KEY(order_id, product_id),

    FOREIGN KEY (order_id)
        REFERENCES Orders(order_id),

    FOREIGN KEY (product_id)
        REFERENCES Products(product_id)
)