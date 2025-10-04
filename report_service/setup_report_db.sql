-- MySQL schema for storing OCR final results
-- Database: report_service (create if not exists)

CREATE DATABASE IF NOT EXISTS report_service
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE report_service;

-- Table: ocr_results
CREATE TABLE IF NOT EXISTS ocr_results (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  message TEXT NULL,
  lokasi VARCHAR(255) NULL,
  latitude DECIMAL(9,6) NULL,
  longitude DECIMAL(9,6) NULL,
  source_file VARCHAR(255) NULL,
  engine VARCHAR(100) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  INDEX idx_created_at (created_at),
  INDEX idx_lokasi (lokasi),
  INDEX idx_lat_lon (latitude, longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS reports (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  report_type ENUM('banjir', 'kebakaran', 'pohon_tumbang', 'kecelakaan', 'lainnya') NOT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT NULL,
  location VARCHAR(255) NULL,
  latitude DECIMAL(9,6) NULL,
  longitude DECIMAL(9,6) NULL,
  reporter_name VARCHAR(255) NULL,
  reporter_phone VARCHAR(20) NULL,
  reporter_email VARCHAR(255) NULL,
  urgency ENUM('rendah', 'sedang', 'tinggi', 'darurat') NOT NULL DEFAULT 'sedang',
  status ENUM('dilaporkan', 'diproses', 'selesai', 'ditolak') NOT NULL DEFAULT 'dilaporkan',
  evidence_files JSON NULL, -- Store array of file paths/names
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  INDEX idx_report_type (report_type),
  INDEX idx_status (status),
  INDEX idx_urgency (urgency),
  INDEX idx_created_at (created_at),
  INDEX idx_location (location),
  INDEX idx_lat_lon (latitude, longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Optional view for quick latest items
CREATE OR REPLACE VIEW v_ocr_results_latest AS
SELECT id, message, lokasi, latitude, longitude, source_file, engine, created_at
FROM ocr_results
ORDER BY created_at DESC;

-- View for latest reports
CREATE OR REPLACE VIEW v_reports_latest AS
SELECT id, report_type, title, description, location, latitude, longitude, 
       reporter_name, urgency, status, evidence_files, created_at, updated_at
FROM reports
ORDER BY created_at DESC;


