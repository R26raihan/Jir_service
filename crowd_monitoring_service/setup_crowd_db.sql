-- Setup Database untuk Crowd Monitoring Service
-- Jalankan script ini di phpMyAdmin

-- Buat database
CREATE DATABASE IF NOT EXISTS crowd_monitoring;
USE crowd_monitoring;

-- Buat tabel untuk data crowd history
CREATE TABLE IF NOT EXISTS crowd_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    location VARCHAR(100) NOT NULL,
    count INT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_location (location),
    INDEX idx_timestamp (timestamp),
    INDEX idx_location_timestamp (location, timestamp)
);

-- Buat tabel untuk lokasi CCTV
CREATE TABLE IF NOT EXISTS locations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    cctv_url TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Buat tabel untuk ROI (Region of Interest) coordinates
CREATE TABLE IF NOT EXISTS roi_coordinates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    location_id INT NOT NULL,
    point_order INT NOT NULL,
    x_coordinate INT NOT NULL,
    y_coordinate INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE,
    INDEX idx_location_order (location_id, point_order)
);

-- Buat tabel untuk density maps
CREATE TABLE IF NOT EXISTS density_maps (
    id INT AUTO_INCREMENT PRIMARY KEY,
    location_id INT NOT NULL,
    density_map_base64 LONGTEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE,
    INDEX idx_location_timestamp (location_id, timestamp)
);

-- Insert data lokasi CCTV sesuai dengan app.py
INSERT INTO locations (name, cctv_url, description) VALUES
('DPR', 'https://cctv.balitower.co.id/Bendungan-Hilir-003-700014_1/embed.html', 'CCTV DPR - Bendungan Hilir'),
('Patung Kuda', 'https://cctv.balitower.co.id/JPO-Merdeka-Barat-507357_9/embed.html', 'CCTV Patung Kuda - JPO Merdeka Barat')
ON DUPLICATE KEY UPDATE
    cctv_url = VALUES(cctv_url),
    description = VALUES(description),
    updated_at = CURRENT_TIMESTAMP;

-- Insert ROI coordinates untuk Patung Kuda
INSERT INTO roi_coordinates (location_id, point_order, x_coordinate, y_coordinate) VALUES
(2, 1, 224, 675),
(2, 2, 392, 383),
(2, 3, 644, 377),
(2, 4, 970, 671)
ON DUPLICATE KEY UPDATE
    x_coordinate = VALUES(x_coordinate),
    y_coordinate = VALUES(y_coordinate);

-- Insert ROI coordinates untuk DPR
INSERT INTO roi_coordinates (location_id, point_order, x_coordinate, y_coordinate) VALUES
(1, 1, 7, 346),
(1, 2, 1067, 375),
(1, 3, 1070, 513),
(1, 4, 5, 454)
ON DUPLICATE KEY UPDATE
    x_coordinate = VALUES(x_coordinate),
    y_coordinate = VALUES(y_coordinate);

-- Insert sample crowd data untuk testing
INSERT INTO crowd_history (location, count, timestamp) VALUES
('DPR', 45, NOW() - INTERVAL 5 MINUTE),
('DPR', 52, NOW() - INTERVAL 4 MINUTE),
('DPR', 38, NOW() - INTERVAL 3 MINUTE),
('DPR', 61, NOW() - INTERVAL 2 MINUTE),
('DPR', 47, NOW() - INTERVAL 1 MINUTE),
('Patung Kuda', 23, NOW() - INTERVAL 5 MINUTE),
('Patung Kuda', 31, NOW() - INTERVAL 4 MINUTE),
('Patung Kuda', 28, NOW() - INTERVAL 3 MINUTE),
('Patung Kuda', 35, NOW() - INTERVAL 2 MINUTE),
('Patung Kuda', 42, NOW() - INTERVAL 1 MINUTE)
ON DUPLICATE KEY UPDATE
    count = VALUES(count),
    timestamp = VALUES(timestamp);

-- Buat view untuk data crowd dengan lokasi info
CREATE OR REPLACE VIEW crowd_history_view AS
SELECT 
    ch.id,
    ch.location,
    l.description as location_description,
    ch.count,
    ch.timestamp,
    ch.created_at
FROM crowd_history ch
LEFT JOIN locations l ON ch.location = l.name
ORDER BY ch.timestamp DESC;

-- Buat view untuk statistik crowd per lokasi
CREATE OR REPLACE VIEW crowd_stats_view AS
SELECT 
    location,
    COUNT(*) as total_records,
    AVG(count) as avg_count,
    MIN(count) as min_count,
    MAX(count) as max_count,
    SUM(count) as total_count,
    DATE(timestamp) as date
FROM crowd_history
GROUP BY location, DATE(timestamp)
ORDER BY date DESC, location;

-- Buat index untuk performa
CREATE INDEX idx_crowd_history_location_timestamp ON crowd_history(location, timestamp);
CREATE INDEX idx_crowd_history_timestamp ON crowd_history(timestamp);
CREATE INDEX idx_density_maps_location_timestamp ON density_maps(location_id, timestamp);

-- Tampilkan hasil setup
SELECT 'Database crowd_monitoring berhasil dibuat!' as status;
SELECT COUNT(*) as total_locations FROM locations;
SELECT COUNT(*) as total_crowd_records FROM crowd_history;
SELECT COUNT(*) as total_roi_coordinates FROM roi_coordinates;

-- Tampilkan data lokasi
SELECT name, description, is_active FROM locations;

-- Tampilkan sample crowd data
SELECT location, count, timestamp FROM crowd_history ORDER BY timestamp DESC LIMIT 10;
