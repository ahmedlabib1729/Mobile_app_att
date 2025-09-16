# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re


class CharityHeadquarters(models.Model):
    _name = 'charity.headquarters'
    _description = 'مقرات الجمعية الخيرية'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name'

    # الحقول الأساسية للمقر
    name = fields.Char(
        string='اسم المقر',
        required=True,
        tracking=True,
        translate=True,
        help='أدخل اسم المقر'
    )

    address = fields.Text(
        string='عنوان المقر',
        required=True,
        tracking=True,
        translate=True,
        help='أدخل العنوان الكامل للمقر'
    )

    manager_id = fields.Many2one(
        'res.users',
        string='مدير المقر',
        required=True,
        tracking=True,
        default=lambda self: self.env.user,
        help='اختر مدير المقر'
    )

    description = fields.Html(
        string='نبذة عن المقر',
        help='أدخل وصف تفصيلي عن المقر وأنشطته'
    )

    phone = fields.Char(
        string='رقم تلفون المقر',
        size=20,
        help='أدخل رقم التلفون الأرضي للمقر'
    )

    mobile = fields.Char(
        string='رقم الموبايل',
        size=20,
        help='أدخل رقم الموبايل للتواصل'
    )

    # حقول إضافية
    email = fields.Char(
        string='البريد الإلكتروني',
        help='أدخل البريد الإلكتروني للمقر'
    )

    active = fields.Boolean(
        string='نشط',
        default=True,
        help='إذا تم إلغاء التحديد، سيتم أرشفة المقر'
    )

    is_active = fields.Boolean(
        string='مفعل',
        default=True,
        tracking=True,
        help='حالة تفعيل المقر - يمكن استخدامها في العمليات المختلفة'
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company,
        required=True
    )

    # Computed fields
    departments_count = fields.Integer(
        string='عدد الأقسام',
        compute='_compute_departments_count',
        help='عدد الأقسام في هذا المقر'
    )

    registrations_count = fields.Integer(
        string='عدد التسجيلات',
        compute='_compute_registrations_count',
        help='إجمالي التسجيلات في هذا المقر'
    )

    # One2many relationships
    department_ids = fields.One2many(
        'charity.departments',
        'headquarters_id',
        string='الأقسام',
        help='الأقسام التابعة لهذا المقر'
    )

    # أضف هذه الحقول بعد الحقول الموجودة
    image = fields.Image(
        string='صورة المقر',
        max_width=1920,
        max_height=1920,
        help='صورة تمثل المقر (يُفضل 1920x1080)'
    )

    image_medium = fields.Image(
        string='صورة متوسطة',
        related='image',
        max_width=512,
        max_height=512,
        store=True
    )

    @api.depends('department_ids')
    def _compute_departments_count(self):
        """حساب عدد الأقسام لكل مقر"""
        for record in self:
            record.departments_count = len(record.department_ids)

    @api.depends('department_ids')
    def _compute_registrations_count(self):
        """حساب إجمالي التسجيلات في المقر"""
        ClubRegistrations = self.env['charity.club.registrations']
        BookingRegistrations = self.env['charity.booking.registrations']

        for record in self:
            club_regs = ClubRegistrations.search_count([
                ('headquarters_id', '=', record.id),
                ('state', '!=', 'cancelled')
            ])
            booking_regs = BookingRegistrations.search_count([
                ('headquarters_id', '=', record.id),
                ('state', '!=', 'cancelled')
            ])
            record.registrations_count = club_regs + booking_regs

    # Constraints
    @api.constrains('phone')
    def _check_phone(self):
        """التحقق من صحة رقم التلفون"""
        for record in self:
            if record.phone:
                # السماح بالأرقام والمسافات والشرطات فقط
                if not re.match(r'^[\d\s\-\+]+$', record.phone):
                    raise ValidationError('رقم التلفون يجب أن يحتوي على أرقام فقط!')

    @api.constrains('mobile')
    def _check_mobile(self):
        """التحقق من صحة رقم الموبايل"""
        for record in self:
            if record.mobile:
                # السماح بالأرقام والمسافات والشرطات فقط
                if not re.match(r'^[\d\s\-\+]+$', record.mobile):
                    raise ValidationError('رقم الموبايل يجب أن يحتوي على أرقام فقط!')

    @api.constrains('email')
    def _check_email(self):
        """التحقق من صحة البريد الإلكتروني"""
        for record in self:
            if record.email:
                # تحقق بسيط من صيغة البريد الإلكتروني
                if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', record.email):
                    raise ValidationError('البريد الإلكتروني غير صحيح!')

    # SQL Constraints
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name, company_id)', 'اسم المقر يجب أن يكون فريداً لكل شركة!'),
    ]

    @api.model
    def create(self, vals):
        """Override create method to add custom logic"""
        # يمكن إضافة أي منطق خاص عند إنشاء مقر جديد
        return super(CharityHeadquarters, self).create(vals)

    def write(self, vals):
        """Override write method to add custom logic"""
        # يمكن إضافة أي منطق خاص عند تحديث المقر
        return super(CharityHeadquarters, self).write(vals)

    def name_get(self):
        """تخصيص طريقة عرض اسم المقر"""
        result = []
        for record in self:
            name = record.name
            if record.address:
                # إضافة أول 30 حرف من العنوان
                address_short = record.address[:30] + '...' if len(record.address) > 30 else record.address
                name = f"{name} ({address_short})"
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100):
        """البحث في المقرات بالاسم أو العنوان"""
        args = args or []
        if name:
            args = ['|', ('name', operator, name), ('address', operator, name)] + args
        return self._search(args, limit=limit)

    def action_view_departments(self):
        """فتح قائمة الأقسام للمقر"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'أقسام {self.name}',
            'view_mode': 'kanban,list,form',
            'res_model': 'charity.departments',
            'domain': [('headquarters_id', '=', self.id)],
            'context': {
                'default_headquarters_id': self.id,
                'search_default_group_type': 1
            }
        }

