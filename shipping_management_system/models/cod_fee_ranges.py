# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CODFeeRange(models.Model):
    """شرائح رسوم COD بسيطة"""
    _name = 'cod.fee.range'
    _description = 'COD Fee Range'
    _order = 'amount_from'

    # ربط مع شركة الشحن أو فئة العميل
    shipping_company_id = fields.Many2one(
        'shipping.company',
        string='Shipping Company',
        ondelete='cascade'
    )

    customer_category_id = fields.Many2one(
        'customer.price.category',
        string='Customer Category',
        ondelete='cascade'
    )

    # النطاق
    amount_from = fields.Float(
        string='From',
        required=True
    )

    amount_to = fields.Float(
        string='To',
        required=True,
        help='Use 0 for unlimited'
    )

    # النسب
    cash_percentage = fields.Float(
        string='Cash %',
        default=1.0
    )

    visa_percentage = fields.Float(
        string='Visa %',
        default=2.0
    )

    @api.constrains('amount_from', 'amount_to')
    def _check_amounts(self):
        for record in self:
            if record.amount_from < 0:
                raise ValidationError(_('From amount cannot be negative!'))
            if record.amount_to > 0 and record.amount_to <= record.amount_from:
                raise ValidationError(_('To amount must be greater than from amount!'))