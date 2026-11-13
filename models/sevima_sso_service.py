# -*- coding: utf-8 -*-
import json
import time
import requests
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SevimaSsoService(models.AbstractModel):
    _name = 'sevima.sso.service'
    _description = 'Service Helper Autentikasi SSO Sevima Platform'

    @api.model
    def get_sso_config(self):
        """Mengambil konfigurasi SSO Sevima dari ir.config_parameter"""
        ICP = self.env['ir.config_parameter'].sudo()
        if hasattr(ICP, 'get_bool'):
            enabled = ICP.get_bool('sirita_sso_sevima.enabled', True)
            base_url = (ICP.get_str('sirita_sso_sevima.base_url', 'https://api.sevimaplatform.com') or 'https://api.sevimaplatform.com').rstrip('/')
            app_key = (ICP.get_str('sirita_sso_sevima.app_key', '') or '').strip()
            secret_key = (ICP.get_str('sirita_sso_sevima.secret_key', '') or '').strip()
            auto_create = ICP.get_bool('sirita_sso_sevima.auto_create_user', True)
            default_user_type = ICP.get_str('sirita_sso_sevima.default_user_type', 'internal') or 'internal'
            timeout = ICP.get_int('sirita_sso_sevima.timeout', 10) or 10
        else:
            enabled = ICP.get_param('sirita_sso_sevima.enabled', 'True').lower() in ('true', '1', 't')
            base_url = ICP.get_param('sirita_sso_sevima.base_url', 'https://api.sevimaplatform.com').rstrip('/')
            app_key = ICP.get_param('sirita_sso_sevima.app_key', '').strip()
            secret_key = ICP.get_param('sirita_sso_sevima.secret_key', '').strip()
            auto_create = ICP.get_param('sirita_sso_sevima.auto_create_user', 'True').lower() in ('true', '1', 't')
            default_user_type = ICP.get_param('sirita_sso_sevima.default_user_type', 'internal')
            timeout = int(ICP.get_param('sirita_sso_sevima.timeout', '10'))

        # Fallback interoperabilitas ke modul sirita_sevima jika kunci kosong
        if (not app_key or not secret_key) and 'sevima.config' in self.env:
            sevima_cfg = self.env['sevima.config'].sudo().search([], limit=1)
            if sevima_cfg and sevima_cfg.app_key and sevima_cfg.secret_key:
                app_key = app_key or sevima_cfg.app_key
                secret_key = secret_key or sevima_cfg.secret_key
                if not base_url or base_url == 'https://api.sevimaplatform.com':
                    base_url = (sevima_cfg.base_url or base_url).rstrip('/')

        return {
            'enabled': enabled,
            'base_url': base_url,
            'app_key': app_key,
            'secret_key': secret_key,
            'auto_create_user': auto_create,
            'default_user_type': default_user_type,
            'timeout': timeout,
        }

    @api.model
    def is_sso_enabled(self):
        """Memeriksa apakah fitur SSO aktif dan kredensial API telah diisi"""
        cfg = self.get_sso_config()
        return bool(cfg['enabled'] and cfg['app_key'] and cfg['secret_key'])

    @api.model
    def is_auto_create_enabled(self):
        """Memeriksa apakah fitur JIT auto-provisioning aktif"""
        return self.get_sso_config().get('auto_create_user', True)

    @api.model
    def resolve_login_to_email(self, login):
        """
        Menyelesaikan input login jika pengguna memasukkan NIP atau username.
        Mengembalikan alamat email yang terdaftar jika ditemukan.
        """
        login_clean = (login or '').strip()
        if not login_clean:
            return login_clean

        # Jika sudah berformat email (@), langsung kembalikan
        if '@' in login_clean:
            return login_clean

        # Cek berdasarkan NIP / Barcode di master data Pegawai (hr.employee)
        employee = self.env['hr.employee'].sudo().search([
            '|', ('barcode', '=', login_clean), ('identification_id', '=', login_clean)
        ], limit=1)
        if employee and employee.work_email:
            _logger.info("SSO Sevima: Resolved login NIP %s -> Email %s dari hr.employee", login_clean, employee.work_email)
            return employee.work_email.strip()

        # Cek berdasarkan sevima_nip di res.users
        user = self.env['res.users'].sudo().search([
            ('sevima_nip', '=', login_clean)
        ], limit=1)
        if user and user.email:
            _logger.info("SSO Sevima: Resolved login NIP %s -> Email %s dari res.users", login_clean, user.email)
            return user.email.strip()

        # Kembalikan apa adanya (mungkin sistem Sevima menerima format login tertentu)
        return login_clean

    @api.model
    def authenticate_sevima(self, login, password):
        """
        Melakukan HTTP POST ke endpoint resmi Sevima SSO:
        POST {base_url}/siakadcloud/v1/user/login
        Headers: X-App-Key, X-Secret-Key, Content-Type, Accept
        Body: {"email": email, "password": password}
        """
        cfg = self.get_sso_config()
        if not cfg['enabled'] or not cfg['app_key'] or not cfg['secret_key']:
            return {
                'success': False,
                'message': _('Layanan SSO Sevima dinonaktifkan atau kredensial API belum lengkap.'),
                'status_code': 0,
                'latency_ms': 0
            }

        email_to_auth = self.resolve_login_to_email(login)
        login_url = f"{cfg['base_url']}/siakadcloud/v1/user/login"
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-App-Key': cfg['app_key'],
            'X-Secret-Key': cfg['secret_key'],
        }
        payload = {
            'email': email_to_auth,
            'password': password
        }

        start_time = time.time()
        try:
            _logger.info("SSO Sevima: Memulai autentikasi ke %s untuk email: %s", login_url, email_to_auth)
            res = requests.post(login_url, headers=headers, json=payload, timeout=cfg['timeout'])
            latency_ms = round((time.time() - start_time) * 1000, 2)

            if res.status_code == 200:
                result = res.json()
                user_id = result.get('id') or result.get('attributes', {}).get('user_id')
                if user_id:
                    _logger.info("SSO Sevima: Autentikasi SUKSES untuk user_id: %s (Latency: %s ms)", user_id, latency_ms)
                    return {
                        'success': True,
                        'data': result,
                        'email': email_to_auth,
                        'latency_ms': latency_ms,
                        'status_code': 200,
                        'raw_response': res.text[:20000]
                    }
                else:
                    return {
                        'success': False,
                        'message': _('Respon Sevima HTTP 200 namun tidak memiliki user_id yang valid.'),
                        'status_code': 200,
                        'latency_ms': latency_ms,
                        'raw_response': res.text[:20000]
                    }
            elif res.status_code == 401:
                _logger.warning("SSO Sevima: Autentikasi GAGAL (HTTP 401) untuk email: %s", email_to_auth)
                return {
                    'success': False,
                    'message': _('Email atau Password akun Sevima SIAKAD tidak cocok, atau akun tidak memiliki akses.'),
                    'status_code': 401,
                    'latency_ms': latency_ms,
                    'raw_response': res.text[:20000]
                }
            elif res.status_code == 403:
                _logger.error("SSO Sevima: Akses API DITOLAK (HTTP 403). Periksa App Key & Secret Key.")
                return {
                    'success': False,
                    'message': _('Akses API Sevima ditolak (HTTP 403 Forbidden). Hubungi administrator TIPD.'),
                    'status_code': 403,
                    'latency_ms': latency_ms,
                    'raw_response': res.text[:20000]
                }
            else:
                _logger.warning("SSO Sevima: Server mengembalikan HTTP %s: %s", res.status_code, res.text[:200])
                return {
                    'success': False,
                    'message': _('Server Sevima mengembalikan kode respons %s: %s') % (res.status_code, res.text[:200]),
                    'status_code': res.status_code,
                    'latency_ms': latency_ms,
                    'raw_response': res.text[:20000]
                }
        except requests.exceptions.Timeout:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            _logger.error("SSO Sevima: Request Timeout setelah %s ms", latency_ms)
            return {
                'success': False,
                'message': _('Koneksi ke Server Sevima Platform timeout (melebihi batas waktu %s detik).') % cfg['timeout'],
                'status_code': 0,
                'latency_ms': latency_ms
            }
        except Exception as e:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            _logger.exception("SSO Sevima: Kesalahan koneksi jaringan: %s", str(e))
            return {
                'success': False,
                'message': _('Kesalahan komunikasi jaringan dengan Sevima API: %s') % str(e),
                'status_code': 0,
                'latency_ms': latency_ms
            }

    @api.model
    def provision_user_from_sevima(self, sevima_data):
        """
        Just-In-Time (JIT) Provisioning:
        Membuat record res.users baru dan menghubungkannya dengan hr.employee.
        """
        attributes = sevima_data.get('attributes', {})
        user_id = str(sevima_data.get('id') or attributes.get('user_id', ''))
        nama = attributes.get('nama') or _('Pengguna Sevima')
        email = (attributes.get('email') or '').strip().lower()
        status_aktif = str(attributes.get('status_aktif', '1'))

        if status_aktif != '1':
            _logger.warning("SSO Sevima: Gagal provisioning, status user tidak aktif (status_aktif=%s)", status_aktif)
            return False

        # Ekstraksi role primer
        roles = attributes.get('role', [])
        primary_role = roles[0] if roles else {}
        role_code = primary_role.get('id_role', '')
        role_name = primary_role.get('nama_role', '')
        nip = primary_role.get('nip', '')
        id_pegawai = primary_role.get('id_pegawai', '')
        id_satker = primary_role.get('id_satker', '')
        nama_satker = primary_role.get('nama_satker', '')

        login = email if email else (nip if nip else f"sevima_{user_id}")

        # Cek apakah user sudah ada berdasarkan login, email, atau sevima_user_id
        existing_user = self.env['res.users'].sudo().search([
            '|', '|',
            ('login', '=', login),
            ('email', '=', email),
            ('sevima_user_id', '=', user_id)
        ], limit=1)

        if existing_user:
            self.sync_user_profile(existing_user, sevima_data)
            return existing_user

        # Tentukan Group Akses Default
        # Role Dosen (DSN) atau Tendik (TDK/PEG) mendapatkan internal user (base.group_user)
        # Role Mahasiswa (MHS) mendapatkan portal user (base.group_portal)
        is_employee_role = role_code in ['DSN', 'TDK', 'PEG'] or 'dosen' in role_name.lower() or 'pegawai' in role_name.lower()
        
        cfg = self.get_sso_config()
        if is_employee_role or cfg.get('default_user_type') == 'internal':
            groups = [
                self.env.ref('base.group_user').id,
            ]
        else:
            groups = [
                self.env.ref('base.group_portal').id,
            ]

        user_vals = {
            'name': nama,
            'login': login,
            'email': email,
            'is_sevima_sso': True,
            'sevima_user_id': user_id,
            'sevima_nip': nip,
            'sevima_role_code': role_code,
            'sevima_role_name': role_name,
            'sevima_id_pegawai': id_pegawai,
            'sevima_id_satker': id_satker,
            'sevima_nama_satker': nama_satker,
            'sevima_last_sync': fields.Datetime.now(),
            'group_ids': [(6, 0, groups)],
            'active': True,
        }

        new_user = self.env['res.users'].sudo().create(user_vals)
        _logger.info("SSO Sevima: Berhasil membuat akun pengguna Odoo baru: %s (ID: %s, Role: %s)", new_user.login, new_user.id, role_name)

        # Kaitkan secara otomatis ke hr.employee jika NIP atau email cocok
        employee = False
        if nip:
            employee = self.env['hr.employee'].sudo().search([
                '|', ('barcode', '=', nip), ('identification_id', '=', nip)
            ], limit=1)
        if not employee and email:
            employee = self.env['hr.employee'].sudo().search([
                ('work_email', '=', email)
            ], limit=1)

        if employee:
            if not employee.user_id:
                employee.sudo().write({'user_id': new_user.id})
                _logger.info("SSO Sevima: Menghubungkan user %s ke pegawai hr.employee %s", new_user.name, employee.name)
            if hasattr(employee, 'sevima_user_id'):
                employee.sudo().write({
                    'sevima_user_id': user_id,
                    'is_sevima_synced': True,
                })

        return new_user

    @api.model
    def sync_user_profile(self, user, sevima_data):
        """Sinkronisasi data profil pengguna dari Sevima API ke Odoo"""
        attributes = sevima_data.get('attributes', {})
        user_id = str(sevima_data.get('id') or attributes.get('user_id', ''))
        nama = attributes.get('nama')
        email = (attributes.get('email') or '').strip().lower()

        roles = attributes.get('role', [])
        primary_role = roles[0] if roles else {}

        update_vals = {
            'is_sevima_sso': True,
            'sevima_user_id': user_id,
            'sevima_last_sync': fields.Datetime.now(),
        }
        if nama and user.name != nama:
            update_vals['name'] = nama
        if email and not user.email:
            update_vals['email'] = email
        if primary_role:
            if primary_role.get('id_role'):
                update_vals['sevima_role_code'] = primary_role.get('id_role')
            if primary_role.get('nama_role'):
                update_vals['sevima_role_name'] = primary_role.get('nama_role')
            if primary_role.get('nip'):
                update_vals['sevima_nip'] = primary_role.get('nip')
            if primary_role.get('id_pegawai'):
                update_vals['sevima_id_pegawai'] = primary_role.get('id_pegawai')
            if primary_role.get('id_satker'):
                update_vals['sevima_id_satker'] = primary_role.get('id_satker')
            if primary_role.get('nama_satker'):
                update_vals['sevima_nama_satker'] = primary_role.get('nama_satker')

        user.sudo().write(update_vals)

        # Relasi hr.employee
        if update_vals.get('sevima_nip'):
            employee = self.env['hr.employee'].sudo().search([
                '|', ('barcode', '=', update_vals['sevima_nip']), ('identification_id', '=', update_vals['sevima_nip'])
            ], limit=1)
            if employee and not employee.user_id:
                employee.sudo().write({'user_id': user.id})

    @api.model
    def create_login_log(self, login, status, message, user_id=None, role=None, ip=None, latency_ms=0, raw_response=None):
        """Mencatat aktivitas login SSO ke dalam model audit sevima.sso.log"""
        try:
            self.env['sevima.sso.log'].sudo().create({
                'name': f"Login {login} - {status.upper()}",
                'login_input': login,
                'status': status,
                'message': message,
                'user_id': user_id,
                'role_info': role,
                'ip_address': ip,
                'latency_ms': latency_ms,
                'raw_response': raw_response,
                'login_date': fields.Datetime.now(),
            })
        except Exception as e:
            _logger.error("SSO Sevima: Gagal menulis log audit login: %s", str(e))
