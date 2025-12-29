# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools import float_is_zero
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class ProfitLossReport(models.AbstractModel):
    _name = 'report.profit.loss'
    _description = 'Profit & Loss Report'

    @api.model
    def get_report_data(self, date_from=False, date_to=False, posted_only=True,
                        comparison=False, comparison_type='previous_period'):
        """
        Get Profit & Loss report data.
        
        Args:
            date_from: Start date
            date_to: End date
            posted_only: Only posted entries
            comparison: Enable comparison
            comparison_type: 'previous_period' or 'previous_year'
        
        Returns structured P&L data with optional comparison.
        """
        # Parse dates
        if isinstance(date_from, str):
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        if isinstance(date_to, str):
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        
        if not date_from:
            date_from = datetime(datetime.now().year, 1, 1).date()
        if not date_to:
            date_to = datetime.now().date()
        
        # Get current period data
        current_data = self._get_period_data(date_from, date_to, posted_only)
        
        # Get comparison period data if enabled
        comparison_data = None
        comp_date_from = None
        comp_date_to = None
        
        if comparison:
            if comparison_type == 'previous_period':
                # Same duration, immediately before
                duration = (date_to - date_from).days + 1
                comp_date_to = date_from - timedelta(days=1)
                comp_date_from = comp_date_to - timedelta(days=duration - 1)
            else:  # previous_year
                # Same dates, previous year
                comp_date_from = date_from - relativedelta(years=1)
                comp_date_to = date_to - relativedelta(years=1)
            
            comparison_data = self._get_period_data(comp_date_from, comp_date_to, posted_only)
        
        # Structure the report
        result = self._structure_report(current_data, comparison_data)
        
        # Add metadata
        result['date_from'] = date_from.strftime('%d/%m/%Y')
        result['date_to'] = date_to.strftime('%d/%m/%Y')
        result['comparison'] = comparison
        result['comparison_type'] = comparison_type
        if comparison:
            result['comp_date_from'] = comp_date_from.strftime('%d/%m/%Y')
            result['comp_date_to'] = comp_date_to.strftime('%d/%m/%Y')
        
        return result

    def _get_period_data(self, date_from, date_to, posted_only):
        """Get account balances for a specific period."""
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
        ], order='code')
        
        # Build domain
        domain = [
            ('account_id', 'in', accounts.ids),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        
        if posted_only:
            domain.append(('parent_state', '=', 'posted'))
        else:
            domain.append(('parent_state', '!=', 'cancel'))
        
        # Read grouped data
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
            # For P&L: Credit - Debit (Income is credit, Expense is debit)
            account_data[acc_id]['balance'] += line.credit - line.debit
        
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
        
        return account_data

    def _structure_report(self, current_data, comparison_data=None):
        """Structure the P&L report into sections."""
        precision = self.env['decimal.precision'].precision_get('Account')
        
        # Initialize sections
        sections = {
            'operating_income': {
                'name': 'Operating Income',
                'icon': 'fa-arrow-up',
                'accounts': [],
                'total': 0.0,
                'comp_total': 0.0,
                'change': 0.0,
                'change_percent': 0.0,
            },
            'cost_of_revenue': {
                'name': 'Cost of Revenue',
                'icon': 'fa-shopping-cart',
                'accounts': [],
                'total': 0.0,
                'comp_total': 0.0,
                'change': 0.0,
                'change_percent': 0.0,
            },
            'operating_expenses': {
                'name': 'Operating Expenses',
                'icon': 'fa-money',
                'accounts': [],
                'total': 0.0,
                'comp_total': 0.0,
                'change': 0.0,
                'change_percent': 0.0,
            },
            'other_income': {
                'name': 'Other Income',
                'icon': 'fa-plus-circle',
                'accounts': [],
                'total': 0.0,
                'comp_total': 0.0,
                'change': 0.0,
                'change_percent': 0.0,
            },
        }
        
        # Classify accounts
        type_mapping = {
            'income': 'operating_income',
            'income_other': 'other_income',
            'expense': 'operating_expenses',
            'expense_depreciation': 'operating_expenses',
            'expense_direct_cost': 'cost_of_revenue',
        }
        
        for acc_id, acc_data in current_data.items():
            section_key = type_mapping.get(acc_data['account_type'])
            if not section_key:
                continue
            
            balance = acc_data['balance']
            comp_balance = 0.0
            
            if comparison_data and acc_id in comparison_data:
                comp_balance = comparison_data[acc_id]['balance']
            
            # For expenses, show as positive (negate the balance)
            if section_key in ('cost_of_revenue', 'operating_expenses'):
                balance = -balance
                comp_balance = -comp_balance
            
            # Skip zero balances if both periods are zero
            if float_is_zero(balance, precision_digits=precision) and \
               float_is_zero(comp_balance, precision_digits=precision):
                continue
            
            change = balance - comp_balance
            change_percent = (change / comp_balance * 100) if comp_balance else 0.0
            
            account_entry = {
                'id': acc_id,
                'code': acc_data['code'],
                'name': acc_data['name'],
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
        
        # Calculate summary figures
        total_income = sections['operating_income']['total'] + sections['other_income']['total']
        comp_total_income = sections['operating_income']['comp_total'] + sections['other_income']['comp_total']
        
        gross_profit = sections['operating_income']['total'] - sections['cost_of_revenue']['total']
        comp_gross_profit = sections['operating_income']['comp_total'] - sections['cost_of_revenue']['comp_total']
        
        operating_profit = gross_profit - sections['operating_expenses']['total']
        comp_operating_profit = comp_gross_profit - sections['operating_expenses']['comp_total']
        
        net_profit = operating_profit + sections['other_income']['total']
        comp_net_profit = comp_operating_profit + sections['other_income']['comp_total']
        
        # Calculate margins
        gross_margin = (gross_profit / sections['operating_income']['total'] * 100) \
            if sections['operating_income']['total'] else 0.0
        net_margin = (net_profit / total_income * 100) if total_income else 0.0
        
        comp_gross_margin = (comp_gross_profit / sections['operating_income']['comp_total'] * 100) \
            if sections['operating_income']['comp_total'] else 0.0
        comp_net_margin = (comp_net_profit / comp_total_income * 100) if comp_total_income else 0.0
        
        return {
            'sections': sections,
            'summary': {
                'total_income': total_income,
                'comp_total_income': comp_total_income,
                'gross_profit': gross_profit,
                'comp_gross_profit': comp_gross_profit,
                'gross_margin': gross_margin,
                'comp_gross_margin': comp_gross_margin,
                'operating_profit': operating_profit,
                'comp_operating_profit': comp_operating_profit,
                'net_profit': net_profit,
                'comp_net_profit': comp_net_profit,
                'net_margin': net_margin,
                'comp_net_margin': comp_net_margin,
                'total_expenses': sections['cost_of_revenue']['total'] + sections['operating_expenses']['total'],
                'comp_total_expenses': sections['cost_of_revenue']['comp_total'] + sections['operating_expenses']['comp_total'],
            }
        }
