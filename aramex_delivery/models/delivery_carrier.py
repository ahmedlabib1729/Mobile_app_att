# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('aramex', 'Aramex')],
        ondelete={'aramex': 'set default'}
    )

    # ========== Aramex Configuration ==========
    aramex_config_ids = fields.Many2many(
        'aramex.config',
        'delivery_carrier_aramex_config_rel',
        'carrier_id',
        'config_id',
        string='Aramex Configurations',
        help='Select Aramex configurations for different countries'
    )

    # ========== Default Service Settings ==========
    aramex_default_product_group = fields.Selection([
        ('EXP', 'Express'),
        ('DOM', 'Domestic'),
    ], string='Default Product Group', default='DOM')

    aramex_default_product_type = fields.Selection([
        ('OND', 'Overnight Document'),
        ('ONP', 'Overnight Parcel'),
        ('PDX', 'Priority Document Express'),
        ('PPX', 'Priority Parcel Express'),
        ('DDX', 'Deferred Document Express'),
        ('DPX', 'Deferred Parcel Express'),
        ('GDX', 'Ground Document Express'),
        ('GPX', 'Ground Parcel Express'),
        ('EPX', 'Economy Parcel Express'),
    ], string='Default Product Type', default='ONP')

    aramex_default_payment_type = fields.Selection([
        ('P', 'Prepaid'),
        ('C', 'Collect'),
        ('3', 'Third Party'),
    ], string='Default Payment Type', default='P')

    aramex_default_service_codes = fields.Char(
        string='Default Service Codes',
        help='Comma-separated service codes (e.g., CODS for COD service)'
    )

    # ========== Additional Settings ==========
    aramex_label_report_id = fields.Integer(
        string='Label Report ID',
        default=9729,
        help='Aramex report ID for label format'
    )

    aramex_label_report_type = fields.Selection([
        ('URL', 'URL'),
        ('RPT', 'Report'),
    ], string='Label Report Type', default='URL')

    aramex_auto_create_pickup = fields.Boolean(
        string='Auto Create Pickup',
        default=True,
        help='Automatically create pickup request when creating shipment'
    )

    aramex_test_mode = fields.Boolean(
        string='Test Mode',
        default=False,
        help='Use Aramex test/staging environment'
    )

    # ========== Pricing Settings ==========
    aramex_base_price = fields.Float(
        string='Base Price',
        default=10.0,
        help='Base price for shipping calculation'
    )

    aramex_price_per_kg = fields.Float(
        string='Price per KG',
        default=2.0,
        help='Additional price per kilogram'
    )

    aramex_cod_fee = fields.Float(
        string='COD Fee',
        default=5.0,
        help='Additional fee for Cash on Delivery service'
    )

    # ========== API Methods ==========
    @api.onchange('delivery_type')
    def _onchange_delivery_type_aramex(self):
        """Auto-configure when Aramex is selected"""
        if self.delivery_type == 'aramex':
            # Auto-select all available configs
            configs = self.env['aramex.config'].search([
                ('company_id', '=', self.company_id.id),
                ('active', '=', True)
            ])
            if configs:
                self.aramex_config_ids = [(6, 0, configs.ids)]

    def get_aramex_config(self, partner=None):
        """Get appropriate Aramex config based on partner country"""
        self.ensure_one()

        if not self.aramex_config_ids:
            raise UserError(_('No Aramex configurations assigned to this delivery method!'))

        # If partner provided, try to match country
        if partner and partner.country_id:
            # First try exact country match with default
            config = self.aramex_config_ids.filtered(
                lambda c: c.country_id == partner.country_id and c.is_default_for_country and c.active
            )
            if config:
                return config[0]

            # Then try any config for that country
            config = self.aramex_config_ids.filtered(
                lambda c: c.country_id == partner.country_id and c.active
            )
            if config:
                return config[0]

        # If no partner or no country match, check if shipping to company's country
        if self.env.company.country_id:
            config = self.aramex_config_ids.filtered(
                lambda c: c.country_id == self.env.company.country_id and c.active
            )
            if config:
                default = config.filtered('is_default_for_country')
                return default[0] if default else config[0]

        # Fallback: return first active config
        active_configs = self.aramex_config_ids.filtered('active')
        if not active_configs:
            raise UserError(_('No active Aramex configuration found!'))

        # Prefer default configs
        default_configs = active_configs.filtered('is_default_for_country')
        return default_configs[0] if default_configs else active_configs[0]

    def aramex_rate_shipment(self, order):
        """Calculate shipping rate for Aramex"""
        self.ensure_one()

        if self.delivery_type != 'aramex':
            return super().aramex_rate_shipment(order)

        # Get config based on customer country
        try:
            config = self.get_aramex_config(order.partner_shipping_id)
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

        # Country-specific base prices (can be configured per country)
        country_multipliers = {
            'SA': 1.2,  # Saudi Arabia - 20% extra
            'AE': 1.0,  # UAE - standard price
            'KW': 1.1,  # Kuwait - 10% extra
            'QA': 1.15,  # Qatar - 15% extra
            'BH': 1.05,  # Bahrain - 5% extra
            'OM': 1.25,  # Oman - 25% extra
            'EG': 0.8,  # Egypt - 20% discount
            'JO': 0.9,  # Jordan - 10% discount
            'LB': 1.3,  # Lebanon - 30% extra
            'IQ': 1.5,  # Iraq - 50% extra
        }

        # Service type multipliers
        service_multipliers = {
            'ONP': 1.0,  # Overnight Parcel - standard
            'OND': 0.8,  # Overnight Document - 20% less
            'PPX': 1.5,  # Priority Parcel Express - 50% extra
            'PDX': 1.3,  # Priority Document Express - 30% extra
            'EPX': 0.7,  # Economy Parcel Express - 30% less
        }

        country_code = config.country_code
        country_multiplier = country_multipliers.get(country_code, 1.0)
        service_multiplier = service_multipliers.get(self.aramex_default_product_type, 1.0)

        # Calculate base shipping cost
        shipping_cost = (self.aramex_base_price + (total_weight * self.aramex_price_per_kg))
        shipping_cost = shipping_cost * country_multiplier * service_multiplier

        # Add COD fee if applicable
        if order.payment_term_id and 'cod' in order.payment_term_id.name.lower():
            shipping_cost += self.aramex_cod_fee

        # Convert to order currency if needed
        if config.currency_id != order.currency_id:
            shipping_cost = config.currency_id._convert(
                shipping_cost,
                order.currency_id,
                order.company_id,
                order.date_order or fields.Date.today()
            )

        # Prepare warning message with details
        warning_msg = False
        if self.aramex_test_mode:
            warning_msg = _(
                'Aramex (TEST MODE)\n'
                'Service: %(service)s to %(country)s\n'
                'Weight: %(weight).2f kg\n'
                'Base: %(base).2f, Per KG: %(per_kg).2f',
                service=dict(self._fields['aramex_default_product_type'].selection).get(
                    self.aramex_default_product_type),
                country=config.country_id.name,
                weight=total_weight,
                base=self.aramex_base_price,
                per_kg=self.aramex_price_per_kg
            )

        return {
            'success': True,
            'price': shipping_cost,
            'error_message': False,
            'warning_message': warning_msg
        }

    def aramex_send_shipping(self, pickings):
        """Validate Aramex shipping for pickings"""
        self.ensure_one()

        if self.delivery_type != 'aramex':
            return super().aramex_send_shipping(pickings)

        # This is called when confirming delivery
        # The actual shipment creation is done via wizard
        # Just validate configuration exists
        for picking in pickings:
            partner = picking.partner_id
            try:
                config = self.get_aramex_config(partner)
                if not config:
                    raise UserError(_('No Aramex configuration found for this delivery!'))

                # Validate required partner information
                if not partner.city:
                    raise UserError(_('Customer city is required for Aramex shipment!'))
                if not partner.country_id:
                    raise UserError(_('Customer country is required for Aramex shipment!'))
                if not (partner.phone or partner.mobile):
                    raise UserError(_('Customer phone number is required for Aramex shipment!'))

            except Exception as e:
                raise UserError(_(
                    'Aramex configuration error for picking %(picking)s:\n%(error)s',
                    picking=picking.name,
                    error=str(e)
                ))

        return True

    def aramex_cancel_shipment(self, shipments):
        """Cancel Aramex shipments"""
        self.ensure_one()

        # This will be implemented when we add the API integration
        # For now, just mark shipments as cancelled
        for shipment in shipments:
            if shipment.state in ['delivered', 'cancelled']:
                raise UserError(_(
                    'Cannot cancel shipment %(awb)s - already %(state)s',
                    awb=shipment.awb_number,
                    state=shipment.state
                ))
            shipment.action_cancel()

        return True

    def aramex_get_tracking_link(self, picking):
        """Generate tracking link for Aramex shipment"""
        self.ensure_one()

        if picking.aramex_shipment_id and picking.aramex_shipment_id.awb_number:
            return picking.aramex_shipment_id.tracking_url
        return False

    def action_get_aramex_rates(self):
        """Action to test rate calculation"""
        self.ensure_one()

        if not self.delivery_type == 'aramex':
            raise UserError(_('This action is only for Aramex carriers!'))

        # Get the last sale order for testing
        last_order = self.env['sale.order'].search([], limit=1, order='id desc')
        if not last_order:
            raise UserError(_('No sale order found for testing!'))

        result = self.aramex_rate_shipment(last_order)

        message = _(
            'Rate Calculation Test\n'
            'Order: %(order)s\n'
            'Customer: %(customer)s\n'
            'Country: %(country)s\n'
            'Success: %(success)s\n'
            'Price: %(price).2f %(currency)s\n'
            'Error: %(error)s',
            order=last_order.name,
            customer=last_order.partner_id.name,
            country=last_order.partner_shipping_id.country_id.name,
            success=result['success'],
            price=result['price'],
            currency=last_order.currency_id.name,
            error=result.get('error_message', 'None')
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Aramex Rate Test'),
                'message': message,
                'type': 'info',
                'sticky': True,
            }
        }