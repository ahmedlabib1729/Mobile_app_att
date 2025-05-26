# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MembershipType(models.Model):
    _name = 'club.membership.type'
    _description = 'أنواع العضويات'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(
        string='اسم العضوية',
        required=True,
        tracking=True
    )

    code = fields.Char(
        string='الرمز',
        required=True,
        help="رمز مختصر لنوع العضوية"
    )

    description = fields.Text(
        string='الوصف',
        help="وصف تفصيلي لمزايا العضوية"
    )

    sequence = fields.Integer(
        string='الترتيب',
        default=10
    )

    active = fields.Boolean(
        string='نشط',
        default=True
    )

    # التسعير
    duration_type = fields.Selection([
        ('days', 'أيام'),
        ('months', 'شهور'),
        ('years', 'سنوات')
    ], string='نوع المدة', required=True, default='months')

    duration_value = fields.Integer(
        string='قيمة المدة',
        default=1,
        help="عدد الأيام/الشهور/السنوات"
    )

    price = fields.Float(
        string='السعر',
        required=True,
        help="السعر الأساسي للعضوية"
    )

    # المزايا والقيود
    max_freeze_days = fields.Integer(
        string='أقصى عدد أيام التجميد',
        default=30,
        help="الحد الأقصى لعدد أيام تجميد العضوية في السنة"
    )

    allow_guest = fields.Boolean(
        string='السماح بإحضار ضيوف',
        default=False
    )

    guest_limit = fields.Integer(
        string='عدد الضيوف المسموح',
        default=0
    )

    facilities_ids = fields.Many2many(
        'club.facility',
        string='المرافق المتاحة',
        help="المرافق التي يمكن للعضو استخدامها"
    )

    # الخصومات
    discount_percentage = fields.Float(
        string='نسبة الخصم للتجديد المبكر %',
        default=0.0,
        help="نسبة الخصم عند التجديد قبل انتهاء العضوية"
    )

    family_discount = fields.Float(
        string='خصم العائلة %',
        default=0.0,
        help="نسبة الخصم للعضو الثاني والثالث من نفس العائلة"
    )

    # القواعد
    auto_renew = fields.Boolean(
        string='تجديد تلقائي',
        default=False,
        help="تجديد العضوية تلقائياً عند الانتهاء"
    )

    renewal_reminder_days = fields.Integer(
        string='تذكير التجديد (أيام)',
        default=30,
        help="عدد الأيام قبل الانتهاء لإرسال تذكير التجديد"
    )

    # الألوان للواجهة
    color = fields.Integer(
        string='اللون',
        default=1
    )

    # الإحصائيات
    member_count = fields.Integer(
        string='عدد الأعضاء',
        compute='_compute_member_count',
        store=True
    )

    @api.depends('membership_ids')
    def _compute_member_count(self):
        for record in self:
            record.member_count = self.env['club.membership'].search_count([
                ('membership_type_id', '=', record.id),
                ('state', '=', 'active')
            ])

    membership_ids = fields.One2many(
        'club.membership',
        'membership_type_id',
        string='العضويات'
    )

    @api.constrains('duration_value')
    def _check_duration_value(self):
        for record in self:
            if record.duration_value <= 0:
                raise ValidationError("قيمة المدة يجب أن تكون أكبر من صفر!")

    @api.constrains('price')
    def _check_price(self):
        for record in self:
            if record.price < 0:
                raise ValidationError("السعر لا يمكن أن يكون سالباً!")

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'الرمز يجب أن يكون فريداً!'),
    ]

    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.code}] {record.name}"
            result.append((record.id, name))
        return result