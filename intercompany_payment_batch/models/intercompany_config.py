# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class IntercompanyConfig(models.Model):
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

    journal_id = fields.Many2one(
        'account.journal',
        string='Target Journal',
        required=True,
        help="The journal to use for auto-generated entries in the target company"
    )

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

    # Distribution fields
    line_ids = fields.One2many(
        'intercompany.config.line',
        'config_id',
        string='Distribution Lines',
        copy=True
    )

    lines_count = fields.Integer(
        string='Distribution Lines',
        compute='_compute_lines_count'
    )

    total_percentage = fields.Float(
        string='Total Percentage',
        compute='_compute_total_percentage'
    )

    @api.depends('line_ids')
    def _compute_lines_count(self):
        for config in self:
            config.lines_count = len(config.line_ids)

    @api.depends('line_ids.percentage', 'line_ids.distribution_type')
    def _compute_total_percentage(self):
        for config in self:
            percentage_lines = config.line_ids.filtered(
                lambda l: l.distribution_type == 'percentage'
            )
            config.total_percentage = sum(percentage_lines.mapped('percentage'))

    @api.constrains('total_percentage')
    def _check_total_percentage(self):
        for config in self:
            if config.total_percentage > 100:
                raise ValidationError(_(
                    'Total percentage cannot exceed 100%% (currently %.2f%%)'
                ) % config.total_percentage)

    @api.constrains('company_id', 'account_id')
    def _check_source_account(self):
        for record in self:
            if record.account_id.company_id and record.account_id.company_id != record.company_id:
                raise ValidationError(_(
                    'The Related Party Account must belong to the Source Company!\n'
                    'Account: %s belongs to %s\n'
                    'But Source Company is: %s'
                ) % (
                    record.account_id.display_name,
                    record.account_id.company_id.name,
                    record.company_id.name
                ))

    @api.constrains('target_company_id', 'target_account_id')
    def _check_target_account(self):
        for record in self:
            if record.target_account_id.company_id and record.target_account_id.company_id != record.target_company_id:
                raise ValidationError(_(
                    'The Target Related Party Account must belong to the Target Company!\n'
                    'Account: %s belongs to %s\n'
                    'But Target Company is: %s'
                ) % (
                    record.target_account_id.display_name,
                    record.target_account_id.company_id.name,
                    record.target_company_id.name
                ))

    @api.constrains('company_id', 'target_company_id')
    def _check_different_companies(self):
        for record in self:
            if record.company_id == record.target_company_id:
                raise ValidationError(_(
                    'Source Company and Target Company must be different!'
                ))

    @api.constrains('journal_id', 'target_company_id')
    def _check_journal_company(self):
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
        if self.company_id:
            self.account_id = False
            return {
                'domain': {
                    'account_id': [('company_id', '=', self.company_id.id)]
                }
            }

    @api.onchange('target_company_id')
    def _onchange_target_company_id(self):
        result = {}
        if self.target_company_id:
            self.target_account_id = False
            self.journal_id = False

            result['domain'] = {
                'target_account_id': [
                    ('company_id', '=', self.target_company_id.id)
                ],
                'journal_id': [
                    ('company_id', '=', self.target_company_id.id),
                    ('type', '=', 'general')
                ]
            }
        return result

    def name_get(self):
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


class IntercompanyConfigLine(models.Model):
    _name = 'intercompany.config.line'
    _description = 'Intercompany Config Distribution Line'
    
    config_id = fields.Many2one(
        'intercompany.config',
        string='Configuration',
        required=True,
        ondelete='cascade'
    )
    
    account_id = fields.Many2one(
        'account.account',
        string='Expense Account',
        required=True
    )
    
    target_account_id = fields.Many2one(
        'account.account',
        string='Target Account'
    )
    
    distribution_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('auto', 'Auto-detect')
    ], string='Type', default='percentage')
    
    percentage = fields.Float(
        string='Percentage',
        default=100.0
    )
    
    label = fields.Char(string='Label')
