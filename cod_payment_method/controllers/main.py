# -*- coding: utf-8 -*-

import logging
from odoo import http, _
from odoo.http import request
from odoo.addons.payment.controllers.portal import PaymentPortal

_logger = logging.getLogger(__name__)


class CODController(http.Controller):

    @http.route('/payment/cod/update-fee', type='json', auth='public', website=True)
    def update_cod_fee(self, provider_id=None, add_fee=True, **kwargs):
        """Add or remove COD fee instantly"""
        order = request.website.sale_get_order()
        if not order:
            return {'success': False, 'error': _('No order found')}

        try:
            if add_fee and provider_id:
                # Get the COD provider
                provider = request.env['payment.provider'].sudo().browse(int(provider_id))
                if provider.code != 'cod':
                    return {'success': False, 'error': _('Invalid provider')}

                if not provider.cod_fee_active:
                    return {'success': False, 'error': _('COD fee not active')}

                # Add COD fee
                _logger.info("Adding COD fee to order %s via AJAX", order.name)
                order.sudo()._add_cod_fee_line()

                # Get the fee line for display
                fee_line_html = ""
                if order.cod_fee_line_id:
                    fee_line_html = f"""
                    <tr class="cod_fee_line text-muted">
                        <td>{order.cod_fee_line_id.name}</td>
                        <td class="text-right">
                            <span class="oe_currency_value">{order.cod_fee_line_id.price_subtotal}</span>
                        </td>
                    </tr>
                    """

                return {
                    'success': True,
                    'amount_total': order.amount_total,
                    'amount_total_formatted': request.env['ir.qweb.field.monetary'].value_to_html(
                        order.amount_total, {'display_currency': order.currency_id}
                    ),
                    'fee_amount': order.cod_fee_line_id.price_unit if order.cod_fee_line_id else 0,
                    'fee_line_html': fee_line_html
                }
            else:
                # Remove COD fee
                _logger.info("Removing COD fee from order %s via AJAX", order.name)
                order.sudo()._remove_cod_fee_line()

                return {
                    'success': True,
                    'amount_total': order.amount_total,
                    'amount_total_formatted': request.env['ir.qweb.field.monetary'].value_to_html(
                        order.amount_total, {'display_currency': order.currency_id}
                    ),
                    'fee_amount': 0
                }

        except Exception as e:
            _logger.error("Error updating COD fee: %s", str(e))
            return {'success': False, 'error': str(e)}

    @http.route('/payment/cod/thank-you/<string:reference>', type='http', auth='public', website=True)
    def cod_thank_you(self, reference, **kwargs):
        """Display thank you page for COD orders"""
        tx = request.env['payment.transaction'].sudo().search([
            ('reference', '=', reference),
            ('provider_code', '=', 'cod')
        ], limit=1)

        if not tx:
            return request.redirect('/shop')

        order = tx.sale_order_ids[0] if tx.sale_order_ids else None

        values = {
            'tx': tx,
            'order': order,
            'reference': reference,
            'amount': tx.amount,
            'currency': tx.currency_id,
        }

        return request.render('cod_payment_method.cod_thank_you_page', values)


class CODPaymentPortal(PaymentPortal):

    @http.route(['/shop/payment'], type='http', auth="public", website=True, sitemap=False)
    def shop_payment(self, **post):
        """Override to ensure COD fee state is correct"""
        order = request.website.sale_get_order()

        if order:
            # Check if we have a COD transaction
            cod_tx = order.transaction_ids.filtered(
                lambda t: t.provider_code == 'cod' and t.state not in ['cancel', 'error']
            )

            # If no COD transaction but has COD fee, remove it
            if not cod_tx and order.cod_fee_line_id:
                _logger.info("Removing orphaned COD fee from order %s", order.name)
                order.sudo()._remove_cod_fee_line()

        return super().shop_payment(**post)