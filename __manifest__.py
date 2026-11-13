# -*- coding: utf-8 -*-
{
    'name': 'SIRITA SSO Sevima',
    'version': '20.0.1.0.0',
    'category': 'Technical/Authentication',
    'summary': 'Single Sign-On (SSO) & JIT Provisioning Terintegrasi API Sevima Platform / SIAKAD Cloud IAIN Parepare',
    'description': """
SIRITA SSO Sevima Platform (Odoo 20)
====================================
Addon autentikasi Single Sign-On (SSO) berbasis API Sevima Platform (SIAKAD Cloud) untuk IAIN Parepare.

Fitur Utama:
------------
1. Delegated Authentication:
   - Pengguna (Dosen, Tendik, Mahasiswa) dapat login ke Odoo menggunakan email/NIP dan password akun Sevima SIAKAD Cloud.
   - Verifikasi langsung via endpoint POST /siakadcloud/v1/user/login Sevima Platform.
2. Just-In-Time (JIT) Provisioning:
   - Otomatis membuat akun user Odoo baru saat pertama kali login berhasil jika opsi diaktifkan.
   - Otomatis menghubungkan ke data master Pegawai (hr.employee) berdasarkan NIP/barcode atau email.
3. Sinkronisasi Data Profil & Role:
   - Menyimpan atribut Sevima: Nama, NIP, ID Pegawai, Kode Role (DSN, TDK, MHS), dan Satker/Prodi.
   - Validasi status aktif akun dari Sevima (status_aktif = 1).
4. Dual-Mode Authentication & Fail-Safe:
   - Administrator lokal Odoo tetap dapat login menggunakan password lokal jika server API Sevima offline.
5. Audit Trail & Log Autentikasi:
   - Mencatat setiap percobaan login SSO (waktu, login/email, IP address, latency ms, status, dan role).
    """,
    'author': 'UPT TIPD IAIN Parepare',
    'website': 'https://tipd.iainpare.ac.id',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'hr',
    ],
    'data': [
        'security/security.xml',
        'security/ir.access.csv',
        'data/ir_config_parameter_data.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/sevima_sso_log_views.xml',
        'views/login_templates.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
