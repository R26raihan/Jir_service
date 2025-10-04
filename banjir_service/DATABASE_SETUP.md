# 🗄️ Database Setup - Banjir Service

## 📋 Overview

Database untuk Banjir Service sudah dibuat dengan struktur yang lengkap untuk menyimpan:
- Data pintu air (status, ketinggian air, kapasitas)
- Data RT terdampak banjir (RT/RW, kelurahan, tinggi genangan)
- Lokasi pintu air (koordinat, alamat)
- Statistik banjir (per hari, per kelurahan)

## 🚀 Cara Setup Database

### 1. **Import ke phpMyAdmin**

1. Buka phpMyAdmin di http://localhost:8080
2. Login dengan username: `root`, password: `Raihan26`
3. Klik tab **"SQL"**
4. Copy dan paste isi file `setup_banjir_db.sql`
5. Klik **"Go"** untuk menjalankan script

### 2. **Atau menggunakan command line**

```bash
mysql -u root -p < setup_banjir_db.sql
```

## 📊 Struktur Database

### **Database**: `banjir_monitoring`

#### **1. Tabel `pintu_air`**
```sql
- id (INT, AUTO_INCREMENT, PRIMARY KEY)
- nama_pintu_air (VARCHAR(255)) - Nama pintu air
- status (VARCHAR(100)) - Status (Normal, Waspada, Siaga)
- ketinggian_air (DECIMAL(10,2)) - Ketinggian air dalam cm
- kapasitas (DECIMAL(10,2)) - Kapasitas maksimal
- unit (VARCHAR(50)) - Unit pengukuran (cm)
- timestamp (TIMESTAMP) - Waktu update data
```

#### **2. Tabel `rt_terdampak`**
```sql
- id (INT, AUTO_INCREMENT, PRIMARY KEY)
- rt (VARCHAR(10)) - Nomor RT
- rw (VARCHAR(10)) - Nomor RW
- kelurahan (VARCHAR(255)) - Nama kelurahan
- tinggi_genangan (DECIMAL(10,2)) - Tinggi genangan dalam cm
- unit_tinggi (VARCHAR(10)) - Unit pengukuran (cm)
- status_banjir (ENUM) - Status: ringan/sedang/berat
- timestamp (TIMESTAMP) - Waktu update data
```

#### **3. Tabel `lokasi_pintu_air`**
```sql
- id (INT, AUTO_INCREMENT, PRIMARY KEY)
- nama (VARCHAR(255), UNIQUE) - Nama pintu air
- alamat (TEXT) - Alamat lengkap
- koordinat_lat, koordinat_lng (DECIMAL) - Koordinat GPS
- deskripsi (TEXT) - Deskripsi lokasi
- is_active (BOOLEAN) - Status aktif
```

#### **4. Tabel `statistik_banjir`**
```sql
- id (INT, AUTO_INCREMENT, PRIMARY KEY)
- tanggal (DATE) - Tanggal statistik
- total_rt_terdampak (INT) - Total RT terdampak
- total_kelurahan_terdampak (INT) - Total kelurahan terdampak
- rata_rata_tinggi_genangan (DECIMAL) - Rata-rata tinggi genangan
- max_tinggi_genangan (DECIMAL) - Tinggi genangan maksimal
- status_terparah (ENUM) - Status terparah hari itu
```

## 📈 Views yang Dibuat

### **1. `pintu_air_view`**
View untuk melihat data pintu air dengan informasi lokasi lengkap.

### **2. `rt_terdampak_stats_view`**
View untuk statistik RT terdampak per kelurahan per hari.

### **3. `dashboard_banjir_view`**
View untuk dashboard banjir dengan statistik lengkap.

## 📝 Sample Data

### **Pintu Air (5 records):**
- Pintu Air Manggarai (Normal, 150.50 cm)
- Pintu Air Karet (Waspada, 180.75 cm)
- Pintu Air Depok (Siaga, 195.25 cm)
- Pintu Air Katulampa (Normal, 145.30 cm)
- Pintu Air Ciliwung (Waspada, 175.80 cm)

### **RT Terdampak (10 records):**
- RT 001/001 Manggarai (25.5 cm, ringan)
- RT 002/001 Manggarai (45.2 cm, sedang)
- RT 004/002 Kebayoran Baru (65.3 cm, berat)
- RT 010/005 Tanjung Priok (70.8 cm, berat)

### **Lokasi Pintu Air (5 records):**
- Koordinat dan alamat lengkap untuk setiap pintu air

### **Statistik Banjir (5 records):**
- Data statistik 5 hari terakhir dengan trend banjir

## 🔧 Konfigurasi Aplikasi

### **Database Connection di `Databanjir.py`:**
```python
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Raihan26",
            database="banjir_monitoring"
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

### **3. Data Pintu Air dari Database**
```
GET /pintu-air/db
```
Ambil data pintu air dari database (50 records terakhir).

### **4. Data RT Terdampak dari Database**
```
GET /rt-terdampak/db
```
Ambil data RT terdampak dari database (100 records terakhir).

### **5. Statistik Banjir**
```
GET /statistik
```
Ambil statistik banjir dari database (30 hari terakhir).

### **6. Root Endpoint**
```
GET /
```
Status aplikasi dengan informasi koneksi database.

## 📊 Indexes untuk Performa

Database sudah dioptimasi dengan indexes:
- `idx_nama_pintu_air` pada pintu_air
- `idx_timestamp` pada pintu_air
- `idx_status` pada pintu_air
- `idx_rt_rw` pada rt_terdampak
- `idx_kelurahan` pada rt_terdampak
- `idx_timestamp` pada rt_terdampak
- `idx_status_banjir` pada rt_terdampak
- `idx_tanggal` pada statistik_banjir

## 🔍 Query Examples

### **1. Cek jumlah records per tabel:**
```sql
SELECT 
    'pintu_air' as table_name, COUNT(*) as count 
FROM pintu_air
UNION ALL
SELECT 'rt_terdampak', COUNT(*) FROM rt_terdampak
UNION ALL
SELECT 'lokasi_pintu_air', COUNT(*) FROM lokasi_pintu_air
UNION ALL
SELECT 'statistik_banjir', COUNT(*) FROM statistik_banjir;
```

### **2. Statistik banjir hari ini:**
```sql
SELECT 
    kelurahan,
    COUNT(*) as total_rt_terdampak,
    AVG(tinggi_genangan) as rata_rata_tinggi_genangan,
    MAX(tinggi_genangan) as max_tinggi_genangan
FROM rt_terdampak
WHERE DATE(timestamp) = CURDATE()
GROUP BY kelurahan;
```

### **3. Status pintu air terbaru:**
```sql
SELECT nama_pintu_air, status, ketinggian_air, unit, timestamp
FROM pintu_air
ORDER BY timestamp DESC
LIMIT 10;
```

### **4. RT terdampak terparah:**
```sql
SELECT rt, rw, kelurahan, tinggi_genangan, status_banjir
FROM rt_terdampak
WHERE status_banjir = 'berat'
ORDER BY tinggi_genangan DESC
LIMIT 10;
```

## ✅ Verifikasi Setup

Setelah menjalankan script, Anda akan melihat output:
- ✅ Database banjir_monitoring berhasil dibuat!
- ✅ 5 pintu air tersedia
- ✅ 10 RT terdampak records
- ✅ 5 lokasi pintu air
- ✅ 5 statistik banjir records
- ✅ Views dan indexes terbuat

## 🚨 Troubleshooting

### **Error: Access denied**
- Pastikan password MySQL benar: `Raihan26`
- Pastikan MySQL service berjalan

### **Error: Database doesn't exist**
- Jalankan script `setup_banjir_db.sql` di phpMyAdmin
- Script akan membuat database otomatis

### **Error: Table already exists**
- Script menggunakan `CREATE TABLE IF NOT EXISTS`
- Data lama tidak akan terhapus

## 🎯 Fitur Database

### **1. Auto-save Data**
- Data pintu air otomatis tersimpan saat scraping
- Data RT terdampak otomatis tersimpan saat scraping
- Timestamp tracking untuk setiap update

### **2. Status Banjir Otomatis**
- Status banjir otomatis ditentukan berdasarkan tinggi genangan:
  - < 30 cm: ringan
  - 30-60 cm: sedang
  - > 60 cm: berat

### **3. Statistik Real-time**
- Views untuk dashboard real-time
- Statistik per kelurahan, per hari
- Trend banjir otomatis

---

**Database siap digunakan untuk Banjir Service!** 🎯
