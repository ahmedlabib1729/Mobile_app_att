# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BrokerAdditionalFee(models.Model):
    """رسوم إضافية بسيطة للوسيط"""
    _name = 'broker.additional.fee'
    _description = 'Broker Additional Fees'
    _order = 'sequence, name'

    name = fields.Char(
        string='Service Name',
        required=True,
        help='Name of the additional service'
    )

    code = fields.Char(
        string='Code',
        required=True,
        help='Short code (e.g., HANDLING)'
    )

    fee_amount = fields.Float(
        string='Fee Amount (EGP)',
        required=True,
        default=0.0,
        help='Fixed fee amount in EGP'
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    auto_apply = fields.Boolean(
        string='Auto Apply',
        default=True,
        help='Automatically apply to all shipments'
    )

    description = fields.Text(
        string='Description',
        help='Optional description'
    )

    @api.constrains('fee_amount')
    def _check_fee_amount(self):
        for record in self:
            if record.fee_amount < 0:
                raise ValidationError(_('Fee amount cannot be negative'))

    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.code}] {record.name} - {record.fee_amount:.0f} EGP"
            result.append((record.id, name))
        return result