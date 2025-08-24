from odoo import api, fields, models


class EmiratesPostZone(models.Model):
    _name = 'emirates.post.zone'
    _description = 'Emirates Post Zones'
    _order = 'name'

    zone_id = fields.Char(
        string='Zone ID',
        required=True,
        index=True
    )

    name = fields.Char(
        string='Name',
        required=True
    )

    emirate_id = fields.Many2one(
        'emirates.post.emirate',
        string='Emirate',
        required=True
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )