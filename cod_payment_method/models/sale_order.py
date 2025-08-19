# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    has_cod_fee = fields.Boolean(
        string="Has COD Fee",
        compute='_compute_has_cod_fee',
        store=True
    )

    cod_fee_line_id = fields.Many2one(
        'sale.order.line',
        string="COD Fee Line",
        help="Reference to the COD fee line"
    )

    @api.depends('transaction_ids', 'transaction_ids.provider_code', 'transaction_ids.state')
    def _compute_has_cod_fee(self):
        """Check if order should have COD fee"""
        for order in self:
            # Check if any transaction uses COD
            cod_transactions = order.transaction_ids.filtered(
                lambda t: t.provider_code == 'cod' and t.state not in ['cancel', 'error']
            )
            order.has_cod_fee = bool(cod_transactions)

    def _check_cod_limits(self, provider):
        """التحقق من حدود مبلغ COD"""
        self.ensure_one()
        amount_total = self.amount_total

        if provider.cod_minimum_amount and amount_total < provider.cod_minimum_amount:
            raise ValidationError(
                _('Order amount must be at least %s to use COD payment.') % provider.cod_minimum_amount
            )

        if provider.cod_maximum_amount and amount_total > provider.cod_maximum_amount:
            raise ValidationError(
                _('Order amount cannot exceed %s for COD payment.') % provider.cod_maximum_amount
            )

    def _add_cod_fee_line(self):
        """إضافة سطر رسوم COD للطلب"""
        self.ensure_one()

        _logger.info("=== Starting COD fee addition for order %s ===", self.name)

        # إزالة أي رسوم COD سابقة
        self._remove_cod_fee_line()

        # البحث عن COD provider مباشرة
        cod_provider = self.env['payment.provider'].sudo().search([
            ('code', '=', 'cod'),
            ('state', '=', 'enabled')
        ], limit=1)

        if not cod_provider:
            _logger.error("No active COD provider found")
            return

        _logger.info("COD Provider: %s, Fee Active: %s", cod_provider.name, cod_provider.cod_fee_active)

        # التحقق من تفعيل الرسوم
        if not cod_provider.cod_fee_active:
            _logger.info("COD fee not active for provider %s", cod_provider.name)
            return

        # التحقق من المنتج
        if not cod_provider.cod_fee_product_id:
            _logger.error("No COD fee product configured for provider %s", cod_provider.name)
            return

        # الحصول على payment method
        payment_method = self.env['payment.method'].sudo().search([
            ('code', '=', 'cod'),
            ('provider_ids', 'in', cod_provider.id)
        ], limit=1)

        # حساب الرسوم
        fee_amount = self._calculate_cod_fee(cod_provider, payment_method)

        _logger.info("Calculated COD fee: %s", fee_amount)

        if fee_amount <= 0:
            _logger.info("COD fee amount is 0 or negative, skipping")
            return

        # إنشاء سطر الرسوم
        fee_line_vals = {
            'order_id': self.id,
            'product_id': cod_provider.cod_fee_product_id.id,
            'name': _('رسوم الدفع عند الاستلام'),
            'product_uom_qty': 1.0,
            'price_unit': fee_amount,
            'product_uom': cod_provider.cod_fee_product_id.uom_id.id,
            'is_cod_fee': True,  # تأكد من وجود هذا الحقل
        }

        # إضافة الضرائب إن وجدت
        if cod_provider.cod_fee_product_id.taxes_id:
            fee_line_vals['tax_id'] = [(6, 0, cod_provider.cod_fee_product_id.taxes_id.ids)]

        fee_line = self.env['sale.order.line'].create(fee_line_vals)
        self.cod_fee_line_id = fee_line

        _logger.info("COD fee line created with ID %s, amount %s", fee_line.id, fee_amount)

    def _calculate_cod_fee(self, provider, payment_method):
        """حساب رسوم COD"""
        self.ensure_one()

        _logger.info("=== Calculating COD fee ===")

        # Get shipping country
        shipping_country = self.partner_shipping_id.country_id if self.partner_shipping_id else self.partner_id.country_id
        _logger.info("Shipping country: %s (ID: %s)",
                     shipping_country.name if shipping_country else "None",
                     shipping_country.id if shipping_country else "None")

        # التحقق من الرسوم حسب الدولة
        if payment_method and payment_method.cod_fee_by_country and payment_method.cod_country_fee_ids:
            _logger.info("Checking country-specific fees...")

            country_fee = payment_method.cod_country_fee_ids.filtered(
                lambda f: f.country_id.id == shipping_country.id and f.active
            )[:1]

            if country_fee:
                _logger.info("Found country-specific fee: %s %s for %s",
                             country_fee.fee_amount, country_fee.fee_type, country_fee.country_id.name)

                if country_fee.fee_type == 'percent':
                    fee = (self.amount_untaxed * country_fee.fee_amount) / 100.0
                    _logger.info("Calculated percentage fee: %s%% of %s = %s",
                                 country_fee.fee_amount, self.amount_untaxed, fee)
                    return fee
                else:
                    _logger.info("Using fixed fee: %s", country_fee.fee_amount)
                    return country_fee.fee_amount
            else:
                _logger.info("No active fee found for country %s",
                             shipping_country.name if shipping_country else "None")

        # استخدام الرسوم الافتراضية من Provider
        _logger.info("Using provider default fee")
        _logger.info("Provider fee type: %s, amount: %s", provider.cod_fee_type, provider.cod_fee_amount)

        if provider.cod_fee_type == 'percent':
            fee = (self.amount_untaxed * provider.cod_fee_amount) / 100.0
            _logger.info("Calculated percentage fee: %s%% of %s = %s",
                         provider.cod_fee_amount, self.amount_untaxed, fee)
            return fee
        else:
            _logger.info("Using fixed fee: %s", provider.cod_fee_amount)
            return provider.cod_fee_amount

    def _remove_cod_fee_line(self):
        """إزالة سطر رسوم COD"""
        self.ensure_one()

        # البحث عن أي سطر رسوم COD
        cod_fee_lines = self.order_line.filtered(lambda l: l.is_cod_fee or l.product_id.default_code == 'COD_FEE')

        if cod_fee_lines:
            _logger.info("Removing %s COD fee lines from order %s", len(cod_fee_lines), self.name)
            cod_fee_lines.unlink()
            self.cod_fee_line_id = False

    @api.model
    def create(self, vals):
        """Override to add COD fee if needed"""
        order = super().create(vals)
        if order.has_cod_fee:
            order._add_cod_fee_line()
        return order

    def write(self, vals):
        """Override to handle COD fee updates"""
        res = super().write(vals)

        # التحقق من تغيير طريقة الدفع
        if 'transaction_ids' in vals or 'payment_term_id' in vals:
            for order in self:
                if order.has_cod_fee:
                    order._add_cod_fee_line()
                else:
                    order._remove_cod_fee_line()

        return res

    def action_view_cod_details(self):
        """Action to show COD payment details"""
        self.ensure_one()
        # يمكنك إضافة wizard أو action هنا لعرض تفاصيل COD
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('COD Payment'),
                'message': _('This order uses Cash on Delivery payment method.'),
                'sticky': False,
            }
        }

    def action_confirm(self):
        """التحقق من COD قبل تأكيد الطلب"""
        for order in self:
            cod_transaction = order.transaction_ids.filtered(
                lambda t: t.payment_method_id.code == 'cod' and t.state != 'cancel'
            )[:1]

            if cod_transaction:
                order._check_cod_limits(cod_transaction.provider_id)

        return super().action_confirm()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_cod_fee = fields.Boolean(
        string="Is COD Fee",
        compute='_compute_is_cod_fee',
        store=True
    )

    @api.depends('order_id.cod_fee_line_id')
    def _compute_is_cod_fee(self):
        """تحديد إذا كان السطر هو رسوم COD"""
        for line in self:
            line.is_cod_fee = line == line.order_id.cod_fee_line_id