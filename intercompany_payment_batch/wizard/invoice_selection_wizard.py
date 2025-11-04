# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class InvoiceSelectionWizard(models.TransientModel):
    _name = 'invoice.selection.wizard'
    _description = 'Invoice Selection Wizard'
    
    batch_id = fields.Many2one(
        'payment.batch',
        string='Payment Batch',
        required=True
    )
    
    paying_company_id = fields.Many2one(
        'res.company',
        string='Paying Company',
        related='batch_id.paying_company_id',
        readonly=True
    )
    
    invoice_ids = fields.Many2many(
        'account.move',
        string='Available Bills',
        domain="[('move_type', '=', 'in_invoice'), ('state', '=', 'posted'), ('payment_state', 'in', ['not_paid', 'partial'])]"
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Filter by Vendor',
        domain="[('supplier_rank', '>', 0)]"
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Filter by Company'
    )
    
    @api.onchange('partner_id', 'company_id')
    def _onchange_filters(self):
        domain = [
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial'])
        ]
        
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
        
        # استبعاد الفواتير الموجودة بالفعل في الدفعة
        existing_invoice_ids = self.batch_id.invoice_line_ids.mapped('invoice_id').ids
        if existing_invoice_ids:
            domain.append(('id', 'not in', existing_invoice_ids))
        
        return {'domain': {'invoice_ids': domain}}
    
    def action_add_invoices(self):
        """إضافة الفواتير المحددة للدفعة"""
        self.ensure_one()
        
        if not self.invoice_ids:
            raise UserError(_('Please select at least one invoice.'))
        
        if self.batch_id.state != 'draft':
            raise UserError(_('Can only add invoices to draft batches.'))
        
        # إضافة الفواتير للدفعة
        for invoice in self.invoice_ids:
            # التحقق من عدم وجود الفاتورة مسبقاً
            existing = self.batch_id.invoice_line_ids.filtered(
                lambda l: l.invoice_id == invoice
            )
            if not existing:
                line_vals = {
                    'batch_id': self.batch_id.id,
                    'invoice_id': invoice.id,
                    'amount': invoice.amount_residual,
                }
                self.env['payment.batch.line'].create(line_vals)
        
        return {'type': 'ir.actions.act_window_close'}
