# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class CODController(http.Controller):

    @http.route('/payment/cod/thank-you/<string:reference>', type='http', auth='public', website=True)
    def cod_thank_you(self, reference, **kwargs):
        """Display thank you page for COD orders"""

        # Get the transaction
        tx = request.env['payment.transaction'].sudo().search([
            ('reference', '=', reference),
            ('provider_code', '=', 'cod')
        ], limit=1)

        if not tx:
            return request.redirect('/shop')

        # Get the sale order
        order = tx.sale_order_ids[0] if tx.sale_order_ids else None

        values = {
            'tx': tx,
            'order': order,
            'reference': reference,
            'amount': tx.amount,
            'currency': tx.currency_id,
        }

        return request.render('cod_payment_method.cod_thank_you_page', values)