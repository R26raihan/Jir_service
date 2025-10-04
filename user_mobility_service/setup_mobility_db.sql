-- Setup Database untuk User Mobility Service
-- Jalankan script ini di phpMyAdmin

-- Buat database
CREATE DATABASE IF NOT EXISTS user_mobility;
USE user_mobility;

-- Buat tabel untuk data mobilitas user
CREATE TABLE IF NOT EXISTS mobility (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    dest_latitude DECIMAL(10, 8) NOT NULL,
    dest_longitude DECIMAL(11, 8) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Buat tabel untuk user profiles
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Buat tabel untuk lokasi favorit
CREATE TABLE IF NOT EXISTS favorite_locations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    address TEXT,
    is_home BOOLEAN DEFAULT FALSE,
    is_work BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Buat tabel untuk statistik mobilitas
CREATE TABLE IF NOT EXISTS mobility_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    total_trips INT DEFAULT 0,
    total_distance DECIMAL(10, 2) DEFAULT 0.00,
    avg_trip_duration DECIMAL(10, 2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_date (user_id, date)
);

-- Insert sample data untuk testing
INSERT INTO users (user_id, name, email, phone) VALUES
('user001', 'John Doe', 'john@example.com', '+6281234567890'),
('user002', 'Jane Smith', 'jane@example.com', '+6281234567891'),
('user003', 'Bob Johnson', 'bob@example.com', '+6281234567892')
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    email = VALUES(email),
    phone = VALUES(phone);

-- Insert sample mobility data
INSERT INTO mobility (user_id, latitude, longitude, dest_latitude, dest_longitude) VALUES
('user001', -6.2088, 106.8456, -6.1751, 106.8650),
('user001', -6.1751, 106.8650, -6.2088, 106.8456),
('user002', -6.2088, 106.8456, -6.2297, 106.6894),
('user002', -6.2297, 106.6894, -6.2088, 106.8456),
('user003', -6.2088, 106.8456, -6.2088, 106.8456)
ON DUPLICATE KEY UPDATE
    timestamp = CURRENT_TIMESTAMP;

-- Insert sample favorite locations
INSERT INTO favorite_locations (user_id, name, latitude, longitude, address, is_home, is_work) VALUES
('user001', 'Rumah', -6.2088, 106.8456, 'Jl. Sudirman No. 123, Jakarta Pusat', TRUE, FALSE),
('user001', 'Kantor', -6.1751, 106.8650, 'Jl. Thamrin No. 456, Jakarta Pusat', FALSE, TRUE),
('user002', 'Rumah', -6.2088, 106.8456, 'Jl. Gatot Subroto No. 789, Jakarta Selatan', TRUE, FALSE),
('user002', 'Mall', -6.2297, 106.6894, 'Mall Taman Anggrek, Jakarta Barat', FALSE, FALSE),
('user003', 'Rumah', -6.2088, 106.8456, 'Jl. Sudirman No. 321, Jakarta Pusat', TRUE, FALSE)
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    address = VALUES(address);

-- Buat index untuk performa
CREATE INDEX idx_mobility_user_id ON mobility(user_id);
CREATE INDEX idx_mobility_timestamp ON mobility(timestamp);
CREATE INDEX idx_mobility_user_timestamp ON mobility(user_id, timestamp);
CREATE INDEX idx_users_user_id ON users(user_id);
CREATE INDEX idx_favorite_locations_user_id ON favorite_locations(user_id);
CREATE INDEX idx_mobility_stats_user_date ON mobility_stats(user_id, date);

-- Tampilkan hasil
SELECT 'Database user_mobility berhasil dibuat!' as status;
SELECT COUNT(*) as total_users FROM users;
SELECT COUNT(*) as total_mobility_records FROM mobility;
SELECT COUNT(*) as total_favorite_locations FROM favorite_locations;
