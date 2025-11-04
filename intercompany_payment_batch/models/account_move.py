# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    payment_batch_id = fields.Many2one(
        'payment.batch',
        string='Payment Batch',
        readonly=True,
        help="The payment batch that generated this entry"
    )
    
    is_intercompany_entry = fields.Boolean(
        string='Is Intercompany Entry',
        compute='_compute_is_intercompany',
        store=True
    )
    
    def _compute_is_intercompany(self):
        for move in self:
            move.is_intercompany_entry = bool(move.payment_batch_id)
