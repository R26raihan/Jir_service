# 🗄️ Database Setup - Crowd Monitoring Service

## 📋 Overview

Database untuk Crowd Monitoring Service sudah dibuat dengan struktur yang lengkap untuk menyimpan:
- Data crowd history (jumlah orang per waktu)
- Informasi lokasi CCTV
- Koordinat ROI (Region of Interest)
- Density maps (base64 encoded)

## 🚀 Cara Setup Database

### 1. **Import ke phpMyAdmin**

1. Buka phpMyAdmin di http://localhost:8080
2. Login dengan username: `root`, password: `Raihan26`
3. Klik tab **"SQL"**
4. Copy dan paste isi file `setup_crowd_db.sql`
5. Klik **"Go"** untuk menjalankan script

### 2. **Atau menggunakan command line**

```bash
mysql -u root -p < setup_crowd_db.sql
```

## 📊 Struktur Database

### **Database**: `crowd_monitoring`

#### **1. Tabel `crowd_history`**
```sql
- id (INT, AUTO_INCREMENT, PRIMARY KEY)
- location (VARCHAR(100)) - Nama lokasi (DPR, Patung Kuda)
- count (INT) - Jumlah orang terdeteksi
- timestamp (TIMESTAMP) - Waktu deteksi
- created_at (TIMESTAMP) - Waktu record dibuat
```

#### **2. Tabel `locations`**
```sql
- id (INT, AUTO_INCREMENT, PRIMARY KEY)
- name (VARCHAR(100), UNIQUE) - Nama lokasi
- cctv_url (TEXT) - URL CCTV feed
- description (TEXT) - Deskripsi lokasi
- is_active (BOOLEAN) - Status aktif
- created_at, updated_at (TIMESTAMP)
```

#### **3. Tabel `roi_coordinates`**
```sql
- id (INT, AUTO_INCREMENT, PRIMARY KEY)
- location_id (INT, FOREIGN KEY) - Referensi ke locations
- point_order (INT) - Urutan titik koordinat
- x_coordinate, y_coordinate (INT) - Koordinat X,Y
- created_at (TIMESTAMP)
```

#### **4. Tabel `density_maps`**
```sql
- id (INT, AUTO_INCREMENT, PRIMARY KEY)
- location_id (INT, FOREIGN KEY) - Referensi ke locations
- density_map_base64 (LONGTEXT) - Density map dalam format base64
- timestamp (TIMESTAMP) - Waktu density map dibuat
- created_at (TIMESTAMP)
```

## 📈 Views yang Dibuat

### **1. `crowd_history_view`**
View untuk melihat data crowd dengan informasi lokasi lengkap.

### **2. `crowd_stats_view`**
View untuk statistik crowd per lokasi per hari (total, rata-rata, min, max).

## 📝 Sample Data

### **Lokasi CCTV:**
- **DPR**: CCTV DPR - Bendungan Hilir
- **Patung Kuda**: CCTV Patung Kuda - JPO Merdeka Barat

### **ROI Coordinates:**
- **Patung Kuda**: 4 titik koordinat untuk area monitoring
- **DPR**: 4 titik koordinat untuk area monitoring

### **Sample Crowd Data:**
- 10 records sample data crowd history
- Data dengan timestamp berbeda untuk testing

## 🔧 Konfigurasi Aplikasi

### **Database Connection di `app.py`:**
```python
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Raihan26",
            database="crowd_monitoring"
        )
        return connection
    except Error as e:
        print(f"[DB ERROR] {e}")
        return None
```

## 🌐 Endpoints Database

### **1. Health Check**
```
GET /health
```
Cek koneksi database dan versi MySQL.

### **2. Database Info**
```
GET /db-info
```
Informasi database dan jumlah records per tabel.

### **3. Crowd History**
```
GET /crowd/history
```
Ambil data crowd history dari database (100 records terakhir).

### **4. Root Endpoint**
```
GET /
```
Status aplikasi dengan informasi koneksi database.

## 📊 Indexes untuk Performa

Database sudah dioptimasi dengan indexes:
- `idx_location` pada crowd_history
- `idx_timestamp` pada crowd_history
- `idx_location_timestamp` pada crowd_history
- `idx_location_order` pada roi_coordinates
- `idx_location_timestamp` pada density_maps

## 🔍 Query Examples

### **1. Cek jumlah records per tabel:**
```sql
SELECT 
    'crowd_history' as table_name, COUNT(*) as count 
FROM crowd_history
UNION ALL
SELECT 'locations', COUNT(*) FROM locations
UNION ALL
SELECT 'roi_coordinates', COUNT(*) FROM roi_coordinates
UNION ALL
SELECT 'density_maps', COUNT(*) FROM density_maps;
```

### **2. Statistik crowd per lokasi hari ini:**
```sql
SELECT 
    location,
    COUNT(*) as total_records,
    AVG(count) as avg_count,
    MIN(count) as min_count,
    MAX(count) as max_count
FROM crowd_history
WHERE DATE(timestamp) = CURDATE()
GROUP BY location;
```

### **3. Data crowd terbaru:**
```sql
SELECT location, count, timestamp
FROM crowd_history
ORDER BY timestamp DESC
LIMIT 10;
```

## ✅ Verifikasi Setup

Setelah menjalankan script, Anda akan melihat output:
- ✅ Database crowd_monitoring berhasil dibuat!
- ✅ 2 lokasi CCTV tersedia
- ✅ 10 sample crowd records
- ✅ 8 ROI coordinates (4 per lokasi)
- ✅ Views dan indexes terbuat

## 🚨 Troubleshooting

### **Error: Access denied**
- Pastikan password MySQL benar: `Raihan26`
- Pastikan MySQL service berjalan

### **Error: Database doesn't exist**
- Jalankan script `setup_crowd_db.sql` di phpMyAdmin
- Script akan membuat database otomatis

### **Error: Table already exists**
- Script menggunakan `CREATE TABLE IF NOT EXISTS`
- Data lama tidak akan terhapus

---

**Database siap digunakan untuk Crowd Monitoring Service!** 🎯
