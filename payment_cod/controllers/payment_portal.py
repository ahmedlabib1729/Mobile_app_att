from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class PaymentPortalCOD(http.Controller):

    @http.route('/payment/cod/calculate_fee', type='json', auth='public', website=True)
    def calculate_cod_fee(self, provider_id, amount, currency_id, country_id=None):
        """AJAX endpoint to calculate COD fees"""
        try:
            provider = request.env['payment.provider'].sudo().browse(int(provider_id))
            currency = request.env['res.currency'].sudo().browse(int(currency_id))

            # Get country from partner if not provided
            if not country_id:
                # Try to get from the current order's shipping address
                order = request.website.sale_get_order()
                if order and order.partner_shipping_id:
                    country = order.partner_shipping_id.country_id
                elif request.env.user.partner_id:
                    country = request.env.user.partner_id.country_id
                else:
                    country = False
            else:
                country = request.env['res.country'].sudo().browse(int(country_id))

            if not provider or provider.code != 'cod':
                return {'fee': 0, 'fee_formatted': '0.00 AED', 'total': amount}

            # Calculate fee using the provider method
            fee = provider._compute_cod_fee(float(amount), currency, country)

            # Format fee for display
            fee_formatted = f"{fee:.2f} {currency.symbol or 'AED'}"

            total_with_fee = float(amount) + fee

            return {
                'fee': fee,
                'fee_formatted': fee_formatted,
                'total': total_with_fee,
                'total_formatted': f"{total_with_fee:.2f} {currency.symbol or 'AED'}"
            }

        except Exception as e:
            _logger.error(f"Error calculating COD fee: {str(e)}")
            return {'fee': 0, 'fee_formatted': '0.00 AED', 'total': amount}