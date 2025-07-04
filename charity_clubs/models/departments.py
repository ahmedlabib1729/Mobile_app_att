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
        ('ladies', 'قسم سيدات'),
        ('nursery', 'قسم حضانة')
    ], string='نوع القسم',
        required=True,
        default='clubs',
        tracking=True,
        help='حدد نوع القسم: نوادي (مع ترمات) أو سيدات أو حضانة'
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

    # حقول خاصة بأقسام السيدات والحضانة
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

    program_ids = fields.One2many(
        'charity.ladies.program',
        'department_id',
        string='البرامج',
        help='البرامج التابعة لهذا القسم'
    )

    programs_count = fields.Integer(
        string='عدد البرامج',
        compute='_compute_programs_count',
        help='عدد البرامج في هذا القسم'
    )

    nursery_plan_ids = fields.One2many(
        'charity.nursery.plan',
        'department_id',
        string='خطط الحضانة'
    )

    workshop_ids = fields.One2many(
        'charity.ladies.workshop',
        'department_id',
        string='الورش',
        help='الورش التابعة لهذا القسم'
    )

    workshops_count = fields.Integer(
        string='عدد الورش',
        compute='_compute_workshops_count',
        help='عدد الورش في هذا القسم'
    )

    @api.depends('club_ids')
    def _compute_clubs_count(self):
        """حساب عدد النوادي لكل قسم"""
        for record in self:
            if record.type == 'clubs':
                record.clubs_count = len(record.club_ids)
            else:
                record.clubs_count = 0

    @api.depends('program_ids')
    def _compute_programs_count(self):
        """حساب عدد البرامج لكل قسم"""
        for record in self:
            if record.type == 'ladies':
                record.programs_count = len(record.program_ids)
            else:
                record.programs_count = 0


    @api.depends('type', 'club_ids')
    def _compute_registrations_count(self):
        """حساب عدد التسجيلات لكل قسم"""
        ClubRegistrations = self.env['charity.club.registrations']
        BookingRegistrations = self.env['charity.booking.registrations']
        NurseryRegistrations = self.env['nursery.child.registration']

        for record in self:
            if record.type == 'clubs':
                # للنوادي: احسب مجموع تسجيلات كل النوادي
                record.registrations_count = ClubRegistrations.search_count([
                    ('department_id', '=', record.id),
                    ('state', '!=', 'cancelled')
                ])
            elif record.type == 'ladies':
                # للسيدات: احسب الحجوزات
                record.registrations_count = BookingRegistrations.search_count([
                    ('department_id', '=', record.id),
                    ('state', '!=', 'cancelled')
                ])
            elif record.type == 'nursery':
                # للحضانة: احسب تسجيلات الأطفال
                record.registrations_count = NurseryRegistrations.search_count([
                    ('department_id', '=', record.id),
                    ('state', '!=', 'rejected')
                ])
            else:
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
    # في ملف departments.py، ابحث عن هذا الـ constraint وغيره كالتالي:

    @api.constrains('booking_price')
    def _check_booking_price(self):
        """التحقق من سعر الحجز"""
        for record in self:
            # تطبيق القيد فقط على أقسام السيدات (وليس الحضانة)
            if record.type == 'ladies' and record.booking_price <= 0:
                raise ValidationError('سعر الحجز يجب أن يكون أكبر من صفر لأقسام السيدات!')
            # الحضانة لها نظام تسعير مختلف عبر جدول الخطط

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
            if record.type == 'ladies':
                name = f"{name} (سيدات)"
            elif record.type == 'nursery':
                name = f"{name} (حضانة)"
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

        if self.type == 'clubs':
            # أقسام النوادي: عرض تسجيلات النوادي
            return {
                'type': 'ir.actions.act_window',
                'name': f'تسجيلات نوادي {self.name}',
                'view_mode': 'list,form',
                'res_model': 'charity.club.registrations',
                'domain': [('department_id', '=', self.id)],
                'context': {
                    'default_department_id': self.id,
                    'default_headquarters_id': self.headquarters_id.id
                },
                'view_ids': [(5, 0, 0),
                             (0, 0, {'view_mode': 'list',
                                     'view_id': self.env.ref('charity_clubs.view_charity_club_registrations_list').id}),
                             (0, 0, {'view_mode': 'form',
                                     'view_id': self.env.ref('charity_clubs.view_charity_club_registration_form').id})
                             ]
            }
        elif self.type == 'ladies':
            # أقسام السيدات: عرض حجوزات السيدات
            return {
                'type': 'ir.actions.act_window',
                'name': f'حجوزات {self.name} - سيدات',
                'view_mode': 'list,form',
                'res_model': 'charity.booking.registrations',
                'domain': [('department_id', '=', self.id)],
                'context': {
                    'default_department_id': self.id,
                    'default_headquarters_id': self.headquarters_id.id,
                    'default_department_type': 'ladies'
                },
                'view_ids': [(5, 0, 0),
                             (0, 0, {'view_mode': 'list',
                                     'view_id': self.env.ref('charity_clubs.view_charity_ladies_booking_list').id}),
                             (0, 0, {'view_mode': 'form',
                                     'view_id': self.env.ref('charity_clubs.view_charity_ladies_booking_form').id})
                             ]
            }
        elif self.type == 'nursery':
            # أقسام الحضانة: عرض تسجيلات الحضانة الجديدة
            return {
                'type': 'ir.actions.act_window',
                'name': f'تسجيلات {self.name} - حضانة',
                'view_mode': 'list,form',
                'res_model': 'nursery.child.registration',
                'domain': [('department_id', '=', self.id)],
                'context': {
                    'default_department_id': self.id,
                    'default_headquarters_id': self.headquarters_id.id
                },
                'view_ids': [(5, 0, 0),
                             (0, 0, {'view_mode': 'list',
                                     'view_id': self.env.ref('charity_clubs.view_nursery_child_registration_list').id}),
                             (0, 0, {'view_mode': 'form',
                                     'view_id': self.env.ref('charity_clubs.view_nursery_child_registration_form').id})
                             ]
            }
        else:
            return {'type': 'ir.actions.do_nothing'}

    def action_view_programs(self):
        """فتح قائمة البرامج للقسم"""
        self.ensure_one()
        if self.type != 'ladies':
            return {'type': 'ir.actions.do_nothing'}
        return {
            'type': 'ir.actions.act_window',
            'name': f'برامج {self.name}',
            'view_mode': 'list,form',
            'res_model': 'charity.ladies.program',
            'domain': [('department_id', '=', self.id)],
            'context': {'default_department_id': self.id}
        }

    @api.depends('workshop_ids')
    def _compute_workshops_count(self):
        """حساب عدد الورش لكل قسم"""
        for record in self:
            if record.type == 'ladies':
                record.workshops_count = len(record.workshop_ids)
            else:
                record.workshops_count = 0

    def action_view_workshops(self):
        """فتح قائمة الورش للقسم"""
        self.ensure_one()
        if self.type != 'ladies':
            return {'type': 'ir.actions.do_nothing'}
        return {
            'type': 'ir.actions.act_window',
            'name': f'ورش {self.name}',
            'view_mode': 'list,form',
            'res_model': 'charity.ladies.workshop',
            'domain': [('department_id', '=', self.id)],
            'context': {'default_department_id': self.id}
        }