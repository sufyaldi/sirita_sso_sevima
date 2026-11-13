# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import AccessDenied
from odoo.fields import Domain
from odoo.http import request

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    is_sevima_sso = fields.Boolean(
        string='Autentikasi SSO Sevima',
        default=False,
        index=True,
        help='Menandakan apakah pengguna diautentikasi melalui Sevima Platform SSO.'
    )
    sevima_user_id = fields.Char(
        string='ID User Sevima',
        index=True,
        readonly=True,
        help='ID unik akun pengguna dari API Sevima Platform (SIAKAD Cloud).'
    )
    sevima_nip = fields.Char(
        string='NIP / NIM Sevima',
        index=True,
        help='Nomor Induk Pegawai (NIP/NIDN) atau Mahasiswa (NIM) dari Sevima.'
    )
    sevima_role_code = fields.Char(
        string='Kode Role Sevima',
        readonly=True,
        help='Kode peran Sevima (contoh: DSN, TDK, MHS)'
    )
    sevima_role_name = fields.Char(
        string='Nama Role Sevima',
        readonly=True,
        help='Nama peran resmi dari Sevima (contoh: Dosen, Tenaga Kependidikan, Mahasiswa)'
    )
    sevima_id_pegawai = fields.Char(
        string='ID Pegawai Sevima',
        readonly=True,
        help='ID data master pegawai di Sevima'
    )
    sevima_id_satker = fields.Char(
        string='ID Satuan Kerja (Satker)',
        readonly=True,
        help='Kode Satuan Kerja / Program Studi / Fakultas di Sevima'
    )
    sevima_nama_satker = fields.Char(
        string='Nama Satker / Prodi',
        readonly=True,
        help='Nama Satker atau Program Studi penugasan'
    )
    sevima_last_sync = fields.Datetime(
        string='Waktu Sinkronisasi Terakhir',
        readonly=True,
        help='Waktu terakhir data profil berhasil diperbarui dari respon Sevima SSO'
    )
    sevima_sso_log_ids = fields.One2many(
        'sevima.sso.log',
        'user_id',
        string='Riwayat Log SSO',
        readonly=True
    )

    def _get_group_ids(self):
        """
        Fail-safe untuk sesi tanpa user terautentikasi (unauthenticated/pre-dispatch),
        di mana self.env.user adalah recordset kosong res.users().
        """
        if not self:
            public_user = self.env.ref('base.public_user', raise_if_not_found=False)
            return public_user._get_group_ids() if public_user else ()
        return super()._get_group_ids()

    @api.model
    def _get_login_domain(self, login):
        """
        Memperluas pencarian akun saat login:
        Dapat menggunakan Email/Login standar atau Nomor NIP/NIM Sevima.
        """
        domain = super()._get_login_domain(login)
        if login:
            return domain | Domain('sevima_nip', '=', login)
        return domain

    def _login(self, credential, user_agent_env):
        """
        Intercept alur login Odoo:
        Jika user lokal tidak ditemukan (AccessDenied), lakukan verifikasi langsung
        ke Sevima API. Jika valid dan JIT Provisioning aktif, buat akun user Odoo secara otomatis.
        """
        try:
            return super()._login(credential, user_agent_env=user_agent_env)
        except AccessDenied:
            sso_service = self.env['sevima.sso.service'].sudo()
            if not sso_service.is_sso_enabled():
                raise

            login = (credential.get('login') or '').strip()
            password = credential.get('password') or ''
            if not login or not password or credential.get('type') != 'password':
                raise

            # Cek apakah user sebenarnya sudah ada di database Odoo
            existing_user = self.sudo().search(self._get_login_domain(login), limit=1)
            if existing_user:
                # Jika user sudah ada, super()._login gagal karena password lokal dan
                # Sevima SSO di _check_credentials keduanya ditolak. Reraise AccessDenied.
                raise

            # User belum ada di database Odoo -> Cek apakah JIT Provisioning aktif
            if not sso_service.is_auto_create_enabled():
                _logger.warning("SSO Sevima: User %s tidak terdaftar di Odoo dan JIT provisioning dinonaktifkan.", login)
                raise

            ip = user_agent_env.get('REMOTE_ADDR') if user_agent_env else (
                request.httprequest.environ.get('REMOTE_ADDR') if request else 'n/a'
            )

            # Lakukan autentikasi langsung ke Sevima API
            sevima_auth = sso_service.authenticate_sevima(login, password)
            if not sevima_auth.get('success'):
                sso_service.create_login_log(
                    login=login,
                    status='failed',
                    message=sevima_auth.get('message', _('Kredensial Sevima Tidak Valid')),
                    ip=ip,
                    latency_ms=sevima_auth.get('latency_ms', 0)
                )
                raise AccessDenied()

            # Buat akun baru secara otomatis (Just-In-Time Provisioning)
            new_user = sso_service.provision_user_from_sevima(sevima_auth['data'])
            if not new_user:
                raise AccessDenied()

            sso_service.create_login_log(
                login=login,
                status='success',
                message=_('JIT Auto-Provisioning dan Login Berhasil via Sevima SSO'),
                user_id=new_user.id,
                role=new_user.sevima_role_name or new_user.sevima_role_code,
                ip=ip,
                latency_ms=sevima_auth.get('latency_ms', 0),
                raw_response=sevima_auth.get('raw_response')
            )

            # Update login date
            new_user.sudo()._update_last_login()

            return {
                'uid': new_user.id,
                'auth_method': 'sevima_sso',
                'mfa': 'default',
            }

    def _check_credentials(self, credential, env):
        """
        Validasi password untuk user yang sudah ada:
        1. Coba password lokal Odoo terlebih dahulu (super)
        2. Jika AccessDenied, periksa ke Sevima API menggunakan email/login user
        """
        try:
            return super()._check_credentials(credential, env)
        except AccessDenied:
            if not (credential.get('type') == 'password' and credential.get('password')):
                raise

            env = env or {}
            interactive = env.get('interactive', True)
            if not interactive and self.env.user._rpc_api_keys_only():
                raise

            sso_service = self.env['sevima.sso.service'].sudo()
            if not sso_service.is_sso_enabled():
                raise

            user = self.env.user
            password = credential['password']
            ip = env.get('REMOTE_ADDR') or (
                request.httprequest.environ.get('REMOTE_ADDR') if request else 'n/a'
            )

            # Gunakan email resmi atau NIP user
            login_candidate = user.email or user.login or user.sevima_nip
            sevima_auth = sso_service.authenticate_sevima(login_candidate, password)

            if sevima_auth.get('success'):
                # Validasi status aktif akun di Sevima
                attributes = sevima_auth['data'].get('attributes', {})
                if str(attributes.get('status_aktif', '1')) != '1':
                    sso_service.create_login_log(
                        login=user.login,
                        status='failed',
                        message=_('Akun Sevima ditolak: status_aktif != 1 (non-aktif)'),
                        user_id=user.id,
                        ip=ip,
                        latency_ms=sevima_auth.get('latency_ms', 0)
                    )
                    raise AccessDenied(_("Akun Sevima SIAKAD Anda berstatus non-aktif."))

                # Sinkronkan update data profil
                sso_service.sync_user_profile(user, sevima_auth['data'])

                sso_service.create_login_log(
                    login=user.login,
                    status='success',
                    message=_('Login Berhasil via Sevima SSO'),
                    user_id=user.id,
                    role=user.sevima_role_name or user.sevima_role_code,
                    ip=ip,
                    latency_ms=sevima_auth.get('latency_ms', 0),
                    raw_response=sevima_auth.get('raw_response')
                )

                return {
                    'uid': user.id,
                    'auth_method': 'sevima_sso',
                    'mfa': 'default',
                }
            else:
                sso_service.create_login_log(
                    login=user.login,
                    status='failed',
                    message=sevima_auth.get('message', _('Verifikasi Password Sevima Gagal')),
                    user_id=user.id,
                    ip=ip,
                    latency_ms=sevima_auth.get('latency_ms', 0)
                )
                raise AccessDenied()
