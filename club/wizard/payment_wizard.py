# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PaymentWizard(models.TransientModel):
    _name = 'payment.wizard'
    _description = 'معالج الدفع'

    subscription_id = fields.Many2one(
        'player.subscription',
        string='الاشتراك',
        required=True
    )

    player_id = fields.Many2one(
        'club.player',
        string='اللاعب',
        related='subscription_id.player_id',
        readonly=True
    )

    parent_id = fields.Many2one(
        'club.parent',
        string='ولي الأمر',
        related='subscription_id.parent_id',
        readonly=True
    )

    sport_id = fields.Many2one(
        'club.sport',
        string='اللعبة',
        related='subscription_id.sport_id',
        readonly=True
    )

    amount_due = fields.Monetary(
        string='المبلغ المستحق',
        related='subscription_id.remaining_amount',
        readonly=True
    )

    amount_to_pay = fields.Monetary(
        string='المبلغ المدفوع',
        required=True
    )

    payment_method = fields.Selection([
        ('cash', 'نقدي'),
        ('bank', 'تحويل بنكي'),
        ('cheque', 'شيك')
    ], string='طريقة الدفع', required=True, default='cash')

    payment_date = fields.Date(
        string='تاريخ الدفع',
        required=True,
        default=fields.Date.context_today
    )

    reference = fields.Char(
        string='المرجع',
        help='رقم الشيك أو رقم الحوالة'
    )

    note = fields.Text(string='ملاحظات')

    currency_id = fields.Many2one(
        'res.currency',
        related='subscription_id.currency_id',
        readonly=True
    )

    @api.onchange('amount_due')
    def _onchange_amount_due(self):
        self.amount_to_pay = self.amount_due

    @api.constrains('amount_to_pay')
    def _check_amount(self):
        for record in self:
            if record.amount_to_pay <= 0:
                raise UserError(_('المبلغ المدفوع يجب أن يكون أكبر من صفر.'))
            if record.amount_to_pay > record.amount_due:
                raise UserError(_('المبلغ المدفوع لا يمكن أن يكون أكبر من المبلغ المستحق.'))

    def action_create_payment(self):
        self.ensure_one()

        # البحث عن سند مفتوح لنفس ولي الأمر
        existing_draft = self.env['payment.receipt'].search([
            ('parent_id', '=', self.parent_id.id),
            ('state', '=', 'draft'),
            ('date', '=', self.payment_date)
        ], limit=1)

        if existing_draft:
            # إضافة سطر جديد للسند الموجود
            receipt = existing_draft
            self.env['payment.receipt.line'].create({
                'receipt_id': receipt.id,
                'subscription_id': self.subscription_id.id,
                'amount': self.amount_to_pay,
                'description': f"دفعة اشتراك {self.player_id.name} في {self.sport_id.name}"
            })
        else:
            # إنشاء سند جديد
            receipt = self.env['payment.receipt'].create({
                'parent_id': self.parent_id.id,
                'date': self.payment_date,
                'payment_method': self.payment_method,
                'reference': self.reference,
                'note': self.note,
                'line_ids': [(0, 0, {
                    'subscription_id': self.subscription_id.id,
                    'amount': self.amount_to_pay,
                    'description': f"دفعة اشتراك {self.player_id.name} في {self.sport_id.name}"
                })]
            })

        # عرض السند
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'payment.receipt',
            'res_id': receipt.id,
            'view_mode': 'form',
            'target': 'current',
        }