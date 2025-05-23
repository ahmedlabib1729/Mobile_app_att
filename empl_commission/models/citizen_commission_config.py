from odoo import models, fields

class CitizenCommissionConfig(models.Model):
    _name = 'citizen.commission.config'
    _description = 'Citizen Commission Configuration'

    required_quantity = fields.Integer(string='Required Lines for Commission', default=50, help="The number of invoice lines required in a month to start calculating the commission.")
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self.env.user)

    commission_per_unit = fields.Float(
        string='Commission per Unit',
        default=35.0,
        help="Amount of commission paid for each unit exceeding the required quantity."
    )