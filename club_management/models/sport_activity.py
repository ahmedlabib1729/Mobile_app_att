# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SportActivity(models.Model):
    _name = 'club.sport.activity'
    _description = 'الأنشطة الرياضية'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(
        string='اسم النشاط',
        required=True,
        tracking=True
    )

    code = fields.Char(
        string='الرمز',
        required=True,
        help="رمز مختصر للنشاط الرياضي"
    )

    description = fields.Text(
        string='الوصف',
        help="وصف تفصيلي للنشاط الرياضي"
    )

    activity_type = fields.Selection([
        ('individual', 'فردي'),
        ('team', 'جماعي'),
        ('fitness', 'لياقة بدنية'),
        ('combat', 'قتالي'),
        ('water', 'مائي'),
        ('other', 'أخرى')
    ], string='نوع النشاط', default='individual', required=True)

    sequence = fields.Integer(
        string='الترتيب',
        default=10
    )

    active = fields.Boolean(
        string='نشط',
        default=True
    )

    # الصورة
    image = fields.Binary(
        string='صورة النشاط',
        attachment=True
    )

    color = fields.Integer(
        string='اللون',
        default=1
    )

    # القواعد والشروط
    min_age = fields.Integer(
        string='الحد الأدنى للعمر',
        default=0,
        help="الحد الأدنى لعمر المشترك"
    )

    max_age = fields.Integer(
        string='الحد الأقصى للعمر',
        default=100,
        help="الحد الأقصى لعمر المشترك (0 = بدون حد)"
    )

    gender = fields.Selection([
        ('all', 'الكل'),
        ('male', 'ذكور فقط'),
        ('female', 'إناث فقط')
    ], string='الجنس', default='all')

    # التسعير
    registration_fee = fields.Float(
        string='رسوم التسجيل',
        default=0.0,
        help="رسوم التسجيل لمرة واحدة"
    )

    monthly_fee = fields.Float(
        string='الرسوم الشهرية',
        default=0.0,
        help="الرسوم الشهرية للنشاط"
    )

    session_fee = fields.Float(
        string='رسوم الحصة',
        default=0.0,
        help="رسوم الحصة الواحدة"
    )

    # المعدات والمتطلبات
    required_equipment = fields.Text(
        string='المعدات المطلوبة',
        help="قائمة بالمعدات المطلوبة للمشاركة"
    )

    medical_clearance_required = fields.Boolean(
        string='يتطلب تصريح طبي',
        default=False
    )

    # القدرة الاستيعابية
    max_capacity = fields.Integer(
        string='الحد الأقصى للمشتركين',
        default=0,
        help="0 = بدون حد"
    )

    # المرافق المطلوبة
    facility_ids = fields.Many2many(
        'club.facility',
        string='المرافق المطلوبة',
        help="المرافق التي يحتاجها هذا النشاط"
    )

    # المستويات
    has_levels = fields.Boolean(
        string='له مستويات',
        default=True,
        help="هل هذا النشاط له مستويات (مبتدئ، متوسط، متقدم)"
    )

    # الإحصائيات
    member_count = fields.Integer(
        string='عدد المشتركين',
        compute='_compute_member_count',
        store=True
    )

    @api.depends('member_activity_ids')
    def _compute_member_count(self):
        for record in self:
            record.member_count = self.env['club.member.activity'].search_count([
                ('activity_id', '=', record.id),
                ('state', '=', 'active')
            ])

    # العلاقات
    member_activity_ids = fields.One2many(
        'club.member.activity',
        'activity_id',
        string='اشتراكات الأعضاء'
    )

    instructor_ids = fields.Many2many(
        'res.partner',
        string='المدربون',
        domain="[('is_company', '=', False)]",
        help="المدربون المعتمدون لهذا النشاط"
    )

    @api.constrains('min_age', 'max_age')
    def _check_age_limits(self):
        for record in self:
            if record.min_age < 0:
                raise ValidationError("الحد الأدنى للعمر لا يمكن أن يكون سالباً!")
            if record.max_age > 0 and record.max_age < record.min_age:
                raise ValidationError("الحد الأقصى للعمر يجب أن يكون أكبر من الحد الأدنى!")

    @api.constrains('registration_fee', 'monthly_fee', 'session_fee')
    def _check_fees(self):
        for record in self:
            if record.registration_fee < 0 or record.monthly_fee < 0 or record.session_fee < 0:
                raise ValidationError("الرسوم لا يمكن أن تكون سالبة!")

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'الرمز يجب أن يكون فريداً!'),
    ]

    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.code}] {record.name}"
            result.append((record.id, name))
        return result