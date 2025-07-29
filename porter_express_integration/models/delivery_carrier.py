# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('porter', 'Porter Express')],
        ondelete={'porter': 'set default'}
    )

    # إعدادات Porter متعددة
    porter_config_ids = fields.Many2many(
        'porter.config',
        'delivery_carrier_porter_config_rel',
        'carrier_id',
        'config_id',
        string='Porter Configurations',
        help='Select Porter configurations for different countries'
    )

    porter_product_code = fields.Selection([
        ('DE', 'Delivery Express'),
        ('SD', 'Same Day'),
        ('ND', 'Next Day'),
    ], string='Porter Service Type', default='DE')

    active_for_sales = fields.Boolean(
        string='Active for Sales',
        default=True,
        help='If unchecked, this delivery method will not appear in sales orders'
    )

    @api.onchange('delivery_type')
    def _onchange_delivery_type_porter(self):
        if self.delivery_type == 'porter':
            # Auto-select all available configs
            configs = self.env['porter.config'].search([
                ('company_id', '=', self.company_id.id),
                ('active', '=', True)
            ])
            if configs:
                self.porter_config_ids = [(6, 0, configs.ids)]

    def get_porter_config(self, partner=None):
        """Get appropriate Porter config based on partner country"""
        self.ensure_one()

        if not self.porter_config_ids:
            raise UserError(_('No Porter configurations assigned to this delivery method!'))

        # If partner provided, try to match country
        if partner and partner.country_id:
            # First try exact country match with default
            config = self.porter_config_ids.filtered(
                lambda c: c.country_id == partner.country_id and c.is_default_for_country and c.active
            )
            if config:
                return config[0]

            # Then try any config for that country
            config = self.porter_config_ids.filtered(
                lambda c: c.country_id == partner.country_id and c.active
            )
            if config:
                return config[0]

        # If no partner or no country match, check if shipping to company's country
        if self.env.company.country_id:
            config = self.porter_config_ids.filtered(
                lambda c: c.country_id == self.env.company.country_id and c.active
            )
            if config:
                default = config.filtered('is_default_for_country')
                return default[0] if default else config[0]

        # Fallback: return first active config
        active_configs = self.porter_config_ids.filtered('active')
        if not active_configs:
            raise UserError(_('No active Porter configuration found!'))

        # Prefer default configs
        default_configs = active_configs.filtered('is_default_for_country')
        return default_configs[0] if default_configs else active_configs[0]

    def porter_rate_shipment(self, order):
        """Calculate shipping rate for Porter Express"""
        self.ensure_one()

        if self.delivery_type != 'porter':
            return super().porter_rate_shipment(order)

        # Get config based on customer country
        try:
            config = self.get_porter_config(order.partner_shipping_id)
        except UserError as e:
            return {
                'success': False,
                'price': 0.0,
                'error_message': str(e),
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

        # يمكنك تخصيص الأسعار حسب الدولة
        base_prices = {
            'KW': 5.0,  # Kuwait
            'SA': 7.0,  # Saudi Arabia
            'AE': 6.0,  # UAE
            'QA': 6.5,  # Qatar
            'BH': 5.5,  # Bahrain
            'OM': 7.5,  # Oman
            'EG': 4.0,  # Egypt
            'JO': 5.5,  # Jordan
        }

        # Service type multipliers
        service_multipliers = {
            'DE': 1.0,  # Delivery Express (standard)
            'SD': 1.5,  # Same Day (50% extra)
            'ND': 0.8,  # Next Day (20% discount)
        }

        country_code = config.country_code
        base_price = base_prices.get(country_code, 5.0)
        service_multiplier = service_multipliers.get(self.porter_product_code, 1.0)

        # Price calculation
        price_per_kg = 2.0
        shipping_cost = (base_price + (total_weight * price_per_kg)) * service_multiplier

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
                'Porter Express (%(service)s) to %(country)s\n'
                'Weight: %(weight).2f kg',
                service=dict(self._fields['porter_product_code'].selection).get(self.porter_product_code),
                country=config.country_id.name,
                weight=total_weight
            ) if config.debug_mode else False
        }

    def porter_send_shipping(self, pickings):
        """Send shipment to Porter Express"""
        self.ensure_one()

        if self.delivery_type != 'porter':
            return super().porter_send_shipping(pickings)

        # This is called when confirming delivery
        # The actual shipment creation is done via wizard
        # Just validate configuration exists
        for picking in pickings:
            partner = picking.partner_id
            try:
                config = self.get_porter_config(partner)
                if not config:
                    raise UserError(_('No Porter configuration found for this delivery!'))
            except Exception as e:
                raise UserError(_(
                    'Porter configuration error for picking %(picking)s:\n%(error)s',
                    picking=picking.name,
                    error=str(e)
                ))

        return True