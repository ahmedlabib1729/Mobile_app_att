# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PaymentReceipt(models.Model):
    _name = 'payment.receipt'
    _description = 'سند قبض'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date desc, name desc'

    name = fields.Char(
        string='رقم السند',
        required=True,
        copy=False,
        readonly=True,
        default='جديد'
    )

    date = fields.Date(
        string='التاريخ',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )

    parent_id = fields.Many2one(
        'club.parent',
        string='ولي الأمر',
        required=True,
        tracking=True
    )

    amount_total = fields.Monetary(
        string='إجمالي المبلغ',
        compute='_compute_amount_total',
        store=True,
        tracking=True
    )

    payment_method = fields.Selection([
        ('cash', 'نقدي'),
        ('bank', 'تحويل بنكي'),
        ('cheque', 'شيك')
    ], string='طريقة الدفع', required=True, default='cash', tracking=True)

    reference = fields.Char(
        string='المرجع',
        help='رقم الشيك أو رقم الحوالة'
    )

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('confirmed', 'مؤكد'),
        ('cancelled', 'ملغي')
    ], string='الحالة', default='draft', tracking=True)

    line_ids = fields.One2many(
        'payment.receipt.line',
        'receipt_id',
        string='تفاصيل السند'
    )

    note = fields.Text(string='ملاحظات')

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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'جديد') == 'جديد':
                vals['name'] = self.env['ir.sequence'].next_by_code('payment.receipt') or 'جديد'
        return super().create(vals_list)

    @api.depends('line_ids.amount')
    def _compute_amount_total(self):
        for record in self:
            record.amount_total = sum(line.amount for line in record.line_ids)

    def action_confirm(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('يمكن تأكيد السندات في حالة المسودة فقط.'))

            if not record.line_ids:
                raise UserError(_('لا يمكن تأكيد سند بدون تفاصيل.'))

            # تحديث الاشتراكات المرتبطة
            for line in record.line_ids:
                if line.subscription_id:
                    subscription = line.subscription_id
                    subscription.paid_amount += line.amount

                    # تحديث حالة السداد
                    if subscription.paid_amount >= subscription.subscription_fee:
                        subscription.payment_state = 'paid'
                    elif subscription.paid_amount > 0:
                        subscription.payment_state = 'partial'

            record.state = 'confirmed'

    def action_cancel(self):
        for record in self:
            if record.state != 'confirmed':
                raise UserError(_('يمكن إلغاء السندات المؤكدة فقط.'))

            # إرجاع المبالغ من الاشتراكات
            for line in record.line_ids:
                if line.subscription_id:
                    subscription = line.subscription_id
                    subscription.paid_amount -= line.amount

                    # تحديث حالة السداد
                    if subscription.paid_amount <= 0:
                        subscription.payment_state = 'unpaid'
                    elif subscription.paid_amount < subscription.subscription_fee:
                        subscription.payment_state = 'partial'

            record.state = 'cancelled'

    def action_print_receipt(self):
        # سيتم تنفيذها لاحقاً لطباعة السند
        return self.env.ref('club.action_report_payment_receipt').report_action(self)

    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        if self.parent_id:
            # جلب الاشتراكات غير المدفوعة بالكامل
            unpaid_subscriptions = self.env['player.subscription'].search([
                ('parent_id', '=', self.parent_id.id),
                ('payment_state', 'in', ['unpaid', 'partial']),
                ('state', 'in', ['draft', 'active'])
            ])

            # إنشاء سطور للاشتراكات
            lines = []
            for sub in unpaid_subscriptions:
                lines.append((0, 0, {
                    'subscription_id': sub.id,
                    'player_id': sub.player_id.id,
                    'sport_id': sub.sport_id.id,
                    'amount': sub.remaining_amount,
                    'description': f"اشتراك {sub.player_id.name} في {sub.sport_id.name}"
                }))

            self.line_ids = lines


class PaymentReceiptLine(models.Model):
    _name = 'payment.receipt.line'
    _description = 'سطر سند القبض'

    receipt_id = fields.Many2one(
        'payment.receipt',
        string='سند القبض',
        required=True,
        ondelete='cascade'
    )

    subscription_id = fields.Many2one(
        'player.subscription',
        string='الاشتراك',
        required=True
    )

    player_id = fields.Many2one(
        'club.player',
        string='اللاعب',
        related='subscription_id.player_id',
        readonly=True,
        store=True
    )

    sport_id = fields.Many2one(
        'club.sport',
        string='اللعبة',
        related='subscription_id.sport_id',
        readonly=True,
        store=True
    )

    amount = fields.Monetary(
        string='المبلغ',
        required=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='receipt_id.currency_id',
        readonly=True
    )

    description = fields.Char(string='الوصف')