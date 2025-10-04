# Banjir Service

Microservice untuk monitoring data banjir Jakarta menggunakan web scraping dari dashboard Jakarta Satu.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
python3 -m pip install fastapi uvicorn selenium
```

### 2. Run Application
```bash
# Menggunakan script
./run.sh

# Atau manual
python3 -m uvicorn Databanjir:app --host 0.0.0.0 --port 8001 --reload
```

## 📋 Features

- **Data Pintu Air**: Monitoring status pintu air Jakarta
- **RT Terdampak**: Data RT yang terdampak banjir dengan tinggi genangan
- **Web Scraping**: Menggunakan Selenium untuk mengambil data real-time
- **REST API**: Endpoint untuk akses data banjir

## 🌐 API Endpoints

### Base URL: `http://localhost:8001`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Status aplikasi |
| `/test` | GET | Test endpoint |
| `/pintu-air` | GET | Data status pintu air |
| `/rt-terdampak` | GET | Data RT terdampak banjir |
| `/docs` | GET | API Documentation (Swagger UI) |

### Contoh Response

#### GET `/pintu-air`
```json
{
  "status": "success",
  "data": [
    "Pintu Air Karet",
    "Status: Normal",
    "Tinggi Air: 2.5m"
  ]
}
```

#### GET `/rt-terdampak`
```json
{
  "status": "success",
  "data": [
    {
      "RT": "001",
      "RW": "005",
      "Kelurahan": "Menteng",
      "Tinggi Genangan (cm)": 15.5
    }
  ]
}
```

#### GET `/test`
```json
{
  "message": "Test endpoint berhasil!",
  "available_endpoints": ["/pintu-air", "/rt-terdampak"],
  "status": "ready"
}
```

## 🔧 Configuration

### Chrome Driver
Aplikasi menggunakan Chrome driver dari Homebrew:
```python
chrome_driver_path = "/opt/homebrew/bin/chromedriver"
```

### Data Source
- **URL**: https://jakartasatu.jakarta.go.id/portal/apps/dashboards/c2b19d6243dd4a2f80fa1e55481fdb11
- **Method**: Web scraping dengan Selenium
- **Update Interval**: Real-time (setiap request)

## 🛠️ Dependencies

- **FastAPI**: Web framework
- **Selenium**: Web scraping
- **Chrome Driver**: Browser automation
- **Uvicorn**: ASGI server

## 📁 Project Structure

```
banjir_service/
├── Databanjir.py        # Main application
├── run.sh              # Run script
├── README.md           # Documentation
└── requirements.txt    # Python dependencies
```

## 🔍 Testing

1. **Start server**: `./run.sh`
2. **Test endpoints**:
   - http://localhost:8001/ (status)
   - http://localhost:8001/test (test data)
   - http://localhost:8001/docs (API docs)
   - http://localhost:8001/pintu-air (data pintu air)
   - http://localhost:8001/rt-terdampak (data RT terdampak)

## ⚠️ Notes

- Aplikasi membutuhkan Chrome browser dan Chrome driver
- Web scraping mungkin memerlukan waktu loading (6 detik)
- Data bergantung pada ketersediaan dashboard Jakarta Satu
- Chrome driver path disesuaikan untuk macOS

## 🚧 TODO

- [ ] Add caching untuk mengurangi request
- [ ] Add error handling yang lebih baik
- [ ] Add logging
- [ ] Add configuration file
- [ ] Add database storage
- [ ] Add scheduled updates

## 🔧 Troubleshooting

### Chrome Driver Error
```bash
# Install Chrome driver
brew install chromedriver

# Check if available
which chromedriver
```

### Port Already in Use
```bash
# Kill process on port 8001
lsof -ti:8001 | xargs kill -9
```

### Selenium Error
- Pastikan Chrome browser terinstall
- Pastikan Chrome driver versi kompatibel
- Cek koneksi internet untuk akses dashboard
