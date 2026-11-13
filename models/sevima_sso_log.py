# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SevimaSsoLog(models.Model):
    _name = 'sevima.sso.log'
    _description = 'Audit Log Autentikasi SSO Sevima'
    _order = 'login_date desc, id desc'

    name = fields.Char(string='Judul Log', required=True)
    login_input = fields.Char(string='Input Login / Email / NIP', index=True, readonly=True)
    user_id = fields.Many2one('res.users', string='Akun Pengguna Odoo', ondelete='set null', readonly=True)
    status = fields.Selection([
        ('success', 'Sukses Terverifikasi'),
        ('failed', 'Gagal / Akses Ditolak'),
        ('error', 'Gangguan Sistem / Timeout'),
    ], string='Status Autentikasi', default='success', index=True, readonly=True)
    
    role_info = fields.Char(string='Peran / Role Sevima', readonly=True)
    ip_address = fields.Char(string='Alamat IP Klien', readonly=True)
    latency_ms = fields.Float(string='Latency (ms)', digits=(8, 2), readonly=True)
    message = fields.Text(string='Pesan / Catatan', readonly=True)
    raw_response = fields.Text(string='Raw Response Sevima', readonly=True)
    login_date = fields.Datetime(string='Waktu Percobaan Login', default=fields.Datetime.now, index=True, readonly=True)
