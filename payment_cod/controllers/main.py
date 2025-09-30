from odoo import http
from odoo.http import request
import json


class CODController(http.Controller):

    @http.route('/payment/cod/check_availability', type='json', auth='public', website=True)
    def check_cod_availability(self, country_id=None, amount=None):
        """التحقق من توفر COD للدولة والمبلغ المحدد"""

        if not country_id:
            return {'available': False, 'message': 'No country specified'}

        # البحث عن مزود COD
        cod_provider = request.env['payment.provider'].sudo().search([
            ('code', '=', 'cod'),
            ('state', '=', 'enabled')
        ], limit=1)

        if not cod_provider:
            return {'available': False, 'message': 'COD not available'}

        # التحقق من الدولة
        country_fee = cod_provider.cod_country_fee_ids.filtered(
            lambda f: f.country_id.id == int(country_id) and f.active
        )

        if not country_fee:
            return {'available': False, 'message': 'COD not available in your country'}

        country_fee = country_fee[0]

        # التحقق من حدود المبلغ
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

        # حساب الرسوم
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