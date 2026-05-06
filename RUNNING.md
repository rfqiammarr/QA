# Running QA Automation Project

Dokumentasi lengkap untuk menjalankan QA Automation Script.

## Prasyarat

- Python 3.8 atau lebih tinggi
- pip (Python Package Manager)

## Instalasi & Setup

### 1. Aktivasi Virtual Environment

Virtual environment sudah dibuat di folder `venv/`. Aktifkan dengan perintah:

**Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
venv\Scripts\activate.bat
```

**Linux/macOS:**
```bash
source venv/bin/activate
```

Setelah diaktifkan, terminal akan menampilkan `(venv)` di awal baris.

### 2. Konfigurasi Lingkungan

Buat file `.env` di root directory project dengan konfigurasi berikut:

```
BASE_URL=http://localhost:5132
USERNAME=your_username
PASSWORD=your_password
TOTAL_TRANSAKSI=5
MAX_RETRY_PER_ITEM=2
```

**Penjelasan konfigurasi:**
- `BASE_URL`: URL aplikasi web yang akan ditest
- `USERNAME`: Username untuk login
- `PASSWORD`: Password untuk login
- `TOTAL_TRANSAKSI`: Jumlah transaksi default yang akan dibuat
- `MAX_RETRY_PER_ITEM`: Maksimal percobaan ulang per item jika terjadi error

## Menjalankan Script

Pastikan virtual environment sudah diaktifkan, kemudian jalankan:

### Dengan default (5 transaksi):
```powershell
python src/main.py
```

### Dengan jumlah transaksi custom:
```powershell
python src/main.py 10
```

Contoh di atas akan membuat 10 transaksi otomatis.

## Menonaktifkan Virtual Environment

Setelah selesai, deaktifkan virtual environment dengan:

```powershell
deactivate
```

## Dependencies yang Terinstal

- **Selenium 4.43.0**: Web automation framework untuk testing
- **Faker 40.15.0**: Library untuk generate data palsu (dummy data)

Semua dependencies sudah terinstal di virtual environment dan siap digunakan.

## Troubleshooting

### Error: "python is not recognized"
Pastikan Python sudah terinstall dan ditambahkan ke PATH sistem.

### Error: Virtual environment tidak teraktifkan
Cek bahwa Anda sudah menjalankan command aktivasi yang sesuai dengan OS Anda.

### Error: Module tidak ditemukan
Pastikan virtual environment sudah diaktifkan sebelum menjalankan script.

## Struktur Project

```
QA/
├── venv/                  # Virtual environment
├── src/
│   ├── __init__.py
│   └── main.py           # Main automation script
├── .env                  # Konfigurasi (create manually)
├── requirements.txt      # Daftar dependencies
├── README.md            # Penjelasan project
└── RUNNING.md           # File ini
```

## Contact & Support

Untuk pertanyaan atau masalah, hubungi tim QA.
