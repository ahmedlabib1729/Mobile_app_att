# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PorterArea(models.Model):
    _name = 'porter.area'
    _description = 'Porter Express Areas'
    _order = 'country_id, name'

    name = fields.Char(
        string='Area Name',
        required=True
    )

    encrypted_area_id = fields.Char(
        string='Encrypted Area ID',
        required=True,
        help='The encrypted ID from Porter API'
    )

    country_id = fields.Many2one(
        'res.country',
        string='Country',
        required=True
    )

    city_name = fields.Char(
        string='City Name',
        help='City this area belongs to'
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    # للبحث السريع
    _sql_constraints = [
        ('area_id_unique', 'UNIQUE(encrypted_area_id)', 'Area ID must be unique!'),
    ]