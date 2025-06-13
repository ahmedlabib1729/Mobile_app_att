# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CharityDepartments(models.Model):
    _name = 'charity.departments'
    _description = 'أقسام المقرات'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'headquarters_id, sequence, name'

    # الحقول الأساسية
    name = fields.Char(
        string='اسم القسم',
        required=True,
        tracking=True,
        help='أدخل اسم القسم'
    )

    headquarters_id = fields.Many2one(
        'charity.headquarters',
        string='المقر',
        required=True,
        ondelete='cascade',
        tracking=True,
        help='اختر المقر التابع له القسم'
    )

    type = fields.Selection([
        ('clubs', 'قسم نوادي'),
        ('booking', 'قسم حجز')
    ], string='نوع القسم',
        required=True,
        default='clubs',
        tracking=True,
        help='حدد نوع القسم: نوادي (مع ترمات) أو حجز مباشر'
    )

    manager_id = fields.Many2one(
        'res.users',
        string='مدير القسم',
        tracking=True,
        default=lambda self: self.env.user,
        help='اختر مدير القسم'
    )

    description = fields.Html(
        string='وصف القسم',
        help='أدخل وصف تفصيلي عن القسم وأنشطته'
    )

    sequence = fields.Integer(
        string='الترتيب',
        default=10,
        help='يستخدم لترتيب الأقسام في العرض'
    )

    # حقول خاصة بأقسام الحجز
    booking_price = fields.Float(
        string='سعر الحجز',
        digits=(10, 2),
        tracking=True,
        help='السعر الثابت للحجز في هذا القسم'
    )

    # حقول إضافية
    active = fields.Boolean(
        string='نشط',
        default=True,
        help='إذا تم إلغاء التحديد، سيتم أرشفة القسم'
    )

    is_active = fields.Boolean(
        string='مفعل',
        default=True,
        tracking=True,
        help='حالة تفعيل القسم للتسجيل'
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company,
        required=True
    )

    color = fields.Integer(
        string='اللون',
        default=0,
        help='لون البطاقة في عرض Kanban'
    )

    # One2many relationships
    club_ids = fields.One2many(
        'charity.clubs',
        'department_id',
        string='النوادي',
        help='النوادي التابعة لهذا القسم'
    )

    # Computed fields
    clubs_count = fields.Integer(
        string='عدد النوادي',
        compute='_compute_clubs_count',
        help='عدد النوادي في هذا القسم'
    )

    registrations_count = fields.Integer(
        string='عدد التسجيلات',
        compute='_compute_registrations_count',
        help='إجمالي التسجيلات في هذا القسم'
    )

    total_revenue = fields.Float(
        string='إجمالي الإيرادات',
        compute='_compute_total_revenue',
        digits=(10, 2),
        help='إجمالي الإيرادات من هذا القسم'
    )

    @api.depends('club_ids')
    def _compute_clubs_count(self):
        """حساب عدد النوادي لكل قسم"""
        for record in self:
            if record.type == 'clubs':
                record.clubs_count = len(record.club_ids)
            else:
                record.clubs_count = 0

    @api.depends('type')
    def _compute_registrations_count(self):
        """حساب عدد التسجيلات لكل قسم"""
        for record in self:
            # سيتم تحديث هذا لاحقاً عند إضافة موديل التسجيلات
            record.registrations_count = 0

    @api.depends('type', 'booking_price')
    def _compute_total_revenue(self):
        """حساب إجمالي الإيرادات"""
        for record in self:
            # سيتم تحديث هذا لاحقاً بناءً على التسجيلات الفعلية
            record.total_revenue = 0.0

    # Onchange methods
    @api.onchange('type')
    def _onchange_type(self):
        """تنظيف الحقول عند تغيير النوع"""
        if self.type == 'clubs':
            self.booking_price = 0.0

    # Constraints
    @api.constrains('booking_price')
    def _check_booking_price(self):
        """التحقق من سعر الحجز"""
        for record in self:
            if record.type == 'booking' and record.booking_price <= 0:
                raise ValidationError('سعر الحجز يجب أن يكون أكبر من صفر لأقسام الحجز!')

    @api.constrains('name', 'headquarters_id')
    def _check_unique_name(self):
        """التحقق من عدم تكرار اسم القسم في نفس المقر"""
        for record in self:
            domain = [
                ('name', '=', record.name),
                ('headquarters_id', '=', record.headquarters_id.id),
                ('id', '!=', record.id)
            ]
            if self.search_count(domain) > 0:
                raise ValidationError('يوجد قسم آخر بنفس الاسم في هذا المقر!')

    # CRUD methods
    @api.model
    def create(self, vals):
        """Override create method"""
        # يمكن إضافة أي منطق خاص عند إنشاء قسم جديد
        return super(CharityDepartments, self).create(vals)

    def write(self, vals):
        """Override write method"""
        # يمكن إضافة أي منطق خاص عند تحديث القسم
        return super(CharityDepartments, self).write(vals)

    def name_get(self):
        """تخصيص طريقة عرض اسم القسم"""
        result = []
        for record in self:
            name = record.name
            if record.headquarters_id:
                name = f"{record.headquarters_id.name} / {name}"
            if record.type == 'booking':
                name = f"{name} (حجز)"
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100):
        """البحث في الأقسام بالاسم أو المقر"""
        args = args or []
        if name:
            args = ['|', ('name', operator, name),
                    ('headquarters_id.name', operator, name)] + args
        return self._search(args, limit=limit)

    def action_view_clubs(self):
        """فتح قائمة النوادي للقسم"""
        self.ensure_one()
        if self.type != 'clubs':
            return
        # سيتم تحديث هذا لاحقاً عند إضافة موديل النوادي
        return {
            'type': 'ir.actions.act_window',
            'name': f'نوادي {self.name}',
            'view_mode': 'kanban,list,form',
            'res_model': 'charity.clubs',
            'domain': [('department_id', '=', self.id)],
            'context': {'default_department_id': self.id}
        }

    def action_view_registrations(self):
        """فتح قائمة التسجيلات للقسم"""
        self.ensure_one()
        # سيتم تحديث هذا لاحقاً عند إضافة موديل التسجيلات
        return {
            'type': 'ir.actions.act_window',
            'name': f'تسجيلات {self.name}',
            'view_mode': 'tree,form',
            'res_model': 'charity.registrations',
            'domain': [('department_id', '=', self.id)],
            'context': {'default_department_id': self.id}
        }