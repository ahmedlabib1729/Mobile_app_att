from odoo import models, fields, api


class contract(models.Model):
    _name = "construction.contract.user"
    _inherit = [  'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    name = fields.Char("Name")
    account_id = fields.Many2one("account.account", string="Parent Account")
    counterpart_account_id = fields.Many2one("account.account", string="partner Account")
    type = fields.Selection([('owner', 'Owner'), ('supconstractor', 'sub contractor')], string="Type")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
