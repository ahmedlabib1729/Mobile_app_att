from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.payment.controllers.portal import PaymentPortal
import logging

_logger = logging.getLogger(__name__)


class WebsiteSaleCOD(WebsiteSale):

    @http.route(['/shop/payment/validate'], type='http', auth="public", website=True, sitemap=False)
    def payment_validate(self, transaction_id=None, sale_order_id=None, **post):
        """Handle COD payment validation"""

        if transaction_id:
            try:
                tx = request.env['payment.transaction'].sudo().browse(int(transaction_id))

                if tx and tx.exists() and tx.provider_code == 'cod':
                    _logger.info(f"Validating COD transaction {tx.reference}")

                    # Process the COD transaction
                    tx.sudo()._process_notification_data({})

                    # Redirect to confirmation
                    return request.redirect('/shop/confirmation')

            except Exception as e:
                _logger.error(f"Error validating COD payment: {str(e)}")

        return super().payment_validate(transaction_id=transaction_id, sale_order_id=sale_order_id, **post)


class PaymentPortalCOD(PaymentPortal):

    @http.route(['/payment/cod/process'], type='json', auth='public')
    def cod_process_payment(self, transaction_id, **kwargs):
        """Process COD payment"""
        try:
            _logger.info(f"Processing COD payment for transaction {transaction_id}")

            tx_sudo = request.env['payment.transaction'].sudo().browse(int(transaction_id))

            if not tx_sudo.exists():
                return {'success': False, 'error': 'Transaction not found'}

            if tx_sudo.provider_code != 'cod':
                return {'success': False, 'error': 'Not a COD transaction'}

            # Process COD transaction
            tx_sudo._process_notification_data({})

            return {
                'success': True,
                'redirect_url': '/shop/confirmation',
            }

        except Exception as e:
            _logger.error(f"Error processing COD payment: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route(['/payment/cod/feedback'], type='http', auth='public', csrf=False)
    def cod_payment_feedback(self, **data):
        """Handle COD payment feedback"""
        _logger.info(f"COD feedback received: {data}")

        # Get transaction by reference
        tx_ref = data.get('reference')
        if not tx_ref:
            _logger.error("No reference in COD feedback")
            return request.redirect('/shop/payment')

        # Find transaction
        tx_sudo = request.env['payment.transaction'].sudo().search([
            ('reference', '=', tx_ref)
        ], limit=1)

        if not tx_sudo:
            _logger.error(f"Transaction not found for reference {tx_ref}")
            return request.redirect('/shop/payment')

        if tx_sudo.provider_code == 'cod':
            # Process the transaction
            tx_sudo._process_notification_data(data)
            _logger.info(f"COD transaction {tx_sudo.reference} processed successfully")

        return request.redirect('/shop/confirmation')