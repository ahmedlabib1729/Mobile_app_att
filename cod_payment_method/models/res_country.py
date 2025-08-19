# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResCountry(models.Model):
    _inherit = 'res.country'

    cod_available = fields.Boolean(
        string="COD Available",
        default=True,
        help="Is Cash on Delivery available in this country"
    )

    cod_default_fee_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percent', 'Percentage')
    ], string="Default COD Fee Type", default='fixed')

    cod_default_fee_amount = fields.Float(
        string="Default COD Fee",
        help="Default COD fee for this country if not specified in payment method"
    )

    cod_notes = fields.Text(
        string="COD Notes",
        help="Special notes or restrictions for COD in this country"
    )