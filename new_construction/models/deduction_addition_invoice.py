from odoo import models, fields, api


class DeductionLines(models.Model):
    _name = "contract.deduction.lines.invoice"
    type = fields.Selection([('deduction', 'Deduction'), ('addition', 'Additional')], string="Type",
                            default='deduction')
    sub_type = fields.Selection([('owner', 'Owner'), ('supconstractor', 'supconstractor')], string="Type")
    name = fields.Many2one("contract.deduction.allowance", string="Name", domain="[('type','=',type) ]")
    account_id = fields.Many2one(related='name.account_id', string="Account ID", store=True, index=True)
    is_precentage = fields.Boolean("Is Precentage")
    precentage = fields.Float("Precentage")
    value = fields.Float("Total Value", compute='_calculate_down_payment', store=True, index=True)
    invoice_id = fields.Many2one("account.invoice")
    contract_id = fields.Many2one(related='invoice_id.contract_id', store=True, index=True, string="Contract")
    value_contract = fields.Float(string='deduction / additional contract value', compute='get_contract_value',
                                  store=True, index=True)
    project_id = fields.Many2one(comodel_name='project.project', string='Project', related="invoice_id.project_id",
                                 store=True)
    contract_id = fields.Many2one(related='invoice_id.contract_id', string="Contract", store=True, index=True)
    contract_date = fields.Date \
        (related='contract_id.date', string="Contract Date", store=True, index=True)
    partner_id = fields.Many2one(related="invoice_id.partner_id", store=True, index=True)

    @api.depends('invoice_id.contract_id', 'name')
    def get_contract_value(self):
        for rec in self:
            rec.value_contract = 0
            item_ded = self.env['contract.deduction.allowance.lines'].search([('name', '=', rec.name.id),
                                                                              ('contract_id', '=',
                                                                               rec.invoice_id.contract_id.id)], limit=1)
            if item_ded:
                rec.value_contract = item_ded.is_down_payment

    move_id = fields.Many2one("account.move")
    last_value = fields.Float("Previous Value")
    current_value = fields.Float("Current Value", compute='_get_current_value', index=True, store=True)

    # @api.depends('invoice_id')
    # def get_last_value(self):
    #     for rec in self:
    #         if not rec.last_value:
    #              rec.last_value =0
    #
    #         if rec.invoice_id.id:
    #             invoice_ids = self.env['account.invoice'].search([('contract_id','=',rec.invoice_id.contract_id.id),
    #                                                               ('id','<',rec.invoice_id.id) ],order='id asc')
    #             last_v=0
    #
    #             for inv in invoice_ids.deduction_ids:
    #
    #                 if inv.name == rec.name:
    #                     last_v += inv.value
    #             rec.last_value=last_v
    @api.depends('precentage', 'invoice_id.work_value_total')
    def _get_current_value(self):
        for rec in self:
            rec.current_value = (rec.precentage * rec.invoice_id.work_value_total) / 100
            if rec.current_value < 0:
                rec.current_value = rec.current_value * -1

    @api.depends('precentage', 'invoice_id.current_total_value')
    def _calculate_down_payment(self):
        t_values = []
        for val in self.invoice_id.invoice_line:
            t_values.append(val.t_value)
        for rec in self:
            if rec.is_precentage == True:
                rec.value = (rec.precentage / 100) * sum(t_values)
            else:
                rec.value = rec.precentage

    @api.onchange('name')
    def _onchange_prectenage(self):
        self.is_precentage = self.name.is_precentage
        self.precentage = self.name.precentage


class AdditionLines(models.Model):
    _name = "contract.addition.lines.invoice"
    type = fields.Selection([('deduction', 'Deduction'), ('addition', 'Additional')], string="Type")
    sub_type = fields.Selection([('owner', 'Owner'), ('supconstractor', 'supconstractor')], string="Type")
    name = fields.Many2one("contract.deduction.allowance", string="Name", domain="[('type','=',type) ]")
    account_id = fields.Many2one(related='name.account_id', string="Account ID", store=True, index=True)
    is_precentage = fields.Boolean("Is Precentage")
    precentage = fields.Float("Precentage")
    value = fields.Float("Total Value", compute='_calculate_down_payment', store=True, index=True)
    invoice_id = fields.Many2one("account.invoice")
    contract_id = fields.Many2one(related='invoice_id.contract_id', store=True, index=True, string="Contract")
    last_value = fields.Float("Previous Value")
    current_value = fields.Float("Current Value", compute='_get_current_value', store=True, index=True)
    value_contract = fields.Float(string='deduction / additional contract value', compute='get_contract_value',
                                  store=True, index=True)

    project_id = fields.Many2one(comodel_name='project.project', string='Project', related="invoice_id.project_id",
                                 store=True)
    contract_id = fields.Many2one(related='invoice_id.contract_id', string="Contract", store=True, index=True)
    contract_date = fields.Date(related='contract_id.date', string="Contract Date", store=True, index=True)
    project_id = fields.Many2one(comodel_name='project.project', string='Project', related="invoice_id.project_id",
                                 store=True)
    contract_id = fields.Many2one(related='invoice_id.contract_id', string="Contract", store=True, index=True)
    contract_date = fields.Date(related='contract_id.date', string="Contract Date", store=True, index=True)
    partner_id = fields.Many2one(related="invoice_id.partner_id", store=True, index=True)

    @api.depends('invoice_id.contract_id', 'name')
    def get_contract_value(self):
        for rec in self:
            rec.value_contract = 0
            item_ded = self.env['contract.deduction.allowance.lines'].search([('name', '=', rec.name.id),
                                                                              ('contract_id', '=',
                                                                               rec.invoice_id.contract_id.id)], limit=1)
            if item_ded:
                rec.value_contract = item_ded.is_down_payment

    # @api.depends('invoice_id')
    # def get_last_value(self):
    #     for rec in self:
    #         rec.last_value =0
    #
    #         if rec.invoice_id:
    #             invoice_ids = self.env['account.invoice'].search([('contract_id','=',rec.invoice_id.contract_id.id)
    #                                                                  ,('id','<',rec.invoice_id.id) ],order='id asc')
    #             last_v=0
    #             for inv in invoice_ids.allowance_ids:
    #                 if inv.name == rec.name:
    #                    last_v += inv.value
    #             rec.last_value = last_v
    @api.depends('last_value', 'value')
    def _get_current_value(self):
        for rec in self:
            rec.current_value = rec.value - rec.last_value
            if rec.current_value < 0:
                rec.current_value = rec.current_value * -1

    @api.depends('precentage', 'invoice_id.current_total_value')
    def _calculate_down_payment(self):
        for rec in self:
            if rec.is_precentage == True:
                rec.value = (rec.precentage / 100) * rec.invoice_id.current_total_value
            else:
                rec.value = rec.precentage

    @api.onchange('name')
    def _onchange_prectenage(self):
        self.is_precentage = self.name.is_precentage
        self.precentage = self.name.precentage
