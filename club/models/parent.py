# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


class ClubParent(models.Model):
    _name = 'club.parent'
    _description = 'ولي الأمر'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _sql_constraints = [
        ('full_mobile_unique', 'UNIQUE(full_mobile)',
         'رقم الموبايل موجود بالفعل! يجب أن يكون رقم الموبايل فريد لكل ولي أمر.')
    ]

    name = fields.Char(string='اسم ولي الأمر', required=True, tracking=True)

    address = fields.Text(string='العنوان', tracking=True)

    country_code = fields.Selection([
        ('+966', 'السعودية (+966)'),
        ('+971', 'الإمارات (+971)'),
        ('+965', 'الكويت (+965)'),
        ('+968', 'عمان (+968)'),
        ('+974', 'قطر (+974)'),
        ('+973', 'البحرين (+973)'),
        ('+20', 'مصر (+20)'),
        ('+962', 'الأردن (+962)'),
    ], string='كود الدولة', default='+966', required=True)

    mobile = fields.Char(
        string='رقم الموبايل',
        required=True,
        tracking=True,
        help='رقم الموبايل بدون كود الدولة (مثال: 501234567)'
    )

    full_mobile = fields.Char(
        string='رقم الموبايل الكامل',
        compute='_compute_full_mobile',
        store=True,
        help='رقم الموبايل الكامل مع كود الدولة'
    )

    email = fields.Char(string='البريد الإلكتروني', tracking=True)

    player_ids = fields.One2many(
        'club.player',
        'parent_id',
        string='الأبناء'
    )

    children_count = fields.Integer(
        string='عدد الأبناء',
        compute='_compute_children_count',
        store=True
    )

    total_children_fees = fields.Monetary(
        string='إجمالي رسوم الأبناء',
        compute='_compute_total_children_fees',
        store=True,
        currency_field='currency_id',
        help='إجمالي رسوم الاشتراك لجميع الأبناء'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='العملة',
        related='company_id.currency_id',
        readonly=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company,
        required=True
    )

    active = fields.Boolean(string='نشط', default=True)

    @api.depends('player_ids')
    def _compute_children_count(self):
        for record in self:
            record.children_count = len(record.player_ids)

    @api.depends('player_ids.total_fees')
    def _compute_total_children_fees(self):
        for record in self:
            record.total_children_fees = sum(child.total_fees for child in record.player_ids)

    @api.depends('country_code', 'mobile')
    def _compute_full_mobile(self):
        for record in self:
            if record.country_code and record.mobile:
                # إزالة الصفر الأول إذا موجود
                mobile = record.mobile
                if mobile.startswith('0'):
                    mobile = mobile[1:]
                record.full_mobile = record.country_code + mobile
            else:
                record.full_mobile = False

    @api.constrains('mobile', 'country_code')
    def _check_mobile(self):
        for record in self:
            if record.mobile and record.country_code:
                clean_mobile = re.sub(r'[^0-9]', '', record.mobile)

                # إزالة الصفر الأول إذا موجود
                if clean_mobile.startswith('0'):
                    clean_mobile = clean_mobile[1:]

                # التحقق حسب كود الدولة
                if record.country_code == '+966':
                    # السعودية: 9 أرقام تبدأ بـ 5
                    if not (len(clean_mobile) == 9 and clean_mobile.startswith('5')):
                        raise ValidationError(_('رقم الموبايل السعودي يجب أن يكون 9 أرقام ويبدأ بـ 5'))

                elif record.country_code == '+971':
                    # الإمارات: 9 أرقام تبدأ بـ 50, 52, 54, 55, 56, 58
                    if not (len(clean_mobile) == 9 and clean_mobile[:2] in ['50', '52', '54', '55', '56', '58']):
                        raise ValidationError(_('رقم الموبايل الإماراتي غير صحيح'))

                elif record.country_code == '+20':
                    # مصر: 10 أرقام تبدأ بـ 10, 11, 12, 15
                    if not (len(clean_mobile) == 10 and clean_mobile[:2] in ['10', '11', '12', '15']):
                        raise ValidationError(_('رقم الموبايل المصري يجب أن يكون 10 أرقام'))

                # لا نحتاج لتحديث الحقل هنا - فقط التحقق
                # record.mobile = clean_mobile  # حذف هذا السطر!

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # تنظيف رقم الموبايل قبل الحفظ
            if 'mobile' in vals:
                clean_mobile = re.sub(r'[^0-9]', '', vals['mobile'])
                if clean_mobile.startswith('0'):
                    vals['mobile'] = clean_mobile[1:]
                else:
                    vals['mobile'] = clean_mobile

        return super().create(vals_list)

    def write(self, vals):
        # تنظيف رقم الموبايل قبل التحديث
        if 'mobile' in vals:
            clean_mobile = re.sub(r'[^0-9]', '', vals['mobile'])
            if clean_mobile.startswith('0'):
                vals['mobile'] = clean_mobile[1:]
            else:
                vals['mobile'] = clean_mobile

        return super().write(vals)

    def action_view_children(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'الأبناء',
            'view_mode': 'list,form',
            'res_model': 'club.player',
            'domain': [('parent_id', '=', self.id)],
            'context': {'default_parent_id': self.id}
        }