# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools import float_is_zero
from datetime import date, datetime


class GeneralLedgerReport(models.AbstractModel):
    _name = 'report.general.ledger'
    _description = 'General Ledger Report'

    # ==================== FILTER DATA ====================
    
    @api.model
    def get_journals(self):
        """Get all journals for filter"""
        journals = self.env['account.journal'].search([])
        return [{
            'id': j.id,
            'name': j.name,
            'code': j.code,
            'type': j.type,
        } for j in journals]

    @api.model
    def get_accounts(self):
        """Get all accounts for filter"""
        accounts = self.env['account.account'].search([], order='code')
        return [{
            'id': a.id,
            'code': a.code,
            'name': a.name,
            'display_name': f"[{a.code}] {a.name}",
        } for a in accounts]

    @api.model
    def get_partners(self):
        """Get partners that have moves"""
        partners = self.env['res.partner'].search([
            ('id', 'in', self.env['account.move.line'].search([]).mapped('partner_id').ids)
        ], order='name')
        return [{
            'id': p.id,
            'name': p.name,
        } for p in partners]

    # ==================== REPORT DATA ====================
    
    @api.model
    def get_report_data(self, date_from=False, date_to=False, journal_ids=False,
                        account_ids=False, partner_ids=False, posted_only=True,
                        show_zero=False):
        """
        Get General Ledger report data grouped by account.
        
        Returns:
        {
            'accounts': [
                {
                    'id': account_id,
                    'code': '1001',
                    'name': 'Cash',
                    'opening': 1000.00,
                    'debit': 500.00,
                    'credit': 200.00,
                    'balance': 1300.00,
                    'moves': [
                        {
                            'id': move_line_id,
                            'date': '01/01/2025',
                            'move_name': 'INV/2025/001',
                            'journal': 'Sales',
                            'partner': 'Customer A',
                            'ref': 'Reference',
                            'label': 'Product Sale',
                            'debit': 500.00,
                            'credit': 0.00,
                            'balance': 1500.00,
                        },
                        ...
                    ]
                },
                ...
            ],
            'totals': {
                'opening': 10000.00,
                'debit': 50000.00,
                'credit': 45000.00,
                'balance': 15000.00,
            }
        }
        """
        MoveLine = self.env['account.move.line']
        Account = self.env['account.account']
        
        # Validate and clean filter inputs
        if journal_ids and not isinstance(journal_ids, (list, tuple)):
            journal_ids = False
        if account_ids and not isinstance(account_ids, (list, tuple)):
            account_ids = False
        if partner_ids and not isinstance(partner_ids, (list, tuple)):
            partner_ids = False
        
        # Build domain for move lines
        domain = [('display_type', 'not in', ('line_section', 'line_note'))]
        
        if posted_only:
            domain.append(('parent_state', '=', 'posted'))
        
        if journal_ids:
            domain.append(('journal_id', 'in', journal_ids))
        
        if account_ids:
            domain.append(('account_id', 'in', account_ids))
        
        if partner_ids:
            domain.append(('partner_id', 'in', partner_ids))
        
        # Date domain for movements
        date_domain = domain.copy()
        if date_from:
            date_domain.append(('date', '>=', date_from))
        if date_to:
            date_domain.append(('date', '<=', date_to))
        
        # Get move lines in period
        move_lines = MoveLine.search(date_domain, order='account_id, date, id')
        
        # Get all accounts that have moves or initial balance
        if account_ids and isinstance(account_ids, (list, tuple)):
            accounts = Account.browse(account_ids)
        else:
            account_ids_with_moves = move_lines.mapped('account_id').ids
            # Also get accounts with opening balance
            opening_domain = domain.copy()
            if date_from:
                opening_domain.append(('date', '<', date_from))
            opening_lines = MoveLine.search(opening_domain)
            account_ids_with_opening = opening_lines.mapped('account_id').ids
            
            all_account_ids = list(set(account_ids_with_moves + account_ids_with_opening))
            accounts = Account.browse(all_account_ids).sorted('code')
        
        # Prepare result
        result = {
            'accounts': [],
            'totals': {
                'opening': 0.0,
                'debit': 0.0,
                'credit': 0.0,
                'balance': 0.0,
            }
        }
        
        precision = self.env['decimal.precision'].precision_get('Account')
        
        for account in accounts:
            # Calculate opening balance (before date_from)
            opening_balance = 0.0
            if date_from:
                opening_domain = [
                    ('account_id', '=', account.id),
                    ('date', '<', date_from),
                    ('display_type', 'not in', ('line_section', 'line_note')),
                ]
                if posted_only:
                    opening_domain.append(('parent_state', '=', 'posted'))
                if journal_ids:
                    opening_domain.append(('journal_id', 'in', journal_ids))
                if partner_ids:
                    opening_domain.append(('partner_id', 'in', partner_ids))
                
                opening_lines = MoveLine.search(opening_domain)
                opening_balance = sum(opening_lines.mapped('debit')) - sum(opening_lines.mapped('credit'))
            
            # Get moves for this account in the period
            account_lines = move_lines.filtered(lambda l: l.account_id.id == account.id)
            
            # Skip if no movements and no opening (unless show_zero)
            if not account_lines and float_is_zero(opening_balance, precision_digits=precision):
                if not show_zero:
                    continue
            
            # Prepare account data
            account_debit = sum(account_lines.mapped('debit'))
            account_credit = sum(account_lines.mapped('credit'))
            closing_balance = opening_balance + account_debit - account_credit
            
            account_data = {
                'id': account.id,
                'code': account.code,
                'name': account.name,
                'opening': opening_balance,
                'debit': account_debit,
                'credit': account_credit,
                'balance': closing_balance,
                'moves': [],
            }
            
            # Add individual moves
            running_balance = opening_balance
            for line in account_lines.sorted(key=lambda l: (l.date, l.id)):
                running_balance += line.debit - line.credit
                
                account_data['moves'].append({
                    'id': line.id,
                    'date': line.date.strftime('%d/%m/%Y') if line.date else '',
                    'move_name': line.move_id.name or '',
                    'move_id': line.move_id.id,
                    'journal': line.journal_id.name or '',
                    'journal_code': line.journal_id.code or '',
                    'partner': line.partner_id.name or '',
                    'partner_id': line.partner_id.id if line.partner_id else False,
                    'ref': line.ref or '',
                    'label': line.name or '',
                    'debit': line.debit,
                    'credit': line.credit,
                    'balance': running_balance,
                })
            
            result['accounts'].append(account_data)
            
            # Update totals
            result['totals']['opening'] += opening_balance
            result['totals']['debit'] += account_debit
            result['totals']['credit'] += account_credit
            result['totals']['balance'] += closing_balance
        
        return result

    @api.model
    def get_account_moves(self, account_id, date_from=False, date_to=False,
                          journal_ids=False, partner_ids=False, posted_only=True):
        """
        Get moves for a single account (for lazy loading)
        """
        MoveLine = self.env['account.move.line']
        
        domain = [
            ('account_id', '=', account_id),
            ('display_type', 'not in', ('line_section', 'line_note')),
        ]
        
        if posted_only:
            domain.append(('parent_state', '=', 'posted'))
        
        if journal_ids:
            domain.append(('journal_id', 'in', journal_ids))
        
        if partner_ids:
            domain.append(('partner_id', 'in', partner_ids))
        
        if date_from:
            domain.append(('date', '>=', date_from))
        
        if date_to:
            domain.append(('date', '<=', date_to))
        
        # Calculate opening balance
        opening_balance = 0.0
        if date_from:
            opening_domain = [
                ('account_id', '=', account_id),
                ('date', '<', date_from),
                ('display_type', 'not in', ('line_section', 'line_note')),
            ]
            if posted_only:
                opening_domain.append(('parent_state', '=', 'posted'))
            if journal_ids:
                opening_domain.append(('journal_id', 'in', journal_ids))
            if partner_ids:
                opening_domain.append(('partner_id', 'in', partner_ids))
            
            opening_lines = MoveLine.search(opening_domain)
            opening_balance = sum(opening_lines.mapped('debit')) - sum(opening_lines.mapped('credit'))
        
        # Get moves
        lines = MoveLine.search(domain, order='date, id')
        
        moves = []
        running_balance = opening_balance
        
        for line in lines:
            running_balance += line.debit - line.credit
            moves.append({
                'id': line.id,
                'date': line.date.strftime('%d/%m/%Y') if line.date else '',
                'move_name': line.move_id.name or '',
                'move_id': line.move_id.id,
                'journal': line.journal_id.name or '',
                'journal_code': line.journal_id.code or '',
                'partner': line.partner_id.name or '',
                'partner_id': line.partner_id.id if line.partner_id else False,
                'ref': line.ref or '',
                'label': line.name or '',
                'debit': line.debit,
                'credit': line.credit,
                'balance': running_balance,
            })
        
        return {
            'opening': opening_balance,
            'moves': moves,
        }

    @api.model
    def get_move_lines(self, move_id):
        """
        Get all lines for a specific journal entry (for expandable details)
        with running balance across lines
        """
        Move = self.env['account.move']
        move = Move.browse(move_id)
        
        if not move.exists():
            return []
        
        lines = []
        running_balance = 0.0
        
        for line in move.line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note')):
            # Running balance = previous balance + (debit - credit)
            running_balance += line.debit - line.credit
            
            # Check if this line makes the entry balanced (balance ≈ 0)
            is_balancing = abs(running_balance) < 0.01
            
            lines.append({
                'id': line.id,
                'account_id': line.account_id.id,
                'account_code': line.account_id.code,
                'account_name': line.account_id.name,
                'partner': line.partner_id.name or '',
                'label': line.name or '',
                'debit': line.debit,
                'credit': line.credit,
                'balance': running_balance,
                'is_balancing': is_balancing,
                'tax_ids': [{'name': t.name} for t in line.tax_ids],
                'analytic': line.analytic_distribution or {},
            })
        
        return {
            'move_id': move.id,
            'move_name': move.name,
            'move_date': move.date.strftime('%d/%m/%Y') if move.date else '',
            'move_ref': move.ref or '',
            'partner': move.partner_id.name or '',
            'journal': move.journal_id.name,
            'state': move.state,
            'lines': lines,
        }
