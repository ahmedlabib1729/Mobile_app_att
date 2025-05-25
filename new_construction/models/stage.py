from odoo import fields, models, api


class ModelName(models.Model):
    _name = "contract.stage"
    _description = 'Description'

    name = fields.Char(required="1")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

class StageLines(models.Model):
    _name = "contract.stage.line"
    _description = 'Description'
    _rec_name = "stage_id"
    stage_id = fields.Many2one("contract.stage")
    prec = fields.Float("Prec %")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    contract_id = fields.Many2one("construction.contract")
class StageLines(models.Model):
    _name = "contract.line.stage.line"
    _description = 'Description'
    _rec_name = "stage_id"
    stage_id = fields.Many2one("contract.stage")
    prec = fields.Float("Prec %")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    contract_line_id = fields.Many2one("construction.contract.line")
    state = fields.Selection(related="contract_line_id.state")



