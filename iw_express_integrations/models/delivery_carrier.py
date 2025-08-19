# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('iw_express', 'IW Express')],
        ondelete={'iw_express': 'set default'}
    )

    # IW Express Settings
    iw_config_ids = fields.Many2many(
        'iw.config',
        'delivery_carrier_iw_config_rel',
        'carrier_id',
        'config_id',
        string='IW Express Configurations',
        help='Select IW Express configurations for different countries'
    )

    iw_service_type = fields.Selection([
        ('PREMIUM', 'Premium'),
        ('INTERNATIONAL', 'International'),
        ('DELIVERY', 'Delivery'),
    ], string='IW Service Type', default='PREMIUM')

    iw_load_type = fields.Selection([
        ('DOCUMENT', 'Document'),
        ('NON-DOCUMENT', 'Non-Document'),
    ], string='IW Load Type', default='NON-DOCUMENT')

    @api.onchange('delivery_type')
    def _onchange_delivery_type_iw(self):
        if self.delivery_type == 'iw_express':
            # Auto-select all available configs
            configs = self.env['iw.config'].search([
                ('company_id', '=', self.company_id.id),
                ('active', '=', True)
            ])
            if configs:
                self.iw_config_ids = [(6, 0, configs.ids)]

    def get_iw_config(self, partner=None):
        """Get appropriate IW config based on partner country"""
        self.ensure_one()

        if not self.iw_config_ids:
            raise UserError(_('No IW Express configurations assigned to this delivery method!'))

        # If partner provided, try to match country
        if partner and partner.country_id:
            # First try exact country match with default
            config = self.iw_config_ids.filtered(
                lambda c: c.country_id == partner.country_id and c.is_default_for_country and c.active
            )
            if config:
                return config[0]

            # Then try any config for that country
            config = self.iw_config_ids.filtered(
                lambda c: c.country_id == partner.country_id and c.active
            )
            if config:
                return config[0]

        # If no partner or no country match, check if shipping to company's country
        if self.env.company.country_id:
            config = self.iw_config_ids.filtered(
                lambda c: c.country_id == self.env.company.country_id and c.active
            )
            if config:
                default = config.filtered('is_default_for_country')
                return default[0] if default else config[0]

        # Fallback: return first active config
        active_configs = self.iw_config_ids.filtered('active')
        if not active_configs:
            raise UserError(_('No active IW Express configuration found!'))

        # Prefer default configs
        default_configs = active_configs.filtered('is_default_for_country')
        return default_configs[0] if default_configs else active_configs[0]

    def iw_express_rate_shipment(self, order):
        """Calculate shipping rate for IW Express"""
        self.ensure_one()

        if self.delivery_type != 'iw_express':
            return super().iw_express_rate_shipment(order)

        # Get config based on customer country
        try:
            config = self.get_iw_config(order.partner_shipping_id)
        except UserError as e:
            return {
                'success': False,
                'price': 0.0,
                'error_message': str(e),
                'warning_message': False
            }

        # Calculate total weight
        total_weight = sum([
            (line.product_id.weight or 0.0) * line.product_uom_qty
            for line in order.order_line.filtered(lambda l: l.product_id.type != 'service')
        ])

        # Default to 1 kg if no weight
        if total_weight <= 0:
            total_weight = 1.0

        # Base prices by country (example rates)
        base_prices = {
            'KW': 3.0,  # Kuwait
            'SA': 8.0,  # Saudi Arabia
            'AE': 5.0,  # UAE
            'QA': 6.0,  # Qatar
            'BH': 4.0,  # Bahrain
            'OM': 7.0,  # Oman
            'EG': 3.5,  # Egypt
            'JO': 5.0,  # Jordan
        }

        # Service type multipliers
        service_multipliers = {
            'PREMIUM': 1.2,  # 20% extra for premium
            'INTERNATIONAL': 1.5,  # 50% extra for international
            'DELIVERY': 1.0,  # Standard rate
        }

        # Document discount
        load_type_multiplier = 0.5 if self.iw_load_type == 'DOCUMENT' else 1.0

        country_code = config.country_code
        base_price = base_prices.get(country_code, 5.0)
        service_multiplier = service_multipliers.get(self.iw_service_type, 1.0)

        # Price calculation
        price_per_kg = 1.5
        shipping_cost = (base_price + (total_weight * price_per_kg)) * service_multiplier * load_type_multiplier

        # Convert to order currency if needed
        if config.currency_id != order.currency_id:
            shipping_cost = config.currency_id._convert(
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
                'IW Express (%(service)s - %(load)s) to %(country)s\n'
                'Weight: %(weight).2f kg',
                service=dict(self._fields['iw_service_type'].selection).get(self.iw_service_type),
                load=dict(self._fields['iw_load_type'].selection).get(self.iw_load_type),
                country=config.country_id.name,
                weight=total_weight
            ) if config.debug_mode else False
        }

    def iw_express_send_shipping(self, pickings):
        """Send shipment to IW Express"""
        self.ensure_one()

        if self.delivery_type != 'iw_express':
            return super().iw_express_send_shipping(pickings)

        # This is called when confirming delivery
        # The actual shipment creation is done via wizard
        # Just validate configuration exists
        for picking in pickings:
            partner = picking.partner_id
            try:
                config = self.get_iw_config(partner)
                if not config:
                    raise UserError(_('No IW Express configuration found for this delivery!'))
            except Exception as e:
                raise UserError(_(
                    'IW Express configuration error for picking %(picking)s:\n%(error)s',
                    picking=picking.name,
                    error=str(e)
                ))

        return True