from odoo import api, exceptions, fields, models, _


class CommissionTypes(models.Model):
    _name = "commission.types"

    name = fields.Char()


class SaleCommission(models.Model):
    _name = "sale.commission"
    _description = "Commission in sales"

    def calculate_section(self, base):
        self.ensure_one()
        for section in self.sections:
            if section.amount_from <= base <= section.amount_to:
                return base * section.percent / 100.0
        return 0.0

    salesmen = fields.Many2many(comodel_name='res.partner')
    sales_team = fields.Many2many(comodel_name='crm.team')

    name = fields.Char('Name', required=True)
    commission_type = fields.Selection(
        selection=[("fixed", "Fixed percentage"),
                   ("section", "By sections")],
        string="Type", required=True, default="fixed")
    apply_to = fields.Selection(
        selection=[("salesman", "Salesman"),
                   ("team", "Sales Team")],
        string="Apply to", required=True, default="salesman")

    fix_qty = fields.Float(string="Fixed percentage")
    leader_fix_qty = fields.Float(string="Leader Fixed percentage")
    sections = fields.One2many(
        comodel_name="sale.commission.section", inverse_name="commission")
    active = fields.Boolean(default=True)
    contract_state = fields.Selection(
        [('open', 'Contract Based'),
         ('paid', 'Payment Based')], string='Contract Status',
        required=True, default='open')


class SaleCommissionSection(models.Model):
    _name = "sale.commission.section"
    _description = "Commission section"

    commission = fields.Many2one("sale.commission", string="Commission")
    amount_from = fields.Float(string="From")
    amount_to = fields.Float(string="To")
    percent = fields.Float(string="Percent", required=True)
    leader_percent = fields.Float(string="Leader Percent", required=True)

    @api.constrains('amount_from', 'amount_to')
    def _check_amounts(self):
        if self.amount_to < self.amount_from:
            raise exceptions.ValidationError(
                _("The lower limit cannot be greater than upper one."))


class CommissionLine(models.Model):
    _name = "commission.line"
    _description = "Commission line"

    Commission_date = fields.Date("Commission Date")
    commission = fields.Many2one("ownership.contract", string="Contract")
    comm_types = fields.Many2one('commission.types', string="Commission Types")
    salesman = fields.Many2one(
        comodel_name="res.partner", required=True, ondelete="restrict")
    amount = fields.Float(string="Total Amount", compute="_calc_total_amount", store=True, digits=(16, 4))
    date = fields.Date(string="Date")
    building_unit = fields.Many2one('product.template', 'Building Unit',
                                    domain=[('is_property', '=', True), ('state', '=', 'free')], required=True, related='commission.building_unit')

    u_amount = fields.Float("Unit Amount")
    amount_prg = fields.Float("Unit Percentage Amount", compute="_calc_amount_prg", store=True,)
    u_percentage = fields.Float("Unit Percentage")
    type = [
        ('fix', 'Fixed'),
        ('percentage', 'Percentage'),
    ]
    u_type = fields.Selection(string="U.Value Type", selection=type, required=True)
    s_type = fields.Selection(string="S.Value Type", selection=type, required=True)

    type = fields.Selection(string="Value Type", selection=type)

    s_amount = fields.Float(string="Sales Amount", digits=(16, 4))
    s_percentage = fields.Float("Sales Percentage", digits=(16, 4))

    @api.depends('u_amount','u_percentage','s_amount','s_percentage')
    def _calc_total_amount(self):
        amount = 0.0
        for record in self:
            if record.u_amount and record.s_amount:
                record.amount = record.s_amount
            if record.u_percentage and record.s_percentage:
                amount = (record.u_percentage * (record.s_percentage/100))
                record.amount = record.commission.pricing * (amount/100)
            if record.u_percentage and record.s_amount:
                record.amount = record.s_amount
            if record.u_amount and record.s_percentage:
                amount = record.u_amount * (record.s_percentage / 100)
                record.amount = amount

    @api.depends('u_percentage')
    def _calc_amount_prg(self):
        for record in self:
            record.amount_prg = record.commission.pricing * (record.u_percentage / 100)


class ownership_contract(models.Model):
    """Invoice inherit to add salesman"""
    _inherit = "ownership.contract"

    def action_confirm(self):
        super(ownership_contract, self).action_confirm()
        self.get_commission()

    @api.depends('commission_line')
    def _compute_commission_total(self):
        for record in self:
            for line in record.commission_line:
                record.commission_total += line.amount

    @api.model
    def _get_default_team(self):
        return self.env['crm.team']._get_default_team_id()

    team_id = fields.Many2one('crm.team', 'Sales Channel', change_default=True, default=_get_default_team, oldname='section_id')
    Commission_date = fields.Date()
    commission_total = fields.Float(
        string="Commissions", compute="_compute_commission_total",
        store=True)
    commission_line = fields.One2many(
        comodel_name="commission.line", inverse_name="commission")

    def get_commission(self):
        comm_line_obj = self.env['commission.line']
        commissions = self.env['sale.commission'].search([])
        user_ids = []

        # for record in self:
        #     for commission in record.commission_line:
        #         commission.unlink()
        for record in self:
            if record.user_id:
                user_ids.append(record.user_id.id)
            for member in record.team_id.member_ids:
                user_ids.append(member.id)
            for rec in record.team_id:
                if rec.user_id:
                    user_ids.append(rec.user_id.id)
            user_ids= list(set(user_ids))
            for user in user_ids:
                total_commission=0
                for commission in commissions:
                    user_exist=0
                    if commission.apply_to == 'salesman':
                        for comm_user in commission.salesmen:
                            if comm_user.id == user:
                                user_exist = 1
                        if user_exist:
                            if commission.commission_type == 'fixed':
                                if commission.contract_state == 'open':
                                    total_commission += record.total_amount*commission.fix_qty / 100.0
                            else: # by section
                                if commission.contract_state == 'open':
                                    total_commission += commission.calculate_section(record.total_amount)
                    elif commission.apply_to == 'team':
                        leader=0
                        for team in commission.sales_team:
                            for team_user in team.member_ids:
                                if user == team_user.id:
                                    user_exist = 1
                                if user == team.user_id.id:
                                    leader = 1
                                    user_exist = 1
                        if user_exist:
                            if leader:
                                if commission.commission_type == 'fixed':
                                    if commission.contract_state == 'open':
                                        total_commission += record.total_amount*commission.leader_fix_qty / 100.0
                                else: # by section
                                    if commission.contract_state == 'open':
                                        total_commission+=record.total_amount*commission.leader_fix_qty / 100.0
                            else:
                                if commission.commission_type=='fixed':
                                    if commission.contract_state=='open':
                                        total_commission+=record.total_amount*commission.fix_qty /100.0
                                else: # by section
                                    if commission.contract_state=='open':
                                        total_commission+=record.total_amount*commission.fix_qty / 100.0
                    if total_commission>0:
                        comm_line_obj.create({'date':record.date,'salesman':user,'amount':total_commission,
                                              'commission':record.id})


    def get_commission_paid(self, installment_amount, commission_date):
        comm_line_obj = self.env['commission.line']
        commissions = self.env['sale.commission'].search([])
        user_ids=[]
        for record in self:
            if record.user_id:
                user_ids.append(record.user_id.id)
            for member in record.team_id.member_ids:
                user_ids.append(member.id)
            for rec in record.team_id:
                if rec.user_id:
                    user_ids.append(rec.user_id.id)
            user_ids= list(set(user_ids))
            for user in user_ids:
                total_commission=0
                for commission in commissions:
                    user_exist=0
                    if commission.apply_to=='salesman':
                        for comm_user in commission.salesmen:
                            if comm_user.id==user:
                                user_exist=1
                        if user_exist:
                            if commission.commission_type=='fixed':
                                if commission.contract_state=='paid':
                                    total_commission+=((installment_amount)*commission.fix_qty / 100.0)
                            else: # by section
                                if commission.contract_state=='paid':
                                    total_commission+= commission.calculate_section(installment_amount)
                    elif commission.apply_to=='team':
                        leader=0
                        for team in commission.sales_team:
                            for team_user in team.member_ids:
                                if user==team_user.id:
                                    user_exist=1
                                if user==team.user_id.id:
                                    leader=1
                                    user_exist=1
                        if user_exist:
                            if leader:
                                if commission.commission_type=='fixed':
                                    if commission.contract_state=='paid':
                                        total_commission+=((installment_amount)*commission.leader_fix_qty / 100.0)
                                else: # by section
                                    if commission.contract_state=='paid':
                                        total_commission+=installment_amount*commission.leader_fix_qty / 100.0
                            else:
                                if commission.commission_type=='fixed':
                                    if commission.contract_state=='paid':
                                        total_commission+=((installment_amount)*commission.fix_qty / 100.0)
                                else: # by section
                                    if commission.contract_state=='paid':
                                        total_commission+=installment_amount*commission.fix_qty / 100.0
                    if total_commission>0:
                        comm_line_obj.create({'date':commission_date,'salesman':user,'amount':total_commission, 'commission':record.id})

