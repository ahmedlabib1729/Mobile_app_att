from odoo import models, fields, api


class Item(models.Model):
    _inherit = 'product.item'

    item_type = fields.Selection([('assay_item', 'Assay Item'), ('contractor_item', 'Contractor Item')], string="Item Type")
    assay_item = fields.Many2one('product.item' ,'Assay Item', domain=[('item_type', '=', 'assay_item')])
