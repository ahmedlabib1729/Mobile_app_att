# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class BookingRegistrations(models.Model):
    _name = 'charity.booking.registrations'
    _description = 'حجوزات الأقسام'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'full_name'
    _order = 'create_date desc'

    # معلومات المستفيد
    full_name = fields.Char(
        string='الاسم الثلاثي باللغة العربية',
        required=True,
        tracking=True,
        help='أدخل الاسم الثلاثي'
    )

    mother_mobile = fields.Char(
        string='رقم التواصل',
        required=True,
        tracking=True,
        help='رقم الهاتف للتواصل'
    )

    mother_whatsapp = fields.Char(
        string='رقم الواتساب',
        required=True,
        help='رقم الواتساب للتواصل'
    )

    birth_date = fields.Date(
        string='تاريخ الميلاد',
        required=True,
        help='تاريخ الميلاد'
    )

    email = fields.Char(
        string='البريد الإلكتروني',
        help='البريد الإلكتروني للتواصل'
    )

    # حقول الحجز
    headquarters_id = fields.Many2one(
        'charity.headquarters',
        string='المقر',
        required=True,
        tracking=True,
        help='اختر المقر'
    )

    department_id = fields.Many2one(
        'charity.departments',
        string='القسم',
        domain="[('headquarters_id', '=', headquarters_id), ('type', 'in', ['ladies', 'nursery'])]",
        required=True,
        tracking=True,
        help='اختر القسم'
    )

    department_booking_price = fields.Float(
        string='سعر القسم',
        related='department_id.booking_price',
        readonly=True,
        help='سعر الحجز للقسم'
    )

    # معلومات إضافية
    registration_date = fields.Datetime(
        string='تاريخ إنشاء الحجز',
        default=fields.Datetime.now,
        readonly=True,
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('confirmed', 'مؤكد'),
        ('approved', 'معتمد'),
        ('rejected', 'مرفوض'),
        ('cancelled', 'ملغي')
    ], string='الحالة',
        default='draft',
        tracking=True,
        help='حالة الحجز'
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company,
        required=True
    )

    # العمر المحسوب
    age = fields.Integer(
        string='العمر',
        compute='_compute_age',
        store=True,
        help='العمر المحسوب من تاريخ الميلاد'
    )

    @api.depends('birth_date')
    def _compute_age(self):
        """حساب العمر من تاريخ الميلاد"""
        from datetime import date
        from dateutil.relativedelta import relativedelta

        today = date.today()
        for record in self:
            if record.birth_date:
                age = relativedelta(today, record.birth_date)
                record.age = age.years
            else:
                record.age = 0

    @api.onchange('headquarters_id')
    def _onchange_headquarters_id(self):
        """تحديث domain الأقسام عند تغيير المقر"""
        if self.headquarters_id:
            self.department_id = False

            # التحقق من نوع القسم المطلوب من السياق
            department_type = self._context.get('default_department_type')
            if department_type:
                domain = [
                    ('headquarters_id', '=', self.headquarters_id.id),
                    ('type', '=', department_type)
                ]
            else:
                domain = [
                    ('headquarters_id', '=', self.headquarters_id.id),
                    ('type', 'in', ['ladies', 'nursery'])
                ]

            return {
                'domain': {
                    'department_id': domain
                }
            }

    @api.constrains('mother_mobile', 'mother_whatsapp')
    def _check_phone_numbers(self):
        """التحقق من صحة أرقام الهواتف"""
        import re
        phone_pattern = re.compile(r'^[\d\s\-\+]+$')

        for record in self:
            if record.mother_mobile and not phone_pattern.match(record.mother_mobile):
                raise ValidationError('رقم التواصل غير صحيح!')
            if record.mother_whatsapp and not phone_pattern.match(record.mother_whatsapp):
                raise ValidationError('رقم الواتساب غير صحيح!')

    @api.constrains('email')
    def _check_email(self):
        """التحقق من صحة البريد الإلكتروني"""
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        for record in self:
            if record.email and not email_pattern.match(record.email):
                raise ValidationError('البريد الإلكتروني غير صحيح!')

    @api.constrains('birth_date')
    def _check_birth_date(self):
        """التحقق من صحة تاريخ الميلاد"""
        from datetime import date
        for record in self:
            if record.birth_date:
                if record.birth_date > date.today():
                    raise ValidationError('تاريخ الميلاد لا يمكن أن يكون في المستقبل!')

    @api.constrains('department_id')
    def _check_department_type(self):
        """التحقق من أن القسم من نوع سيدات أو حضانة"""
        for record in self:
            if record.department_id and record.department_id.type not in ['ladies', 'nursery']:
                raise ValidationError('يجب اختيار قسم من نوع سيدات أو حضانة!')

    def action_confirm(self):
        """تأكيد الحجز"""
        self.ensure_one()
        if self.state == 'draft':
            self.state = 'confirmed'

    def action_approve(self):
        """اعتماد الحجز"""
        self.ensure_one()
        if self.state == 'confirmed':
            self.state = 'approved'

    def action_reject(self):
        """رفض الحجز"""
        self.ensure_one()
        if self.state in ('draft', 'confirmed'):
            self.state = 'rejected'

    def action_cancel(self):
        """إلغاء الحجز"""
        self.ensure_one()
        if self.state != 'approved':
            self.state = 'cancelled'

    def action_reset_draft(self):
        """إعادة الحجز إلى مسودة"""
        self.ensure_one()
        self.state = 'draft'

    def name_get(self):
        """تخصيص طريقة عرض اسم الحجز"""
        result = []
        for record in self:
            name = f"{record.full_name} - {record.department_id.name if record.department_id else ''}"
            result.append((record.id, name))
        return result