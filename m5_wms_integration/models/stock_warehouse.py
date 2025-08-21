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

    # حقول إضافية لعرض معلومات M5
    m5_client_id = fields.Char(
        string='M5 Client ID',
        compute='_compute_m5_info',
        readonly=True
    )

    m5_warehouse_id = fields.Char(
        string='M5 Warehouse ID',
        compute='_compute_m5_info',
        readonly=True
    )

    m5_auto_send = fields.Boolean(
        string='Auto Send Orders',
        compute='_compute_m5_info',
        readonly=True
    )

    @api.depends('m5_config_id')
    def _compute_m5_enabled(self):
        for warehouse in self:
            warehouse.m5_enabled = bool(warehouse.m5_config_id and warehouse.m5_config_id.active)

    @api.depends('m5_config_id')
    def _compute_m5_info(self):
        for warehouse in self:
            if warehouse.m5_config_id:
                warehouse.m5_client_id = warehouse.m5_config_id.client_id
                warehouse.m5_warehouse_id = warehouse.m5_config_id.warehouse_id
                warehouse.m5_auto_send = warehouse.m5_config_id.auto_send_orders
            else:
                warehouse.m5_client_id = False
                warehouse.m5_warehouse_id = False
                warehouse.m5_auto_send = False