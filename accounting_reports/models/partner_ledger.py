# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools import float_is_zero
import logging

_logger = logging.getLogger(__name__)


class PartnerLedgerReport(models.AbstractModel):
    _name = 'report.partner.ledger'
    _description = 'Partner Ledger Report'

    # ==================== FILTER DATA ====================

    @api.model
    def get_partners(self):
        """Get partners that have receivable/payable moves"""
        MoveLine = self.env['account.move.line']

        # Get accounts of type receivable or payable
        account_types = ['asset_receivable', 'liability_payable']
        accounts = self.env['account.account'].search([
            ('account_type', 'in', account_types)
        ])

        if not accounts:
            return []

        # Get partners with moves on these accounts
        partner_ids = MoveLine.search([
            ('account_id', 'in', accounts.ids),
            ('partner_id', '!=', False),
        ]).mapped('partner_id').ids

        partners = self.env['res.partner'].browse(partner_ids).sorted('name')

        return [{
            'id': p.id,
            'name': p.name,
            'ref': p.ref or '',
            'is_customer': any(acc.account_type == 'asset_receivable' for acc in accounts),
            'is_vendor': any(acc.account_type == 'liability_payable' for acc in accounts),
        } for p in partners]

    @api.model
    def get_partner_tags(self):
        """Get all partner tags/categories"""
        tags = self.env['res.partner.category'].search([], order='name')
        return [{
            'id': t.id,
            'name': t.name,
            'color': t.color,
            'parent_id': t.parent_id.id if t.parent_id else False,
            'parent_name': t.parent_id.name if t.parent_id else '',
        } for t in tags]

    @api.model
    def get_account_types(self):
        """Get receivable/payable account types"""
        return [
            {'id': 'asset_receivable', 'name': 'Receivable'},
            {'id': 'liability_payable', 'name': 'Payable'},
        ]

    # ==================== REPORT DATA ====================

    @api.model
    def get_report_data(self, date_from=False, date_to=False, partner_ids=False,
                        account_type=False, posted_only=True, tag_ids=False):
        """
        Get Partner Ledger report data.

        Args:
            date_from: Start date
            date_to: End date
            partner_ids: List of partner IDs to filter (False = all)
            account_type: 'asset_receivable', 'liability_payable', or False (both)
            posted_only: Only posted entries
            tag_ids: List of partner tag IDs to filter

        Returns:
            {
                'partners': [
                    {
                        'id': partner_id,
                        'name': 'Partner Name',
                        'ref': 'REF001',
                        'opening': 1000.00,
                        'debit': 5000.00,
                        'credit': 3000.00,
                        'balance': 3000.00,
                        'moves': [...]
                    }
                ],
                'totals': {
                    'opening': ...,
                    'debit': ...,
                    'credit': ...,
                    'balance': ...
                }
            }
        """
        MoveLine = self.env['account.move.line']
        Partner = self.env['res.partner']
        Account = self.env['account.account']

        # Debug log
        _logger.info("Partner Ledger - account_type received: %s (type: %s)", account_type, type(account_type))

        # Get receivable/payable accounts
        # Handle empty string as False
        if not account_type or account_type == '':
            account_types = ['asset_receivable', 'liability_payable']
        else:
            account_types = [account_type]

        _logger.info("Partner Ledger - filtering by account_types: %s", account_types)

        accounts = Account.search([('account_type', 'in', account_types)])
        _logger.info("Partner Ledger - found %d accounts", len(accounts))

        if not accounts:
            return {'partners': [], 'totals': {'opening': 0, 'debit': 0, 'credit': 0, 'balance': 0}}

        # If tag_ids provided, get partners with those tags
        tag_partner_ids = False
        if tag_ids and isinstance(tag_ids, (list, tuple)) and len(tag_ids) > 0:
            tag_partners = Partner.search([('category_id', 'in', tag_ids)])
            tag_partner_ids = tag_partners.ids
            _logger.info("Partner Ledger - filtering by tags, found %d partners", len(tag_partner_ids))

        # Build base domain
        domain = [
            ('account_id', 'in', accounts.ids),
            ('partner_id', '!=', False),
            ('display_type', 'not in', ('line_section', 'line_note')),
        ]

        if posted_only:
            domain.append(('parent_state', '=', 'posted'))

        # Partner filter - combine with tag filter
        effective_partner_ids = None
        if partner_ids and isinstance(partner_ids, (list, tuple)) and len(partner_ids) > 0:
            if tag_partner_ids:
                # Intersection of both filters
                effective_partner_ids = list(set(partner_ids) & set(tag_partner_ids))
            else:
                effective_partner_ids = partner_ids
        elif tag_partner_ids:
            effective_partner_ids = tag_partner_ids

        if effective_partner_ids is not None:
            if len(effective_partner_ids) == 0:
                # No partners match the filters
                return {'partners': [], 'totals': {'opening': 0, 'debit': 0, 'credit': 0, 'balance': 0}}
            domain.append(('partner_id', 'in', effective_partner_ids))

        # Date domain for period movements
        date_domain = domain.copy()
        if date_from:
            date_domain.append(('date', '>=', date_from))
        if date_to:
            date_domain.append(('date', '<=', date_to))

        # Get move lines in period
        move_lines = MoveLine.search(date_domain, order='partner_id, date, id')

        # Get all partners that have moves
        if effective_partner_ids is not None:
            all_partner_ids = effective_partner_ids
        else:
            # Partners with moves in period
            partner_ids_in_period = move_lines.mapped('partner_id').ids

            # Partners with opening balance
            opening_domain = domain.copy()
            if date_from:
                opening_domain.append(('date', '<', date_from))
            opening_lines = MoveLine.search(opening_domain)
            partner_ids_with_opening = opening_lines.mapped('partner_id').ids

            all_partner_ids = list(set(partner_ids_in_period + partner_ids_with_opening))

        partners = Partner.browse(all_partner_ids).sorted('name')

        # Prepare result
        result = {
            'partners': [],
            'totals': {
                'opening': 0.0,
                'debit': 0.0,
                'credit': 0.0,
                'balance': 0.0,
            }
        }

        precision = self.env['decimal.precision'].precision_get('Account')

        for partner in partners:
            # Calculate opening balance
            opening_balance = 0.0
            if date_from:
                opening_domain = [
                    ('account_id', 'in', accounts.ids),
                    ('partner_id', '=', partner.id),
                    ('date', '<', date_from),
                    ('display_type', 'not in', ('line_section', 'line_note')),
                ]
                if posted_only:
                    opening_domain.append(('parent_state', '=', 'posted'))

                opening_lines = MoveLine.search(opening_domain)
                opening_balance = sum(opening_lines.mapped('debit')) - sum(opening_lines.mapped('credit'))

            # Get moves for this partner
            partner_lines = move_lines.filtered(lambda l: l.partner_id.id == partner.id)

            # Skip if no movements and no opening
            if not partner_lines and float_is_zero(opening_balance, precision_digits=precision):
                continue

            # Calculate totals
            partner_debit = sum(partner_lines.mapped('debit'))
            partner_credit = sum(partner_lines.mapped('credit'))
            closing_balance = opening_balance + partner_debit - partner_credit

            partner_data = {
                'id': partner.id,
                'name': partner.name,
                'ref': partner.ref or '',
                'tags': [{'id': t.id, 'name': t.name, 'color': t.color} for t in partner.category_id],
                'opening': opening_balance,
                'debit': partner_debit,
                'credit': partner_credit,
                'balance': closing_balance,
                'moves': [],
            }

            # Add individual moves
            running_balance = opening_balance
            for line in partner_lines.sorted(key=lambda l: (l.date, l.id)):
                running_balance += line.debit - line.credit

                partner_data['moves'].append({
                    'id': line.id,
                    'date': line.date.strftime('%d/%m/%Y') if line.date else '',
                    'move_name': line.move_id.name or '',
                    'move_id': line.move_id.id,
                    'journal': line.journal_id.name or '',
                    'journal_code': line.journal_id.code or '',
                    'account': line.account_id.name or '',
                    'account_code': line.account_id.code or '',
                    'account_type': line.account_id.account_type,
                    'ref': line.ref or '',
                    'label': line.name or '',
                    'debit': line.debit,
                    'credit': line.credit,
                    'balance': running_balance,
                })

            result['partners'].append(partner_data)

            # Update totals
            result['totals']['opening'] += opening_balance
            result['totals']['debit'] += partner_debit
            result['totals']['credit'] += partner_credit
            result['totals']['balance'] += closing_balance

        return result