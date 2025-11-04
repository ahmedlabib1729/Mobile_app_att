# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PaymentBatchLine(models.Model):
    _name = 'payment.batch.line'
    _description = 'Payment Batch Line'
    _rec_name = 'invoice_id'
    
    batch_id = fields.Many2one(
        'payment.batch',
        string='Batch',
        required=True,
        ondelete='cascade'
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Vendor Bill',
        required=True,
        domain="[('move_type', '=', 'in_invoice'), ('state', '=', 'posted'), ('payment_state', 'in', ['not_paid', 'partial'])]"
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        related='invoice_id.partner_id',
        string='Vendor',
        store=True,
        readonly=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        related='invoice_id.company_id',
        string='Company',
        store=True,
        readonly=True
    )
    
    invoice_date = fields.Date(
        related='invoice_id.invoice_date',
        string='Invoice Date',
        store=True,
        readonly=True
    )
    
    due_date = fields.Date(
        related='invoice_id.invoice_date_due',
        string='Due Date',
        store=True,
        readonly=True
    )
    
    invoice_number = fields.Char(
        related='invoice_id.name',
        string='Invoice Number',
        store=True,
        readonly=True
    )
    
    total_amount = fields.Monetary(
        related='invoice_id.amount_total',
        string='Invoice Total',
        currency_field='currency_id',
        readonly=True
    )
    
    residual_amount = fields.Monetary(
        related='invoice_id.amount_residual',
        string='Amount Due',
        currency_field='currency_id',
        readonly=True
    )
    
    amount = fields.Monetary(
        string='Payment Amount',
        required=True,
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='invoice_id.currency_id',
        string='Currency',
        readonly=True
    )
    
    state = fields.Selection(
        related='batch_id.state',
        string='Batch State',
        readonly=True
    )
    
    generated_move_id = fields.Many2one(
        'account.move',
        string='Generated Entry',
        readonly=True,
        help="The journal entry generated in the target company"
    )
    
    notes = fields.Text(string='Notes')
    
    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        if self.invoice_id:
            self.amount = self.invoice_id.amount_residual
    
    @api.constrains('amount', 'residual_amount')
    def _check_amount(self):
        for line in self:
            if line.amount <= 0:
                raise ValidationError(_('Payment amount must be positive.'))
            if line.amount > line.residual_amount:
                raise ValidationError(_(
                    'Payment amount (%.2f) cannot exceed the amount due (%.2f) for invoice %s'
                ) % (line.amount, line.residual_amount, line.invoice_number))
    
    @api.constrains('invoice_id', 'batch_id')
    def _check_duplicate_invoice(self):
        for line in self:
            duplicate = self.search([
                ('batch_id', '=', line.batch_id.id),
                ('invoice_id', '=', line.invoice_id.id),
                ('id', '!=', line.id)
            ])
            if duplicate:
                raise ValidationError(_(
                    'Invoice %s is already added to this batch.'
                ) % line.invoice_number)
    
    def unlink(self):
        for line in self:
            if line.state not in ('draft', 'cancelled'):
                raise ValidationError(_(
                    'You cannot delete lines from a confirmed or posted batch.'
                ))
        return super().unlink()
