# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Parent(models.Model):
    _name = 'club.parent'
    _description = 'ولي أمر اللاعب'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name'

    # معلومات أساسية
    name = fields.Char(
        string='اسم ولي الأمر',
        required=True,
        tracking=True
    )

    identification_number = fields.Char(
        string='رقم الهوية',
        required=True,
        copy=False
    )

    nationality = fields.Many2one(
        'res.country',
        string='الجنسية',
        required=True
    )

    # معلومات الاتصال
    mobile = fields.Char(
        string='رقم الجوال',
        required=True
    )

    email = fields.Char(
        string='البريد الإلكتروني',
        required=True
    )

    # معلومات إضافية
    phone = fields.Char(
        string='رقم الهاتف الثابت'
    )

    address = fields.Text(
        string='العنوان'
    )

    job = fields.Char(
        string='الوظيفة'
    )

    # الأبناء المسجلين
    player_ids = fields.One2many(
        'club.player',
        'parent_id',
        string='الأبناء المسجلين'
    )

    player_count = fields.Integer(
        string='عدد الأبناء',
        compute='_compute_player_count',
        store=True
    )

    # معلومات إضافية
    notes = fields.Text(
        string='ملاحظات'
    )

    active = fields.Boolean(
        string='نشط',
        default=True
    )

    @api.depends('player_ids')
    def _compute_player_count(self):
        for parent in self:
            parent.player_count = len(parent.player_ids)

    @api.constrains('mobile')
    def _check_mobile(self):
        for parent in self:
            if parent.mobile and not parent.mobile.isdigit():
                raise ValidationError('رقم الجوال يجب أن يحتوي على أرقام فقط!')

    @api.constrains('email')
    def _check_email(self):
        for parent in self:
            if parent.email and '@' not in parent.email:
                raise ValidationError('البريد الإلكتروني غير صحيح!')

    def name_get(self):
        result = []
        for parent in self:
            name = f"{parent.name} ({parent.identification_number})"
            result.append((parent.id, name))
        return result