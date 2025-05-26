# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta
from dateutil.relativedelta import relativedelta


class PlayerSubscription(models.Model):
    _name = 'player.subscription'
    _description = 'اشتراك اللاعب'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'start_date desc'

    display_name = fields.Char(
        string='الاسم',
        compute='_compute_display_name',
        store=True
    )

    player_id = fields.Many2one(
        'club.player',
        string='اللاعب',
        required=True,
        tracking=True,
        ondelete='restrict'
    )

    sport_id = fields.Many2one(
        'club.sport',
        string='اللعبة',
        required=True,
        tracking=True,
        ondelete='restrict'
    )

    start_date = fields.Date(
        string='تاريخ البداية',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )

    end_date = fields.Date(
        string='تاريخ الانتهاء',
        compute='_compute_end_date',
        store=True,
        readonly=False,
        tracking=True
    )

    duration_months = fields.Integer(
        string='مدة الاشتراك (بالشهور)',
        related='sport_id.subscription_duration',
        readonly=True
    )

    subscription_period = fields.Selection([
        ('1', 'شهر'),
        ('3', '3 شهور'),
        ('6', '6 شهور'),
        ('12', 'سنة')
    ], string='فترة الاشتراك', default='3')

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('active', 'نشط'),
        ('expired', 'منتهي'),
        ('cancelled', 'ملغي'),
        ('renewed', 'مجدد')
    ], string='الحالة', default='draft', tracking=True)

    payment_state = fields.Selection([
        ('unpaid', 'غير مدفوع'),
        ('partial', 'مدفوع جزئياً'),
        ('paid', 'مدفوع')
    ], string='حالة السداد', default='unpaid', tracking=True)

    subscription_fee = fields.Monetary(
        string='رسوم الاشتراك',
        related='sport_id.subscription_fee',
        readonly=True,
        store=True
    )

    paid_amount = fields.Monetary(
        string='المبلغ المدفوع',
        default=0.0,
        tracking=True
    )

    remaining_amount = fields.Monetary(
        string='المبلغ المتبقي',
        compute='_compute_remaining_amount',
        store=True
    )

    parent_id = fields.Many2one(
        'club.parent',
        string='ولي الأمر',
        related='player_id.parent_id',
        store=True,
        readonly=True
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

    days_to_expire = fields.Integer(
        string='أيام حتى الانتهاء',
        compute='_compute_days_to_expire',
        store=True
    )

    is_expiring_soon = fields.Boolean(
        string='قرب الانتهاء',
        compute='_compute_days_to_expire',
        store=True
    )

    active = fields.Boolean(
        string='نشط',
        default=True
    )

    source_request_id = fields.Many2one(
        'subscription.request',
        string='طلب الاشتراك المصدر',
        readonly=True,
        help='الطلب الذي أنشأ هذا الاشتراك'
    )

    subscription_period = fields.Selection([
        ('1', 'شهر'),
        ('3', '3 شهور'),
        ('6', '6 شهور'),
        ('12', 'سنة')
    ], string='فترة الاشتراك', default='3')

    @api.depends('player_id', 'sport_id')
    def _compute_display_name(self):
        for record in self:
            if record.player_id and record.sport_id:
                record.display_name = f"{record.player_id.name} - {record.sport_id.name}"
            else:
                record.display_name = _('اشتراك جديد')

    @api.depends('start_date', 'subscription_period')
    def _compute_end_date(self):
        for record in self:
            if record.start_date and record.subscription_period:
                months = int(record.subscription_period)
                record.end_date = record.start_date + relativedelta(months=months)
            else:
                record.end_date = False

    @api.depends('subscription_fee', 'paid_amount')
    def _compute_remaining_amount(self):
        for record in self:
            record.remaining_amount = record.subscription_fee - record.paid_amount

    @api.depends('end_date', 'state')
    def _compute_days_to_expire(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.end_date and record.state == 'active':
                delta = record.end_date - today
                record.days_to_expire = delta.days
                record.is_expiring_soon = 0 <= delta.days <= 7
            else:
                record.days_to_expire = 0
                record.is_expiring_soon = False

    @api.constrains('player_id', 'sport_id', 'start_date', 'end_date')
    def _check_overlap(self):
        for record in self:
            if record.state == 'cancelled':
                continue

            domain = [
                ('player_id', '=', record.player_id.id),
                ('sport_id', '=', record.sport_id.id),
                ('id', '!=', record.id),
                ('state', 'not in', ['cancelled', 'expired'])
            ]

            overlapping = self.search(domain)
            for overlap in overlapping:
                if (record.start_date <= overlap.end_date and
                        record.end_date >= overlap.start_date):
                    raise ValidationError(
                        _('يوجد اشتراك نشط للاعب %s في لعبة %s خلال هذه الفترة!') %
                        (record.player_id.name, record.sport_id.name)
                    )

    def action_activate(self):
        for record in self:
            if record.payment_state == 'unpaid':
                raise ValidationError(_('لا يمكن تفعيل الاشتراك قبل السداد!'))
            record.state = 'active'

    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'

    def action_renew(self):
        for record in self:
            new_subscription = record.copy({
                'start_date': record.end_date + timedelta(days=1),
                'state': 'draft',
                'payment_state': 'unpaid',
                'paid_amount': 0.0,
            })
            record.state = 'renewed'
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'player.subscription',
                'res_id': new_subscription.id,
                'view_mode': 'form',
                'target': 'current',
            }

    @api.model
    def _cron_check_expired_subscriptions(self):
        """مهمة مجدولة للتحقق من الاشتراكات المنتهية"""
        today = fields.Date.context_today(self)
        expired_subscriptions = self.search([
            ('state', '=', 'active'),
            ('end_date', '<', today)
        ])
        expired_subscriptions.write({'state': 'expired'})

    def action_view_payments(self):
        """عرض المدفوعات المرتبطة بهذا الاشتراك"""
        self.ensure_one()

        # البحث عن السندات التي تحتوي على هذا الاشتراك
        receipt_lines = self.env['payment.receipt.line'].search([
            ('subscription_id', '=', self.id)
        ])
        receipt_ids = receipt_lines.mapped('receipt_id').ids

        return {
            'type': 'ir.actions.act_window',
            'name': 'المدفوعات',
            'view_mode': 'list,form',
            'res_model': 'payment.receipt',
            'domain': [('id', 'in', receipt_ids)],
            'context': {}
        }

    def action_make_payment(self):
        """فتح معالج الدفع"""
        self.ensure_one()

        if self.remaining_amount <= 0:
            raise ValidationError(_('لا يوجد مبلغ مستحق للدفع.'))

        return {
            'type': 'ir.actions.act_window',
            'name': 'دفع الاشتراك',
            'res_model': 'payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_subscription_id': self.id,
                'default_amount_to_pay': self.remaining_amount,
            }
        }