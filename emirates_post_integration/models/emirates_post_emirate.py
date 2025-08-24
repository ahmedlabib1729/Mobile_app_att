from odoo import api, fields, models


class EmiratesPostEmirate(models.Model):
    _name = 'emirates.post.emirate'
    _description = 'Emirates Post Emirates'
    _order = 'name'

    emirate_id = fields.Char(
        string='Emirate ID',
        required=True,
        index=True
    )

    name = fields.Char(
        string='Name',
        required=True
    )

    code = fields.Char(
        string='Code',
        required=True
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    _sql_constraints = [
        ('emirate_id_unique', 'UNIQUE(emirate_id)', 'Emirate ID must be unique!'),
    ]