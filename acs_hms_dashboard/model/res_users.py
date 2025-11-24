# -*- coding: utf-8 -*-
# Part of AlmightyCS. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _

DASHBOARD_FIELDS = ['acs_dashboard_color']

class ResUsers(models.Model):
    _inherit = "res.users"

    acs_dashboard_color = fields.Char(string='HMS Dashboard Color', default="#1C67CA")

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + DASHBOARD_FIELDS

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + DASHBOARD_FIELDS