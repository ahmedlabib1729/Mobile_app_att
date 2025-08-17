# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaymentProviderCOD(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('cod', "Cash on Delivery")],
        ondelete={'cod': 'cascade'}
    )

    def _compute_feature_support_fields(self):
        """ Override to specify COD provider features """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'cod').update({
            'support_tokenization': False,
            'support_express_checkout': False,
            'support_manual_capture': False,
            'support_refund': 'full_only',
            'require_currency': False,
        })

    def _cod_get_default_payment_method_codes(self):
        """ Return the default payment method codes for COD """
        return ['cod']


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override to add COD specific rendering values """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'cod':
            return res
        return res

    def _get_specific_processing_values(self, processing_values):
        """ Override to add COD specific processing values """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'cod':
            return res
        return res

    def _send_payment_request(self):
        """ Override to handle COD payment request """
        self.ensure_one()
        if self.provider_code != 'cod':
            return super()._send_payment_request()

        # For COD, immediately set as pending
        self._set_pending()

        # Add COD fee to related sales orders if configured
        for order in self.sale_order_ids:
            order.sudo()._add_cod_fee_line()

        # Return the expected format with the EXACT id that Odoo is looking for
        return {
            'redirect_form_html': '''
<html>
<body>
<form id="payment_redirect_form" action="/payment/status" method="post">
    <input type="hidden" name="csrf_token" value="%s"/>
</form>
<script>document.getElementById("payment_redirect_form").submit();</script>
</body>
</html>
''' % self.env['ir.http']._get_default_csrf_token()
        }

    def _handle_notification_data(self, provider_code, notification_data):
        """ Override to handle COD notification """
        if provider_code == 'cod':
            tx = self._get_tx_from_notification_data(provider_code, notification_data)
            tx._process_notification_data(notification_data)
            return tx
        return super()._handle_notification_data(provider_code, notification_data)

    def _process_notification_data(self, data):
        """ Process the notification data for COD """
        self.ensure_one()
        if self.provider_code != 'cod':
            return super()._process_notification_data(data)

        # For COD, we just ensure it's pending
        if self.state not in ['pending', 'done']:
            self._set_pending()

        return True

    def action_confirm_cod_payment(self):
        """Action to confirm COD payment after delivery"""
        self.ensure_one()
        if self.provider_code == 'cod' and self.state == 'pending':
            self._set_done()
            # Confirm the sale order if not already confirmed
            for order in self.sale_order_ids:
                if order.state in ['draft', 'sent']:
                    order.action_confirm()


class PaymentMethod(models.Model):
    _inherit = 'payment.method'

    @api.model
    def _get_compatible_providers(self, *args, provider_ids=None, **kwargs):
        """Override to handle COD provider compatibility"""
        result = super()._get_compatible_providers(*args, provider_ids=provider_ids, **kwargs)

        # If COD provider exists, ensure it's included
        cod_provider = self.env['payment.provider'].sudo().search([
            ('code', '=', 'cod'),
            ('state', '!=', 'disabled')
        ], limit=1)

        if cod_provider and provider_ids:
            if cod_provider.id in provider_ids and cod_provider.id not in result.ids:
                result |= cod_provider

        return result