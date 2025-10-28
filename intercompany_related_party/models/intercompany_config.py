# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class IntercompanyConfig(models.Model):
    """
    Configuration model for mapping Related Party accounts between companies.

    This model defines how related party accounts in one company should map to
    the corresponding accounts in other companies for automatic journal entry creation.
    """
    _name = 'intercompany.config'
    _description = 'Intercompany Related Party Configuration'
    _order = 'company_id, target_company_id'
    _sql_constraints = [
        ('unique_mapping',
         'UNIQUE(company_id, account_id, target_company_id)',
         'A mapping for this account and target company already exists!')
    ]

    company_id = fields.Many2one(
        'res.company',
        string='Source Company',
        required=True,
        default=lambda self: self.env.company,
        help="The company where the payment is made"
    )

    account_id = fields.Many2one(
        'account.account',
        string='Related Party Account',
        required=True,
        help="The Related Party account in the source company"
    )

    # Target company and account
    target_company_id = fields.Many2one(
        'res.company',
        string='Target Company',
        required=True,
        help="The company that will receive the auto-generated entry"
    )

    target_account_id = fields.Many2one(
        'account.account',
        string='Target Related Party Account',
        required=True,
        help="The Related Party account in the target company (opposite side)"
    )

    # Journal for auto-generated entries
    journal_id = fields.Many2one(
        'account.journal',
        string='Target Journal',
        required=True,
        help="The journal to use for auto-generated entries in the target company"
    )

    # Additional fields
    active = fields.Boolean(
        default=True,
        help="Uncheck to disable this mapping without deleting it"
    )

    auto_post = fields.Boolean(
        string='Auto Post',
        default=True,
        help="Automatically post the generated entries in the target company"
    )

    notes = fields.Text(
        string='Notes',
        help="Internal notes about this configuration"
    )

    # Computed fields for display
    account_code = fields.Char(
        related='account_id.code',
        string='Account Code',
        readonly=True
    )

    target_account_code = fields.Char(
        related='target_account_id.code',
        string='Target Account Code',
        readonly=True
    )

    @api.constrains('company_id', 'account_id')
    def _check_source_account(self):
        """Validate that the source account belongs to the source company"""
        for record in self:
            # In Odoo 18, account.account uses company_ids (Many2many) instead of company_id
            if record.company_id not in record.account_id.company_ids:
                # Get the company names for the error message
                account_companies = ', '.join(record.account_id.company_ids.mapped('name'))
                raise ValidationError(_(
                    'The Related Party Account must belong to the Source Company!\n'
                    'Account: %s belongs to %s\n'
                    'But Source Company is: %s'
                ) % (
                    record.account_id.display_name,
                    account_companies or 'no company',
                    record.company_id.name
                ))

    @api.constrains('target_company_id', 'target_account_id')
    def _check_target_account(self):
        """Validate that the target account belongs to the target company"""
        for record in self:
            # In Odoo 18, account.account uses company_ids (Many2many) instead of company_id
            if record.target_company_id not in record.target_account_id.company_ids:
                # Get the company names for the error message
                account_companies = ', '.join(record.target_account_id.company_ids.mapped('name'))
                raise ValidationError(_(
                    'The Target Related Party Account must belong to the Target Company!\n'
                    'Account: %s belongs to %s\n'
                    'But Target Company is: %s'
                ) % (
                    record.target_account_id.display_name,
                    account_companies or 'no company',
                    record.target_company_id.name
                ))

    @api.constrains('company_id', 'target_company_id')
    def _check_different_companies(self):
        """Ensure source and target companies are different"""
        for record in self:
            if record.company_id == record.target_company_id:
                raise ValidationError(_(
                    'Source Company and Target Company must be different!'
                ))

    @api.constrains('journal_id', 'target_company_id')
    def _check_journal_company(self):
        """Validate that the journal belongs to the target company"""
        for record in self:
            if record.journal_id.company_id != record.target_company_id:
                raise ValidationError(_(
                    'The Target Journal must belong to the Target Company!\n'
                    'Journal: %s belongs to %s\n'
                    'But Target Company is: %s'
                ) % (
                                          record.journal_id.display_name,
                                          record.journal_id.company_id.name,
                                          record.target_company_id.name
                                      ))

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """Clear account_id when company changes and set domain"""
        if self.company_id:
            self.account_id = False
            return {
                'domain': {
                    'account_id': [('company_ids', 'in', self.company_id.id)]
                }
            }
        return {
            'domain': {
                'account_id': []
            }
        }

    @api.onchange('target_company_id')
    def _onchange_target_company_id(self):
        """Allow viewing accounts from target company using sudo"""
        result = {}
        if self.target_company_id:
            self.target_account_id = False
            self.journal_id = False

            # Use sudo() to bypass company restrictions
            # This allows viewing accounts from other companies
            result['domain'] = {
                'target_account_id': [
                    ('company_ids', 'in', self.target_company_id.id)
                ],
                'journal_id': [
                    ('company_id', '=', self.target_company_id.id),
                    ('type', '=', 'general')
                ]
            }
        return result

    def name_get(self):
        """Custom display name for the record"""
        result = []
        for record in self:
            name = '%s (%s) → %s (%s)' % (
                record.company_id.name,
                record.account_id.code or record.account_id.name,
                record.target_company_id.name,
                record.target_account_id.code or record.target_account_id.name,
            )
            result.append((record.id, name))
        return result