# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime


class NurseryClassConfig(models.Model):
    _name = 'nursery.class.config'
    _description = 'تكوين صفوف الحضانة'
    _rec_name = 'class_name'
    _order = 'sequence, id'

    class_name = fields.Selection([
        ('before_kg', 'قبل الروضة'),
        ('nursery_2_3', 'صف الحضانة 2-3'),
        ('nursery_1_2', 'صف الحضانة 1-2'),
        ('nursery_0_1', 'صف الحضانة 0-1')
    ], string='اسم الصف', required=True)

    date_from = fields.Date(string='تاريخ الميلاد من', required=True)
    date_to = fields.Date(string='تاريخ الميلاد إلى', required=True)

    academic_year = fields.Char(string='السنة الدراسية', required=True,
                                help='مثال: 2024-2025')

    department_id = fields.Many2one('charity.departments',
                                    string='القسم',
                                    domain=[('type', '=', 'nursery')],
                                    required=True)

    is_active = fields.Boolean(string='نشط', default=True)
    sequence = fields.Integer(string='الترتيب', default=10)

    # حقل محسوب لعرض الفئة العمرية
    age_range_display = fields.Char(string='الفئة العمرية',
                                    compute='_compute_age_range_display',
                                    store=True)

    @api.depends('date_from', 'date_to')
    def _compute_age_range_display(self):
        for record in self:
            if record.date_from and record.date_to:
                today = fields.Date.today()
                age_from = (today - record.date_to).days // 365
                age_to = (today - record.date_from).days // 365
                record.age_range_display = f"من {age_from} إلى {age_to} سنة"
            else:
                record.age_range_display = ''

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from >= record.date_to:
                raise ValidationError('تاريخ البداية يجب أن يكون قبل تاريخ النهاية!')

    @api.constrains('class_name', 'department_id', 'academic_year', 'is_active')
    def _check_unique_active_class(self):
        """التحقق من عدم وجود صف نشط مكرر لنفس القسم والسنة"""
        for record in self:
            if record.is_active:
                duplicate = self.search([
                    ('id', '!=', record.id),
                    ('class_name', '=', record.class_name),
                    ('department_id', '=', record.department_id.id),
                    ('academic_year', '=', record.academic_year),
                    ('is_active', '=', True)
                ])
                if duplicate:
                    raise ValidationError(
                        f'يوجد بالفعل تكوين نشط لصف {dict(self._fields["class_name"].selection).get(record.class_name)} '
                        f'في القسم {record.department_id.name} للسنة {record.academic_year}!'
                    )

    def check_child_eligibility(self, birth_date, department_id):
        """التحقق من أهلية الطفل للتسجيل بناءً على تاريخ الميلاد"""
        eligible_configs = self.search([
            ('department_id', '=', department_id),
            ('is_active', '=', True),
            ('date_from', '<=', birth_date),
            ('date_to', '>=', birth_date)
        ])
        return eligible_configs