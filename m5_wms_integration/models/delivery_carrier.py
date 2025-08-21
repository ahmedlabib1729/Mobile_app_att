# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('m5_wms', 'M5 WMS')],
        ondelete={'m5_wms': 'set default'}
    )

    # M5 Configuration
    m5_config_id = fields.Many2one(
        'm5.config',
        string='M5 Configuration',
        help='Select M5 WMS configuration'
    )

    m5_service_type = fields.Selection([
        ('standard', 'Standard Delivery'),
        ('express', 'Express Delivery'),
        ('same_day', 'Same Day Delivery'),
    ], string='M5 Service Type', default='standard')

    # حقول محسوبة لعرض معلومات M5
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

    m5_api_url = fields.Char(
        string='M5 API URL',
        compute='_compute_m5_info',
        readonly=True
    )

    @api.depends('m5_config_id')
    def _compute_m5_info(self):
        """حساب معلومات M5"""
        for carrier in self:
            if carrier.m5_config_id:
                carrier.m5_client_id = carrier.m5_config_id.client_id
                carrier.m5_warehouse_id = carrier.m5_config_id.warehouse_id
                carrier.m5_api_url = carrier.m5_config_id.api_url
            else:
                carrier.m5_client_id = False
                carrier.m5_warehouse_id = False
                carrier.m5_api_url = False

    @api.onchange('delivery_type')
    def _onchange_delivery_type_m5(self):
        if self.delivery_type == 'm5_wms':
            # Auto-select first active M5 config
            config = self.env['m5.config'].search([
                ('company_id', '=', self.company_id.id),
                ('active', '=', True)
            ], limit=1)
            if config:
                self.m5_config_id = config

    def m5_rate_shipment(self, order):
        """Calculate shipping rate for M5 WMS"""
        self.ensure_one()

        if not self.m5_config_id:
            return {
                'success': False,
                'price': 0.0,
                'error_message': _('No M5 configuration selected!'),
                'warning_message': False
            }

        # حساب الوزن الإجمالي
        total_weight = sum([
            (line.product_id.weight or 0.0) * line.product_uom_qty
            for line in order.order_line.filtered(lambda l: l.product_id.type != 'service')
        ])

        # Default to 1 kg if no weight
        if total_weight <= 0:
            total_weight = 1.0

        # أسعار بسيطة حسب نوع الخدمة
        service_prices = {
            'standard': 5.0,  # Standard delivery
            'express': 10.0,  # Express delivery
            'same_day': 15.0,  # Same day delivery
        }

        base_price = service_prices.get(self.m5_service_type, 5.0)

        # حساب السعر: سعر أساسي + (وزن × سعر لكل كيلو)
        price_per_kg = 2.0
        shipping_cost = base_price + (total_weight * price_per_kg)

        return {
            'success': True,
            'price': shipping_cost,
            'error_message': False,
            'warning_message': _(
                'M5 WMS %(service)s\nWeight: %(weight).2f kg',
                service=dict(self._fields['m5_service_type'].selection).get(self.m5_service_type),
                weight=total_weight
            ) if self.m5_config_id.debug_mode else False
        }

    def m5_send_shipping(self, pickings):
        """This is called when delivery order is created"""
        self.ensure_one()

        # Just validate configuration exists
        if not self.m5_config_id:
            raise UserError(_('No M5 configuration found for this delivery method!'))

        # The actual sending is done manually via button
        return True