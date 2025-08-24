# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('emirates_post', 'Emirates Post')],
        ondelete={'emirates_post': 'set default'}
    )

    emirates_post_config_id = fields.Many2one(
        'emirates.post.config',
        string='Emirates Post Configuration',
        help='Select Emirates Post configuration'
    )

    @api.onchange('delivery_type')
    def _onchange_delivery_type_emirates_post(self):
        if self.delivery_type == 'emirates_post':
            # Auto-select first available config
            config = self.env['emirates.post.config'].search([
                ('company_id', '=', self.company_id.id),
                ('active', '=', True)
            ], limit=1)
            if config:
                self.emirates_post_config_id = config

    def emirates_post_rate_shipment(self, order):
        """Calculate shipping rate for Emirates Post"""
        self.ensure_one()

        if self.delivery_type != 'emirates_post':
            return super().emirates_post_rate_shipment(order)

        if not self.emirates_post_config_id:
            return {
                'success': False,
                'price': 0.0,
                'error_message': _('No Emirates Post configuration assigned!'),
                'warning_message': False
            }

        # Calculate total weight
        total_weight = sum([
            (line.product_id.weight or 0.0) * line.product_uom_qty
            for line in order.order_line.filtered(lambda l: l.product_id.type != 'service')
        ])

        # Default to 500g if no weight
        if total_weight <= 0:
            total_weight = 500

        # Simple price calculation (customize as needed)
        base_price = 15.0  # Base price in AED
        price_per_kg = 5.0
        shipping_cost = base_price + ((total_weight / 1000) * price_per_kg)

        # Convert to order currency if needed
        if self.emirates_post_config_id.company_id.currency_id != order.currency_id:
            shipping_cost = self.emirates_post_config_id.company_id.currency_id._convert(
                shipping_cost,
                order.currency_id,
                order.company_id,
                order.date_order or fields.Date.today()
            )

        return {
            'success': True,
            'price': shipping_cost,
            'error_message': False,
            'warning_message': _(
                'Emirates Post Shipping\n'
                'Weight: %(weight).2f g',
                weight=total_weight
            ) if self.emirates_post_config_id.debug_mode else False
        }

    def emirates_post_send_shipping(self, pickings):
        """Send shipment to Emirates Post"""
        self.ensure_one()

        if self.delivery_type != 'emirates_post':
            return super().emirates_post_send_shipping(pickings)

        # Validate configuration
        if not self.emirates_post_config_id:
            raise UserError(_('No Emirates Post configuration found!'))

        # Just return empty dict for now - manual shipment creation
        # This satisfies webkul module expectations
        return {
            'exact_price': 0.0,
            'tracking_number': '',
            'date_delivery': False,
            'weight': 0.0,
            'attachments': []
        }

    def send_shipping(self, pickings):
        """Override to handle Emirates Post differently"""
        self.ensure_one()

        if self.delivery_type == 'emirates_post':
            # For Emirates Post, return dict format expected by webkul
            return self.emirates_post_send_shipping(pickings)
        else:
            # For others, use standard behavior
            res = super().send_shipping(pickings)
            # If standard Odoo returns list, but webkul expects dict, convert
            if isinstance(res, list) and len(res) == 1:
                return res[0]
            return res