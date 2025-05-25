from datetime import datetime
from odoo.tools import frozendict, formatLang, format_date, float_compare, Query
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from json import dumps
import json


class AccountMove(models.Model):
    _inherit = 'account.move'
    invoice_id = fields.Many2one('account.invoice', string="Invoice")
    project_id = fields.Many2one("project.project", string="Project", )


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    type_invoice = fields.Selection(related='move_id.invoice_id.type', store=True, index=True)
    project_id = fields.Many2one(related='move_id.project_id', store=True, index=True)


    # def _prepare_analytic_distribution_line(self, distribution, account_id, distribution_on_each_plan):
    #     """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
    #         analytic tags with analytic distribution.
    #     """
    #     self.ensure_one()
    #     account_id = account_id
    #     account = self.env['account.analytic.account'].browse(account_id)
    #     distribution_plan = distribution_on_each_plan.get(account.root_plan_id, 0) + distribution
    #     decimal_precision = self.env['decimal.precision'].precision_get('Percentage Analytic')
    #     if float_compare(distribution_plan, 100, precision_digits=decimal_precision) == 0:
    #         amount = -self.balance * (100 - distribution_on_each_plan.get(account.root_plan_id, 0)) / 100.0
    #     else:
    #         amount = -self.balance * distribution / 100.0
    #     distribution_on_each_plan[account.root_plan_id] = distribution_plan
    #     default_name = self.name or (self.ref or '/' + ' -- ' + (self.partner_id and self.partner_id.name or '/'))
    #     return {
    #         'name': default_name,
    #         'date': self.date,
    #         'account_id': account_id,
    #         'partner_id': self.partner_id.id,
    #         'unit_amount': self.quantity,
    #         'product_id': self.product_id and self.product_id.id or False,
    #         'product_uom_id': self.product_uom_id and self.product_uom_id.id or False,
    #         'amount': amount,
    #         'general_account_id': self.account_id.id,
    #         'ref': self.ref,
    #         'move_line_id': self.id,
    #         'user_id': self.move_id.invoice_user_id.id or self._uid,
    #         'company_id': account.company_id.id or self.company_id.id or self.env.company.id,
    #         'category': 'invoice' if self.move_id.is_sale_document() else 'vendor_bill' if self.move_id.is_purchase_document() else 'other',
    #     }


class Invoice(models.Model):
    _name = "account.invoice"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    name = fields.Char(compute="_get_invoice_name", string="Name")
    notes = fields.Char("Notes")
    type = fields.Selection([('owner', 'Owner'), ('supconstractor', 'sub contractor')], string="Type")
    type_move = fields.Selection([('process', 'Process'), ('final', 'Final')], string="Type")
    contract_id = fields.Many2one("construction.contract", string="Contract")
    contract_value = fields.Float(related='contract_id.total_value', store=True, index=True)
    contract_date = fields.Date(related='contract_id.date', string="Contract Date", store=True, index=True)
    contract_date = fields.Date(related='contract_id.date', string="Contract Date", store=True, index=True)
    number_manual = fields.Char("Manual number")
    project_id = fields.Many2one(related='contract_id.project_id', string="Project", store=True, index=True)
    tag_ids = fields.Many2many('project.tags', relation='account_invoice_project_tags_rel',
                               related='project_id.tag_ids', string='Tags')
    partner_id = fields.Many2one(related="project_id.partner_id", string="Customer", store=True, index=True)
    sub_contactor = fields.Many2one(related='contract_id.sub_contactor', string="sub contractor Name")
    deduction_ids = fields.One2many("contract.deduction.lines.invoice", "invoice_id",
                                    string="Deductions", domain=[('type', '=', 'deduction')])
    allowance_ids = fields.One2many("contract.addition.lines.invoice", "invoice_id",
                                    string="Additions", domain=[('type', '=', 'addition')])
    is_tender = fields.Boolean(default=False)
    invoice_line = fields.One2many('account.invoice.line', 'invoice_id', string="Lines")
    date = fields.Date(string="Date", default=datetime.today())

    due_date = fields.Date(string="Due Date", default=datetime.today())

    state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted'), ('cancel', 'Cancel')], string="State",
                             default='draft')

    current_total_value = fields.Float(compute='get_current_total_value')
    current_total_value_deduction = fields.Float("current deduction", compute='_calculate_total_deduction_addition',
                                                 store=True, index=True)
    current_total_value_addition = fields.Float("Current Additional", compute='_calculate_total_deduction_addition',
                                                store=True, index=True)
    payment_amount = fields.Float("payment Amount", compute="compute_payment_amount")
    payment_count = fields.Integer("payment Count", compute='compute_payment_count')
    payment_state = fields.Selection([('not_paid', 'Not paid'), ('in_payment', 'Partially Paid'), ('paid', 'Paid')]
                                     , compute='_get_payment_state', store=True, index=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    amount_price_total = fields.Float(compute='_get_amount_price_total', store=True, index=True)
    work_value_total = fields.Float(compute='_get_work_value_total', store=True, index=True)
    deduction_value_total = fields.Float(compute='_get_deduction_value_total', store=True, index=True)
    remaining_value = fields.Float("remaining Value", compute='get_remaining')
    is_last = fields.Boolean(compute='_get_last_invoice')
    payment_ids_line = fields.Many2many("account.payment", "p_id", "invoice_id", string="Payment",
                                        compute='get_payment_ids')
    is_payment_visible = fields.Boolean(compute='get_payment_ids')
    eng_template_id = fields.Many2one("construction.engineer")
    tag_id_custom = fields.Char(string='Tags', compute='_get_tags', store=True)
    analytic_account = fields.Many2one('account.analytic.account')

    engineer_template_count = fields.Integer(string='Engineer Template Count',
                                             compute='_compute_engineer_template_count')

    def _compute_engineer_template_count(self):
        for rec in self:
            rec.engineer_template_count = 1 if rec.eng_template_id else 0

    def action_view_engineer_templates(self):
        self.ensure_one()
        return {
            'name': _('Engineer Templates'),
            'type': 'ir.actions.act_window',
            'res_model': 'construction.engineer',
            'view_mode': 'tree,form',
            'domain': [('id', '=', self.eng_template_id.id)],
            'target': 'current',
        }

    def _update_analytic_distribution(self):
        moves = self.env['account.move'].search([('invoice_id', '=', self.id)])
        for move in moves:
            analytic_account = self.analytic_account
            if analytic_account:
                json_value = {
                    str(analytic_account.id): float(100),
                }
                for line in move.line_ids:
                    if line.debit > 0 and line.account_id.account_type == 'expense_direct_cost':
                        line.analytic_distribution = json_value
                    if line.credit > 0 and line.account_id.account_type == 'income':
                        line.analytic_distribution = json_value

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

    @api.depends('invoice_line')
    def get_current_total_value(self):
        for rec in self:
            rec.current_total_value = 0
            if rec.invoice_line:
                rec.current_total_value = sum(rec.invoice_line.mapped('work_value'))

    def register_payment(self):
        view_form = self.env.ref('construction.invoice_payment_view_form')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'view_mode': 'form',
            'views': [(view_form.id, 'form')],
            'res_model': 'construction.payment.wizard',
            'target': 'new',
            'domain': [('invoice_id', '=', self.id)],
            'context': {
                'default_invoice_id': self.id,
                'default_partner_id': self.sub_contactor.id,
                'default_contract_id': self.contract_id.id,
                'default_project_id': self.project_id.id,
            }
        }

    def action_cancel(self):
        self.state = 'cancel'
        move_ids = self.env['account.move'].search([('invoice_id', '=', self.id)])
        for rec in move_ids:
            rec.button_cancel()

    @api.depends('payment_ids_line')
    def compute_payment_amount(self):
        for rec in self:
            payment_ids = self.env['account.payment'].search([('invoice_ids', '=', rec.id)])
            print()
            rec.payment_amount = sum(l.amount for l in payment_ids)

    @api.depends('payment_ids_line')
    def compute_payment_count(self):
        for rec in self:
            payment_ids = self.env['account.payment'].search([('invoice_ids', '=', self.id)])
            rec.payment_count = len(payment_ids.ids)

    @api.depends('state', 'payment_state', 'remaining_value')
    def get_payment_ids(self):
        for rec in self:

            rec.payment_ids_line = []
            rec.is_payment_visible = False
            if rec.state == 'posted' and rec.payment_state != 'paid':
                lines = []
                payment_ids = self.env['account.payment'].search([('state', '=', 'posted'),
                                                                  ('contract_id', '=', rec.contract_id.id)])
                for line in payment_ids:
                    amount = line.amount
                    if not line.invoice_ids and not line.reconciled_bill_ids:
                        if rec.remaining_value >= amount:
                            rec.payment_ids_line = [(4, line.id,)]
                            rec.is_payment_visible = True

    # @api.depends('contract_id.number_of_invoice')
    def _get_last_invoice(self):
        for rec in self:
            rec.is_last = False
            # inv_ids = self.env['account.invoice'].search([('contract_id', '=', self.contract_id.id)], order='id desc',
            #                                              limit=1)
            # if inv_ids.id == rec.id:
            #     rec.is_last = True

    def reset_invoice(self):
        self.state = 'draft'
        move_ids = self.env['account.move'].search([('invoice_id', '=', self.id)])
        for rec in move_ids:
            rec.button_cancel()

    @api.depends('payment_amount')
    def get_remaining(self):
        for rec in self:
            rec.remaining_value = abs(rec.amount_price_total - rec.payment_amount)

    @api.depends('deduction_ids', 'allowance_ids')
    def _calculate_total_deduction_addition(self):
        for rec in self:
            deduction_value, addition_value = 0, 0
            for ded in rec.deduction_ids:
                deduction_value += ded.current_value
            for allow in rec.allowance_ids:
                addition_value += allow.current_value
            rec.current_total_value_deduction = deduction_value
            rec.current_total_value_addition = addition_value

    @api.depends('current_total_value', 'deduction_ids', 'allowance_ids', 'work_value_total', 'deduction_value_total')
    def _get_amount_price_total(self):
        for rec in self:
            deduction_value, addition_value = 0, 0
            for ded in rec.deduction_ids:
                deduction_value += ded.current_value
            for allow in rec.allowance_ids:
                addition_value += allow.current_value
            rec.amount_price_total = rec.work_value_total - rec.deduction_value_total

    @api.depends('invoice_line', 'invoice_line.work_value', 'invoice_line.t_value')
    def _get_work_value_total(self):
        lines = []
        for rec in self:
            for line in rec.invoice_line:
                lines.append(line.work_value)
            rec.work_value_total = sum(lines)

    # @api.depends('deduction_ids', 'invoice_line', 'deduction_ids.precentage')
    # def _get_deduction_value_total(self):
    #     lines = []
    #     for rec in self:
    #         for line in rec.deduction_ids:
    #             lines.append(line.value)
    #         rec.deduction_value_total = sum(lines)

    @api.depends('deduction_ids', 'invoice_line', 'deduction_ids.precentage')
    def _get_deduction_value_total(self):
        lines = []
        for rec in self:
            for line in rec.deduction_ids:
                lines.append(line.current_value)
            rec.deduction_value_total = sum(lines)

    @api.depends('project_id')
    def _get_invoice_name(self):
        for rec in self:
            rec.name = 'INV/' + str(rec.id).zfill(5)

    @api.depends('state')
    def _get_payment_state(self):
        for rec in self:
            rec.payment_state = 'not_paid'
            if rec.payment_amount == 0:
                rec.payment_state = 'not_paid'
            elif rec.payment_amount < rec.amount_price_total:
                rec.payment_state = 'in_payment'
            elif rec.payment_amount == rec.amount_price_total:
                rec.payment_state = 'paid'
            lines = []

            p_list = []
            # for p in rec.payment_ids:
            #     p_list.append(p.payment_id.id)

            # if rec.state == 'posted':
            # screen_ids = self.env['account.screen'].search([('invoice_id','=',self.id)])
            # for sr in screen_ids:
            #     sr.unlink()

            # payment_ids = self.env['account.payment'].search([('state','=','posted'),('contract_id', '=', rec.contract_id.id)])
            # for line in payment_ids:
            #     if not line.invoice_ids and not line.reconciled_bill_ids :
            #         if  line.id not in p_list:
            #
            #             lines.append((0, 0, {
            #                 'payment_id': line.id
            #
            #             }))
            #
            #     rec.payment_ids = lines

    def action_post(self):
        self.state = 'posted'
        self.create_journal_enteries()
        self._update_analytic_distribution()

    def create_journal_enteries(self):
        lines = self._get_move_line()
        print(">>>>>>>>>xxxx>>>>>>>>>> ", lines)

        journal = ''
        partner_id = ''
        if self.type == 'owner':
            if not self.company_id.ks_middle_journal_owner:
                raise ValidationError("Please Select journal")
            journal = self.company_id.ks_middle_journal_owner.id
            partner_id = self.partner_id.id

        elif self.type == 'supconstractor':
            if not self.company_id.ks_middle_account_sup:
                raise ValidationError("Please Select journal")
            journal = self.company_id.ks_middle_account_sup.id
            partner_id = self.sub_contactor.id
        move2 = self.env['account.move'].create({'date': datetime.today(),
                                                 'partner_id': partner_id,
                                                 'company_id': self.company_id.id,
                                                 'journal_id': journal,
                                                 'name': self._get_payment_name(journal),
                                                 'project_id': self.project_id.id,
                                                 'line_ids': lines,
                                                 'invoice_id': self.id
                                                 })

    def _get_payment_name(self, journal):
        sequ = self.env['account.move'].search([('journal_id', '=', journal)])
        journal_id = self.env['account.journal'].search([('id', '=', journal)])
        name = journal_id.code + "/" + str(datetime.now().year) + "/" \
               + str(datetime.now().month) + "/" + str(len(sequ) + 1).zfill(4)
        return name

    def _get_move_line(self):
        lines = []
        debit, credit = 0, 0
        if self.type == 'supconstractor':
            for rec in self.deduction_ids:
                credit += round(rec.current_value, 2)
                lines.append((0, 0, {
                    'account_id': rec.account_id.id,
                    'credit': round(rec.current_value, 2),
                    'debit': 0,
                    'partner_id': self.sub_contactor.id,
                    'name': self._get_invoice_lines_notes(),
                    'analytic_distribution': self._get_invoice_lines_analytic_distribution(),
                }))
            for rec in self.allowance_ids:
                debit += round(rec.current_value, 2)
                lines.append((0, 0, {
                    'account_id': rec.account_id.id,
                    'debit': round(rec.current_value, 2),
                    'credit': 0,
                    'partner_id': self.sub_contactor.id,
                    'name': self._get_invoice_lines_notes(),
                    'analytic_distribution': self._get_invoice_lines_analytic_distribution(),
                }))
        else:
            for rec in self.deduction_ids:
                debit += round(rec.current_value, 2)
                lines.append((0, 0, {
                    'account_id': rec.account_id.id,
                    'debit': round(rec.current_value, 2),
                    'credit': 0,
                    'partner_id': self.partner_id.id,
                    'name': self._get_invoice_lines_notes(),
                    'analytic_distribution': self._get_invoice_lines_analytic_distribution(),

                }))
            for rec in self.allowance_ids:
                credit += round(rec.current_value, 2)
                lines.append((0, 0, {
                    'account_id': rec.account_id.id,
                    'credit': round(rec.current_value, 2),
                    'debit': 0,
                    'partner_id': self.partner_id.id,
                    'name': self._get_invoice_lines_notes(),
                    'analytic_distribution': self._get_invoice_lines_analytic_distribution(),

                }))
        if self.type != 'supconstractor':
            credit += round(self.current_total_value, 2)
            lines.append((0, 0, {
                'account_id': self.contract_id.revenue_account_id.id,
                'credit': round(self.current_total_value, 2),
                'debit': 0,
                'partner_id': self.partner_id.id,
                'name': self._get_invoice_lines_notes(),
                'analytic_distribution': self._get_invoice_lines_analytic_distribution(),

            }))
            lines.append((0, 0, {
                'account_id': self.contract_id.account_id.id,
                'credit': 0,
                'debit': round(credit - debit, 2),
                'partner_id': self.partner_id.id,
                'name': self._get_invoice_lines_notes(),
                'analytic_distribution': self._get_invoice_lines_analytic_distribution(),
            }))
        elif self.type == 'supconstractor':
            print(">>>>>>>>>>>XXX ", round(self.current_total_value, 2))
            print(">>>>>>>>>>>www ", self.amount_price_total)
            print(">>>>>>>>>>>uuu ", credit + self.amount_price_total)
            print(">>>>>>>>>>>ooo ", round(credit + self.amount_price_total, 2))
            debit += round(self.current_total_value, 2)
            lines.append((0, 0, {
                'account_id': self.contract_id.revenue_account_id.id,
                'credit': 0,
                'debit': round(self.current_total_value, 2),
                'partner_id': self.sub_contactor.id,
                'name': self._get_invoice_lines_notes(),
                'analytic_distribution': self._get_invoice_lines_analytic_distribution(),

            }))
            print(debit, ">>>>>>>>>>>XXX ", credit)
            print(debit - credit, ">>>>>>>>>>>XXX ", round(debit - credit, 2))
            lines.append((0, 0, {
                'account_id': self.contract_id.account_id.id,
                'credit': round(self.amount_price_total, 2),
                'debit': 0,
                'partner_id': self.sub_contactor.id,
                'name': self._get_invoice_lines_notes(),
                'analytic_distribution': self._get_invoice_lines_analytic_distribution(),

            }))

        return lines

    def _get_invoice_lines_notes(self):
        """ Collect all notes from invoice lines and join them as a single string """
        notes_list = []
        for line in self.invoice_line:
            if line.notes:
                notes_list.append(line.notes)
        return '\n'.join(notes_list) if notes_list else '/'

    def _get_invoice_lines_analytic_distribution(self):
        """ Merge all analytic distribution from invoice lines """
        result = {}
        for line in self.invoice_line:
            if line.analytic_distribution:
                for key, value in line.analytic_distribution.items():
                    if key in result:
                        result[key] += value
                    else:
                        result[key] = value
        return result

    def action_payment(self):
        view_form = self.env.ref('new_construction.payment_inherited_form_invoice')
        payment_id = self.env['account.payment'].search([('invoice_ids', '=', self.id)])
        amount = 0
        for rec in payment_id:
            amount += rec.amount
        journal, partner_id, payment_type, partner_type = '', '', '', ''
        if self.type == 'owner':
            if not self.company_id.ks_middle_journal_owner:
                raise ValidationError("Please Select journal")
            journal = self.company_id.ks_middle_journal_owner.id
            partner_id = self.partner_id.id
            payment_type = 'inbound'
            partner_type = 'customer'

        elif self.type == 'supconstractor':
            if not self.company_id.ks_middle_account_sup:
                raise ValidationError("Please Select journal")
            journal = self.company_id.ks_middle_account_sup.id
            partner_id = self.sub_contactor.id
            payment_type = 'outbound'
            partner_type = 'supplier'

        return {
            'type': 'ir.actions.act_window',
            'name': 'Payment',
            'view_mode': 'form',
            'views': [(view_form.id, 'form')],
            'res_model': 'account.payment',
            'target': 'current',
            'context': {
                'default_invoice_ids': self.id,
                'default_journal_id': journal,
                'default_payment_type': payment_type,
                'default_partner_type': partner_type,
                'default_contract_id': self.contract_id.id if self.contract_id else '',
                'default_partner_id': partner_id,
                'default_amount': self.remaining_value
            }

        }

    def view_journal(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Journal',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'target': 'current',
            'domain': [('invoice_id', '=', self.id)]

        }

    def view_payment(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payment',
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'target': 'current',
            'domain': [('invoice_ids', '=', self.id)]
        }

    def unlink(self):
        for rec in self:
            if rec.state == 'posted':
                raise ValidationError("You Cann't posted invoice")
            for recr in rec.invoice_line:
                recr.unlink()
            for ded in rec.deduction_ids:
                ded.unlink()
            for all in rec.allowance_ids:
                all.unlink()
        res = super(Invoice, self).unlink()
        return res


class InvoiceLine(models.Model):
    _name = "account.invoice.line"
    _order = 'tender_id'

    project_id = fields.Many2one(related='invoice_id.project_id', store=True, index=True)
    tender_id = fields.Many2one('construction.tender', string="Tender ID")
    contract_line_id = fields.Many2one("construction.contract.line")
    # name = fields.Text(related='tender_id.description', string="Description")  #Abdulrhman comment
    name = fields.Text(string="Description")

    code = fields.Char(string="Code")
    item = fields.Many2one("product.item", string='Item')
    uom_id = fields.Many2one(related='item.uom_id', string="Unit of Measure", store=True, index=True)

    type = fields.Selection([('owner', 'Owner'), ('supconstractor', 'sub contractor')], string="Type")

    notes = fields.Char("Notes")
    quantity = fields.Float("Quantity")
    price_unit = fields.Float(string="Price Unit")
    value = fields.Float(readonly=True)
    previous_value = fields.Float(compute='get_previous_value', store=True)
    work_value = fields.Float(string="Work Value", compute='_compute_work_value', store=True)
    parent_id = fields.Many2one("account.invoice", ondelete='cascade', index=True, copy=False)
    contract_id = fields.Many2one(related='invoice_id.contract_id')
    t_value = fields.Float('Value')
    item = fields.Many2one('product.item', string='بند المقايسة', domain=[('item_type', '=', 'assay_item')])
    item_sub = fields.Many2one('product.item', string='بند المقاول', domain=[('item_type', '=', 'contractor_item')])

    # @api.depends('quantity', 'price_unit')
    # def get_value(self):
    #     for rec in self:
    #         rec.value = rec.quantity * rec.price_unit

    project_id = fields.Many2one(comodel_name='project.project', string='Project', related="invoice_id.project_id",
                                 store=True)
    invoice_id = fields.Many2one("account.invoice")
    date = fields.Date(related='invoice_id.date', store=True, index=True)

    partner_id = fields.Many2one(related="invoice_id.partner_id", store=True, index=True)

    move_id = fields.Many2one("account.move")
    wbs_item_id = fields.Char(string="WBS-item Id")
    wbs_item = fields.Many2one('wbs.item.line', string="WBS-item", domain="[('id','=',wbs_item_id)]")
    sub_contarctor_item_id = fields.Char('construction subconstractor ID')
    sub_contarctor_item = fields.Many2one('construction.subconstractor', domain="[('id','=',sub_contarctor_item_id)]")
    percentage = fields.Float("percentage %")
    differance = fields.Float(compute='get_differance', store=True)
    stage_id =  fields.Many2one("contract.stage")
    analytic_distribution = fields.Json(string="Analytic Distribution")
    analytic_precision = fields.Integer(string="Analytic Precision", default=2)

    @api.depends('previous_value', 'value')
    def get_differance(self):
        for rec in self:
            rec.differance =  rec.value- rec.previous_value


    # @api.depends('price_unit', 'quantity')
    # def _get_value_line(self):
    #     for rec in self:
    #         rec.value = rec.price_unit * rec.quantity

    @api.depends('item', 'value', 'item_sub','stage_id')
    def get_previous_value(self):
        for rec in self:
            print('pppppppppp asc', rec)
            print('pppppppppp asc', rec.contract_id.id)
            rec.previous_value = 0
            if rec.id:
                lines_pre_ids = self.env['account.invoice.line'].search(
                    [
                        ('item', '=', rec.item.id),
                        ('item_sub', '=', rec.item_sub.id),
                        ('uom_id', '=', rec.uom_id.id),
                        ('contract_id', '=', rec.contract_id.id),
                        ('id', '<', rec.id),
                        ('stage_id','=',rec.stage_id.id)
                    ], order='id asc')
                for line in lines_pre_ids:
                    print('line', line)
                    rec.previous_value = line.value

    @api.depends('item', 't_value', 'previous_value')
    def _compute_work_value(self):
        for rec in self:
            rec.work_value = rec.value - rec.previous_value
