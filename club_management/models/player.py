# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date


class Player(models.Model):
    _name = 'club.player'
    _description = 'لاعب النادي'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name'

    # معلومات أساسية
    name = fields.Char(
        string='اسم اللاعب',
        required=True,
        tracking=True
    )

    nationality = fields.Many2one(
        'res.country',
        string='الجنسية',
        required=True
    )

    birth_place = fields.Char(
        string='محل الميلاد',
        required=True
    )

    birth_date = fields.Date(
        string='تاريخ الميلاد',
        required=True,
        tracking=True
    )

    age = fields.Integer(
        string='العمر',
        compute='_compute_age',
        store=True
    )

    # رقم الهوية - فريد
    identification_number = fields.Char(
        string='رقم الجواز/الهوية',
        required=True,
        copy=False,
        tracking=True
    )

    gender = fields.Selection([
        ('male', 'ذكر'),
        ('female', 'أنثى')
    ], string='الجنس', required=True, default='male')

    # ولي الأمر
    parent_id = fields.Many2one(
        'club.parent',
        string='ولي الأمر',
        required=True
    )

    # الصورة
    image = fields.Binary(
        string='صورة اللاعب',
        attachment=True
    )

    # معلومات إضافية
    phone = fields.Char(
        string='رقم الهاتف'
    )

    email = fields.Char(
        string='البريد الإلكتروني'
    )

    address = fields.Text(
        string='العنوان'
    )

    notes = fields.Text(
        string='ملاحظات'
    )

    active = fields.Boolean(
        string='نشط',
        default=True
    )

    # العضويات المرتبطة
    membership_ids = fields.One2many(
        'club.membership',
        'player_id',
        string='العضويات'
    )

    # الأنشطة المسجل بها
    activity_ids = fields.One2many(
        'club.member.activity',
        'player_id',
        string='الأنشطة المسجلة'
    )

    @api.depends('birth_date')
    def _compute_age(self):
        today = date.today()
        for player in self:
            if player.birth_date:
                born = player.birth_date
                age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
                player.age = age
            else:
                player.age = 0

    @api.constrains('identification_number')
    def _check_unique_identification(self):
        for player in self:
            if player.identification_number:
                domain = [
                    ('identification_number', '=', player.identification_number),
                    ('id', '!=', player.id)
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError('رقم الهوية/الجواز مسجل مسبقاً!')

    @api.constrains('birth_date')
    def _check_birth_date(self):
        for player in self:
            if player.birth_date and player.birth_date > fields.Date.today():
                raise ValidationError('تاريخ الميلاد لا يمكن أن يكون في المستقبل!')

    @api.model
    def create(self, vals):
        # يمكن إضافة رقم تسلسلي للاعب إذا أردت
        return super(Player, self).create(vals)

    def name_get(self):
        result = []
        for player in self:
            name = f"{player.name} ({player.identification_number})"
            result.append((player.id, name))
        return result