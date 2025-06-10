# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Add withdrawn state to existing building unit states
    state = fields.Selection(
        selection_add=[('withdrawn', 'Withdrawn')],
        ondelete={'withdrawn': 'cascade'}
    )

    # Withdrawal tracking fields
    withdrawal_date = fields.Date(
        string='Withdrawal Date',
        readonly=True,
        help="Date when unit was withdrawn due to overdue payments"
    )

    # Withdrawal monitoring
    withdrawal_monitor_ids = fields.One2many(
        'withdrawal.monitor',
        'building_unit_id',
        string='Withdrawal Monitors',
        help="Withdrawal monitoring records for this unit"
    )

    withdrawal_monitor_count = fields.Integer(
        string='Withdrawal Monitors',
        compute='_compute_withdrawal_monitor_count'
    )

    @api.depends('withdrawal_monitor_ids')
    def _compute_withdrawal_monitor_count(self):
        for record in self:
            record.withdrawal_monitor_count = len(record.withdrawal_monitor_ids)

    def action_view_withdrawal_monitors(self):
        """Open withdrawal monitors for this unit"""
        self.ensure_one()
        return {
            'name': _('Withdrawal Monitors'),
            'type': 'ir.actions.act_window',
            'res_model': 'withdrawal.monitor',
            'view_mode': 'tree,form',
            'domain': [('building_unit_id', '=', self.id)],
            'context': {
                'default_building_unit_id': self.id,
            },
            'target': 'current',
        }