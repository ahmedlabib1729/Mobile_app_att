# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools import float_is_zero
from datetime import datetime


class TaxReport(models.AbstractModel):
    _name = 'report.tax.report'
    _description = 'Tax Report'

    @api.model
    def get_report_data(self, date_from=False, date_to=False, posted_only=True):
        """
        Get Tax report data grouped by tax.
        
        Returns:
        {
            'sales_taxes': [
                {
                    'tax_id': 1,
                    'tax_name': 'VAT 5% (Sales)',
                    'tax_amount': 5.0,
                    'base_amount': 100000.00,
                    'tax_total': 5000.00,
                    'invoice_count': 25,
                }
            ],
            'purchase_taxes': [...],
            'totals': {
                'sales_base': 100000.00,
                'sales_tax': 5000.00,
                'purchase_base': 80000.00,
                'purchase_tax': 4000.00,
                'net_tax': 1000.00,  # Sales Tax - Purchase Tax
            }
        }
        """
        MoveLine = self.env['account.move.line']
        
        # Build domain
        domain = [
            ('tax_line_id', '!=', False),  # Only tax lines
            ('parent_state', '=', 'posted') if posted_only else ('parent_state', '!=', 'cancel'),
        ]
        
        if date_from:
            if isinstance(date_from, str):
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            domain.append(('date', '>=', date_from))
        
        if date_to:
            if isinstance(date_to, str):
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            domain.append(('date', '<=', date_to))
        
        # Get all tax lines
        tax_lines = MoveLine.search(domain)
        
        # Group by tax
        sales_taxes = {}
        purchase_taxes = {}
        
        for line in tax_lines:
            tax = line.tax_line_id
            tax_id = tax.id
            
            # Get base amount from the tax base
            # tax_base_amount is the base on which this tax was computed
            base_amount = abs(line.tax_base_amount)
            tax_amount = abs(line.balance)
            
            # Determine if sales or purchase tax
            move_type = line.move_id.move_type
            
            if move_type in ('out_invoice', 'out_refund', 'out_receipt'):
                # Sales tax
                tax_dict = sales_taxes
                # For refunds, amounts might be negative
                if move_type == 'out_refund':
                    base_amount = -base_amount
                    tax_amount = -tax_amount
            elif move_type in ('in_invoice', 'in_refund', 'in_receipt'):
                # Purchase tax
                tax_dict = purchase_taxes
                # For refunds, amounts might be negative
                if move_type == 'in_refund':
                    base_amount = -base_amount
                    tax_amount = -tax_amount
            else:
                # Journal entries - check tax type
                if tax.type_tax_use == 'sale':
                    tax_dict = sales_taxes
                elif tax.type_tax_use == 'purchase':
                    tax_dict = purchase_taxes
                else:
                    continue
            
            if tax_id not in tax_dict:
                tax_dict[tax_id] = {
                    'tax_id': tax_id,
                    'tax_name': tax.name,
                    'tax_percent': tax.amount,
                    'tax_type': tax.amount_type,
                    'base_amount': 0.0,
                    'tax_total': 0.0,
                    'invoice_count': 0,
                    'move_ids': set(),
                }
            
            tax_dict[tax_id]['base_amount'] += base_amount
            tax_dict[tax_id]['tax_total'] += tax_amount
            tax_dict[tax_id]['move_ids'].add(line.move_id.id)
        
        # Convert to list and calculate invoice count
        sales_list = []
        for tax_data in sorted(sales_taxes.values(), key=lambda x: x['tax_name']):
            tax_data['invoice_count'] = len(tax_data['move_ids'])
            tax_data['move_ids'] = list(tax_data['move_ids'])
            sales_list.append(tax_data)
        
        purchase_list = []
        for tax_data in sorted(purchase_taxes.values(), key=lambda x: x['tax_name']):
            tax_data['invoice_count'] = len(tax_data['move_ids'])
            tax_data['move_ids'] = list(tax_data['move_ids'])
            purchase_list.append(tax_data)
        
        # Calculate totals
        sales_base = sum(t['base_amount'] for t in sales_list)
        sales_tax = sum(t['tax_total'] for t in sales_list)
        purchase_base = sum(t['base_amount'] for t in purchase_list)
        purchase_tax = sum(t['tax_total'] for t in purchase_list)
        
        return {
            'sales_taxes': sales_list,
            'purchase_taxes': purchase_list,
            'totals': {
                'sales_base': sales_base,
                'sales_tax': sales_tax,
                'purchase_base': purchase_base,
                'purchase_tax': purchase_tax,
                'net_tax': sales_tax - purchase_tax,
            },
            'date_from': date_from.strftime('%d/%m/%Y') if date_from else '',
            'date_to': date_to.strftime('%d/%m/%Y') if date_to else '',
        }

    @api.model
    def get_tax_details(self, tax_id, date_from=False, date_to=False, 
                        tax_type='sale', posted_only=True):
        """
        Get detailed moves for a specific tax.
        
        Returns list of invoices/moves with this tax.
        """
        MoveLine = self.env['account.move.line']
        
        domain = [
            ('tax_line_id', '=', tax_id),
            ('parent_state', '=', 'posted') if posted_only else ('parent_state', '!=', 'cancel'),
        ]
        
        if date_from:
            if isinstance(date_from, str):
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            domain.append(('date', '>=', date_from))
        
        if date_to:
            if isinstance(date_to, str):
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            domain.append(('date', '<=', date_to))
        
        # Filter by move type based on tax_type
        if tax_type == 'sale':
            domain.append(('move_id.move_type', 'in', ('out_invoice', 'out_refund', 'out_receipt', 'entry')))
        else:
            domain.append(('move_id.move_type', 'in', ('in_invoice', 'in_refund', 'in_receipt', 'entry')))
        
        tax_lines = MoveLine.search(domain, order='date desc')
        
        # Group by move
        moves_data = {}
        for line in tax_lines:
            move = line.move_id
            move_id = move.id
            
            if move_id not in moves_data:
                moves_data[move_id] = {
                    'move_id': move_id,
                    'move_name': move.name,
                    'date': line.date.strftime('%d/%m/%Y') if line.date else '',
                    'partner_name': move.partner_id.name or '',
                    'move_type': move.move_type,
                    'base_amount': 0.0,
                    'tax_amount': 0.0,
                }
            
            base = line.tax_base_amount
            tax = line.balance
            
            # Handle refunds
            if move.move_type in ('out_refund', 'in_refund'):
                base = -abs(base)
                tax = -abs(tax)
            else:
                base = abs(base)
                tax = abs(tax)
            
            moves_data[move_id]['base_amount'] += base
            moves_data[move_id]['tax_amount'] += tax
        
        return list(moves_data.values())
