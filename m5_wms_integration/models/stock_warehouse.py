# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    m5_config_id = fields.Many2one(
        'm5.config',
        string='M5 Configuration',
        help='M5 WMS configuration for this warehouse'
    )

    m5_enabled = fields.Boolean(
        string='M5 Integration Enabled',
        compute='_compute_m5_enabled',
        store=True
    )

    @api.depends('m5_config_id')
    def _compute_m5_enabled(self):
        for warehouse in self:
            warehouse.m5_enabled = bool(warehouse.m5_config_id and warehouse.m5_config_id.active)