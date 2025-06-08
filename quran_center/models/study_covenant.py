# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StudyCovenant(models.Model):
    _name = 'quran.study.covenant'
    _description = 'Study Covenant'
    _rec_name = 'name'

    name = fields.Char(
        string='اسم الميثاق',
        required=True
    )



    program_type = fields.Selection([
        ('clubs', 'برامج النوادي'),
        ('ladies', 'برامج السيدات')
    ], string='نوع البرنامج', required=True, default='clubs')

    active = fields.Boolean(
        string='نشط',
        default=True
    )