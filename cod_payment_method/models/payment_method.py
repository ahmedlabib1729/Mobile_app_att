# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PaymentMethod(models.Model):
    _inherit = 'payment.method'

    # حقل محسوب لتحديد إذا كانت طريقة الدفع COD
    is_cod_method = fields.Boolean(
        string="Is COD Method",
        compute='_compute_is_cod_method',
        store=True
    )

    # Override image field for COD
    image = fields.Binary(
        compute='_compute_image',
        store=True,
        readonly=False
    )

    # حقول خاصة بـ COD
    cod_country_ids = fields.Many2many(
        'res.country',
        'payment_method_country_rel',
        'method_id',
        'country_id',
        string="Available Countries",
        help="Countries where COD is available. Leave empty to allow all countries."
    )

    cod_fee_by_country = fields.Boolean(
        string="Different Fees by Country",
        help="Set different COD fees for each country"
    )

    cod_country_fee_ids = fields.One2many(
        'payment.method.country.fee',
        'payment_method_id',
        string="Country Fees"
    )

    @api.depends('code')
    def _compute_is_cod_method(self):
        for method in self:
            method.is_cod_method = method.code == 'cod' if method.code else False

    @api.depends('code', 'provider_ids.image_128')
    def _compute_image(self):
        for method in self:
            if method.code == 'cod' and method.provider_ids:
                # Get image from provider if available
                provider = method.provider_ids[0]
                if provider.image_128:
                    method.image = provider.image_128
                else:
                    # Set a default image for COD
                    method.image = False
            elif not method.image:
                method.image = False


class PaymentMethodCountryFee(models.Model):
    """نموذج لتحديد رسوم مختلفة لكل دولة"""
    _name = 'payment.method.country.fee'
    _description = 'COD Fees by Country'
    _rec_name = 'country_id'

    payment_method_id = fields.Many2one(
        'payment.method',
        string="Payment Method",
        required=True,
        ondelete='cascade'
    )

    country_id = fields.Many2one(
        'res.country',
        string="Country",
        required=True
    )

    fee_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percent', 'Percentage')
    ], string="Fee Type", default='fixed', required=True)

    fee_amount = fields.Float(
        string="Fee Amount",
        required=True,
        help="Fixed amount or percentage to charge for COD in this country"
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id
    )

    active = fields.Boolean(
        string="Active",
        default=True
    )

    _sql_constraints = [
        ('country_method_unique', 'unique(payment_method_id, country_id)',
         'You cannot have duplicate country fees for the same payment method!')
    ]