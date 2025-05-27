# KTP Detection System

Sistem verifikasi dan ekstraksi data KTP Indonesia menggunakan AI dan Computer Vision.

## 🚀 Fitur Utama

- **Verifikasi KTP**: Deteksi apakah gambar adalah KTP Indonesia yang valid
- **Ekstraksi Data**: Ekstraksi otomatis semua field KTP menggunakan AI
- **Validasi Bisnis**: Validasi data dengan aturan bisnis Indonesia (NIK, format tanggal, dll)
- **Database Storage**: Penyimpanan data ke MariaDB dengan MCP integration
- **Web Interface**: Interface web yang user-friendly untuk upload dan hasil
- **REST API**: API endpoints untuk integrasi dengan sistem lain

## 🛠️ Teknologi Stack

- **Backend**: FastAPI (Python)
- **AI/ML**: Google Gemini Flash 2.5
- **Database**: MariaDB dengan MCP MySQL
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Image Processing**: PIL, OpenCV
- **Computer Vision**: Google Gemini Vision API

## 📋 Persyaratan

### Software Requirements
- Python 3.8+
- MariaDB 10.5+
- Node.js (untuk MCP server MySQL)

### API Keys
- Google AI API Key (untuk Gemini Flash 2.5)

## 🔧 Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd KTPDetection
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup Environment Variables
Salin `.env` file dan update konfigurasi:
```bash
cp .env.example .env
```

Edit `.env` file:
```env
# Gemini AI Configuration
GEMINI_API_KEY=your_actual_gemini_api_key_here

# MariaDB Configuration
DB_HOST=localhost
DB_PORT=3306
DB_NAME=ktp_detection
DB_USER=your_mysql_user
DB_PASSWORD=your_mysql_password

# Application Settings
UPLOAD_DIR=uploads/
MAX_FILE_SIZE=10485760
ALLOWED_EXTENSIONS=jpg,jpeg,png,webp,bmp
DEBUG=True
HOST=0.0.0.0
PORT=8000
```

### 4. Setup MariaDB Database
```sql
-- Create database
CREATE DATABASE ktp_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user (optional)
CREATE USER 'ktp_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON ktp_detection.* TO 'ktp_user'@'localhost';
FLUSH PRIVILEGES;
```

### 5. Setup MCP MySQL Server
Pastikan MCP MySQL server sudah dikonfigurasi dan berjalan. Lihat dokumentasi MCP untuk setup detail.

### 6. Initialize Database Tables
Jalankan endpoint untuk membuat tables:
```bash
# Setelah aplikasi berjalan
curl -X POST http://localhost:8000/api/init-database
```

## 🚀 Menjalankan Aplikasi

### Development Mode
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Aplikasi akan tersedia di: `http://localhost:8000`

## 📚 API Documentation

Setelah aplikasi berjalan, akses dokumentasi API di:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🔍 API Endpoints

### Core Endpoints

#### POST `/api/verify-ktp`
Upload dan verifikasi foto KTP
- **Input**: File gambar (JPG, PNG, WebP, BMP)
- **Output**: Data KTP yang diekstrak + status validasi

#### GET `/api/ktp/{nik}`
Ambil data KTP berdasarkan NIK
- **Input**: NIK (16 digit)
- **Output**: Data KTP jika ditemukan

#### POST `/api/search-ktp`
Pencarian data KTP
- **Input**: NIK atau Nama (partial search)
- **Output**: List data KTP dengan pagination

### Utility Endpoints

#### GET `/api/health`
Health check aplikasi dan services

#### GET `/api/stats`
Statistik processing KTP

#### POST `/api/test-gemini`
Test koneksi ke Gemini API

#### POST `/api/init-database`
Initialize database dan create tables

## 📝 Format Response

### Success Response (KTP Valid)
```json
{
  "is_valid_ktp": true,
  "confidence_score": 0.95,
  "extracted_data": {
    "nik": "3201234567890123",
    "nama": "JOHN DOE",
    "tempat_lahir": "JAKARTA",
    "tanggal_lahir": "01-01-1990",
    "jenis_kelamin": "LAKI-LAKI",
    "alamat": "JL. CONTOH NO. 123",
    "rt_rw": "001/002",
    "kelurahan": "KELURAHAN CONTOH",
    "kecamatan": "KECAMATAN CONTOH",
    "kabupaten_kota": "KOTA JAKARTA SELATAN",
    "provinsi": "DKI JAKARTA",
    "agama": "ISLAM",
    "status_perkawinan": "BELUM KAWIN",
    "pekerjaan": "SWASTA",
    "kewarganegaraan": "WNI",
    "berlaku_hingga": "SEUMUR HIDUP"
  },
  "validation_errors": [],
  "processing_notes": null,
  "database_id": 1
}
```

### Error Response (KTP Tidak Valid)
```json
{
  "is_valid_ktp": false,
  "confidence_score": 0.2,
  "extracted_data": null,
  "validation_errors": [
    "Bukan KTP Indonesia yang valid",
    "Logo Garuda tidak terdeteksi",
    "Format layout tidak sesuai"
  ],
  "processing_notes": "Gambar tidak memenuhi kriteria KTP Indonesia"
}
```

## 🔧 Konfigurasi

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google AI API Key | Required |
| `DB_HOST` | MariaDB Host | localhost |
| `DB_PORT` | MariaDB Port | 3306 |
| `DB_NAME` | Database Name | ktp_detection |
| `DB_USER` | Database User | Required |
| `DB_PASSWORD` | Database Password | Required |
| `UPLOAD_DIR` | Upload Directory | uploads/ |
| `MAX_FILE_SIZE` | Max File Size (bytes) | 10485760 (10MB) |
| `ALLOWED_EXTENSIONS` | Allowed File Extensions | jpg,jpeg,png,webp,bmp |
| `DEBUG` | Debug Mode | True |
| `HOST` | Server Host | 0.0.0.0 |
| `PORT` | Server Port | 8000 |

### File Size & Format Limits
- **Maximum File Size**: 10MB
- **Supported Formats**: JPG, JPEG, PNG, WebP, BMP
- **Recommended Resolution**: 800x500 pixels minimum

## 🧪 Testing

### Manual Testing
1. Akses `http://localhost:8000`
2. Upload foto KTP Indonesia
3. Periksa hasil verifikasi

### API Testing
```bash
# Health check
curl http://localhost:8000/api/health

# Upload KTP
curl -X POST \
  -F "file=@path/to/ktp.jpg" \
  http://localhost:8000/api/verify-ktp

# Search by NIK
curl http://localhost:8000/api/ktp/3201234567890123
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Gemini API Error
```
Error: GEMINI_API_KEY belum dikonfigurasi
```
**Solution**: Set valid Google AI API key di `.env` file

#### 2. Database Connection Error
```
Error: Can't connect to MySQL server
```
**Solution**: 
- Pastikan MariaDB berjalan
- Periksa kredensial database di `.env`
- Jalankan `mysql -u username -p` untuk test koneksi

#### 3. MCP MySQL Error
```
Error: MCP MySQL server not responding
```
**Solution**:
- Pastikan MCP MySQL server berjalan
- Periksa konfigurasi MCP di sistem

#### 4. File Upload Error
```
Error: File terlalu besar
```
**Solution**: 
- Compress gambar atau gunakan resolusi lebih rendah
- Check `MAX_FILE_SIZE` setting

### Logging
Aplikasi menggunakan Python logging. Check console output untuk detail error.

## 📊 Performance

### Typical Processing Times
- **Image Validation**: ~200ms
- **Gemini AI Analysis**: ~2-5 seconds
- **Data Validation**: ~100ms
- **Database Save**: ~50ms
- **Total**: ~3-6 seconds per image

### Scalability Considerations
- Gemini API rate limits
- Database connection pooling
- Image processing memory usage
- Concurrent request handling

## 🔒 Security

### Data Privacy
- Gambar KTP tidak disimpan permanen
- Data sensitif di-hash saat perlu
- Database menggunakan encryption in transit

### API Security
- Input validation untuk semua endpoints
- File type validation
- File size limits
- SQL injection prevention

### Recommendations
- Gunakan HTTPS di production
- Setup database firewall
- Regular security updates
- Monitor API usage

## 🤝 Contributing

1. Fork repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Team

- **Developer**: KTP Detection Team
- **AI Integration**: Google Gemini Flash 2.5
- **Database**: MariaDB + MCP MySQL

## 📞 Support

Untuk pertanyaan atau issue:
1. Check documentation di `/docs`
2. Review API health di `/health`
3. Submit issue di repository

---

**Built with ❤️ using FastAPI, Google AI, and MariaDB**
