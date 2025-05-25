from odoo import fields, models, api, _
import itertools

from odoo.exceptions import ValidationError
from num2words import num2words


class Engineer(models.Model):
    _name = "construction.engineer"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'utm.mixin']

    _description = 'engineer'

    name = fields.Char(default=_('New'))
    project_id = fields.Many2one("project.project")
    tag_ids = fields.Many2many('project.tags', relation='construction_engineer_project_tags_rel',
                               related='project_id.tag_ids', string='Tags')
    type = fields.Selection([('owner', 'Owner'), ('supconstractor', 'sub contractor')], string="Type", default='owner')
    contract_id = fields.Many2one("construction.contract",domain="[('type','=',type),('project_id','=',project_id)]")
    type_move = fields.Selection([('process', 'Process'), ('final', 'Final')], string="Type", default='process')


    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'), ('cancel', 'Cancel')], default='draft')
    lines = fields.One2many(
        comodel_name='construction.engineer.lines',
        inverse_name='parent_id',
        string='',
        required=False)
    referance = fields.Char()
    deduction_ids = fields.One2many("contract.deduction.allowance.lines", "eng_template_id",
                                    string="Deductions", domain=[('type', '=', 'deduction')])
    allowance_ids = fields.One2many("contract.deduction.allowance.lines", "eng_template_id",
                                    string="Allowance", domain=[('type', '=', 'addition')])
    total_value = fields.Float("Total value ", compute='_get_total_value', store=True, index=True)
    tag_id_custom = fields.Char(string='Tags', compute='_get_tags', store=True)
    invoice_count = fields.Integer(string='Invoice Count', compute='_compute_invoice_count')

    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = self.env['account.invoice'].search_count([('eng_template_id', '=', rec.id)])

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.invoice',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('new_construction.view_move_construction_tree_sub').id, 'tree'),
                (self.env.ref('new_construction.view_move_construction_invoice_sub').id, 'form'),
            ],
            'domain': [('eng_template_id', '=', self.id)],
            'target': 'current',
        }

    def change_to_word(self, no):
        return num2words(no, lang='ar')
    @api.model
    @api.depends('tag_ids')
    def _get_tags(self):
        tag_custom = ''
        for rec in self:
            if rec.tag_ids:
                tag_custom = ','.join([p.name for p in rec.tag_ids])
            else:
                tag_custom = ''
            rec.tag_id_custom = tag_custom

    @api.depends('lines')
    def _get_total_value(self):
        for rec in self:
            rec.total_value = 0
            for record in rec.lines:
                rec.total_value += record.differance


    @api.onchange("project_id","type")
    def _onchange_project(self):
        if self.project_id and self.type:
            contract_id = self.env['construction.contract'].search([('type','=',self.type),('project_id','=',self.project_id.id)],limit=1)
            if contract_id:
                self.contract_id=contract_id.id

    def action_draft(self):
        temp_id = self.env['account.invoice'].search([('eng_template_id','=',self.id),('state','!=','cancel') ])
        if temp_id:
            raise ValidationError("You can't reset to draft  ")
        else :
            self.state='draft'


    def action_select_items(self):
        return {
            'name': (''),
            'view_mode': 'form',
            'res_model': 'template.items',
            'type': 'ir.actions.act_window',
            'context': {'default_template_id': self.id},
            'target': 'new'
        }



    def action_confirm(self):
        self.state = 'confirm'
        self.create_invoice()

    def action_cancel(self):
        self.state = 'cancel'

    def create_invoice(self):

        prev_invoice_ids = self.env['account.invoice'].search([ \
            ( 'type','=', 'owner'),('state','!=','cancel'),
            ('contract_id','=',self.contract_id.id)])
        check = False
        print(">>>>>>>>>>.",prev_invoice_ids)
        if prev_invoice_ids:
            check=True

        invoice = self.env['account.invoice'].create(
            {
                'type': self.type,
                'type_move': self.type_move,
                'contract_id': self.contract_id.id,
                'eng_template_id': self.id,
                'type':self.type,
                'invoice_line': self.get_lines(self.contract_id,check),


            }
        )
        for ded in self.allowance_ids:
            self.env['contract.addition.lines.invoice'].create({
                'type':ded.type,
                'sub_type':ded.sub_type,
                'name':ded.name.id,
                'account_id':ded.account_id.id,
                'is_precentage':ded.is_precentage,
                'precentage':ded.precentage,
                'invoice_id':invoice.id,

            })
        for ded in self.deduction_ids:
            self.env['contract.deduction.lines.invoice'].create({
                'type':ded.type,
                'sub_type':ded.sub_type,
                'name':ded.name.id,
                'account_id':ded.account_id.id,
                'is_precentage':ded.is_precentage,
                'precentage':ded.precentage,
                'invoice_id':invoice.id,


            })


    def get_lines(self, contract_id,check):
        print('get_linesssssssssssssssssssssssssssssssssssssssssss')
        tender = []

        # if check:
        #     return  tender
        docs = []
        for rec in self.lines:
            if rec.display_type==False:
                tender.append({
                    'id': rec.contract_line_id.id,
                    'contract_line_id': rec.contract_line_id.id,
                    'qty': rec.qty,
                    'price':rec.prec_price,
                    'last_qty':rec.previous_qty

                })
                docs.append((0, 0, {
                    'contract_line_id': rec.contract_line_id.id,
                    # 'quantity':contract_line_id.qty*(percentage/100),
                    'quantity': rec.total_qty,
                    'code': rec.contract_line_id.code,
                    'item': rec.item.id,
                    'item_sub': rec.item_sub.id,
                    # 'price_unit':price,
                    'price_unit': rec.price_unit,
                    'percentage': rec.percentage,
                    'name': rec.name+"-"+rec.stage_id.name,
                    'stage_id': rec.stage_id.id,
                    'value':rec.prec_price,
                    'analytic_distribution': rec.analytic_distribution,
                    'notes' : rec.notes,

                }))


        lines = sorted(tender, key=lambda i: (i['id']))

        invoice_previous = self.env['account.invoice'].search([('contract_id', '=', contract_id.id)],
                                                              order='id desc', limit=1)


        # for key, group in itertools.groupby(lines, key=lambda x: (x['id'])):
        #
        #     i =last_qty= price=qty=0
        #     id = ''
        #
        #     for item in group:
        #         i += item['qty']
        #         price += item['price']
        #         # last_qty += item['last_qty']
        #
        #         id = item['id']
        #     # invoicelines = self.env['account.invoice.line'].search(
        #     #     [('contract_line_id', '=', id), ('invoice_id', '=', invoice_previous.id), ])
        #     # for l in invoicelines:
        #     #     print(">>>>>>>>>>>",l.quantity,l.percentage)
        #     #     last_qty+=(l.quantity)
        #     contract_line_id = self.env['construction.contract.line'].search([('id','=',id)])
        #     percentage = (price/contract_line_id.total_value) * 100 if contract_line_id.total_value > 0 else 0
        #
        #     # print(">>>>>>>>>>>>>>>>",percentage,contract_line_id.qty*(percentage/100))
        #     docs.append((0, 0, {
        #         'contract_line_id': id,
        #         # 'quantity':contract_line_id.qty*(percentage/100),
        #         'quantity': rec.qty,
        #         'code': contract_line_id.code,
        #         'item': contract_line_id.item.id,
        #         # 'price_unit':price,
        #         'price_unit':contract_line_id.price_unit,
        #         'percentage':percentage,
        #         'name':contract_line_id.name,
        #     }))
        return docs

    # def unlink(self):
    #     for rec in self:
    #         if rec.state!='draft':
    #             raise ValidationError("You  Cann't delete ")
    #     res=super(Engineer, self).unlink()
    #     return res

    @api.model
    def create(self, vals):

        res = super(Engineer, self).create(vals)
        res.name = self.env['ir.sequence'].next_by_code(
            'construction.engineer')
        for rec in res.contract_id.deduction_ids:
            new_id = rec.copy()
            new_id.eng_template_id=res.id
            new_id.contract_id=False
        for rec in res.contract_id.allowance_ids:
            new_id = rec.copy()
            new_id.eng_template_id=res.id
            new_id.contract_id = False
        return res


class Engineerlines(models.Model):
    _name = "construction.engineer.lines"
    _description = 'engineer'
    _order = 'name,item'
    sequence = fields.Integer(string='Sequence', default=10)
    parent_id = fields.Many2one("construction.engineer", ondelete='cascade', index=True, copy=False)

    tender_id = fields.Many2one('construction.tender', string="Tender ID")
    item = fields.Many2one('product.item', string='Item')
    name = fields.Text(string="Description")
    uom_id = fields.Many2one(related='item.uom_id', string="Unit of Measure")
    remind_qty = fields.Float("Remind Quantity")
    qty = fields.Float("Quantity")
    tender_qty = fields.Float(string="Contract Quantity")
    notes = fields.Char("Notes")
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False)
    stage_id = fields.Many2one("contract.stage")
    percentage = fields.Float(string="percentage %")
    related_job = fields.Many2one(related='item.related_job')
    prec_price = fields.Float("Price",compute='get_price_cost')
    other_prec = fields.Float("Prectenge stage")
    amount = fields.Float("Amount",compute='get_price_cost')
    amount_previous = fields.Float("Previuos Amount",compute='get_previous_qty')
    contract_line_id  =fields.Many2one("construction.contract.line")
    previous_qty = fields.Float(compute="get_previous_qty")
    contract_id = fields.Many2one(related='parent_id.contract_id')
    total_qty = fields.Float(compute='get_total_qty')
    differance = fields.Float(compute='get_differance', store=True)

    @api.depends('previous_qty', 'qty')
    def get_total_qty(self):
        for rec in self:
            rec.total_qty = 0
            rec.total_qty = rec.previous_qty + rec.qty

    @api.depends( 'item','stage_id','contract_id','parent_id.state')
    def get_previous_qty(self):
        for rec in self:
            rec.previous_qty=rec.amount_previous=0
            if rec.id:
                lines_pre_ids = self.env['construction.engineer.lines'].search([('contract_id','=',rec.contract_id.id),\
                                                                                ('item','=',rec.item.id),
                                                                                ('stage_id','=',rec.stage_id.id),
                                                                                ('id','<',rec.id),
                                                                                ('parent_id.state','=','confirm')
                                                                                ])

                rec.previous_qty = sum(lines_pre_ids.mapped('qty'))

                for l in lines_pre_ids:
                    amount = round((l.total_qty * (l.contract_line_id.price_unit * (l.other_prec / 100))), 2)

                    prec_price = round((l.percentage / 100) * l.amount, 2)
                    # print("==================",l.percentage,l.contract_line_id.price_unit,prec_price,amount,l.amount_previous)
                rec.amount_previous = sum(lines_pre_ids.mapped('differance'))
                # print(">>>>>>>..",)




    @api.depends('qty','percentage','contract_line_id','other_prec','total_qty')
    def get_price_cost(self):
        for rec in self:
            rec.prec_price=rec.amount=0
            rec.amount = round((rec.total_qty  * (rec.contract_line_id.price_unit*(rec.other_prec/100))), 2)

            rec.prec_price = round((rec.percentage / 100) * rec.amount, 2)
            # if rec.other_prec>0:
            #     rec.amount=round(((rec.other_prec/100)*rec.contract_line_id.total_value),2)
            #     if rec.percentage>0:
            #        rec.prec_price=round((rec.percentage/100)*rec.amount,2)
    @api.depends('prec_price','amount_previous')
    def get_differance(self):
        for rec in self:
            rec.differance = abs(rec.prec_price-rec.amount_previous)

    @api.depends('qty','contract_line_id')
    def get_percentage(self):
        for rec in self:
            rec.percentage=0
            if rec.contract_line_id.qty>0:
                p=round((rec.qty/rec.contract_line_id.qty)*100,2)
                rec.percentage=p

    @api.constrains('parent_id','qty')
    def check_percentage(self):

        for rec in self:
            print(">>>>>>>>>>>>>>>>>>>................................", rec.parent_id.project_id.percentage)
            if rec.contract_line_id.qty >0:
                p = round((rec.qty / rec.contract_line_id.qty) * 100, 2)
                if rec.parent_id.project_id.percentage + 100 < p:
                    raise ValidationError("لقد تعديت نسبه الانجاز")



    @api.onchange('qty')
    def _onchange_qty(self):
        if self.remind_qty > 0:
            self.remind_qty -= self.qty
            if self.remind_qty < 0:
                self.remind_qty = 0

    def unlink(self):
        for rec in self:
            if rec.parent_id.state != 'draft':
                raise ValidationError("You  Cann't delete ")
        res = super(Engineerlines, self).unlink()
        return res
