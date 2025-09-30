from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class PaymentPortalCOD(http.Controller):

    @http.route('/payment/cod/calculate_fee', type='json', auth='public', website=True)
    def calculate_cod_fee(self, provider_id, amount, currency_id, country_id=None):
        """AJAX endpoint to calculate COD fees"""
        try:
            _logger.info(
                f"Calculating COD fee: provider_id={provider_id}, amount={amount}, currency_id={currency_id}, country_id={country_id}")

            provider = request.env['payment.provider'].sudo().browse(int(provider_id))
            currency = request.env['res.currency'].sudo().browse(int(currency_id))

            # Get country from partner if not provided
            if not country_id:
                # Try to get from the current order's shipping address
                order = request.website.sale_get_order()
                if order:
                    if order.partner_shipping_id and order.partner_shipping_id.country_id:
                        country = order.partner_shipping_id.country_id
                    elif order.partner_invoice_id and order.partner_invoice_id.country_id:
                        country = order.partner_invoice_id.country_id
                    elif order.partner_id and order.partner_id.country_id:
                        country = order.partner_id.country_id
                    else:
                        # Default to UAE if no country found
                        country = request.env['res.country'].sudo().search([('code', '=', 'AE')], limit=1)
                elif request.env.user.partner_id and request.env.user.partner_id.country_id:
                    country = request.env.user.partner_id.country_id
                else:
                    # Default to UAE
                    country = request.env['res.country'].sudo().search([('code', '=', 'AE')], limit=1)
            else:
                country = request.env['res.country'].sudo().browse(int(country_id))

            if not provider or provider.code != 'cod':
                _logger.warning(
                    f"Invalid provider or not COD: provider_id={provider_id}, code={provider.code if provider else 'None'}")
                return {'fee': 0, 'fee_formatted': '0.00 AED', 'total': amount}

            # Calculate fee using the provider method
            fee = provider._compute_cod_fee(float(amount), currency, country)

            _logger.info(f"Calculated COD fee: {fee} for country {country.name if country else 'Unknown'}")

            # Format fee for display
            currency_symbol = currency.symbol or currency.name or 'AED'
            fee_formatted = f"{fee:.2f} {currency_symbol}"

            total_with_fee = float(amount) + fee

            return {
                'fee': fee,
                'fee_formatted': fee_formatted,
                'total': total_with_fee,
                'total_formatted': f"{total_with_fee:.2f} {currency_symbol}",
                'country_name': country.name if country else 'Unknown'
            }

        except Exception as e:
            _logger.error(f"Error calculating COD fee: {str(e)}", exc_info=True)
            return {'fee': 0, 'fee_formatted': '0.00 AED', 'total': amount}

    @http.route('/payment/cod/check_availability', type='json', auth='public', website=True)
    def check_cod_availability(self, country_id=None, amount=None):
        """Check COD availability for country and amount"""
        try:
            if not country_id:
                # Get from current order
                order = request.website.sale_get_order()
                if order and order.partner_shipping_id:
                    country_id = order.partner_shipping_id.country_id.id
                else:
                    return {'available': False, 'message': 'No country specified'}

            # Find COD provider
            cod_provider = request.env['payment.provider'].sudo().search([
                ('code', '=', 'cod'),
                ('state', '=', 'enabled')
            ], limit=1)

            if not cod_provider:
                return {'available': False, 'message': 'COD not available'}

            # Check country configuration
            country_fee = cod_provider.cod_country_fee_ids.filtered(
                lambda f: f.country_id.id == int(country_id) and f.active
            )

            if not country_fee:
                return {'available': False, 'message': 'COD not available in your country'}

            country_fee = country_fee[0]

            # Check amount limits
            if amount:
                amount = float(amount)
                if country_fee.min_amount and amount < country_fee.min_amount:
                    return {
                        'available': False,
                        'message': f'Minimum order amount for COD is {country_fee.min_amount} {country_fee.currency_id.symbol}'
                    }
                if country_fee.max_amount and amount > country_fee.max_amount:
                    return {
                        'available': False,
                        'message': f'Maximum order amount for COD is {country_fee.max_amount} {country_fee.currency_id.symbol}'
                    }

            # Calculate fees
            fee = 0
            if country_fee.fee_type == 'fixed':
                fee = country_fee.fee_amount
            elif amount:
                fee = amount * (country_fee.fee_percentage / 100.0)

            return {
                'available': True,
                'fee': fee,
                'fee_type': country_fee.fee_type,
                'fee_percentage': country_fee.fee_percentage if country_fee.fee_type == 'percentage' else 0,
                'instructions': country_fee.instructions or cod_provider.cod_instructions
            }

        except Exception as e:
            _logger.error(f"Error checking COD availability: {str(e)}", exc_info=True)
            return {'available': False, 'message': 'Error checking availability'}