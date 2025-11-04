# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    payment_batch_id = fields.Many2one(
        'payment.batch',
        string='Payment Batch',
        readonly=True,
        help="The payment batch that generated this payment"
    )
    
    is_batch_payment = fields.Boolean(
        string='Is Batch Payment',
        compute='_compute_is_batch',
        store=True
    )
    
    def _compute_is_batch(self):
        for payment in self:
            payment.is_batch_payment = bool(payment.payment_batch_id)
