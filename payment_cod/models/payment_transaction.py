from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    cod_fee_amount = fields.Monetary(
        string='COD Fee',
        currency_field='currency_id',
        readonly=True
    )

    @api.model
    def _compute_reference(self, provider_code, prefix=None, separator='-', **kwargs):
        """Generate reference for COD"""
        if provider_code == 'cod':
            prefix = prefix or 'COD'
        return super()._compute_reference(provider_code, prefix=prefix, separator=separator, **kwargs)

    def _get_specific_rendering_values(self, processing_values):
        """Override for COD specific values"""
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code == 'cod':
            # Pass all required values for the template
            res.update({
                'api_url': '/payment/cod/process',
                'reference': self.reference,
                'amount': self.amount,
                'currency_id': self.currency_id.id,
                'partner_id': self.partner_id.id,
                'provider_id': self.provider_id.id,
                'transaction_id': self.id,
            })
            _logger.info(f"COD rendering values for {self.reference}: {res}")
        return res

    def _get_specific_processing_values(self, processing_values):
        """Override for COD processing"""
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code == 'cod':
            # Add any COD specific processing values here
            pass
        return res

    def _process_notification_data(self, notification_data):
        """Process COD payment"""
        super()._process_notification_data(notification_data)

        if self.provider_code == 'cod':
            # Set transaction as pending (will be done when delivered)
            self._set_pending()

            # Process COD order
            self._process_cod_order()

            _logger.info(f"COD transaction {self.reference} set to pending")

    def _process_cod_order(self):
        """Process COD order with fees"""
        self.ensure_one()

        if self.provider_code != 'cod':
            return

        # Get sale orders linked to this transaction
        sale_orders = self.sale_order_ids

        if not sale_orders:
            _logger.warning(f"No sale orders linked to COD transaction {self.reference}")
            return

        for order in sale_orders:
            # Add COD fee if applicable
            country = order.partner_shipping_id.country_id or \
                      order.partner_invoice_id.country_id or \
                      order.partner_id.country_id

            if country and self.provider_id:
                # Use _compute_cod_fee instead of _compute_fees
                fee_amount = self.provider_id._compute_cod_fee(
                    order.amount_untaxed,
                    order.currency_id,
                    country
                )

                if fee_amount > 0:
                    self.cod_fee_amount = fee_amount
                    self._add_cod_fee_to_order(order, fee_amount)

            # Confirm order if in draft state
            if order.state == 'draft':
                order.with_context(send_email=True).action_confirm()
                _logger.info(f"COD: Order {order.name} confirmed")

    def _add_cod_fee_to_order(self, order, fee_amount):
        """Add COD fee line to order"""
        # Check if COD fee already exists
        existing_cod_line = order.order_line.filtered(
            lambda l: l.product_id.default_code == 'COD_FEE'
        )

        if existing_cod_line:
            # Update existing line
            existing_cod_line.price_unit = fee_amount
            return

        # Get or create COD fee product
        cod_product = self.env['product.product'].search([
            ('default_code', '=', 'COD_FEE')
        ], limit=1)

        if not cod_product:
            cod_product = self.env['product.product'].create({
                'name': 'Cash on Delivery Fee',
                'default_code': 'COD_FEE',
                'type': 'service',
                'categ_id': self.env.ref('product.product_category_all').id,
                'sale_ok': True,
                'purchase_ok': False,
                'list_price': 0.0,
                'taxes_id': [(5, 0, 0)],
                'invoice_policy': 'order',
            })

        # Add fee line to order
        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': cod_product.id,
            'name': _('Cash on Delivery Fee'),
            'product_uom_qty': 1,
            'price_unit': fee_amount,
            'tax_id': [(5, 0, 0)],
        })

        _logger.info(f"Added COD fee {fee_amount} to order {order.name}")