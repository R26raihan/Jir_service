-- Setup Database untuk Banjir Service
-- Jalankan script ini di phpMyAdmin

-- Buat database
CREATE DATABASE IF NOT EXISTS banjir_monitoring;
USE banjir_monitoring;

-- Buat tabel untuk data pintu air
CREATE TABLE IF NOT EXISTS pintu_air (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nama_pintu_air VARCHAR(255) NOT NULL,
    status VARCHAR(100),
    ketinggian_air DECIMAL(10, 2),
    kapasitas DECIMAL(10, 2),
    unit VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_nama_pintu_air (nama_pintu_air),
    INDEX idx_timestamp (timestamp),
    INDEX idx_status (status)
);

-- Buat tabel untuk data RT terdampak banjir
CREATE TABLE IF NOT EXISTS rt_terdampak (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rt VARCHAR(10) NOT NULL,
    rw VARCHAR(10) NOT NULL,
    kelurahan VARCHAR(255) NOT NULL,
    tinggi_genangan DECIMAL(10, 2) NOT NULL,
    unit_tinggi VARCHAR(10) DEFAULT 'cm',
    status_banjir ENUM('ringan', 'sedang', 'berat') DEFAULT 'ringan',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_rt_rw (rt, rw),
    INDEX idx_kelurahan (kelurahan),
    INDEX idx_timestamp (timestamp),
    INDEX idx_status_banjir (status_banjir)
);

-- Buat tabel untuk lokasi pintu air
CREATE TABLE IF NOT EXISTS lokasi_pintu_air (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nama VARCHAR(255) NOT NULL UNIQUE,
    alamat TEXT,
    koordinat_lat DECIMAL(10, 8),
    koordinat_lng DECIMAL(11, 8),
    deskripsi TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Buat tabel untuk statistik banjir
CREATE TABLE IF NOT EXISTS statistik_banjir (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tanggal DATE NOT NULL,
    total_rt_terdampak INT DEFAULT 0,
    total_kelurahan_terdampak INT DEFAULT 0,
    rata_rata_tinggi_genangan DECIMAL(10, 2) DEFAULT 0.00,
    max_tinggi_genangan DECIMAL(10, 2) DEFAULT 0.00,
    status_terparah ENUM('ringan', 'sedang', 'berat') DEFAULT 'ringan',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_date (tanggal),
    INDEX idx_tanggal (tanggal)
);

-- Insert sample data pintu air
INSERT INTO pintu_air (nama_pintu_air, status, ketinggian_air, kapasitas, unit) VALUES
('Pintu Air Manggarai', 'Normal', 150.50, 200.00, 'cm'),
('Pintu Air Karet', 'Waspada', 180.75, 200.00, 'cm'),
('Pintu Air Depok', 'Siaga', 195.25, 200.00, 'cm'),
('Pintu Air Katulampa', 'Normal', 145.30, 200.00, 'cm'),
('Pintu Air Ciliwung', 'Waspada', 175.80, 200.00, 'cm')
ON DUPLICATE KEY UPDATE
    status = VALUES(status),
    ketinggian_air = VALUES(ketinggian_air),
    timestamp = CURRENT_TIMESTAMP;

-- Insert sample data RT terdampak
INSERT INTO rt_terdampak (rt, rw, kelurahan, tinggi_genangan, status_banjir) VALUES
('001', '001', 'Manggarai', 25.5, 'ringan'),
('002', '001', 'Manggarai', 45.2, 'sedang'),
('003', '002', 'Kebayoran Baru', 15.8, 'ringan'),
('004', '002', 'Kebayoran Baru', 65.3, 'berat'),
('005', '003', 'Kemayoran', 35.7, 'sedang'),
('006', '003', 'Kemayoran', 55.1, 'berat'),
('007', '004', 'Cengkareng', 20.3, 'ringan'),
('008', '004', 'Cengkareng', 40.6, 'sedang'),
('009', '005', 'Tanjung Priok', 30.2, 'sedang'),
('010', '005', 'Tanjung Priok', 70.8, 'berat')
ON DUPLICATE KEY UPDATE
    tinggi_genangan = VALUES(tinggi_genangan),
    status_banjir = VALUES(status_banjir),
    timestamp = CURRENT_TIMESTAMP;

-- Insert sample lokasi pintu air
INSERT INTO lokasi_pintu_air (nama, alamat, koordinat_lat, koordinat_lng, deskripsi) VALUES
('Pintu Air Manggarai', 'Jl. Manggarai Utara, Jakarta Selatan', -6.2088, 106.8456, 'Pintu air utama di Manggarai'),
('Pintu Air Karet', 'Jl. Karet, Jakarta Pusat', -6.1751, 106.8650, 'Pintu air di area Karet'),
('Pintu Air Depok', 'Jl. Depok, Jakarta Selatan', -6.2297, 106.6894, 'Pintu air di Depok'),
('Pintu Air Katulampa', 'Jl. Katulampa, Bogor', -6.2088, 106.8456, 'Pintu air di Katulampa'),
('Pintu Air Ciliwung', 'Jl. Ciliwung, Jakarta Pusat', -6.1751, 106.8650, 'Pintu air di Ciliwung')
ON DUPLICATE KEY UPDATE
    alamat = VALUES(alamat),
    koordinat_lat = VALUES(koordinat_lat),
    koordinat_lng = VALUES(koordinat_lng),
    deskripsi = VALUES(deskripsi),
    updated_at = CURRENT_TIMESTAMP;

-- Insert sample statistik banjir
INSERT INTO statistik_banjir (tanggal, total_rt_terdampak, total_kelurahan_terdampak, rata_rata_tinggi_genangan, max_tinggi_genangan, status_terparah) VALUES
(CURDATE(), 10, 5, 40.85, 70.8, 'berat'),
(CURDATE() - INTERVAL 1 DAY, 8, 4, 35.20, 60.5, 'sedang'),
(CURDATE() - INTERVAL 2 DAY, 5, 3, 25.60, 45.2, 'sedang'),
(CURDATE() - INTERVAL 3 DAY, 3, 2, 20.30, 35.7, 'ringan'),
(CURDATE() - INTERVAL 4 DAY, 2, 1, 15.80, 25.5, 'ringan')
ON DUPLICATE KEY UPDATE
    total_rt_terdampak = VALUES(total_rt_terdampak),
    total_kelurahan_terdampak = VALUES(total_kelurahan_terdampak),
    rata_rata_tinggi_genangan = VALUES(rata_rata_tinggi_genangan),
    max_tinggi_genangan = VALUES(max_tinggi_genangan),
    status_terparah = VALUES(status_terparah),
    updated_at = CURRENT_TIMESTAMP;

-- Buat view untuk data pintu air dengan lokasi
CREATE OR REPLACE VIEW pintu_air_view AS
SELECT 
    pa.id,
    pa.nama_pintu_air,
    pa.status,
    pa.ketinggian_air,
    pa.kapasitas,
    pa.unit,
    lpa.alamat,
    lpa.koordinat_lat,
    lpa.koordinat_lng,
    pa.timestamp,
    pa.created_at
FROM pintu_air pa
LEFT JOIN lokasi_pintu_air lpa ON pa.nama_pintu_air = lpa.nama
ORDER BY pa.timestamp DESC;

-- Buat view untuk statistik RT terdampak per kelurahan
CREATE OR REPLACE VIEW rt_terdampak_stats_view AS
SELECT 
    kelurahan,
    COUNT(*) as total_rt_terdampak,
    AVG(tinggi_genangan) as rata_rata_tinggi_genangan,
    MAX(tinggi_genangan) as max_tinggi_genangan,
    MIN(tinggi_genangan) as min_tinggi_genangan,
    SUM(CASE WHEN status_banjir = 'ringan' THEN 1 ELSE 0 END) as rt_ringan,
    SUM(CASE WHEN status_banjir = 'sedang' THEN 1 ELSE 0 END) as rt_sedang,
    SUM(CASE WHEN status_banjir = 'berat' THEN 1 ELSE 0 END) as rt_berat,
    DATE(timestamp) as tanggal
FROM rt_terdampak
GROUP BY kelurahan, DATE(timestamp)
ORDER BY tanggal DESC, total_rt_terdampak DESC;

-- Buat view untuk dashboard banjir
CREATE OR REPLACE VIEW dashboard_banjir_view AS
SELECT 
    DATE(rt.timestamp) as tanggal,
    COUNT(DISTINCT rt.kelurahan) as total_kelurahan_terdampak,
    COUNT(*) as total_rt_terdampak,
    AVG(rt.tinggi_genangan) as rata_rata_tinggi_genangan,
    MAX(rt.tinggi_genangan) as max_tinggi_genangan,
    CASE 
        WHEN MAX(rt.tinggi_genangan) >= 60 THEN 'berat'
        WHEN MAX(rt.tinggi_genangan) >= 30 THEN 'sedang'
        ELSE 'ringan'
    END as status_terparah,
    COUNT(DISTINCT pa.nama_pintu_air) as total_pintu_air_aktif
FROM rt_terdampak rt
LEFT JOIN pintu_air pa ON DATE(rt.timestamp) = DATE(pa.timestamp)
GROUP BY DATE(rt.timestamp)
ORDER BY tanggal DESC;

-- Buat index untuk performa
CREATE INDEX idx_pintu_air_timestamp ON pintu_air(timestamp);
CREATE INDEX idx_rt_terdampak_kelurahan_timestamp ON rt_terdampak(kelurahan, timestamp);
CREATE INDEX idx_rt_terdampak_status_timestamp ON rt_terdampak(status_banjir, timestamp);
CREATE INDEX idx_statistik_banjir_tanggal ON statistik_banjir(tanggal);

-- Tampilkan hasil setup
SELECT 'Database banjir_monitoring berhasil dibuat!' as status;
SELECT COUNT(*) as total_pintu_air FROM pintu_air;
SELECT COUNT(*) as total_rt_terdampak FROM rt_terdampak;
SELECT COUNT(*) as total_lokasi_pintu_air FROM lokasi_pintu_air;
SELECT COUNT(*) as total_statistik FROM statistik_banjir;

-- Tampilkan sample data pintu air
SELECT nama_pintu_air, status, ketinggian_air, unit, timestamp FROM pintu_air ORDER BY timestamp DESC LIMIT 5;

-- Tampilkan sample data RT terdampak
SELECT rt, rw, kelurahan, tinggi_genangan, status_banjir, timestamp FROM rt_terdampak ORDER BY timestamp DESC LIMIT 5;
