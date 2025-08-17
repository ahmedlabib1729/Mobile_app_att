# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import werkzeug


class CODController(http.Controller):

    @http.route('/payment/cod/process', type='http', auth='public', csrf=True, methods=['POST', 'GET'])
    def cod_process(self, **post):
        """Process COD payment and redirect to status page"""

        # Get reference from post data
        reference = post.get('reference')

        if reference:
            # Find the transaction
            tx = request.env['payment.transaction'].sudo().search([
                ('reference', '=', reference),
                ('provider_code', '=', 'cod')
            ], limit=1)

            if tx:
                # Process the transaction
                tx._handle_notification_data('cod', post)

        # Always redirect to payment status
        return werkzeug.utils.redirect('/payment/status')