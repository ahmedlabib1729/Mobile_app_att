# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ClubSport(models.Model):
    _name = 'club.sport'
    _description = 'الألعاب الرياضية'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'sequence, name'

    # الحقول الأساسية
    name = fields.Char(
        string='اسم اللعبة',
        required=True,
        tracking=True,
        help='مثال: كرة القدم، كرة السلة، السباحة'
    )

    code = fields.Char(
        string='رمز اللعبة',
        required=True,
        tracking=True,
        help='رمز مختصر للعبة مثل: FOOT, BASKET, SWIM'
    )

    description = fields.Text(
        string='وصف اللعبة',
        help='وصف تفصيلي عن اللعبة والمهارات المطلوبة'
    )

    sport_type = fields.Selection([
        ('individual', 'فردية'),
        ('team', 'جماعية')
    ], string='نوع اللعبة', required=True, default='team', tracking=True)

    image = fields.Image(
        string='صورة اللعبة',
        max_width=1024,
        max_height=1024,
        help='صورة أو أيقونة تمثل اللعبة'
    )

    active = fields.Boolean(
        string='نشطة',
        default=True,
        tracking=True,
        help='حدد ما إذا كانت اللعبة متاحة حالياً'
    )

    sequence = fields.Integer(
        string='الترتيب',
        default=10,
        help='يستخدم لترتيب الألعاب في القوائم'
    )

    # حقول مالية
    subscription_fee = fields.Monetary(
        string='رسوم الاشتراك',
        required=True,
        tracking=True,
        help='رسوم الاشتراك الشهرية أو الدورية'
    )

    has_uniform_cost = fields.Boolean(
        string='يوجد تكلفة للزي الرياضي؟',
        default=True,
        help='حدد إذا كانت هذه اللعبة تتطلب شراء زي رياضي'
    )

    uniform_cost = fields.Monetary(
        string='تكلفة الزي الرياضي',
        tracking=True,
        help='تكلفة الزي الرياضي المطلوب للعبة'
    )

    subscription_duration = fields.Integer(
        string='مدة الاشتراك (بالشهور)',
        default=3,
        required=True,
        help='المدة الافتراضية للاشتراك بالشهور'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='العملة',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        default=lambda self: self.env.company
    )

    # حقول الموظفين
    coach_id = fields.Many2one(
        'hr.employee',
        string='المدرب الرئيسي',
        tracking=True
    )

    assistant_coach_ids = fields.Many2many(
        'hr.employee',
        'sport_assistant_coach_rel',
        'sport_id',
        'employee_id',
        string='المدربين المساعدين'
    )

    # حقول الإحصائيات (محسوبة)
    registered_players_count = fields.Integer(
        string='عدد اللاعبين المسجلين',
        compute='_compute_statistics',
        store=True,
        help='العدد الإجمالي للاعبين المسجلين في هذه اللعبة'
    )

    active_classes_count = fields.Integer(
        string='عدد الفصول النشطة',
        compute='_compute_statistics',
        store=True,
        help='عدد الفصول أو المجموعات التدريبية النشطة'
    )

    total_revenue = fields.Monetary(
        string='إجمالي الإيرادات',
        compute='_compute_statistics',
        store=True,
        help='إجمالي الإيرادات من هذه اللعبة'
    )

    # العلاقات
    player_ids = fields.Many2many(
        'club.player',
        'player_sport_rel',
        'sport_id',
        'player_id',
        string='اللاعبين المسجلين',
        compute='_compute_players',
        store=False
    )

    subscription_ids = fields.One2many(
        'player.subscription',
        'sport_id',
        string='الاشتراكات'
    )

    active_subscription_ids = fields.One2many(
        'player.subscription',
        'sport_id',
        string='الاشتراكات النشطة',
        domain=[('state', '=', 'active')]
    )

    monthly_fee = fields.Monetary(
        string='الرسوم الشهرية',
        compute='_compute_monthly_fee',
        store=True,
        help='الرسوم الشهرية المحسوبة'
    )

    @api.depends('player_ids', 'player_ids.active')
    def _compute_statistics(self):
        for record in self:
            # حساب عدد اللاعبين النشطين
            record.registered_players_count = len(record.player_ids.filtered('active'))

            # حساب إجمالي الإيرادات
            record.total_revenue = record.registered_players_count * record.subscription_fee

            # عدد الفصول النشطة (سيتم تحديثه لاحقاً عند إضافة نموذج الفصول)
            record.active_classes_count = 0

    @api.depends('active_subscription_ids.player_id')
    def _compute_players(self):
        for record in self:
            record.player_ids = record.active_subscription_ids.mapped('player_id')

    @api.depends('subscription_fee', 'subscription_duration')
    def _compute_monthly_fee(self):
        for record in self:
            if record.subscription_duration and record.subscription_duration > 0:
                record.monthly_fee = record.subscription_fee / record.subscription_duration
            else:
                record.monthly_fee = record.subscription_fee

    @api.constrains('code')
    def _check_code_unique(self):
        for record in self:
            if record.code:
                # التحقق من أن الكود يحتوي على أحرف وأرقام فقط
                clean_code = record.code.upper().strip()
                if not clean_code.replace('_', '').isalnum():
                    raise ValidationError(_('رمز اللعبة يجب أن يحتوي على أحرف وأرقام فقط!'))

                # التحقق من عدم التكرار
                existing = self.search([
                    ('code', '=ilike', clean_code),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_('رمز اللعبة "%s" موجود بالفعل!') % clean_code)

    @api.onchange('code')
    def _onchange_code(self):
        if self.code:
            self.code = self.code.upper().strip()

    @api.onchange('has_uniform_cost')
    def _onchange_has_uniform_cost(self):
        if not self.has_uniform_cost:
            self.uniform_cost = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'code' in vals and vals['code']:
                vals['code'] = vals['code'].upper().strip()
        return super().create(vals_list)

    def write(self, vals):
        if 'code' in vals and vals['code']:
            vals['code'] = vals['code'].upper().strip()
        return super().write(vals)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'رمز اللعبة يجب أن يكون فريد!'),
        ('subscription_fee_positive', 'CHECK(subscription_fee >= 0)', 'رسوم الاشتراك يجب أن تكون قيمة موجبة!'),
        ('uniform_cost_positive', 'CHECK(uniform_cost >= 0)', 'تكلفة الزي الرياضي يجب أن تكون قيمة موجبة!'),
    ]