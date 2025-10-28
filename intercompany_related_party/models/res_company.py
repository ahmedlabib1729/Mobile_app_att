# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResCompany(models.Model):
    """
    Extension of res.company to add intercompany configuration counter.
    """
    _inherit = 'res.company'

    intercompany_config_count = fields.Integer(
        string='Intercompany Configurations',
        compute='_compute_intercompany_config_count',
        help="Number of intercompany configurations for this company"
    )

    def _compute_intercompany_config_count(self):
        """Count intercompany configurations"""
        for company in self:
            company.intercompany_config_count = self.env['intercompany.config'].search_count([
                '|',
                ('company_id', '=', company.id),
                ('target_company_id', '=', company.id),
            ])

    def action_view_intercompany_configs(self):
        """Action to view intercompany configurations"""
        self.ensure_one()

        action = self.env['ir.actions.act_window']._for_xml_id(
            'intercompany_related_party.action_intercompany_config'
        )

        action['domain'] = [
            '|',
            ('company_id', '=', self.id),
            ('target_company_id', '=', self.id),
        ]
        action['context'] = {'default_company_id': self.id}

        return action