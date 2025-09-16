# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LadiesProgram(models.Model):
    _name = 'charity.ladies.program'
    _description = 'برامج السيدات'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'department_id, sequence, name'

    # الحقول الأساسية
    name = fields.Char(
        string='اسم البرنامج',
        required=True,
        tracking=True,
        help='أدخل اسم البرنامج'
    )

    department_id = fields.Many2one(
        'charity.departments',
        string='القسم',

        ondelete='cascade',
        domain=[('type', '=', 'ladies')],
        tracking=True,
        help='القسم التابع له البرنامج'
    )

    # معلومات البرنامج
    description = fields.Text(
        string='وصف البرنامج',
        required=True,
        translate=True,
        help='وصف تفصيلي للبرنامج'
    )

    instructor_id = fields.Many2one(
        'res.partner',
        string='المحاضر',
        required=True,
        tracking=True,
        help='المحاضر المسؤول عن البرنامج'
    )

    # الموعد - حقل نصي بسيط
    schedule = fields.Text(
        string='موعد البرنامج',
        required=True,
        help='موعد البرنامج (مثال: كل يوم أحد من 4-6 مساءً)'
    )

    # معلومات إضافية
    max_capacity = fields.Integer(
        string='السعة القصوى',
        default=30,
        help='العدد الأقصى للمشتركات'
    )

    sequence = fields.Integer(
        string='الترتيب',
        default=10,
        help='يستخدم لترتيب البرامج في العرض'
    )

    active = fields.Boolean(
        string='نشط',
        default=True,
        help='إذا تم إلغاء التحديد، سيتم أرشفة البرنامج'
    )

    is_active = fields.Boolean(
        string='مفعل للتسجيل',
        default=True,
        tracking=True,
        help='هل البرنامج مفتوح للتسجيل الجديد'
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        related='department_id.company_id',
        store=True,
        readonly=True
    )

    # الإحصائيات
    enrollment_ids = fields.Many2many(
        'charity.member.subscription',
        'program_subscription_rel',
        'program_id',
        'subscription_id',
        string='الاشتراكات',
        domain=[('state', '=', 'active')]
    )

    enrollments_count = fields.Integer(
        string='عدد المشتركات',
        compute='_compute_enrollments_count',
        help='عدد المشتركات الحاليات'
    )

    available_seats = fields.Integer(
        string='المقاعد المتاحة',
        compute='_compute_available_seats',
        help='عدد المقاعد المتاحة'
    )

    @api.depends('enrollment_ids')
    def _compute_enrollments_count(self):
        """حساب عدد المشتركات"""
        for record in self:
            record.enrollments_count = len(record.enrollment_ids)

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
                raise ValidationError('السعة القصوى يجب أن تكون أكبر من صفر!')

    @api.constrains('name', 'department_id')
    def _check_unique_name(self):
        """التحقق من عدم تكرار اسم البرنامج في نفس القسم"""
        for record in self:
            domain = [
                ('name', '=', record.name),
                ('department_id', '=', record.department_id.id),
                ('id', '!=', record.id)
            ]
            if self.search_count(domain) > 0:
                raise ValidationError('يوجد برنامج آخر بنفس الاسم في هذا القسم!')

    def name_get(self):
        """تخصيص طريقة عرض اسم البرنامج"""
        result = []
        for record in self:
            name = record.name
            if record.department_id:
                name = f"{record.department_id.name} / {name}"
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100):
        """البحث في البرامج"""
        args = args or []
        if name:
            args = ['|', '|',
                    ('name', operator, name),
                    ('department_id.name', operator, name),
                    ('instructor_id.name', operator, name)] + args
        return self._search(args, limit=limit)

    def action_view_enrollments(self):
        """عرض المشتركات في البرنامج"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'مشتركات {self.name}',
            'view_mode': 'list,form',
            'res_model': 'charity.member.subscription',
            'domain': [('program_ids', 'in', self.id)],
            'context': {
                'default_program_ids': [(4, self.id)],
                'default_department_id': self.department_id.id
            }
        }