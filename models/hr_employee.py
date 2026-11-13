# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    sevima_user_id = fields.Char(
        string='ID User Sevima',
        readonly=True,
        help='ID akun pengguna Sevima Platform terkait pegawai ini'
    )
    is_sevima_synced = fields.Boolean(
        string='Sinkron Sevima SSO',
        default=False,
        help='Menandai pegawai yang akun Odoo-nya terhubung ke Sevima SSO'
    )
    sevima_role_name = fields.Char(
        related='user_id.sevima_role_name',
        string='Peran Sevima',
        readonly=True
    )
    sevima_nama_satker = fields.Char(
        related='user_id.sevima_nama_satker',
        string='Satker Sevima',
        readonly=True
    )
