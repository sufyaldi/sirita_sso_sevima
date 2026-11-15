# SIRITA SSO Sevima Platform (Odoo 20)

Addon resmi integrasi Single Sign-On (SSO) dan *Just-In-Time (JIT) User Provisioning* terhubung dengan API Sevima Platform (SIAKAD Cloud).

---

## 🌟 Fitur Utama

1. **Delegated Passthrough SSO:**
   - Dosen, Tenaga Kependidikan (Tendik), dan Mahasiswa dapat masuk ke Odoo langsung menggunakan akun SIAKAD Cloud Sevima.
   - Mendukung login menggunakan **Email resmi** maupun **Nomor Induk Pegawai (NIP/NIDN)** atau **NIM**.
   - Menggunakan endpoint resmi: `POST /siakadcloud/v1/user/login`.

2. **Just-In-Time (JIT) Auto-Provisioning:**
   - Akun pengguna Odoo (`res.users`) otomatis dibuat saat pertama kali login berhasil.
   - Otomatis menghubungkan akun dengan data master kepegawaian (`hr.employee`) berdasarkan NIP/Barcode atau email.
   - Menetapkan hak akses secara cerdas:
     - Dosen (`DSN`) & Tendik (`TDK`/`PEG`) -> **Internal User** (`base.group_user`).
     - Mahasiswa (`MHS`) -> **Portal User** (`base.group_portal`).

3. **Sinkronisasi Profil & Penegakan Status Akun:**
   - Menyimpan nama lengkap, gelar akademik, kode peran, ID Satker, dan nama program studi / fakultas.
   - Memvalidasi atribut `status_aktif`: akun dengan nilai non-aktif (`"0"`) otomatis ditolak login.

4. **Dual-Mode Authentication & Local Fail-Safe:**
   - Akun administrator internal Odoo tetap dapat login menggunakan password lokal Odoo jika jaringan atau API Sevima sedang offline.

5. **Audit Trail & Monitoring Keamanan (`sevima.sso.log`):**
   - Mencatat setiap percobaan login SSO (waktu, email/NIP, IP klien, latency ms, status sukses/gagal, dan peran).
   - Tampilan visual monitoring di menu Administrasi.

---

## 📂 Struktur Direktori

```
sirita_sso_sevima/
├── __init__.py
├── __manifest__.py
├── README.md
├── controllers/
│   ├── __init__.py
│   └── main.py
├── data/
│   └── ir_config_parameter_data.xml
├── models/
│   ├── __init__.py
│   ├── hr_employee.py
│   ├── res_config_settings.py
│   ├── res_users.py
│   ├── sevima_sso_log.py
│   └── sevima_sso_service.py
├── security/
│   ├── ir.access.csv
│   └── security.xml
├── static/
│   ├── description/
│   │   └── icon.png
│   └── src/
│       └── img/
│           └── logo_iain.png
└── views/
    ├── login_templates.xml
    ├── menus.xml
    ├── res_config_settings_views.xml
    ├── res_users_views.xml
    └── sevima_sso_log_views.xml
```

---

## 🚀 Panduan Instalasi & Aktivasi

1. **Perbarui Daftar Modul di Odoo 20:**
   - Aktifkan Developer Mode di Odoo.
   - Masuk ke menu **Apps** -> Klik **Update Apps List**.
   - Cari modul **SIRITA SSO Sevima** (`sirita_sso_sevima`).
   - Klik tombol **Install** (atau **Upgrade**).

2. **Pengaturan Kredensial:**
   - Buka menu **Settings** -> Pilih tab **SSO Sevima**.
   - Masukkan **App Key** (`X-App-Key`) dan **Secret Key** (`X-Secret-Key`).
   - Masukkan email dan password akun uji coba pada bagian *Uji Koneksi & Autentikasi Langsung*, lalu klik **⚡ Uji Login Akun Sevima**.
   - Simpan pengaturan.

---

## 📄 Dokumen Arsitektur Lengkap

Silakan baca dokumen arsitektur komprehensif di:  
[`docs/RENCANA_IMPLEMENTASI_SSO_SEVIMA.md`](file:///home/iain/app-my/addons/sirita_sso_sevima/docs/RENCANA_IMPLEMENTASI_SSO_SEVIMA.md)
