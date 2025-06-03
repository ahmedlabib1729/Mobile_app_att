# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ClubPlayer(models.Model):
    _name = 'club.player'
    _description = 'لاعب النادي'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _sql_constraints = [
        ('id_number_unique', 'UNIQUE(id_number)',
         'رقم الجواز/الهوية موجود بالفعل! يجب أن يكون رقم الجواز فريد لكل لاعب.')
    ]

    name = fields.Char(string='اسم اللاعب', required=True, tracking=True)

    id_number = fields.Char(
        string='رقم الجواز/الهوية',
        required=True,
        tracking=True,
        help='رقم الجواز أو الهوية الوطنية - يجب أن يكون فريد'
    )

    nationality_id = fields.Many2one(
        'res.country',
        string='الجنسية',
        required=True,
        tracking=True
    )

    birth_country_id = fields.Many2one(
        'res.country',
        string='محل الميلاد',
        tracking=True
    )

    birth_date = fields.Date(string='تاريخ الميلاد', tracking=True)

    # إضافة حقل الجنس
    gender = fields.Selection([
        ('male', 'ذكر'),
        ('female', 'أنثى')
    ], string='الجنس', required=True, default='male', tracking=True)

    address = fields.Text(string='العنوان', tracking=True)

    parent_id = fields.Many2one(
        'club.parent',
        string='ولي الأمر',
        tracking=True
    )

    age = fields.Integer(
        string='العمر',
        compute='_compute_age',
        store=True
    )

    active = fields.Boolean(string='نشط', default=True)

    sport_ids = fields.Many2many(
        'club.sport',
        'player_sport_rel',
        'player_id',
        'sport_id',
        string='الألعاب المسجل بها',
        compute='_compute_sports',
        store=False
    )

    subscription_ids = fields.One2many(
        'player.subscription',
        'player_id',
        string='الاشتراكات'
    )

    active_subscription_ids = fields.One2many(
        'player.subscription',
        'player_id',
        string='الاشتراكات النشطة',
        domain=[('state', '=', 'active')]
    )

    total_fees = fields.Monetary(
        string='إجمالي الرسوم',
        compute='_compute_total_fees',
        store=True,
        currency_field='currency_id',
        help='إجمالي رسوم الاشتراك لجميع الألعاب المسجل بها'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='العملة',
        related='company_id.currency_id',
        readonly=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company,
        required=True
    )

    total_remaining = fields.Monetary(
        string='إجمالي المتبقي',
        compute='_compute_total_fees',
        store=True,
        help='إجمالي المبالغ المتبقية من جميع الاشتراكات'
    )

    # إضافة حقل الحالة الصحية
    medical_conditions = fields.Text(
        string='الحالة الصحية',
        help='أي حالات صحية أو حساسية يجب مراعاتها'
    )

    @api.depends('birth_date')
    def _compute_age(self):
        from datetime import date
        for record in self:
            if record.birth_date:
                today = date.today()
                record.age = today.year - record.birth_date.year - (
                        (today.month, today.day) < (record.birth_date.month, record.birth_date.day)
                )
            else:
                record.age = 0

    @api.constrains('id_number')
    def _check_id_number(self):
        for record in self:
            if record.id_number:
                # التحقق من أن رقم الجواز لا يحتوي على مسافات في البداية أو النهاية
                if record.id_number != record.id_number.strip():
                    raise ValidationError(_('رقم الجواز/الهوية لا يجب أن يحتوي على مسافات في البداية أو النهاية.'))

                # التحقق من أن رقم الجواز ليس فارغاً بعد إزالة المسافات
                if not record.id_number.strip():
                    raise ValidationError(_('رقم الجواز/الهوية لا يمكن أن يكون فارغاً.'))

                # التحقق من طول رقم الجواز (مثال: يجب أن يكون على الأقل 5 أحرف)
                if len(record.id_number.strip()) < 5:
                    raise ValidationError(_('رقم الجواز/الهوية يجب أن يكون على الأقل 5 أحرف.'))

    @api.depends('active_subscription_ids.subscription_fee', 'subscription_ids.remaining_amount',
                 'subscription_ids.state')
    def _compute_total_fees(self):
        for record in self:
            active_subs = record.active_subscription_ids
            record.total_fees = sum(sub.subscription_fee for sub in active_subs)

            # حساب المتبقي من جميع الاشتراكات النشطة وغير الملغاة
            unpaid_subs = record.subscription_ids.filtered(
                lambda s: s.state in ['draft', 'active', 'expired'] and s.remaining_amount > 0
            )
            record.total_remaining = sum(sub.remaining_amount for sub in unpaid_subs)

    @api.depends('active_subscription_ids.sport_id')
    def _compute_sports(self):
        for record in self:
            record.sport_ids = record.active_subscription_ids.mapped('sport_id')

    def action_create_subscription(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'اشتراك جديد',
            'view_mode': 'form',
            'res_model': 'player.subscription',
            'context': {
                'default_player_id': self.id,
                'default_parent_id': self.parent_id.id,
            },
            'target': 'new',
        }

    def action_view_unpaid_subscriptions(self):
        """عرض الاشتراكات التي بها مبالغ متبقية"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'الاشتراكات غير المدفوعة',
            'view_mode': 'list,form',
            'res_model': 'player.subscription',
            'domain': [
                ('player_id', '=', self.id),
                ('state', 'in', ['draft', 'active', 'expired']),
                ('remaining_amount', '>', 0)
            ],
            'context': {'default_player_id': self.id}
        }