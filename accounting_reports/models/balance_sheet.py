# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools import float_is_zero
from datetime import datetime
from dateutil.relativedelta import relativedelta


class BalanceSheetReport(models.AbstractModel):
    _name = 'report.balance.sheet'
    _description = 'Balance Sheet Report'

    @api.model
    def get_report_data(self, as_of_date=False, posted_only=True,
                        comparison=False, comparison_date=False):
        """
        Get Balance Sheet report data.
        
        Args:
            as_of_date: Balance sheet date
            posted_only: Only posted entries
            comparison: Enable comparison
            comparison_date: Date for comparison period
        
        Returns structured Balance Sheet data.
        """
        # Parse dates
        if isinstance(as_of_date, str):
            as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()
        if isinstance(comparison_date, str):
            comparison_date = datetime.strptime(comparison_date, '%Y-%m-%d').date()
        
        if not as_of_date:
            as_of_date = datetime.now().date()
        
        # Default comparison to end of previous year
        if comparison and not comparison_date:
            comparison_date = datetime(as_of_date.year - 1, 12, 31).date()
        
        # Get current period data
        current_data = self._get_balances(as_of_date, posted_only)
        
        # Get comparison period data if enabled
        comparison_data = None
        if comparison and comparison_date:
            comparison_data = self._get_balances(comparison_date, posted_only)
        
        # Structure the report
        result = self._structure_report(current_data, comparison_data)
        
        # Add metadata
        result['as_of_date'] = as_of_date.strftime('%d/%m/%Y')
        result['comparison'] = comparison
        if comparison and comparison_date:
            result['comparison_date'] = comparison_date.strftime('%d/%m/%Y')
        
        return result

    def _get_balances(self, as_of_date, posted_only):
        """Get account balances as of a specific date."""
        MoveLine = self.env['account.move.line']
        Account = self.env['account.account']
        
        # Balance Sheet account types
        bs_account_types = [
            # Assets
            'asset_receivable',
            'asset_cash',
            'asset_current',
            'asset_non_current',
            'asset_prepayments',
            'asset_fixed',
            # Liabilities
            'liability_payable',
            'liability_credit_card',
            'liability_current',
            'liability_non_current',
            # Equity
            'equity',
            'equity_unaffected',
        ]
        
        # Get all BS accounts
        accounts = Account.search([
            ('account_type', 'in', bs_account_types)
        ], order='code')
        
        # Build domain - all entries up to as_of_date
        domain = [
            ('account_id', 'in', accounts.ids),
            ('date', '<=', as_of_date),
        ]
        
        if posted_only:
            domain.append(('parent_state', '=', 'posted'))
        else:
            domain.append(('parent_state', '!=', 'cancel'))
        
        # Get move lines
        move_lines = MoveLine.search(domain)
        
        # Group by account
        account_data = {}
        for line in move_lines:
            acc_id = line.account_id.id
            if acc_id not in account_data:
                account = line.account_id
                account_data[acc_id] = {
                    'id': acc_id,
                    'code': account.code,
                    'name': account.name,
                    'account_type': account.account_type,
                    'balance': 0.0,
                }
            # Debit - Credit for balance
            account_data[acc_id]['balance'] += line.debit - line.credit
        
        # Add accounts with zero balance
        for account in accounts:
            if account.id not in account_data:
                account_data[account.id] = {
                    'id': account.id,
                    'code': account.code,
                    'name': account.name,
                    'account_type': account.account_type,
                    'balance': 0.0,
                }
        
        # Calculate retained earnings (P&L accounts)
        retained_earnings = self._calculate_retained_earnings(as_of_date, posted_only)
        
        return {
            'accounts': account_data,
            'retained_earnings': retained_earnings,
        }

    def _calculate_retained_earnings(self, as_of_date, posted_only):
        """Calculate retained earnings from P&L accounts."""
        MoveLine = self.env['account.move.line']
        Account = self.env['account.account']
        
        # P&L account types
        pl_account_types = [
            'income',
            'income_other',
            'expense',
            'expense_depreciation',
            'expense_direct_cost',
        ]
        
        # Get all P&L accounts
        accounts = Account.search([
            ('account_type', 'in', pl_account_types)
        ])
        
        if not accounts:
            return 0.0
        
        # Build domain
        domain = [
            ('account_id', 'in', accounts.ids),
            ('date', '<=', as_of_date),
        ]
        
        if posted_only:
            domain.append(('parent_state', '=', 'posted'))
        else:
            domain.append(('parent_state', '!=', 'cancel'))
        
        # Get totals
        move_lines = MoveLine.search(domain)
        
        total = 0.0
        for line in move_lines:
            # Credit - Debit for P&L (Income is credit positive)
            total += line.credit - line.debit
        
        return total

    def _structure_report(self, current_data, comparison_data=None):
        """Structure the Balance Sheet into sections."""
        precision = self.env['decimal.precision'].precision_get('Account')
        
        # Define sections with their account types
        sections = {
            # ASSETS
            'current_assets': {
                'name': 'Current Assets',
                'category': 'assets',
                'icon': 'fa-money',
                'types': ['asset_receivable', 'asset_cash', 'asset_current', 'asset_prepayments'],
                'accounts': [],
                'total': 0.0,
                'comp_total': 0.0,
            },
            'non_current_assets': {
                'name': 'Non-Current Assets',
                'category': 'assets',
                'icon': 'fa-building',
                'types': ['asset_non_current', 'asset_fixed'],
                'accounts': [],
                'total': 0.0,
                'comp_total': 0.0,
            },
            # LIABILITIES
            'current_liabilities': {
                'name': 'Current Liabilities',
                'category': 'liabilities',
                'icon': 'fa-credit-card',
                'types': ['liability_payable', 'liability_credit_card', 'liability_current'],
                'accounts': [],
                'total': 0.0,
                'comp_total': 0.0,
            },
            'non_current_liabilities': {
                'name': 'Non-Current Liabilities',
                'category': 'liabilities',
                'icon': 'fa-bank',
                'types': ['liability_non_current'],
                'accounts': [],
                'total': 0.0,
                'comp_total': 0.0,
            },
            # EQUITY
            'equity': {
                'name': 'Equity',
                'category': 'equity',
                'icon': 'fa-balance-scale',
                'types': ['equity', 'equity_unaffected'],
                'accounts': [],
                'total': 0.0,
                'comp_total': 0.0,
            },
        }
        
        # Classify accounts into sections
        for acc_id, acc_data in current_data['accounts'].items():
            section_key = None
            for key, section in sections.items():
                if acc_data['account_type'] in section['types']:
                    section_key = key
                    break
            
            if not section_key:
                continue
            
            balance = acc_data['balance']
            comp_balance = 0.0
            
            if comparison_data and acc_id in comparison_data['accounts']:
                comp_balance = comparison_data['accounts'][acc_id]['balance']
            
            # For liabilities and equity, negate (they have credit balance)
            if sections[section_key]['category'] in ('liabilities', 'equity'):
                balance = -balance
                comp_balance = -comp_balance
            
            # Skip zero balances
            if float_is_zero(balance, precision_digits=precision) and \
               float_is_zero(comp_balance, precision_digits=precision):
                continue
            
            change = balance - comp_balance
            change_percent = (change / comp_balance * 100) if comp_balance else 0.0
            
            account_entry = {
                'id': acc_id,
                'code': acc_data['code'],
                'name': acc_data['name'],
                'account_type': acc_data['account_type'],
                'balance': balance,
                'comp_balance': comp_balance,
                'change': change,
                'change_percent': change_percent,
            }
            
            sections[section_key]['accounts'].append(account_entry)
            sections[section_key]['total'] += balance
            sections[section_key]['comp_total'] += comp_balance
        
        # Sort accounts by code
        for section in sections.values():
            section['accounts'].sort(key=lambda x: x['code'])
            section['change'] = section['total'] - section['comp_total']
            if section['comp_total']:
                section['change_percent'] = section['change'] / section['comp_total'] * 100
            else:
                section['change_percent'] = 0.0
        
        # Add retained earnings to equity
        retained_earnings = current_data['retained_earnings']
        comp_retained_earnings = comparison_data['retained_earnings'] if comparison_data else 0.0
        
        if not float_is_zero(retained_earnings, precision_digits=precision) or \
           not float_is_zero(comp_retained_earnings, precision_digits=precision):
            sections['equity']['accounts'].append({
                'id': 0,
                'code': '---',
                'name': 'Retained Earnings (Current Year)',
                'account_type': 'retained_earnings',
                'balance': retained_earnings,
                'comp_balance': comp_retained_earnings,
                'change': retained_earnings - comp_retained_earnings,
                'change_percent': ((retained_earnings - comp_retained_earnings) / comp_retained_earnings * 100) 
                                  if comp_retained_earnings else 0.0,
            })
            sections['equity']['total'] += retained_earnings
            sections['equity']['comp_total'] += comp_retained_earnings
        
        # Recalculate equity change after adding retained earnings
        sections['equity']['change'] = sections['equity']['total'] - sections['equity']['comp_total']
        if sections['equity']['comp_total']:
            sections['equity']['change_percent'] = sections['equity']['change'] / sections['equity']['comp_total'] * 100
        
        # Calculate summary totals
        total_assets = sections['current_assets']['total'] + sections['non_current_assets']['total']
        comp_total_assets = sections['current_assets']['comp_total'] + sections['non_current_assets']['comp_total']
        
        total_liabilities = sections['current_liabilities']['total'] + sections['non_current_liabilities']['total']
        comp_total_liabilities = sections['current_liabilities']['comp_total'] + sections['non_current_liabilities']['comp_total']
        
        total_equity = sections['equity']['total']
        comp_total_equity = sections['equity']['comp_total']
        
        total_liabilities_equity = total_liabilities + total_equity
        comp_total_liabilities_equity = comp_total_liabilities + comp_total_equity
        
        # Check if balanced
        is_balanced = float_is_zero(total_assets - total_liabilities_equity, precision_digits=precision)
        
        return {
            'sections': sections,
            'summary': {
                'total_assets': total_assets,
                'comp_total_assets': comp_total_assets,
                'total_current_assets': sections['current_assets']['total'],
                'comp_total_current_assets': sections['current_assets']['comp_total'],
                'total_non_current_assets': sections['non_current_assets']['total'],
                'comp_total_non_current_assets': sections['non_current_assets']['comp_total'],
                'total_liabilities': total_liabilities,
                'comp_total_liabilities': comp_total_liabilities,
                'total_equity': total_equity,
                'comp_total_equity': comp_total_equity,
                'total_liabilities_equity': total_liabilities_equity,
                'comp_total_liabilities_equity': comp_total_liabilities_equity,
                'is_balanced': is_balanced,
                'difference': total_assets - total_liabilities_equity,
            }
        }
