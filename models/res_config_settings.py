# -*- coding: utf-8 -*-
import time
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sevima_sso_enabled = fields.Boolean(
        string='Aktifkan SSO Sevima Platform',
        config_parameter='sirita_sso_sevima.enabled',
        default=True,
        help='Aktifkan autentikasi pengguna menggunakan akun Sevima Platform (SIAKAD Cloud).'
    )
    sevima_sso_base_url = fields.Char(
        string='Base URL API Sevima',
        config_parameter='sirita_sso_sevima.base_url',
        default='https://api.sevimaplatform.com',
        help='Base URL API Sevima Platform (contoh: https://api.sevimaplatform.com)'
    )
    sevima_sso_app_key = fields.Char(
        string='App Key',
        config_parameter='sirita_sso_sevima.app_key',
        help='App Key resmi dari Sevima Platform (Header: X-App-Key)'
    )
    sevima_sso_secret_key = fields.Char(
        string='Secret Key',
        config_parameter='sirita_sso_sevima.secret_key',
        help='Secret Key resmi dari Sevima Platform (Header: X-Secret-Key)'
    )
    sevima_sso_auto_create_user = fields.Boolean(
        string='Just-In-Time (JIT) Auto-Provisioning User',
        config_parameter='sirita_sso_sevima.auto_create_user',
        default=True,
        help='Otomatis membuat user Odoo baru ketika user Sevima pertama kali login dengan kredensial valid.'
    )
    sevima_sso_default_user_type = fields.Selection([
        ('internal', 'Pengguna Internal (Dosen/Tendik)'),
        ('portal', 'Pengguna Portal (Mahasiswa)'),
    ], string='Tipe Akses User Baru Default',
        config_parameter='sirita_sso_sevima.default_user_type',
        default='internal',
        help='Tipe akses default untuk akun baru yang tidak teridentifikasi sebagai pegawai/dosen.'
    )
    sevima_sso_timeout = fields.Integer(
        string='Batas Waktu Request (detik)',
        config_parameter='sirita_sso_sevima.timeout',
        default=10,
        help='Batas waktu request HTTP POST ke server Sevima sebelum timeout.'
    )

    # Uji Koneksi Live
    sevima_sso_test_email = fields.Char(
        string='Email Akun Uji Coba',
        config_parameter='sirita_sso_sevima.test_email',
        help='Email akun Sevima untuk pengujian koneksi live'
    )
    sevima_sso_test_password = fields.Char(
        string='Password Akun Uji Coba',
        config_parameter='sirita_sso_sevima.test_password',
        help='Password akun Sevima untuk pengujian koneksi live'
    )

    def action_test_sevima_sso_connection(self):
        """Menguji koneksi dan verifikasi kredensial API Sevima secara langsung"""
        self.ensure_one()
        base_url = (self.sevima_sso_base_url or 'https://api.sevimaplatform.com').rstrip('/')
        app_key = (self.sevima_sso_app_key or '').strip()
        secret_key = (self.sevima_sso_secret_key or '').strip()
        test_email = (self.sevima_sso_test_email or '').strip()
        test_password = self.sevima_sso_test_password or ''

        # Fallback ke parameter tersimpan jika field form kosong
        ICP = self.env['ir.config_parameter'].sudo()
        if not app_key:
            app_key = (ICP.get_param('sirita_sso_sevima.app_key', '') or '').strip()
        if not secret_key:
            secret_key = (ICP.get_param('sirita_sso_sevima.secret_key', '') or '').strip()
        if not test_email:
            test_email = (ICP.get_param('sirita_sso_sevima.test_email', '') or '').strip()
        if not test_password:
            test_password = ICP.get_param('sirita_sso_sevima.test_password', '') or ''

        if not app_key or not secret_key:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Kredensial Belum Lengkap'),
                    'message': _('Harap isi App Key dan Secret Key sebelum menguji koneksi.'),
                    'sticky': True,
                    'type': 'warning',
                }
            }

        if not test_email or not test_password:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Data Akun Uji Kosong'),
                    'message': _('Harap masukkan Email dan Password akun Sevima untuk melakukan tes login.'),
                    'sticky': True,
                    'type': 'warning',
                }
            }

        login_url = f"{base_url}/siakadcloud/v1/user/login"
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-App-Key': app_key,
            'X-Secret-Key': secret_key,
        }
        payload = {
            'email': test_email,
            'password': test_password
        }

        start_time = time.time()
        try:
            res = requests.post(login_url, headers=headers, json=payload, timeout=self.sevima_sso_timeout or 10)
            latency = round((time.time() - start_time) * 1000, 2)

            if res.status_code == 200:
                data = res.json()
                user_id = data.get('id') or data.get('attributes', {}).get('user_id')
                nama = data.get('attributes', {}).get('nama', 'User')
                roles = data.get('attributes', {}).get('role', [])
                role_name = roles[0].get('nama_role') if roles else 'N/A'
                msg = _("Uji Login SSO Berhasil! HTTP 200 (Latency: %s ms). Pengguna: %s (%s, ID: %s)") % (
                    latency, nama, role_name, user_id
                )
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Koneksi SSO Sevima Berhasil'),
                        'message': msg,
                        'sticky': False,
                        'type': 'success',
                    }
                }
            elif res.status_code == 401:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Autentikasi Gagal (HTTP 401)'),
                        'message': _('Email atau Password salah, atau akun tidak memiliki hak akses API pada Sevima.'),
                        'sticky': True,
                        'type': 'danger',
                    }
                }
            elif res.status_code == 403:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Akses Ditolak (HTTP 403 Forbidden)'),
                        'message': _('App Key atau Secret Key tidak valid atau tidak memiliki akses endpoint user/login.'),
                        'sticky': True,
                        'type': 'danger',
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Respons Server Tidak Sesuai'),
                        'message': _('Server mengembalikan HTTP %s: %s') % (res.status_code, res.text[:200]),
                        'sticky': True,
                        'type': 'danger',
                    }
                }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Kesalahan Koneksi Jaringan'),
                    'message': str(e),
                    'sticky': True,
                    'type': 'danger',
                }
            }

    def action_view_sso_logs(self):
        """Membuka view log audit SSO Sevima"""
        return {
            'name': _('Audit Log SSO Sevima'),
            'type': 'ir.actions.act_window',
            'res_model': 'sevima.sso.log',
            'view_mode': 'list,form',
            'target': 'current',
        }
