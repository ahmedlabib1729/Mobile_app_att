# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


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

        # إزالة أي رسوم COD سابقة
        self._remove_cod_fee_line()

        # الحصول على معلومات COD
        cod_transaction = self.transaction_ids.filtered(
            lambda t: t.provider_code == 'cod' and t.state != 'cancel'
        )[:1]

        if not cod_transaction:
            return

        provider = cod_transaction.provider_id

        # التحقق من تفعيل الرسوم
        if not provider.cod_fee_active:
            return

        # التحقق من المنتج
        if not provider.cod_fee_product_id:
            return

        # حساب الرسوم
        payment_method = cod_transaction.payment_method_id
        fee_amount = self._calculate_cod_fee(provider, payment_method)

        if fee_amount <= 0:
            return

        # إنشاء سطر الرسوم
        fee_line_vals = {
            'order_id': self.id,
            'product_id': provider.cod_fee_product_id.id,
            'name': _('Cash on Delivery Fee'),
            'product_uom_qty': 1.0,
            'price_unit': fee_amount,
            'product_uom': provider.cod_fee_product_id.uom_id.id,
        }

        # إضافة الضرائب إن وجدت
        if provider.cod_fee_product_id.taxes_id:
            fee_line_vals['tax_id'] = [(6, 0, provider.cod_fee_product_id.taxes_id.ids)]

        fee_line = self.env['sale.order.line'].create(fee_line_vals)
        self.cod_fee_line_id = fee_line

    def _calculate_cod_fee(self, provider, payment_method):
        """حساب رسوم COD"""
        self.ensure_one()

        # التحقق من الرسوم حسب الدولة
        if payment_method.cod_fee_by_country and payment_method.cod_country_fee_ids:
            country_fee = payment_method.cod_country_fee_ids.filtered(
                lambda f: f.country_id == self.partner_shipping_id.country_id and f.active
            )[:1]

            if country_fee:
                if country_fee.fee_type == 'percent':
                    return (self.amount_untaxed * country_fee.fee_amount) / 100.0
                else:
                    return country_fee.fee_amount

        # استخدام الرسوم الافتراضية من Provider
        if provider.cod_fee_type == 'percent':
            return (self.amount_untaxed * provider.cod_fee_amount) / 100.0
        else:
            return provider.cod_fee_amount

    def _remove_cod_fee_line(self):
        """إزالة سطر رسوم COD"""
        self.ensure_one()
        if self.cod_fee_line_id:
            self.cod_fee_line_id.unlink()
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