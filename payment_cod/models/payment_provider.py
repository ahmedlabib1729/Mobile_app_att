from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64
import logging

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('cod', 'Cash on Delivery')],
        ondelete={'cod': 'set default'}
    )

    cod_country_fee_ids = fields.One2many(
        'cod.country.fee',
        'provider_id',
        string='COD Country Fees',
        help='Configure fees for each country'
    )

    cod_instructions = fields.Text(
        string='COD Instructions',
        translate=True,
        help='Instructions shown to customers when selecting COD',
        default='Payment will be collected upon delivery'
    )

    def _get_default_cod_image(self):
        """Generate default COD image"""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
            <rect width="128" height="128" fill="#4CAF50" rx="8"/>
            <text x="64" y="50" font-family="Arial" font-size="36" font-weight="bold" fill="white" text-anchor="middle">COD</text>
            <text x="64" y="80" font-family="Arial" font-size="14" fill="white" text-anchor="middle">Cash on Delivery</text>
        </svg>'''
        return base64.b64encode(svg_content.encode('utf-8'))

    @api.model_create_multi
    def create(self, vals_list):
        """Set default values for COD providers"""
        for vals in vals_list:
            if vals.get('code') == 'cod':
                if not vals.get('image_128'):
                    vals['image_128'] = self._get_default_cod_image()
                # COD doesn't need redirect
                vals['redirect_form_view_id'] = False

        providers = super().create(vals_list)

        for provider in providers:
            if provider.code == 'cod':
                provider._setup_cod_provider()

        return providers

    def write(self, vals):
        """Update COD providers"""
        res = super().write(vals)
        for record in self:
            if record.code == 'cod':
                if not record.image_128:
                    record.image_128 = record._get_default_cod_image()
                if record.state == 'enabled':
                    record._setup_cod_provider()
        return res

    def _setup_cod_provider(self):
        """Setup COD provider configuration"""
        self.ensure_one()

        # Ensure journal exists
        if not self.journal_id:
            journal = self.env['account.journal'].search([
                ('type', '=', 'bank'),
                ('name', 'ilike', 'COD')
            ], limit=1)

            if not journal:
                journal = self.env['account.journal'].create({
                    'name': 'Cash on Delivery',
                    'type': 'bank',
                    'code': 'COD',
                })

            self.journal_id = journal.id

    def _compute_cod_fee(self, amount, currency, country):
        """Calculate COD fees based on country - Public method for AJAX calls"""
        self.ensure_one()

        if self.code != 'cod':
            return 0.0

        # Find active fee configuration for the country
        country_fee = self.cod_country_fee_ids.filtered(
            lambda f: f.country_id.id == country.id and f.active
        ) if country else False

        if not country_fee:
            _logger.info(f"No COD fee configuration found for country {country.name if country else 'Unknown'}")
            return 0.0

        country_fee = country_fee[0]

        # Check amount limits
        if country_fee.min_amount and amount < country_fee.min_amount:
            return 0.0
        if country_fee.max_amount and amount > country_fee.max_amount:
            return 0.0

        # Calculate fee
        if country_fee.fee_type == 'fixed':
            if country_fee.currency_id != currency:
                return country_fee.currency_id._convert(
                    country_fee.fee_amount,
                    currency,
                    self.env.company,
                    fields.Date.today()
                )
            return country_fee.fee_amount
        else:
            return amount * (country_fee.fee_percentage / 100.0)

    def _compute_fees(self, amount, currency, country):
        """Calculate total fees including COD"""
        self.ensure_one()

        # Check if parent has _compute_fees method
        fees = 0.0
        if hasattr(super(PaymentProvider, self), '_compute_fees'):
            fees = super()._compute_fees(amount, currency, country)

        if self.code == 'cod':
            cod_fee = self._compute_cod_fee(amount, currency, country)
            fees += cod_fee

        return fees

    @api.model
    def _get_compatible_providers(self, *args, country_id=None, **kwargs):
        """Filter providers based on country"""
        providers = super()._get_compatible_providers(*args, country_id=country_id, **kwargs)

        if country_id:
            cod_providers = providers.filtered(lambda p: p.code == 'cod')
            for provider in cod_providers:
                available_countries = provider.cod_country_fee_ids.filtered('active').mapped('country_id')
                if available_countries and country_id not in available_countries.ids:
                    providers -= provider

        return providers

    def _get_redirect_form_view(self, is_validation=False):
        """COD uses inline processing"""
        if self.code == 'cod':
            # Return the template reference as expected by Odoo
            return self.env.ref('payment_cod.cod_inline_form')
        return super()._get_redirect_form_view(is_validation=is_validation)

    def _get_validation_amount(self):
        """COD doesn't require validation"""
        if self.code == 'cod':
            return 0.00
        return super()._get_validation_amount()

    def _get_validation_currency(self):
        """COD validation currency"""
        if self.code == 'cod':
            return self.journal_id.currency_id or self.env.company.currency_id
        return super()._get_validation_currency()