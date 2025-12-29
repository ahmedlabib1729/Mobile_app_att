# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools import float_is_zero


class TrialBalanceReport(models.AbstractModel):
    _name = 'report.trial.balance'
    _description = 'Trial Balance Report'

    @api.model
    def get_account_types(self):
        """Get account types for filter"""
        return [
            {'id': 'asset_receivable', 'name': 'Receivable'},
            {'id': 'asset_cash', 'name': 'Bank and Cash'},
            {'id': 'asset_current', 'name': 'Current Assets'},
            {'id': 'asset_non_current', 'name': 'Non-current Assets'},
            {'id': 'asset_prepayments', 'name': 'Prepayments'},
            {'id': 'asset_fixed', 'name': 'Fixed Assets'},
            {'id': 'liability_payable', 'name': 'Payable'},
            {'id': 'liability_credit_card', 'name': 'Credit Card'},
            {'id': 'liability_current', 'name': 'Current Liabilities'},
            {'id': 'liability_non_current', 'name': 'Non-current Liabilities'},
            {'id': 'equity', 'name': 'Equity'},
            {'id': 'equity_unaffected', 'name': 'Current Year Earnings'},
            {'id': 'income', 'name': 'Income'},
            {'id': 'income_other', 'name': 'Other Income'},
            {'id': 'expense', 'name': 'Expenses'},
            {'id': 'expense_depreciation', 'name': 'Depreciation'},
            {'id': 'expense_direct_cost', 'name': 'Cost of Revenue'},
            {'id': 'off_balance', 'name': 'Off-Balance Sheet'},
        ]

    @api.model
    def get_report_data(self, date_from=False, date_to=False, account_types=False,
                        posted_only=True, hide_zero=True):
        """
        Get Trial Balance report data.
        
        Returns:
        {
            'accounts': [
                {
                    'id': account_id,
                    'code': '1001',
                    'name': 'Cash',
                    'account_type': 'asset_cash',
                    'account_type_name': 'Bank and Cash',
                    'opening_debit': 1000.00,
                    'opening_credit': 0.00,
                    'opening_balance': 1000.00,
                    'debit': 5000.00,
                    'credit': 3000.00,
                    'closing_debit': 6000.00,
                    'closing_credit': 3000.00,
                    'closing_balance': 3000.00,
                }
            ],
            'totals': {
                'opening_debit': ...,
                'opening_credit': ...,
                'debit': ...,
                'credit': ...,
                'closing_debit': ...,
                'closing_credit': ...,
            }
        }
        """
        MoveLine = self.env['account.move.line']
        Account = self.env['account.account']
        
        # Account type names mapping
        type_names = {t['id']: t['name'] for t in self.get_account_types()}
        
        # Get accounts
        account_domain = []
        if account_types and isinstance(account_types, (list, tuple)):
            account_domain.append(('account_type', 'in', account_types))
        
        accounts = Account.search(account_domain, order='code')
        
        if not accounts:
            return {
                'accounts': [],
                'totals': {
                    'opening_debit': 0, 'opening_credit': 0,
                    'debit': 0, 'credit': 0,
                    'closing_debit': 0, 'closing_credit': 0,
                }
            }
        
        # Base domain
        base_domain = [
            ('account_id', 'in', accounts.ids),
            ('display_type', 'not in', ('line_section', 'line_note')),
        ]
        
        if posted_only:
            base_domain.append(('parent_state', '=', 'posted'))
        
        result = {
            'accounts': [],
            'totals': {
                'opening_debit': 0.0,
                'opening_credit': 0.0,
                'debit': 0.0,
                'credit': 0.0,
                'closing_debit': 0.0,
                'closing_credit': 0.0,
            }
        }
        
        precision = self.env['decimal.precision'].precision_get('Account')
        
        for account in accounts:
            # Opening balance (before date_from)
            opening_debit = 0.0
            opening_credit = 0.0
            
            if date_from:
                opening_domain = [
                    ('account_id', '=', account.id),
                    ('date', '<', date_from),
                    ('display_type', 'not in', ('line_section', 'line_note')),
                ]
                if posted_only:
                    opening_domain.append(('parent_state', '=', 'posted'))
                
                opening_lines = MoveLine.search(opening_domain)
                opening_debit = sum(opening_lines.mapped('debit'))
                opening_credit = sum(opening_lines.mapped('credit'))
            
            opening_balance = opening_debit - opening_credit
            
            # Period movements
            period_domain = [
                ('account_id', '=', account.id),
                ('display_type', 'not in', ('line_section', 'line_note')),
            ]
            if posted_only:
                period_domain.append(('parent_state', '=', 'posted'))
            if date_from:
                period_domain.append(('date', '>=', date_from))
            if date_to:
                period_domain.append(('date', '<=', date_to))
            
            period_lines = MoveLine.search(period_domain)
            period_debit = sum(period_lines.mapped('debit'))
            period_credit = sum(period_lines.mapped('credit'))
            
            # Closing balance
            closing_debit = opening_debit + period_debit
            closing_credit = opening_credit + period_credit
            closing_balance = closing_debit - closing_credit
            
            # Skip zero balances if hide_zero
            if hide_zero:
                if (float_is_zero(opening_balance, precision_digits=precision) and
                    float_is_zero(period_debit, precision_digits=precision) and
                    float_is_zero(period_credit, precision_digits=precision) and
                    float_is_zero(closing_balance, precision_digits=precision)):
                    continue
            
            account_data = {
                'id': account.id,
                'code': account.code,
                'name': account.name,
                'account_type': account.account_type,
                'account_type_name': type_names.get(account.account_type, account.account_type),
                'opening_debit': opening_debit,
                'opening_credit': opening_credit,
                'opening_balance': opening_balance,
                'debit': period_debit,
                'credit': period_credit,
                'closing_debit': closing_debit,
                'closing_credit': closing_credit,
                'closing_balance': closing_balance,
            }
            
            result['accounts'].append(account_data)
            
            # Update totals
            result['totals']['opening_debit'] += opening_debit
            result['totals']['opening_credit'] += opening_credit
            result['totals']['debit'] += period_debit
            result['totals']['credit'] += period_credit
            result['totals']['closing_debit'] += closing_debit
            result['totals']['closing_credit'] += closing_credit
        
        return result
