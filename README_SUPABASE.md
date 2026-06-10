# Setup Supabase untuk JalanCare V6

Dokumen ini menjelaskan cara memakai Supabase PostgreSQL dan opsional Supabase Storage.

## 1. Buat Project Supabase

1. Buka Supabase.
2. Buat project baru.
3. Simpan password database yang kamu buat.
4. Tunggu project selesai dibuat.

## 2. Ambil DATABASE_URL

Di Supabase dashboard:

```text
Project Settings
Database
Connection string
```

Gunakan connection string PostgreSQL. Untuk deploy di Railway/Render, biasanya lebih aman memakai connection string pooler.

Contoh bentuk umum:

```text
postgresql://postgres.xxxxxx:password@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
```

Masukkan ke environment variable:

```text
DATABASE_URL=postgresql://...
```

Catatan:
- Jangan tulis password database ke GitHub.
- Simpan di Environment Variables Railway/Render.
- Jika password mengandung karakter khusus seperti `@`, `#`, atau `/`, encode password terlebih dahulu.

## 3. Jalankan Lokal dengan SQLite

Kalau `DATABASE_URL` kosong, aplikasi otomatis pakai SQLite lokal:

```text
database.db
```

Jalankan:

```bash
pip install -r requirements.txt
python app.py
```

## 4. Jalankan Lokal dengan Supabase PostgreSQL

Buat file `.env` dari `.env.example`, lalu isi:

```text
DATABASE_URL=postgresql://...
SECRET_KEY=isi_secret_key
```

Lalu jalankan:

```bash
python app.py
```

## 5. Deploy Railway

1. Upload project ke GitHub.
2. Buka Railway.
3. New Project.
4. Deploy from GitHub Repository.
5. Masuk tab Variables.
6. Tambahkan:

```text
SECRET_KEY=isi_random_secret_key
DATABASE_URL=postgresql://...
MODEL_PATH=best.pt
ADMIN_DEFAULT_USERNAME=admin
ADMIN_DEFAULT_PASSWORD=admin123
```

Start command otomatis memakai `Procfile`:

```text
web: gunicorn app:app
```

## 6. Deploy Render

1. Upload project ke GitHub.
2. Buat Web Service baru.
3. Build Command:

```bash
pip install -r requirements.txt
```

4. Start Command:

```bash
gunicorn app:app
```

5. Tambahkan Environment Variables:

```text
SECRET_KEY=isi_random_secret_key
DATABASE_URL=postgresql://...
MODEL_PATH=best.pt
```

## 7. Setup Supabase Storage Opsional

Supabase Storage dipakai agar gambar tidak hilang saat redeploy.

### Buat bucket

Di Supabase:

```text
Storage
New bucket
```

Nama bucket:

```text
jalancare
```

Untuk demo, bucket bisa dibuat public agar gambar mudah ditampilkan.

### Environment Variables Storage

Tambahkan:

```text
USE_SUPABASE_STORAGE=true
SUPABASE_URL=https://project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=service_role_key
SUPABASE_STORAGE_BUCKET=jalancare
```

Catatan keamanan:
- `SUPABASE_SERVICE_ROLE_KEY` jangan pernah diupload ke GitHub.
- Masukkan hanya ke Environment Variables Railway/Render.
- Jangan tampilkan service role key di frontend.

## 8. Tentang best.pt

Untuk demo cepat, letakkan `best.pt` di folder project sejajar dengan `app.py`.

Struktur:

```text
jalancare_v6_supabase_ready/
├── app.py
├── best.pt
├── requirements.txt
├── Procfile
└── runtime.txt
```

Kalau file `best.pt` terlalu besar untuk GitHub, simpan di cloud storage lalu download manual di server atau gunakan storage khusus model.

## 9. Catatan Penting

- PostgreSQL menyimpan data laporan, admin, dan notifikasi.
- Supabase Storage menyimpan file gambar.
- SQLite tetap tersedia untuk lokal.
- Folder upload lokal tetap tersedia sebagai fallback.
