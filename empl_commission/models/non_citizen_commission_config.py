from odoo import models, fields


class NonCitizenCommissionConfig(models.Model):
    _name = 'non.citizen.commission.config'
    _description = 'Non-Citizen Commission Configuration'

    name = fields.Char(string='Name', required=True)
    class_id = fields.Char(string='Class ID', required=True)
    commission_rate = fields.Float(string='Commission Rate', required=True,
                                   help="Commission rate as a decimal (e.g., 0.10 for 10%)")
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('class_id_unique', 'unique(class_id)', 'Class ID must be unique!')
    ]