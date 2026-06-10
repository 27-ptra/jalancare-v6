# Deployment Checklist JalanCare V6

## Sebelum Upload ke GitHub

Pastikan file ini ADA:
- app.py
- requirements.txt
- Procfile
- runtime.txt
- README.md
- README_SUPABASE.md
- .env.example
- templates/
- static/

Pastikan file ini JANGAN masuk GitHub:
- .env
- database.db
- secret key
- Supabase service role key

## best.pt

Untuk demo cepat, `best.pt` boleh ditaruh sejajar dengan `app.py`.

Jika GitHub menolak karena file terlalu besar:
1. Jangan upload `best.pt` ke GitHub.
2. Upload model ke cloud storage.
3. Download manual ke server atau gunakan storage khusus model.

## Environment Variables Minimal

```text
SECRET_KEY=isi_random_secret_key
DATABASE_URL=postgresql://...
MODEL_PATH=best.pt
ADMIN_DEFAULT_USERNAME=admin
ADMIN_DEFAULT_PASSWORD=admin123
```

## Jika Pakai Supabase Storage

```text
USE_SUPABASE_STORAGE=true
SUPABASE_URL=https://project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=isi_service_role_key
SUPABASE_STORAGE_BUCKET=jalancare
```

## Test Lokal

```bash
pip install -r requirements.txt
python app.py
```

## Test Production Command

Linux/server:

```bash
gunicorn app:app
```

## Cek Setelah Deploy

- Buka landing page
- Register/login admin
- Upload laporan
- Cek status tiket
- Buka dashboard
- Cek peta
- Update status
- Upload bukti perbaikan
- Download PDF
- Cek log notifikasi
