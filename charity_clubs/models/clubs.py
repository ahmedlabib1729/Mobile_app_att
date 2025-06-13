# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, time


class CharityClubs(models.Model):
    _name = 'charity.clubs'
    _description = 'نوادي الأقسام'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'department_id, sequence, name'

    # الحقول الأساسية
    name = fields.Char(
        string='اسم النادي',
        required=True,
        tracking=True,
        help='أدخل اسم النادي'
    )

    department_id = fields.Many2one(
        'charity.departments',
        string='القسم',
        required=True,
        ondelete='cascade',
        domain=[('type', '=', 'clubs')],
        tracking=True,
        help='القسم التابع له النادي'
    )

    goal = fields.Text(
        string='الهدف',
        required=True,
        help='الهدف من النادي'
    )

    content = fields.Html(
        string='المحتوى',
        required=True,
        help='محتوى النادي والأنشطة'
    )

    # حقول الوقت
    time_from = fields.Float(
        string='الوقت من',
        required=True,
        help='وقت بداية النادي'
    )

    time_to = fields.Float(
        string='الوقت إلى',
        required=True,
        help='وقت نهاية النادي'
    )

    # حقول العمر
    age_from = fields.Integer(
        string='العمر من',
        required=True,
        default=5,
        help='الحد الأدنى للعمر'
    )

    age_to = fields.Integer(
        string='العمر إلى',
        required=True,
        default=18,
        help='الحد الأقصى للعمر'
    )

    # نوع النادي (ذكور/إناث/مختلط)
    gender_type = fields.Selection([
        ('male', 'ذكور'),
        ('female', 'إناث'),
        ('both', 'مختلط')
    ], string='نوع المستفيدين',
        required=True,
        default='both',
        tracking=True,
        help='حدد نوع المستفيدين المسموح لهم بالتسجيل'
    )

    # حقول إضافية
    sequence = fields.Integer(
        string='الترتيب',
        default=10,
        help='يستخدم لترتيب النوادي في العرض'
    )

    active = fields.Boolean(
        string='نشط',
        default=True,
        help='إذا تم إلغاء التحديد، سيتم أرشفة النادي'
    )

    is_active = fields.Boolean(
        string='مفعل للتسجيل',
        default=True,
        tracking=True,
        help='هل النادي مفتوح للتسجيل الجديد'
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        related='department_id.company_id',
        store=True,
        readonly=True
    )

    # العلاقات
    term_ids = fields.One2many(
        'charity.club.terms',
        'club_id',
        string='الترمات',
        help='ترمات النادي'
    )

    # Computed fields
    terms_count = fields.Integer(
        string='عدد الترمات',
        compute='_compute_terms_count',
        help='عدد الترمات في هذا النادي'
    )

    active_terms_count = fields.Integer(
        string='الترمات النشطة',
        compute='_compute_active_terms_count',
        help='عدد الترمات النشطة للتسجيل'
    )

    registrations_count = fields.Integer(
        string='عدد التسجيلات',
        compute='_compute_registrations_count',
        help='إجمالي التسجيلات في هذا النادي'
    )

    total_revenue = fields.Float(
        string='إجمالي الإيرادات',
        compute='_compute_total_revenue',
        digits=(10, 2),
        help='إجمالي الإيرادات من هذا النادي'
    )

    # حقل مساعد لعرض الوقت
    time_display = fields.Char(
        string='أوقات النادي',
        compute='_compute_time_display',
        help='عرض أوقات النادي'
    )

    age_range_display = fields.Char(
        string='الفئة العمرية',
        compute='_compute_age_range_display',
        help='عرض الفئة العمرية'
    )

    @api.depends('term_ids')
    def _compute_terms_count(self):
        """حساب عدد الترمات"""
        for record in self:
            record.terms_count = len(record.term_ids)

    @api.depends('term_ids.is_active')
    def _compute_active_terms_count(self):
        """حساب عدد الترمات النشطة"""
        for record in self:
            record.active_terms_count = len(record.term_ids.filtered('is_active'))

    @api.depends('name')
    def _compute_registrations_count(self):
        """حساب عدد التسجيلات"""
        for record in self:
            # سيتم تحديث هذا لاحقاً عند إضافة موديل التسجيلات
            record.registrations_count = 0

    @api.depends('name')
    def _compute_total_revenue(self):
        """حساب إجمالي الإيرادات"""
        for record in self:
            # سيتم تحديث هذا لاحقاً بناءً على التسجيلات الفعلية
            record.total_revenue = 0.0

    @api.depends('time_from', 'time_to')
    def _compute_time_display(self):
        """عرض الوقت بصيغة مقروءة"""
        for record in self:
            from_time = '{:02.0f}:{:02.0f}'.format(*divmod(record.time_from * 60, 60))
            to_time = '{:02.0f}:{:02.0f}'.format(*divmod(record.time_to * 60, 60))
            record.time_display = f"{from_time} - {to_time}"

    @api.depends('age_from', 'age_to')
    def _compute_age_range_display(self):
        """عرض الفئة العمرية"""
        for record in self:
            record.age_range_display = f"من {record.age_from} إلى {record.age_to} سنة"

    # Constraints
    @api.constrains('time_from', 'time_to')
    def _check_time(self):
        """التحقق من صحة الوقت"""
        for record in self:
            if record.time_from >= record.time_to:
                raise ValidationError('وقت البداية يجب أن يكون قبل وقت النهاية!')
            if record.time_from < 0 or record.time_from >= 24:
                raise ValidationError('وقت البداية غير صحيح!')
            if record.time_to < 0 or record.time_to > 24:
                raise ValidationError('وقت النهاية غير صحيح!')

    @api.constrains('age_from', 'age_to')
    def _check_age_range(self):
        """التحقق من صحة الفئة العمرية"""
        for record in self:
            if record.age_from < 0:
                raise ValidationError('العمر لا يمكن أن يكون سالباً!')
            if record.age_from >= record.age_to:
                raise ValidationError('العمر الأدنى يجب أن يكون أقل من العمر الأقصى!')
            if record.age_to > 100:
                raise ValidationError('العمر الأقصى لا يمكن أن يتجاوز 100 سنة!')

    @api.constrains('name', 'department_id')
    def _check_unique_name(self):
        """التحقق من عدم تكرار اسم النادي في نفس القسم"""
        for record in self:
            domain = [
                ('name', '=', record.name),
                ('department_id', '=', record.department_id.id),
                ('id', '!=', record.id)
            ]
            if self.search_count(domain) > 0:
                raise ValidationError('يوجد نادي آخر بنفس الاسم في هذا القسم!')

    def name_get(self):
        """تخصيص طريقة عرض اسم النادي"""
        result = []
        for record in self:
            name = record.name
            if record.department_id:
                name = f"{record.department_id.name} / {name}"
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100):
        """البحث في النوادي"""
        args = args or []
        if name:
            args = ['|', ('name', operator, name),
                    ('department_id.name', operator, name)] + args
        return self._search(args, limit=limit)

    def action_view_terms(self):
        """فتح قائمة الترمات"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'ترمات {self.name}',
            'view_mode': 'tree,form',
            'res_model': 'charity.club.terms',
            'domain': [('club_id', '=', self.id)],
            'context': {'default_club_id': self.id}
        }

    def action_view_registrations(self):
        """فتح قائمة التسجيلات"""
        self.ensure_one()
        # سيتم تحديث هذا لاحقاً عند إضافة موديل التسجيلات
        return {
            'type': 'ir.actions.act_window',
            'name': f'تسجيلات {self.name}',
            'view_mode': 'tree,form',
            'res_model': 'charity.registrations',
            'domain': [('club_id', '=', self.id)],
            'context': {'default_club_id': self.id}
        }


class CharityClubTerms(models.Model):
    _name = 'charity.club.terms'
    _description = 'ترمات النوادي'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'club_id, date_from'

    name = fields.Char(
        string='اسم الترم',
        required=True,
        tracking=True,
        help='اسم الترم (مثال: الترم الأول 2024)'
    )

    club_id = fields.Many2one(
        'charity.clubs',
        string='النادي',
        required=True,
        ondelete='cascade',
        tracking=True,
        help='النادي التابع له الترم'
    )

    date_from = fields.Date(
        string='تاريخ البداية',
        required=True,
        tracking=True,
        help='تاريخ بداية الترم'
    )

    date_to = fields.Date(
        string='تاريخ النهاية',
        required=True,
        tracking=True,
        help='تاريخ نهاية الترم'
    )

    price = fields.Float(
        string='سعر الترم',
        required=True,
        digits=(10, 2),
        tracking=True,
        help='سعر التسجيل في الترم'
    )

    max_capacity = fields.Integer(
        string='السعة القصوى',
        default=30,
        help='العدد الأقصى للمسجلين في الترم'
    )

    is_active = fields.Boolean(
        string='مفتوح للتسجيل',
        default=True,
        tracking=True,
        help='هل الترم مفتوح للتسجيل الجديد'
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        related='club_id.company_id',
        store=True,
        readonly=True
    )

    # Computed fields
    registrations_count = fields.Integer(
        string='عدد المسجلين',
        compute='_compute_registrations_count',
        help='عدد المسجلين في هذا الترم'
    )

    available_seats = fields.Integer(
        string='المقاعد المتاحة',
        compute='_compute_available_seats',
        help='عدد المقاعد المتاحة للتسجيل'
    )

    state = fields.Selection([
        ('upcoming', 'قادم'),
        ('ongoing', 'جاري'),
        ('finished', 'منتهي')
    ], string='الحالة',
        compute='_compute_state',
        store=True,
        help='حالة الترم'
    )

    @api.depends('name')
    def _compute_registrations_count(self):
        """حساب عدد المسجلين"""
        for record in self:
            # سيتم تحديث هذا لاحقاً عند إضافة موديل التسجيلات
            record.registrations_count = 0

    @api.depends('registrations_count', 'max_capacity')
    def _compute_available_seats(self):
        """حساب المقاعد المتاحة"""
        for record in self:
            record.available_seats = record.max_capacity - record.registrations_count

    @api.depends('date_from', 'date_to')
    def _compute_state(self):
        """حساب حالة الترم"""
        today = fields.Date.today()
        for record in self:
            if record.date_from and record.date_to:
                if today < record.date_from:
                    record.state = 'upcoming'
                elif today > record.date_to:
                    record.state = 'finished'
                else:
                    record.state = 'ongoing'
            else:
                record.state = False

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """التحقق من صحة التواريخ"""
        for record in self:
            if record.date_from >= record.date_to:
                raise ValidationError('تاريخ البداية يجب أن يكون قبل تاريخ النهاية!')

    @api.constrains('price')
    def _check_price(self):
        """التحقق من السعر"""
        for record in self:
            if record.price < 0:
                raise ValidationError('السعر لا يمكن أن يكون سالباً!')

    @api.constrains('max_capacity')
    def _check_capacity(self):
        """التحقق من السعة"""
        for record in self:
            if record.max_capacity <= 0:
                raise ValidationError('السعة القصوى يجب أن تكون أكبر من صفر!')

    @api.constrains('club_id', 'date_from', 'date_to')
    def _check_overlapping_terms(self):
        """التحقق من عدم تداخل الترمات"""
        for record in self:
            domain = [
                ('club_id', '=', record.club_id.id),
                ('id', '!=', record.id),
                '|',
                '&', ('date_from', '<=', record.date_from), ('date_to', '>=', record.date_from),
                '&', ('date_from', '<=', record.date_to), ('date_to', '>=', record.date_to)
            ]
            if self.search_count(domain) > 0:
                raise ValidationError('يوجد ترم آخر متداخل في نفس الفترة!')

    def name_get(self):
        """تخصيص طريقة عرض اسم الترم"""
        result = []
        for record in self:
            name = f"{record.name} ({record.date_from} - {record.date_to})"
            result.append((record.id, name))
        return result