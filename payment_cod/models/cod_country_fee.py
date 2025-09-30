from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CodCountryFee(models.Model):
    _name = 'cod.country.fee'
    _description = 'COD Country Fee Configuration'
    _rec_name = 'country_id'
    _order = 'country_id'

    provider_id = fields.Many2one(
        'payment.provider',
        string='Payment Provider',
        required=True,
        ondelete='cascade',
        domain=[('code', '=', 'cod')]
    )

    country_id = fields.Many2one(
        'res.country',
        string='Country',
        required=True
    )

    fee_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage')
    ], string='Fee Type', default='fixed', required=True)

    fee_amount = fields.Monetary(
        string='Fee Amount',
        currency_field='currency_id',
        help='Fixed fee amount in the selected currency'
    )

    fee_percentage = fields.Float(
        string='Fee Percentage',
        digits='Product Price',
        help='Percentage of the total amount (e.g., 2.5 for 2.5%)'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    min_amount = fields.Monetary(
        string='Minimum Order Amount',
        currency_field='currency_id',
        help='Minimum order amount to allow COD'
    )

    max_amount = fields.Monetary(
        string='Maximum Order Amount',
        currency_field='currency_id',
        help='Maximum order amount to allow COD'
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    instructions = fields.Text(
        string='Country Specific Instructions',
        translate=True,
        help='Additional instructions for this country'
    )

    @api.constrains('fee_type', 'fee_amount', 'fee_percentage')
    def _check_fee_values(self):
        for record in self:
            if record.fee_type == 'fixed' and record.fee_amount < 0:
                raise ValidationError(_('Fee amount must be positive!'))
            if record.fee_type == 'percentage' and not (0 <= record.fee_percentage <= 100):
                raise ValidationError(_('Fee percentage must be between 0 and 100!'))

    @api.constrains('min_amount', 'max_amount')
    def _check_amount_limits(self):
        for record in self:
            if record.min_amount and record.max_amount and record.min_amount > record.max_amount:
                raise ValidationError(_('Minimum amount cannot be greater than maximum amount!'))

    # تم حذف constraint التكرار مؤقتاً
    # @api.constrains('country_id', 'provider_id')
    # def _check_unique_country(self):
    #     for record in self:
    #         existing = self.search([
    #             ('country_id', '=', record.country_id.id),
    #             ('provider_id', '=', record.provider_id.id),
    #             ('id', '!=', record.id)
    #         ])
    #         if existing:
    #             raise ValidationError(_('This country is already configured for this payment provider!'))

    @api.onchange('fee_type')
    def _onchange_fee_type(self):
        if self.fee_type == 'fixed':
            self.fee_percentage = 0.0
        else:
            self.fee_amount = 0.0

    def name_get(self):
        result = []
        for record in self:
            if record.fee_type == 'fixed':
                name = f"{record.country_id.name} - {record.fee_amount} {record.currency_id.symbol}"
            else:
                name = f"{record.country_id.name} - {record.fee_percentage}%"
            result.append((record.id, name))
        return result