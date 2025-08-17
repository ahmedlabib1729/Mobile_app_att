# حقول الحالة



from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    # حقول خاصة بـ COD
    is_cod_provider = fields.Boolean(
        string="Is COD Provider",
        compute='_compute_is_cod_provider'
    )

    cod_fee_active = fields.Boolean(
        string="Apply COD Fee",
        help="If checked, a fee will be added to orders using COD payment method"
    )

    cod_fee_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percent', 'Percentage')
    ], string="COD Fee Type", default='fixed')

    cod_fee_amount = fields.Float(
        string="COD Fee Amount",
        help="Fixed amount or percentage to charge for COD"
    )

    cod_fee_product_id = fields.Many2one(
        'product.product',
        string="COD Fee Product",
        domain=[('type', '=', 'service')],
        help="Product used for COD fee in sales orders"
    )

    cod_minimum_amount = fields.Float(
        string="Minimum Order Amount",
        help="Minimum order amount to allow COD payment"
    )

    cod_maximum_amount = fields.Float(
        string="Maximum Order Amount",
        help="Maximum order amount to allow COD payment"
    )

    is_published = fields.Boolean(
        string='Published',
        help="Whether the provider is visible on the website."
    )

    def action_toggle_is_published(self):
        """Toggle the published state"""
        self.ensure_one()
        if self.code == 'cod':
            self.is_published = not self.is_published
            if self.is_published:
                self.state = 'enabled'
                # Enable payment method
                payment_method = self.env['payment.method'].search([
                    ('code', '=', 'cod'),
                    ('provider_ids', 'in', self.id)
                ], limit=1)
                if payment_method:
                    payment_method.active = True
            else:
                self.state = 'disabled'
        return True  # -*- coding: utf-8 -*-


    @api.depends('code')
    def _compute_is_cod_provider(self):
        for provider in self:
            provider.is_cod_provider = provider.code == 'cod'

    def _is_tokenization_supported(self, **kwargs):
        """COD doesn't support tokenization"""
        self.ensure_one()
        if self.code == 'cod':
            return False
        return super()._is_tokenization_supported(**kwargs)

    def _compute_feature_support_fields(self):
        """Compute supported features for COD"""
        super()._compute_feature_support_fields()
        for provider in self.filtered(lambda p: p.code == 'cod'):
            provider.support_manual_capture = False
            provider.support_express_checkout = False
            provider.support_tokenization = False