from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import ValidationError


class contract(models.Model):
    _name = "construction.contract"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'utm.mixin']
    name = fields.Char("Name", compute='_get_name')
    type = fields.Selection([('owner', 'Owner'), ('supconstractor', 'sub contractor')], string="Type", default='owner')
    project_id = fields.Many2one("project.project", string="Project")
    partner_id_2 = fields.Many2one("res.partner", string="Customer", store=True, index=True)
    date = fields.Date("Date", default=datetime.today())
    recieve_date = fields.Date("Receive Date")
    contract_id = fields.Many2one("construction.contract.user", string="Contract", domain="[('type','=',type)]")
    account_id = fields.Many2one(related="contract_id.account_id", string="Partner Account", store=True, index=True)

    down_payment_prectenge = fields.Float("Down Payment %")
    down_payment_value = fields.Float("Down Payment Value", compute="calculate_down_payment",
                                      store=True, index=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    revenue_account_id = fields.Many2one(related='contract_id.counterpart_account_id', store=True, index=True,
                                         string="Revenue Account")
    # lines_id = fields.One2many("construction.contract.line", "contract_id", readonly=False)
    sub_lines_id = fields.One2many("construction.contract.line", "sup_contract_id")

    total_value = fields.Float(compute='_get_total_value', string="Contract Value")
    deduction_ids = fields.One2many("contract.deduction.allowance.lines", "contract_id",
                                    string="Deductions", domain=[('type', '=', 'deduction')])
    allowance_ids = fields.One2many("contract.deduction.allowance.lines", "contract_id",
                                    string="Allowance", domain=[('type', '=', 'addition')])

    sub_contactor = fields.Many2one("res.partner", string="sub contractor Name")
    date = fields.Date("Date", default=datetime.today())
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm')], string="State", default='draft')
    referance = fields.Char()

    is_sub_contract = fields.Boolean()
    partial_contract = fields.Many2one('construction.contract')
    stage_ids = fields.One2many(
        comodel_name='contract.stage.line',
        inverse_name='contract_id',
        string='stages',
        required=False)



    count_sub = fields.Integer(compute='get_count_sub')
    count_eng = fields.Integer(compute='get_count_sub')
    amount_tax = fields.Float(compute="get_amount_tax")


    # project_id = fields.Many2one("project.project", string="Project", domain="[('type','!=','draft')]")
    lines_id = fields.One2many("construction.contract.line", "contract_id", compute='_onchnage_project', store=True,
                               index=1, readonly=False)
    order_id = fields.Many2one("construction.sale.order", string="Referance Financial Offer")


    @api.depends("project_id")
    def _onchnage_project(self):

        if self.project_id:
            order_id = self.env['construction.sale.order'].search([('project_id', '=', self.project_id.id),
                                                                   ('state', '=', 'confirm')], limit=1)
            lines = []
            for rec in self.lines_id:
                rec.unlink()
            if order_id:
                self.order_id = order_id
                for rec in self.order_id.order_lines:

                    if rec.display_type==False:
                        lines.append((0, 0, {
                            'code': rec.name,
                            'item': rec.item.id,
                            'name': rec.description,
                            'qty': rec.qty,
                            'notes': rec.notes,
                            'tax_ids':[(4,tax.id)for tax in rec.tax_ids] if rec.tax_ids else [],
                            'price_unit': rec.price, 'discount': rec.discount,
                            'type': 'owner', 'tender_id': rec.tender_id.id,


                        }))
                    else:
                        print(">>>>>>>>>>>>>>>..")
                        lines.append((0, 0, {
                            'display_type':rec.display_type,

                            'name': rec.name
                        }))

                if self.type == 'owner':
                    self.lines_id = lines
            else:
                self.order_id = ''
                for rec in self.lines_id:
                    rec.unlink()


    @api.depends('lines_id.tax_ids')
    def get_amount_tax(self):
        for rec in self:
            rec.amount_tax = 0
            for line in rec.lines_id:
                for tax in line.tax_ids:
                    rec.amount_tax += line.total_value * (tax.amount / 100)

    @api.constrains('project_id')
    def check_unique_project(self):
        contract_id = self.env['construction.contract'].search([('is_sub_contract','=',False),('id','!=',self.id),('project_id','=',self.project_id.id)])
        if len(contract_id)>1 and self.type!='supconstractor':
            raise ValidationError("Contract must be unique for each project")

    def action_draft(self):
        temp_id = self.env['construction.engineer'].search([('contract_id','=',self.id) ])
        if temp_id:
            raise ValidationError("You can't reset to draft because you contract have Templates ")
        else :
            self.state='draft'



    @api.onchange("project_id")
    def _onchnage_project_id(self):
        if self.project_id:
            if self.project_id.partner_id:
                self.partner_id_2 = self.project_id.partner_id.id

    @api.depends('project_id')
    def get_count_sub(self):
        for rec in self:
            rec.count_sub = rec.count_eng = 0
            sub_ids = self.env['construction.contract'].search([('partial_contract', '=', self.id)])
            con_ids = self.env['construction.engineer'].search([('contract_id', '=', self.id)])
            if sub_ids:
                rec.count_sub = len(sub_ids)
            if con_ids:
                rec.count_eng = len(con_ids)

    @api.constrains('stage_ids')
    def check_stage_ids(self):
        total_prec = 0
        for rec in self.stage_ids:
            total_prec += rec.prec
        if self.stage_ids and (total_prec < 100 or total_prec > 100):
            raise ValidationError("Please prec must be equal 100")

    def view_partial_contract(self):
        view = self.env.ref('new_construction.view_contract_tree_sub_contract')
        if self.type == 'supconstractor':
            view_form = self.env.ref('new_construction.view_contract_form_sub')
        else:
            view_form = self.env.ref('new_construction.view_contract_form_sub_contract_view')

        return {
            'name': ('Sub Contract'),
            'view_mode': 'tree,form',
            'view_type': 'form',
            'views': [(view.id, 'tree'), (view_form.id, 'form')],
            'res_model': 'construction.contract',
            'domain': [('partial_contract', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_partial_contract': self.id},
            'target': 'current'
        }

    def view_engineer_tem(self):
        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>...",self.id)
        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>...",self.contract_id)
        return {
            'name': ('Template'),
            'view_mode': 'tree,form',
            'res_model': 'construction.engineer',
            'domain': [('contract_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context':{'default_contract_id':self.id,'default_project_id':self.project_id.id,'default_type':self.type},
            'target': 'current'
        }

    def create_partial_contract(self):
        if self.type == 'supconstractor':
            view = self.env.ref('new_construction.view_contract_form_sub')
        else:
            view = self.env.ref('new_construction.view_contract_form')

        return {
            'name': ('SUB Contract'),
            'view_mode': 'form',
            'view_id': view.id,
            'res_model': 'construction.contract',
            'type': 'ir.actions.act_window',

            'target': 'new',
            'context': {
                'default_project_id': self.project_id.id,
                'default_partner_id_2': self.partner_id_2.id,
                'default_contract_id': self.contract_id.id,
                'default_account_id': self.account_id.id,
                'default_revenue_account_id': self.revenue_account_id.id,
                'default_partial_contract': self.id,
                'default_type': self.type,
                'default_is_sub_contract': True
            }
        }

    @api.depends('create_date')
    def _get_name(self):

        for rec in self:
            if rec.type == 'owner':
                rec.name = 'Owner Contract  /' + str(rec.project_id.name) + " /" + str(rec.id).zfill(4)
            elif rec.type == 'supconstractor':
                rec.name = str(rec.project_id.name) + "/" + rec.sub_contactor.name + " /" + str(rec.id).zfill(4)

    @api.depends('lines_id','amount_tax')
    def _get_total_value(self):
        for rec in self:
            rec.total_value = 0
            for record in rec.lines_id:
                rec.total_value += record.total_value
            rec.total_value+=rec.amount_tax
            # if rec.type == 'owner':
            #     for record in rec.lines_id:
            #         rec.total_value += record.total_value
            # elif rec.type == 'supconstractor':
            #     for record in rec.sub_lines_id:
            #         rec.total_value += record.total_value

    @api.depends('down_payment_prectenge', 'total_value')
    def calculate_down_payment(self):
        for rec in self:
            rec.down_payment_value = (rec.down_payment_prectenge / 100) * rec.total_value

    def action_confirm(self):
        self.state = 'confirm'

    def create_engineer_template(self):


        tem_id = self.env['construction.engineer'].create({
            'contract_id': self.id,
            'project_id': self.project_id.id,
        })
        for rec in self.deduction_ids:
            new_id = rec.copy()
            new_id.eng_template_id=tem_id.id
        for rec in self.allowance_ids:
            new_id = rec.copy()
            new_id.eng_template_id=tem_id.id

    def create_engineer_tem(self, project_id, stage, tem_id, prec):

        sub_contract_ids = self.env['construction.contract'].search([('partial_contract', '=', self.id)])
        for rec in self.lines_id:
            if rec.display_type == False and not rec.stage_line_ids:

                m_qty = self.get_remind_qty(rec.id)
                if m_qty == 0:
                    m_qty = rec.qty
                self.env['construction.engineer.lines'].create({
                    'parent_id': tem_id.id,
                    # 'tender_id': rec.tender_id if rec.tender_id else '',
                    'stage_id': stage.id,
                    'remind_qty': abs(m_qty - ((rec.qty * prec) / 100)),
                    'qty': (rec.qty * prec) / 100,
                    'tender_qty': rec.qty,
                    'contract_line_id': rec.id,
                    'item': rec.item.id,
                    'other_prec': prec,
                    'uom_id': rec.uom_id.id,
                    'related_job': rec.related_job.id if rec.related_job else '',
                    'name':rec.name

                })



            elif rec.display_type and not rec.stage_line_ids:
                print("====================================================================", rec.name)
                self.env['construction.engineer.lines'].create({
                    'parent_id': tem_id.id,
                    'display_type': rec.display_type,
                    'name': rec.name,
                    'contract_line_id': rec.id

                })
        if sub_contract_ids:
            for rec in sub_contract_ids.lines_id:
                if rec.display_type == False:
                    if not rec.stage_line_ids:
                        m_qty = self.get_remind_qty(rec.id)
                        if m_qty == 0:
                            m_qty = rec.qty
                        self.env['construction.engineer.lines'].create({
                            'parent_id': tem_id.id,
                            'tender_id': rec.tender_id if rec.tender_id else '',
                            'stage_id': stage.id,
                            'remind_qty': abs(m_qty - ((rec.qty * prec) / 100)),
                            'qty': (rec.qty * prec) / 100,
                            'tender_qty': rec.qty,
                            'contract_line_id': rec.id,
                            'item': rec.item.id, 'other_prec': prec,
                            'uom_id': rec.uom_id.id,
                            'related_job': rec.related_job.id if rec.related_job else '',
                            'name': rec.name

                        })

                elif rec.display_type and not rec.stage_line_ids:
                    self.env['construction.engineer.lines'].create({
                        'parent_id': tem_id.id,
                        'display_type': rec.display_type,
                        'name': rec.name,

                    })

    def get_remind_qty(self, tender):
        lines = self.env['construction.engineer.lines'].search(
            [('contract_line_id', '=', tender), ('parent_id.state', '!=', 'cancel')])

        qty = sum(lines.mapped('qty'))
        return qty
    def unlink(self):
        for rec in self:
            temp_id = self.env['construction.engineer'].search([('contract_id', '=', rec.id)])
            if temp_id:
                raise ValidationError("You can't delete because you contract have Templates")
        res =super().unlink()
        return res


class ContractLine(models.Model):
    _name = "construction.contract.line"
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False, help="Technical field for UX purpose.")
    code = fields.Char("Code")
    contract_id = fields.Many2one("construction.contract")
    project_id = fields.Many2one("project.project")
    sup_contract_id = fields.Many2one("construction.contract")
    item = fields.Many2one('product.item', string='Item')
    name = fields.Text("Description")
    sequence = fields.Integer(string='Sequence', default=10)
    uom_id = fields.Many2one(related='item.uom_id', string="Unit of Measure")
    qty = fields.Float("Quantity")
    notes = fields.Char("Notes")
    price_unit = fields.Float("Price Unit ", )
    discount = fields.Float("Discount % ", )
    total_value = fields.Float("Total value ", compute='_get_total_value', store=True, index=True)
    tender_id = fields.Many2one('construction.tender', string="Tender ID")
    tender_ids = fields.Many2one('construction.tender', string="Tender ID")
    type = fields.Selection([('owner', 'Owner'), ('supconstractor', 'sub contractor')], string="Type", default='owner')

    is_sub_contract = fields.Boolean(related='contract_id.is_sub_contract')
    related_job = fields.Many2one(related='item.related_job')
    state = fields.Selection(related="contract_id.state")


    stage_line_ids = fields.One2many("contract.line.stage.line", "contract_line_id")
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string='taxes')

    @api.constrains('stage_line_ids')
    def constain_stage_ids(self):
        perc = 0
        for record in self:
            perc = 0
            for rec in record.stage_line_ids:
                perc += rec.prec
            print(">")
            if perc != 100:
                raise ValidationError("Percentage must be equal 100")

    def add_stage_line_ids(self):
        view_id = self.env.ref('new_construction.contract_line_stage_view_form')
        return {
            'name': ('Stages'),
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': view_id.id,
            'res_model': 'construction.contract.line',
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            # 'context': {'default_contract_line_id': self.id},
            'target': 'new'
        }

    def view_stage_line_ids(self):
        view_tree = self.env.ref('new_construction.view_contract_form_sub')

        view_form = self.env.ref('new_construction.contract_line_stage_view_form')
        view_id = self.env.ref('new_construction.contract_line_stage_view_form')

        return {
            'name': ('Stages'),
            'view_mode': 'form',
            # 'views': [(view_tree.id, 'tree'), (view_form.id, 'form')],
            'view_id': view_id.id,
            'res_model': 'construction.contract.line',
            'type': 'ir.actions.act_window',
            # 'context': {'default_contract_line_id': self.id},
            # 'domain': [('contract_line_id', '=', self.id)],
            'res_id':self.id,
            'target': 'new'
        }

    @api.onchange('item', 'contract_id')
    def get_iteme(self):
        if self.type=='supconstractor':

            ids = []
            job_id = self.env['construction.job.cost'].search([('project_id', '=', self.project_id.id)])
            for l in job_id:
                ids.append(l.item.id)


            domain = {'item': [('id', 'in', ids)]}
            return {'domain': domain}

    _sql_constraints = [
        ('code_uniq_contract', 'UNIQUE (code,contract_id)', 'You can not have  the same code !')
    ]

    @api.depends("price_unit", "qty", "discount")
    def _get_total_value(self):
        for rec in self:
            value = rec.price_unit * rec.qty
            rec.total_value = (value) - (value * (rec.discount / 100))

    def action_save(self):
        return {'type': 'ir.actions.act_window_close'}





    # @api.onchange('item')
    # def get_item_at_project(self):
    #     if self.contract_id.project_id:
    #         item = self.env['construction.tender'].search([('project_id', '=', self.contract_id.project_id.id)])
    #         ids = []
    #         for rec in item.item:
    #             ids.append(rec.id)
    #         domain = {'item': [('id', 'in', ids)]}
    #
    #         return {'domain': domain}

    @api.onchange('tender_ids')
    def _get_tender_ids(self):

        if self.sup_contract_id.project_id:

            domain = {'tender_ids': [
                ('id', 'in', self.sup_contract_id.project_id.tender_ids.ids)]
            }
            return {'domain': domain}
        elif self.contract_id.project_id:

            domain = {'tender_ids': [('id', 'in', self.contract_id.project_id.tender_ids.ids)]
                      }

            return {'domain': domain}



    @api.model
    def create(self, vals):
        res = super(ContractLine, self).create(vals)
        for rec in self:
            if 'code' in vals:
                res.tender_ids = self.env['construction.tender'].search([('code', '=', rec.code),
                                                                        ('project_id', '=',
                                                                         rec.contract_id.project_id.id)])
            # if res.contract_id.type == 'supconstractor':
            #     res.code = self.env['construction.tender'].search([('id', '=', rec.tender_id.id),
            #                                                        ('project_id', '=',
            #                                                         rec.contract_id.project_id.id)])

        return res


