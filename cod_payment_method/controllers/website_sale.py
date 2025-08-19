# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleCOD(WebsiteSale):

    @http.route(['/shop/payment'], type='http', auth="public", website=True, sitemap=False)
    def shop_payment(self, **post):
        """Override to handle COD fee"""
        # First, call super to ensure order exists
        response = super().shop_payment(**post)

        # Get current order
        order = request.website.sale_get_order()

        if order:
            # Check if we need to add/remove COD fee based on selected payment
            # This happens when returning to payment page
            self._update_cod_fee_for_order(order)

        return response

    def _update_cod_fee_for_order(self, order):
        """Update COD fee based on current state"""
        # Check if order has COD transaction
        cod_tx = order.transaction_ids.filtered(
            lambda t: t.provider_code == 'cod' and t.state not in ['cancel', 'error']
        )

        if cod_tx:
            # Check if provider has fee enabled
            provider = cod_tx[0].provider_id
            if provider.cod_fee_active and not order.cod_fee_line_id:
                order.sudo()._add_cod_fee_line()
        else:
            # Remove COD fee if no COD transaction
            if order.cod_fee_line_id:
                order.sudo()._remove_cod_fee_line()