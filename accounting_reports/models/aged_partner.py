# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools import float_is_zero
from datetime import datetime, timedelta


class AgedPartnerReport(models.AbstractModel):
    _name = 'report.aged.partner'
    _description = 'Aged Partner Report (Receivable/Payable)'

    @api.model
    def get_report_data(self, as_of_date=False, partner_ids=False, 
                        report_type='receivable', period_length=30):
        """
        Get Aged Partner report data.
        
        Args:
            as_of_date: Date to calculate aging from (default: today)
            partner_ids: List of partner IDs to filter (False = all)
            report_type: 'receivable' or 'payable'
            period_length: Number of days per period (default: 30)
        
        Returns:
        {
            'partners': [
                {
                    'id': partner_id,
                    'name': 'Partner Name',
                    'ref': 'REF001',
                    'not_due': 1000.00,
                    'period1': 500.00,    # 0-30
                    'period2': 300.00,    # 31-60
                    'period3': 200.00,    # 61-90
                    'period4': 100.00,    # 91-120
                    'older': 50.00,       # 120+
                    'total': 2150.00,
                    'lines': [...]
                }
            ],
            'totals': {
                'not_due': ...,
                'period1': ...,
                'period2': ...,
                'period3': ...,
                'period4': ...,
                'older': ...,
                'total': ...
            },
            'period_labels': ['Not Due', '0-30', '31-60', '61-90', '91-120', '120+']
        }
        """
        MoveLine = self.env['account.move.line']
        Partner = self.env['res.partner']
        Account = self.env['account.account']
        
        # Set as_of_date
        if not as_of_date:
            as_of_date = fields.Date.today()
        elif isinstance(as_of_date, str):
            as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()
        
        # Determine account type
        if report_type == 'receivable':
            account_type = 'asset_receivable'
        else:
            account_type = 'liability_payable'
        
        # Get accounts
        accounts = Account.search([('account_type', '=', account_type)])
        
        if not accounts:
            return self._empty_result(period_length)
        
        # Build domain for open items
        domain = [
            ('account_id', 'in', accounts.ids),
            ('parent_state', '=', 'posted'),
            ('reconciled', '=', False),
            ('date', '<=', as_of_date),
            ('partner_id', '!=', False),
        ]
        
        if partner_ids and isinstance(partner_ids, (list, tuple)):
            domain.append(('partner_id', 'in', partner_ids))
        
        # Get move lines
        move_lines = MoveLine.search(domain, order='partner_id, date_maturity, date')
        
        # Calculate period boundaries
        period_labels = self._get_period_labels(period_length)
        
        # Group by partner
        partners_data = {}
        
        for line in move_lines:
            partner_id = line.partner_id.id
            
            if partner_id not in partners_data:
                partners_data[partner_id] = {
                    'id': partner_id,
                    'name': line.partner_id.name,
                    'ref': line.partner_id.ref or '',
                    'not_due': 0.0,
                    'period1': 0.0,
                    'period2': 0.0,
                    'period3': 0.0,
                    'period4': 0.0,
                    'older': 0.0,
                    'total': 0.0,
                    'lines': [],
                }
            
            # Calculate amount (residual)
            amount = line.amount_residual
            if report_type == 'payable':
                amount = -amount  # Make payable positive
            
            # Determine due date
            due_date = line.date_maturity or line.date
            
            # Calculate days overdue
            days = (as_of_date - due_date).days
            
            # Assign to period
            period = self._get_period(days, period_length)
            
            partners_data[partner_id][period] += amount
            partners_data[partner_id]['total'] += amount
            
            # Add line details
            partners_data[partner_id]['lines'].append({
                'id': line.id,
                'move_id': line.move_id.id,
                'move_name': line.move_id.name,
                'date': line.date.strftime('%d/%m/%Y') if line.date else '',
                'date_maturity': due_date.strftime('%d/%m/%Y') if due_date else '',
                'days': days,
                'ref': line.ref or '',
                'label': line.name or '',
                'amount': amount,
                'period': period,
            })
        
        # Calculate totals
        totals = {
            'not_due': 0.0,
            'period1': 0.0,
            'period2': 0.0,
            'period3': 0.0,
            'period4': 0.0,
            'older': 0.0,
            'total': 0.0,
        }
        
        result_partners = []
        precision = self.env['decimal.precision'].precision_get('Account')
        
        for partner_data in sorted(partners_data.values(), key=lambda x: x['name']):
            # Skip zero balance partners
            if float_is_zero(partner_data['total'], precision_digits=precision):
                continue
            
            result_partners.append(partner_data)
            
            for key in totals:
                totals[key] += partner_data[key]
        
        return {
            'partners': result_partners,
            'totals': totals,
            'period_labels': period_labels,
            'as_of_date': as_of_date.strftime('%d/%m/%Y'),
            'report_type': report_type,
        }
    
    def _get_period(self, days, period_length):
        """Determine which period a number of days falls into"""
        if days < 0:
            return 'not_due'
        elif days <= period_length:
            return 'period1'
        elif days <= period_length * 2:
            return 'period2'
        elif days <= period_length * 3:
            return 'period3'
        elif days <= period_length * 4:
            return 'period4'
        else:
            return 'older'
    
    def _get_period_labels(self, period_length):
        """Generate period labels based on period length"""
        p = period_length
        return [
            'Not Due',
            f'0-{p}',
            f'{p+1}-{p*2}',
            f'{p*2+1}-{p*3}',
            f'{p*3+1}-{p*4}',
            f'{p*4}+'
        ]
    
    def _empty_result(self, period_length):
        """Return empty result structure"""
        return {
            'partners': [],
            'totals': {
                'not_due': 0, 'period1': 0, 'period2': 0,
                'period3': 0, 'period4': 0, 'older': 0, 'total': 0
            },
            'period_labels': self._get_period_labels(period_length),
            'as_of_date': fields.Date.today().strftime('%d/%m/%Y'),
            'report_type': 'receivable',
        }

    @api.model
    def get_partners(self, report_type='receivable'):
        """Get partners that have receivable/payable balance"""
        MoveLine = self.env['account.move.line']
        Account = self.env['account.account']
        
        if report_type == 'receivable':
            account_type = 'asset_receivable'
        else:
            account_type = 'liability_payable'
        
        accounts = Account.search([('account_type', '=', account_type)])
        
        if not accounts:
            return []
        
        partner_ids = MoveLine.search([
            ('account_id', 'in', accounts.ids),
            ('parent_state', '=', 'posted'),
            ('reconciled', '=', False),
            ('partner_id', '!=', False),
        ]).mapped('partner_id').ids
        
        partners = self.env['res.partner'].browse(partner_ids).sorted('name')
        
        return [{'id': p.id, 'name': p.name, 'ref': p.ref or ''} for p in partners]
