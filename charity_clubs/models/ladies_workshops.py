# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LadiesWorkshop(models.Model):
    _name = 'charity.ladies.workshop'
    _description = 'ورش السيدات'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'department_id, sequence, name'

    # الحقول الأساسية
    name = fields.Char(
        string='اسم الورشة',
        required=True,
        tracking=True,
        help='أدخل اسم الورشة'
    )

    department_id = fields.Many2one(
        'charity.departments',
        string='القسم',
        required=True,
        ondelete='cascade',
        domain=[('type', '=', 'ladies')],
        tracking=True,
        help='القسم التابع له الورشة'
    )

    # الموعد
    schedule = fields.Text(
        string='موعد الورشة',
        required=True,
        help='موعد الورشة'
    )

    # السعر
    price = fields.Float(
        string='سعر الورشة',
        required=True,
        digits=(10, 2),
        tracking=True,
        help='سعر الورشة'
    )

    # معلومات إضافية
    max_capacity = fields.Integer(
        string='عدد المقاعد',
        default=20,
        required=True,
        help='العدد الأقصى للمشتركات'
    )

    sequence = fields.Integer(
        string='الترتيب',
        default=10
    )

    active = fields.Boolean(
        string='نشط',
        default=True
    )

    is_active = fields.Boolean(
        string='مفعلة',
        default=True,
        tracking=True,
        help='هل الورشة مفتوحة للتسجيل'
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        related='department_id.company_id',
        store=True,
        readonly=True
    )

    # الإحصائيات
    enrollment_ids = fields.One2many(
        'charity.booking.registrations',
        'workshop_id',
        string='التسجيلات',
        domain=[('state', '!=', 'cancelled')]
    )

    enrollments_count = fields.Integer(
        string='عدد المشتركات',
        compute='_compute_enrollments_count'
    )

    available_seats = fields.Integer(
        string='المقاعد المتاحة',
        compute='_compute_available_seats'
    )

    @api.depends('enrollment_ids')
    def _compute_enrollments_count(self):
        """حساب عدد المشتركات"""
        for record in self:
            record.enrollments_count = len(record.enrollment_ids.filtered(
                lambda r: r.state in ['confirmed', 'approved']
            ))

    @api.depends('enrollments_count', 'max_capacity')
    def _compute_available_seats(self):
        """حساب المقاعد المتاحة"""
        for record in self:
            record.available_seats = record.max_capacity - record.enrollments_count

    @api.constrains('max_capacity')
    def _check_capacity(self):
        """التحقق من السعة"""
        for record in self:
            if record.max_capacity <= 0:
                raise ValidationError('عدد المقاعد يجب أن يكون أكبر من صفر!')

    @api.constrains('price')
    def _check_price(self):
        """التحقق من السعر"""
        for record in self:
            if record.price <= 0:
                raise ValidationError('سعر الورشة يجب أن يكون أكبر من صفر!')

    def name_get(self):
        """تخصيص طريقة عرض اسم الورشة"""
        result = []
        for record in self:
            name = record.name
            if record.department_id:
                name = f"{record.department_id.name} / {name}"
            result.append((record.id, name))
        return result

    def action_view_enrollments(self):
        """عرض المشتركات في الورشة"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'مشتركات {self.name}',
            'view_mode': 'list,form',
            'res_model': 'charity.booking.registrations',
            'domain': [('workshop_id', '=', self.id)],
            'context': {
                'default_workshop_id': self.id,
                'default_department_id': self.department_id.id,
                'default_booking_mode': 'workshop'
            }
        }