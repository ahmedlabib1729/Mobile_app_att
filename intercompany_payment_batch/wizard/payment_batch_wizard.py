# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class PaymentBatchWizard(models.TransientModel):
    _name = 'payment.batch.wizard'
    _description = 'Payment Batch Creation Wizard'
    
    name = fields.Char(
        string='Batch Name',
        default=lambda self: f'BATCH/{datetime.now().strftime("%Y%m%d")}'
    )
    
    date = fields.Date(
        string='Payment Date',
        required=True,
        default=fields.Date.context_today
    )
    
    paying_company_id = fields.Many2one(
        'res.company',
        string='Paying Company',
        required=True,
        default=lambda self: self.env.company,
        help="The central company that will make payments"
    )
    
    payment_journal_id = fields.Many2one(
        'account.journal',
        string='Payment Journal',
        required=True,
        domain="[('type', 'in', ['bank', 'cash']), ('company_id', '=', paying_company_id)]"
    )
    
    partner_ids = fields.Many2many(
        'res.partner',
        string='Vendors',
        domain="[('supplier_rank', '>', 0)]",
        help="Leave empty to include all vendors"
    )
    
    company_ids = fields.Many2many(
        'res.company',
        string='Bill Companies',
        help="Companies to include bills from"
    )
    
    date_from = fields.Date(
        string='Bills From',
        default=lambda self: fields.Date.context_today() - timedelta(days=30)
    )
    
    date_to = fields.Date(
        string='Bills To',
        default=fields.Date.context_today
    )
    
    only_due = fields.Boolean(
        string='Only Due Bills',
        default=True,
        help="Include only bills that are due"
    )
    
    max_amount = fields.Float(
        string='Maximum Amount per Bill',
        help="Leave 0 for no limit"
    )
    
    def action_create_batch(self):
        """إنشاء دفعة جديدة مع الفواتير المحددة"""
        self.ensure_one()
        
        # البحث عن الفواتير
        domain = [
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial'])
        ]
        
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        
        if self.company_ids:
            domain.append(('company_id', 'in', self.company_ids.ids))
        
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))
        
        if self.only_due:
            domain.append(('invoice_date_due', '<=', fields.Date.context_today()))
        
        if self.max_amount > 0:
            domain.append(('amount_residual', '<=', self.max_amount))
        
        invoices = self.env['account.move'].search(domain)
        
        if not invoices:
            raise UserError(_('No bills found matching the criteria.'))
        
        # إنشاء الدفعة
        batch_vals = {
            'name': self.name,
            'date': self.date,
            'paying_company_id': self.paying_company_id.id,
            'payment_journal_id': self.payment_journal_id.id,
            'state': 'draft',
        }
        
        batch = self.env['payment.batch'].create(batch_vals)
        
        # إضافة الفواتير
        for invoice in invoices:
            line_vals = {
                'batch_id': batch.id,
                'invoice_id': invoice.id,
                'amount': invoice.amount_residual,
            }
            self.env['payment.batch.line'].create(line_vals)
        
        # فتح الدفعة الجديدة
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'payment.batch',
            'res_id': batch.id,
            'view_mode': 'form',
            'target': 'current',
        }
