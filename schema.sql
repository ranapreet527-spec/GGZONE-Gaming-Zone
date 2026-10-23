
CREATE DATABASE IF NOT EXISTS gaming_zone
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE gaming_zone;

-- 1. Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('customer', 'admin')
        NOT NULL DEFAULT 'customer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Games table
CREATE TABLE IF NOT EXISTS games (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE,
    genre VARCHAR(80) NOT NULL,
    platform ENUM('PC', 'PlayStation', 'Xbox') NOT NULL,
    description TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 3. Gaming stations table
CREATE TABLE IF NOT EXISTS stations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    station_type ENUM('PC', 'PlayStation', 'Xbox') NOT NULL,
    hourly_rate DECIMAL(10,2) NOT NULL DEFAULT 100.00,
    status ENUM('available', 'maintenance')
        NOT NULL DEFAULT 'available'
);

-- 4. Compatible games for each station
CREATE TABLE IF NOT EXISTS station_games (
    station_id INT NOT NULL,
    game_id INT NOT NULL,

    PRIMARY KEY (station_id, game_id),

    FOREIGN KEY (station_id)
        REFERENCES stations(id)
        ON DELETE CASCADE,

    FOREIGN KEY (game_id)
        REFERENCES games(id)
        ON DELETE CASCADE
);

-- 5. Customer bookings
CREATE TABLE IF NOT EXISTS bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    station_id INT NOT NULL,
    game_id INT NOT NULL,
    booking_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,

    status ENUM(
        'pending',
        'approved',
        'rejected',
        'completed',
        'cancelled'
    ) NOT NULL DEFAULT 'pending',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id),

    FOREIGN KEY (station_id)
        REFERENCES stations(id),

    FOREIGN KEY (game_id)
        REFERENCES games(id),

    INDEX idx_station_booking (
        station_id,
        booking_date,
        status,
        start_time,
        end_time
    )
);

-- 6. Gaming sessions
CREATE TABLE IF NOT EXISTS gaming_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL UNIQUE,
    actual_start DATETIME NULL,
    actual_end DATETIME NULL,

    status ENUM(
        'not_started',
        'running',
        'ended'
    ) NOT NULL DEFAULT 'not_started',

    FOREIGN KEY (booking_id)
        REFERENCES bookings(id)
);

-- 7. Billing and payment records
CREATE TABLE IF NOT EXISTS bills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL UNIQUE,
    amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,

    payment_status ENUM('unpaid', 'paid')
        NOT NULL DEFAULT 'unpaid',

    payment_method ENUM('Cash', 'UPI', 'Card') NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (booking_id)
        REFERENCES bookings(id)
);
