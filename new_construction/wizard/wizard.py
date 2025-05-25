from datetime import datetime

from odoo import models, fields, api

class wizard(models.Model):
    _name = "invoice.tender.wizard"
    contract_id = fields.Many2one("construction.contract")
    tender_ids = fields.Many2many('construction.tender', 'tender_id_invoice_pop', "tender", 'id',)
    contract_lines_ids_ids = fields.Many2many('construction.contract.line', "contract_id_wizard", 'wizard_invi_id','id',
                                      domain="[('sup_contract_id','=',contract_id)]")
    project_id = fields.Many2one("project.project")
    invoice_id = fields.Many2one("account.invoice")
    #invoice_id = fields.Many2one("account.move")



    @api.onchange( 'tender_ids')
    def _get_tender_ids(self):
        ids,lines = [],[]

        tender = self.env['construction.contract.line'].search([('contract_id', '=', self.invoice_id.contract_id.id)])
        if self.invoice_id.type=='supconstractor':
            tender = self.env['construction.contract.line'].search(
                [('sup_contract_id', '=', self.invoice_id.contract_id.id)])

        invoice_lines = self.env['account.invoice.line'].search([('invoice_id','=',self.invoice_id.id)])
        for rec in invoice_lines:
            lines.append(rec.tender_id.id)
        for rec in tender:

            if self.invoice_id.type=='owner':
                if lines:
                    if rec.tender_id.type == 'transcation' and rec.tender_id.id not in lines  :
                        ids.append(rec.tender_id.id)
                else:
                    if rec.tender_id.type == 'transcation':
                        ids.append(rec.tender_id.id)
            elif self.invoice_id.type=='supconstractor':
                if rec.tender_id.id not in lines:
                    ids.append(rec.tender_id.id)



        return {'domain': {'tender_ids': [('id', 'in', ids)]}}

    # @api.onchange('contract_lines_ids_ids')
    # def _get_contract_lines_ids(self):
    #     ids,lines = [],[]
    #
    #     tender = self.env['construction.contract.line'].search(
    #             [('sup_contract_id', '=', self.contract_id.id)])
    #
    #     invoice_lines = self.env['account.invoice.line'].search([('invoice_id','=',self.invoice_id.id)])
    #     for rec in invoice_lines:
    #         domain=[]
    #         # domain.append(('tender_id','=',rec.tender_id.id))
    #         domain.append(('contract_id', '=', self.contract_id.id))
    #         # if rec.sub_contarctor_item:
    #         #     domain.append(('sub_contarctor_item', '=', rec.sub_contarctor_item.id))
    #         # if rec.wbs_item:
    #         #     domain.append(('wbs_item', '=', rec.wbs_item.id))
    #         contract_line_id=self.env['construction.contract.line'].search(domain)
    #         if contract_line_id:
    #              lines.append(rec.contract_line_id.id)
    #
    #     # for rec in tender:
    #     #     domain = []
    #     #     domain.append(('tender_id', '=', rec.tender_id.id))
    #     #     domain.append(('invoice_id', '=', self.invoice_id.id))
    #     #     if rec.sub_contarctor_item:
    #     #         domain.append(('sub_contarctor_item', '=', rec.sub_contarctor_item.id))
    #     #     if rec.wbs_item:
    #     #         domain.append(('wbs_item', '=', rec.wbs_item.id))
    #     #     contract_line_id = self.env['account.invoice.line'].search(domain)
    #     #     if contract_line_id not in lines and contract_line_id:
    #     #         ids.append(contract_line_id.id)
    #
    #
    #
    #
    #
    #     return {'domain': {'contract_lines_ids_ids': [('id', 'in', lines)]}}
    def add_lines(self):
        lines,tender_ids_list,chidls_id = [],[],[]
        for rec in self.contract_lines_ids_ids:
            self.tender_ids=[(4,rec.tender_id.id)]
        for rec in self.tender_ids:
            if rec.id not in self.invoice_id.invoice_line.tender_id.ids:
                if rec.parent_item.id not in self.invoice_id.invoice_line.tender_id.ids:
                        tender_ids_list,chidls_id = self._get_parent(rec.id,tender_ids_list)
                        # print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>",tender_ids_list,chidls_id)
                        if  chidls_id:
                            lines.extend(chidls_id)
                lines.append(rec.id)

        lst=[]
        if self.invoice_id.type=='owner':
            lines = list(dict.fromkeys(lines))
            for rec in lines:
                lst.append((0, 0, {'tender_id': rec}))
        else:
            for rec in self.contract_lines_ids_ids:
                lst.append((0, 0, {
                    'tender_id': rec.tender_id.id,
                    'name': rec.description,
                    'sub_contarctor_item':rec.sub_contarctor_item.id if rec.sub_contarctor_item else '',
                    'wbs_item':rec.wbs_item.id if rec.wbs_item else ''
                }))

        self.invoice_id.invoice_line = lst

    def cancel(self):
        return {'type': 'ir.actions.act_window_close'}
    def _get_parent(self,tender,tender_ids_list):
        check=True
        par_ids=[]
        while(check==True):
            parent_id = self.env['construction.tender'].search([('id','=',tender)])
            if parent_id.parent_item and parent_id.parent_item.id not in tender_ids_list:
                par_ids.append(parent_id.parent_item.id)
                tender=parent_id.parent_item.id
                tender_ids_list.append(parent_id.parent_item.id)
            else:
                check=False
        return par_ids,tender_ids_list
