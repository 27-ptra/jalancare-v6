# JalanCare V6 - Supabase Ready

Versi ini siap untuk:

```text
Railway / Render + Supabase PostgreSQL + Supabase Storage opsional + best.pt
```

## Fitur
- Landing page formal dan responsive
- Buat laporan masyarakat
- Cek status laporan
- Login dan register admin
- Dashboard statistik
- Grafik laporan
- Peta laporan
- Update status
- Upload foto bukti setelah perbaikan
- PDF laporan
- Simulasi notifikasi WhatsApp/email
- SQLite otomatis untuk lokal
- Supabase PostgreSQL untuk online
- Supabase Storage opsional untuk gambar

## Cara Jalan Lokal

1. Extract ZIP.
2. Taruh `best.pt` sejajar dengan `app.py`.
3. Jalankan:

```bash
pip install -r requirements.txt
python app.py
```

Jika `DATABASE_URL` kosong, aplikasi otomatis menggunakan SQLite lokal:

```text
database.db
```

## Setup Supabase

Baca file:

```text
README_SUPABASE.md
```

## Environment Variables

Contoh tersedia di:

```text
.env.example
```

Minimal untuk deploy:

```text
SECRET_KEY=isi_random_secret_key
DATABASE_URL=postgresql://...
MODEL_PATH=best.pt
```

Opsional Supabase Storage:

```text
USE_SUPABASE_STORAGE=true
SUPABASE_URL=https://project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=isi_service_role_key
SUPABASE_STORAGE_BUCKET=jalancare
```

## Admin Default

Jika belum ada admin di database, sistem otomatis membuat admin default:

```text
Username: admin
Password: admin123
```

Bisa diganti melalui environment variable:

```text
ADMIN_DEFAULT_USERNAME
ADMIN_DEFAULT_PASSWORD
ADMIN_DEFAULT_EMAIL
```

## File Deployment

Sudah tersedia:

```text
Procfile
runtime.txt
requirements.txt
```

Procfile:

```text
web: gunicorn app:app
```

## Catatan Penting

- Untuk lokal, SQLite sudah cukup.
- Untuk deploy online, gunakan Supabase PostgreSQL.
- Untuk gambar tidak hilang saat redeploy, aktifkan Supabase Storage.
- Jangan upload `.env` atau service role key ke GitHub.
