# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _

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

        # Add COD fee when rendering payment form
        if self.sale_order_ids:
            order = self.sale_order_ids[0]
            provider = self.provider_id
            if provider.cod_fee_active:
                _logger.info("Checking COD fee for order %s", order.name)
                order.sudo()._add_cod_fee_line()

        return res

    def _get_specific_processing_values(self, processing_values):
        """ Override to add COD specific processing values """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'cod':
            return res
        return res

    @api.model
    def create(self, vals):
        """Override to ensure COD fee is added"""
        transaction = super().create(vals)

        # If it's COD, ensure fee is added
        if transaction.provider_code == 'cod':
            for order in transaction.sale_order_ids:
                if transaction.provider_id.cod_fee_active:
                    _logger.info("Adding COD fee to order %s on transaction creation", order.name)
                    order.sudo()._add_cod_fee_line()

        return transaction

    def _send_payment_request(self):
        """ Override to handle COD payment request """
        self.ensure_one()
        if self.provider_code != 'cod':
            return super()._send_payment_request()

        # Ensure COD fee is added before completing
        for order in self.sale_order_ids:
            if self.provider_id.cod_fee_active:
                order.sudo()._add_cod_fee_line()

        # For COD, set as done
        self._set_done()

        # Log the success
        _logger.info("COD transaction %s set to done", self.reference)

        # Return empty dict
        return {}

    def _handle_notification_data(self, provider_code, notification_data):
        """ Override to handle COD notification """
        if provider_code == 'cod':
            tx = self._get_tx_from_notification_data(provider_code, notification_data)
            if tx:
                tx._process_notification_data(notification_data)
            return tx
        return super()._handle_notification_data(provider_code, notification_data)

    def _process_notification_data(self, data):
        """ Process the notification data for COD """
        self.ensure_one()
        if self.provider_code != 'cod':
            return super()._process_notification_data(data)

        # For COD, set as done
        if self.state != 'done':
            self._set_done()
            _logger.info("COD transaction %s processed and set to done", self.reference)

        return True


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