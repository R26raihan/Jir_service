# Crowd Monitoring Service

Microservice untuk monitoring kepadatan kerumunan menggunakan AI model CSRNet dan CCTV feeds.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
python3 -m pip install -r requirements.txt
```

### 2. Run Application
```bash
# Menggunakan script
./run.sh

# Atau manual
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## 📋 Features

- **Real-time Crowd Counting**: Menggunakan model CSRNet untuk menghitung jumlah orang
- **CCTV Integration**: Mengambil feed dari CCTV publik Jakarta
- **ROI Detection**: Area of Interest untuk fokus monitoring
- **Density Maps**: Visualisasi kepadatan kerumunan
- **REST API**: Endpoint untuk akses data real-time

## 🌐 API Endpoints

### Base URL: `http://localhost:8000`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Status aplikasi |
| `/test` | GET | Test endpoint dengan data crowd |
| `/crowd` | GET | Data crowd real-time semua lokasi |
| `/crowd/history` | GET | History data crowd (database disabled) |
| `/crowd/densitymap` | GET | Density map base64 untuk lokasi tertentu |
| `/docs` | GET | API Documentation (Swagger UI) |

### Contoh Response

#### GET `/crowd`
```json
{
  "DPR": {
    "count": 45,
    "timestamp": "2024-01-15 14:30:25"
  },
  "Patung Kuda": {
    "count": 23,
    "timestamp": "2024-01-15 14:30:20"
  }
}
```

#### GET `/test`
```json
{
  "message": "Test endpoint berhasil!",
  "crowd_data": {},
  "available_locations": ["DPR", "Patung Kuda"]
}
```

## 📍 Lokasi yang Dimonitor

1. **DPR** - Bendungan Hilir
2. **Patung Kuda** - JPO Merdeka Barat

## 🔧 Configuration

### CCTV URLs
```python
cctv_urls = {
    "DPR": "https://cctv.balitower.co.id/Bendungan-Hilir-003-700014_1/embed.html",
    "Patung Kuda": "https://cctv.balitower.co.id/JPO-Merdeka-Barat-507357_9/embed.html",
}
```

### ROI Polygons
Setiap lokasi memiliki area of interest (ROI) yang didefinisikan dengan koordinat polygon.

## 🗄️ Database

**Status**: Sementara dinonaktifkan untuk testing

Ketika diaktifkan, data akan disimpan ke MySQL database dengan struktur:
- `crowd_history`: location, count, timestamp

## 🛠️ Dependencies

- **FastAPI**: Web framework
- **PyTorch**: Deep learning framework
- **OpenCV**: Computer vision
- **Selenium**: Web scraping untuk CCTV
- **Pillow**: Image processing
- **NumPy**: Numerical computing

## 📁 Project Structure

```
crowd_monitoring_service/
├── app.py                 # Main application
├── requirements.txt       # Python dependencies
├── run.sh                # Run script
├── README.md             # Documentation
├── model/
│   ├── model.py          # CSRNet model definition
│   └── weights.pth       # Pre-trained weights
└── chromedriver-win64/   # Chrome driver
```

## 🔍 Testing

1. **Start server**: `./run.sh`
2. **Test endpoints**:
   - http://localhost:8000/ (status)
   - http://localhost:8000/test (test data)
   - http://localhost:8000/docs (API docs)

## ⚠️ Notes

- Background monitoring sementara dinonaktifkan untuk testing
- Database connection dinonaktifkan
- Chrome driver path perlu disesuaikan dengan sistem
- Model weights harus tersedia di `model/weights.pth`

## 🚧 TODO

- [ ] Aktifkan background monitoring
- [ ] Setup database connection
- [ ] Optimize Chrome driver path
- [ ] Add error handling
- [ ] Add logging
- [ ] Add configuration file
